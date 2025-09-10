import asyncio
import aiohttp
import os, re, json
from itertools import product
import urllib3, requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- User input ---

print("       Welcome back lieutenant       ")
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


payload = input("Payload (use FUZZ/BUZZ/CUZZ/DUZZ placeholders): ").strip()

print("⚠️ Note: All FUZZ/BUZZ/CUZZ/DUZZ will be replaced if present in URL headers & payload")
# --- add tracker obj ---
tracker = {}

# --- add wlist array ---
wlist=[]
for i in re.findall("[FBCD]{1}UZZ", payload):
   wlist.append(input(f"Please enter wodlist for {i} in payload: ").replace('~/', os.path.expanduser("~")+'/') )
for i in re.findall("[FBCD]{1}UZZ", url):
   wlist.append(input(f"Please enter wodlist for {i} in URL: ").replace('~/', os.path.expanduser("~")+'/') )
for i in re.findall("[FBCD]{1}UZZ", json.dumps(headers)):
   wlist.append(input(f"Please enter wodlist for {i} in headers: ").replace('~/', os.path.expanduser("~")+'/') )


# --- ASYNC brutemain (replaces requests.*) ---
async def brutemain(url, headers, payload, wlist, method, tracker,
                    f1=None,f2=None,f3=None,f4=None, sem=None, session=None):
    current = {} # current req details
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
        if method=="POST":
            async with session.post(url, headers=headers, data=payload, ssl=False) as r:
                text = await r.text()
                status = r.status
                resp_headers = r.headers
        elif method=="GET":
            async with session.get(url, headers=headers, ssl=False) as r:
                text = await r.text()
                status = r.status
                resp_headers = r.headers

    print(f"[I]: Bruting, req sent ~ [{method}] {url} with payload {payload}\nHeaders: {str(headers)}")
    current["sc"] = status
    current["hsize"] = len("".join(f"{k}: {v}\r\n" for k, v in resp_headers.items()).encode("utf-8"))
    current["rsize"] = len(text)
    current["words"] = len(text.split(' '))
    current["lines"] = len(text.split("\n"))
    for i in tracker:
        if (tracker[i]!="DYNAMIC"):
            if (tracker[i]!=current[i]):
                with open('finds.txt', 'a') as f:
                    f.write(f"Find for URL {url}\nDefault req: sc={tracker['sc']},hsize={tracker['hsize']},rsize={tracker['rsize']},words={tracker['words']},lines={tracker['lines']}  VS sc={current['sc']},hsize={current['hsize']},rsize={current['rsize']},words={current['words']},lines={current['lines']}\n ON STRING(s) f1={f1},f2={f2},f3={f3},f4={f4},\n\n")
                return ""


# --- ASYNC brute wrapper with batching ---
async def brute(url, headers, payload, wlist, method, tracker, sem, session, batch_size=50000):
    batch = []

    async def run_batch(batch):
        if batch:
            await asyncio.gather(*batch)
            batch.clear()

    # try 4-wordlists
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

    # fallback to 3 wordlists
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

    # fallback to 2 wordlists
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

    print("Please check finds.txt for results")



## MAIN()

for i in range(3):
    # keep sync staticism detection as-is
    if method == "GET":
        r = requests.get(url.replace("FUZZ", i*" A ").replace("BUZZ", i*" A ").replace("CUZZ", i*" A ").replace("DUZZ", i*" A "),
                         headers=json.loads(json.dumps(headers).replace("FUZZ", i*" A ").replace("BUZZ", i*" A ").replace("CUZZ", i*" A ").replace("DUZZ", i*" A ")),
                         verify=False)
    if method == "POST":
        r = requests.post(url.replace("FUZZ", i*" A ").replace("BUZZ", i*" A ").replace("CUZZ", i*" A ").replace("DUZZ", i*" A "),
                          headers=json.loads(json.dumps(headers).replace("FUZZ", i*" A ").replace("BUZZ", i*" A ").replace("CUZZ", i*" A ").replace("DUZZ", i*" A ")),
                          verify=False,
                          data=payload.replace("FUZZ", i*" A ").replace("BUZZ", i*" A ").replace("CUZZ", i*" A ").replace("DUZZ", i*" A "))
    if i==0:
        tracker["sc"] = r.status_code
        tracker["hsize"] = len("".join(f"{k}: {v}\r\n" for k, v in r.headers.items()).encode("utf-8"))
        tracker["rsize"] = len(r.text)
        tracker["words"] = len(r.text.split(' '))
        tracker["lines"] = len(r.text.split("\n"))
    else:
        if tracker["sc"] != r.status_code: tracker["sc"] = "DYNAMIC"
        if tracker["hsize"] != len("".join(f"{k}: {v}\r\n" for k, v in r.headers.items()).encode("utf-8")): tracker["hsize"] = "DYNAMIC"
        if tracker["rsize"] != len(r.text): tracker["rsize"] = "DYNAMIC"
        if tracker["words"] != len(r.text.split(' ')): tracker["words"] = "DYNAMIC"
        if tracker["lines"] != len(r.text.split("\n")): tracker["lines"] = "DYNAMIC"

print("Okay fam static settings detected so far:")
print("Status code staticism: "+str(tracker["sc"]))
print("Headers size staticism: "+str(tracker["hsize"]))
print("Response size staticism: "+str(tracker["rsize"]))
print("Words staticism: "+str(tracker["words"]))
print("Lines staticism: "+str(tracker["lines"]))

open("finds.txt", "w").close()

async def main():
    sem = asyncio.Semaphore(100)
    async with aiohttp.ClientSession() as session:
        if os.path.isfile(url):
            with open(url) as uf:
                for line in uf:
                    u = line.strip()
                    if u:
                        await brute(u, headers, payload, wlist, method, tracker, sem, session)
        else:
            await brute(url, headers, payload, wlist, method, tracker, sem, session)

asyncio.run(main())
