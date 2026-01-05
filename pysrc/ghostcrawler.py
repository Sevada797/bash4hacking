import asyncio
from playwright.async_api import async_playwright
import sys
import os
from datetime import datetime

# 🔧 Ask for file path
def get_url_file():
    path = input("Enter path to file with URLs: ").strip()
    while not os.path.exists(path):
        path = input("File not found. Enter valid path: ").strip()
    return path

# 🔧 Ask for raw headers
def get_headers_from_input():
    print("Paste raw headers (press Enter twice to end):")
    lines = []
    while True:
        line = sys.stdin.readline().strip("\n")
        if line == "":
            break
        lines.append(line)
    headers = {}
    for line in lines:
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip()] = v.strip()
    return headers

# 📝 Setup logging files
url_file = get_url_file()
url_filename = url_file.split("/")[-1].split(".")[0]
log_file = f"ghostcrawl_{url_filename}.txt"
responses_file = f"ghostcrawl_{url_filename}_responses.txt"
log_handle = open(log_file, 'w')
responses_handle = open(responses_file, 'w')

def log_message(msg):
    """Write to both console and log file"""
    print(msg)
    log_handle.write(msg + "\n")
    log_handle.flush()

def log_response_body(url, status, content_type, body):
    """Log response body to responses file"""
    responses_handle.write(f"URL: {url}\n")
    responses_handle.write(f"Status: {status}\n")
    responses_handle.write(f"Content-Type: {content_type}\n")
    responses_handle.write(f"{'='*50}\n")
    responses_handle.write(body + "\n")
    responses_handle.write(f"{'='*50}\n\n")
    responses_handle.flush()

headers_input = get_headers_from_input()
log_message(f"📋 Log file: {log_file}")
log_message(f"📝 Responses file: {responses_file}")
log_message(f"📂 URLs from: {url_file}")
log_message("=" * 80)

async def run():
    urls = open(url_file).read().splitlines()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(extra_http_headers=headers_input)
        
        for url in urls:
            page = await context.new_page()
            # 🎯 Log every request
            page.on("request", lambda req: asyncio.create_task(log_request(req)))
            # 🔴 Log every response
            page.on("response", lambda res: asyncio.create_task(log_response(res)))
            
            try:
                log_message(f"🔍 Visiting: {url}")
                await page.goto(url, timeout=7000, wait_until="load")
                log_message(f"✅ Page loaded: {url}")
                log_message(f"⏳ Waiting 3s for all requests to fire...")
                await page.wait_for_timeout(3000)
            except Exception as e:
                log_message(f"❌ Failed/Timeout: {url} ({e})")
            await page.close()
        await browser.close()

async def log_request(req):
    try:
        method = req.method
        url = req.url
        post_data = await req.post_data() if method != "GET" else None
        curl = f"curl -X {method} '{url}'"
        if post_data:
            curl += f" -d '{post_data}'"
        log_message(f"💥 {curl}")
    except Exception as e:
        log_message(f"Error logging request: {e}")

async def log_response(res):
    """Log HTTP responses and capture body if text-based"""
    try:
        status = res.status
        url = res.url
        content_type = res.headers.get("content-type", "unknown")
        log_message(f"📡 [{status}] {url}")
        
        # Check if response is text-based (json, xml, html, text, etc)
        if any(t in content_type.lower() for t in ["application/json", "application/xml", "text/html", "text/plain", "text/xml", "application/"]):
            try:
                body = await res.text()
                log_response_body(url, status, content_type, body)
            except:
                pass
    except Exception as e:
        log_message(f"Error logging response: {e}")

asyncio.run(run())
log_message(f"✅ Logging complete: {log_file}")
log_message(f"✅ Responses saved: {responses_file}")
log_handle.close()
responses_handle.close()
