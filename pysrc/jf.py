#!/usr/bin/env python3

import re
import os
import json
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

SOURCE_MAP_URL = re.compile(
    r"//#\s*sourceMappingURL=([^\s\n]+\.map)",
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


async def fetch_with_timeout(session, url, timeout_sec):
    """Fetch with custom timeout"""
    print(f"[JF] Requesting: {url}")
    try:
        timeout = aiohttp.ClientTimeout(total=timeout_sec)
        async with session.get(url, ssl=False, timeout=timeout) as r:
            if r.status == 200:
                return await r.text(errors="ignore")
    except Exception:
        pass
    return None


async def extract_js(target, origin, html):
    js_urls = set()

    for m in SCRIPT_REL2.finditer(html):
        base = target if target.endswith("/") else target + "/"
        print(f"[DBG] origin={origin} base={base} rel={m.group('url')}")
        js_urls.add(urljoin(base, m.group("url")))

    for m in SCRIPT_ABS.finditer(html):
        u = m.group("url")
        if u.startswith("//"):
            u = "https:" + u
        js_urls.add(u)

    for m in SCRIPT_REL.finditer(html):
        js_urls.add(urljoin(origin, m.group("url")))

    return js_urls


async def extract_source_map_url(js_url, js_body):
    """Extract sourceMappingURL from JS and resolve it"""
    m = SOURCE_MAP_URL.search(js_body)
    if m:
        map_url = m.group(1)
        if map_url.startswith("http"):
            print(f"[JF] Map detected (absolute): {map_url}")
            return map_url
        elif map_url.startswith("//"):
            parsed = urlparse(js_url)
            resolved = f"{parsed.scheme}:{map_url}"
            print(f"[JF] Map detected (protocol-relative): {resolved}")
            return resolved
        else:
            resolved = urljoin(js_url.rsplit("/", 1)[0] + "/", map_url)
            print(f"[JF] Map detected (relative): {resolved}")
            return resolved
    return None


async def extract_source_content(map_url, session):
    """Fetch .map file and extract sourceContent array"""
    print(f"[JF] Fetching sourcemap: {map_url}")
    body = await fetch_with_timeout(session, map_url, 300)
    if not body:
        print(f"[JF] Failed to fetch sourcemap: {map_url}")
        return None

    try:
        cleaned = body.replace("\\t", "").replace("\\n", "").replace("\\r", "")
        sourcemap = json.loads(cleaned)
        
        if "sourcesContent" in sourcemap and sourcemap["sourcesContent"]:
            content = "\n".join(src for src in sourcemap["sourcesContent"] if src)
            print(f"[JF] Extracted sourceContent from map ({len(content)} bytes)")
            return content
        else:
            print(f"[JF] No sourcesContent found in map")
    except Exception as e:
        print(f"[JF] Error parsing sourcemap: {e}")
    
    return None


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

    # Check for sourceMap URL
    map_url = await extract_source_map_url(js_url, body)
    
    if map_url and map_url not in seen_js:
        seen_js.add(map_url)
        source_content = await extract_source_content(map_url, session)
        
        if source_content:
            print(f"[JF] Scanning sourcemap patterns: {js_url} --> {map_url}")
            for pattern in patterns:
                for match in re.finditer(pattern, source_content, re.DOTALL):
                    line = (
                        f"[JF] Pattern hit (SOURCEMAP)\n"
                        f"Pattern: {pattern}\n"
                        f"Match: {match.group(0)}\n"
                        f"Page: {page_url}\n"
                        f"JS: {js_url} --> {map_url}\n"
                    )
                    print(line)
                    await f_log.write(line + "\n")
                    await f_log.flush()
            return
    else:
        if map_url:
            print(f"[JF] Sourcemap already seen: {map_url}")
        else:
            print(f"[JF] No sourcemap found, scanning raw JS: {js_url}")

    # Scan raw JS if no map or map failed
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
        timeout=timeout,
        trust_env=True
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
                js_urls = await extract_js(target, origin, html)
                
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
    # expand: if any -H value is a file, load lines from it; else use as-is
    raw = []
    for h in header_list:
        expanded = os.path.expanduser(h)
        if os.path.isfile(expanded):
            with open(expanded, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        raw.append(line)
        else:
            raw.append(h)
    for h in raw:
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
