#!/usr/bin/env python3
"""
Apex Web Development — self-contained website + backend.

Runs on Python 3 standard library ONLY. No pip installs, no Node.
    python3 server.py            # serves on http://localhost:8080
    PORT=3000 python3 server.py  # custom port

Features:
  - Serves the marketing site (public/)
  - Editable content stored in SQLite (admin edits persist)
  - Live chat: visitors message, admin replies from /admin inbox
  - Contact leads stored + shown in admin
  - Photo uploads (base64 JSON) for portfolio work
  - /admin password-protected panel
"""

import os, json, sqlite3, hashlib, hmac, secrets, base64, mimetypes, time, re, threading
import urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, urlencode

ROOT = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(ROOT, "public")
UPLOADS = os.path.join(ROOT, "uploads")
DB_PATH = os.path.join(ROOT, "apex.db")
PORT = int(os.environ.get("PORT", "8080"))

# Storage: use Postgres when DATABASE_URL is set (production / Render),
# otherwise fall back to a local SQLite file (offline development).
USE_PG = bool(os.environ.get("DATABASE_URL"))
psycopg2 = None
if USE_PG:
    import psycopg2
    import psycopg2.extras

MAX_BODY = 12 * 1024 * 1024          # reject request bodies larger than 12 MB (memory-DoS guard)
SESSION_TTL = 30 * 24 * 3600         # admin sessions expire after 30 days

# Lightweight in-memory per-IP rate limiter (sliding window).
_rl_lock = threading.Lock()
_rl_hits = {}

def rate_ok(key, limit, window):
    now = time.time()
    with _rl_lock:
        if len(_rl_hits) > 20000:        # safety valve against unbounded growth
            _rl_hits.clear()
        q = _rl_hits.setdefault(key, [])
        cutoff = now - window
        drop = 0
        for t in q:
            if t >= cutoff:
                break
            drop += 1
        if drop:
            del q[:drop]
        if len(q) >= limit:
            return False
        q.append(now)
        return True

# Secure API key handling (OWASP: Secrets Management)
# ---------------------------------------------------------------------------
# ALL secrets come from environment variables — nothing is hard-coded, and the
# Stripe secret key is used only server-side (it is NEVER sent to the browser;
# the client only ever gets /api/pay/config -> {enabled, currency}).
# To ROTATE a key: create a new key in the Stripe dashboard, update the
# STRIPE_SECRET_KEY env var in Render, redeploy, then revoke the old key. No
# code change is required. Same pattern for DATABASE_URL.
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "").strip()
STRIPE_CURRENCY = os.environ.get("STRIPE_CURRENCY", "cad").strip().lower()

def stripe_post(path, fields):
    data = urlencode(fields).encode()
    req = urllib.request.Request("https://api.stripe.com/v1/" + path, data=data)
    req.add_header("Authorization", "Bearer " + STRIPE_SECRET_KEY)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {"error": {"message": "Payment service error."}}

os.makedirs(UPLOADS, exist_ok=True)

# ---------------------------------------------------------------------------
# Default editable content (seeded on first run; afterwards lives in the DB)
# ---------------------------------------------------------------------------
DEFAULT_CONTENT = {
    "business": {
        "name": "Apex Web Development",
        "owner": "Ben Stephan",
        "tagline": "Websites that make local businesses look like the industry leaders they are.",
        "phone": "587-888-7315",
        "email": "apexwebprojects@gmail.com",
        "website": "www.apexweb.ca",
        "location": "Calgary, Alberta — serving businesses everywhere",
        "hours": "Mon–Fri 9am–6pm MT"
    },
    "hero": {
        "eyebrow": "Custom Web Design & Development",
        "headline": "Your business deserves a website that wins customers.",
        "sub": "I build fast, modern, custom websites for local and established businesses — replacing tired, outdated designs with sites that look premium and actually convert.",
        "ctaPrimary": "Get a Free Quote",
        "ctaSecondary": "See My Work",
        "stat1num": "100%", "stat1label": "Custom-built, never templated",
        "stat2num": "1.2s", "stat2label": "Typical load time",
        "stat3num": "24/7", "stat3label": "Direct line to the developer"
    },
    "about": {
        "heading": "Hi, I'm Ben — the developer behind Apex.",
        "body": "I help local and established businesses replace poor, outdated, or DIY websites with something they're proud to share. No bloated page-builders, no agency runaround — you work directly with the person writing the code. Every site is designed from scratch around your brand, your customers, and the results you actually care about.",
        "points": [
            "Hand-coded, custom design — never a recycled template",
            "Built to load fast and rank well on Google",
            "Mobile-first so it looks flawless on every phone",
            "You get a direct line to me, not a support ticket"
        ]
    },
    "services": [
        {"icon": "✦", "title": "Custom Website Design", "desc": "A unique, hand-crafted design built around your brand — not a template thousands of others already use."},
        {"icon": "↻", "title": "Redesigns & Rescues", "desc": "Have an outdated or broken site? I rebuild it into something modern, fast, and credible."},
        {"icon": "⚡", "title": "Performance & SEO", "desc": "Lightning-fast load times and clean, search-friendly code so customers actually find you."},
        {"icon": "▢", "title": "Mobile-First Build", "desc": "Most of your visitors are on a phone. Every site is designed to feel perfect there first."},
        {"icon": "✉", "title": "Lead & Contact Systems", "desc": "Contact forms, click-to-call, live chat, and booking — turn visitors into real inquiries."},
        {"icon": "⚙", "title": "Care & Maintenance", "desc": "Ongoing updates, hosting help, edits, and peace of mind so your site never goes stale."}
    ],
    "pricing": [
        {"name": "Starter", "price": "799", "period": "one-time", "blurb": "Perfect for a clean, professional one-page presence.",
         "features": ["Single-page custom design", "Mobile responsive", "Contact form + click-to-call", "Basic SEO setup", "Up to 5 sections"], "featured": False, "cta": "Start here"},
        {"name": "Business", "price": "1,499", "period": "one-time", "blurb": "The complete multi-page site most local businesses need.",
         "features": ["Up to 6 custom pages", "Premium custom design & animation", "Gallery / portfolio section", "On-page SEO + Google setup", "Live chat integration", "1 month free support"], "featured": True, "cta": "Most popular"},
        {"name": "Premium", "price": "2,999", "period": "one-time", "blurb": "A standout site with the works for businesses going all-in.",
         "features": ["Unlimited pages & custom sections", "Fully bespoke design system", "Booking / e-commerce ready", "Advanced SEO & analytics", "Copywriting assistance", "3 months priority support"], "featured": False, "cta": "Go premium"}
    ],
    "carePlan": {"name": "Care Plan", "price": "49", "period": "/month", "blurb": "Hosting help, security, edits & monthly updates so you never worry about your site.", "enabled": True},
    "portfolio": [
        {"title": "Summit Grill & Tap", "category": "Restaurant", "style": "Bold & Appetizing",
         "description": "A warm, photo-forward site with an immersive menu and reservation flow — built to make people hungry.", "image": "", "tags": ["Restaurant", "Menu", "Bookings"], "accent": "#E8593B"},
        {"title": "Whitaker Law Group", "category": "Professional Services", "style": "Minimal & Trustworthy",
         "description": "Clean, calm, and authoritative. Quiet typography and lots of whitespace that signals credibility.", "image": "", "tags": ["Legal", "Corporate", "Minimal"], "accent": "#2F4858"},
        {"title": "Pulse Fitness Studio", "category": "Health & Fitness", "style": "Vibrant & Energetic",
         "description": "High-energy gradients, motion, and a class schedule that practically makes you want to work out.", "image": "", "tags": ["Fitness", "Booking", "Bold"], "accent": "#7C3AED"}
    ],
    "testimonials": [
        {"name": "Sarah M.", "role": "Owner, Local Bakery", "quote": "Ben took our embarrassing old site and turned it into something we're genuinely proud of. Calls went up within weeks."},
        {"name": "Dave R.", "role": "Contractor", "quote": "Fast, professional, and he actually picked up the phone. Best money I've spent on the business this year."},
        {"name": "Priya K.", "role": "Salon Manager", "quote": "Our new site looks like it belongs to a company ten times our size. Booking online has been a game changer."}
    ],
    "process": [
        {"step": "01", "title": "Discovery", "desc": "We talk about your business, your customers, and what success looks like."},
        {"step": "02", "title": "Design", "desc": "I craft a custom design tailored to your brand — you review and shape it."},
        {"step": "03", "title": "Build", "desc": "I hand-code the site, fast and clean, and you watch it come together."},
        {"step": "04", "title": "Launch", "desc": "We go live, connect everything, and I make sure you know how to use it."}
    ],
    "faq": [
        {"q": "How long does a website take?", "a": "Most projects launch in 1–3 weeks depending on size and how quickly we get your content and feedback."},
        {"q": "Do I own my website?", "a": "100%. You own the site, the domain, and all the content. No lock-in."},
        {"q": "Can you fix or redesign my current website?", "a": "Absolutely — redesigns and rescues are a big part of what I do. I can rebuild on a fresh, modern foundation."},
        {"q": "What do you need from me to start?", "a": "Just a conversation. A free quote call helps me understand your goals; from there I handle the heavy lifting."},
        {"q": "Do you offer ongoing support?", "a": "Yes — the optional Care Plan covers edits, hosting help, and updates so your site stays current."}
    ],
    "careers": [
        {"title": "Freelance Web Designer", "type": "Contract / Remote", "location": "Remote",
         "description": "Love crafting beautiful interfaces? I occasionally partner with designers on larger builds. Send a portfolio."}
    ],
    "privacy": "",  # generated default below if empty
    "social": {"facebook": "", "instagram": "", "linkedin": ""}
}

DEFAULT_PRIVACY = """## Privacy Policy

_Last updated: this policy applies to www.apexweb.ca and all services provided by Apex Web Development ("we", "us", "Ben Stephan")._

### 1. Who we are
Apex Web Development is a custom web design and development business operated by Ben, based in Calgary, Alberta, Canada. You can reach us any time at the phone number or email listed on this website.

### 2. What information we collect
- **Information you give us.** When you use our contact form, request a quote, or message us through live chat, we collect the name, email, phone number, and any details you choose to provide.
- **Automatic information.** Like most websites, our server may record basic technical data such as your browser type and the pages you visit, to keep the site secure and working well.

### 3. How we use your information
We use your information only to:
- Respond to your inquiry, quote request, or chat message;
- Provide the services you ask for;
- Improve our website and services.

We do **not** sell, rent, or trade your personal information to anyone.

### 4. Live chat
When you use the live chat on this site, your messages are stored so we can read and reply to them. Please don't share sensitive information (passwords, payment card numbers, etc.) through chat.

### 5. Cookies
This site uses minimal local storage to remember your chat session so we can continue the conversation. We do not use advertising or third-party tracking cookies.

### 6. How we protect your data
Your information is stored securely and access is limited to the business owner. We retain inquiry and chat records only as long as needed to serve you and for reasonable business records.

### 7. Your rights
You may ask us to access, correct, or delete the personal information we hold about you at any time by contacting us. We'll respond promptly.

### 8. Third-party links
Our site may link to other websites. We are not responsible for the privacy practices of those sites.

### 9. Changes to this policy
We may update this policy from time to time. The latest version will always be posted on this page.

### 10. Contact us
Questions about your privacy or this policy? Contact Ben at Apex Web Development using the phone number or email shown on this website.
"""

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
class CurWrap:
    """Cursor wrapper: makes execute() chainable and translates ? -> %s for Postgres."""
    def __init__(self, cur): self._c = cur
    def execute(self, sql, params=()):
        if USE_PG:
            sql = sql.replace("?", "%s")
        self._c.execute(sql, params)
        return self
    def fetchone(self): return self._c.fetchone()
    def fetchall(self): return self._c.fetchall()
    def __getattr__(self, n): return getattr(self._c, n)

class ConnWrap:
    def __init__(self, conn): self._conn = conn
    def cursor(self):
        if USE_PG:
            return CurWrap(self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor))
        return CurWrap(self._conn.cursor())
    def commit(self): self._conn.commit()
    def close(self): self._conn.close()
    def __getattr__(self, n): return getattr(self._conn, n)

def db():
    if USE_PG:
        return ConnWrap(psycopg2.connect(os.environ["DATABASE_URL"]))
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return ConnWrap(conn)

def init_db():
    conn = db()
    c = conn.cursor()
    pk = "SERIAL PRIMARY KEY" if USE_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"
    blob = "BYTEA" if USE_PG else "BLOB"
    c.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, created INTEGER)")
    c.execute("""CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY, name TEXT, email TEXT, created INTEGER, last_activity INTEGER)""")
    c.execute(f"""CREATE TABLE IF NOT EXISTS messages (
        id {pk}, conv_id TEXT, sender TEXT,
        body TEXT, ts INTEGER, read_by_admin INTEGER DEFAULT 0)""")
    c.execute(f"""CREATE TABLE IF NOT EXISTS leads (
        id {pk}, name TEXT, email TEXT, phone TEXT,
        message TEXT, ts INTEGER, handled INTEGER DEFAULT 0)""")
    c.execute(f"""CREATE TABLE IF NOT EXISTS uploads (
        name TEXT PRIMARY KEY, mime TEXT, data {blob}, ts INTEGER)""")
    conn.commit()

    # Seed content
    if not get_setting(c, "content"):
        content = dict(DEFAULT_CONTENT)
        content["privacy"] = DEFAULT_PRIVACY
        set_setting(c, "content", json.dumps(content))
    # Seed admin password (default: changeme123 — CHANGE IT in admin settings)
    if not get_setting(c, "admin_pw"):
        set_setting(c, "admin_pw", hash_pw("changeme123"))
    conn.commit()
    conn.close()

def get_setting(c, key):
    row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None

def set_setting(c, key, value):
    c.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=?", (key, value, value))

def hash_pw(pw, salt=None):
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 120000).hex()
    return f"{salt}${h}"

def verify_pw(pw, stored):
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(hash_pw(pw, salt), stored)

# ---------------------------------------------------------------------------
# Schema-based input validation  (OWASP: Input Validation / Mass Assignment)
# ---------------------------------------------------------------------------
# Every public write endpoint runs its JSON body through validate() with an
# explicit schema. This enforces: allow-listed fields only (unexpected fields
# are rejected — blocks mass-assignment), correct types, and length/range
# limits. Strings are trimmed; nothing is trusted by default.
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def validate(body, schema):
    """Validate & sanitize `body` against `schema`. Returns (clean_dict, error_or_None).

    schema field rules: {"type": str|int|float|bool|dict, "required": bool,
      "min": n, "max": n, "format": "email", "choices": [...], "default": v}
    For str, min/max are length limits; for numbers, value limits.
    Unknown top-level fields are rejected (mass-assignment guard).
    """
    if not isinstance(body, dict):
        return None, "Invalid request body."
    unexpected = [k for k in body.keys() if k not in schema]
    if unexpected:
        return None, "Unexpected field(s): " + ", ".join(sorted(unexpected)[:5])
    clean = {}
    for field, rule in schema.items():
        val = body.get(field)
        missing = field not in body or val is None or (isinstance(val, str) and val.strip() == "")
        if missing:
            if rule.get("required"):
                return None, "Missing required field: " + field
            clean[field] = rule.get("default")
            continue
        t = rule.get("type", str)
        if t is str:
            if not isinstance(val, str):
                return None, field + " must be text."
            val = val.strip()
            if len(val) > rule.get("max", 10000):
                return None, field + " is too long (max " + str(rule.get("max", 10000)) + ")."
            if len(val) < rule.get("min", 0):
                return None, field + " is too short."
            if rule.get("format") == "email" and not EMAIL_RE.match(val):
                return None, "Please enter a valid email address."
            if "choices" in rule and val not in rule["choices"]:
                return None, "Invalid value for " + field + "."
        elif t in (int, float):
            if isinstance(val, bool):
                return None, field + " must be a number."
            try:
                val = float(val) if t is float else int(val)
            except (TypeError, ValueError):
                return None, field + " must be a number."
            if "min" in rule and val < rule["min"]:
                return None, field + " is too small."
            if "max" in rule and val > rule["max"]:
                return None, field + " is too large."
        elif t is bool:
            if not isinstance(val, bool):
                return None, field + " must be true or false."
        elif t is dict:
            if not isinstance(val, dict):
                return None, field + " must be an object."
            if len(json.dumps(val)) > rule.get("max", 2_000_000):
                return None, field + " is too large."
        clean[field] = val
    return clean, None

# Per-endpoint input schemas (allow-listed fields, types, length/range limits).
S_CHAT_START = {"name": {"type": str, "max": 80}, "email": {"type": str, "max": 120}}
S_CHAT_SEND  = {"conv_id": {"type": str, "required": True, "max": 64},
                "body": {"type": str, "required": True, "min": 1, "max": 2000},
                "name": {"type": str, "max": 80}, "email": {"type": str, "max": 120}}
S_CONTACT    = {"name": {"type": str, "required": True, "min": 1, "max": 120},
                "email": {"type": str, "max": 160, "format": "email"},
                "phone": {"type": str, "max": 60}, "message": {"type": str, "max": 3000}}
S_PAY        = {"amount": {"type": float, "required": True, "min": 1, "max": 50000},
                "description": {"type": str, "max": 200}}
S_LOGIN      = {"password": {"type": str, "required": True, "max": 200}}
S_CONTENT    = {"content": {"type": dict, "required": True, "max": 1_500_000}}
S_UPLOAD     = {"data": {"type": str, "required": True, "max": 16_000_000}}
S_REPLY      = {"conv_id": {"type": str, "required": True, "max": 64},
                "body": {"type": str, "required": True, "min": 1, "max": 2000}}
S_LEAD       = {"id": {"type": int, "required": True, "min": 1}, "handled": {"type": bool, "default": True}}
S_PW         = {"current": {"type": str, "required": True, "max": 200},
                "new": {"type": str, "required": True, "min": 8, "max": 200}}
S_NONE       = {}   # endpoints that take no body — still reject unexpected fields

# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = "ApexWeb/1.0"

    # -- helpers --------------------------------------------------------------
    def _send(self, code, body=b"", ctype="application/json", extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        # Content-Security-Policy (OWASP: mitigates XSS + clickjacking). 'unsafe-inline'
        # is required because the site uses inline styles/handlers; external script
        # injection, framing, and untrusted origins are still blocked.
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; "
                         "script-src 'self' 'unsafe-inline'; "
                         "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                         "font-src 'self' https://fonts.gstatic.com; "
                         "img-src 'self' data:; "
                         "connect-src 'self'; "
                         "form-action 'self'; base-uri 'self'; frame-ancestors 'none'")
        self.send_header("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, obj, code=200, extra=None):
        # API responses may contain private data (leads, chats) — never cache them.
        headers = {"Cache-Control": "no-store"}
        if extra:
            headers.update(extra)
        self._send(code, json.dumps(obj), "application/json", headers)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _cookies(self):
        out = {}
        for part in (self.headers.get("Cookie") or "").split(";"):
            if "=" in part:
                k, v = part.strip().split("=", 1)
                out[k] = v
        return out

    def _is_admin(self):
        token = self._cookies().get("apex_session")
        if not token:
            return False
        conn = db(); c = conn.cursor()
        try:
            row = c.execute("SELECT created FROM sessions WHERE token=?", (token,)).fetchone()
            if not row:
                return False
            if time.time() - (row["created"] or 0) > SESSION_TTL:   # expire stale/stolen tokens
                c.execute("DELETE FROM sessions WHERE token=?", (token,))
                conn.commit()
                return False
            return True
        finally:
            conn.close()

    def _client_ip(self):
        # Behind Render's proxy the trustworthy client IP is the RIGHTMOST
        # X-Forwarded-For entry — the one the proxy itself appended. Any value a
        # client tries to spoof ends up on the left, so taking the last entry
        # stops attackers from rotating a fake IP to bypass the per-IP limits.
        xff = self.headers.get("X-Forwarded-For", "")
        if xff:
            return xff.split(",")[-1].strip()
        return self.client_address[0] if self.client_address else "?"

    def _rl(self, bucket, limit, window):
        return rate_ok(self._client_ip() + ":" + bucket, limit, window)

    def _too_many(self):
        return self._json({"error": "Too many requests. Please wait a few minutes and try again."}, 429)

    def log_message(self, *a):  # quieter logs
        pass

    # -- routing --------------------------------------------------------------
    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        if path.startswith("/api/"):
            return self.api_get(path, parse_qs(u.query))
        if path.startswith("/uploads/"):
            return self.serve_upload(path)
        if path == "/admin" or path == "/admin/":
            return self.serve_file("admin.html")
        if path == "/privacy" or path == "/privacy/":
            return self.serve_file("privacy.html")
        if path == "/pay" or path == "/pay/":
            return self.serve_file("pay.html")
        if path == "/pay/success" or path == "/pay/success/":
            return self.serve_file("pay-success.html")
        if path == "/" or path == "":
            return self.serve_file("index.html")
        return self.serve_file(path.lstrip("/"))

    def _base_url(self):
        if os.environ.get("BASE_URL"):
            return os.environ["BASE_URL"].rstrip("/")
        proto = self.headers.get("X-Forwarded-Proto", "http")
        host = self.headers.get("X-Forwarded-Host") or self.headers.get("Host", "localhost:%d" % PORT)
        return f"{proto}://{host}"

    def do_HEAD(self):
        self.do_GET()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > MAX_BODY:
            self.close_connection = True
            return self._json({"error": "Request too large."}, 413)
        u = urlparse(self.path)
        if u.path.startswith("/api/"):
            return self.api_post(u.path)
        self._json({"error": "not found"}, 404)

    # -- static ---------------------------------------------------------------
    def serve_file(self, relpath):
        relpath = relpath.split("?")[0]
        full = os.path.normpath(os.path.join(PUBLIC, relpath))
        if not full.startswith(PUBLIC) or not os.path.isfile(full):
            return self._send(404, "404 — Not found", "text/plain")
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        with open(full, "rb") as f:
            data = f.read()
        cache = "no-cache" if full.endswith((".html",)) else "public, max-age=3600"
        self._send(200, data, ctype, {"Cache-Control": cache})

    def serve_upload(self, path):
        name = os.path.basename(path)
        conn = db(); c = conn.cursor()
        try:
            row = c.execute("SELECT mime,data FROM uploads WHERE name=?", (name,)).fetchone()
        finally:
            conn.close()
        if not row:
            return self._send(404, "404", "text/plain")
        ctype = row["mime"] or "application/octet-stream"
        self._send(200, bytes(row["data"]), ctype, {"Cache-Control": "public, max-age=86400"})

    # -- API GET --------------------------------------------------------------
    def api_get(self, path, q):
        # Baseline per-IP rate limit for ALL read endpoints (graceful 429).
        # Generous: the chat widget and admin inbox poll a few times per minute.
        if not self._rl("api_get", 240, 60):
            return self._too_many()
        conn = db(); c = conn.cursor()
        try:
            if path == "/api/content":
                content = json.loads(get_setting(c, "content"))
                return self._json(content)

            if path == "/api/pay/config":
                return self._json({"enabled": bool(STRIPE_SECRET_KEY), "currency": STRIPE_CURRENCY.upper()})

            if path == "/api/chat/messages":
                conv_id = (q.get("conv_id") or [""])[0][:64]
                try:
                    after = max(0, int((q.get("after") or ["0"])[0]))
                except (TypeError, ValueError):
                    after = 0
                if not conv_id:
                    return self._json({"messages": []})
                rows = c.execute(
                    "SELECT id,sender,body,ts FROM messages WHERE conv_id=? AND id>? ORDER BY id",
                    (conv_id, after)).fetchall()
                return self._json({"messages": [dict(r) for r in rows]})

            # ----- admin only -----
            if path.startswith("/api/admin/"):
                if not self._is_admin():
                    return self._json({"error": "unauthorized"}, 401)
                # User-based (per-session) rate limit, on top of the per-IP one.
                if not rate_ok("adminu:" + self._cookies().get("apex_session", ""), 300, 60):
                    return self._too_many()

                if path == "/api/admin/me":
                    return self._json({"ok": True})

                if path == "/api/admin/conversations":
                    rows = c.execute("""
                        SELECT cv.id, cv.name, cv.email, cv.last_activity,
                          (SELECT COUNT(*) FROM messages m WHERE m.conv_id=cv.id AND m.sender='visitor' AND m.read_by_admin=0) AS unread,
                          (SELECT body FROM messages m WHERE m.conv_id=cv.id ORDER BY m.id DESC LIMIT 1) AS last_msg
                        FROM conversations cv ORDER BY cv.last_activity DESC""").fetchall()
                    return self._json({"conversations": [dict(r) for r in rows]})

                if path == "/api/admin/conversation":
                    conv_id = (q.get("conv_id") or [""])[0][:64]
                    c.execute("UPDATE messages SET read_by_admin=1 WHERE conv_id=? AND sender='visitor'", (conv_id,))
                    conn.commit()
                    rows = c.execute("SELECT id,sender,body,ts FROM messages WHERE conv_id=? ORDER BY id", (conv_id,)).fetchall()
                    info = c.execute("SELECT name,email FROM conversations WHERE id=?", (conv_id,)).fetchone()
                    return self._json({"messages": [dict(r) for r in rows], "info": dict(info) if info else {}})

                if path == "/api/admin/unread_count":
                    n = c.execute("SELECT COUNT(*) AS n FROM messages WHERE sender='visitor' AND read_by_admin=0").fetchone()["n"]
                    leads = c.execute("SELECT COUNT(*) AS n FROM leads WHERE handled=0").fetchone()["n"]
                    return self._json({"unread": n, "leads": leads})

                if path == "/api/admin/leads":
                    rows = c.execute("SELECT * FROM leads ORDER BY id DESC").fetchall()
                    return self._json({"leads": [dict(r) for r in rows]})

            return self._json({"error": "not found"}, 404)
        finally:
            conn.close()

    # -- API POST -------------------------------------------------------------
    def api_post(self, path):
        body = self._read_json()
        # Baseline per-IP rate limit for ALL write endpoints (graceful 429).
        if not self._rl("api_post", 60, 60):
            return self._too_many()
        conn = db(); c = conn.cursor()
        try:
            # ---- public ----
            if path == "/api/chat/start":
                if not self._rl("chatstart", 15, 300):
                    return self._too_many()
                data, err = validate(body, S_CHAT_START)
                if err:
                    return self._json({"error": err}, 400)
                conv_id = secrets.token_hex(12)
                now = int(time.time())
                c.execute("INSERT INTO conversations(id,name,email,created,last_activity) VALUES(?,?,?,?,?)",
                          (conv_id, data.get("name") or "Visitor", data.get("email") or "", now, now))
                conn.commit()
                return self._json({"conv_id": conv_id})

            if path == "/api/chat/send":
                if not self._rl("chatsend", 40, 300):
                    return self._too_many()
                data, err = validate(body, S_CHAT_SEND)
                if err:
                    return self._json({"error": err}, 400)
                conv_id, text = data["conv_id"], data["body"]
                # User-based limit: cap messages per conversation even across IPs.
                if not rate_ok("conv:" + conv_id, 30, 300):
                    return self._too_many()
                row = c.execute("SELECT id FROM conversations WHERE id=?", (conv_id,)).fetchone()
                if not row:
                    return self._json({"error": "no conversation"}, 404)
                now = int(time.time())
                c.execute("INSERT INTO messages(conv_id,sender,body,ts) VALUES(?,?,?,?)", (conv_id, "visitor", text, now))
                c.execute("UPDATE conversations SET last_activity=? WHERE id=?", (now, conv_id))
                if data.get("name"):
                    c.execute("UPDATE conversations SET name=? WHERE id=?", (data["name"], conv_id))
                if data.get("email"):
                    c.execute("UPDATE conversations SET email=? WHERE id=?", (data["email"], conv_id))
                conn.commit()
                return self._json({"ok": True})

            if path == "/api/contact":
                if not self._rl("contact", 6, 600):
                    return self._too_many()
                data, err = validate(body, S_CONTACT)
                if err:
                    return self._json({"error": err}, 400)
                if not (data.get("email") or data.get("phone")):
                    return self._json({"error": "Please add an email or phone so we can reach you."}, 400)
                c.execute("INSERT INTO leads(name,email,phone,message,ts) VALUES(?,?,?,?,?)",
                          (data["name"], data.get("email") or "", data.get("phone") or "", data.get("message") or "", int(time.time())))
                conn.commit()
                return self._json({"ok": True})

            if path == "/api/pay/create-checkout":
                if not self._rl("pay", 15, 600):
                    return self._too_many()
                if not STRIPE_SECRET_KEY:
                    return self._json({"error": "Online payments aren't set up yet. Please contact us."}, 400)
                data, err = validate(body, S_PAY)
                if err:
                    return self._json({"error": err}, 400)
                cents = int(round(data["amount"] * 100))
                if cents < 100 or cents > 5000000:   # defense-in-depth (schema already bounds it)
                    return self._json({"error": "Please enter an amount between $1 and $50,000."}, 400)
                desc = data.get("description") or "Apex Web Development — project payment"
                base = self._base_url()
                sess = stripe_post("checkout/sessions", {
                    "mode": "payment",
                    "line_items[0][price_data][currency]": STRIPE_CURRENCY,
                    "line_items[0][price_data][product_data][name]": desc,
                    "line_items[0][price_data][unit_amount]": str(cents),
                    "line_items[0][quantity]": "1",
                    "billing_address_collection": "auto",
                    "success_url": base + "/pay/success?session_id={CHECKOUT_SESSION_ID}",
                    "cancel_url": base + "/pay",
                })
                if sess.get("url"):
                    return self._json({"url": sess["url"]})
                print("[stripe] checkout error:", (sess.get("error") or {}).get("message"))
                return self._json({"error": "We couldn't start checkout right now. Please try again, or contact us to pay another way."}, 400)

            if path == "/api/pay/subscribe":
                if not self._rl("pay", 15, 600):
                    return self._too_many()
                if not STRIPE_SECRET_KEY:
                    return self._json({"error": "Online payments aren't set up yet. Please contact us."}, 400)
                _, err = validate(body, S_NONE)   # takes no input; reject any injected fields
                if err:
                    return self._json({"error": err}, 400)
                care = (json.loads(get_setting(c, "content")).get("carePlan") or {})
                if care.get("enabled") is False:
                    return self._json({"error": "The Care Plan isn't available right now."}, 400)
                try:
                    cents = int(round(float(str(care.get("price", "")).replace(",", "")) * 100))
                except (TypeError, ValueError):
                    cents = 0
                if cents < 100:
                    return self._json({"error": "The Care Plan price isn't set up yet."}, 400)
                base = self._base_url()
                sess = stripe_post("checkout/sessions", {
                    "mode": "subscription",
                    "line_items[0][price_data][currency]": STRIPE_CURRENCY,
                    "line_items[0][price_data][product_data][name]": "Apex " + (care.get("name") or "Care Plan") + " (monthly)",
                    "line_items[0][price_data][unit_amount]": str(cents),
                    "line_items[0][price_data][recurring][interval]": "month",
                    "line_items[0][quantity]": "1",
                    "success_url": base + "/pay/success?session_id={CHECKOUT_SESSION_ID}&type=sub",
                    "cancel_url": base + "/pay",
                })
                if sess.get("url"):
                    return self._json({"url": sess["url"]})
                print("[stripe] subscription error:", (sess.get("error") or {}).get("message"))
                return self._json({"error": "We couldn't start the subscription right now. Please try again, or contact us."}, 400)

            if path == "/api/admin/login":
                if not self._rl("login", 8, 300):
                    return self._too_many()
                data, err = validate(body, S_LOGIN)
                if err:
                    return self._json({"error": err}, 400)
                stored = get_setting(c, "admin_pw")
                if verify_pw(data["password"], stored):
                    token = secrets.token_hex(24)
                    c.execute("INSERT INTO sessions(token,created) VALUES(?,?)", (token, int(time.time())))
                    conn.commit()
                    secure = "; Secure" if self.headers.get("X-Forwarded-Proto", "").lower() == "https" else ""
                    return self._json({"ok": True}, extra={
                        "Set-Cookie": f"apex_session={token}; HttpOnly; Path=/; SameSite=Lax; Max-Age=2592000{secure}"})
                time.sleep(0.5)
                return self._json({"error": "Incorrect password"}, 401)

            # ---- admin only ----
            if path.startswith("/api/admin/"):
                if not self._is_admin():
                    return self._json({"error": "unauthorized"}, 401)
                # User-based (per-session) rate limit, on top of the per-IP one.
                if not rate_ok("adminu:" + self._cookies().get("apex_session", ""), 240, 60):
                    return self._too_many()

                if path == "/api/admin/logout":
                    token = self._cookies().get("apex_session")
                    c.execute("DELETE FROM sessions WHERE token=?", (token,))
                    conn.commit()
                    return self._json({"ok": True}, extra={"Set-Cookie": "apex_session=; Path=/; Max-Age=0"})

                if path == "/api/admin/content":
                    # Full content replacement (admin-trusted; still type + size checked).
                    data, err = validate(body, S_CONTENT)
                    if err:
                        return self._json({"error": err}, 400)
                    set_setting(c, "content", json.dumps(data["content"]))
                    conn.commit()
                    return self._json({"ok": True})

                if path == "/api/admin/upload":
                    data, err = validate(body, S_UPLOAD)
                    if err:
                        return self._json({"error": err}, 400)
                    m = re.match(r"data:(image/[\w.+-]+);base64,(.*)$", data["data"], re.S)
                    if not m:
                        return self._json({"error": "Invalid image data."}, 400)
                    # Strict MIME allow-list — raster only. SVG is rejected (can carry
                    # scripts → stored-XSS risk when served inline).
                    ALLOWED = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}
                    mime = m.group(1)
                    if mime not in ALLOWED:
                        return self._json({"error": "Only PNG, JPG, WEBP or GIF images are allowed."}, 400)
                    try:
                        raw = base64.b64decode(m.group(2), validate=True)
                    except (base64.binascii.Error, ValueError):
                        return self._json({"error": "Invalid image data."}, 400)
                    if len(raw) > 8 * 1024 * 1024:
                        return self._json({"error": "Image too large (max 8MB)."}, 400)
                    fname = secrets.token_hex(10) + ALLOWED[mime]
                    blob = psycopg2.Binary(raw) if USE_PG else sqlite3.Binary(raw)
                    c.execute("INSERT INTO uploads(name,mime,data,ts) VALUES(?,?,?,?)",
                              (fname, mime, blob, int(time.time())))
                    conn.commit()
                    return self._json({"url": f"/uploads/{fname}"})

                if path == "/api/admin/reply":
                    data, err = validate(body, S_REPLY)
                    if err:
                        return self._json({"error": err}, 400)
                    conv_id, text = data["conv_id"], data["body"]
                    now = int(time.time())
                    c.execute("INSERT INTO messages(conv_id,sender,body,ts) VALUES(?,?,?,?)", (conv_id, "admin", text, now))
                    c.execute("UPDATE conversations SET last_activity=? WHERE id=?", (now, conv_id))
                    conn.commit()
                    return self._json({"ok": True})

                if path == "/api/admin/lead_handled":
                    data, err = validate(body, S_LEAD)
                    if err:
                        return self._json({"error": err}, 400)
                    c.execute("UPDATE leads SET handled=? WHERE id=?", (1 if data["handled"] else 0, data["id"]))
                    conn.commit()
                    return self._json({"ok": True})

                if path == "/api/admin/password":
                    data, err = validate(body, S_PW)
                    if err:
                        return self._json({"error": err}, 400)
                    if not verify_pw(data["current"], get_setting(c, "admin_pw")):
                        return self._json({"error": "Current password is incorrect"}, 401)
                    set_setting(c, "admin_pw", hash_pw(data["new"]))
                    cur_token = self._cookies().get("apex_session")
                    c.execute("DELETE FROM sessions WHERE token != ?", (cur_token,))  # log out any other/stolen sessions
                    conn.commit()
                    return self._json({"ok": True})

            return self._json({"error": "not found"}, 404)
        finally:
            conn.close()


def _startup_checks():
    """Warn about insecure defaults at boot (OWASP: secure defaults)."""
    conn = db(); c = conn.cursor()
    try:
        if verify_pw("changeme123", get_setting(c, "admin_pw") or ""):
            print("  ⚠  Admin password is still the default 'changeme123' — change it in Admin → Settings.")
    finally:
        conn.close()
    print("  ℹ  Payments:", "enabled" if STRIPE_SECRET_KEY else "disabled (set STRIPE_SECRET_KEY to enable)")
    print("  ✓  Secrets loaded from environment; none are exposed to the browser.")

def main():
    init_db()
    _startup_checks()
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("\n  ✦ Apex Web Development is running")
    print(f"    Site   →  http://localhost:{PORT}")
    print(f"    Admin  →  http://localhost:{PORT}/admin   (default password: changeme123)")
    print("    Press Ctrl+C to stop.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.\n")


if __name__ == "__main__":
    main()
