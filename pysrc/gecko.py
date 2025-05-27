import httpx
import sys
import os
import anyio

async def resolve_redirect(session, url, keyword=None):
    try:
        r = await session.get(url, follow_redirects=True, timeout=3)
        final = str(r.url)
        if keyword is None or keyword in final:
            print(f"[+] {url} -> {final}")
            return final
        else:
            print(f"[-] {url} -> {final} (filtered)")
    except Exception as e:
        print(f"[-] {url} failed: {e}")
    return None

async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 gecko-fast.py <url-file> [filter-substring]")
        return

    input_file = sys.argv[1]
    keyword = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.isfile(input_file):
        print(f"❌ File not found: {input_file}")
        return

    with open(input_file, "r") as f:
        links = [line.strip() for line in f if line.strip()]

    results = []

    async with httpx.AsyncClient() as session:
        async with anyio.create_task_group() as tg:
            for link in links:
                tg.start_soon(run_and_store, session, link, keyword, results)

    with open("redirects.txt", "w") as f:
        for url in results:
            if url:
                f.write(url + "\n")

async def run_and_store(session, url, keyword, results):
    result = await resolve_redirect(session, url, keyword)
    if result:
        results.append(result)

if __name__ == "__main__":
    anyio.run(main)
