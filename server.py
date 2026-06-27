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

import os, json, sqlite3, hashlib, hmac, secrets, base64, mimetypes, time, re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(ROOT, "public")
UPLOADS = os.path.join(ROOT, "uploads")
DB_PATH = os.path.join(ROOT, "apex.db")
PORT = int(os.environ.get("PORT", "8080"))

os.makedirs(UPLOADS, exist_ok=True)

# ---------------------------------------------------------------------------
# Default editable content (seeded on first run; afterwards lives in the DB)
# ---------------------------------------------------------------------------
DEFAULT_CONTENT = {
    "business": {
        "name": "Apex Web Development",
        "owner": "Ben Stephan",
        "tagline": "Websites that make local businesses look like the industry leaders they are.",
        "phone": "403-402-5016",
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
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, created INTEGER)")
    c.execute("""CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY, name TEXT, email TEXT, created INTEGER, last_activity INTEGER)""")
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, conv_id TEXT, sender TEXT,
        body TEXT, ts INTEGER, read_by_admin INTEGER DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT, phone TEXT,
        message TEXT, ts INTEGER, handled INTEGER DEFAULT 0)""")
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
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, obj, code=200, extra=None):
        self._send(code, json.dumps(obj), "application/json", extra)

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
        row = c.execute("SELECT token FROM sessions WHERE token=?", (token,)).fetchone()
        conn.close()
        return bool(row)

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
        if path == "/" or path == "":
            return self.serve_file("index.html")
        return self.serve_file(path.lstrip("/"))

    def do_HEAD(self):
        self.do_GET()

    def do_POST(self):
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
        full = os.path.normpath(os.path.join(UPLOADS, name))
        if not full.startswith(UPLOADS) or not os.path.isfile(full):
            return self._send(404, "404", "text/plain")
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        with open(full, "rb") as f:
            data = f.read()
        self._send(200, data, ctype, {"Cache-Control": "public, max-age=86400"})

    # -- API GET --------------------------------------------------------------
    def api_get(self, path, q):
        conn = db(); c = conn.cursor()
        try:
            if path == "/api/content":
                content = json.loads(get_setting(c, "content"))
                return self._json(content)

            if path == "/api/chat/messages":
                conv_id = (q.get("conv_id") or [""])[0]
                after = int((q.get("after") or ["0"])[0])
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
                    conv_id = (q.get("conv_id") or [""])[0]
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
        conn = db(); c = conn.cursor()
        try:
            # ---- public ----
            if path == "/api/chat/start":
                conv_id = secrets.token_hex(12)
                now = int(time.time())
                c.execute("INSERT INTO conversations(id,name,email,created,last_activity) VALUES(?,?,?,?,?)",
                          (conv_id, (body.get("name") or "Visitor")[:80], (body.get("email") or "")[:120], now, now))
                conn.commit()
                return self._json({"conv_id": conv_id})

            if path == "/api/chat/send":
                conv_id = body.get("conv_id", "")
                text = (body.get("body") or "").strip()[:2000]
                if not conv_id or not text:
                    return self._json({"error": "missing"}, 400)
                row = c.execute("SELECT id FROM conversations WHERE id=?", (conv_id,)).fetchone()
                if not row:
                    return self._json({"error": "no conversation"}, 404)
                now = int(time.time())
                c.execute("INSERT INTO messages(conv_id,sender,body,ts) VALUES(?,?,?,?)", (conv_id, "visitor", text, now))
                c.execute("UPDATE conversations SET last_activity=? WHERE id=?", (now, conv_id))
                if body.get("name"):
                    c.execute("UPDATE conversations SET name=? WHERE id=?", (body["name"][:80], conv_id))
                if body.get("email"):
                    c.execute("UPDATE conversations SET email=? WHERE id=?", (body["email"][:120], conv_id))
                conn.commit()
                return self._json({"ok": True})

            if path == "/api/contact":
                name = (body.get("name") or "").strip()[:120]
                email = (body.get("email") or "").strip()[:160]
                phone = (body.get("phone") or "").strip()[:60]
                msg = (body.get("message") or "").strip()[:3000]
                if not name or not (email or phone):
                    return self._json({"error": "Please add your name and a way to reach you."}, 400)
                c.execute("INSERT INTO leads(name,email,phone,message,ts) VALUES(?,?,?,?,?)",
                          (name, email, phone, msg, int(time.time())))
                conn.commit()
                return self._json({"ok": True})

            if path == "/api/admin/login":
                stored = get_setting(c, "admin_pw")
                if verify_pw(body.get("password", ""), stored):
                    token = secrets.token_hex(24)
                    c.execute("INSERT INTO sessions(token,created) VALUES(?,?)", (token, int(time.time())))
                    conn.commit()
                    return self._json({"ok": True}, extra={
                        "Set-Cookie": f"apex_session={token}; HttpOnly; Path=/; SameSite=Lax; Max-Age=2592000"})
                time.sleep(0.5)
                return self._json({"error": "Incorrect password"}, 401)

            # ---- admin only ----
            if path.startswith("/api/admin/"):
                if not self._is_admin():
                    return self._json({"error": "unauthorized"}, 401)

                if path == "/api/admin/logout":
                    token = self._cookies().get("apex_session")
                    c.execute("DELETE FROM sessions WHERE token=?", (token,))
                    conn.commit()
                    return self._json({"ok": True}, extra={"Set-Cookie": "apex_session=; Path=/; Max-Age=0"})

                if path == "/api/admin/content":
                    # full content replacement
                    new = body.get("content")
                    if not isinstance(new, dict):
                        return self._json({"error": "bad content"}, 400)
                    set_setting(c, "content", json.dumps(new))
                    conn.commit()
                    return self._json({"ok": True})

                if path == "/api/admin/upload":
                    data_url = body.get("data", "")
                    m = re.match(r"data:(image/[\w.+-]+);base64,(.*)$", data_url, re.S)
                    if not m:
                        return self._json({"error": "invalid image"}, 400)
                    ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp",
                           "image/gif": ".gif", "image/svg+xml": ".svg"}.get(m.group(1), ".img")
                    raw = base64.b64decode(m.group(2))
                    if len(raw) > 8 * 1024 * 1024:
                        return self._json({"error": "Image too large (max 8MB)"}, 400)
                    fname = secrets.token_hex(10) + ext
                    with open(os.path.join(UPLOADS, fname), "wb") as f:
                        f.write(raw)
                    return self._json({"url": f"/uploads/{fname}"})

                if path == "/api/admin/reply":
                    conv_id = body.get("conv_id", "")
                    text = (body.get("body") or "").strip()[:2000]
                    if not conv_id or not text:
                        return self._json({"error": "missing"}, 400)
                    now = int(time.time())
                    c.execute("INSERT INTO messages(conv_id,sender,body,ts) VALUES(?,?,?,?)", (conv_id, "admin", text, now))
                    c.execute("UPDATE conversations SET last_activity=? WHERE id=?", (now, conv_id))
                    conn.commit()
                    return self._json({"ok": True})

                if path == "/api/admin/lead_handled":
                    c.execute("UPDATE leads SET handled=? WHERE id=?", (1 if body.get("handled", True) else 0, body.get("id")))
                    conn.commit()
                    return self._json({"ok": True})

                if path == "/api/admin/password":
                    cur = body.get("current", ""); new = body.get("new", "")
                    if not verify_pw(cur, get_setting(c, "admin_pw")):
                        return self._json({"error": "Current password is incorrect"}, 401)
                    if len(new) < 8:
                        return self._json({"error": "New password must be at least 8 characters"}, 400)
                    set_setting(c, "admin_pw", hash_pw(new))
                    conn.commit()
                    return self._json({"ok": True})

            return self._json({"error": "not found"}, 404)
        finally:
            conn.close()


def main():
    init_db()
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
