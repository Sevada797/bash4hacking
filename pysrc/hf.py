import aiohttp
import asyncio
import argparse
import os
import re
import resource

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


async def fetch(session, url, values, f_log, log_lock, counter, total, allow_redirects, a_chars=0, b_chars=0):
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
            html_lower = html.lower()

            for val in values:
                val_lower = val.lower()
                for match in re.finditer(re.escape(val_lower), html_lower):
                    start = max(0, match.start() - b_chars)
                    end = min(len(html), match.end() + a_chars)
                    snippet = html[start:end].replace('\n', ' ').replace('\r', '')
                    async with log_lock:
                        f_log.write(f"{url} -> {val}\nContext: {snippet}\n\n")
                        f_log.flush()



    except asyncio.TimeoutError:
        try:
            raw, resp = await retry_with_longer_timeout(
                session,
                url,
                ssl=False,
                allow_redirects=allow_redirects
            )
            html = raw.decode(errors="ignore")
            html_lower = html.lower()

            for val in values:
                val_lower = val.lower()
                for match in re.finditer(re.escape(val_lower), html_lower):
                    start = max(0, match.start() - b_chars)
                    end = min(len(html), match.end() + a_chars)
                    snippet = html[start:end].replace('\n', ' ').replace('\r', '')
                    async with log_lock:
                        f_log.write(f"{url} -> {val}\nContext: {snippet}\n\n")
                        f_log.flush()

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


async def main(file, values, use_ua, use_burp, custom_headers, no_follow, a_chars, b_chars):
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
        with open(log_file, "a") as f_log:
            tasks = [
                asyncio.create_task(
                    fetch(session, url, values, f_log, log_lock, counter, total, allow_redirects, a_chars, b_chars)
                )
                for url in urls
            ]
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
    parser.add_argument("-nf", "--no-follow", action="store_true", help="Do NOT follow redirects (don't follow open redirects)")

    args = parser.parse_args()

    if not args.value and not args.E:
        parser.error("You must provide either a value or -E with multiple values.")

    value_list = args.E.split("|") if args.E else [args.value]

    try:
        print("Looking for 🔎️ [" + ", ".join(value_list) + "] values")
        asyncio.run(main(args.file, value_list, args.ua_chrome, args.burp, args.H, args.no_follow, args.A, args.B))
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user.")
