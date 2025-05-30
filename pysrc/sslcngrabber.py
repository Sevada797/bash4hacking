import asyncio
import ipaddress
import ssl
import socket
from cryptography import x509
from cryptography.hazmat.backends import default_backend

# 🧠 extract CN and SANs from cert
def extract_domains(cert_der):
    cert = x509.load_der_x509_certificate(cert_der, default_backend())
    domains = []

    # CN
    try:
        cn = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
        domains.append(cn)
    except Exception:
        pass

    # SANs
    try:
        ext = cert.extensions.get_extension_for_oid(x509.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
        sans = ext.value.get_values_for_type(x509.DNSName)
        domains.extend(sans)
    except Exception:
        pass

    return set(domains)

# ⚡ async ssl grabber
async def grab_cert(ip):
    try:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, 443, ssl=ssl_ctx), timeout=2
        )

        cert_bin = writer.get_extra_info('ssl_object').getpeercert(True)
        domains = extract_domains(cert_bin)
        writer.close()
        await writer.wait_closed()

        if domains:
            print(f"[+] {ip} --> {domains}")
            return ip, domains
    except:
        return None

# 🧠 generate all IPs from CIDR
def generate_ips(cidr):
    return [str(ip) for ip in ipaddress.ip_network(cidr)]

# 🎯 run all tasks
async def main(cidr):
    ip_list = generate_ips(cidr)
    tasks = [grab_cert(ip) for ip in ip_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    found = []
    for res in results:
        if res and isinstance(res, tuple):
            found.append(res)

    # Save results
    with open("found_domains.txt", "w") as f:
        for ip, domains in found:
            for d in domains:
                f.write(f"{ip} -> {d}\n")

    print(f"\n✅ Done! {len(found)} IPs with cert domains saved to found_domains.txt")

# 👉 Start here
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python sslcngrabber.py <CIDR>")
        print("Example: python sslcngrabber.py 81.19.64.0/19")
        exit()

    asyncio.run(main(sys.argv[1]))
