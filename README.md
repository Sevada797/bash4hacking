# bash4hacking
![Demopic](https://github.com/Sevada797/bash4hacking/blob/main/assets/BFH.png?raw=true)
Set of scripts that will be useful for bug hunters.<br>
Some of the scripts are helpful for "data analysis" kinda.<br>
Read  `Instalation` for installation

## 🔧 Installation

Clone the repo and run the setup:

```bash
git clone https://github.com/sevada797/bash4hacking.git
cd bash4hacking
bash setup.sh  # setup for auto-sourcing functions via ~/.bashrc or ~/.zshrc (2nd not well tested on)
bash install-requirements.sh
```

#### Explanations short:
1. bash setup.sh - setup for auto-sourcing functions via ~/.bashrc or ~/.zshrc (2nd not well tested on)
2. bash install - requirements.sh - install binaries that are used and some python libraries

## 🛠️ Tools available
Just run `menu` for this ;)

Also I provided screen

## Intrusive Thoughts
~~Should make this thing more structured + push not useful funcs in /archive (time 2 mkdir it) + add descriptions show up during menu(), mm, yeah defo would be better.
If you are perfectionist ahh person, just keep an eye on my repo :) defo I'll make it better day by day.~~

Kinda done, still some funcs now may lack requiremenets, I may fix that also sooner or later.

## Todo

### Change

In crawl -> add option to not crawl any logout URLs -> Sessioned crawl will get interrupted

Maybe ~ export all output files in export_b4_variables() , for better management/tracking of the output files, e.g. axss()->$axss_out

Make 'menu combos' better, add only practical combos.

Requirements fix, and maybe even have tracking file

Zsh support still sucks, Install zsh -> check the tool on zsh for all possible problems, and make syntax-es both ways bash/zsh compatible

### Create 

jsmap() - should visit JS files, get paths, then map to original url, get uniques by comparing with common crawl (this would be optional but useful very, and recommended),
then fuzz, and remove 404 or static same size >50 etc..

modsubs() - should do from found subs clever prefix shuffle->dns probe, to find more subs


2. paramverse (useful in case by case basis, there are apps, that just even if one param is smth else then default, page won't load :| like in transactional pages,
so instead of qsreplace which replaces all, I'll do replace each by time , so from 1 url that has 5 params, will be created 5 urls :D ), 

3. danalyst (should look for json data in URLs and play with them, inject XSS if url found in value replace url analyze things.. further maybe do same for base64 encoded jsons and just b64 data in urls, m64 will help here :) ),



What else.. uh, gotta remain creative as a hunter u know


### Useful?
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-donate-orange?style=flat&logo=buy-me-a-coffee)](https://buymeacoffee.com/zatikyansed)
