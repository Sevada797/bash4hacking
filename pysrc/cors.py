#!/usr/bin/env python3
"""
cors.py
Usage:
  python3 cors.py urls_file

Sends OPTIONS requests with Origin: null and logs only responses that include
Access-Control-Allow-Origin or Access-Control-Allow-Credentials (case-insensitive).
Output file: hdump
"""
import sys
import asyncio
import aiohttp
from aiohttp import ClientTimeout
from pathlib import Path
from typing import List

CONCURRENCY = 20
OUTPUT_FILE = "cors_finds"
OUTPUT_FILE2 = "cors_finds_fatal"
# Chrome-like UA
USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")

async def fetch(session, url, sem):
    async with sem:
        record = {"url": url}
        try:
            # enforce 15s per request
            resp = await asyncio.wait_for(session.options(url, allow_redirects=True), timeout=15)
            record["status"] = resp.status
            record["headers"] = dict(resp.headers)
        except Exception as e:
            record["error"] = str(e)
        return record

def format_record(r: dict) -> str:
    parts = [f"=== URL: {r.get('url', '<no-url>')} ==="]
    if "error" in r:
        parts.append(f"ERROR: {r['error']}")
    else:
        parts.append(f"Status: {r.get('status')}")
        headers = r.get("headers", {})
        if headers:
            for k, v in headers.items():
                parts.append(f"{k}: {v}")
        else:
            parts.append("(no headers)")
    parts.append("")  # blank line
    return "\n".join(parts)

def headers_contain_interesting(h: dict) -> bool:
    # check case-insensitively for ACAO or ACAC presence
    if not h:
        return False
    keys = {k.lower() for k in h.keys()}
    return ("access-control-allow-origin" in keys) or ("access-control-allow-credentials" in keys)

def headers_contain_fatal(h: dict) -> bool:
    # check case-insensitively for ACAO and ACAC presence
    if not h:
        return False
    keys = {k.lower() for k in h.keys()}
    return ("access-control-allow-origin" in keys) and ("access-control-allow-credentials" in keys)


async def run(urls: List[str]):
    timeout = ClientTimeout(total=30)
    sem = asyncio.Semaphore(CONCURRENCY)
    # send Origin: null and simple Accept + UA
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*", "Origin": "null"}
    connector = aiohttp.TCPConnector(limit_per_host=CONCURRENCY, ssl=False)
    async with aiohttp.ClientSession(timeout=timeout, headers=headers, connector=connector) as session:
        tasks = [fetch(session, u, sem) for u in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)


    # write interesting records (those with ACAO||ACAC)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        matched = 0
        for r in results:
            headers = r.get("headers", {}) if isinstance(r, dict) else {}
            if "error" in r:
                # log errors as well (optional) — keep original behavior? we'll skip errors by default
                # if you want to keep errors, uncomment the next two lines:
                # fh.write(format_record(r))
                # continue
                continue
            if headers_contain_interesting(headers):
                fh.write(format_record(r))
                matched += 1
    # write fatal records (those with ACAO+ACAC)
    with open(OUTPUT_FILE2, "w", encoding="utf-8") as fh:
        matched2 = 0
        for r in results:
            headers = r.get("headers", {}) if isinstance(r, dict) else {}
            if "error" in r:
                continue
            if headers_contain_fatal(headers):
                fh.write(format_record(r))
                matched2 += 1

    print(f"done — wrote {matched} matching entries to {OUTPUT_FILE}")
    print(f"done — wrote {matched2} matching entries to {OUTPUT_FILE2}")

def normalize_url(u: str) -> str:
    u = u.strip()
    if not u:
        return ""
    if u.startswith("#"):
        return ""  # comment
    if u.startswith("http://") or u.startswith("https://"):
        return u
    # default to http if scheme missing
    return "http://" + u

def read_urls_from_file(path: str) -> List[str]:
    p = Path(path)
    if not p.is_file():
        print(f"Error: file not found: {path}")
        sys.exit(1)
    lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    urls = []
    for line in lines:
        n = normalize_url(line)
        if n:
            urls.append(n)
    return urls

def usage():
    print("Usage: python3 cors.py urls_file")
    print("  urls_file: text file with one URL per line. Lines starting with '#' are ignored.")
    print("Example: python3 cors.py targets.txt")
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        usage()

    urls_file = sys.argv[1]
    urls = read_urls_from_file(urls_file)
    if not urls:
        print("No URLs found in file (or file only contains comments/blank lines). Exiting.")
        sys.exit(1)

    try:
        asyncio.run(run(urls))
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
