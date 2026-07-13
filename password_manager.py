import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json, os, secrets, string, threading, time, csv, webbrowser
from datetime import datetime
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes, padding as crypto_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from zxcvbn import zxcvbn as _zxcvbn
import hmac as _hmac, hashlib as _hashlib

try:
    import pyperclip
    HAS_CLIP = True
except Exception:
    HAS_CLIP = False

try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    HAS_FLASK = True
except Exception:
    HAS_FLASK = False

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    HAS_PDF = True
except Exception:
    HAS_PDF = False

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except Exception:
    HAS_TRAY = False

APP_TITLE   = "The LockShed"
# Bump this on every release (v1.0.0 -> v1.0.1 -> v1.0.2 -> ... -> v1.1.0
# for bigger changes). Keep this in sync with MyAppVersion in
# build/installer.iss and the version shown on the landing page
# (index.html) - all three should always match. See README.txt
# section 10 for the release checklist.
APP_VERSION = "v1.0.0"

# When bundled by PyInstaller (frozen), __file__ points into a temp/extracted
# location rather than next to the actual .exe, so data folders like
# chrome_extension/ and mobile_pwa/ (bundled alongside the exe) would be
# looked up in the wrong place. sys._MEIPASS is set by the PyInstaller
# bootloader in both --onefile and --onedir builds and always points to
# where the bundled data actually lives.
import sys
if getattr(sys, "frozen", False):
    BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ICON_PATH   = os.path.join(BASE_DIR, "assets", "lock_icon.png")
try:
    from PIL import Image as _PILImage
    _HEADER_ICON = ctk.CTkImage(_PILImage.open(ICON_PATH), size=(52, 52))
    HAS_HEADER_ICON = True
except Exception:
    HAS_HEADER_ICON = False

SETTINGS_FILE     = os.path.join(os.path.expanduser("~"), ".lockshed_settings.json")
DEFAULT_DATA_FILE = os.path.join(os.path.expanduser("~"), ".lockshed.enc")

# One-time migration from the app's old name ("Lösenordsvalvet") so nobody's
# existing vault silently "disappears" just because the default file names
# changed. Only copies (never deletes/moves) the old files, and only when
# the new ones don't already exist - safe to run on every startup.
def _migrate_legacy_paths():
    old_settings = os.path.join(os.path.expanduser("~"), ".losenordsvalvet_settings.json")
    old_data     = os.path.join(os.path.expanduser("~"), ".losenordsvalvet.enc")
    import shutil
    if os.path.exists(old_settings) and not os.path.exists(SETTINGS_FILE):
        try:
            shutil.copy2(old_settings, SETTINGS_FILE)
            print(f"[LockShed] Migrated settings from old location: {old_settings}")
        except Exception as e:
            print(f"[LockShed] Could not migrate settings file: {e}")
    if os.path.exists(old_data) and not os.path.exists(DEFAULT_DATA_FILE):
        try:
            shutil.copy2(old_data, DEFAULT_DATA_FILE)
            print(f"[LockShed] Migrated vault file from old location: {old_data}")
        except Exception as e:
            print(f"[LockShed] Could not migrate vault file: {e}")

_migrate_legacy_paths()

CATEGORIES  = ["Other","Email","Social","Work","Finance","Gaming","Torrent","TV & Film","Anime"]


# Migration map: old Swedish category names -> new English names
CAT_MIGRATION = {
    "Other":   "Other",
    "E-post":   "Email",
    "Socialt":  "Social",
    "Jobb":     "Work",
    "Finans":   "Finance",
    "Gaming":   "Gaming",
    "Torrent":  "Torrent",
    "TV & Film":"TV & Film",
    "Anime":    "Anime",
    "Alla":     "All",
}

def migrate_entries(entries):
    """Translate old Swedish category/field values to English."""
    changed = False
    for e in entries:
        old_cat = e.get("category", "Other")
        new_cat = CAT_MIGRATION.get(old_cat, old_cat)
        if new_cat != old_cat:
            e["category"] = new_cat
            changed = True
    return entries, changed
CAT_ICONS   = {
    "All":      "All",
    "Other":    "Other",
    "Email":    "Email",
    "Social":   "Social",
    "Work":     "Work",
    "Finance":  "Finance",
    "Gaming":   "Gaming",
    "Torrent":  "Torrent",
    "TV & Film":"TV & Film",
    "Anime":    "Anime",
}
CAT_GROUPS = {
    "FILTER": ["All"],
    "CATEGORIES": ["Other","Email","Social","Work","Finance","Gaming","Torrent","TV & Film","Anime"],
}
AUTO_LOCK_SECONDS = 600
CLIP_CLEAR_SECONDS = 30
FONT_SCALE = 1.15  # global font scaling factor for readability (1.0 = default size)
API_PORT        = 19485   # browser extension (localhost only)
API_MOBILE_PORT = 19486   # mobile PWA (local network)
MOBILE_MAX_ATTEMPTS   = 5        # failed PIN attempts before a lockout
MOBILE_LOCKOUT_SECONDS = 60      # how long a source IP is locked out for
MOBILE_TOKEN_TTL       = 12 * 3600  # session token lifetime (sliding), seconds

THEMES = {
    "Light": {
        "mode": "light", "color": "#2563eb",
        "sidebar_bg":"#1e293b", "sidebar_fg":"#cbd5e1", "sidebar_sub":"#94a3b8", "sidebar_hover":"#334155",
        "main_bg":"#f0f2f5", "card_bg":"#ffffff", "search_bg":"#ffffff",
        "text_primary":"#1a1a1a", "text_muted":"#888888",
        "accent":"#2563eb", "accent_hover":"#1d4ed8",
        "danger":"#dc2626", "row_alt":"#f8fafc", "border":"#e2e8f0",
    },
    "Dark": {
        "mode": "dark", "color": "#4299e1",
        "sidebar_bg":"#0f0f0f", "sidebar_fg":"#a0aec0", "sidebar_sub":"#4a5568", "sidebar_hover":"#1a1a1a",
        "main_bg":"#1a1a2e", "card_bg":"#16213e", "search_bg":"#16213e",
        "text_primary":"#e2e8f0", "text_muted":"#718096",
        "accent":"#4299e1", "accent_hover":"#3182ce",
        "danger":"#fc8181", "row_alt":"#1e2a45", "border":"#2d3748",
    },
    "Abstract Tech": {
        "mode": "dark", "color": "#a855f7",
        "sidebar_bg":"#0d0221", "sidebar_fg":"#c084fc", "sidebar_sub":"#6b21a8", "sidebar_hover":"#1e0545",
        "main_bg":"#0a001a", "card_bg":"#0d0030", "search_bg":"#12003a",
        "text_primary":"#e9d5ff", "text_muted":"#a855f7",
        "accent":"#a855f7", "accent_hover":"#9333ea",
        "danger":"#f43f5e", "row_alt":"#110040", "border":"#3b0764",
    },
    "AI Security": {
        "mode": "dark", "color": "#00e676",
        "sidebar_bg":"#001a12", "sidebar_fg":"#00ff88", "sidebar_sub":"#00994d", "sidebar_hover":"#002b1d",
        "main_bg":"#00100a", "card_bg":"#001a0f", "search_bg":"#001a0f",
        "text_primary":"#ccffe8", "text_muted":"#00994d",
        "accent":"#00e676", "accent_hover":"#00c853",
        "danger":"#ff1744", "row_alt":"#002214", "border":"#003d1f",
    },
    "Gaming": {
        "mode": "dark", "color": "#ff4500",
        "sidebar_bg":"#0a0a0a", "sidebar_fg":"#ff6b35", "sidebar_sub":"#994020", "sidebar_hover":"#1a0a00",
        "main_bg":"#0f0800", "card_bg":"#120a00", "search_bg":"#1a1000",
        "text_primary":"#ffd700", "text_muted":"#cc8800",
        "accent":"#ff4500", "accent_hover":"#cc3700",
        "danger":"#ff0055", "row_alt":"#1a0e00", "border":"#3d1f00",
    },
    "Midnatt": {
        "mode": "dark", "color": "#4f8ef7",
        "sidebar_bg":"#13203a", "sidebar_fg":"#c8d6f0", "sidebar_sub":"#4a6080", "sidebar_hover":"#1e3050",
        "main_bg":"#0f1b2d", "card_bg":"#1a2d45", "search_bg":"#1a2d45",
        "text_primary":"#dce8f8", "text_muted":"#6b86a8",
        "accent":"#4f8ef7", "accent_hover":"#3a75e0",
        "danger":"#f05060", "row_alt":"#1e3350", "border":"#2a4060",
        "hover_row":"#223558",
    },
    "Vault Blue": {
        "mode": "dark", "color": "#4f8cff",
        "sidebar_bg":"#0a1228", "sidebar_fg":"#aebbd4", "sidebar_sub":"#7989ab", "sidebar_hover":"#132042",
        "main_bg":"#060a16", "card_bg":"#0e1a36", "search_bg":"#0e1a36",
        "text_primary":"#f3f6fb", "text_muted":"#7989ab",
        "accent":"#4f8cff", "accent_hover":"#2563eb",
        "danger":"#ff6b6b", "row_alt":"#101d3d", "border":"#1c2740",
        "hover_row":"#142447",
    },
    "Miyabi": {
        # Japanese washi-paper aesthetic: warm sepia/cream tones, deep
        # cherry-wood sidebar, gold accent. Named "Miyabi" (雅) - a term
        # for refined, courtly elegance in traditional Japanese aesthetics.
        "mode": "light", "color": "#b8860b",
        "sidebar_bg":"#2b1810", "sidebar_fg":"#d4b896", "sidebar_sub":"#8a6f56", "sidebar_hover":"#3d2418",
        "main_bg":"#ede0c8", "card_bg":"#f5ecd7", "search_bg":"#e8dcc0",
        "text_primary":"#3a2a1a", "text_muted":"#8a7256",
        "accent":"#b8860b", "accent_hover":"#9a6f08",
        "danger":"#a13d2e", "row_alt":"#e3d5b4", "border":"#c9b48c",
        "hover_row":"#dccba2",
    },
}

STRENGTH_COLORS = ["#ef4444","#f97316","#eab308","#22c55e","#16a34a","#15803d"]
STRENGTH_LABELS = ["Very weak","Weak","Fair","Good","Strong","Very strong"]

def load_settings():
    try:
        with open(SETTINGS_FILE,"r",encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_settings(s):
    with open(SETTINGS_FILE,"w",encoding="utf-8") as f: json.dump(s,f,ensure_ascii=False,indent=2)

def get_data_file():  return load_settings().get("data_file", DEFAULT_DATA_FILE)
def get_theme_name(): return load_settings().get("theme","Vault Blue")
def get_theme():      return THEMES.get(get_theme_name(), THEMES["Light"])

def get_ext_secret():
    """Per-install pairing secret for the browser extension. Generated once
    on first use and stored in settings - never hardcoded/shared across
    installs, so it can't be read out of the public source code."""
    s = load_settings()
    secret = s.get("ext_secret")
    if not secret:
        secret = secrets.token_urlsafe(24)
        s["ext_secret"] = secret
        save_settings(s)
    return secret

def regenerate_ext_secret():
    """Invalidate the current pairing secret (e.g. if it may have leaked)
    and issue a new one. The extension will need to be re-paired."""
    s = load_settings()
    secret = secrets.token_urlsafe(24)
    s["ext_secret"] = secret
    save_settings(s)
    return secret

def load_custom_categories():
    """Load user-defined categories from settings, falling back to defaults."""
    cats = load_settings().get("custom_categories", None)
    if cats:
        global CATEGORIES, CAT_GROUPS, CAT_ICONS
        CATEGORIES = cats
        CAT_GROUPS["CATEGORIES"] = cats
        CAT_ICONS = {"All": "All"}
        for c in cats:
            CAT_ICONS[c] = c

# FILE FORMAT: 16 bytes salt | 2 bytes version | encrypted blob | 32 bytes MAC
FILE_VERSION = b"VT"

def derive_keys(password: str, salt: bytes):
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
                     iterations=600000, backend=default_backend())
    master = kdf.derive(password.encode())
    enc_key = _hmac.new(master, b'enc', _hashlib.sha256).digest()
    mac_key = _hmac.new(master, b'mac', _hashlib.sha256).digest()
    return enc_key, mac_key

def _encrypt_blob(data: bytes, enc_key: bytes, mac_key: bytes) -> bytes:
    iv = os.urandom(16)
    padder = crypto_padding.PKCS7(128).padder()
    padded = padder.update(data) + padder.finalize()
    enc = Cipher(algorithms.AES(enc_key), modes.CBC(iv), backend=default_backend()).encryptor()
    ct  = enc.update(padded) + enc.finalize()
    mac = _hmac.new(mac_key, iv + ct, _hashlib.sha256).digest()
    return iv + ct + mac

def _decrypt_blob(blob: bytes, enc_key: bytes, mac_key: bytes) -> bytes:
    iv, ct, mac = blob[:16], blob[16:-32], blob[-32:]
    expected = _hmac.new(mac_key, iv + ct, _hashlib.sha256).digest()
    if not _hmac.compare_digest(mac, expected):
        raise ValueError('Wrong password or tampered file')
    dec = Cipher(algorithms.AES(enc_key), modes.CBC(iv), backend=default_backend()).decryptor()
    padded = dec.update(ct) + dec.finalize()
    unpadder = crypto_padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()

def generate_password(length=16,upper=True,digits=True,symbols=True):
    chars = string.ascii_lowercase
    if upper:   chars += string.ascii_uppercase
    if digits:  chars += string.digits
    if symbols: chars += "!@#$%^&*()-_=+"
    return "".join(secrets.choice(chars) for _ in range(length))

def fnt(size):
    """Scale a font size by the global FONT_SCALE factor, rounded to nearest int."""
    return round(size * FONT_SCALE)

def pw_strength(pw):
    """Use zxcvbn for realistic strength (0-4). Map to 0-5 scale."""
    if not pw: return 0
    r = _zxcvbn(pw)
    # zxcvbn gives 0-4; we map to 0-5 based on crack time
    score = r["score"]
    secs  = r["crack_times_seconds"]["offline_slow_hashing_1e4_per_second"]
    if score == 4 and secs > 3e10:  # > ~1000 years
        return 5
    return score

def pw_feedback(pw):
    """Return warning + suggestions from zxcvbn."""
    if not pw: return "", []
    r = _zxcvbn(pw)
    return r["feedback"]["warning"], r["feedback"]["suggestions"]

def now_str(): return datetime.now().strftime("%Y-%m-%d %H:%M")

# ── Local API Server (for browser extension) ──────────────────────────────────
class LocalAPIServer:
    """Tiny Flask server on localhost that the browser extension talks to.

    Security model:
    - The extension's background service worker (not content scripts, which
      run in the page's own origin) is the only legitimate caller. Browsers
      always send Origin: chrome-extension://<id> for such requests, and no
      web page's JavaScript can forge that header. We only ever answer (and
      only ever set an Access-Control-Allow-Origin header for) requests
      whose Origin starts with "chrome-extension://" - this alone blocks the
      "any website can just fetch() us" drive-by attack.
    - On top of that, a per-install random secret (see get_ext_secret) is
      required, checked with a constant-time comparison, as defense in depth
      in case a malicious browser extension ever tried the same trick.
    - No entries are ever returned while the vault is locked, even if the
      secret and origin checks pass.
    """

    def __init__(self, get_entries_fn, is_locked_fn=lambda: False):
        self.get_entries = get_entries_fn
        self.is_locked   = is_locked_fn
        self._thread = None
        if not HAS_FLASK:
            return
        self.flask_app = Flask(__name__)
        # NOTE: no CORS(...) wildcard here on purpose - CORS headers are set
        # manually per-request in start(), restricted to the extension origin.
        self._register_routes()

    def _check_origin(self):
        origin = request.headers.get("Origin", "")
        # No Origin header at all (e.g. a local curl/script) is allowed
        # through to the secret check; an Origin that isn't a browser
        # extension (i.e. any normal website) is rejected outright,
        # regardless of what secret it presents.
        return (not origin) or origin.startswith("chrome-extension://")

    def _check_secret(self):
        if not self._check_origin():
            return False
        header = request.headers.get("X-Secret", "")
        return bool(header) and _hmac.compare_digest(header, get_ext_secret())

    def _register_routes(self):
        app = self.flask_app

        @app.route("/ping", methods=["GET"])
        def ping():
            if not self._check_secret(): return jsonify({"error": "forbidden"}), 403
            return jsonify({"status": "ok", "app": APP_TITLE, "locked": self.is_locked()})

        @app.route("/lookup", methods=["POST"])
        def lookup():
            if not self._check_secret(): return jsonify({"error": "forbidden"}), 403
            if self.is_locked():
                return jsonify({"error": "locked", "entries": []}), 423
            data     = request.get_json(silent=True) or {}
            domain   = data.get("domain", "").lower().strip()
            show_all = data.get("show_all", False)
            entries  = self.get_entries()
            results  = []

            # Extract root domain e.g. "www.deviantart.com" -> "deviantart.com"
            def root_domain(d):
                parts = d.replace("https://","").replace("http://","").split("/")[0].split(".")
                return ".".join(parts[-2:]) if len(parts) >= 2 else d

            root = root_domain(domain)

            for e in entries:
                url      = e.get("url", "").lower()
                name     = e.get("name", "").lower()
                url_root = root_domain(url)

                # Score-based matching
                score = 0
                if root and root in url:         score = 3  # best: root domain in url
                elif root and root in url_root:  score = 3
                elif domain and domain in url:   score = 2
                elif root and root in name:      score = 1  # name matches
                elif name and name in domain:    score = 1
                elif show_all:                   score = 0
                else:                            continue

                results.append({
                    "name":  e["name"],
                    "user":  e.get("user", ""),
                    "pass":  e.get("pass", ""),
                    "url":   e.get("url", ""),
                    "_score": score,
                })

            results.sort(key=lambda x: (-x["_score"], x["name"].lower()))
            for r in results: r.pop("_score", None)
            return jsonify({"entries": results, "domain": domain})


    def _register_mobile_routes(self):
        """Mobile PWA endpoints - PIN protected, accessible from LAN.

        The raw PIN is only ever transmitted once, on /m/auth. A successful
        login exchanges it for a short-lived, per-session token (X-Mobile-Token)
        used for everything after that - so a single network capture of one
        request doesn't hand over the permanent credential, and repeated
        guesses against /m/auth are rate-limited per source IP.
        """
        app = self.mobile_app
        self._mobile_fails  = {}   # ip -> {"count": int, "locked_until": ts}
        self._mobile_tokens = {}   # token -> expiry ts

        @app.after_request
        def cors_mobile(response):
            response.headers["Access-Control-Allow-Origin"]  = "*"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Mobile-Token"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            return response

        def client_key():
            return request.remote_addr or "unknown"

        def is_locked_out():
            info = self._mobile_fails.get(client_key())
            return bool(info) and time.time() < info.get("locked_until", 0)

        def register_failure():
            info = self._mobile_fails.setdefault(client_key(), {"count": 0, "locked_until": 0})
            info["count"] += 1
            if info["count"] >= MOBILE_MAX_ATTEMPTS:
                info["locked_until"] = time.time() + MOBILE_LOCKOUT_SECONDS
                info["count"] = 0

        def register_success():
            self._mobile_fails.pop(client_key(), None)

        def issue_token():
            token = secrets.token_urlsafe(24)
            self._mobile_tokens[token] = time.time() + MOBILE_TOKEN_TTL
            return token

        def check_token():
            token = request.headers.get("X-Mobile-Token", "")
            if not token:
                return False
            expiry = self._mobile_tokens.get(token)
            if not expiry or time.time() > expiry:
                self._mobile_tokens.pop(token, None)
                return False
            self._mobile_tokens[token] = time.time() + MOBILE_TOKEN_TTL  # sliding expiry
            return True

        @app.route("/", methods=["GET"])
        @app.route("/index.html", methods=["GET"])
        def m_index():
            from flask import Response
            pwa_dir = os.path.join(BASE_DIR, "mobile_pwa")
            path = os.path.join(pwa_dir, "index.html")
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return Response(content, mimetype="text/html")

        @app.route("/<path:filename>", methods=["GET"])
        def m_static(filename):
            from flask import send_from_directory
            pwa_dir = os.path.join(BASE_DIR, "mobile_pwa")
            return send_from_directory(pwa_dir, filename)

        @app.route("/m/ping", methods=["GET", "OPTIONS"])
        def m_ping():
            if request.method == "OPTIONS": return jsonify({}), 200
            return jsonify({"status": "ok", "app": f"{APP_TITLE} Mobile"})

        @app.route("/m/auth", methods=["POST", "OPTIONS"])
        def m_auth():
            if request.method == "OPTIONS": return jsonify({}), 200
            if is_locked_out():
                return jsonify({"error": "Too many failed attempts. Try again in a minute."}), 429
            data = request.get_json(silent=True) or {}
            pin = data.get("pin", "")
            stored = load_settings().get("mobile_pin", "")
            if not stored:
                return jsonify({"error": "No mobile PIN set. Configure it in Settings."}), 403
            if bool(pin) and _hmac.compare_digest(pin, stored):
                register_success()
                return jsonify({"ok": True, "token": issue_token()})
            register_failure()
            return jsonify({"error": "Wrong PIN"}), 401

        @app.route("/m/entries", methods=["GET", "OPTIONS"])
        def m_entries():
            if request.method == "OPTIONS": return jsonify({}), 200
            if not check_token(): return jsonify({"error": "Unauthorized"}), 401
            if self.is_locked():
                return jsonify({"error": "Vault is locked on the desktop app.", "entries": []}), 423
            q = request.args.get("q", "").lower()
            entries = self.get_entries()
            results = []
            for e in entries:
                if q and not any(q in str(e.get(k, "")).lower()
                                 for k in ("name", "user", "url", "note", "category")):
                    continue
                results.append({
                    "id":       e["id"],
                    "name":     e["name"],
                    "user":     e.get("user", ""),
                    "category": e.get("category", ""),
                    "url":      e.get("url", ""),
                    "strength": pw_strength(e["pass"]),
                })
            results.sort(key=lambda x: x["name"].lower())
            return jsonify({"entries": results})

        @app.route("/m/password/<int:entry_id>", methods=["GET", "OPTIONS"])
        def m_password(entry_id):
            if request.method == "OPTIONS": return jsonify({}), 200
            if not check_token(): return jsonify({"error": "Unauthorized"}), 401
            if self.is_locked():
                return jsonify({"error": "Vault is locked on the desktop app."}), 423
            entries = self.get_entries()
            e = next((x for x in entries if x["id"] == entry_id), None)
            if not e: return jsonify({"error": "Not found"}), 404
            return jsonify({"password": e["pass"], "user": e.get("user", "")})

    def start(self):
        if not HAS_FLASK or self._thread:
            return
        import logging
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)
        # Also create a second Flask app for mobile (listens on all interfaces)
        self.mobile_app = Flask(__name__ + "_mobile")
        CORS(self.mobile_app, origins="*")
        self._register_mobile_routes()

        @self.flask_app.after_request
        def add_cors(response):
            # Only ever grant CORS access to a browser-extension origin -
            # never a wildcard. A normal website's JavaScript cannot spoof
            # "Origin: chrome-extension://...", so this is what stops any
            # page you visit from silently reading your vault. See the
            # LocalAPIServer docstring for the full rationale.
            origin = request.headers.get("Origin", "")
            if origin.startswith("chrome-extension://"):
                response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Secret"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            return response

        @self.flask_app.route("/lookup", methods=["OPTIONS"])
        @self.flask_app.route("/ping",   methods=["OPTIONS"])
        def options_handler():
            from flask import Response
            return Response(status=200)

        self.server_error = None

        def run():
            try:
                self.flask_app.run(host="127.0.0.1", port=API_PORT,
                                   debug=False, use_reloader=False)
            except OSError as e:
                self.server_error = str(e)
                print(f"[LockShed] API server error: {e}")

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

        # Mobile server on all interfaces (LAN accessible) - opt-in only.
        # We don't bind 0.0.0.0 at all unless the user has already set a
        # mobile PIN in Settings, so the port isn't sitting open on the
        # network for people who never intend to use the phone app. If you
        # set a PIN for the first time, restart the app to start this server.
        if load_settings().get("mobile_pin"):
            def run_mobile():
                try:
                    self.mobile_app.run(host="0.0.0.0", port=API_MOBILE_PORT,
                                       debug=False, use_reloader=False)
                except OSError as e:
                    print(f"[LockShed] Mobile server error: {e}")

            self._mobile_thread = threading.Thread(target=run_mobile, daemon=True)
            self._mobile_thread.start()
        else:
            self._mobile_thread = None
            print("[LockShed] Mobile server not started (no PIN set in Settings > Mobile).")

        # Verify server started after short delay
        def verify():
            import urllib.request
            time.sleep(2)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{API_PORT}/ping",
                    headers={"X-Secret": get_ext_secret()})
                urllib.request.urlopen(req, timeout=2)
                print(f"[LockShed] API server running on port {API_PORT}")
                self.server_ok = True
            except Exception as e:
                self.server_ok = False
                print(f"[LockShed] API server NOT reachable: {e}")

        threading.Thread(target=verify, daemon=True).start()

# ── Main App ───────────────────────────────────────────────────────────────────
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        # On Windows, the taskbar often shows python.exe's default icon
        # instead of our custom one, because Tkinter apps run via
        # pythonw.exe get grouped under Python's own App User Model ID by
        # default. Setting our own unique AppUserModelID tells Windows to
        # treat this as a distinct application, which makes the taskbar
        # icon use iconbitmap() below instead of falling back to Python's.
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "PasswordVault.App.1")
        except Exception:
            pass  # not on Windows, or API unavailable - icon still works in titlebar
        self.title(APP_TITLE)
        try:
            self.iconbitmap(os.path.join(BASE_DIR, "assets", "lock_icon.ico"))
        except Exception:
            pass
        self.geometry("1200x720")
        self.minsize(900,560)
        self.enc_key = None
        self.mac_key = None
        self.salt    = None
        self.entries = []
        self.selected_id = None
        self.sort_col    = "name"
        self.sort_rev    = False
        self.filter_cat  = "All"
        self._last_activity = time.time()
        self._locked = False
        self._lock_dialog_open = False
        self._unlock_attempts = 0
        self._max_unlock_attempts = 3
        self._clip_timer = None
        self._tray = None

        T = get_theme()
        ctk.set_appearance_mode(T["mode"])
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=T["main_bg"])
        self.T = T

        load_custom_categories()
        self._build_ui()
        # Start local API server for browser extension
        self._api_server = LocalAPIServer(lambda: self.entries, lambda: self._locked)
        self._api_server.start()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        # bind_all only catches events in this window, not separate Toplevel
        # dialogs (EntryDialog, SettingsDialog, etc). bind() on "all" via the
        # Tk interpreter itself catches activity everywhere, including child
        # windows, so editing an entry for a long time won't trigger auto-lock.
        self.bind_all("<Motion>",    self._reset_activity, add="+")
        self.bind_all("<KeyPress>",  self._reset_activity, add="+")
        self.bind_all("<Button>",    self._reset_activity, add="+")
        self._start_auto_lock()
        self.after(100, self._prompt_unlock)

    # ── UI ─────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        T = self.T
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar - outer frame uses grid with 3 rows: header (fixed), scrollable categories (expand), footer (fixed)
        self.sidebar = ctk.CTkFrame(self, width=210, corner_radius=0, fg_color=T["sidebar_bg"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_rowconfigure(0, weight=0)  # header
        self.sidebar.grid_rowconfigure(1, weight=1)  # scrollable categories
        self.sidebar.grid_rowconfigure(2, weight=0)  # footer

        # ── Header (fixed) ──────────────────────────────────────────────────
        header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew")

        if HAS_HEADER_ICON:
            ctk.CTkLabel(header, image=_HEADER_ICON, text="").pack(pady=(24,4))
        else:
            ctk.CTkLabel(header, text="🔐", font=("Segoe UI",fnt(32)),
                         text_color="#ffffff").pack(pady=(24,2))
        ctk.CTkLabel(header, text=APP_TITLE, font=("Segoe UI",fnt(14),"bold"),
                     text_color="#ffffff").pack()
        ctk.CTkLabel(header, text="Your private vault", font=("Segoe UI",fnt(9)),
                     text_color=T["sidebar_sub"]).pack(pady=(0,2))
        ctk.CTkLabel(header, text=APP_VERSION, font=("Segoe UI",fnt(8)),
                     text_color=T["sidebar_sub"]).pack(pady=(0,4))
        api_color = "#22c55e" if HAS_FLASK else "#6b86a8"
        api_text  = "● Extension ready" if HAS_FLASK else "● Install flask for extension"
        ctk.CTkLabel(header, text=api_text, font=("Segoe UI",fnt(8)),
                     text_color=api_color).pack(pady=(0,10))
        ctk.CTkFrame(header, height=1, fg_color=T["sidebar_sub"]).pack(fill="x", padx=20, pady=4)

        # ── Scrollable categories area (expands, scrolls if needed) ─────────
        cat_scroll = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent",
            corner_radius=0, scrollbar_button_color=T["sidebar_hover"],
            scrollbar_button_hover_color=T["sidebar_sub"])
        cat_scroll.grid(row=1, column=0, sticky="nsew")
        cat_scroll.grid_columnconfigure(0, weight=1)

        self._cat_buttons = {}
        for group, cats in CAT_GROUPS.items():
            ctk.CTkLabel(cat_scroll, text=group,
                font=("Segoe UI", fnt(8), "bold"), text_color=T["sidebar_sub"],
                anchor="w").pack(fill="x", padx=8, pady=(8,1))
            for cat in cats:
                label = CAT_ICONS.get(cat, cat)
                is_active = (cat == self.filter_cat)
                btn = ctk.CTkButton(cat_scroll, text=label, anchor="w",
                    font=("Segoe UI",fnt(11)),
                    fg_color=T["accent"] if is_active else "transparent",
                    text_color="#ffffff" if is_active else T["sidebar_fg"],
                    hover_color=T["accent"] if is_active else T["sidebar_hover"],
                    corner_radius=10, command=lambda c=cat: self._set_filter(c))
                btn.pack(fill="x", padx=2, pady=1, ipady=4)
                self._cat_buttons[cat] = btn

        # ── Footer (always pinned, never scrolls away) ───────────────────────
        footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew")

        ctk.CTkFrame(footer, height=1, fg_color=T["sidebar_sub"]).pack(fill="x", padx=20, pady=(4,6))

        for label, cmd in [
            ("Change password", self._change_master),
            ("Settings",        self._open_settings),
        ]:
            ctk.CTkButton(footer, text=label, anchor="w",
                font=("Segoe UI",fnt(10)), fg_color="transparent",
                text_color=T["sidebar_sub"], hover_color=T["sidebar_hover"],
                corner_radius=8, command=cmd
            ).pack(fill="x", padx=10, pady=1, ipady=3)

        ctk.CTkButton(footer, text="⏻  Exit", anchor="w",
            font=("Segoe UI",fnt(10)), fg_color="transparent",
            text_color="#ef4444", hover_color="#7f1d1d",
            corner_radius=8, command=self.destroy
        ).pack(fill="x", padx=10, pady=(6,10), ipady=3)

        # Main
        self.main = ctk.CTkFrame(self, corner_radius=0, fg_color=T["main_bg"])
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(1, weight=1)

        # Toolbar
        toolbar = ctk.CTkFrame(self.main, fg_color=T["main_bg"], corner_radius=0)
        toolbar.grid(row=0, column=0, sticky="ew", padx=16, pady=(12,6))
        toolbar.grid_columnconfigure(0, weight=1)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh())
        search = ctk.CTkEntry(toolbar, textvariable=self.search_var,
            placeholder_text="🔍  Search service, username or URL…",
            height=38, corner_radius=12, font=("Segoe UI",fnt(12)),
            border_width=1, border_color=T["border"])
        search.grid(row=0, column=0, sticky="ew", padx=(0,10))

        ctk.CTkButton(toolbar, text="＋  New", width=100, height=38,
            corner_radius=12, font=("Segoe UI",fnt(12),"bold"),
            command=self._open_add).grid(row=0, column=1)

        # Treeview (tk for table)
        tree_frame = ctk.CTkFrame(self.main, corner_radius=12, fg_color=T["card_bg"])
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0,6))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("PM.Treeview",
            background=T["card_bg"], fieldbackground=T["card_bg"],
            foreground=T["text_primary"], rowheight=46,
            borderwidth=0, font=("Segoe UI",fnt(11)))
        style.configure("PM.Treeview.Heading",
            background=T["card_bg"], foreground=T["text_muted"],
            font=("Segoe UI",fnt(10),"bold"), borderwidth=0, relief="flat")
        style.map("PM.Treeview",
            background=[("selected", T["accent"])],
            foreground=[("selected", "#ffffff")])
        style.layout("PM.Treeview", [('PM.Treeview.treearea',{'sticky':'nswe'})])

        cols = ("name","user","category","strength","changed","url")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                  style="PM.Treeview", selectmode="browse")

        headers = [("name","Service",210),
                   ("user","Username / Email",200), ("category","Category",95),
                   ("strength","Strength",80), ("changed","Last changed",125), ("url","URL",135)]
        for col, text, width in headers:
            self.tree.heading(col, text=text,
                command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=width, minwidth=30)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        def _yscroll_and_redraw(*args):
            vsb.set(*args)
            self._draw_strength_overlays()
        self.tree.configure(yscrollcommand=_yscroll_and_redraw)
        self.tree.bind("<Configure>", lambda e: self._draw_strength_overlays(), add="+")
        self._strength_meta = {}
        self._strength_overlays = {}
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(8,0), pady=8)
        vsb.grid(row=0, column=1, sticky="ns", pady=8, padx=(0,4))

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda e: self._open_edit())
        self.tree.bind("<Motion>", self._on_tree_hover)
        self.tree.bind("<Leave>",  lambda e: self._clear_hover())
        self.tree.tag_configure("fav_row",  foreground=T["accent"])
        self.tree.tag_configure("hovered",  background=T.get("hover_row", T["row_alt"]))
        self._hovered_iid = None

        # Action bar
        abar = ctk.CTkFrame(self.main, fg_color=T["main_bg"], corner_radius=0)
        abar.grid(row=2, column=0, sticky="ew", padx=16, pady=(0,10))

        btn_cfg = dict(height=32, corner_radius=8, font=("Segoe UI",fnt(11)))
        ctk.CTkButton(abar, text="⭐ Favorite",    width=110, **btn_cfg,
            fg_color=T["card_bg"], text_color=T["text_primary"],
            hover_color=T["border"], command=self._toggle_fav).pack(side="left", padx=(0,6))
        ctk.CTkButton(abar, text="📋 Copy",    width=110, **btn_cfg,
            fg_color=T["card_bg"], text_color=T["text_primary"],
            hover_color=T["border"], command=self._copy_password).pack(side="left", padx=(0,6))
        ctk.CTkButton(abar, text="🌐 Open URL",  width=110, **btn_cfg,
            fg_color=T["card_bg"], text_color=T["text_primary"],
            hover_color=T["border"], command=self._open_url).pack(side="left", padx=(0,6))
        ctk.CTkButton(abar, text="✏️ Edit",   width=110, **btn_cfg,
            fg_color=T["card_bg"], text_color=T["text_primary"],
            hover_color=T["border"], command=self._open_edit).pack(side="left", padx=(0,6))
        ctk.CTkButton(abar, text="🕘 History", width=110, **btn_cfg,
            fg_color=T["card_bg"], text_color=T["text_primary"],
            hover_color=T["border"], command=self._show_history).pack(side="left", padx=(0,6))
        ctk.CTkButton(abar, text="🗑 Delete",     width=100, **btn_cfg,
            fg_color=T["danger"], text_color="#ffffff",
            hover_color="#991b1b", command=self._delete_entry).pack(side="left")

        self.status_var = tk.StringVar(value="")
        ctk.CTkLabel(abar, textvariable=self.status_var,
            font=("Segoe UI",fnt(10)), text_color=T["text_muted"]).pack(side="right", padx=8)

    # ── Unlock ─────────────────────────────────────────────────────────────────
    def _prompt_unlock(self, re_lock=False):
        data_file = get_data_file()
        is_new = not os.path.exists(data_file) and not re_lock
        dlg = MasterDialog(self, new=is_new)
        self.wait_window(dlg)
        if not dlg.result:
            try: self.destroy()
            except: pass
            return
        pw = dlg.result
        if os.path.exists(data_file):
            try:
                with open(data_file,"rb") as f: raw = f.read()
                self.salt = raw[:16]
                ver       = raw[16:18]
                blob      = raw[18:]
                ek, mk = derive_keys(pw, self.salt)
                # Support old Fernet files (no version marker)
                if ver == FILE_VERSION:
                    data = _decrypt_blob(blob, ek, mk)
                else:
                    # Legacy Fernet fallback
                    from cryptography.fernet import Fernet
                    import base64
                    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC as _P
                    from cryptography.hazmat.primitives import hashes as _h
                    _kdf = _P(algorithm=_h.SHA256(),length=32,salt=raw[:16],iterations=480000)
                    _key = base64.urlsafe_b64encode(_kdf.derive(pw.encode()))
                    data = Fernet(_key).decrypt(raw[16:])
                    # Immediately re-save with new format
                    self.enc_key, self.mac_key = ek, mk
                    self.entries = json.loads(data)
                    self.entries, _ = migrate_entries(self.entries)
                    self._save()
                    self._unlock_attempts = 0
                    messagebox.showinfo("Upgraded",
                        "Your file has been upgraded to improved encryption (AES-256-CBC + HMAC-SHA256)!")
                    self._locked = False; self._reset_activity(); self._refresh(); return
                self.enc_key, self.mac_key = ek, mk
                self.entries = json.loads(data)
                # Migrate old Swedish category names to English
                self.entries, migrated = migrate_entries(self.entries)
                if migrated:
                    self._save()
                self._unlock_attempts = 0
            except Exception as e:
                self._unlock_attempts += 1
                remaining = self._max_unlock_attempts - self._unlock_attempts
                if remaining > 0:
                    plural = "attempt" if remaining == 1 else "attempts"
                    messagebox.showerror("Wrong Password",
                        f"Wrong Password\n\n{remaining} {plural} remaining.")
                    self._prompt_unlock(re_lock=re_lock)
                    return
                else:
                    messagebox.showerror("Locked Out",
                        "Wrong Password\n\nToo many failed attempts. The app will now close.")
                    try: self.destroy()
                    except Exception: pass
                    return
        else:
            self.salt = secrets.token_bytes(16)
            self.enc_key, self.mac_key = derive_keys(pw, self.salt)
            self.entries = []
            self._save()
        self._locked = False
        self._lock_dialog_open = False
        self._unlock_attempts = 0
        self._reset_activity()
        self._refresh()

    def _save(self):
        if not self.enc_key: return
        blob = _encrypt_blob(json.dumps(self.entries).encode(), self.enc_key, self.mac_key)
        with open(get_data_file(),"wb") as f:
            f.write(self.salt + FILE_VERSION + blob)

    # ── Auto-lock ──────────────────────────────────────────────────────────────
    def _start_auto_lock(self):
        def loop():
            while True:
                time.sleep(5)
                enabled = load_settings().get("auto_lock_enabled", True)
                if (enabled and not self._locked
                        and time.time() - self._last_activity > AUTO_LOCK_SECONDS):
                    # Set the lock flag and wipe decrypted entries from memory
                    # together, right here, so there's no window where the
                    # local API server (running on its own thread) could see
                    # _locked=True but still hand out cached entries, or
                    # vice versa. Plain list/bool assignment is thread-safe
                    # enough for this; only the UI refresh needs the main thread.
                    self._locked = True
                    self.entries = []
                    self.after(0, self._do_lock)
        t = threading.Thread(target=loop, daemon=True)
        t.start()

    def _reset_activity(self):
        self._last_activity = time.time()

    def _do_lock(self):
        # Guard - only show one lock dialog at a time
        if self._lock_dialog_open:
            return
        self._lock_dialog_open = True
        self.tree.delete(*self.tree.get_children())
        self.entries = []
        self.status_var.set("  Vault locked — enter master password")
        self._prompt_unlock(re_lock=True)
        self._lock_dialog_open = False

    # ── Tray ───────────────────────────────────────────────────────────────────
    def _on_close(self):
        if HAS_TRAY:
            self.withdraw()
            self._start_tray()
        else:
            self.destroy()

    def _start_tray(self):
        if self._tray: return
        try:
            img = Image.open(os.path.join(BASE_DIR, "assets", "lock_icon.png")).convert("RGBA")
            img = img.resize((64, 64), Image.LANCZOS)
        except Exception:
            img = Image.new("RGB",(64,64), color=(30,41,59))
            d = ImageDraw.Draw(img)
            d.ellipse([16,8,48,56], fill=(37,99,235))
            d.rectangle([28,28,36,48], fill="white")
            d.ellipse([24,16,40,32], fill="white")

        menu = pystray.Menu(
            pystray.MenuItem(f"Open {APP_TITLE}", self._tray_show, default=True),
            pystray.MenuItem("Quit", self._tray_quit)
        )
        self._tray = pystray.Icon("lockshed", img, APP_TITLE, menu)
        threading.Thread(target=self._tray.run, daemon=True).start()

    def _tray_show(self):
        self._tray.stop(); self._tray = None
        self.after(0, self.deiconify)

    def _tray_quit(self):
        self._tray.stop()
        self.after(0, self.destroy)

    # ── List ───────────────────────────────────────────────────────────────────
    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        self._strength_meta = {}
        q    = self.search_var.get().lower()
        filt = self.filter_cat
        passwords_seen = {}
        for e in self.entries:
            passwords_seen.setdefault(e["pass"], []).append(e["id"])

        def sort_key(e):
            if self.sort_col == "name":     v = ("" if e.get("fav") else "zzz") + e.get("name","").lower(); return v
            if self.sort_col == "strength": return pw_strength(e["pass"])
            return str(e.get(self.sort_col,"")).lower()

        rows = sorted(self.entries, key=sort_key, reverse=self.sort_rev)

        shown = 0
        for e in rows:
            if filt != "All" and e.get("category") != filt: continue
            if q and not any(q in str(e.get(k,"")).lower()
                             for k in ("name","user","url","note")): continue

            s        = pw_strength(e["pass"])
            is_dupe  = len(passwords_seen[e["pass"]]) > 1
            url_disp = e.get("url","")[:26] + "…" if len(e.get("url",""))>26 else e.get("url","")
            name_disp = ("⭐ " if e.get("fav") else "    ") + e["name"]

            # Strength now rendered as colored dot overlays (see _draw_strength_overlays)
            self._strength_meta[str(e["id"])] = (s, is_dupe)
            str_display = ""

            tags = ("fav_row",) if e.get("fav") else ()

            self.tree.insert("","end", iid=str(e["id"]),
                values=(name_disp, e.get("user",""),
                        e.get("category","Other"), str_display,
                        e.get("changed","–"), url_disp),
                tags=tags)
            shown += 1

        weak  = sum(1 for e in self.entries if pw_strength(e["pass"]) <= 1)
        dupes = sum(1 for pw, ids in passwords_seen.items() if len(ids)>1 for _ in ids)
        total = len(self.entries)
        parts = [f"{shown} of {total} entries"]
        if weak:  parts.append(f"[!] {weak} weak")
        if dupes: parts.append(f"[!] {dupes} duplicates")
        self.status_var.set("   ".join(parts))
        self.after(1, self._draw_strength_overlays)

    def _draw_strength_overlays(self):
        for cv in self._strength_overlays.values():
            try: cv.destroy()
            except Exception: pass
        self._strength_overlays = {}

        T = self.T
        for iid in self.tree.get_children():
            bbox = self.tree.bbox(iid, "strength")
            if not bbox:
                continue
            x, y, w, h = bbox
            s, is_dupe = self._strength_meta.get(iid, (0, False))

            cv = tk.Canvas(self.tree, width=w, height=h,
                            bg=T["card_bg"], highlightthickness=0)
            if is_dupe:
                cv.create_text(6, h // 2, anchor="w", text="⚠ Duplicate",
                                fill="#f5b942", font=("Segoe UI", fnt(10)))
            else:
                color = "#3ddc84" if s >= 3 else ("#f5b942" if s == 2 else "#ff6b6b")
                empty_color = T.get("border", "#2a4060")
                dot_r, gap, start_x, cy = 4, 10, 8, h // 2
                for i in range(6):
                    cx = start_x + i * gap
                    fill = color if i <= s else empty_color
                    cv.create_oval(cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r,
                                    fill=fill, outline="")
            cv.place(in_=self.tree, x=x, y=y, width=w, height=h)
            self._strength_overlays[iid] = cv

    def _sort_by(self, col):
        if self.sort_col == col: self.sort_rev = not self.sort_rev
        else: self.sort_col = col; self.sort_rev = False
        self._refresh()

    def _set_filter(self, cat):
        self.filter_cat = cat
        for n, btn in self._cat_buttons.items():
            if n == cat:
                btn.configure(fg_color=self.T["accent"],
                              text_color="#ffffff",
                              hover_color=self.T["accent"],
                              font=("Segoe UI", fnt(11), "bold"))
            else:
                btn.configure(fg_color="transparent",
                              text_color=self.T["sidebar_fg"],
                              hover_color=self.T["sidebar_hover"],
                              font=("Segoe UI", fnt(11)))
        self._refresh()

    def _on_select(self, _=None):
        sel = self.tree.selection()
        self.selected_id = int(sel[0]) if sel else None
        # Defer the overlay color update by one event-loop tick. The
        # <<TreeviewSelect>> event fires before Tkinter has finished
        # repainting the row's own selection background, so updating our
        # canvas overlay's bg immediately causes a brief visual mismatch
        # (a "cut-out" rectangle) until the underlying row catches up.
        self.after(1, self._sync_overlay_colors)

    def _sync_overlay_colors(self):
        sel = self.tree.selection()
        for iid, cv in self._strength_overlays.items():
            try:
                if iid == self._hovered_iid:
                    cv.configure(bg=self.T.get("hover_row", self.T["row_alt"]))
                else:
                    cv.configure(bg=self.T["accent"] if iid in sel else self.T["card_bg"])
            except Exception:
                pass

    def _overlay_base_bg(self, iid):
        sel = self.tree.selection()
        return self.T["accent"] if iid in sel else self.T["card_bg"]

    def _on_tree_hover(self, event):
        iid = self.tree.identify_row(event.y)
        if iid == self._hovered_iid: return
        if self._hovered_iid:
            tags = [t for t in self.tree.item(self._hovered_iid,"tags") if t != "hovered"]
            self.tree.item(self._hovered_iid, tags=tags)
            cv = self._strength_overlays.get(self._hovered_iid)
            if cv: cv.configure(bg=self._overlay_base_bg(self._hovered_iid))
        self._hovered_iid = iid
        if iid:
            tags = list(self.tree.item(iid, "tags")) + ["hovered"]
            self.tree.item(iid, tags=tags)
            cv = self._strength_overlays.get(iid)
            if cv: cv.configure(bg=self.T.get("hover_row", self.T["row_alt"]))

    def _clear_hover(self):
        if self._hovered_iid:
            tags = [t for t in self.tree.item(self._hovered_iid,"tags") if t != "hovered"]
            self.tree.item(self._hovered_iid, tags=tags)
            cv = self._strength_overlays.get(self._hovered_iid)
            if cv: cv.configure(bg=self._overlay_base_bg(self._hovered_iid))
            self._hovered_iid = None

    def _get_selected(self):
        if self.selected_id is None:
            messagebox.showinfo("Select an entry","Please select a row from the list first."); return None
        return next((e for e in self.entries if e["id"]==self.selected_id), None)

    # ── Actions ────────────────────────────────────────────────────────────────
    def _toggle_fav(self):
        e = self._get_selected()
        if not e: return
        e["fav"] = not e.get("fav", False)
        msg = f"{'⭐ Added to favorites' if e['fav'] else '☆ Removed from favorites'}: {e['name']}"
        eid = e["id"]
        self._save(); self._refresh()
        # Re-select the same row after refresh
        try:
            self.tree.selection_set(str(eid))
            self.selected_id = eid
        except: pass
        self.status_var.set(msg)

    def _copy_password(self):
        e = self._get_selected()
        if not e: return
        if HAS_CLIP:
            import pyperclip
            pyperclip.copy(e["pass"])
            self.status_var.set(f"📋 Copied — clears in {CLIP_CLEAR_SECONDS}s")
            if self._clip_timer: self._clip_timer.cancel()
            def clear_clip():
                try:
                    import pyperclip as pc
                    if pc.paste() == e["pass"]: pc.copy("")
                except: pass
                self.after(0, lambda: self.status_var.set("Clipboard cleared"))
            self._clip_timer = threading.Timer(CLIP_CLEAR_SECONDS, clear_clip)
            self._clip_timer.daemon = True
            self._clip_timer.start()
        else:
            messagebox.showinfo("Password", e["pass"])

    def _open_url(self):
        e = self._get_selected()
        if not e: return
        url = e.get("url","").strip()
        if not url: messagebox.showinfo("No URL","This entry has no URL saved."); return
        if not url.startswith(("http://","https://")): url = "https://" + url
        webbrowser.open(url)

    def _open_add(self):
        dlg = EntryDialog(self, title="Add new password")
        self.wait_window(dlg)
        if dlg.result:
            new_id = max((e["id"] for e in self.entries), default=0)+1
            self.entries.append({**dlg.result, "id":new_id, "changed":now_str()})
            self._save(); self._refresh()

    def _open_edit(self):
        e = self._get_selected()
        if not e: return
        old_pass = e["pass"]
        dlg = EntryDialog(self, title="Edit", existing=e)
        self.wait_window(dlg)
        if dlg.result:
            changed = dlg.result["pass"] != old_pass
            e.update(dlg.result)
            if changed:
                e["changed"] = now_str()
                # Keep the last 3 previous passwords (most recent first)
                history = e.get("history", [])
                history.insert(0, {"pass": old_pass, "changed_at": now_str()})
                e["history"] = history[:3]
            self._save(); self._refresh()

    def _show_history(self):
        e = self._get_selected()
        if not e: return
        dlg = HistoryDialog(self, e)
        self.wait_window(dlg)

    def _delete_entry(self):
        e = self._get_selected()
        if not e: return
        if messagebox.askyesno("Delete",f"Delete the password for {e['name']}?"):
            self.entries = [x for x in self.entries if x["id"]!=e["id"]]
            self.selected_id = None
            self._save(); self._refresh()

    def _change_master(self):
        from tkinter.simpledialog import askstring
        old = askstring("Change password","Current password:", show="*", parent=self)
        if not old: return
        try:
            with open(get_data_file(),"rb") as f: raw=f.read()
            _decrypt_blob(raw[18:], *derive_keys(old, raw[:16]))
        except: messagebox.showerror("Error","Wrong password."); return
        new1 = askstring("Change password","New password:", show="*", parent=self)
        if not new1: return
        new2 = askstring("Change password","Confirm:", show="*", parent=self)
        if new1 != new2: messagebox.showerror("Error","Passwords do not match."); return
        self.salt = secrets.token_bytes(16)
        self.enc_key, self.mac_key = derive_keys(new1, self.salt)
        self._save()
        messagebox.showinfo("Done","Password changed!")

    def _open_settings(self):
        dlg = SettingsDialog(self)
        self.wait_window(dlg)

    def apply_theme(self):
        T = get_theme(); self.T = T
        ctk.set_appearance_mode(T["mode"])
        # Only destroy direct CTkFrame/CTk widgets that belong to App's own
        # layout (sidebar, main). winfo_children() also returns child
        # Toplevel windows (like SettingsDialog) since they're technically
        # children of App - destroying those would close open dialogs.
        for w in self.winfo_children():
            if not isinstance(w, tk.Toplevel):
                w.destroy()
        self.configure(fg_color=T["main_bg"])
        self._build_ui(); self._refresh()

    # ── CSV Import ─────────────────────────────────────────────────────────────
    def import_csv(self):
        path = filedialog.askopenfilename(
            title="Select CSV file", filetypes=[("CSV","*.csv"),("All files","*.*")])
        if not path: return
        imported = 0
        next_id  = max((e["id"] for e in self.entries), default=0)+1
        try:
            with open(path,"r",encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get("name") or row.get("title") or row.get("Name") or row.get("Title","")
                    user = row.get("username") or row.get("email") or row.get("Username") or row.get("Email","")
                    pw   = row.get("password") or row.get("Password","")
                    url  = row.get("url") or row.get("URL") or row.get("login_uri","")
                    note = row.get("note") or row.get("notes") or row.get("Note","")
                    if name and pw:
                        self.entries.append({"id":next_id,"name":name,"user":user,
                            "pass":pw,"url":url,"note":note,"category":"Other",
                            "changed":now_str(),"fav":False})
                        next_id += 1; imported += 1
            self._save(); self._refresh()
            messagebox.showinfo("Import complete",f"Imported {imported} entries.")
        except Exception as ex:
            messagebox.showerror("Import error",str(ex))

    # ── PDF Export ─────────────────────────────────────────────────────────────
    def export_pdf(self, show_passwords=None):
        if not HAS_PDF:
            messagebox.showwarning("Missing","Install reportlab: pip install reportlab"); return
        if show_passwords is None:
            dlg = PDFExportDialog(self)
            self.wait_window(dlg)
            if dlg.result is None: return
            show_passwords = dlg.result
        path = filedialog.asksaveasfilename(
            title="Save PDF", defaultextension=".pdf",
            filetypes=[("PDF","*.pdf")])
        if not path: return
        try:
            doc = SimpleDocTemplate(path, pagesize=A4,
                leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
            styles = getSampleStyleSheet()
            elems  = []
            elems.append(Paragraph(f"{APP_TITLE} - Export", styles["Title"]))
            elems.append(Paragraph(f"Exported: {now_str()}", styles["Normal"]))
            elems.append(Spacer(1,16))

            if show_passwords:
                headers = ["Service","Username","Password","Category","URL","Note"]
            else:
                headers = ["Service","Username","Category","URL","Note","Strength"]
            data = [headers]
            for e in sorted(self.entries, key=lambda x: x["name"].lower()):
                s = pw_strength(e["pass"])
                if show_passwords:
                    data.append([e["name"], e.get("user",""), e.get("pass",""),
                                 e.get("category",""), e.get("url","")[:30], e.get("note","")[:30]])
                else:
                    data.append([e["name"], e.get("user",""), e.get("category",""),
                                 e.get("url","")[:35], e.get("note","")[:40],
                                 STRENGTH_LABELS[s]])

            col_widths = [80,100,100,65,85,85] if show_passwords else [90,110,70,100,100,65]
            tbl = Table(data, repeatRows=1, colWidths=col_widths)
            style_cmds = [
                ("BACKGROUND", (0,0),(-1,0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR",  (0,0),(-1,0), colors.white),
                ("FONTNAME",   (0,0),(-1,0), "Helvetica-Bold"),
                ("FONTSIZE",   (0,0),(-1,-1), 8),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#f8fafc")]),
                ("GRID",       (0,0),(-1,-1), 0.25, colors.HexColor("#e2e8f0")),
                ("VALIGN",     (0,0),(-1,-1), "MIDDLE"),
                ("TOPPADDING", (0,0),(-1,-1), 5),
                ("BOTTOMPADDING",(0,0),(-1,-1),5),
            ]
            if show_passwords:
                style_cmds += [
                    ("TEXTCOLOR", (2,1),(2,-1), colors.HexColor("#dc2626")),
                    ("FONTNAME",  (2,1),(2,-1), "Helvetica-Bold"),
                    ("BACKGROUND",(2,0),(2,0),  colors.HexColor("#dc2626")),
                ]
            tbl.setStyle(TableStyle(style_cmds))
            elems.append(tbl)
            elems.append(Spacer(1,12))
            if show_passwords:
                elems.append(Paragraph(
                    "CONFIDENTIAL: This document contains passwords in plain text. Keep it secure and delete after use.",
                    styles["Normal"]))
            else:
                elems.append(Paragraph(
                    "This PDF does not contain passwords. Safe to store as reference.",
                    styles["Normal"]))
            doc.build(elems)
            messagebox.showinfo("Done",f"PDF saved: {path}")
        except Exception as ex:
            messagebox.showerror("Error",str(ex))


# ── Master Password Dialog ─────────────────────────────────────────────────────
class PDFExportDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Export PDF")
        self.resizable(False, False)
        self.result = None
        T = parent.T
        self.configure(fg_color=T["main_bg"])
        self.grab_set()
        # Keep parent's auto-lock timer from firing while this dialog is open
        self.bind("<Motion>",   lambda e: parent._reset_activity(), add="+")
        self.bind("<KeyPress>", lambda e: parent._reset_activity(), add="+")
        self.bind("<Button>",   lambda e: parent._reset_activity(), add="+")

        ctk.CTkLabel(self, text="Export to PDF", font=("Segoe UI",fnt(15),"bold")).pack(pady=(24,4))
        ctk.CTkLabel(self, text="Choose what to include in the PDF:",
            font=("Segoe UI",fnt(11)), text_color=T["text_muted"]).pack(pady=(0,20))

        opt1 = ctk.CTkFrame(self, corner_radius=10)
        opt1.pack(fill="x", padx=28, pady=6)
        ctk.CTkLabel(opt1, text="Metadata only",
            font=("Segoe UI",fnt(12),"bold"), anchor="w").pack(fill="x", padx=14, pady=(12,2))
        ctk.CTkLabel(opt1, text="Service, username, category, URL and note. No passwords included.",
            font=("Segoe UI",fnt(10)), text_color=T["text_muted"],
            anchor="w", wraplength=260, justify="left").pack(fill="x", padx=14, pady=(0,12))
        ctk.CTkButton(opt1, text="Export without passwords", height=36, corner_radius=8,
            font=("Segoe UI",fnt(11)), command=lambda: self._pick(False)).pack(padx=14, pady=(0,14), fill="x")

        opt2 = ctk.CTkFrame(self, corner_radius=10, border_width=1, border_color="#dc2626")
        opt2.pack(fill="x", padx=28, pady=6)
        ctk.CTkLabel(opt2, text="Include passwords", font=("Segoe UI",fnt(12),"bold"),
            text_color="#dc2626", anchor="w").pack(fill="x", padx=14, pady=(12,2))
        ctk.CTkLabel(opt2, text="Exports all passwords in plain text. Keep this file secure!",
            font=("Segoe UI",fnt(10)), text_color=T["text_muted"],
            anchor="w", wraplength=260, justify="left").pack(fill="x", padx=14, pady=(0,12))
        ctk.CTkButton(opt2, text="Export with passwords", height=36, corner_radius=8,
            font=("Segoe UI",fnt(11)), fg_color="#dc2626", hover_color="#991b1b", text_color="#ffffff",
            command=lambda: self._pick(True)).pack(padx=14, pady=(0,14), fill="x")

        ctk.CTkButton(self, text="Cancel", height=32, corner_radius=8,
            fg_color="transparent", border_width=1,
            border_color=("gray50","gray60"), text_color=("gray20","gray80"),
            command=self.destroy).pack(pady=(8,20), padx=28, fill="x")

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width()  - 340) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 420) // 2
        self.geometry(f"340x420+{x}+{y}")
        self.lift(); self.attributes("-topmost", True)
        self.after(150, lambda: self.attributes("-topmost", False))
        self.focus_force()

    def _confirm_with_passwords(self):
        return messagebox.askyesno("Are you sure?", "This will export all passwords in plain text. Store the PDF securely and delete after use. Continue?", parent=self)

    def _pick(self, include_passwords):
        if include_passwords and not self._confirm_with_passwords():
            return
        self.result = include_passwords
        self.destroy()


class HistoryDialog(ctk.CTkToplevel):
    def __init__(self, parent, entry):
        super().__init__(parent)
        self.title("Password History")
        self.resizable(False, False)
        T = parent.T
        self.configure(fg_color=T["main_bg"])
        self.grab_set()
        # Keep parent's auto-lock timer from firing while this dialog is open
        self.bind("<Motion>",   lambda e: parent._reset_activity(), add="+")
        self.bind("<KeyPress>", lambda e: parent._reset_activity(), add="+")
        self.bind("<Button>",   lambda e: parent._reset_activity(), add="+")

        history = entry.get("history", [])

        ctk.CTkLabel(self, text=f"History for {entry['name']}",
            font=("Segoe UI", fnt(15), "bold")).pack(pady=(24,4), padx=24)
        ctk.CTkLabel(self, text="Previous passwords for this entry (last 3 kept)",
            font=("Segoe UI", fnt(11)), text_color=T["text_muted"]).pack(pady=(0,16), padx=24)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=(0,8))

        if not history:
            ctk.CTkLabel(body, text="No previous passwords yet.\nHistory is recorded whenever you change a password.",
                font=("Segoe UI", fnt(11)), text_color=T["text_muted"],
                justify="left").pack(pady=20)
        else:
            for i, h in enumerate(history):
                row = ctk.CTkFrame(body, corner_radius=10, fg_color=T["card_bg"])
                row.pack(fill="x", pady=4)

                inner = ctk.CTkFrame(row, fg_color="transparent")
                inner.pack(fill="x", padx=12, pady=10)

                label_text = "Most recent" if i == 0 else f"{i+1} changes ago"
                ctk.CTkLabel(inner, text=label_text, font=("Segoe UI", fnt(9), "bold"),
                    text_color=T["accent"], anchor="w").pack(fill="x")

                pw_row = ctk.CTkFrame(inner, fg_color="transparent")
                pw_row.pack(fill="x", pady=(4,0))

                pw_var = tk.StringVar(value="•" * len(h["pass"]))
                pw_label = ctk.CTkLabel(pw_row, textvariable=pw_var,
                    font=("Consolas", fnt(12)), text_color=T["text_primary"], anchor="w")
                pw_label.pack(side="left", fill="x", expand=True)

                state = {"shown": False}
                def toggle(pv=pw_var, pw=h["pass"], st=state):
                    st["shown"] = not st["shown"]
                    pv.set(pw if st["shown"] else "•" * len(pw))

                ctk.CTkButton(pw_row, text="👁", width=30, height=26, corner_radius=6,
                    fg_color=("gray85","gray30"), hover_color=("gray75","gray40"),
                    command=toggle).pack(side="left", padx=(6,0))

                ctk.CTkButton(pw_row, text="Copy", width=55, height=26, corner_radius=6,
                    fg_color=("gray85","gray30"), hover_color=("gray75","gray40"),
                    text_color=T["text_primary"], font=("Segoe UI", fnt(9)),
                    command=lambda pw=h["pass"]: self._copy_hist(pw)
                ).pack(side="left", padx=(4,0))

                changed_at = h.get("changed_at", "unknown date")
                ctk.CTkLabel(inner, text=f"Changed: {changed_at}",
                    font=("Segoe UI", fnt(9)), text_color=T["text_muted"],
                    anchor="w").pack(fill="x", pady=(4,0))

        ctk.CTkButton(self, text="Close", height=36, corner_radius=8,
            command=self.destroy).pack(pady=(4,20), padx=24, fill="x")

        self.update_idletasks()
        w = 380
        h_height = min(560, 220 + len(history) * 110)
        x = parent.winfo_x() + (parent.winfo_width()  - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h_height) // 2
        self.geometry(f"{w}x{h_height}+{x}+{y}")
        self.lift(); self.attributes("-topmost", True)
        self.after(150, lambda: self.attributes("-topmost", False))
        self.focus_force()

    def _copy_hist(self, pw):
        if HAS_CLIP:
            import pyperclip
            pyperclip.copy(pw)


class MasterDialog(ctk.CTkToplevel):
    def __init__(self, parent, new=False):
        super().__init__(parent)
        self.title(APP_TITLE)
        self.resizable(False, False)
        self.result = None
        T = parent.T
        self.configure(fg_color=T["main_bg"])
        self.grab_set()
        # Keep parent's auto-lock timer from firing while this dialog is open
        self.bind("<Motion>",   lambda e: parent._reset_activity(), add="+")
        self.bind("<KeyPress>", lambda e: parent._reset_activity(), add="+")
        self.bind("<Button>",   lambda e: parent._reset_activity(), add="+")

        # Top accent bar
        accent_bar = ctk.CTkFrame(self, height=4, corner_radius=0, fg_color=T["accent"])
        accent_bar.pack(fill="x")

        # Logo area
        logo_frame = ctk.CTkFrame(self, fg_color=T.get("card_bg", T["main_bg"]),
                                   corner_radius=0)
        logo_frame.pack(fill="x", pady=(0, 0))
        if HAS_HEADER_ICON:
            ctk.CTkLabel(logo_frame, image=_HEADER_ICON, text="").pack(pady=(28, 4))
        else:
            ctk.CTkLabel(logo_frame, text="🔐", font=("Segoe UI", fnt(48)),
                         text_color=T["accent"]).pack(pady=(28, 4))
        ctk.CTkLabel(logo_frame, text=APP_TITLE,
                     font=("Segoe UI", fnt(20), "bold"),
                     text_color=T["text_primary"]).pack()
        ctk.CTkLabel(logo_frame, text="Your private vault",
                     font=("Segoe UI", fnt(11)),
                     text_color=T["text_muted"]).pack(pady=(2, 2))
        ctk.CTkLabel(logo_frame, text=APP_VERSION,
                     font=("Segoe UI", fnt(9)),
                     text_color=T["text_muted"]).pack(pady=(0, 20))

        # Divider
        ctk.CTkFrame(self, height=1, fg_color=T["border"], corner_radius=0).pack(fill="x")

        # Form area
        form = ctk.CTkFrame(self, fg_color=T["main_bg"], corner_radius=0)
        form.pack(fill="x", padx=36, pady=24)

        if new:
            ctk.CTkLabel(form, text="Choose a strong master password",
                font=("Segoe UI", fnt(12)), text_color=T["text_muted"]).pack(anchor="w", pady=(0,12))
        else:
            ctk.CTkLabel(form, text="Welcome back",
                font=("Segoe UI", fnt(13), "bold"), text_color=T["text_primary"]).pack(anchor="w")
            ctk.CTkLabel(form, text="Enter your master password to unlock",
                font=("Segoe UI", fnt(11)), text_color=T["text_muted"]).pack(anchor="w", pady=(2,12))

        ctk.CTkLabel(form, text="Master password", font=("Segoe UI", fnt(11)),
                     text_color=T["text_muted"], anchor="w").pack(fill="x")
        self.pw = ctk.CTkEntry(form, show="*", height=42,
            placeholder_text="Enter password…", corner_radius=8,
            font=("Segoe UI", fnt(13)), border_width=2, border_color=T["border"])
        self.pw.pack(fill="x", pady=(4, 0))
        self.pw.focus()

        self.caps_label = ctk.CTkLabel(form, text="", font=("Segoe UI", fnt(10)),
                     text_color="#f59e0b", anchor="w")
        self.caps_label.pack(fill="x", pady=(2,0))
        self.pw.bind("<KeyPress>",   self._check_caps)
        self.pw.bind("<KeyRelease>", self._check_caps)
        self.pw.bind("<FocusIn>",    self._check_caps)

        self.pw2 = None
        if new:
            ctk.CTkLabel(form, text="Confirm password", font=("Segoe UI", fnt(11)),
                         text_color=T["text_muted"], anchor="w").pack(fill="x", pady=(12,0))
            self.pw2 = ctk.CTkEntry(form, show="*", height=42,
                placeholder_text="Repeat password…", corner_radius=8,
                font=("Segoe UI", fnt(13)), border_width=2, border_color=T["border"])
            self.pw2.pack(fill="x", pady=(4, 0))
            self.pw2.bind("<KeyPress>",   self._check_caps)
            self.pw2.bind("<KeyRelease>", self._check_caps)
            self.pw2.bind("<FocusIn>",    self._check_caps)

        # Buttons
        ctk.CTkButton(form,
            text="Create vault" if new else "Unlock",
            height=42, corner_radius=8,
            font=("Segoe UI", fnt(13), "bold"),
            command=self._ok).pack(fill="x", pady=(20, 6))

        self.bind("<Return>", lambda _: self._ok())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.update_idletasks()
        w, h = 380, (430 if not new else 560)
        x = parent.winfo_x() + (parent.winfo_width() - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.lift(); self.attributes("-topmost", True)
        self.after(150, lambda: self.attributes("-topmost", False))
        self.focus_force()

    def _check_caps(self, event=None):
        """Detect Caps Lock state. On Windows, Tkinter's event.state bit 0x0002
        reflects the actual Caps Lock toggle (not just Shift held), which is
        what we want — this differs from X11 where the same bit can mean
        something else, but this app only targets Windows."""
        try:
            caps_on = bool(event.state & 0x0002) if event else False
        except Exception:
            caps_on = False
        self.caps_label.configure(
            text="⚠ Caps Lock is on" if caps_on else "")

    def _ok(self):
        pw = self.pw.get()
        if not pw:
            messagebox.showwarning("Empty", "Please enter a password.", parent=self); return
        if self.pw2:
            if pw != self.pw2.get():
                messagebox.showerror("Error", "Passwords do not match.", parent=self); return
            if len(pw) < 6:
                messagebox.showwarning("För kort", "Minimum 6 characters.", parent=self); return
        self.result = pw; self.destroy()


# ── Entry Dialog ───────────────────────────────────────────────────────────────
class EntryDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, existing=None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False,False)
        self.result = None
        T = parent.T
        self.configure(fg_color=T["main_bg"])
        self.grab_set()
        # Keep parent's auto-lock timer from firing while this dialog is open
        self.bind("<Motion>",   lambda e: parent._reset_activity(), add="+")
        self.bind("<KeyPress>", lambda e: parent._reset_activity(), add="+")
        self.bind("<Button>",   lambda e: parent._reset_activity(), add="+")

        ctk.CTkLabel(self, text=title, font=("Segoe UI",fnt(15),"bold")).pack(pady=(20,12))

        def row(label, var, show=False):
            ctk.CTkLabel(self, text=label, font=("Segoe UI",fnt(11)),
                anchor="w").pack(fill="x", padx=28, pady=(6,0))
            e = ctk.CTkEntry(self, textvariable=var, width=320, height=36,
                corner_radius=8, show="*" if show else "", font=("Segoe UI",fnt(12)))
            e.pack(padx=28, pady=(2,0)); return e

        self.v_name = tk.StringVar(value=existing["name"] if existing else "")
        self.v_user = tk.StringVar(value=existing.get("user","") if existing else "")
        self.v_pass = tk.StringVar(value=existing.get("pass","") if existing else "")
        self.v_url  = tk.StringVar(value=existing.get("url","")  if existing else "")
        self.v_note = tk.StringVar(value=existing.get("note","") if existing else "")
        self.v_cat  = tk.StringVar(value=existing.get("category","Other") if existing else "Other")

        row("Service / Website *", self.v_name)
        row("Username / Email", self.v_user)

        ctk.CTkLabel(self, text="Password *", font=("Segoe UI",fnt(11)), anchor="w").pack(fill="x",padx=28,pady=(6,0))
        prow = ctk.CTkFrame(self, fg_color="transparent")
        prow.pack(padx=28, pady=(2,0), fill="x")
        self.pw_e = ctk.CTkEntry(prow, textvariable=self.v_pass, width=240,
            height=36, corner_radius=8, show="*", font=("Segoe UI",fnt(12)))
        self.pw_e.pack(side="left")
        self._show = False
        def toggle():
            self._show = not self._show
            self.pw_e.configure(show="" if self._show else "*")
            eye_btn.configure(text="🙈" if self._show else "👁")
        eye_btn = ctk.CTkButton(prow, text="👁", width=36, height=36,
            corner_radius=8, fg_color=("gray85","gray30"), hover_color=("gray75","gray40"), command=toggle)
        eye_btn.pack(side="left", padx=4)

        self.caps_label = ctk.CTkLabel(self, text="", font=("Segoe UI", fnt(10)),
                     text_color="#f59e0b", anchor="w")
        self.caps_label.pack(fill="x", padx=28, pady=(2,0))
        self.pw_e.bind("<KeyPress>",   self._check_caps)
        self.pw_e.bind("<KeyRelease>", self._check_caps)
        self.pw_e.bind("<FocusIn>",    self._check_caps)

        # Generator
        # Strength feedback label
        self.strength_lbl = ctk.CTkLabel(self, text="", font=("Segoe UI",fnt(10)),
            text_color=("gray40","gray70"), wraplength=320, justify="left")
        self.strength_lbl.pack(padx=28, anchor="w")
        self.v_pass.trace_add("write", lambda *_: self._update_strength())

        gen = ctk.CTkFrame(self, corner_radius=10)
        gen.pack(padx=28, pady=(4,8), fill="x")
        ctk.CTkLabel(gen, text="Generate password", font=("Segoe UI",fnt(10),"bold")).pack(anchor="w",padx=10,pady=(8,4))

        self.v_len    = tk.IntVar(value=16)
        self.v_upper  = tk.BooleanVar(value=True)
        self.v_digits = tk.BooleanVar(value=True)
        self.v_syms   = tk.BooleanVar(value=True)

        lrow = ctk.CTkFrame(gen, fg_color="transparent"); lrow.pack(fill="x",padx=10)
        ctk.CTkLabel(lrow, text="Length:", font=("Segoe UI",fnt(10))).pack(side="left")
        ctk.CTkSlider(lrow, from_=8, to=32, variable=self.v_len,
            width=140, number_of_steps=24).pack(side="left",padx=6)
        ctk.CTkLabel(lrow, textvariable=self.v_len, font=("Segoe UI",fnt(10)), width=24).pack(side="left")

        crow = ctk.CTkFrame(gen, fg_color="transparent"); crow.pack(fill="x",padx=10,pady=(4,8))
        for txt, var in [("A–Z",self.v_upper),("0–9",self.v_digits),("!@#",self.v_syms)]:
            ctk.CTkCheckBox(crow, text=txt, variable=var, font=("Segoe UI",fnt(10)),
                width=60).pack(side="left",padx=4)
        ctk.CTkButton(crow, text="⚡ Generate", width=100, height=28, corner_radius=8,
            command=lambda: self.v_pass.set(generate_password(
                self.v_len.get(),self.v_upper.get(),self.v_digits.get(),self.v_syms.get()))
        ).pack(side="right",padx=4)

        row("URL (optional)", self.v_url)
        ctk.CTkLabel(self, text="Category", font=("Segoe UI",fnt(11)), anchor="w").pack(fill="x",padx=28,pady=(6,0))
        ctk.CTkOptionMenu(self, values=CATEGORIES, variable=self.v_cat,
            width=320, height=36, corner_radius=8, font=("Segoe UI",fnt(12))).pack(padx=28,pady=(2,0))
        row("Note (optional)", self.v_note)

        bf = ctk.CTkFrame(self, fg_color="transparent"); bf.pack(pady=16)
        ctk.CTkButton(bf, text="Cancel", width=110, fg_color="transparent",
            border_width=1, border_color=("gray60","gray50"), text_color=("gray20","gray80"), command=self.destroy).pack(side="left",padx=6)
        ctk.CTkButton(bf, text="Save", width=110, command=self._ok).pack(side="left",padx=6)

        self.bind("<Return>", lambda _: self._ok())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.update_idletasks()
        self.geometry(f"+{parent.winfo_x()+80}+{parent.winfo_y()+40}")
        self.lift(); self.attributes("-topmost",True)
        self.after(150, lambda: self.attributes("-topmost",False))
        self.focus_force()

    def _check_caps(self, event=None):
        """Detect Caps Lock state via the keyboard event's state bitmask."""
        try:
            caps_on = bool(event.state & 0x0002) if event else False
        except Exception:
            caps_on = False
        self.caps_label.configure(
            text="⚠ Caps Lock is on" if caps_on else "")

    def _update_strength(self):
        pw = self.v_pass.get()
        if not pw:
            self.strength_lbl.configure(text=""); return
        s = pw_strength(pw)
        warn, sugg = pw_feedback(pw)
        colors_map = ["#ef4444","#f97316","#eab308","#22c55e","#16a34a","#15803d"]
        labels_map = ["Very weak","Weak","Fair","Good","Strong","Very strong"]
        bar = "●" * (s+1) + "○" * (5-s)
        txt = f"{bar}  {labels_map[s]}"
        if warn:  txt += f"  ⚠ {warn}"
        self.strength_lbl.configure(text=txt, text_color=colors_map[s])

    def _ok(self):
        name = self.v_name.get().strip()
        pw   = self.v_pass.get()
        if not name or not pw:
            messagebox.showwarning("Missing","Service and password are required.",parent=self); return
        self.result = {"name":name,"user":self.v_user.get().strip(),"pass":pw,
                       "url":self.v_url.get().strip(),"note":self.v_note.get().strip(),
                       "category":self.v_cat.get()}
        self.destroy()


# ── Settings Dialog ────────────────────────────────────────────────────────────
class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Settings")
        self.resizable(False,False)
        self.grab_set()
        # Keep parent's auto-lock timer from firing while this dialog is open
        self.bind("<Motion>",   lambda e: parent._reset_activity(), add="+")
        self.bind("<KeyPress>", lambda e: parent._reset_activity(), add="+")
        self.bind("<Button>",   lambda e: parent._reset_activity(), add="+")
        T = parent.T
        self.configure(fg_color=T["main_bg"])

        settings = load_settings()
        self.v_path  = tk.StringVar(value=settings.get("data_file", DEFAULT_DATA_FILE))
        self.v_theme = tk.StringVar(value=settings.get("theme","Light"))

        ctk.CTkLabel(self, text="⚙️  Settings",
            font=("Segoe UI",fnt(16),"bold")).pack(pady=(20,4))

        # ── Tabs ──
        tabs = ctk.CTkTabview(self, width=520, corner_radius=12)
        tabs.pack(padx=20, pady=10, fill="both", expand=True)
        t_theme  = tabs.add("🎨 Theme")
        t_file   = tabs.add("📁 Data file")
        t_cats   = tabs.add("🏷 Categories")
        t_mobile = tabs.add("📱 Mobile")
        t_ext    = tabs.add("🧩 Extension")
        t_import = tabs.add("📥 Import / Export")

        # Theme tab
        grid = ctk.CTkFrame(t_theme, fg_color="transparent")
        grid.pack(fill="both", expand=True, pady=8)
        self._theme_frames = {}
        theme_names = list(THEMES.keys())  # includes Midnatt
        for i, name in enumerate(theme_names):
            tc = THEMES[name]
            col, row_n = i%3, i//3
            outer = ctk.CTkFrame(grid, corner_radius=12, fg_color=tc["sidebar_bg"],
                border_width=3,
                border_color=tc["accent"] if name==self.v_theme.get() else tc["sidebar_bg"])
            outer.grid(row=row_n, column=col, padx=6, pady=6, sticky="ew")
            grid.columnconfigure(col, weight=1)
            ctk.CTkLabel(outer, text=name, font=("Segoe UI",fnt(11),"bold"),
                text_color=tc["sidebar_fg"]).pack(padx=10,pady=(8,2))
            preview = ctk.CTkFrame(outer, fg_color=tc["main_bg"], corner_radius=6, height=28)
            preview.pack(fill="x", padx=8, pady=(0,8))
            ctk.CTkLabel(preview, text="  Abc", font=("Segoe UI",fnt(9)),
                text_color=tc["text_primary"]).pack(side="left")
            ctk.CTkLabel(preview, text="▶ ", font=("Segoe UI",fnt(9)),
                fg_color=tc["accent"], text_color="#ffffff",
                corner_radius=4).pack(side="right")
            for w in [outer]+outer.winfo_children()+preview.winfo_children():
                try: w.bind("<Button-1>", lambda e,n=name: self._pick(n))
                except: pass
            self._theme_frames[name] = outer

        # File tab
        ctk.CTkLabel(t_file, text="Path to .enc file:",
            font=("Segoe UI",fnt(11)), anchor="w").pack(fill="x",padx=8,pady=(12,4))
        prow = ctk.CTkFrame(t_file, fg_color="transparent"); prow.pack(fill="x",padx=8)
        ctk.CTkEntry(prow, textvariable=self.v_path, width=270,
            height=36, corner_radius=8).pack(side="left")
        ctk.CTkButton(prow, text="Open existing…", width=110, height=36,
            corner_radius=8, command=self._open_existing).pack(side="left",padx=4)
        ctk.CTkButton(prow, text="New…", width=70, height=36,
            corner_radius=8, fg_color=("gray80","gray30"),
            text_color=("gray10","gray90"), hover_color=("gray70","gray40"),
            command=self._browse).pack(side="left",padx=(0,2))
        ctk.CTkLabel(t_file,
            text="\"Open existing\" points the app at an .enc file you already have (e.g. after moving to a new PC or restoring a backup). \"New\" creates a fresh file at a location you choose.",
            font=("Segoe UI",fnt(9)), text_color=T["text_muted"],
            wraplength=420, justify="left").pack(padx=8,pady=(6,2),anchor="w")
        ctk.CTkLabel(t_file, text="Tip: Choose a OneDrive/Dropbox folder for automatic backup.",
            font=("Segoe UI",fnt(9)), text_color=T["text_muted"],
            wraplength=420).pack(padx=8,pady=(0,8),anchor="w")
        ctk.CTkButton(t_file, text="Reset to default path", width=200,
            fg_color=("gray80","gray30"),
            text_color=("gray10","gray90"),
            hover_color=("gray70","gray40"),
            command=lambda: self.v_path.set(DEFAULT_DATA_FILE)).pack(pady=4)

        ctk.CTkFrame(t_file, height=1, fg_color=T["border"]).pack(fill="x", padx=8, pady=(16,12))

        ctk.CTkLabel(t_file, text="Security",
            font=("Segoe UI",fnt(11),"bold"), anchor="w").pack(fill="x", padx=8)

        autolock_settings = load_settings()
        self.v_autolock = tk.BooleanVar(value=autolock_settings.get("auto_lock_enabled", True))
        autolock_row = ctk.CTkFrame(t_file, fg_color="transparent")
        autolock_row.pack(fill="x", padx=8, pady=(6,2))
        ctk.CTkSwitch(autolock_row, text="Auto-lock after 10 minutes of inactivity",
            variable=self.v_autolock, onvalue=True, offvalue=False,
            font=("Segoe UI",fnt(10))).pack(side="left")
        ctk.CTkLabel(t_file,
            text="When off, the vault stays unlocked until you close the app or click \"Exit\" manually. Not recommended on shared computers.",
            font=("Segoe UI",fnt(9)), text_color=T["text_muted"],
            wraplength=420, justify="left").pack(padx=8, pady=(2,8), anchor="w")

        # Import/Export tab
        # ── Categories tab ────────────────────────────────────────────────────
        ctk.CTkLabel(t_cats, text="Manage categories",
            font=("Segoe UI",fnt(13),"bold")).pack(pady=(12,4))
        ctk.CTkLabel(t_cats,
            text="Add, rename or delete categories. Drag the ☰ handle to reorder.\nEntries using a deleted category will be moved to \"Other\".",
            font=("Segoe UI",fnt(10)), text_color=T["text_muted"],
            wraplength=440, justify="left").pack(padx=8, anchor="w")

        # List frame
        list_outer = ctk.CTkFrame(t_cats, corner_radius=8)
        list_outer.pack(fill="both", expand=True, padx=8, pady=8)

        self._cat_listbox_frame = ctk.CTkScrollableFrame(list_outer, height=160, corner_radius=0, fg_color="transparent")
        self._cat_listbox_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self._cat_rows = []
        self._cat_row_widgets = {}     # category name -> row frame (for drag hit-testing/highlight)
        self._cat_badge_labels = {}    # category name -> position-number label
        self._drag_cat = None          # category currently being dragged, or None
        self._drag_order = None        # in-memory order while dragging (not yet saved)
        self._build_cat_list()

        # Bound once, not per-rebuild: these fire on every mouse move/release
        # in the whole app but no-op immediately unless a drag is in
        # progress (self._drag_cat is set), so they're harmless the rest
        # of the time. add="+" so we don't clobber the app's existing
        # global bindings (e.g. the auto-lock activity tracker).
        self._cat_listbox_frame.bind_all("<B1-Motion>", self._on_drag_motion, add="+")
        self._cat_listbox_frame.bind_all("<ButtonRelease-1>", self._end_drag, add="+")

        # Add new category row
        add_row = ctk.CTkFrame(t_cats, fg_color="transparent")
        add_row.pack(fill="x", padx=8, pady=(0,4))
        self.v_new_cat = tk.StringVar()
        ctk.CTkEntry(add_row, textvariable=self.v_new_cat, placeholder_text="New category name…",
            height=34, corner_radius=8, font=("Segoe UI",fnt(12))).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(add_row, text="＋ Add", width=80, height=34, corner_radius=8,
            command=self._add_category).pack(side="left", padx=(6,0))

        # ── Mobile tab ───────────────────────────────────────────────────────
        ctk.CTkLabel(t_mobile, text="Mobile Access (WiFi)",
            font=("Segoe UI", fnt(13), "bold")).pack(pady=(12,4))
        ctk.CTkLabel(t_mobile,
            text=f"Connect your phone via WiFi using the {APP_TITLE} mobile app.",
            font=("Segoe UI", fnt(10)), text_color=T["text_muted"],
            wraplength=440).pack(padx=8, anchor="w")

        # LAN IP display
        import socket
        try:
            lan_ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            lan_ip = "unknown"
        ip_frame = ctk.CTkFrame(t_mobile, corner_radius=8)
        ip_frame.pack(fill="x", padx=8, pady=(12,4))
        ctk.CTkLabel(ip_frame, text="Your computer's IP address:",
            font=("Segoe UI", fnt(10)), anchor="w").pack(fill="x", padx=12, pady=(10,2))
        ctk.CTkLabel(ip_frame, text=f"{lan_ip}:{API_MOBILE_PORT}",
            font=("Consolas", fnt(14), "bold"), text_color=T["accent"],
            anchor="w").pack(fill="x", padx=12, pady=(0,10))
        ctk.CTkLabel(ip_frame,
            text="Open this address in Brave on your phone to access the mobile app.",
            font=("Segoe UI", fnt(9)), text_color=T["text_muted"],
            wraplength=420, anchor="w").pack(fill="x", padx=12, pady=(0,10))

        # PIN setup
        settings_data = load_settings()
        self.v_pin = tk.StringVar(value=settings_data.get("mobile_pin",""))
        pin_frame = ctk.CTkFrame(t_mobile, corner_radius=8)
        pin_frame.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(pin_frame, text="Mobile PIN (6-10 digits):",
            font=("Segoe UI", fnt(10)), anchor="w").pack(fill="x", padx=12, pady=(10,2))
        pin_row = ctk.CTkFrame(pin_frame, fg_color="transparent")
        pin_row.pack(fill="x", padx=12, pady=(0,10))
        ctk.CTkEntry(pin_row, textvariable=self.v_pin, width=160, height=34,
            show="*", placeholder_text="Enter 6+ digit PIN…",
            corner_radius=8, font=("Segoe UI", fnt(12))).pack(side="left")
        ctk.CTkLabel(pin_row, text="Required to access passwords from phone",
            font=("Segoe UI", fnt(9)), text_color=T["text_muted"]).pack(side="left", padx=(10,0))

        ctk.CTkLabel(t_mobile,
            text="⚠ Only enable this on networks you trust (e.g. your home WiFi), "
                 "not public/office WiFi - anyone else on the same network can "
                 "reach this feature, and a short PIN can be guessed. The app "
                 "locks a device out for a minute after 5 wrong PINs.",
            font=("Segoe UI", fnt(9)), text_color=T["danger"],
            wraplength=440, justify="left").pack(padx=8, pady=(4,0), anchor="w")

        ctk.CTkLabel(t_mobile,
            text="Make sure your phone and computer are on the same WiFi network. "
                 "If you're turning mobile access on for the first time, restart "
                 "the app afterwards for it to take effect.",
            font=("Segoe UI", fnt(9)), text_color=T["text_muted"],
            wraplength=440, justify="left").pack(padx=8, pady=(8,0), anchor="w")

        # ── Extension tab ────────────────────────────────────────────────────
        ctk.CTkLabel(t_ext, text="Browser Extension Pairing",
            font=("Segoe UI", fnt(13), "bold")).pack(pady=(12,4))
        ctk.CTkLabel(t_ext,
            text="The extension needs this one-time pairing code to talk to the "
                 "app. Copy it and paste it into the extension's options page "
                 "(right-click the extension icon → Options).",
            font=("Segoe UI", fnt(10)), text_color=T["text_muted"],
            wraplength=440, justify="left").pack(padx=8, anchor="w")

        ext_frame = ctk.CTkFrame(t_ext, corner_radius=8)
        ext_frame.pack(fill="x", padx=8, pady=(12,4))
        ctk.CTkLabel(ext_frame, text="Pairing code:",
            font=("Segoe UI", fnt(10)), anchor="w").pack(fill="x", padx=12, pady=(10,2))
        self.v_ext_secret = tk.StringVar(value=get_ext_secret())
        secret_row = ctk.CTkFrame(ext_frame, fg_color="transparent")
        secret_row.pack(fill="x", padx=12, pady=(0,10))
        secret_entry = ctk.CTkEntry(secret_row, textvariable=self.v_ext_secret,
            width=300, height=34, corner_radius=8, font=("Consolas", fnt(11)),
            state="readonly")
        secret_entry.pack(side="left")
        ctk.CTkButton(secret_row, text="Copy", width=70, height=34, corner_radius=8,
            fg_color=("gray80","gray30"), text_color=("gray10","gray90"),
            hover_color=("gray70","gray40"),
            command=self._copy_ext_secret).pack(side="left", padx=(6,0))

        ctk.CTkButton(t_ext, text="🔄  Regenerate code (revokes old pairing)",
            width=280, height=34, corner_radius=8,
            fg_color=T["danger"], text_color="#ffffff", hover_color="#991b1b",
            command=self._regenerate_ext_secret).pack(pady=(4,4))
        ctk.CTkLabel(t_ext,
            text="Regenerating immediately invalidates the old code - the "
                 "extension will show \"App not running\" until you re-paste "
                 "the new code into it.",
            font=("Segoe UI", fnt(9)), text_color=T["text_muted"],
            wraplength=440, justify="left").pack(padx=8, pady=(0,8), anchor="w")

        ctk.CTkLabel(t_import, text="Import passwords",
            font=("Segoe UI",fnt(13),"bold")).pack(pady=(12,4))
        ctk.CTkLabel(t_import,
            text="Import from CSV (works with Chrome, Firefox, Bitwarden, LastPass etc.)",
            font=("Segoe UI",fnt(10)), text_color=T["text_muted"], wraplength=420).pack(padx=8)
        ctk.CTkButton(t_import, text="📥  Import CSV", width=200, height=36,
            corner_radius=10, command=self._do_import).pack(pady=8)

        ctk.CTkLabel(t_import, text="Export passwords",
            font=("Segoe UI",fnt(13),"bold")).pack(pady=(12,4))
        ctk.CTkLabel(t_import,
            text="Export a PDF with metadata (passwords are NOT shown in plain text).",
            font=("Segoe UI",fnt(10)), text_color=T["text_muted"], wraplength=420).pack(padx=8)
        ctk.CTkButton(t_import, text="📄  Export PDF", width=200, height=36,
            corner_radius=10, command=self._do_export).pack(pady=8)

        # Buttons
        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(pady=12)
        ctk.CTkButton(bf, text="Cancel", width=120, fg_color="transparent",
            border_width=1, border_color=("gray50","gray60"),
            text_color=("gray20","gray80"),
            hover_color=("gray85","gray30"),
            command=self._cancel).pack(side="left", padx=6)
        ctk.CTkButton(bf, text="Save & apply", width=160,
            command=self._save).pack(side="left", padx=6)
        ctk.CTkButton(bf, text="⏻  Exit app", width=110,
            fg_color="#dc2626", hover_color="#991b1b", text_color="#ffffff",
            command=self._exit_app).pack(side="left", padx=(16,0))

        self.update_idletasks()
        self.geometry(f"+{parent.winfo_x()+50}+{parent.winfo_y()+30}")
        self.lift(); self.attributes("-topmost",True)
        self.after(150, lambda: self.attributes("-topmost",False))
        self.focus_force()

    def _cancel(self):
        # If categories were reordered via drag-and-drop while this dialog
        # was open, refresh the sidebar so the new order shows immediately -
        # this is safe to call here since it only runs once, on close.
        self.destroy()
        self.parent.apply_theme()

    def _exit_app(self):
        self.destroy()
        self.parent.destroy()

    def _build_cat_list(self):
        for w in self._cat_listbox_frame.winfo_children():
            w.destroy()
        self._cat_rows = []
        self._cat_row_widgets = {}
        self._cat_badge_labels = {}
        cats = load_settings().get("custom_categories", list(CATEGORIES))
        T = self.parent.T
        for i, cat in enumerate(cats):
            row = ctk.CTkFrame(self._cat_listbox_frame, fg_color=T["card_bg"], corner_radius=6,
                border_width=0, border_color=T["accent"])
            row.pack(fill="x", pady=2)
            self._cat_row_widgets[cat] = row

            # Position badge - purely informational now (drag the handle
            # next to it to reorder; no longer editable).
            badge = ctk.CTkLabel(row, text=str(i+1), width=26, height=26, corner_radius=6,
                fg_color=T["accent"], text_color="#ffffff",
                font=("Segoe UI", fnt(11), "bold"))
            badge.pack(side="left", padx=(6,2), pady=4)
            self._cat_badge_labels[cat] = badge

            # Drag handle - press and drag this to reorder the category.
            handle = ctk.CTkLabel(row, text="☰", width=24, font=("Segoe UI", fnt(13)),
                text_color=T["text_muted"], cursor="fleur")
            handle.pack(side="left", padx=(0,2))
            handle.bind("<ButtonPress-1>", lambda e, c=cat: self._start_drag(c))

            v = tk.StringVar(value=cat)
            entry = ctk.CTkEntry(row, textvariable=v, height=30,
                corner_radius=6, font=("Segoe UI",fnt(11)))
            entry.pack(side="left", fill="x", expand=True, pady=4)
            self._cat_rows.append((cat, v))

            ctk.CTkButton(row, text="Edit", width=44, height=30, corner_radius=6, font=("Segoe UI",fnt(9)),
                fg_color="transparent", text_color=T["accent"],
                hover_color=T["border"],
                command=lambda old=cat, vr=v: self._rename_category(old, vr)
            ).pack(side="left", padx=(4,0))
            if cat != "Other":
                ctk.CTkButton(row, text="✕", width=30, height=30, corner_radius=6,
                    fg_color="transparent", text_color=T["danger"],
                    hover_color=T["border"],
                    command=lambda c=cat: self._delete_category(c)
                ).pack(side="left", padx=(2,4))

    def _highlight_row(self, cat, on):
        row = self._cat_row_widgets.get(cat)
        if not row or not row.winfo_exists():
            return
        T = self.parent.T
        if on:
            row.configure(border_width=2, fg_color=T["row_alt"])
        else:
            row.configure(border_width=0, fg_color=T["card_bg"])

    def _start_drag(self, cat):
        self._drag_cat = cat
        self._drag_order = self._get_custom_cats()  # working copy, only saved on drop
        self._highlight_row(cat, True)

    def _on_drag_motion(self, event):
        if not self._drag_cat or not self._cat_listbox_frame.winfo_exists():
            return
        cats = self._drag_order
        if cats is None or self._drag_cat not in cats:
            return

        # Which row is the cursor currently over? Compare against each
        # row's on-screen midpoint - works correctly even while the list
        # is scrolled, since winfo_rooty() reflects actual screen position.
        target_index = len(cats)
        for i, c in enumerate(cats):
            row = self._cat_row_widgets.get(c)
            if not row or not row.winfo_exists():
                continue
            mid = row.winfo_rooty() + row.winfo_height() / 2
            if event.y_root < mid:
                target_index = i
                break

        cur_index = cats.index(self._drag_cat)
        if target_index == cur_index or target_index == cur_index + 1:
            return  # dropping here wouldn't change anything - skip the reflow

        cats.pop(cur_index)
        insert_at = target_index if target_index < cur_index else target_index - 1
        cats.insert(insert_at, self._drag_cat)
        self._reflow_cat_rows(cats)

    def _reflow_cat_rows(self, cats):
        """Re-stack the already-existing row widgets into a new order
        in place - no destroy/recreate, so nothing flickers. Much cheaper
        than a full _build_cat_list() and safe to call on every step of
        a drag."""
        for cat in cats:
            row = self._cat_row_widgets.get(cat)
            if row and row.winfo_exists():
                row.pack_forget()
                row.pack(fill="x", pady=2)
        for i, cat in enumerate(cats):
            badge = self._cat_badge_labels.get(cat)
            if badge and badge.winfo_exists():
                badge.configure(text=str(i+1))

    def _end_drag(self, event):
        if not self._drag_cat:
            return
        self._highlight_row(self._drag_cat, False)
        if self._drag_order:
            self._reorder_custom_cats(self._drag_order)  # single write, on drop
        self._drag_cat = None
        self._drag_order = None

    def _reorder_custom_cats(self, cats):
        """Lightweight category-order save used during drag-and-drop.
        Unlike _save_custom_cats(), this does NOT rebuild the entire main
        window (sidebar/UI) on every drag step - that would be wasteful
        and can cause flicker. The sidebar order updates next time it's
        rebuilt (e.g. theme change, app restart, or Save & apply)."""
        s = load_settings()
        s["custom_categories"] = cats
        save_settings(s)
        global CATEGORIES, CAT_GROUPS, CAT_ICONS
        CATEGORIES = cats
        CAT_GROUPS["CATEGORIES"] = cats
        CAT_ICONS = {"All": "All"}
        for c in cats:
            CAT_ICONS[c] = c

    def _get_custom_cats(self):
        return load_settings().get("custom_categories", list(CATEGORIES))

    def _save_custom_cats(self, cats):
        s = load_settings()
        s["custom_categories"] = cats
        save_settings(s)
        global CATEGORIES, CAT_GROUPS, CAT_ICONS
        CATEGORIES = cats
        CAT_GROUPS["CATEGORIES"] = cats
        CAT_ICONS = {"All": "All"}
        for c in cats:
            CAT_ICONS[c] = c
        self.parent.apply_theme()

    def _add_category(self):
        name = self.v_new_cat.get().strip()
        if not name:
            messagebox.showwarning("Empty", "Enter a category name.", parent=self); return
        cats = self._get_custom_cats()
        if name in cats:
            messagebox.showwarning("Exists", f'"{name}" already exists.', parent=self); return
        cats.append(name)
        self._save_custom_cats(cats)
        self.v_new_cat.set("")
        self._build_cat_list()
        messagebox.showinfo("Added", f'Category "{name}" added!', parent=self)

    def _rename_category(self, old_name, var):
        new_name = var.get().strip()
        if not new_name or new_name == old_name: return
        cats = self._get_custom_cats()
        if new_name in cats:
            messagebox.showwarning("Exists", f'"{new_name}" already exists.', parent=self); return
        cats = [new_name if c == old_name else c for c in cats]
        for e in self.parent.entries:
            if e.get("category") == old_name:
                e["category"] = new_name
        self.parent._save()
        self._save_custom_cats(cats)
        self._build_cat_list()
        messagebox.showinfo("Renamed", f'"{old_name}" renamed to "{new_name}".', parent=self)

    def _delete_category(self, cat):
        count = sum(1 for e in self.parent.entries if e.get("category") == cat)
        msg = f'Delete "{cat}"?'
        if count:
            msg += f"\n\n{count} {'entry' if count==1 else 'entries'} will be moved to \"Other\"."
        if not messagebox.askyesno("Delete category", msg, parent=self): return
        for e in self.parent.entries:
            if e.get("category") == cat:
                e["category"] = "Other"
        self.parent._save()
        cats = [c for c in self._get_custom_cats() if c != cat]
        self._save_custom_cats(cats)
        self._build_cat_list()

    def _copy_ext_secret(self):
        if HAS_CLIP:
            import pyperclip
            pyperclip.copy(self.v_ext_secret.get())
            messagebox.showinfo("Copied", "Pairing code copied to clipboard.", parent=self)
        else:
            messagebox.showinfo("Pairing code", self.v_ext_secret.get(), parent=self)

    def _regenerate_ext_secret(self):
        if not messagebox.askyesno("Regenerate pairing code",
                "This immediately revokes the current pairing code.\n"
                "The extension will stop working until you paste the new "
                "code into its options page.\n\nContinue?", parent=self):
            return
        new_secret = regenerate_ext_secret()
        self.v_ext_secret.set(new_secret)
        messagebox.showinfo("Regenerated",
            "New pairing code generated. Update the extension's options page "
            "with the new code.", parent=self)

    def _pick(self, name):
        self.v_theme.set(name)
        for n, frm in self._theme_frames.items():
            tc = THEMES[n]
            frm.configure(border_color=tc["accent"] if n==name else tc["sidebar_bg"])

    def _browse(self):
        cur = self.v_path.get()
        path = filedialog.asksaveasfilename(
            parent=self, title="Choose location for new vault file",
            initialdir=os.path.dirname(cur) or os.path.expanduser("~"),
            initialfile=os.path.basename(cur),
            defaultextension=".enc",
            filetypes=[("Encrypted file","*.enc"),("All files","*.*")])
        if path: self.v_path.set(path)

    def _open_existing(self):
        """Point the app at an existing .enc file (e.g. a backup or a file
        moved from another PC), without overwriting or moving anything."""
        cur = self.v_path.get()
        path = filedialog.askopenfilename(
            parent=self, title="Open existing vault file",
            initialdir=os.path.dirname(cur) or os.path.expanduser("~"),
            filetypes=[("Encrypted file","*.enc"),("All files","*.*")])
        if not path:
            return
        if not os.path.exists(path):
            messagebox.showerror("Not found", "Selected file does not exist.", parent=self)
            return
        self.v_path.set(path)
        messagebox.showinfo("Path selected",
            "Click \"Save & apply\" to start using this vault file. "
            "You'll be asked for its master password the next time you unlock.",
            parent=self)

    def _do_import(self):
        self.destroy()
        self.parent.import_csv()

    def _do_export(self):
        self.destroy()
        self.parent.export_pdf()

    def _save(self):
        new_path  = self.v_path.get().strip()
        new_theme = self.v_theme.get()
        if not new_path:
            messagebox.showwarning("Empty","Please enter a path.",parent=self); return
        old_path = get_data_file()
        if os.path.exists(old_path) and os.path.abspath(old_path)!=os.path.abspath(new_path):
            move = messagebox.askyesnocancel("Move file?",
                f"Move the database file?\nFrom: {old_path}\nTo:   {new_path}",parent=self)
            if move is None: return
            if move:
                try:
                    import shutil
                    os.makedirs(os.path.dirname(new_path) or ".",exist_ok=True)
                    shutil.move(old_path, new_path)
                except Exception as ex:
                    messagebox.showerror("Error",str(ex),parent=self); return
        s = load_settings()
        s["data_file"]  = new_path
        s["theme"]      = new_theme
        if hasattr(self, "v_autolock"):
            s["auto_lock_enabled"] = self.v_autolock.get()
        if hasattr(self, "v_pin"):
            pin = self.v_pin.get().strip()
            if pin and not pin.isdigit():
                messagebox.showwarning("Invalid PIN", "PIN must contain only digits.", parent=self)
                return
            if pin and len(pin) < 6:
                messagebox.showwarning("PIN too short",
                    "Please use at least 6 digits - shorter PINs are too easy "
                    "to guess for something reachable over WiFi.", parent=self)
                return
            was_enabled = bool(load_settings().get("mobile_pin"))
            s["mobile_pin"] = pin
            if pin and not was_enabled:
                messagebox.showinfo("Restart required",
                    "Mobile access is now configured. Restart The LockShed "
                    "for the phone server to start listening.", parent=self)
        save_settings(s)
        self.destroy()
        self.parent.apply_theme()


if __name__ == "__main__":
    app = App()
    app.mainloop()
