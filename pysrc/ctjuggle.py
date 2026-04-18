import aiohttp
import asyncio
import argparse
import os
import resource
import json

soft, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
SEM_LIMIT = min(soft - 100, 500)
print(f"[INFO] Semaphore limit: {SEM_LIMIT}")

from aiohttp.client_exceptions import (
    ClientConnectorError, ClientProxyConnectionError, ClientOSError,
    ClientResponseError, ServerTimeoutError, ClientSSLError
)

TIMEOUT       = aiohttp.ClientTimeout(total=20, connect=5, sock_connect=5, sock_read=10)
RETRY_TIMEOUT = aiohttp.ClientTimeout(total=60, connect=10, sock_connect=10, sock_read=30)

INJECT_PARAMS = ["format", "type", "output", "ct", "content-type"]
INJECT_VALUE  = "html"

CHROME_HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection":      "keep-alive",
}

# ── helpers ────────────────────────────────────────────────────

def is_json_ct(ct: str):
    return "json" in ct.lower()

def is_html_ct(ct: str):
    return "text/html" in ct.lower()

def looks_like_json_body(raw: bytes):
    return raw.lstrip()[:1] in (b"{", b"[")

def build_variants(base: str):
    sep = "&" if "?" in base else "?"
    return [f"{base}{sep}{p}={INJECT_VALUE}" for p in INJECT_PARAMS]


# ── fetch ──────────────────────────────────────────────────────

async def get(session, url):
    try:
        async with session.get(url, ssl=False, allow_redirects=True, timeout=TIMEOUT) as r:
            raw = await r.content.read(256 * 1024)
            return r.status, r.headers.get("Content-Type", ""), raw
    except asyncio.TimeoutError:
        try:
            async with session.get(url, ssl=False, allow_redirects=True, timeout=RETRY_TIMEOUT) as r:
                raw = await r.content.read(256 * 1024)
                return r.status, r.headers.get("Content-Type", ""), raw
        except Exception:
            return None, None, None
    except (ClientConnectorError, ClientProxyConnectionError, ClientOSError,
            ClientResponseError, ServerTimeoutError, ClientSSLError, aiohttp.InvalidURL):
        return None, None, None
    except Exception as e:
        print(f"\n[ERR] {url}: {e}")
        return None, None, None


# ── per-url logic ──────────────────────────────────────────────

async def process(session, url, sem, results, counter, total):
    async with sem:
        _, ct, raw = await get(session, url)
        counter[0] += 1
        print(f"\r[{counter[0]}/{total}] scanning...", end="", flush=True)

        if raw is None:
            return

        baseline_is_json = is_json_ct(ct) or (not ct and looks_like_json_body(raw))
        if not baseline_is_json:
            return

        baseline_ct = ct or None

        for injected in build_variants(url):
            s2, ct2, raw2 = await get(session, injected)
            if raw2 is None:
                continue

            ct2_lower = ct2.lower() if ct2 else ""
            hit, reason = False, ""

            if baseline_ct is None:
                if is_html_ct(ct2_lower):
                    hit    = True
                    reason = "CT absent → now text/html"

            elif is_json_ct(baseline_ct):
                if is_html_ct(ct2_lower):
                    hit    = True
                    reason = f"CT flipped: {baseline_ct} → {ct2}"
                elif not ct2:
                    hit    = True
                    reason = f"CT dropped: was {baseline_ct}"

            if hit:
                entry = {
                    "original_url": url,
                    "injected_url": injected,
                    "baseline_ct":  baseline_ct,
                    "new_ct":       ct2 or "(none)",
                    "status":       s2,
                    "reason":       reason,
                }
                results.append(entry)
                print(f"\n[HIT] {injected}  |  {reason}")
                break


# ── main ───────────────────────────────────────────────────────

async def main(file, extra_headers):
    if not os.path.exists(file):
        print(f"[ERROR] File not found: {file}")
        return

    with open(file) as f:
        urls = [l.strip() for l in f if l.strip()]

    if not urls:
        print("[ERROR] Empty URL list.")
        return

    headers = {**CHROME_HEADERS}
    if extra_headers:
        for h in extra_headers:
            if ":" in h:
                k, v = h.split(":", 1)
                headers[k.strip()] = v.strip()

    sem       = asyncio.Semaphore(SEM_LIMIT)
    results   = []
    counter   = [0]
    total     = len(urls)
    connector = aiohttp.TCPConnector(limit=SEM_LIMIT, limit_per_host=10)

    async with aiohttp.ClientSession(headers=headers, connector=connector, trust_env=True) as session:
        await asyncio.gather(*[
            asyncio.create_task(process(session, url, sem, results, counter, total))
            for url in urls
        ])

    os.makedirs("ctjuggle", exist_ok=True)
    out = "ctjuggle/results.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n[DONE] {len(results)} hit(s) → {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CT juggling — JSON endpoints that flip to text/html")
    parser.add_argument("file", help="File with URLs (one per line)")
    parser.add_argument("-H", action="append", help="Extra header  -H 'Name: val'")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.file, args.H))
    except KeyboardInterrupt:
        print("\n[INFO] Stopped.")