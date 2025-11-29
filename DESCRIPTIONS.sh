#!/bin/bash

# Descriptions for bash4hacking functions (exactly matching your real scripts)

shadowdom_desc() {
echo "Get 200 status URLs downloaded from wayback machine, then use shadowfind() to grep thing and get according URLs "
}

shadowfind_desc() {
echo "Helper for shadowdom(), greps->gets URLs exact where there is a match "
}

op_desc() {
echo "for XSS checks again, visiting urls, getting json object keys and making params from them, then so we can test further"
}

falfa_desc() {
echo "Just double fuzzes subs list with ffuf with alpha1-2.txt -e .php,.html"
}

falfa2_desc() { 
echo "Just double fuzzes subs list with ffuf with alpha3-4.txt no -e sinc wlist is long, although maybe better do falfa2 on URLs since it'll take longer"
}

ai_desc() {
echo "Simple AI hacking assistant from CLI (export your OPENAI_API_KEY in ~/.bashrc)"
}

usubs_desc() {
echo "Use me after axss() or asubs() only, to get more subs ;D (I hate typing long, so no args here :3)"
}

cors_desc() {
echo "COOL!NEW! This my tool checks for CORS misconfigs :D and logs sus/interesting headers in 'cors_finds' file"
}

epaths_desc() {
echo "This also can be quite useful, like if you wanna quick check main existing paths, especially 1st level, to quick check or focus on functionalities and other stuff, e.g. CORS misconfig hunt, or idk etc."
}

crawl_desc() {
echo "NEW! my cool crawler, it has per-depth timeout, bad patterns filtering a bit, and other smart filtering features"
}

pxss_desc() {
echo "NEW! checks for directly params reflection with '\"> after paths() 1,2,3"
}

pxss2_desc() {
echo "less chance to hit, checks for directly paths reflection after paths() 1 & 2 with '\"> "
}

bp_desc() {
echo "Prints header based bypass for curling"
}

more200_desc() {
echo "COOL! USEFUL+NEW! It gets 200 codes after following 3xx sc subs, auto in scope filter exists! STORY_BEHIND: I thought what are we missing, maybe during httpx -mc 200.. and thought this idea :) "
}

inj_desc() {
echo "USEFUL! (I binded this with Alt+I but not applied here that yet), echoes injections I use in register inputs"
}

digger_desc() {
echo "NEW! Header dumping for given URLs, if providing subs provide in URL format"
}

gsubs_desc() {
echo "NEW! COOL! Provide a list of subs, it detects domains, and for each domain provides dork, not including subs for that current domain."
}

br_desc() {
echo "ULTIMATE BRUTER, craft HTTP req from 0 inject where needed FUZZ/BUZZ/CUZZ/DUZZ ~ auto detection of any kind of anomaly using headers size(hsize),words,lines,rsize after performing What to Rely on"
}

fsubs_desc() {
echo "COOL! Fuzz subs - double fuzzing for directory discovery, discover what's in these subs!"
}

deadsubs_desc() {
echo "Should've collect deadsubs, but maybe I messed smth here"
}

sto_desc() {
echo "Subdomain takeover checker -- No luck hunting STO yet ~_~"
}

longsubr2_desc() {
echo "Brute subdomains - Takes a day, smart filter for 5 letter combos, removed 3 consequent vowels and consonants + removed 2 repetitive consequent letters"
}

longsubr_desc() {
echo "COOL! SLOW! Brute subdomains - Takes some 1-2 hours if you scan one domain, tests alfa3-4 + list from danielmiessler/SecLists"
}

phones_desc() {
echo "Greps possible phone number patterns"
}

p2_desc() {
echo "Automatically check for p2 leakage via id/uuid/md5 + other greps & hf"
}

xml_desc() {
echo "Checking for xml acceptance on subs"
}

uuid_desc() {
echo "Greps uuid patterns"
}

freg_desc() {
echo "Fuzz possible register endps"
}

lql_desc() {
echo "Test for times based SQL injections"
}

pcut_desc() {
echo "EAGLE VISION! Cut all urls, after looping for each param from given params list, and grepping out them and after each using '| head -n<amount_you_choose>'"
}

lsubs_desc() {
echo "Give subs list and get 4 files, live subs and status code 200 subs, with and without 'https://' prefix"
}

reptile_desc() {
echo "COOL! Same as HF just uses headless browser from playwright"
}

fcheck_desc() {
echo "Provide file link, it downloads and does exif + first lines hexdump, so you can know the file processors of target"
}

fuzz_desc() {
echo "Just does fuzz, I created it for using after ssrfhunt"
}

ssrfgen_desc() {
echo "Greps out possible to ssrf links"
}

ssrfhunt_desc() {
echo "Replaces all occurencies of possible path/link param values with your hook"
}

rocket_desc() {
echo "COOL! Drops maximum amount of same lengthed data (URLs)"
}

depo_desc() {
echo "Checks for possible dependency confusion RCE in node"
}

subsubs2_desc() {
echo "NOT BAD! Again for pulling unique new subs from existing subs, but this time from headers, since CSP can point to smth interesting (e.g. allow-origin)"
}

filter_desc() {
echo "SLOW! This function is super helpfull (and slow haha), but you can defo run it on like 100K urls to get filtered unique ones based on static_percent"
}

gapi_desc() {
echo "Checks google API key in several paid API endpoints"
}

mails_desc() {
echo "Grep -ao mail patterns."
}

asubs_desc() {
  echo "Find active subdomains using assetfinder, subfinder, subr, and httpx. Also checks CNs of dead subs."
}

axss_desc() {
  echo "COOL! Automated XSS prep: gathers subs, collects URLs with wayback/katana, extracts params, prepares for gbr scan."
}

bxss_desc() {
  echo "COOL! Generate pre-made Blind XSS payloads for a given program name + webhook.site endpoint."
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
  echo "COOL! BUT for non BB programs mostly! Automated ffuf scan for sensitive file leaks using a domain list and SENSITIVE dir."
}

f2_desc() {
  echo "DIG MORE, MAYBE SMTH! Fast subdomain port scanner with naabu + httpx. Supports full port mode."
}

filip_desc() {
  echo "COOL! grep leak or Found after, Detect technologies and possibly leaked files by matching known patterns in URL lists."
}

frames_desc() {
  echo "KINDA COOL! Generates a paginated HTML file with iframes to preview subdomains visually."
}

gqli_desc() {
  echo "Sends introspection queries to GraphQL endpoints and pretty prints schema with jq."
}

gr_desc() {
  echo "COOL! Wrapper for gecko.py , follows redirs and logs em, also has filter, easy use also for open-redir finding after rr()."
}

hf_desc() {
  echo "COOL! Powerful reflection finder using Python. Accepts filters, headers, and user agents."
}

kage_desc() {
  echo "COOL! Check Wayback Machine for archived versions of single or multiple URLs with 200 Status Code."
}

links_desc() {
  echo "USEFUL! Extracts full links (http/https) that match a domain from files or stdin."
}
m64_desc() { echo " USEFUL! Generate minimal base64 variants of a string and optionally grep them from file."; }

mdd_desc() { echo "Grep for MD5 hashes (32-char hex) from a file."; }

menu_desc() { echo "Show list of available BFH functions and check for updates."; }

moreparams_desc() { echo "Fetch HTML pages from targets and extract unique input names."; }

orgen_desc() { echo "Generate open redirect payloads using common parameters."; }

params_desc() { echo "Extract unique GET parameter names from URLs."; }

paths_desc() { echo "Extract and reconstruct paths from URL lists with filtering options."; }

ports_desc() { echo "Extract unique open ports from a file, excluding 80 and 443."; }

robots_desc() { echo "Fetch robots.txt from subdomains and extract disallowed paths and clean-param directives."; }

rr_desc() { echo "USEFUL! Filter possible open redirect URLs and prepare them for quick testing."; }

scream_desc() { echo "Scan file for sensitive keywords like admin, login, token, etc."; }

sslcon_desc() { echo "Perform raw SSL connection using openssl s_client."; }

subr_desc() { echo "Run passive subdomain enumeration using subr.py script."; }

subs_desc() { echo "Extract subdomains matching given domain from file or stdin."; }

subs443_desc() { echo "Check dead subs CN, to get other subdomains."; }

subsubs_desc() { echo "Use gospider to crawl existing subs and extract unseen subdomains."; }

updatebfh_desc() { echo "Pull latest version of BFH toolset and reload shell environment."; }
