#!/usr/bin/env python3

import re
import os
import sys
import argparse
import asyncio
import aiofiles
from pathlib import Path

# =========================
# Regexes for JS discovery
# =========================

SCRIPT_INLINE = re.compile(
    r"<script\b(?![^>]*\bsrc\b)[^>]*>(?P<body>[\s\S]*?)</script\s*>",
    re.IGNORECASE
)

SCRIPT_ABS = re.compile(
    r"<script[^>]+src=(\"|')(?P<url>(https?:)?//[^\"'>]+\.js)",
    re.IGNORECASE
)

SCRIPT_REL = re.compile(
    r"<script[^>]+src=(\"|')(?P<url>/[^\"'>]+\.js)",
    re.IGNORECASE
)

SCRIPT_REL2 = re.compile(
    r"<script[^>]+src=(\"|')(?P<url>[^/\"'>][^\"'>]+\.js)",
    re.IGNORECASE
)


# =========================
# File helpers
# =========================

async def read_file(filepath):
    """Read file asynchronously"""
    try:
        async with aiofiles.open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return await f.read()
    except Exception:
        return None


def is_js_file(filepath):
    """Check if file is a JS file"""
    return filepath.endswith(".js")


def is_html_file(filepath):
    """Check if file is HTML/HTM file"""
    return filepath.endswith((".html", ".htm"))


def is_php_file(filepath):
    """Check if file is a PHP file"""
    return filepath.endswith(".php")


def is_py_file(filepath):
    """Check if file is a Python file"""
    return filepath.endswith(".py")


async def extract_local_js_refs(html_file, html_content):
    """Extract local JS references from HTML (relative paths only)"""
    js_files = set()
    html_dir = os.path.dirname(html_file)
    
    # SCRIPT_REL2: relative paths like "js/app.js"
    for m in SCRIPT_REL2.finditer(html_content):
        rel_path = m.group("url")
        full_path = os.path.normpath(os.path.join(html_dir, rel_path))
        if os.path.isfile(full_path):
            js_files.add(full_path)
    
    # SCRIPT_REL: absolute paths like "/js/app.js" (resolve relative to HTML dir)
    # For local files, treat /path as relative to HTML directory
    for m in SCRIPT_REL.finditer(html_content):
        rel_path = m.group("url").lstrip("/")
        full_path = os.path.normpath(os.path.join(html_dir, rel_path))
        if os.path.isfile(full_path):
            js_files.add(full_path)
    
    return js_files


# =========================
# Core logic
# =========================

async def scan_inline(file_path, html, pattern, f_log):
    """Scan inline scripts in HTML"""
    for m in SCRIPT_INLINE.finditer(html):
        body = m.group("body")
        if not body.strip():
            continue

        for match in re.finditer(pattern, body, re.IGNORECASE | re.DOTALL):
            line = (
                f"[JFL] Pattern hit (INLINE)\n"
                f"Pattern: {pattern}\n"
                f"Match: {match.group(0)}\n"
                f"File: {file_path}\n"
                f"JS: INLINE <script>\n"
            )
            print(line)
            await f_log.write(line + "\n")
            await f_log.flush()


async def scan_js_file(source_file, js_file, pattern, seen_js, f_log):
    """Scan a single JS file for pattern"""
    if js_file in seen_js:
        return
    seen_js.add(js_file)

    body = await read_file(js_file)
    if not body:
        return

    for match in re.finditer(pattern, body, re.IGNORECASE | re.DOTALL):
        line = (
            f"[JFL] Pattern hit\n"
            f"Pattern: {pattern}\n"
            f"Match: {match.group(0)}\n"
            f"Source: {source_file}\n"
            f"JS File: {js_file}\n"
        )
        print(line)
        await f_log.write(line + "\n")
        await f_log.flush()


async def scan_html_file(file_path, pattern, seen_js, f_log):
    """Scan HTML file for inline and external JS"""
    html = await read_file(file_path)
    if not html:
        return

    # Scan inline scripts
    await scan_inline(file_path, html, pattern, f_log)

    # Extract and scan external JS refs
    js_files = await extract_local_js_refs(file_path, html)
    for js_file in js_files:
        await scan_js_file(file_path, js_file, pattern, seen_js, f_log)


async def scan_js_file_direct(file_path, pattern, seen_js, f_log):
    """Directly scan a JS file"""
    if file_path in seen_js:
        return
    seen_js.add(file_path)

    body = await read_file(file_path)
    if not body:
        return

    for match in re.finditer(pattern, body, re.IGNORECASE | re.DOTALL):
        line = (
            f"[JFL] Pattern hit\n"
            f"Pattern: {pattern}\n"
            f"Match: {match.group(0)}\n"
            f"JS File: {file_path}\n"
        )
        print(line)
        await f_log.write(line + "\n")
        await f_log.flush()


async def collect_files(target_path):
    """Recursively collect HTML, JS, PHP and Python files"""
    target_path = os.path.expanduser(target_path)
    target_path = os.path.abspath(target_path)

    files = {"html": [], "js": [], "php": [], "py": []}

    if os.path.isfile(target_path):
        if is_html_file(target_path):
            files["html"].append(target_path)
        elif is_js_file(target_path):
            files["js"].append(target_path)
        elif is_php_file(target_path):
            files["php"].append(target_path)
        elif is_py_file(target_path):
            files["py"].append(target_path)
    elif os.path.isdir(target_path):
        for root, dirs, filenames in os.walk(target_path):
            for fname in filenames:
                fpath = os.path.join(root, fname)
                if is_html_file(fpath):
                    files["html"].append(fpath)
                elif is_js_file(fpath):
                    files["js"].append(fpath)
                elif is_php_file(fpath):
                    files["php"].append(fpath)
                elif is_py_file(fpath):
                    files["py"].append(fpath)

    return files


async def run(target_path, pattern):
    """Main scan logic"""
    log_path = "jfl/log.txt"
    
    # Collect files
    files = await collect_files(target_path)
    all_html = files["html"]
    all_js = files["js"]
    all_php = files["php"]
    all_py = files["py"]

    if not any([all_html, all_js, all_php, all_py]):
        print("[!] No HTML, JS, PHP or Python files found")
        return

    print(f"[JFL] Found {len(all_html)} HTML, {len(all_js)} JS, {len(all_php)} PHP, {len(all_py)} Python files")

    async with aiofiles.open(log_path, "a") as f_log:
        seen_js = set()

        # Scan all HTML files (inline + external refs)
        html_tasks = [
            scan_html_file(f, pattern, seen_js, f_log)
            for f in all_html
        ]
        if html_tasks:
            await asyncio.gather(*html_tasks)

        # Scan direct JS files
        js_tasks = [
            scan_js_file_direct(f, pattern, seen_js, f_log)
            for f in all_js
        ]
        if js_tasks:
            await asyncio.gather(*js_tasks)

        # Scan PHP files
        php_tasks = [
            scan_js_file_direct(f, pattern, seen_js, f_log)
            for f in all_php
        ]
        if php_tasks:
            await asyncio.gather(*php_tasks)

        # Scan Python files
        py_tasks = [
            scan_js_file_direct(f, pattern, seen_js, f_log)
            for f in all_py
        ]
        if py_tasks:
            await asyncio.gather(*py_tasks)


# =========================
# CLI
# =========================

async def load_pattern(pattern_input):
    """Load pattern from file or use direct input"""
    expanded_path = os.path.expanduser(pattern_input)

    if os.path.isfile(expanded_path):
        async with aiofiles.open(expanded_path, "r", encoding="utf-8", errors="ignore") as f:
            content = await f.read()
            patterns = [
                line.strip()
                for line in content.split("\n")
                if line.strip() and not line.startswith("#")
            ]
            return patterns if patterns else [content.strip()]

    return [pattern_input]


def parse_args():
    p = argparse.ArgumentParser(
        description="jfl — Local JS pattern finder"
    )
    p.add_argument("target", help="Directory or file path (supports ~ and .)")
    p.add_argument("pattern", help="Regex pattern or file with patterns")
    return p.parse_args()


async def main():
    args = parse_args()
    patterns = await load_pattern(args.pattern)
    os.makedirs("jfl", exist_ok=True)
    log_path = "jfl/log.txt"

    # Clear old logs
    async with aiofiles.open(log_path, "w") as f:
        await f.write("")

    try:
        for pattern in patterns:
            print(f"[JFL] Scanning with pattern: {pattern}")
            await run(args.target, pattern)
    except KeyboardInterrupt:
        print("\n[JFL] Interrupted")
    except Exception as e:
        print(f"[!] Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
