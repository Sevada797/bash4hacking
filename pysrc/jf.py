#!/usr/bin/env python3

import re
import os
import argparse
import asyncio
import aiohttp
import aiofiles
from urllib.parse import urljoin, urlparse

# =========================
# Regexes for JS discovery
# =========================

SCRIPT_INLINE = re.compile(
    r"<script\b(?![^>]*\bsrc\b)[^>]*>(?P<body>[\s\S]*?)</script\s*>",
    re.IGNORECASE
)

SCRIPT_ABS = re.compile(
    r"<script[^>]+src=(\"|')(?P<url>(https?:)?//[^\"'>]+\.js)",
    re.IGNORECASE
)

SCRIPT_REL = re.compile(
    r"<script[^>]+src=(\"|')(?P<url>/[^\"'>]+\.js)",
    re.IGNORECASE
)

SCRIPT_REL2 = re.compile(
    r"<script[^>]+src=(\"|')(?P<url>[^/\"'>][^\"'>]+\.js)",
    re.IGNORECASE
)


# =========================
# Fetch helpers
# =========================

async def fetch(session, url):
    print(f"[JF] Requesting: {url}")
    try:
        async with session.get(url, ssl=False) as r:
            if r.status == 200:
                return await r.text(errors="ignore")
    except Exception:
        pass
    return None


async def extract_js(origin, html):
    js_urls = set()

    for m in SCRIPT_REL2.finditer(html):
        js_urls.add(urljoin(origin, m.group("url")))

    for m in SCRIPT_ABS.finditer(html):
        u = m.group("url")
        if u.startswith("//"):
            u = "https:" + u
        js_urls.add(u)

    for m in SCRIPT_REL.finditer(html):
        js_urls.add(urljoin(origin, m.group("url")))

    return js_urls


# =========================
# Core logic
# =========================

async def scan_inline(page_url, html, patterns, f_log):
    for m in SCRIPT_INLINE.finditer(html):
        body = m.group("body")
        if not body.strip():
            continue

        for pattern in patterns:
            for match in re.finditer(pattern, body, re.DOTALL):
                line = (
                    f"[JF] Pattern hit (INLINE)\n"
                    f"Pattern: {pattern}\n"
                    f"Match: {match.group(0)}\n"
                    f"Page: {page_url}\n"
                    f"JS: INLINE <script>\n"
                )
                print(line)
                await f_log.write(line + "\n")
                await f_log.flush()


async def scan_js(page_url, js_url, session, patterns, seen_js, f_log):
    if js_url in seen_js:
        return
    seen_js.add(js_url)

    body = await fetch(session, js_url)
    if not body:
        return

    for pattern in patterns:
        for match in re.finditer(pattern, body, re.DOTALL):
            line = (
                f"[JF] Pattern hit\n"
                f"Pattern: {pattern}\n"
                f"Match: {match.group(0)}\n"
                f"Page: {page_url}\n"
                f"JS: {js_url}\n"
            )
            print(line)
            await f_log.write(line + "\n")
            await f_log.flush()


async def run(targets, patterns, headers):
    log_path = "jf/log.txt"
    
    connector = aiohttp.TCPConnector(limit=100, ssl=False)
    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(
        headers=headers,
        connector=connector,
        timeout=timeout
    ) as session:

        async with aiofiles.open(log_path, "a") as f_log:
            seen_js = set()

            # Fetch all target pages in parallel
            page_tasks = [
                fetch(session, target.rstrip("/"))
                for target in targets
            ]
            pages = await asyncio.gather(*page_tasks)

            # Process all pages + extract all JS URLs
            all_js_tasks = []
            for target, html in zip(targets, pages):
                if not html:
                    continue

                page_url = target
                parsed = urlparse(target)
                origin = f"{parsed.scheme}://{parsed.netloc}/"

                #origin = target.rstrip("/") + "/"
                #parsed = urlparse(target)
                #origin = f"{parsed.scheme}://{parsed.netloc}/"

                # origin = target.rsplit("/", 1)[0] + "/" //Buggy

                # inline JS
                await scan_inline(page_url, html, patterns, f_log)

                # external JS
                js_urls = await extract_js(origin, html)
                
                for js_url in js_urls:
                    all_js_tasks.append(
                        scan_js(page_url, js_url, session, patterns, seen_js, f_log)
                    )

            # Blast all JS requests at once
            if all_js_tasks:
                await asyncio.gather(*all_js_tasks)


# =========================
# CLI
# =========================



def parse_headers(header_list):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Accept": "*/*"
    }
    for h in header_list:
        if ":" in h:
            k, v = h.split(":", 1)
            headers[k.strip()] = v.strip()
    return headers


async def load_targets(t):
    """Non-blocking target loader"""
    if t.startswith("http"):
        return [t]

    async with aiofiles.open(t, "r") as f:
        content = await f.read()
        return [
            line.strip()
            for line in content.split("\n")
            if line.strip() and not line.startswith("#")
        ]


def parse_args():
    p = argparse.ArgumentParser(
        description="jf — JS pattern finder with back-mapping to origin pages"
    )
    p.add_argument("target", help="URL or file with URLs")
    p.add_argument("pattern", help="Regex pattern or file with patterns")
    p.add_argument("-H", action="append", default=[], help="Custom header (repeatable)")
    return p.parse_args()


async def load_pattern(pattern_input):
    """Load pattern from file or use direct input"""
    # Expand ~ to home directory
    expanded_path = os.path.expanduser(pattern_input)
    
    # Check if it's a file
    if os.path.isfile(expanded_path):
        async with aiofiles.open(expanded_path, "r") as f:
            content = await f.read()
            # If file has multiple lines, combine them (remove comments/whitespace)
            patterns = [
                line.strip()
                for line in content.split("\n")
                if line.strip() and not line.startswith("#")
            ]
            return patterns if patterns else [content.strip()]
    
    # Otherwise treat as direct regex input
    return [pattern_input]
    

async def main():
    args = parse_args()
    targets = await load_targets(args.target)
    patterns = await load_pattern(args.pattern)
    headers = parse_headers(args.H)
    os.makedirs("jf", exist_ok=True)
    log_path = "jf/log.txt"
    # del old logs
    async with aiofiles.open(log_path, "w") as f:
        await f.write("")
    try:
        await run(targets, patterns, headers)
    except KeyboardInterrupt:
        print("\n[JF] Interrupted")

# Later fix, like regex in loop, why fetch all again ? 

if __name__ == "__main__": asyncio.run(main())
