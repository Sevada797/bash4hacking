import asyncio
import socket
import sys
import os
import argparse

COMMON_SUBS = [
    "www", "mail", "ftp", "smtp", "pop", "imap", "ns1", "ns2", "cpanel", "webmail", "localhost",
    "admin", "portal", "api", "test", "dev", "staging", "beta", "uat", "vpn", "secure", "server",
    "app", "mobile", "blog", "cdn", "m", "static", "web", "assets", "auth", "db", "sso", "docs",
    "support", "shop", "store", "video", "news", "media", "img", "images", "js", "css", "download",
    "uploads", "files", "pay", "payment", "checkout", "cart", "billing", "invoice", "order", "track",
    "account", "accounts", "my", "dashboard", "user", "users", "profile", "login", "logout", "register",
    "signup", "signin", "auth", "oauth", "id", "identity", "api1", "api2", "api3", "status", "health",
    "monitor", "monitoring", "log", "logs", "metrics", "graph", "analytics", "data", "db1", "db2",
    "database", "sql", "mysql", "mongo", "cache", "redis", "proxy", "cdn1", "cdn2", "cdn3", "cdn4",
    "edge", "origin", "node", "node1", "node2", "gw", "gateway", "router", "switch", "firewall",
    "net", "network", "static1", "static2", "uploads1", "uploads2", "cdn-static", "assets1", "assets2",
    "dev1", "dev2", "dev3", "test1", "test2", "test3", "qa", "qa1", "qa2", "stage", "prod", "production",
    "build", "builds", "ci", "cd", "jenkins", "git", "repo", "repos", "code", "source", "release",
    "beta1", "alpha", "alpha1", "patch", "old", "legacy", "v1", "v2", "v3", "v4", "new", "next", "future",
    "internal", "private", "public", "partner", "partners", "vendor", "vendors", "client", "clients",
    "customer", "customers", "crm", "erp", "hr", "help", "helpdesk", "zendesk", "freshdesk", "feedback",
    "forum", "community", "social", "facebook", "twitter", "linkedin", "youtube", "media1", "cdn-edge",
    "s1", "s2", "s3", "s4", "s5", "edge1", "edge2", "zone", "geo", "region", "country", "lang", "en",
    "us", "uk", "de", "fr", "es", "cn", "in", "ru", "br", "it", "jp", "kr", "ca", "au", "mx", "ar", "nz",
    "live", "livetest", "demo", "sandbox", "mock", "simulate", "testenv", "preprod", "gray", "canary",
    "ops", "infra", "service", "services", "task", "queue", "worker", "workers", "job", "jobs",
    "api-gateway", "api-auth", "api-data", "api-status", "api-login", "api-user", "api-internal",
    "db-main", "db-replica", "cache1", "cache2", "cache-main", "redis1", "redis2", "mongo1", "mongo2",
    "mysql1", "mysql2", "pg", "postgres", "pg1", "pg2", "noc", "it", "tech", "devops", "gitlab",
    "bitbucket", "jira", "confluence", "docs1", "docs2", "faq", "manual", "howto", "kb", "guide",
    "book", "blog1", "blog2", "press", "newsroom", "marketing", "ad", "ads", "tracking", "tag",
    "pixel", "events", "event", "promo", "offer", "deals", "sale", "discount", "gift", "aff", "affiliate",
    "ref", "refer", "referral", "contest", "survey", "poll", "vote", "qa-team", "qa-api", "ci-runner"
]


# Generate a-z{1,3}
def gen_short_subs():
    from itertools import product
    alphabet = 'abcdefghijklmnopqrstuvwxyz'
    for i in range(1, 3):
        for p in product(alphabet, repeat=i):
            yield ''.join(p)

# Async UDP resolve attempt
async def resolve(domain, sub):
    fqdn = f"{sub}.{domain}"
    try:
        await asyncio.get_event_loop().getaddrinfo(fqdn, 53, proto=socket.IPPROTO_UDP)
        #print(f"[+] Found: {fqdn}")
        print(f"{fqdn}")
    except:
        pass

async def run(domain):
    subs = list(gen_short_subs()) + COMMON_SUBS
    tasks = [resolve(domain, sub) for sub in subs]
    await asyncio.gather(*tasks)

def main():
    parser = argparse.ArgumentParser(description="Async UDP subdomain brute")
    parser.add_argument("-d", "--domain", help="Single domain to brute force")
    parser.add_argument("-f", "--file", help="File with list of domains (one per line)")
    args = parser.parse_args()

    if args.domain:
        asyncio.run(run(args.domain))
    elif args.file:
        with open(args.file) as f:
            domains = [line.strip() for line in f if line.strip()]
        for domain in domains:
            #print(f"\n[~] Brute forcing: {domain}")
            asyncio.run(run(domain))
    else:
        print("Usage: subr.py -d domain.com or -f domains.txt")

if __name__ == "__main__":
    main()
