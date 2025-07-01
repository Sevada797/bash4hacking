import aiohttp
import asyncio
import argparse
import os
import re
import resource

soft, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
safe_limit = min(soft - 100, 10000)
safe_limit=500
print(f"[INFO] Using max {safe_limit} connections")

from aiohttp.client_exceptions import (
    ClientConnectorError,
    ClientProxyConnectionError,
    ClientOSError,
    ClientResponseError,
    ServerTimeoutError,
    ClientSSLError
)

async def fetch(session, url, values, f_log, log_lock, counter, total, a_chars=0, b_chars=0):
    try:
        async with session.get(url, timeout=5, ssl=False) as resp:
            content_type = resp.headers.get("Content-Type", "").lower()
            allowed_types = ["text/html", "application/json", "application/javascript", "text/plain"]
            if not any(ct in content_type for ct in allowed_types):
                return

            try:
                html = await resp.text()
            except UnicodeDecodeError:
                try:
                    html = (await resp.read()).decode('latin-1')
                except Exception:
                    html = ""

            for val in values:
                val_lower = val.lower()
                html_lower = html.lower()
                for match in re.finditer(re.escape(val_lower), html_lower):
                    start = max(0, match.start() - b_chars)
                    end = min(len(html), match.end() + a_chars)
                    snippet = html[start:end].replace('\n', ' ').replace('\r', '')
                    async with log_lock:
                        f_log.write(f"{url} -> {val}\nContext: {snippet}\n\n")
                        f_log.flush()

    except (ClientConnectorError, ClientProxyConnectionError, ClientOSError, ClientResponseError,
            ServerTimeoutError, asyncio.TimeoutError, ClientSSLError, aiohttp.InvalidURL):
        pass
    except Exception as e:
        print(f"\n[ERROR] Unexpected error for {url}: {e}")
    finally:
        counter[0] += 1
        print(f"\r{counter[0]} requests done out of {total}", end="", flush=True)


async def main(file, values, use_ua, use_burp, custom_headers, a_chars, b_chars):
    if not os.path.exists(file):
        print(f"[ERROR] File {file} not found.")
        return

    with open(file) as f:
        urls = [line.strip() for line in f if line.strip()]

    if not urls or not re.match(r"^https?://", urls[0]):
        print(f"\n[ERROR] URLs should start with http(s). Run:")
        print(f"  sed -i 's|^|https://|' {file}")
        return

    os.makedirs("hf", exist_ok=True)
    log_file = "hf/log.txt"
    if os.path.exists(log_file):
        os.remove(log_file)

    headers = {}
    if use_ua:
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/113.0.0.0"

    if custom_headers:
        for h in custom_headers:
            if ":" in h:
                k, v = h.split(":", 1)
                headers[k.strip()] = v.strip()

    proxy = "http://127.0.0.1:8080" if use_burp else None

    connector = aiohttp.TCPConnector(limit=safe_limit)
    timeout = aiohttp.ClientTimeout(total=10)
    counter = [0]
    total = len(urls)
    sem = asyncio.Semaphore(safe_limit)

    async with aiohttp.ClientSession(headers=headers, connector=connector, timeout=timeout) as session:
        session._default_proxy = proxy

        log_lock = asyncio.Lock()
        with open(log_file, "a") as f_log:

            async def sem_fetch(url):
                async with sem:
                    await fetch(session, url, values, f_log, log_lock, counter, total, a_chars, b_chars)

            tasks = [asyncio.create_task(sem_fetch(url)) for url in urls]
            await asyncio.gather(*tasks)

    print(f"\n[INFO]: Check {log_file} for successful finds")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Async HF Reflector")
    parser.add_argument("file", help="File with URLs")
    parser.add_argument("value", nargs="?", help="Single value to search (optional if -E is used)")
    parser.add_argument("-E", help="Pipe-separated list of values (e.g. 'token|auth|csrf')")
    parser.add_argument("--ua-chrome", action="store_true", help="Use Chrome User-Agent")
    parser.add_argument("--burp", action="store_true", help="Use Burp Proxy")
    parser.add_argument("-H", action="append", help="Custom headers (e.g., -H 'X-Test: 1'). Use multiple times.")
    parser.add_argument("-A", type=int, default=0, help="Additional characters AFTER match")
    parser.add_argument("-B", type=int, default=0, help="Additional characters BEFORE match")

    args = parser.parse_args()

    if not args.value and not args.E:
        parser.error("You must provide either a value or -E with multiple values.")

    value_list = args.E.split("|") if args.E else [args.value]

    try:
        asyncio.run(main(args.file, value_list, args.ua_chrome, args.burp, args.H, args.A, args.B))
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user.")
