import asyncio
import aiohttp
import os, re, json
from itertools import product
import urllib3, requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- User input ---

print("       Welcome back lieutenant       ")
print("⚠️ Note: All FUZZ/BUZZ/CUZZ/DUZZ will be replaced if present in URL headers & payload")
url = input("Target URL or URLs file: ").strip() # URL or URLs file
method = input("HTTP method (GET/POST, default POST): ").strip().upper() or "POST"

headers_input = input("Headers (JSON format, optional): ").strip()
if headers_input:
    headers = json.loads(headers_input)
else:
    headers = {}
headers['User-Agent'] = 'Mozilla/5.0 (Chrome)'

ct_input = input("Content-Type (press Enter for default urlencoded, or type your own): ").strip()
if not ct_input:
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
else:
    headers['Content-Type'] = ct_input

# ensure consistent compression + connection
headers.setdefault("Accept-Encoding", "gzip, deflate")
headers.setdefault("Connection", "close")

payload = input("Payload: ").strip()

# Time to reset results !!
open("br_finds.txt", "w").close()


# --- helper functions for stable header compare ---
DYN_HEADERS = {
    "date","set-cookie","etag","server","x-request-id",
    "content-length","vary","transfer-encoding",
    "connection","keep-alive","via","x-powered-by"
}

def filtered_header_keys(headers):
    """Return non-dynamic header keys"""
    try:
        keys = [k.lower() for k in headers.keys()]
    except:
        keys = [k.lower() for k, _ in headers.items()]
    return set(k for k in keys if k not in DYN_HEADERS)

def header_lines_count(headers):
    """Stable header count (non-dynamic only)."""
    return len(filtered_header_keys(headers))

def header_keys_diff(base, cur):
    b = filtered_header_keys(base)
    c = filtered_header_keys(cur)
    return sorted(list(c - b)), sorted(list(b - c))


# --- add wlist array ---
wlist = []

if os.path.isfile(url):
    with open(url) as uf:
        scan_target = uf.read()
else:
    scan_target = url

all_placeholders = re.findall(r"[FBCD]UZZ", scan_target)
all_placeholders += re.findall(r"[FBCD]UZZ", payload)
all_placeholders += re.findall(r"[FBCD]UZZ", json.dumps(headers))
placeholders = list(dict.fromkeys(all_placeholders))

for ph in placeholders:
    wlist.append(
        input(f"Please enter wordlist for {ph}: ")
        .replace('~/', os.path.expanduser("~") + '/')
    )


# --- ASYNC brutemain ---
async def brutemain(url, headers, payload, wlist, method, tracker,
            f1=None,f2=None,f3=None,f4=None, sem=None, session=None):
    current = {}
    if (f1 and f2 and f3 and f4):
        payload=payload.replace("FUZZ", f1).replace("BUZZ", f2).replace("CUZZ", f3).replace("DUZZ", f4)
        url=url.replace("FUZZ", f1).replace("BUZZ", f2).replace("CUZZ", f3).replace("DUZZ", f4)
        headers=json.loads(json.dumps(headers).replace("FUZZ", f1).replace("BUZZ", f2).replace("CUZZ", f3).replace("DUZZ", f4))
    elif (f1 and f2 and f3):
        payload=payload.replace("FUZZ", f1).replace("BUZZ", f2).replace("CUZZ", f3)
        url=url.replace("FUZZ", f1).replace("BUZZ", f2).replace("CUZZ", f3)
        headers=json.loads(json.dumps(headers).replace("FUZZ", f1).replace("BUZZ", f2).replace("CUZZ", f3))
    elif (f1 and f2):
        payload=payload.replace("FUZZ", f1).replace("BUZZ", f2)
        url=url.replace("FUZZ", f1).replace("BUZZ", f2)
        headers=json.loads(json.dumps(headers).replace("FUZZ", f1).replace("BUZZ", f2))
    elif (f1):
        payload=payload.replace("FUZZ", f1)
        url=url.replace("FUZZ", f1)
        headers=json.loads(json.dumps(headers).replace("FUZZ", f1))

    async with sem:
        try:
            if method=="POST":
                async with session.post(
                    url,
                    headers=headers,
                    data=payload,
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=15),
                    allow_redirects=False,
                    compress=False
                ) as r:
                    text = await r.text(errors="ignore")
                    status = r.status
                    resp_headers = r.headers
            elif method=="GET":
                async with session.get(
                    url,
                    headers=headers,
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=15),
                    allow_redirects=False,
                    compress=False
                ) as r:
                    text = await r.text(errors="ignore")
                    status = r.status
                    resp_headers = r.headers
        except (aiohttp.ClientError, asyncio.TimeoutError):
            print(f"[!] Skipped {url} due to disconnect/timeout")
            return ""

    print(f"[I]: Bruting, req sent ~ [{method}] {url} with payload {payload}\nHeaders: {str(headers)}")
    current["sc"] = status
    current["hlines"] = header_lines_count(resp_headers)
    current["_hkeys"] = sorted(list(filtered_header_keys(resp_headers)))
    current["rsize"] = len(text)
    current["words"] = len(text.split(' '))
    current["lines"] = len(text.split("\n"))

    for i in tracker:
        if (tracker[i]!="DYNAMIC"):
            if (tracker[i]!=current[i]):
                diffinfo = ""
                if i == "hlines":
                    added, removed = header_keys_diff(
                        dict.fromkeys(tracker.get("_hkeys", [])),
                        dict.fromkeys(current.get("_hkeys", []))
                    )
                    if added or removed:
                        diffinfo = f"Header keys added: {added}  removed: {removed}\n"
                with open('br_finds.txt', 'a') as f:
                    f.write(
                        f"Find for URL {url}\n"
                        f"Default req: sc={tracker['sc']},hlines={tracker['hlines']},rsize={tracker['rsize']},words={tracker['words']},lines={tracker['lines']}  "
                        f"VS sc={current['sc']},hlines={current['hlines']},rsize={current['rsize']},words={current['words']},lines={current['lines']}\n"
                        f"{diffinfo}"
                        f" ON STRING(s) f1={f1},f2={f2},f3={f3},f4={f4},\n\n"
                    )
                return ""


# --- ASYNC brute wrapper ---
async def brute(url, headers, payload, wlist, method, sem, session, batch_size=50000):
    tracker = {}

    # use a requests.Session for identical behaviour
    req_session = requests.Session()
    req_session.headers.update(headers)
    req_session.verify = False
    req_session.trust_env = False

    for i in range(1,4):
        try:
            if method == "GET":
                r = req_session.get(
                    url.replace("FUZZ", i*" A ").replace("BUZZ", i*" A ").replace("CUZZ", i*" A ").replace("DUZZ", i*" A "),
                    timeout=10, allow_redirects=False
                )
            if method == "POST":
                r = req_session.post(
                    url.replace("FUZZ", i*" A ").replace("BUZZ", i*" A ").replace("CUZZ", i*" A ").replace("DUZZ", i*" A "),
                    timeout=10, allow_redirects=False,
                    data=payload.replace("FUZZ", i*" A ").replace("BUZZ", i*" A ").replace("CUZZ", i*" A ").replace("DUZZ", i*" A ")
                )
        except:
            print(f"[!] Skipped {url} during staticism check")
            return

        if i==1:
            tracker["sc"] = r.status_code
            tracker["hlines"] = header_lines_count(r.headers)
            tracker["_hkeys"] = sorted(list(filtered_header_keys(r.headers)))
            tracker["rsize"] = len(r.text)
            tracker["words"] = len(r.text.split(' '))
            tracker["lines"] = len(r.text.split("\n"))
        else:
            if tracker["sc"] != r.status_code: tracker["sc"] = "DYNAMIC"
            if tracker["hlines"] != header_lines_count(r.headers): tracker["hlines"] = "DYNAMIC"
            if tracker["rsize"] != len(r.text): tracker["rsize"] = "DYNAMIC"
            if tracker["words"] != len(r.text.split(' ')): tracker["words"] = "DYNAMIC"
            if tracker["lines"] != len(r.text.split("\n")): tracker["lines"] = "DYNAMIC"
    
    print("Okay fam static settings detected so far:")
    print("Status code staticism:", tracker["sc"])
    print("Header lines staticism:", tracker["hlines"])
    print("Response size staticism:", tracker["rsize"])
    print("Words staticism:", tracker["words"])
    print("Lines staticism:", tracker["lines"])

    batch = []
    async def run_batch(batch):
        if batch:
            await asyncio.gather(*batch)
            batch.clear()

    # 4-wordlists
    try:
        with open(wlist[0]) as f1:
            for line1 in f1:
                w1 = line1.strip()
                with open(wlist[1]) as f2:
                    for line2 in f2:
                        w2 = line2.strip()
                        with open(wlist[2]) as f3:
                            for line3 in f3:
                                w3 = line3.strip()
                                with open(wlist[3]) as f4:
                                    for line4 in f4:
                                        w4 = line4.strip()
                                        batch.append(brutemain(url, headers, payload, wlist, method, tracker,
                                                               w1, w2, w3, w4, sem, session))
                                        if len(batch) >= batch_size:
                                            await run_batch(batch)
        await run_batch(batch)
        return
    except IndexError:
        pass

    # 3-wordlists
    try:
        with open(wlist[0]) as f1:
            for line1 in f1:
                w1 = line1.strip()
                with open(wlist[1]) as f2:
                    for line2 in f2:
                        w2 = line2.strip()
                        with open(wlist[2]) as f3:
                            for line3 in f3:
                                w3 = line3.strip()
                                batch.append(brutemain(url, headers, payload, wlist, method, tracker,
                                                       w1, w2, w3, None, sem, session))
                                if len(batch) >= batch_size:
                                    await run_batch(batch)
        await run_batch(batch)
        return
    except IndexError:
        pass

    # 2-wordlists
    try:
        with open(wlist[0]) as f1:
            for line1 in f1:
                w1 = line1.strip()
                with open(wlist[1]) as f2:
                    for line2 in f2:
                        w2 = line2.strip()
                        batch.append(brutemain(url, headers, payload, wlist, method, tracker,
                                               w1, w2, None, None, sem, session))
                        if len(batch) >= batch_size:
                            await run_batch(batch)
        await run_batch(batch)
        return
    except IndexError:
        pass

    # single wordlist
    with open(wlist[0]) as f1:
        for line1 in f1:
            w1 = line1.strip()
            batch.append(brutemain(url, headers, payload, wlist, method, tracker,
                                   w1, None, None, None, sem, session))
            if len(batch) >= batch_size:
                await run_batch(batch)
    await run_batch(batch)

    print("Please check br_finds.txt for results")


# --- MAIN ---
async def main():
    sem = asyncio.Semaphore(100)
    async with aiohttp.ClientSession() as session:
        if os.path.isfile(url):
            with open(url) as uf:
                for line in uf:
                    u = line.strip()
                    if u:
                        await brute(u, headers, payload, wlist, method, sem, session)
        else:
            await brute(url, headers, payload, wlist, method, sem, session)

asyncio.run(main())
