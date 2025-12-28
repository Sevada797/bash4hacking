#!/usr/bin/env python3
import asyncio
import aiohttp
import re
import sys
from urllib.parse import urljoin

PAYLOAD = "mySafeStr'NoWayThisCouldBeInHTML_1<NoWayThisCouldBeInHTML_2\"mySafeStr"
CONCURRENCY = 10
RESULT_FILE = "formxss_finds.txt"

HEADERS = {
    "User-Agent": "chrome",
}

# ---------------- helpers ----------------

def extract_names(html):
    names = set()
    names |= set(re.findall(r'name=["\']([^"\']+)["\']', html, re.I))
    names |= set(re.findall(r'name=([a-zA-Z0-9_]+)', html))

    clean = set()
    for n in names:
        n = n.split('=')[0]
        if re.fullmatch(r'[a-zA-Z0-9_]+', n):
            clean.add(n)
    return sorted(clean)

def extract_forms(html):
    """
    Returns list of (action, inner_html)
    """
    forms = []
    for m in re.finditer(
        r'<form\b([^>]*)>(.*?)</form>',
        html,
        re.I | re.S
    ):
        attrs = m.group(1)
        body = m.group(2)

        action_m = re.search(r'action=(?:"([^"]+)"|\'([^\']+)\'|([^\s>]+))', attrs, re.I)
        action = action_m.group(1) if action_m else None

        forms.append((action, body))

    return forms

# ---------------- network ----------------

async def fetch_html(session, url, sem):
    async with sem:
        print(f"[→] FETCH {url}")
        async with session.get(
            url,
            headers=HEADERS,
            ssl=False,
            timeout=1
        ) as r:
            return await r.text(errors="ignore")

# ---------------- discovery ----------------

async def fetch_forms(session, url, sem):
    async with sem:
        try:
            html = await fetch_html(session, url, sem)
        except Exception as e:
            print(f"[-] Fetch failed: {url} ({e})")
            return []

        # ultra-fast form gate
        if "</form>" not in html.lower():
            print(f"[-] No forms found: {url}")
            return []
    
        forms = extract_forms(html)
        if not forms:
            print(f"[-] Form tag seen but regex failed: {url}")
            return []
    
        names = extract_names(html)
        if not names:
            print(f"[-] Form(s) found but no input names: {url}")
            return []
    
        payload = "&".join(f"{n}={PAYLOAD}" for n in names)
        targets = []
    
        for action, _ in forms:
            full_action = urljoin(url, action) if action else url
    
            print(f"[+] Form discovered: {full_action}")
            print(f"    inputs={names}")
    
            targets.append({
                "url": full_action,
#               "methods": ["get", "post"],  ** Default use both, for edge case hunting **
                "payload": payload,
            })
    
        return targets

async def replay_get(session, url, payload, sem):
    async with sem:
        full_url = f"{url}&{payload}" if "?" in url else f"{url}?{payload}"; endpoint=full_url
        print(f"[→] GET  {full_url}")
        try:
            async with session.get(full_url, headers=HEADERS, ssl=False) as r:
                html = await r.text(errors="ignore")
                return {"html":html,"endpoint":endpoint}
        except Exception as e:
            print(f"[-] GET failed: {url} ({e})")
            return None

async def replay_post(session, url, payload, sem):
    async with sem:
        print(f"[→] POST {url}")
        payload=payload.replace("'", "%27")
        endpoint = f"{url} --data '{payload}' -X POST" # this here for logging
        payload_dict = dict(x.split("=", 1) for x in payload.split("&")) # this for req
        try:
            async with session.post(
                url,
                data=payload_dict,
                headers={**HEADERS, "Content-Type":"application/x-www-form-urlencoded"},
                ssl=False
            ) as r:
                html = await r.text(errors="ignore")
                return {"html":html,"endpoint":endpoint}
        except Exception as e:
            print(f"[-] POST failed: {url} ({e})")
            return None

def check_risk(html, method, log_endpoint):
    if not html:
        return
    risk = 0
    if "mySafeStr'NoWayThisCouldBeInHTML_1" in html:
        risk += 1
    if "NoWayThisCouldBeInHTML_1<NoWayThisCouldBeInHTML_2" in html:
        risk += 1
    if "NoWayThisCouldBeInHTML_2\"mySafeStr" in html:
        risk += 1
    if "`mySafeStr" in html or "mySafeStr`" in html or "mySafeStr>" in html:
        risk = 900

    if risk >= 1:
        line = f"Risk {risk} | {method.upper()} | {log_endpoint}"
        print(f"[!] {line}")
        with open(RESULT_FILE, "a") as f:
            f.write(line + "\n")

async def replay_once(session, item, sem):
    # fire GET
    resp_get = await replay_get(session, item["url"], item["payload"], sem)
    log_endpoint = resp_get["endpoint"]
    check_risk(resp_get["html"], "get", log_endpoint)

    # fire POST
    resp_post = await replay_post(session, item["url"], item["payload"], sem)
    log_endpoint = resp_post["endpoint"]
    check_risk(resp_post["html"], "post", log_endpoint)


async def replay(session, item, sem):
    await replay_once(session, item, sem)

# ---------------- main ----------------

async def main(urls):
    sem = asyncio.Semaphore(CONCURRENCY)
    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(
        headers=HEADERS,
        timeout=timeout
    ) as session:

        # ==========================================================
        # PHASE 1 — DISCOVERY (fire all, wait all)
        # ==========================================================

        print(f"[+] Starting discovery for {len(urls)} URLs")

        discovery_tasks = [
            asyncio.create_task(fetch_forms(session, u, sem))
            for u in urls
        ]

        all_targets = []

        # handle results as they complete (NOT gather)
        for task in asyncio.as_completed(discovery_tasks):
            try:
                targets = await task
                if targets:
                    all_targets.extend(targets)
            except Exception as e:
                print(f"[-] Discovery task crashed: {e}")

        print(f"[+] Discovery finished")
        print(f"[+] Total form targets queued: {len(all_targets)}")

        # hard phase barrier
        if not all_targets:
            return

        # ==========================================================
        # PHASE 2 — REPLAY (fire all, wait all)
        # ==========================================================

        print(f"[+] Starting replay phase")

        replay_tasks = [
            asyncio.create_task(replay(session, item, sem))
            for item in all_targets
        ]

        for task in asyncio.as_completed(replay_tasks):
            try:
                await task
            except Exception as e:
                print(f"[-] Replay task crashed: {e}")

        print("[+] Replay finished")


# ---------------- entry ----------------

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: formxss <urls_file>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        urls = [x.strip() for x in f if x.strip()]

    asyncio.run(main(urls))
