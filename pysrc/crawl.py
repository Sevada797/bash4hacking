#!/usr/bin/env python3
import asyncio, aiohttp, time, re, argparse, os
from urllib.parse import urljoin, urlparse
from collections import defaultdict
import ssl
# --- Global config placeholders ---
semaphore_limit = 10
collection, visited = [], set()
scanme = {}
bad_patterns = [
    re.compile(r"/[a-zA-Z0-9]+\-[a-zA-Z0-9]+\-"),
    re.compile(r"/[a-zA-Z0-9]+_[a-zA-Z0-9]+_"),
    re.compile(r"/[0-9]+\-")
]

print('''
⠀⠀⠀⠀⠀⠀⠀⠀⣀⣤⣶⣶⣾⣿⣿⣿⣿⣷⣶⣶⣤⣀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⣠⣶⣿⣿⠿⠛⠉⠉⠉⠀⠀⠉⠉⠉⠛⠿⣿⣿⣶⣄⠀⠀⠀⠀⠀
⠀⠀⠀⣠⣾⣿⠟⠉⠀⠀⠀⠀⢀⣤⣤⣤⣀⠀⠀⠀⠀⠀⠉⠻⣿⣷⣄⠀⠀⠀
⠀⠀⣼⣿⡟⠁⠀⠀⠀⠀⣠⣾⣿⣿⣿⣿⣿⣿⣯⣢⡀⠀⠀⠀⠈⢻⣿⣧⠀⠀
⠀⣼⣿⡟⠀⠀⠀⠀⠀⣼⣿⣿⣿⣿⣿⣿⠏⠁⠀⠀⠀⠀⠀⠀⠀⠀⢻⣿⣧⠀
⢸⣿⡟⠀⠀⠀⠀⠀⢠⣿⣿⣿⣿⣿⣿⣿⣶⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⣿⡇
⣾⣿⡇⠀⠀⠀⠀⠀⣰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣷
⣿⣿⡁⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣆⠀⠀⠀⠀⠀⠀⠀⢀⣿⣿
⢿⣿⡇⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡄⠀⠀⠀⠀⠀⠀⢸⣿⡿
⢸⣿⣧⠀⠀⠀⠀⠀⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⠀⠀⠀⠀⠀⠀⣼⣿⡇
⠀⢻⣿⣧⠀⠀⠀⠀⠈⠋⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣧⠀⠀⠀⠀⣼⣿⡟⠀
⠀⠀⢻⣿⣧⡀⠀⠀⠀⠀⠀⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠀⠀⢀⣼⣿⡟⠀⠀
⠀⠀⠀⠙⢿⣿⣦⣀⠀⠀⢀⣼⠟⠙⠘⣿⣿⣿⣿⣿⣿⣿⠀⣴⣿⡿⠋⠀⠀⠀
⠀⠀⠀⠀⠀⠙⠿⣿⣿⣿⣿⣦⣀⣀⣾⣁⡈⠛⢿⣿⣿⣿⡆⠹⠋⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠉⠛⠿⠿⢿⣿⣿⣿⣿⣆⠈⢻⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀

      Starting crow(ler) v1.0, by me & AI. 3nj0y~
''')
time.sleep(3)

# --- Helpers ---
def keep_unique_5_per_first_path(urls):
    first_path_map = defaultdict(list)
    for u in urls:
        path = urlparse(u).path
        segments = path.split("/")
        first_path = "/" + segments[1] if len(segments) > 1 else "/"
        if len(first_path_map[first_path]) < 5:
            first_path_map[first_path].append(u)
    result = []
    for lst in first_path_map.values():
        result.extend(lst)
    return result

def filter_bad_patterns(urls):
    pattern_map = defaultdict(list)
    result = []
    for u in urls:
        added = False
        for pat in bad_patterns:
            if pat.search(urlparse(u).path):
                if len(pattern_map[pat]) < 5:
                    pattern_map[pat].append(u)
                    added = True
                break
        if not added:
            result.append(u)
    # Add kept bad patterns at the end
    for lst in pattern_map.values():
        result.extend(lst)
    return result

def write_log(collection, filename="crawler_log"):
    """Deduplicate, sort, and rewrite log"""
    collection = sorted(set(collection))
    with open(filename, "w") as f:
        f.write("\n".join(collection) + "\n")
    return collection

# --- global domain holder ---
base_domain = None

def extract_domain_from_input(args):
    """Extract base domain from user input (URL or file first line)"""
    global base_domain
    if args.list_file:
        with open(args.list_file, "r") as f:
            first_line = next((line.strip() for line in f if line.strip()), None)
            if not first_line:
                raise ValueError("List file is empty")
            base = urlparse(first_line).netloc
    else:
        base = urlparse(args.url).netloc
    base_domain = base.split(":")[0]
    print(f"[+] Base domain set to: {base_domain}")


# --- Async gathering ---
async def gather(url, session):
    visited.add(url)
    try:
        async with session.get(url, timeout=10) as resp:
            try:
                html = await resp.text()
            except UnicodeDecodeError:
                print(f"Skipped non-UTF8 content: {url}")
                return []
    except Exception as e:
        print(f"Failed {url}: {e}")
        return []

    # Extract links
    relative_links = re.findall(r'["\'](/[a-zA-Z0-9_\-/?.=&%]+)["\']', html)
    absolute_links_raw = re.findall(r'https?://[^"\'>\\<\s]+', html)
    combined_links = absolute_links_raw + [urljoin(url, p) for p in relative_links]
    unique_links = sorted(set(combined_links))

    # Keep only in-scope
    # use base_domain for scoping
    domain_pattern = re.escape(base_domain)
    scoped_links = [l for l in unique_links if re.search(fr'//{domain_pattern}|\.{domain_pattern}', l)]

    for link in scoped_links:
        print(link)
    return scoped_links

async def crawl_depth(depth_level, urls, session, sem, pdt):
    next_urls = []
    start_time = time.time()
    for u in urls:
        if u in visited:
            continue
        if time.time() - start_time > pdt:
            print("Max per-depth time exceeded")
            break
        async with sem:
            new_links = await gather(u, session)
        # Apply unique 5 + bad pattern filter
        new_links = keep_unique_5_per_first_path(new_links)
        new_links = filter_bad_patterns(new_links)

        next_urls += new_links
        collection.extend(new_links)
        write_log(collection)
    return next_urls

async def run_crawler(urls, depth, pdt):
    sem = asyncio.Semaphore(semaphore_limit)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:

        # Depth 0
        first_urls = []
        for u in urls:
            new_links = await gather(u, session)
            new_links = keep_unique_5_per_first_path(new_links)
            new_links = filter_bad_patterns(new_links)
            first_urls.extend(new_links)
        scanme[1] = first_urls
        collection.extend(first_urls + urls)
        write_log(collection)

        # Further depths
        for i in range(1, depth + 1):
            if i not in scanme:
                scanme[i] = []
            next_urls = await crawl_depth(i, scanme[i], session, sem, pdt)
            scanme[i + 1] = next_urls

def crawl(args):
    urls = []
    if args.list_file:
        # Read bulk URLs from file
        with open(args.list_file, "r") as f:
            urls = [line.strip() for line in f if line.strip()]
    else:
        urls = [args.url.strip("/")]

    extract_domain_from_input(args)

    asyncio.run(run_crawler(urls, args.depth, args.pdt))

# --- CLI parsing ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Async Python Crawler")
    parser.add_argument("url", nargs="?", help="Single URL to crawl")
    parser.add_argument("depth", type=int, help="Crawl depth")
    parser.add_argument("pdt", type=int, help="Max seconds per depth")
    parser.add_argument("-l", "--list-file", help="File with list of URLs to crawl in bulk")
    args = parser.parse_args()
    crawl(args)
