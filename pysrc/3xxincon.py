import asyncio
import aiohttp
import sys
import argparse
import re
from urllib.parse import urljoin, urlparse

OUTPUT = "3xxincon.txt"
CONCURRENCY = 15
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

def ensure_https(url_str):
    """Add https:// if no scheme present"""
    if not url_str.startswith(('http://', 'https://')):
        return f"https://{url_str}"
    return url_str

def normalize_url(url_str):
    """
    Normalize URL for comparison:
    - Remove trailing slashes
    - Remove www prefix
    - Lowercase
    - Extract just domain + path (ignore port variations)
    """
    if not url_str:
        return ""
    
    url_str = url_str.strip()
    parsed = urlparse(url_str)
    
    # Get netloc without www
    netloc = parsed.netloc.lower()
    if netloc.startswith('www.'):
        netloc = netloc[4:]
    
    # Get path and remove trailing slash
    path = parsed.path.rstrip('/') if parsed.path else ''
    
    # Combine
    normalized = f"{netloc}{path}"
    return normalized

def urls_match(url1, url2):
    """
    Check if two URLs are effectively the same:
    - Absolute vs relative (resolve against same origin)
    - With/without www
    - With/without trailing slash
    - Same path = match
    """
    if not url1 or not url2:
        return False
    
    # Normalize both
    norm1 = normalize_url(url1)
    norm2 = normalize_url(url2)
    
    # Direct match after normalization
    if norm1 == norm2:
        return True
    
    # Check if one is relative and other is absolute with same path
    parsed1 = urlparse(url1)
    parsed2 = urlparse(url2)
    
    # If one is relative (no scheme)
    if not parsed1.scheme and parsed2.scheme:
        # url1 is relative like '/admin', url2 is absolute like 'https://site.com/admin'
        path1 = parsed1.path.rstrip('/')
        path2 = parsed2.path.rstrip('/')
        if path1 == path2 and path1:  # Both have same path and path is not empty
            return True
    
    if not parsed2.scheme and parsed1.scheme:
        path1 = parsed1.path.rstrip('/')
        path2 = parsed2.path.rstrip('/')
        if path1 == path2 and path1:
            return True
    
    return False

async def check_redirect_inconsistency(session, url, semaphore):
    """Check for inconsistencies between header redirect and body content"""
    async with semaphore:
        try:
            async with session.get(url, allow_redirects=False, ssl=False, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                status = resp.status
                
                # Only check 3xx responses
                if not (300 <= status < 400):
                    return None
                
                # Get Location header
                location_header = resp.headers.get('Location', '').strip()
                
                # Get response body
                body = await resp.text(errors='ignore')
                
                # Check response size (flag if suspiciously large for a redirect)
                response_size = len(body.encode('utf-8'))
                # Most 3xx redirects are <1KB, flag if >10KB
                large_response = response_size > 10240  # 10KB threshold
                
                # Find redirects in body
                body_redirects = set()
                
                # Find href attributes
                href_matches = re.findall(r'href=["\']([^"\']+)["\']', body, re.IGNORECASE)
                body_redirects.update(href_matches)
                
                # Find meta refresh
                meta_match = re.search(r'meta\s+http-equiv=["\']refresh["\'][^>]*content=["\']([^"\']*url=)?([^"\']+)', body, re.IGNORECASE)
                if meta_match:
                    body_redirects.add(meta_match.group(2))
                
                # Find javascript redirects
                js_patterns = [
                    r'window\.location\s*=\s*["\']([^"\']+)["\']',
                    r'location\.href\s*=\s*["\']([^"\']+)["\']',
                    r'location\.replace\s*\(\s*["\']([^"\']+)["\']',
                    r'redirect["\s:]*=?["\s]*([^"<>\s]+)'
                ]
                
                for pattern in js_patterns:
                    matches = re.findall(pattern, body, re.IGNORECASE)
                    body_redirects.update(matches)
                
                # Clean up: remove empty strings, whitespace-only, and very short junk
                body_redirects.discard('')
                # Filter: remove strings < 3 chars, obvious HTML junk (common tag attributes)
                junk_patterns = {'href', 'src', 'alt', 'id', 'class', 'data', 'title', 'name', 'value', 'type'}
                body_redirects = {
                    r.strip() for r in body_redirects 
                    if r.strip() and len(r.strip()) > 3 and r.strip().lower() not in junk_patterns
                }
                
                # Only check for inconsistency if we found actual redirects in body
                # Skip if no body redirects (like mail.ru case with empty/minimal body)
                if not body_redirects:
                    return None
                
                # Check for inconsistency
                if location_header and body_redirects:
                    # Check if ANY body redirect matches the header location
                    has_match = False
                    for body_redirect in body_redirects:
                        if urls_match(body_redirect, location_header):
                            has_match = True
                            break
                    
                    # Only report if no match found (true inconsistency)
                    if not has_match:
                        return {
                            'url': url,
                            'status': status,
                            'header_location': location_header,
                            'body_redirects': body_redirects
                        }
        
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            pass
        
        return None

async def scan_urls(urls):
    """Scan multiple URLs concurrently - normal pace, not too fast"""
    semaphore = asyncio.Semaphore(CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=CONCURRENCY, ssl=False)
    headers = {'User-Agent': USER_AGENT}
    
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        tasks = [check_redirect_inconsistency(session, url, semaphore) for url in urls]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]

def main():
    parser = argparse.ArgumentParser(description="Detect 3xx redirect inconsistencies (header vs body)")
    parser.add_argument("-f", "--file", required=True, help="File with URLs or subdomains (one per line)")
    args = parser.parse_args()
    
    try:
        with open(args.file) as f:
            urls = [ensure_https(line.strip()) for line in f if line.strip()]
    except FileNotFoundError:
        print(f"[!] Error: File '{args.file}' not found")
        sys.exit(1)
    
    if not urls:
        print(f"[!] Error: No URLs found in '{args.file}'")
        sys.exit(1)
    
    print(f"[*] Scanning {len(urls)} URLs for 3xx redirect inconsistencies...")
    print(f"[*] Concurrency: {CONCURRENCY}")
    
    results = asyncio.run(scan_urls(urls))
    
    if results:
        print(f"\n[+] Found {len(results)} inconsistencies:\n")
        
        output_lines = []
        for result in results:
            print(f"[!] {result['url']}")
            print(f"    Status: {result['status']}")
            print(f"    Header Location: {result['header_location']}")
            print(f"    Body Redirects: {', '.join(result['body_redirects'])}\n")
            
            output_lines.append(f"[!] {result['url']}")
            output_lines.append(f"    Status: {result['status']}")
            output_lines.append(f"    Header Location: {result['header_location']}")
            output_lines.append(f"    Body Redirects: {', '.join(result['body_redirects'])}")
            output_lines.append("")
        
        with open(OUTPUT, 'w') as f:
            f.write('\n'.join(output_lines))
        print(f"[✓] Results saved to: {OUTPUT}")
    else:
        print("[~] No inconsistencies found")

if __name__ == "__main__":
    main()