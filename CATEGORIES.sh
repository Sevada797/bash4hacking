#!/bin/bash

# Categories: 
# DATA_ANALYSIS
# FUZZING
# ENUMERATION
# XSS
# CRAWLING
# ACTION
# OTHER

# Tool category definitions

cors_category() { echo "ACTION DRIVEN TESTING"; }
cors2_category() { echo "ACTION DRIVEN TESTING"; }
hf_category() { echo "ACTION DRIVEN TESTING"; }
reptile_category() { echo "ACTION DRIVEN TESTING"; }
kage_category() { echo "ACTION DRIVEN TESTING"; }
shadowdom() { echo "ACTION DRIVEN TESTING"; }
shadowfind() { echo "ACTION DRIVEN TESTING"; }
gqli_desc()  { echo "ACTION DRIVEN TESTING"; }


crawl_category() { echo "Advanced Crawling"; }
ghost_category() { echo "Advanced Crawling"; }



links_category() { echo "PURE DATA_ANALYSIS SMART GREPS ETC... (some prepare files for further testing)"; }
filip_category() { echo "PURE DATA_ANALYSIS SMART GREPS ETC... (some prepare files for further testing)"; }
paths_category() { echo "PURE DATA_ANALYSIS SMART GREPS ETC... (some prepare files for further testing)"; }
epaths_category() { echo "PURE DATA_ANALYSIS SMART GREPS ETC... (some prepare files for further testing)"; }
params_category() { echo "PURE DATA_ANALYSIS SMART GREPS ETC... (some prepare files for further testing)"; }
pcut_category() { echo "PURE DATA_ANALYSIS SMART GREPS ETC... (some prepare files for further testing)"; }
m64_category() { echo "PURE DATA_ANALYSIS SMART GREPS ETC... (some prepare files for further testing)"; }
mdd_category() { echo "PURE DATA_ANALYSIS SMART GREPS ETC... (some prepare files for further testing)"; }
uuid_category() { echo "PURE DATA_ANALYSIS SMART GREPS ETC... (some prepare files for further testing)"; }
ports_category() { echo "PURE DATA_ANALYSIS SMART GREPS ETC... (some prepare files for further testing)"; }
mails_category() { echo "PURE DATA_ANALYSIS SMART GREPS ETC... (some prepare files for further testing)"; }
phones_category() { echo "PURE DATA_ANALYSIS SMART GREPS ETC... (some prepare files for further testing)"; }
scream_category() { echo "PURE DATA_ANALYSIS SMART GREPS ETC... (some prepare files for further testing)"; }


fsubs_category() { echo "FUZZING"; }
falfa_category() { echo "FUZZING"; }
falfa2_category() { echo "FUZZING"; }
f1_category() { echo "FUZZING"; }
freg_category() { echo "FUZZING"; }

fuzz_category() { echo "PROBING (ffuf/httpx)"; }
lsubs_category() { echo "PROBING (ffuf/httpx)"; }


asubs_category() { echo "SUBS_RECON"; }
gsubs_category() { echo "SUBS_RECON"; }
subs_category() { echo "SUBS_RECON"; }
subr_category() { echo "SUBS_RECON"; }
usubs_category() { echo "SUBS_RECON"; }
subsubs_category() { echo "SUBS_RECON"; }
subsubs2_category() { echo "SUBS_RECON"; }
longsubr_category() { echo "SUBS_RECON"; }
longsubr2_category() { echo "SUBS_RECON"; }
pivot_category() { echo "SUBS_RECON"; }


formxss_category() { echo "XSS"; }
pxss_category() { echo "XSS"; }
pxss2_category() { echo "XSS"; }
axss_category() { echo "XSS"; }
bxss_category() { echo "XSS"; }
op_category() { echo "XSS"; }
arjunxss_category() { echo "XSS"; }


lql_category() { echo "SQL injection - Should remove I think, or repair, cause rn idk it just doesn't hit "; }

br_category() { echo "BRUTING"; }

sto_category() { echo "USELESS or UNEFFECTIVE IRL CASES (I may drop them to archive soon)"; }
p2_category() { echo "USELESS or UNEFFECTIVE IRL CASES (I may drop them to archive soon)"; }



# Default: if no category defined
default_category() { echo "OTHER"; }
