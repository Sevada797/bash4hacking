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

PATH = r"/(?!/)[a-zA-Z0-9_\./\-]+(\?[a-zA-Z_\-]+(=([a-zA-Z0-9_%\-]+)?)?(&[a-zA-Z_\-]+=([a-zA-Z0-9_%\-]+)?)*|)"

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


async def extract_js(origin, html):
    js_urls = set()

    for m in SCRIPT_ABS.finditer(html):
        url = m.group("url")
        if url.startswith("//"):
            url = "https:" + url
        js_urls.add(url)

    for m in SCRIPT_REL.finditer(html):
        js_urls.add(urljoin(origin, m.group("url")))

    return js_urls


async def scan_js(origin, session, js_url, seen, outfile):
    print(f"Visiting: {js_url}")

    body = await fetch(session, js_url)
    if not body:
        return

    for rx in PATH_REGEXES:
        for m in rx.finditer(body):
            path = m.group(0)[1:-1]

            if path in ("/", ""):
                continue

            full = urljoin(origin, path)

            if full not in seen:
                seen.add(full)
                line = f"{js_url} -> {full}"
                print(line)
                outfile.write(line + "\n")


# =========================
# Main runner
# =========================

async def run(targets, headers):
    connector = aiohttp.TCPConnector(ssl=False, limit=25)
    timeout = aiohttp.ClientTimeout(total=20)

    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        headers=headers
    ) as session:

        seen = set()

        with open("jsmap.txt", "w") as outfile:
            for target in targets:
                origin = target.rstrip("/") + "/"

                html = await fetch(session, origin)
                if not html:
                    continue

                js_urls = await extract_js(origin, html)

                tasks = [
                    scan_js(origin, session, js, seen, outfile)
                    for js in js_urls
                ]

                await asyncio.gather(*tasks)


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
        asyncio.run(run(targets, headers))
    except KeyboardInterrupt:
        print("\nInterrupted.")


if __name__ == "__main__":
    main()
