import httpx
import asyncio
import sys
import os

async def resolve_redirect(session, url, keyword=None):
    try:
        r = await session.get(url, follow_redirects=True, timeout=8)
        final = str(r.url)
        if keyword is None or keyword in final:
            print(f"[+] {url} -> {final}")
            return final
    except Exception as e:
        print(f"[-] {url} failed: {e}")
    return None

async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 gecko.py <url-file> [filter-substring]")
        return

    input_file = sys.argv[1]
    keyword = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.isfile(input_file):
        print(f"❌ File not found: {input_file}")
        return

    with open(input_file, "r") as f:
        links = [line.strip() for line in f if line.strip()]

    async with httpx.AsyncClient() as session:
        tasks = [resolve_redirect(session, link, keyword) for link in links]
        results = await asyncio.gather(*tasks)

    with open("redirects.txt", "w") as f:
        for url in results:
            if url:
                f.write(url + "\n")

if __name__ == "__main__":
    asyncio.run(main())
