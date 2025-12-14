#!/usr/bin/env python3
import asyncio
import aiohttp
import re
import sys
from urllib.parse import urljoin
from bs4 import BeautifulSoup

PAYLOAD = "mySafeStr'NoWayThisCouldBeInHTML_1<NoWayThisCouldBeInHTML_2\"mySafeStr"
CONCURRENCY = 10
BATCH_SLEEP = 8
RESULT_FILE = "formxss_finds.txt"

sem = asyncio.Semaphore(CONCURRENCY)

HEADERS = {
    "User-Agent": "chrome",
}

# ---------------- helpers ----------------

def extract_names(html):
    names = set()
    # name="..." and name='...'
    names |= set(re.findall(r'name=["\']([^"\']+)["\']', html, re.I))
    # name=xxx
    names |= set(re.findall(r'name=([a-zA-Z0-9_]+)', html))

    clean = set()
    for n in names:
        n = n.split('=')[0]
        if re.fullmatch(r'[a-zA-Z0-9_]+', n):
            clean.add(n)
    return sorted(clean)

async def fetch_html(session, url):
    async with sem:
        async with session.get(url, headers=HEADERS, ssl=False, timeout=15) as r:
            return await r.text()

# ---------------- discovery ----------------

async def fetch_forms(session, url):
    try:
        html = await fetch_html(session, url)
    except Exception as e:
        print(f"[-] Fetch failed: {url} ({e})")
        return []

    soup = BeautifulSoup(html, "html.parser")
    forms = soup.find_all("form")
    if not forms:
        print(f"[-] No forms found: {url}")
        return []

    names = extract_names(html)
    if not names:
        print(f"[-] Form(s) found but no input names: {url}")
        return []

    payload = "&".join(f"{n}={PAYLOAD}" for n in names)
    targets = []

    for f in forms:
        action = f.get("action") or url
        full_action = urljoin(url, action)
        
        print(f"[+] Form discovered: {full_action}")
        print(f"    inputs={names}")
        # ALWAYS test BOTH methods
        targets.append({
            "url": full_action,
            "methods": ["get", "post"],
            "payload": payload,
        })

    return targets

# ---------------- replay ----------------

async def replay_one(session, url, method, payload):
    try:
        if method == "get":
            if "?" in url:
                full_url = f"{url}&{payload}"
            else:
                full_url = f"{url}?{payload}"

            async with session.get(full_url, headers=HEADERS, ssl=False, timeout=15) as r:
                html = await r.text()
        else:
            async with session.post(
                url,
                data=payload,
                headers={
                    **HEADERS,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                ssl=False,
                timeout=15,
            ) as r:
                html = await r.text()
    except Exception as e:
        print(f"[-] Fetch failed: {full_url} ({e})")
        return

    risk = 0
    if "mySafeStr'NoWayThisCouldBeInHTML_1" in html:
        risk += 1
    if "NoWayThisCouldBeInHTML_1<NoWayThisCouldBeInHTML_2" in html:
        risk += 1
    if "NoWayThisCouldBeInHTML_2\"mySafeStr" in html:
        risk += 1
    if "`mySafeStr" in html or "mySafeStr`" in html:
        risk = 900

    if risk >= 1:
        line = f"Risk {risk} | {method.upper()} | {url}"
        print(f"[!] {line}")
        with open(RESULT_FILE, "a") as f:
            f.write(line + "\n")

async def replay(session, item):
    for m in item["methods"]:
        await replay_one(session, item["url"], m, item["payload"])

# ---------------- main ----------------

async def main(urls):
    async with aiohttp.ClientSession() as session:
        pending = []

        for url in urls:
            try:
                pending.extend(await fetch_forms(session, url))
            except Exception:
                pass

        for i in range(0, len(pending), CONCURRENCY):
            batch = pending[i:i + CONCURRENCY]
            await asyncio.gather(*(replay(session, x) for x in batch))
            await asyncio.sleep(BATCH_SLEEP)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 formxss.py urls.txt")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        urls = [x.strip() for x in f if x.strip()]

    asyncio.run(main(urls))
