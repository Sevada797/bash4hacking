# bash4hacking
Set of scripts that will be useful for bug hunters.<br>
Some of the scripts are helpful for "data analysis" kinda.<br>
Read  `Instalation` for installation

## 🔧 Installation

Clone the repo and run the setup:

```bash
git clone https://github.com/sevada797/bash4hacking.git
cd bash4hacking
bash setup.sh
```

## 🛠️ Tools available
### 1) HF (HTTP find)
This bash code will look our given value, and look it in all HTTP responses that we got from urls, in other words if our given values are reflected in list of urls.

> Usage: hf <file_with_urls\> <value\> (--ua-chrome) (--burp)


### 2) HHI (HTTP headers inspector)
This bash code will look for any kind of bad or interesting for us headers like `X-Frame-Options: allow`  or  `Access-Control-Allow-Origin: *`. (Coming soon)

### 3) m64
Tool for giving you the 3 possible minimal substrings of base64 encoded text 

> Usage: m64  \<string\>  or m64 \<string\> \<file\>

### 4) subs
Exfiltrate subdomains from fetched urls
this will get you all subdomains of that domain (you can use it after amass scan for exmaple haha)

> Usage: subs  \<domain\>  \<file\>

### 5) lsubs
filters out the subdomains that give 200 status and outs in subs200 file

> Usage: lsubs \<file\>

### 6) params
Will get you all parameters from a list of urls 

> Usage: params \<file\>

### 7) mdd
Will detect md5 in a list of urls for example

> Usage: mdd \<file\>

## 8) kagefuzz
fuzzes sensitive paths in wayback and checks for availibility

> Usage: kagefuzz \<file-with-domains\>

## 9) gr
Resolves and follows all redirects in the given list of URLs.
If a second argument is provided, it filters and prints only the final URLs containing that substring.
Useful for catching internal redirectors (or you can weaponize it for open redirect hunting hehe 😈️)

> Usage: gr <url-file> [filter-substring]

## 10) mygitleaks
Loops and checkouts all commit hashes, after greps entire dir for sensitive info (feel free to contribute in grep match-string)
(OK there seems to be a better one already 😅️ here  [gitleaks](https://github.com/gitleaks/gitleaks) I renamed to mygitleaks for no conflict)
> Usage: mygitleaks \<local-path-or-git-url\> [branch-to-return-to]

## 11) links
links extractor
> Usage: links <domain> [file]

## 12) robots
provide subs list and it fetches all robots.txt and from there
it gathers for you paths and parameters (parameters only from keys like Clean-param)
> Usage robots \<subdomains-file\>

## 13) orgen 
generates a list of possbile open redirects from a subdomain list
>Usage: gen_open_redirect_payloads \<url | file_with_urls\>
Example:
  gen_open_redirect_payloads https://target.com
  gen_open_redirect_payloads urls.txt




### Useful?
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-donate-orange?style=flat&logo=buy-me-a-coffee)](https://buymeacoffee.com/zatikyansed)
