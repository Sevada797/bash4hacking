import asyncio
import aiohttp
import sys
import argparse

# Thresholds for response size (in bytes)
NORMAL_3XX_SIZE = 1024      # 1KB - normal redirect response
SUSPICIOUS_3XX_SIZE = 10240 # 10KB - suspicious threshold
VERY_SUSPICIOUS_3XX_SIZE = 102400 # 100KB - very suspicious
OUTPUT = "3xxdata.txt"
CONCURRENCY = 15
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

def ensure_https(url_str):
    """Add https:// if no scheme present"""
    if not url_str.startswith(('http://', 'https://')):
        return f"https://{url_str}"
    return url_str

async def check_3xx_response_size(session, url, semaphore):
    """Check 3xx response body size - flag if suspiciously large"""
    async with semaphore:
        try:
            async with session.get(url, allow_redirects=False, ssl=False, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                status = resp.status
                
                # Only check 3xx responses
                if not (300 <= status < 400):
                    return None
                
                # Get response body
                body = await resp.text(errors='ignore')
                
                # Calculate size in bytes
                response_size = len(body.encode('utf-8'))
                
                # Flag if suspiciously large
                if response_size > SUSPICIOUS_3XX_SIZE:
                    return {
                        'url': url,
                        'status': status,
                        'size': response_size,
                        'size_kb': round(response_size / 1024, 2),
                        'level': 'CRITICAL' if response_size > VERY_SUSPICIOUS_3XX_SIZE else 'SUSPICIOUS'
                    }
        
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            pass
        
        return None

async def scan_urls(urls):
    """Scan multiple URLs concurrently - normal pace"""
    semaphore = asyncio.Semaphore(CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=CONCURRENCY, ssl=False)
    headers = {'User-Agent': USER_AGENT}
    
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        tasks = [check_3xx_response_size(session, url, semaphore) for url in urls]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]

def main():
    parser = argparse.ArgumentParser(description="Detect suspiciously large 3xx responses")
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
    
    print(f"[*] Scanning {len(urls)} URLs for suspiciously large 3xx responses...")
    print(f"[*] Threshold: {SUSPICIOUS_3XX_SIZE/1024}KB (normal redirects are <1KB)")
    
    results = asyncio.run(scan_urls(urls))
    
    if results:
        # Sort by size, largest first
        results.sort(key=lambda x: x['size'], reverse=True)
        
        print(f"\n[+] Found {len(results)} suspicious 3xx responses:\n")
        
        output_lines = []
        for result in results:
            severity = f"[{result['level']}]" if result['level'] == 'CRITICAL' else ""
            output_line = f"[!] {result['url']} --> {result['size_kb']}KB ({result['size']} bytes) {severity}"
            print(output_line)
            output_lines.append(output_line)
        
        with open(OUTPUT, 'w') as f:
            f.write('\n'.join(output_lines))
        print(f"\n[✓] Results saved to: {OUTPUT}")
    else:
        print("[~] No suspicious 3xx responses found")

if __name__ == "__main__":
    main()