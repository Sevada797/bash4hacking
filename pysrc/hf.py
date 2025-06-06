import aiohttp
import asyncio
import argparse
import os
import re

from aiohttp.client_exceptions import (
    ClientConnectorError,
    ClientProxyConnectionError,
    ClientOSError,
    ClientResponseError,
    ServerTimeoutError,
    ClientSSLError
)


async def fetch(session, url, values, log_file, counter, total):
    try:
        async with session.get(url, timeout=5, ssl=False) as resp:
            content_type = resp.headers.get("Content-Type", "").lower()

            allowed_types = ["text/html", "application/json", "application/javascript", "text/plain"]
            if not any(ct in content_type for ct in allowed_types):
                return  # skip non-text responses

            try:
                html = await resp.text()
            except UnicodeDecodeError:
                try:
                    html = (await resp.read()).decode('latin-1')
                except Exception:
                    html = ""

            for val in values:
                if val.lower() in html.lower():
                    async with asyncio.Lock():
                        with open(log_file, "a") as f:
                            f.write(url + " -> " + val + "\n")

    except (
        ClientConnectorError,
        ClientProxyConnectionError,
        ClientOSError,
        ClientResponseError,
        ServerTimeoutError,
        asyncio.TimeoutError,
        ClientSSLError,
        aiohttp.InvalidURL
    ):
        pass
    except Exception as e:
        print(f"\n[ERROR] Unexpected error for {url}: {e}")
    finally:
        counter[0] += 1
        print(f"\r{counter[0]} requests done out of {total}", end="", flush=True)


async def main(file, values, use_ua, use_burp, custom_headers):
    if not os.path.exists(file):
        print(f"[ERROR] File {file} not found.")
        return

    with open(file) as f:
        urls = [line.strip() for line in f if line.strip()]

    if not urls or not re.match(r"^https?://", urls[0]):
        print(f"\n[ERROR] URLs should start with http(s). Run:")
        print(f"  sed -i 's|^|https://|' {file}")
        print(f"To revert back:")
        print(f"  sed -i 's|^https://||' {file}")
        return

    os.makedirs("hf", exist_ok=True)
    log_file = "hf/log.txt"
    if os.path.exists(log_file):
        os.remove(log_file)

    headers = {}
    if use_ua:
        headers["User-Agent"] = "chrome"

    if custom_headers:
        for h in custom_headers:
            if ":" in h:
                k, v = h.split(":", 1)
                headers[k.strip()] = v.strip()

    proxy = "http://127.0.0.1:8080" if use_burp else None

    connector = aiohttp.TCPConnector(limit=100)
    timeout = aiohttp.ClientTimeout(total=6)

    counter = [0]
    total = len(urls)
    sem = asyncio.Semaphore(100)

    async with aiohttp.ClientSession(headers=headers, connector=connector, timeout=timeout) as session:
        session._default_proxy = proxy

        async def sem_fetch(url):
            async with sem:
                await fetch(session, url, values, log_file, counter, total)

        tasks = [sem_fetch(url) for url in urls]
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

    args = parser.parse_args()

    if not args.value and not args.E:
        parser.error("You must provide either a value or -E with multiple values.")

    value_list = args.E.split("|") if args.E else [args.value]

    try:
        asyncio.run(main(args.file, value_list, args.ua_chrome, args.burp, args.H))
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user.")
