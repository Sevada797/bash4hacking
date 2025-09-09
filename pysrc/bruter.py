import asyncio
import aiohttp
import os, re, json
from itertools import product
import requests

# --- User input ---

print("       Welcome back lieutenant       ")
url = input("Target URL: ").strip()
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
if not payload:
    print("⚠️ Note: Payload is empty. All FUZZ/BUZZ/CUZZ/DUZZ will be replaced if present.")

# --- add tracker obj ---
tracker = {}

# --- add wlist array ---
wlist=[]
for i in re.findall("[FBCD]{1}UZZ", payload):
   wlist.append(input(f"Please enter wodlist for {i}: ").replace('~/', '/home/'+os.getlogin()+'/') )

def brutemain(url, headers, payload, wlist, method, tracker, f1=None,f2=None,f3=None,f4=None):
    current = {} # current req details
    if (f1 and f2 and f3 and f4):
        payload=payload.replace("FUZZ", f1).replace("BUZZ", f2).replace("CUZZ", f3).replace("DUZZ", f4)
        url=url.replace("FUZZ", f1).replace("BUZZ", f2).replace("CUZZ", f3).replace("DUZZ", f4)
    elif (f1 and f2 and f3):
        payload=payload.replace("FUZZ", f1).replace("BUZZ", f2).replace("CUZZ", f3)
        url=url.replace("FUZZ", f1).replace("BUZZ", f2).replace("CUZZ", f3)
    elif (f1 and f2):
        payload=payload.replace("FUZZ", f1).replace("BUZZ", f2)
        url=url.replace("FUZZ", f1).replace("BUZZ", f2)
    elif (f1):
        payload=payload.replace("FUZZ", f1)
        url=url.replace("FUZZ", f1)
    else:
        payload=payload # just for the sake of philosophy ;D
        url=url # just for the sake of philosophy ;D

    if method=="POST":
        r = requests.post(url, headers=headers, verify=False, data=payload)
    elif method=="GET":
        r = requests.post(url, headers=headers, verify=False)
    print (f"[I]: Bruting, req sent ~ [{method}] {url} with payload {payload}\nHeaders: {str(headers)}")
    current["sc"] = r.status_code
    current["hsize"] = len("".join(f"{k}: {v}\r\n" for k, v in r.headers.items()).encode("utf-8")) # headers size
    current["rsize"] = len(r.text)
    current["words"] = len(r.text.split(' '))
    current["lines"] = len(r.text.split("\n"))
    for i in tracker:
        if (tracker[i]!="DYNAMIC"):
            if ((tracker[i]!=current[i]) or 
        (tracker[i]!=current[i])
        or (tracker[i]!=current[i])
        or (tracker[i]!=current[i])
        or (tracker[i]!=current[i]) ):
                f=open('finds.txt', 'a')
                f.write(f"Default req: sc={tracker['sc']},hsize={tracker['hsize']},rsize={tracker['rsize']},words={tracker['words']},lines={tracker['lines']}  VS sc={current['sc']},hsize={current['hsize']},rsize={current['rsize']},words={current['words']},lines={current['lines']}\n ON STRING(s) f1={f1},f2={f2},f3={f3},f4={f4},\n\n")
                f.close()
                return ""


def brute(url, headers, payload, wlist, method, tracker):
    # 4 wordlists
    try:
        with open(wlist[0]) as f1:
            for line1 in f1:
                word1 = line1.strip()
                if not word1:
                    continue
                with open(wlist[1]) as f2:
                    for line2 in f2:
                        word2 = line2.strip()
                        if not word2:
                            continue
                        with open(wlist[2]) as f3:
                            for line3 in f3:
                                word3 = line3.strip()
                                if not word3:
                                    continue
                                with open(wlist[3]) as f4:
                                    for line4 in f4:
                                        word4 = line4.strip()
                                        if not word4:
                                            continue
                                        brutemain(url, headers, payload, wlist, method, tracker, word1, word2, word3, word4)
    except IndexError:
        # fallback for fewer than 4 wordlists
        try:
            with open(wlist[0]) as f1:
                for line1 in f1:
                    word1 = line1.strip()
                    if not word1:
                        continue
                    with open(wlist[1]) as f2:
                        for line2 in f2:
                            word2 = line2.strip()
                            if not word2:
                                continue
                            with open(wlist[2]) as f3:
                                for line3 in f3:
                                    word3 = line3.strip()
                                    if not word3:
                                        continue
                                    brutemain(url, headers, payload, wlist, method, tracker, word1, word2, word3)
        except IndexError:
            try:
                with open(wlist[0]) as f1:
                    for line1 in f1:
                        word1 = line1.strip()
                        if not word1:
                            continue
                        with open(wlist[1]) as f2:
                            for line2 in f2:
                                word2 = line2.strip()
                                if not word2:
                                    continue
                                brutemain(url, headers, payload, wlist, method, tracker, word1, word2)
            except IndexError:
                with open(wlist[0]) as f1:
                    for line1 in f1:
                        word1 = line1.strip()
                        if not word1:
                            continue
                        brutemain(url, headers, payload, wlist, method, tracker, word1)

    print("Please check finds.txt for results")




## MAIN()

for i in range(3):  #  " A " space + increasing is useful, to then not caught false positives in case if e.g. FUZZ is reflected in HTML 
    if method == "GET":
        r = requests.get(url.replace("FUZZ", i*" A ").replace("BUZZ", i*" A ").replace("CUZZ", i*" A ").replace("DUZZ", i*" A "), headers=headers, verify=False)
    if method == "POST":
        r = requests.post(url, headers=headers, verify=False, data=payload.replace("FUZZ", i*" A ").replace("BUZZ", i*" A ").replace("CUZZ", i*" A ").replace("DUZZ", i*" A "))
    if i==0: #setter part in loop 
        tracker["sc"] = r.status_code
        tracker["hsize"] = len("".join(f"{k}: {v}\r\n" for k, v in r.headers.items()).encode("utf-8")) # headers size
        tracker["rsize"] = len(r.text)
        tracker["words"] = len(r.text.split(' '))
        tracker["lines"] = len(r.text.split("\n"))
    else:
        if tracker["sc"] != r.status_code:
            tracker["sc"] = "DYNAMIC"
        if tracker["hsize"] != len("".join(f"{k}: {v}\r\n" for k, v in r.headers.items()).encode("utf-8")):
            tracker["hsize"] = "DYNAMIC"
        if tracker["rsize"] != len(r.text):
            tracker["rsize"] = "DYNAMIC"
        if tracker["words"] != len(r.text.split(' ')):
            tracker["words"] = "DYNAMIC"
        if tracker["lines"] != len(r.text.split("\n")):
            tracker["lines"] = "DYNAMIC"
print("Okay fam static settings detected so far:")

print("Status code staticism: "+str(tracker["sc"]))
print("Headers size staticism: "+str(tracker["hsize"]))
print("Response size staticism: "+str(tracker["rsize"]))
print("Words staticism: "+str(tracker["words"]))
print("Lines staticism: "+str(tracker["lines"]))

# STATICISIM DETECTD FOR FURTHER RESULT DETECTION, START BRUTE()

open("finds.txt", "w").close() # Clear previous finds

brute(url, headers, payload, wlist, method, tracker)