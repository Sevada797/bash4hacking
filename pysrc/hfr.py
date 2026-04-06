import aiohttp
import asyncio
import argparse
import os
import re
import resource
import aiofiles
import threading
import signal
import time


# -------------------------
# Debug kill switch — set to True to enable
# -------------------------

active_urls = set()
active_urls_lock = threading.Lock()


DEBUG_AND_KILL = False
DEBUG_KILL_AFTER_SECONDS = 30

def debug_kill_timer():
    time.sleep(DEBUG_KILL_AFTER_SECONDS)
    with active_urls_lock:
        urls_snapshot = list(active_urls)

    print(f"\n[DEBUG] {DEBUG_KILL_AFTER_SECONDS}s timer fired — dumping state & killing!")
    print(f"[DEBUG] Active URLs at kill time ({len(urls_snapshot)}):")
    for u in urls_snapshot:
        print(f"  -> {u}")

    os.makedirs("hfr", exist_ok=True)
    try:
        with open("hfr/debug_kill.txt", "w") as f:
            f.write(f"Killed after: {DEBUG_KILL_AFTER_SECONDS}s\n")
            f.write(f"Active URLs ({len(urls_snapshot)}):\n")
            for u in urls_snapshot:
                f.write(f"  {u}\n")
        print("[DEBUG] Written to hfr/debug_kill.txt")
    except Exception as e:
        print(f"[DEBUG] Failed to write: {e}")

    os.kill(os.getpid(), signal.SIGKILL)  # SIGKILL cannot be caught or ignored


soft, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
safe_limit = min(soft - 100, 10000)
safe_limit = 500
print(f"[INFO] Using max {safe_limit} connections")

from aiohttp.client_exceptions import (
    ClientConnectorError,
    ClientProxyConnectionError,
    ClientOSError,
    ClientResponseError,
    ServerTimeoutError,
    ClientSSLError
)


# -------------------------
# Magic bytes signatures
# -------------------------
MAGIC_BYTES = {
    b'\x25\x50\x44\x46': 'PDF',
    b'\xFF\xD8\xFF': 'JPEG/JPG',
    b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A': 'PNG',
    b'\x47\x49\x46\x38\x37\x61': 'GIF87a',
    b'\x47\x49\x46\x38\x39\x61': 'GIF89a',
    b'\x50\x4B\x03\x04': 'ZIP',
    b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1': 'DOC/XLS/PPT (OLE)',
    b'\x42\x4D': 'BMP',
    b'\x1F\x8B': 'GZIP',
    b'\x37\x7A\xBC\xAF\x27\x1C': '7ZIP',
    b'\x52\x61\x72\x21\x1A\x07': 'RAR',
    b'\x4F\x67\x67\x53': 'OGG',
    b'\x49\x44\x33': 'MP3',
    b'\x00\x00\x00\x18\x66\x74\x79\x70': 'MP4',
    b'\x52\x49\x46\x46': 'RIFF/WAV/AVI',
    b'\x7F\x45\x4C\x46': 'ELF binary',
    b'\x4D\x5A': 'EXE/DLL',
}

def detect_magic(raw: bytes):
    for magic, filetype in MAGIC_BYTES.items():
        if raw.startswith(magic):
            return filetype
    return None

# -------------------------
# retry helper (ONLY for timeout)
# -------------------------
async def retry_with_longer_timeout(session, url, **kwargs):
    retry_timeout = aiohttp.ClientTimeout(
        total=10,
        connect=10,
        sock_connect=10,
        sock_read=30
    )
    async with session.get(url, timeout=retry_timeout, **kwargs) as resp:
        raw = await resp.content.read(500 * 1024)
        return raw, resp


async def fetch(session, url, patterns, f_log, log_lock, counter, total, allow_redirects, semaphore):
    acquired = await semaphore.acquire()
    with active_urls_lock:
        active_urls.add(url)

    try:
        async with session.get(url, ssl=False, allow_redirects=allow_redirects) as resp:
            # ← release semaphore NOW — connection is open, slot is free for next URL
            semaphore.release()
            acquired = False

            raw_peek = await resp.content.read(16)
            filetype = detect_magic(raw_peek)
            if filetype:
                print(f"\r[SKIP] {url} -> {filetype}")
                return

            content_type = resp.headers.get("Content-Type", "").lower()
            allowed_types = ["text/html", "text/plain", "application/json",
                             "application/javascript", "application/xml"]
            if not any(ct in content_type for ct in allowed_types):
                return

            raw_rest = await resp.content.read(500 * 1024 - 16)
            raw = raw_peek + raw_rest
            html = raw.decode(errors="ignore")

            for pattern in patterns:
                for match in re.finditer(pattern, html, re.DOTALL):
                    async with log_lock:
                        await f_log.write(f"[HFR] Pattern hit\n")
                        await f_log.write(f"Pattern: {pattern}\n")
                        await f_log.write(f"Match: {match.group(0)}\n")
                        await f_log.write(f"URL: {url}\n\n")

    except asyncio.TimeoutError:
        if acquired:
            semaphore.release()
            acquired = False
        try:
            retry_timeout = aiohttp.ClientTimeout(total=10, connect=10, sock_connect=10, sock_read=30)
            async with session.get(url, ssl=False, allow_redirects=allow_redirects, timeout=retry_timeout) as resp:
                raw = await resp.content.read(500 * 1024)
                filetype = detect_magic(raw)
                if filetype:
                    return
                html = raw.decode(errors="ignore")
                for pattern in patterns:
                    for match in re.finditer(pattern, html, re.DOTALL):
                        async with log_lock:
                            await f_log.write(f"[HFR] Pattern hit (retry)\n")
                            await f_log.write(f"Pattern: {pattern}\n")
                            await f_log.write(f"Match: {match.group(0)}\n")
                            await f_log.write(f"URL: {url}\n\n")
        except Exception:
            pass

    except (ClientConnectorError, ClientProxyConnectionError, ClientOSError,
            ClientResponseError, ServerTimeoutError, ClientSSLError, aiohttp.InvalidURL):
        if acquired:
            semaphore.release()
            acquired = False

    except Exception as e:
        print(f"\n[ERROR] {url}: {e}")
        if acquired:
            semaphore.release()
            acquired = False

    finally:
        if acquired:          # safety net — should never hit but just in case
            semaphore.release()
        with active_urls_lock:
            active_urls.discard(url)
        counter[0] += 1
        print(f"\r{counter[0]} requests done out of {total}", end="", flush=True)


async def load_targets(target_input):
    """Non-blocking target loader - file or single URL"""
    if target_input.startswith("http"):
        return [target_input]

    async with aiofiles.open(target_input, "r") as f:
        content = await f.read()
        return [
            line.strip()
            for line in content.split("\n")
            if line.strip() and not line.startswith("#")
        ]


async def load_pattern(pattern_input):
    """Load pattern from file or use direct input"""
    # Expand ~ to home directory
    expanded_path = os.path.expanduser(pattern_input)
    
    # Check if it's a file
    if os.path.isfile(expanded_path):
        async with aiofiles.open(expanded_path, "r") as f:
            content = await f.read()
            # If file has multiple lines, return them (remove comments/whitespace)
            patterns = [
                line.strip()
                for line in content.split("\n")
                if line.strip() and not line.startswith("#")
            ]
            return patterns if patterns else [content.strip()]
    
    # Otherwise treat as direct regex input
    return [pattern_input]


async def main(file, patterns, use_ua, use_burp, custom_headers, no_follow):
    if DEBUG_AND_KILL:
        threading.Thread(target=debug_kill_timer, daemon=True).start()
    semaphore = asyncio.Semaphore(100)  # tune this number down if CPU spikes
    try:
        urls = await load_targets(file)
    except Exception as e:
        print(f"[ERROR] Failed to load targets: {e}")
        return

    if not urls or not re.match(r"^https?://", urls[0]):
        print(f"\n[ERROR] URLs should start with http(s)")
        if isinstance(file, str) and not file.startswith("http"):
            print(f"  sed -i 's|^|https://|' {file}")
        return

    os.makedirs("hfr", exist_ok=True)
    log_file = "hfr/log.txt"
    
    # Clear old logs
    async with aiofiles.open(log_file, "w") as f:
        await f.write("")

    headers = {}
    if use_ua:
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/113.0.0.0"

    if custom_headers:
        for h in custom_headers:
            if ":" in h:
                k, v = h.split(":", 1)
                headers[k.strip()] = v.strip()

    proxy = "http://127.0.0.1:8080" if use_burp else None

    connector = aiohttp.TCPConnector(limit=200, limit_per_host=10)
    timeout = aiohttp.ClientTimeout(
        total=10,
        connect=5,
        sock_connect=5,
        sock_read=10
    )

    counter = [0]
    total = len(urls)
    allow_redirects = not no_follow

    async with aiohttp.ClientSession(headers=headers, connector=connector, timeout=timeout, trust_env=True) as session:
        session._default_proxy = proxy

        log_lock = asyncio.Lock()
        async with aiofiles.open(log_file, "a") as f_log:
            tasks = [
                asyncio.create_task(
                    fetch(session, url, patterns, f_log, log_lock, counter, total, allow_redirects, semaphore)
                )
                for url in urls
            ]
            await asyncio.gather(*tasks)

    print(f"\n[INFO]: Check {log_file} for successful finds")


def parse_headers(header_list):
    """Parse custom headers"""
    headers = {}
    if header_list:
        for h in header_list:
            if ":" in h:
                k, v = h.split(":", 1)
                headers[k.strip()] = v.strip()
    return headers


def parse_args():
    parser = argparse.ArgumentParser(description="HFR - HTTP Find Regex (async pattern matcher for URLs)")
    parser.add_argument("file", help="File with URLs or single URL")
    parser.add_argument("pattern", help="Regex pattern or file with patterns (one per line)")
    parser.add_argument("--ua-chrome", action="store_true", help="Use Chrome User-Agent")
    parser.add_argument("--burp", action="store_true", help="Use Burp Proxy")
    parser.add_argument("-H", action="append", default=[], help="Custom headers (e.g., -H 'X-Test: 1'). Use multiple times.")
    parser.add_argument("-nf", "--no-follow", action="store_true", help="Do NOT follow redirects")
    return parser.parse_args()


async def main_async():
    args = parse_args()
    
    patterns = await load_pattern(args.pattern)
    
    print(f"[HFR] Loaded {len(patterns)} pattern(s):")
    for p in patterns:
        print(f"  - {p}")
    
    try:
        await main(args.file, patterns, args.ua_chrome, args.burp, args.H, args.no_follow)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user.")


if __name__ == "__main__":
    asyncio.run(main_async())