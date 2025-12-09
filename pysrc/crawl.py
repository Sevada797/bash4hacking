#!/usr/bin/env python3
import asyncio, aiohttp, time, re, argparse, os
from urllib.parse import urljoin, urlparse
from collections import defaultdict
import ssl
import traceback 

# --- Global config placeholders ---
semaphore_limit = 10
collection, visited = [], set()
scanme = {}
bad_patterns = [
    re.compile(r"/[a-zA-Z0-9]+\-[a-zA-Z0-9]+\-"),
    re.compile(r"/[a-zA-Z0-9]+_[a-zA-Z0-9]+_"),
    re.compile(r"/[0-9]+\-")
]

# Default Chrome User-Agent
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
}

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
    """Append collection to file, dedupe + keep sorted"""
    
    existing = set()
    if os.path.exists(filename):
        with open(filename, "r") as f:
            existing = {line.strip() for line in f.readlines() if line.strip()}
    
    # Add all from collection
    existing.update(collection)
    
    # Sort and write
    merged = sorted(existing)
    with open(filename, "w") as f:
        f.write("\n".join(merged) + "\n")

    # Also update original list in-memory:
    collection.clear()
    collection.extend(merged)
    
    return collection

def parse_custom_headers(header_list):
    """Parse -H headers in format 'Key: Value'"""
    custom = {}
    if not header_list:
        return custom
    
    for h in header_list:
        if ':' in h:
            key, value = h.split(':', 1)
            custom[key.strip()] = value.strip()
    return custom

# --- global domain holder ---
base_domain = None
current_origin = None

def extract_domain_and_current_origin(url):
    global base_domain, current_origin
    # try to read the url from path or direct input
    parsed = urlparse(url)
    host = parsed.netloc

    # extract main domain (handles subdomains)
    parts = host.split(".")
    if len(parts) >= 2:
        base_domain = ".".join(parts[-2:])
    else:
        base_domain = host

    # store full host for strict origin matching
    current_origin = host  
    print("\n")
    print(f"[+] Base domain set to: {base_domain}")
    print(f"[+] Current origin set to: {current_origin}")
    time.sleep(2)

# --- Async gathering ---
async def gather(url, session):
    try:
        async with session.get(url, timeout=10) as resp:
            try:
                html = await resp.text()
                visited.add(url)
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
        # ---- filter crawl targets to current origin right before gather ----
        parsed_u = urlparse(u)
        if parsed_u.netloc != current_origin:
            print(f"Skiping {u} cause not in current origin")
            continue  # skip visiting URLs not matching current origin

        async with sem:
            new_links = await gather(u, session)
        # Apply unique 5 + bad pattern filter
        new_links = keep_unique_5_per_first_path(new_links)
        new_links = filter_bad_patterns(new_links)

        next_urls += new_links
        collection.extend(new_links)
        write_log(collection)
    return next_urls

async def run_crawler(url, depth, pdt, headers):
    global collection, visited, scanme
    collection, visited = [], set()
    scanme = {}
    sem = asyncio.Semaphore(semaphore_limit)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    # Merge default headers with custom headers (custom overwrites default)
    final_headers = {**DEFAULT_HEADERS, **headers}
    
    print(f"\n[+] Using headers:")
    for k, v in final_headers.items():
        print(f"    {k}: {v}")
    print()

    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=ssl_context),
        headers=final_headers
    ) as session:

        # Depth 0
        first_urls = []

        new_links = await gather(url, session)
        new_links = keep_unique_5_per_first_path(new_links)
        new_links = filter_bad_patterns(new_links)
        first_urls.extend(new_links)
        scanme[1] = first_urls
        collection.extend(first_urls + [url])
        write_log(collection)

        # Further depths
        for i in range(1, depth + 1):
            if i not in scanme:
                scanme[i] = []
            next_urls = await crawl_depth(i, scanme[i], session, sem, pdt)
            scanme[i + 1] = next_urls

def crawl(args):
    urls = []
    
    # Parse custom headers
    custom_headers = parse_custom_headers(args.headers)

    if args.list_file:
        # Read bulk URLs from file
        with open(args.list_file, "r") as f:
            urls = [line.strip() for line in f if line.strip()]
    else:
        urls = [args.url.strip("/")]
    
    for u in urls:
        # RESET GLOBALS for each new root
        global collection, visited, scanme, current_origin, base_domain
        collection, visited = [], set()
        scanme = {}
        extract_domain_and_current_origin(u)
    
        print(f"\n=== Crawling {u} ===\n")
        asyncio.run(run_crawler(u, args.depth, args.pdt, custom_headers))

# --- CLI parsing ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Async Python Crawler with Chrome UA")
    parser.add_argument("url", nargs="?", help="Single URL to crawl")
    parser.add_argument("depth", type=int, help="Crawl depth")
    parser.add_argument("pdt", type=int, help="Max seconds per depth")
    parser.add_argument("-l", "--list-file", help="File with list of URLs to crawl in bulk")
    parser.add_argument("-H", "--headers", action="append", help="Custom headers (format: 'Key: Value'). Can be used multiple times.")
    args = parser.parse_args()
    crawl(args)