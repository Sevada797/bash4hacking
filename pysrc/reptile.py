from playwright.sync_api import sync_playwright
import argparse
import os
import re

def fetch_and_scan(page, url, values, f_log, a_chars, b_chars):
    try:
        page.goto(url, timeout=5000, wait_until="networkidle")
        html = page.content().lower()

        for val in values:
            val_lower = val.lower()
            for match in re.finditer(re.escape(val_lower), html):
                start = max(0, match.start() - b_chars)
                end = min(len(html), match.end() + a_chars)
                snippet = html[start:end].replace('\n', ' ').replace('\r', '')
                f_log.write(f"{url} -> {val}\nContext: {snippet}\n\n")
                f_log.flush()
    except Exception as e:
        print(f"[ERROR] {url} failed: {e}")

def main(file, values, use_ua, use_burp, custom_headers, a_chars, b_chars):
    if not os.path.exists(file):
        print(f"[ERROR] File {file} not found.")
        return

    with open(file) as f:
        urls = [line.strip() for line in f if line.strip()]

    if not urls or not re.match(r"^https?://", urls[0]):
        print(f"\n[ERROR] URLs should start with http(s). Run:")
        print(f"  sed -i 's|^|https://|' {file}")
        return

    os.makedirs("reptile", exist_ok=True)
    log_file = "reptile/log.txt"
    if os.path.exists(log_file):
        os.remove(log_file)

    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/113.0.0.0" if use_ua else None
    proxy = "http://127.0.0.1:8080" if use_burp else None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        context_args = {}
        if user_agent:
            context_args["user_agent"] = user_agent
        if proxy:
            context_args["proxy"] = {"server": proxy}
        if custom_headers:
            context_args["extra_http_headers"] = {
                k.strip(): v.strip()
                for h in custom_headers if ":" in h
                for k, v in [h.split(":", 1)]
            }

        context = browser.new_context(**context_args)
        page = context.new_page()

        with open(log_file, "a") as f_log:
            for i, url in enumerate(urls, 1):
                print(f"[{i}/{len(urls)}] {url}")
                fetch_and_scan(page, url, values, f_log, a_chars, b_chars)

        browser.close()

    print(f"\n[INFO]: Check {log_file} for matches")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Playwright Reptile Reflector")
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

    print("Looking for 🔍 [" + ", ".join(value_list) + "]")
    main(args.file, value_list, args.ua_chrome, args.burp, args.H, args.A, args.B)
