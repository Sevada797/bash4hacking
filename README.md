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
bash setup.sh
```

## 🛠️ Tools available
Just run `menu` for this ;)

Also I provided screen

## Intrusive Thoughts
~~Should make this thing more structured + push not useful funcs in /archive (time 2 mkdir it) + add descriptions show up during menu(), mm, yeah defo would be better.
If you are perfectionist ahh person, just keep an eye on my repo :) defo I'll make it better day by day.~~

Kinda done, still some funcs now may lack requiremenets, I may fix that also sooner or later.

##Todo

Create 

1. paramverse (useful in case by case basis, there are apps, that just even if one param is smth else then default, page won't load :| like in transactional pages,
so instead of qsreplace which replaces all, I'll do replace each by time , so from 1 url that has 5 params, will be created 5 urls :D ), 

2. paramcut (basically just loop in all params then grep $i urls, then leave one sample for each ),

3. danalyst (should look for json data in URLs and play with them, inject XSS if url found in value replace url analyze things.. further maybe do same for base64 encoded jsons and just b64 data in urls, m64 will help here :) ),

4. pthunt (path traversal hunter)

What else.. uh, gotta remain creative as a hunter u know


### Useful?
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-donate-orange?style=flat&logo=buy-me-a-coffee)](https://buymeacoffee.com/zatikyansed)
