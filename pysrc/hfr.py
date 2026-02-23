import aiohttp
import asyncio
import argparse
import os
import re
import resource
import aiofiles

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
# retry helper (ONLY for timeout)
# -------------------------
async def retry_with_longer_timeout(session, url, **kwargs):
    retry_timeout = aiohttp.ClientTimeout(
        total=60,
        connect=10,
        sock_connect=10,
        sock_read=30
    )
    async with session.get(url, timeout=retry_timeout, **kwargs) as resp:
        raw = await resp.content.read(500 * 1024)
        return raw, resp


async def fetch(session, url, patterns, f_log, log_lock, counter, total, allow_redirects):
    try:
        async with session.get(url, ssl=False, allow_redirects=allow_redirects) as resp:
            content_type = resp.headers.get("Content-Type", "").lower()

            allowed_types = [
                "text/html",
                "text/plain",
                "text/html; charset=utf-8",
                "text/plain; charset=utf-8",
                "application/json",
                "application/javascript",
                "application/xml"
            ]

            if not any(ct in content_type for ct in allowed_types):
                return

            raw = await resp.content.read(500 * 1024)
            html = raw.decode(errors="ignore")

            for pattern in patterns:
                for match in re.finditer(pattern, html, re.DOTALL):
                    matched_text = match.group(0)
                    async with log_lock:
                        await f_log.write(f"[HFR] Pattern hit\n")
                        await f_log.write(f"Pattern: {pattern}\n")
                        await f_log.write(f"Match: {matched_text}\n")
                        await f_log.write(f"URL: {url}\n\n")

    except asyncio.TimeoutError:
        try:
            raw, resp = await retry_with_longer_timeout(
                session,
                url,
                ssl=False,
                allow_redirects=allow_redirects
            )
            html = raw.decode(errors="ignore")

            for pattern in patterns:
                for match in re.finditer(pattern, html, re.DOTALL):
                    matched_text = match.group(0)
                    async with log_lock:
                        await f_log.write(f"[HFR] Pattern hit (retry)\n")
                        await f_log.write(f"Pattern: {pattern}\n")
                        await f_log.write(f"Match: {matched_text}\n")
                        await f_log.write(f"URL: {url}\n\n")

        except Exception:
            pass

    except (ClientConnectorError, ClientProxyConnectionError, ClientOSError,
            ClientResponseError, ServerTimeoutError, ClientSSLError, aiohttp.InvalidURL):
        pass

    except Exception as e:
        print(f"\n[ERROR] Unexpected error for {url}: {e}")

    finally:
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
        total=120,
        connect=5,
        sock_connect=5,
        sock_read=10
    )

    counter = [0]
    total = len(urls)
    allow_redirects = not no_follow

    async with aiohttp.ClientSession(headers=headers, connector=connector, timeout=timeout) as session:
        session._default_proxy = proxy

        log_lock = asyncio.Lock()
        async with aiofiles.open(log_file, "a") as f_log:
            tasks = [
                asyncio.create_task(
                    fetch(session, url, patterns, f_log, log_lock, counter, total, allow_redirects)
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