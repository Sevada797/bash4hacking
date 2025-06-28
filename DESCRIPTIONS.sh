#!/bin/bash

# Descriptions for bash4hacking functions (exactly matching your real scripts)
mails_desc() {
echo "Grep -ao mail patterns."
}

asubs_desc() {
  echo "Find active subdomains using assetfinder, subfinder, subr, and httpx-go. Also checks CNs of dead subs."
}

axss_desc() {
  echo "Automated XSS prep: gathers subs, collects URLs with wayback/katana, extracts params, prepares for gbr scan."
}

bxss_desc() {
  echo "Generate pre-made Blind XSS payloads for a given program name + webhook.site endpoint."
}

collect_desc() {
  echo "Curls URLs from stdin or file and saves HTML with randomized filenames per domain."
}

dj_desc() {
  echo "Filters out static file types from stdin or file input. Helps clean URL lists."
}

dork_desc() {
  echo "Google and DuckDuckGo dork generator for domains using intext:\"index of /\"."
}

f1_desc() {
  echo "Automated ffuf scan for sensitive file leaks using a domain list and SENSITIVE dir."
}

f2_desc() {
  echo "Fast subdomain port scanner with naabu + httpx. Supports full port mode."
}

filip_desc() {
  echo "Detect technologies and possibly leaked files by matching known patterns in URL lists."
}

frames_desc() {
  echo "Generates a paginated HTML file with iframes to preview subdomains visually."
}

gqli_desc() {
  echo "Sends introspection queries to GraphQL endpoints and pretty prints schema with jq."
}

gr_desc() {
  echo "Wrapper for gecko.py that filters or parses URL files for reflection-based recon."
}

hf_desc() {
  echo "Powerful param reflection tester using Python. Accepts filters, headers, and user agents."
}

kage_desc() {
  echo "Check Wayback Machine for archived versions of single or multiple URLs."
}

links_desc() {
  echo "Extracts full links (http/https) that match a domain from files or stdin."
}
m64_desc() { echo "Generate minimal base64 variants of a string and optionally grep them from file."; }

mdd_desc() { echo "Grep for MD5 hashes (32-char hex) from a file."; }

menu_desc() { echo "Show list of available BFH functions and check for updates."; }

moreparams_desc() { echo "Fetch HTML pages from targets and extract unique input names."; }

orgen_desc() { echo "Generate open redirect payloads using common parameters."; }

params_desc() { echo "Extract unique GET parameter names from URLs."; }

paths_desc() { echo "Extract and reconstruct paths from URL lists with filtering options."; }

ports_desc() { echo "Extract unique open ports from a file, excluding 80 and 443."; }

robots_desc() { echo "Fetch robots.txt from subdomains and extract disallowed paths and clean-param directives."; }

rr_desc() { echo "Filter possible open redirect URLs and prepare them for quick testing."; }

scream_desc() { echo "Scan file for sensitive keywords like admin, login, token, etc."; }

sslcon_desc() { echo "Perform raw SSL connection using openssl s_client."; }

subr_desc() { echo "Run passive subdomain enumeration using subr.py script."; }

subs_desc() { echo "Extract subdomains matching given domain from file or stdin."; }

subs443_desc() { echo "Check which subdomains are alive over port 443 using Python script."; }

subsubs_desc() { echo "Use gospider to crawl existing subs and extract unseen subdomains."; }

updatebfh_desc() { echo "Pull latest version of BFH toolset and reload shell environment."; }
