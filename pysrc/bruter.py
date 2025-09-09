import asyncio
import aiohttp
import re, json
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
   wlist.append(input(f"Please enter wodlist for {i}: ") )

def brutemain(url, headers, payload, wlist, method, tracker, f1=None,f2=None,f3=None,f4=None):
    if method == "POST":
        ''
    #r = requests.post(url, headers=headers, verify=False, data=payload.replace("FUZZ", i*" A ").replace("BUZZ", i*" A ").replace("CUZZ", i*" A ").replace("DUZZ", i*" A "))

def brute(url, headers, payload, wlist, method, tracker):

    try:
        with open(wlist[0]) as f1:
            with open(wlist[1]) as f2:
                with open(wlist[2]) as f3:
                    with open(wlist[3]) as f4:
                        brutemain(url, headers, payload, wlist, method, tracker, f1, f2, f3, f4)
    except:
        try:
            with open(wlist[0]) as f1:
               with open(wlist[1]) as f2:
                   with open(wlist[2]) as f3:
                        brutemain(url, headers, payload, wlist, method, tracker, f1, f2, f3)
        except:
            try:
                with open(wlist[0]) as f1:
                    with open(wlist[1]) as f2:
                        brutemain(url, headers, payload, wlist, method, tracker, f1, f2)
            except:
                try:
                    with open(wlist[0]) as f1:
                        brutemain(url, headers, payload, wlist, method, tracker, f1)
                except:
                    brutemain(url, headers, payload, wlist, method, tracker)



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
# if =="DYNAMIC" not static
print("Status code staticism: "+str(tracker["sc"]))
print("Headers size staticism: "+str(tracker["hsize"]))
print("Response size staticism: "+str(tracker["rsize"]))
print("Words staticism: "+str(tracker["words"]))
print("Lines staticism: "+str(tracker["lines"]))

# STATICISIM DETECTD FOR FURTHER RESULT DETECTION, START BRUTE()

brute(url, headers, payload, wlist, method, tracker)