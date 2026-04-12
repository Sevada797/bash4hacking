#!/usr/bin/env python3
"""
sproxy.py — session-injecting MITM HTTP/HTTPS proxy.

- Injects cookies from ~/.sessme/SESSION.json by Host header
- Full MITM TLS via ~/.sproxy/ca.crt — reads plaintext on both sides
- Handles plain HTTP and HTTPS (CONNECT) transparently
- Follows redirects internally including http→https upgrades
- Tools talk plain HTTP or HTTPS to proxy on 127.0.0.1:7797
- CA generated once by the sproxy() bash wrapper

Usage:
  python3 sproxy.py          # quiet mode — only injection logs
  python3 sproxy.py --debug  # full hexdump of all traffic
"""

import socket
import ssl
import threading
import json
import re
import os
import sys
import datetime
import tempfile
import ipaddress

from concurrent.futures import ThreadPoolExecutor

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.primitives.serialization import load_pem_private_key


from curl_cffi import requests as cffi_requests


def do_request_cffi(method, host, port, path, injector, extra_headers=b"", body=b""):
    url = f"https://{host}{path}" if port == 443 else f"http://{host}:{port}{path}"
    raw_req = build_request(method, path, host, extra_headers, body)
    injected = injector.inject(raw_req)
    
    # Parse injected headers back out for cffi
    hdr_block = injected.split(b"\r\n\r\n", 1)[0]
    headers = {}
    for line in hdr_block.split(b"\r\n")[1:]:
        if b":" in line:
            k, v = line.split(b":", 1)
            headers[k.decode().strip()] = v.decode().strip()
    
    resp = cffi_requests.request(
        method,
        url,
        headers=headers,
        data=body or None,
        impersonate="chrome131",  # spoof Chrome TLS fingerprint
        allow_redirects=True,
        timeout=30,
    )
    
    # Reconstruct raw HTTP response
    status_line = f"HTTP/1.1 {resp.status_code} OK\r\n".encode()
    resp_headers = b"".join(f"{k}: {v}\r\n".encode() for k, v in resp.headers.items())
    return status_line + resp_headers + b"\r\n" + resp.content


def recv_until_headers_complete(sock):
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(65535)
        if not chunk:
            break
        data += chunk
    return data

LISTEN_HOST   = "127.0.0.1"
LISTEN_PORT   = 7797
SESSION_PATH  = os.path.join(os.path.expanduser("~"), ".sessme", "SESSION.json")
CA_DIR        = os.path.join(os.path.expanduser("~"), ".sproxy")
CA_CERT_PATH  = os.path.join(CA_DIR, "ca.crt")
CA_KEY_PATH   = os.path.join(CA_DIR, "ca.key")
MAX_REDIRECTS = 10

DEBUG = "--debug" in sys.argv

PROXY_THREAD_WORKERS = 500


# ── Debug helpers ─────────────────────────────────────────────────────────────

def hexdump(data: bytes, label: str = ""):
    if not DEBUG:
        return
    if label:
        print(f"[hexdump] ── {label} ({len(data)} bytes) ──")
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_part   = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 0x20 <= b < 0x7f else "." for b in chunk)
        print(f"  {i:04x}  {hex_part:<48}  |{ascii_part}|")
    print()


def log_headers(data: bytes, label: str = ""):
    """Print just the HTTP headers section, skipping body. Always shown in debug."""
    if not DEBUG:
        return
    try:
        headers_raw = data.split(b"\r\n\r\n", 1)[0]
        print(f"[headers] ── {label} ──")
        for line in headers_raw.split(b"\r\n"):
            print(f"  {line.decode(errors='replace')}")
        print()
    except Exception:
        pass


def dbg(msg: str):
    if DEBUG:
        print(f"[debug] {msg}")


# ── CA Loader ─────────────────────────────────────────────────────────────────

def load_ca():
    with open(CA_CERT_PATH, "rb") as f:
        ca_cert = load_pem_x509_certificate(f.read())
    with open(CA_KEY_PATH, "rb") as f:
        ca_key = load_pem_private_key(f.read(), password=None)
    return ca_cert, ca_key


# ── Per-host cert generator ───────────────────────────────────────────────────

def generate_cert_for_host(host, ca_cert, ca_key):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, host)])
    try:
        san = x509.SubjectAlternativeName([
            x509.IPAddress(ipaddress.ip_address(host))
        ])
    except ValueError:
        san = x509.SubjectAlternativeName([x509.DNSName(host)])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
        .add_extension(san, critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    return cert, key


# ── Cookie Injector ───────────────────────────────────────────────────────────

class CookieInjector:
    def __init__(self, path=SESSION_PATH):
        self.path = path
        self.sessions = self._load()

    def _load(self):
        try:
            with open(self.path) as f:
                data = json.load(f)
            print(f"[sproxy] sessions loaded: {len(data)} domains")
            return data
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"[sproxy] WARNING: could not load sessions: {e}")
            return {}

    def reload(self):
        self.sessions = self._load()

    def _match(self, host):
        host = host.lower()
        for domain, cookies in self.sessions.items():
            if host == domain:
                #print("Faqqq, "+str(host)+"::"+str(domain))
                return cookies
        return None

    def inject(self, raw: bytes) -> bytes:
        """
        Inject session cookies into a raw HTTP request (bytes).
        Works on both plain HTTP and decrypted MITM HTTPS traffic.
        Returns raw unchanged if no matching session found.
        """
        # must look like an HTTP request — skip TLS/binary blobs
        if not raw or raw[0] not in b"GPHDBOCPTU":  # GET POST HEAD DELETE etc
            return raw

        try:
            headers_raw, body = raw.split(b"\r\n\r\n", 1)
        except ValueError:
            return raw

        lines = headers_raw.split(b"\r\n")
        host       = None
        cookie_idx = None

        for i, line in enumerate(lines):
            low = line.lower()
            if low.startswith(b"host:"):
                host = line.split(b":", 1)[1].strip().decode(errors="replace")
                # strip port if present
                host = host.split(":")[0]
                lines[i] = b"Host: " + host.encode()   # This for fixing "Host header with port" bug
            if low.startswith(b"cookie:"):
                cookie_idx = i

        if not host:
            return raw

        session_cookie = self._match(host)
        if not session_cookie:
            dbg(f"no session for {host} — not injecting")
            return raw

        if cookie_idx is not None:
            #existing = lines[cookie_idx].split(b":", 1)[1].strip().decode()
            #merged   = existing + "; " + session_cookie
            #lines[cookie_idx] = b"Cookie: " + merged.encode()
            # LATER fix merging cookies
            lines[cookie_idx] = b"Cookie: " + session_cookie.encode()
        else:
            lines.append(b"Cookie: " + session_cookie.encode())
        #lines.append(b"Bash4hacking: cookie_injector")  ## for debugging and making sure header modification happens we can 
        # uncomment this
                # override User-Agent to Chrome
        CHROME_UA = b"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ua_idx = None
        for i, line in enumerate(lines):
            if line.lower().startswith(b"user-agent:"):
                ua_idx = i
                break
        if ua_idx is not None:
            lines[ua_idx] = b"User-Agent: " + CHROME_UA
        else:
            lines.append(b"User-Agent: " + CHROME_UA)
        # in inject(), after UA override
        accept_idx = None
        for i, line in enumerate(lines):
            if line.lower().startswith(b"accept:"):
                accept_idx = i
                break
        if accept_idx is not None:
            lines[accept_idx] = b"Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        else:
            lines.append(b"Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8")


        injected = b"\r\n".join(lines) + b"\r\n\r\n" + body
        if DEBUG:
            print(f"[sproxy] ✓ cookies injected for {host}")
            log_headers(injected, f"after injection → {host}")
        return injected


# ── Remote connection helpers ─────────────────────────────────────────────────

def open_connection(host, port, timeout=120):
    raw = socket.create_connection((host, port), timeout=timeout)
    raw.settimeout(timeout)
    if port == 443:
        ctx = ssl.create_default_context()
        return ctx.wrap_socket(raw, server_hostname=host)
    return raw


def recv_full_response(sock, timeout=20):
    sock.settimeout(timeout)   # ← add this line at the top
    data = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk

        if b"\r\n\r\n" not in data:
            continue

        header_part, body = data.split(b"\r\n\r\n", 1)

        cl_match = re.search(rb"content-length:\s*(\d+)", header_part, re.IGNORECASE)
        if cl_match:
            expected = int(cl_match.group(1))
            while len(body) < expected:
                more = sock.recv(4096)
                if not more:
                    break
                body += more
            return header_part + b"\r\n\r\n" + body

        te_match = re.search(rb"transfer-encoding:\s*chunked", header_part, re.IGNORECASE)
        if te_match:
            while not body.rstrip().endswith(b"0\r\n\r\n"):
                more = sock.recv(4096)
                if not more:
                    break
                body += more
            return header_part + b"\r\n\r\n" + body

        status_match = re.match(rb"HTTP/[\d.]+ (\d+)", header_part)
        if status_match:
            code = int(status_match.group(1))
            if code in (204, 304) or data.startswith(b"HTTP") and b"Content-Length: 0" in header_part:
                return data

        break

    while True:
        more = sock.recv(4096)
        if not more:
            break
        data += more
    return data


def parse_status(response: bytes):
    match = re.match(rb"HTTP/[\d.]+ (\d+)", response)
    return int(match.group(1)) if match else 0


def parse_location(response: bytes):
    match = re.search(rb"\r\nLocation:\s*(.+)\r\n", response, re.IGNORECASE)
    return match.group(1).strip().decode() if match else None


def parse_location_parts(location: str):
    if location.startswith("https://"):
        rest = location[8:]
        scheme, port = "https", 443
    elif location.startswith("http://"):
        rest = location[7:]
        scheme, port = "http", 80
    else:
        return None, None, None, location

    host_part, _, path = rest.partition("/")
    path = "/" + path if path else "/"

    if ":" in host_part:
        host, p = host_part.rsplit(":", 1)
        port = int(p)
    else:
        host = host_part

    return scheme, host, port, path


def build_request(method, path, host, extra_headers=b"", body=b""):
    req  = f"{method} {path} HTTP/1.1\r\n".encode()
    req += f"Host: {host.split(':')[0]}\r\n".encode()
    req += b"Connection: keep-alive\r\n"
    if extra_headers:
        req += extra_headers
    req += b"\r\n"
    req += body
    return req


# ── Core request sender (plain HTTP or TLS upstream) ─────────────────────────

def do_request(method, host, port, path, injector,
               extra_headers=b"", body=b"", redirect_count=0):
    if redirect_count > MAX_REDIRECTS:
        return b"HTTP/1.1 508 Loop Detected\r\n\r\nToo many redirects"

    raw_req = build_request(method, path, host, extra_headers, body)
    log_headers(raw_req, f"REQUEST before inject → {host}:{port}{path}")

    raw_req = injector.inject(raw_req)
    log_headers(raw_req, f"REQUEST after inject → {host}:{port}{path}")
    hexdump(raw_req, f"REQUEST bytes → {host}:{port}{path}")

    try:
        sock = open_connection(host, port)  # timeout=120 baked in now
        sock.sendall(raw_req)
        # sock.settimeout(30) was here — now it's already set in open_connection
        response = recv_full_response(sock)
        sock.close()
    except Exception as e:
        return f"HTTP/1.1 502 Bad Gateway\r\n\r\n{e}".encode()

    log_headers(response, f"RESPONSE from {host}:{port}{path}")
    hexdump(response, f"RESPONSE bytes from {host}:{port}{path}")

    status = parse_status(response)

    if status in (301, 302, 303, 307, 308):
        location = parse_location(response)
        if not location:
            return response

        scheme, new_host, new_port, new_path = parse_location_parts(location)

        if new_host is None:
            new_host, new_port = host, port

        print(f"[sproxy] redirect {status} → {location}")

        next_method = method if status in (307, 308) else "GET"
        next_body   = body   if status in (307, 308) else b""

        return do_request(next_method, new_host, new_port, new_path,
                          injector, extra_headers, next_body,
                          redirect_count + 1)

    return response


# ── MITM TLS handler ──────────────────────────────────────────────────────────


def mitm_connect(client_sock, host, port, injector, ca_cert, ca_key, executor):
    """
    Full MITM:
      1. TLS handshake with client using per-host cert signed by our CA
      2. TLS handshake with real server as a normal TLS client
      3. Pipe plaintext both ways — inject cookies on client→server side
    """
    cert, key = generate_cert_for_host(host, ca_cert, ca_key)

    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem  = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption()
    )

    cf = tempfile.NamedTemporaryFile(delete=False, suffix=".crt")
    cf.write(cert_pem); cf.close()
    kf = tempfile.NamedTemporaryFile(delete=False, suffix=".key")
    kf.write(key_pem);  kf.close()

    client_tls = None
    server_tls = None

    try:
        # side A: us ↔ client (we present our fake cert signed by our CA)
        ctx_client = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx_client.load_cert_chain(cf.name, kf.name)
        client_tls = ctx_client.wrap_socket(client_sock, server_side=True)

        # side B: us ↔ real server (normal TLS client)
        ctx_server = ssl.create_default_context()
        raw_server = socket.create_connection((host, port), timeout=120)
        raw_server.settimeout(15)                        # ← add this
        server_tls = ctx_server.wrap_socket(raw_server, server_hostname=host)
        client_tls.settimeout(15)
        server_tls.settimeout(15)

        if DEBUG:
            print(f"[sproxy] MITM TLS established ↔ {host}:{port}")

    except Exception as e:
        print(f"[sproxy] MITM handshake failed for {host}:{port} — {e}")
        for s in (client_tls, server_tls):
            if s:
                try: s.close()
                except: pass
        return
    finally:
        for p in (cf.name, kf.name):
            try: os.unlink(p)
            except: pass


    def client_to_server():
        try:
            while True:
                data = client_tls.recv(65535)
                if not data:
                    break
                log_headers(data, f"MITM client→{host} (before inject)")
                hexdump(data, f"MITM PLAIN client→{host}")
                data = injector.inject(data)   # cookie injection on decrypted plaintext
                server_tls.sendall(data)
        except OSError:
            pass
        finally:
            for s in (client_tls, server_tls):
                try: s.close()
                except: pass

    def server_to_client():
        try:
            while True:
                data = server_tls.recv(65535)
                if not data:
                    break
                log_headers(data, f"MITM {host}→client")
                hexdump(data, f"MITM PLAIN {host}→client")
                client_tls.sendall(data)
        except OSError:
            pass
        finally:
            for s in (client_tls, server_tls):
                try: s.close()
                except: pass

    executor.submit(client_to_server)
    executor.submit(server_to_client)


# ── Client handler ────────────────────────────────────────────────────────────

def handle_client(client, injector, ca_cert, ca_key, executor):
    try:
        data = recv_until_headers_complete(client)
        
        # DEBUG — log every incoming request raw
        #print(f"[sproxy] incoming ({len(data)} bytes): {data[:200]}")
        
        if not data:
            return
        # ── CONNECT → MITM TLS ─────────────────────────────────────────────
        if data.startswith(b"CONNECT"):
            target = data.split(b" ")[1].decode()
            host, port = target.rsplit(":", 1)
            port = int(port)

            client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            if DEBUG:
                print(f"[sproxy] CONNECT {host}:{port} → MITM TLS")
            mitm_connect(client, host, port, injector, ca_cert, ca_key, executor)
            client = None   # pipe threads own the socket now
            return

        # ── Plain HTTP ─────────────────────────────────────────────────────
        log_headers(data, "plain HTTP from client")
        hexdump(data, "plain HTTP from client (bytes)")

        first_line = data.split(b"\r\n")[0].decode()
        parts  = first_line.split(" ")
        method = parts[0] if len(parts) > 0 else "GET"
        url    = parts[1] if len(parts) > 1 else "/"

        if url.startswith("http://") or url.startswith("https://"):
            _, new_host, new_port, path = parse_location_parts(url)
        else:
            path     = url
            new_host = None
            new_port = 80

        host_match = re.search(rb"^Host:\s*(.+)", data, re.MULTILINE | re.IGNORECASE)
        if not new_host:
            if not host_match:
                return
            h = host_match.group(1).strip().decode()
            new_host, new_port = (h.rsplit(":", 1) if ":" in h else (h, 80))
            if isinstance(new_port, str):
                new_port = int(new_port)

        try:
            hdr_block, body = data.split(b"\r\n\r\n", 1)
        except ValueError:
            hdr_block, body = data, b""

        hdr_lines = hdr_block.split(b"\r\n")[1:]
        skip = {b"host", b"connection", b"proxy-connection"}
        extra = b"\r\n".join(
            l for l in hdr_lines
            if not l.lower().split(b":")[0].strip() in skip
        )
        if extra:
            extra += b"\r\n"

        response = do_request(method, new_host, new_port, path,
                              injector, extra, body)
        client.sendall(response)

    except Exception as e:
        print(f"[sproxy] handle_client error: {e}")
    finally:
        if client:
            try: client.close()
            except: pass


# ── Start ─────────────────────────────────────────────────────────────────────

def start():
    injector = CookieInjector()
    ca_cert, ca_key = load_ca()
    print(f"[sproxy] CA loaded: {CA_CERT_PATH}")
    if DEBUG:
        print("[sproxy] DEBUG mode ON — full traffic logging enabled")

    executor = ThreadPoolExecutor(max_workers=PROXY_THREAD_WORKERS)

    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((LISTEN_HOST, LISTEN_PORT))
    s.listen(100)

    print(f"[sproxy] listening on {LISTEN_HOST}:{LISTEN_PORT}")
    print("[sproxy] press enter once, this proxy is being run in background if was called by sessme()")
    print("""NOTE: Make sure aiohttp and go tools are run by proxychain as for now, although for most of my tools
I'll fix the problem, with 'trust_env=True'""")
    while True:
        c, addr = s.accept()
        executor.submit(handle_client, c, injector, ca_cert, ca_key, executor)


if __name__ == "__main__":
    start()
