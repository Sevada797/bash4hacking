import socket
import ssl
import sys
import concurrent.futures

def get_cn_from_cert(hostname):
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=3) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                subject = dict(x[0] for x in cert['subject'])
                cn = subject.get('commonName', None)
                return hostname, cn
    except Exception:
        return hostname, None

def load_targets(path):
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]

def main(filename):
    domains = load_targets(filename)
#    print("[*] Scanning for SSL CNs from dead subs...\n")

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(get_cn_from_cert, d): d for d in domains}
        for future in concurrent.futures.as_completed(futures):
            domain, cn = future.result()
            if cn:
#                print(f"[+] {domain} -> CN: {cn}")
                print(f"{cn}")
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 subs443.py domains.txt")
        sys.exit(1)
    main(sys.argv[1])
