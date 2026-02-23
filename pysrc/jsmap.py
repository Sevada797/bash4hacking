#!/usr/bin/env python3

import re
import argparse
import asyncio
import aiohttp
from urllib.parse import urljoin

# =========================
# Regexes (CORE)
# =========================

SCRIPT_ABS = re.compile(
    r"<script[^>]+src=(\"|')(?P<url>(https?:)?//[^\"'>]+\.js)",
    re.IGNORECASE
)

SCRIPT_REL = re.compile(
    r"<script[^>]+src=(\"|')(?P<url>/[^\"'>]+\.js)",
    re.IGNORECASE
)

# :(( no \$ , we will miss, e.g. `some/path/${configURL}`

PATH = r"/(?!/)[a-zA-Z0-9_:\{\}\$\./\-]+(\?[a-zA-Z_\-]+(=([a-zA-Z0-9_%\-]+)?)?(&[a-zA-Z_\-]+=([a-zA-Z0-9_%\-]+)?)*|)"

PATH_REGEXES = [
    re.compile(rf"'{PATH}'"),
    re.compile(rf'"{PATH}"'),
    re.compile(rf"`{PATH}`"),
]

# =========================
# Async helpers
# =========================

async def fetch(session, url):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
            if r.status == 200:
                return await r.text()
    except Exception:
        pass
    return None


def extract_js(origin, html):
    js_urls = set()

    for m in SCRIPT_ABS.finditer(html):
        url = m.group("url")
        if url.startswith("//"):
            url = "https:" + url
        js_urls.add(url)

    for m in SCRIPT_REL.finditer(html):
        js_urls.add(urljoin(origin, m.group("url")))

    return js_urls


def extract_paths(js_body):
    paths = []
    for rx in PATH_REGEXES:
        for m in rx.finditer(js_body):
            path = m.group(0)[1:-1]
            if path not in ("/", ""):
                paths.append(path)
    return paths


# =========================
# Main runner
# =========================

async def run(targets, headers):
    connector = aiohttp.TCPConnector(ssl=False, limit=50)
    timeout = aiohttp.ClientTimeout(total=20)

    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        headers=headers
    ) as session:

        # STAGE 1: Fetch all target HTMLs in parallel
        print("[*] Stage 1: Fetching all target HTMLs...")
        html_map = {}
        
        async def fetch_and_store(origin):
            html = await fetch(session, origin)
            if html:
                html_map[origin] = html
        
        await asyncio.gather(*[
            fetch_and_store(target.rstrip("/") + "/")
            for target in targets
        ])
        
        print(f"[+] Fetched {len(html_map)} HTMLs")

        # STAGE 2: Extract JS URLs from all HTMLs (in-memory regex)
        print("[*] Stage 2: Extracting JS URLs...")
        js_map = {}  # js_url -> origin
        
        for origin, html in html_map.items():
            js_urls = extract_js(origin, html)
            for js_url in js_urls:
                js_map[js_url] = origin
        
        print(f"[+] Found {len(js_map)} JS URLs")

        # STAGE 3: Fetch all JS files in parallel
        print("[*] Stage 3: Fetching all JS files...")
        js_bodies = {}
        
        async def fetch_js_and_store(js_url):
            body = await fetch(session, js_url)
            if body:
                js_bodies[js_url] = body
        
        await asyncio.gather(*[
            fetch_js_and_store(js_url)
            for js_url in js_map.keys()
        ])
        
        print(f"[+] Fetched {len(js_bodies)} JS files")

        # STAGE 4: Extract paths and map to origins (in-memory regex)
        print("[*] Stage 4: Extracting paths from JS...")
        results = []
        seen = set()
        
        for js_url, body in js_bodies.items():
            origin = js_map[js_url]
            paths = extract_paths(body)
            
            for path in paths:
                full = urljoin(origin, path)
                if full not in seen:
                    seen.add(full)
                    line = f"{js_url} -> {full}"
                    print(line)
                    results.append(line)
        
        print(f"[+] Found {len(results)} unique paths")
        
        return results


# =========================
# CLI
# =========================

def parse_args():
    p = argparse.ArgumentParser(
        description="Async JS path miner (URL or file of URLs)"
    )
    p.add_argument(
        "target",
        help="Single URL or file containing URLs"
    )
    p.add_argument(
        "-H",
        action="append",
        default=[],
        help="Custom header (repeatable)"
    )
    return p.parse_args()


def parse_headers(header_list):
    headers = {}
    headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/113.0.0.0"
    for h in header_list:
        if ":" in h:
            k, v = h.split(":", 1)
            headers[k.strip()] = v.strip()
    return headers


def load_targets(target):
    if target.startswith("http"):
        return [target]

    with open(target, "r") as f:
        return [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        ]


def main():
    args = parse_args()
    headers = parse_headers(args.H)
    targets = load_targets(args.target)

    try:
        results = asyncio.run(run(targets, headers))
        with open("jsmap.txt", "w") as f:
            f.write("\n".join(results))
        print(f"[+] Results written to jsmap.txt")
    except KeyboardInterrupt:
        print("\nInterrupted.")


if __name__ == "__main__":
    main()
