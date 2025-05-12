# bash4hacking
Set of scripts that will be useful for bug hunters
for using any of the scripts run ```source <filename>```
for pernamently making autoload the script add the ```source <filename>``` line
in ```~/.bashrc``` file, make sure you do this with absolute path

# Tools available
## 1) HF (HTTP find)
This bash code will look our given value, and look it in all HTTP responses that we got from urls, in other words if our given values are reflected in list of urls.

> Usage: hf <file_with_urls\> <value\> (--ua-chrome) (--burp)


## 2) HHI (HTTP headers inspector)
This bash code will look for any kind of bad or interesting for us headers like `X-Frame-Options: allow`  or  `Access-Control-Allow-Origin: *`. (Coming soon)

## 3) m64
Tool for giving you the 3 possible minimal substrings of base64 encoded text 

> Usage: m64  \<string\>  or m64 \<string\> \<file\>

## 4) subs
Exfiltrate subdomains from fetched urls

> Usage: subs  \<domain\>  \<file\>
this will get you all subdomains of that domain (you can use it after amass scan for exmaple haha)

## 5) lsubs

> Usage: lsubs \<file\>
filters out the subdomains that give 200 status and outs in subs200 file

## 6) params

> Usage: params \<file\>
will get you all parameters from a list of urls 

## 7) mdd

> Usage: mdd \<file\>
will detect md5 in a list of urls for example




## Useful?
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-donate-orange?style=flat&logo=buy-me-a-coffee)](https://buymeacoffee.com/zatikyansed)
