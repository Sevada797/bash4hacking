#!/usr/bin/env python3
"""
sessme.py — dump ALL cookies from existing Chrome/Chromium profile into
~/.sessme/SESSION.json, grouped by host with proper domain matching.

Usage:
  python3 sessme.py                   # dump every host found in the DB

Domain grouping:
  a.b.com  -> merged from: a.b.com, .a.b.com, .b.com
  a.com    -> merged from: a.com,   .a.com

Output: ~/.sessme/SESSION.json
  { "a.b.com": "name=val; ...", "a.com": "name=val; ...", ... }

Python 3.8+ compatible.
"""

import os, shutil, tempfile, sqlite3, hmac, json, socket
from hashlib import sha1

# ── crypto ────────────────────────────────────────────────────────────────────
try:
    from Crypto.Cipher import AES
    from Crypto.Protocol.KDF import PBKDF2
    CRYPTO_LIB = "pycryptodome"
except ImportError:
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes, padding
        from cryptography.hazmat.backends import default_backend
        CRYPTO_LIB = "cryptography"
    except ImportError:
        CRYPTO_LIB = None

# ── Chromium AES-CBC constants ────────────────────────────────────────────────
SALT       = b"saltysalt"
ITERATIONS = 1
KEY_LENGTH = 16
V10_PASS   = b"peanuts"

HOME = os.path.expanduser("~")
COOKIE_DB_CANDIDATES = [
    f"{HOME}/.config/google-chrome/Default/Cookies",
    f"{HOME}/.config/google-chrome/Profile 1/Cookies",
    f"{HOME}/.config/brave-browser/Default/Cookies",
    f"{HOME}/.config/vivaldi/Default/Cookies",
]

SESSME_DIR  = os.path.join(HOME, ".sessme")
SESSION_JSON = os.path.join(SESSME_DIR, "SESSION.json")


# ── key helpers ───────────────────────────────────────────────────────────────

def pbkdf2_key(password):
    if CRYPTO_LIB == "pycryptodome":
        return PBKDF2(password, SALT, dkLen=KEY_LENGTH, count=ITERATIONS,
                      prf=lambda p, s: hmac.new(p, s, sha1).digest())
    kdf = PBKDF2HMAC(algorithm=hashes.SHA1(), length=KEY_LENGTH,
                     salt=SALT, iterations=ITERATIONS,
                     backend=default_backend())
    return kdf.derive(password)


def aes_cbc_decrypt(key, iv, ciphertext):
    try:
        if CRYPTO_LIB == "pycryptodome":
            raw = AES.new(key, AES.MODE_CBC, iv).decrypt(ciphertext)
            return raw[:-raw[-1]]
        cipher   = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        dec      = cipher.decryptor()
        raw      = dec.update(ciphertext) + dec.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(raw) + unpadder.finalize()
    except Exception:
        return None


# ── v11 key via pure dbus ─────────────────────────────────────────────────────

def get_v11_key(prefer="chrome"):
    try:
        import dbus
        bus = dbus.SessionBus()
        svc = dbus.Interface(
            bus.get_object("org.freedesktop.secrets", "/org/freedesktop/secrets"),
            "org.freedesktop.Secret.Service")

        session_path = svc.OpenSession("plain", dbus.String("", variant_level=1))[1]

        apps = ["chrome", "chromium"] if prefer == "chrome" else ["chromium", "chrome"]
        for app in apps:
            found, _ = svc.SearchItems({"application": app})
            for item_path in found:
                obj   = bus.get_object("org.freedesktop.secrets", item_path)
                label = str(obj.Get("org.freedesktop.Secret.Item", "Label",
                                    dbus_interface="org.freedesktop.DBus.Properties"))
                if label not in ("Chrome Safe Storage", "Chromium Safe Storage"):
                    continue
                raw = bytes(dbus.Interface(obj, "org.freedesktop.Secret.Item")
                            .GetSecret(session_path)[2])
                key = pbkdf2_key(raw)
                print(f"[sessme] v11 key: {label!r}")
                return key
    except Exception as e:
        print(f"[sessme] keyring error: {e}")
    return None


def detect_browser(db_path):
    return "chromium" if "chromium" in db_path.lower() else "chrome"


# ── decryption ────────────────────────────────────────────────────────────────

def decrypt_value(enc, v11_key):
    if not enc:
        return ""
    if isinstance(enc, memoryview):
        enc = bytes(enc)
    elif isinstance(enc, str):
        enc = enc.encode("utf-8")

    if not CRYPTO_LIB:
        return enc.decode("utf-8", errors="replace")

    prefix = enc[:3]
    iv     = enc[3:19]
    body   = enc[19:]

    if prefix == b"v10":
        raw = aes_cbc_decrypt(pbkdf2_key(V10_PASS), iv, body)
        return raw[16:].decode("utf-8", errors="replace") if raw is not None else "<v10:failed>"
    if prefix == b"v11":
        if not v11_key:
            return "<v11:no_key>"
        raw = aes_cbc_decrypt(v11_key, iv, body)
        return raw[16:].decode("utf-8", errors="replace") if raw is not None else "<v11:failed>"

    return enc.decode("utf-8", errors="replace")


# ── DB helpers ────────────────────────────────────────────────────────────────

def find_cookie_db():
    for p in COOKIE_DB_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def fetch_all_cookies(cur):
    """Return every row: (host_key, name, encrypted_value)."""
    cur.execute("SELECT host_key, name, encrypted_value FROM cookies ORDER BY host_key, name")
    return cur.fetchall()


# ── grouping ──────────────────────────────────────────────────────────────────

def group_cookies(rows, v11_key):
    buckets = {}
    for db_host, name, enc in rows:
        canonical = db_host.lstrip(".")
        value = decrypt_value(enc, v11_key)
        buckets.setdefault(canonical, {})[name] = value

    # Second pass: for each host, merge in cookies from parent domains
    all_hosts = set(buckets.keys())
    for host in all_hosts:
        parts = host.split(".")
        # Walk up the domain hierarchy, e.g. barnaul.hh.ru -> hh.ru -> ru
        for i in range(1, len(parts) - 1):          # skip the full host itself and the TLD
            parent = ".".join(parts[i:])             # e.g. "hh.ru"
            if parent in buckets:
                # Parent cookies go in first (lower priority), host cookies win on conflict
                merged = {**buckets[parent], **buckets[host]}
                buckets[host] = merged

    return {
        host: "; ".join(f"{n}={v}" for n, v in pairs.items())
        for host, pairs in buckets.items()
    }

# ── SESSION.json writer ───────────────────────────────────────────────────────

def write_session_json(data):
    os.makedirs(SESSME_DIR, exist_ok=True)
    existing = {}
    try:
        with open(SESSION_JSON, "r", encoding="utf-8") as f:
            existing = json.load(f)
    except Exception:
        pass

    existing.update(data)
    with open(SESSION_JSON, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"[sessme] {SESSION_JSON} written ({len(data)} host(s) updated)")

# ── Func to check if socket is open (for sproxy call||skip) ───────────────────────────────────────────────────────
def is_port_open(host, port):
    s = socket.socket()
    result = s.connect_ex((host, port))
    s.close()
    return result == 0


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    if not CRYPTO_LIB:
        print("[sessme] WARNING: no crypto lib — pip install pycryptodome")

    db = find_cookie_db()
    if not db:
        print("[sessme] ERROR: cookie DB not found. Candidates:")
        for p in COOKIE_DB_CANDIDATES:
            print(f"         {p}")
        return

    print(f"[sessme] DB: {db}")

    tmp = tempfile.mktemp(suffix=".cookies.tmp")
    shutil.copy2(db, tmp)

    v11_key = get_v11_key(prefer=detect_browser(db))
    print("[sessme] v11 decryption ready ✓" if v11_key
          else "[sessme] v11 key unavailable — v10 fallback only")

    try:
        con  = sqlite3.connect(tmp)
        cur  = con.cursor()
        rows = fetch_all_cookies(cur)
        con.close()
        print(f"[sessme] total rows in DB: {len(rows)}")
    finally:
        os.unlink(tmp)

    grouped = group_cookies(rows, v11_key)

    if not grouped:
        print("[sessme] no cookies found — SESSION.json not updated")
        return

    for host, cookie_str in sorted(grouped.items()):
        n = cookie_str.count(";") + 1
        # print(f"[sessme]   {host}: {n} cookie(s)")   # I comment out print, too long out

    write_session_json(grouped)
    
    if is_port_open("127.0.0.1", 7797):
        ##  We can't do the export in this py file, because of this hierarchy of processes
        #    bash
        #      └── python
        #        └── os.system() → new shell
        #
        #   So we just will call the export from sessme(), thanks for attention

        print("[sessme] Proxy (sproxy) already running, exporting the proxy env vars only")
    else:
        print("[sessme] Running proxy (sproxy) and exporting the proxy env vars")
        os.system("python3 \"$BFH_PATH/pysrc/sproxy.py\" &")





if __name__ == "__main__":
    main()