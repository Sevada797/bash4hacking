#!/usr/bin/env python3
"""
digger.py
Usage:
  python3 digger.py urls_file

Reads URLs from "urls_file" (one URL per line, lines starting with '#' are ignored),
fetches them concurrently, and writes response headers to 'hdump'.
After completion prints: "check hdump file for results"
"""
import sys
import asyncio
import aiohttp
from aiohttp import ClientTimeout
from pathlib import Path
from typing import List

# tweak concurrency if you want
CONCURRENCY = 20
OUTPUT_FILE = "hdump"

# Chrome-like UA
USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")

async def fetch(session: aiohttp.ClientSession, url: str, sem: asyncio.Semaphore):
    async with sem:
        record = {"url": url}
        try:
            async with session.get(url, allow_redirects=True) as resp:
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

async def run(urls: List[str]):
    timeout = ClientTimeout(total=30)
    sem = asyncio.Semaphore(CONCURRENCY)
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    connector = aiohttp.TCPConnector(limit_per_host=CONCURRENCY, ssl=False)
    async with aiohttp.ClientSession(timeout=timeout, headers=headers, connector=connector) as session:
        tasks = [fetch(session, u, sem) for u in urls]
        results = await asyncio.gather(*tasks, return_exceptions=False)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        for r in results:
            fh.write(format_record(r))

    print("check hdump file for results")

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
    print("Usage: python3 digger.py urls_file")
    print("  urls_file: text file with one URL per line. Lines starting with '#' are ignored.")
    print("Example: python3 digger.py targets.txt")
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
