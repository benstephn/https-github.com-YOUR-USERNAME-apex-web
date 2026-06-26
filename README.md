# Apex Web Development — website + admin

A complete, self-contained marketing site for Apex Web Development (Ben), with a live
chat you can answer and a full `/admin` panel to edit everything. **No Node, no installs** —
it runs on the Python 3 that's already on your Mac.

## Run it

```bash
cd apex
python3 server.py
```

Then open:

- **Website** → http://localhost:8080
- **Admin**   → http://localhost:8080/admin

Use a different port: `PORT=3000 python3 server.py`

## First login

Default admin password: **`changeme123`**
Log in at `/admin`, then change it under **Settings → Change password** right away.

## What you can do

| Where | What |
|-------|------|
| **Chat Inbox** | Read & reply to visitors who chat from the site, in real time. |
| **Quote Requests** | Every contact-form submission lands here with name/email/phone. |
| **Business Info** | Name, phone, email, location, hours — updates the whole site. |
| **Hero, About, Services, Process** | Edit all the marketing copy. |
| **Pricing** | Add/remove packages, set prices, mark one "featured". |
| **Work / Portfolio** | Add projects, **upload photos** of completed work, set styles & tags. |
| **Testimonials, FAQ, Careers** | Add/remove entries freely. |
| **Privacy Policy** | Edit the full policy text (Markdown). |

Everything you save goes live instantly.

## How the chat works

1. A visitor clicks the chat bubble, enters their name/email, and messages you.
2. You see it under **Admin → Chat Inbox** (a red badge shows unread count).
3. You reply; the visitor sees it appear within a few seconds.

> The chat works as long as `server.py` is running. For it to work when you're not at
> your computer, the site needs to be hosted online (see below) and you check the inbox
> from your phone's browser at `yoursite.com/admin`.

## Files

```
server.py          The whole backend (Python stdlib only)
public/            The website (index, privacy, admin + css/js)
uploads/           Photos you upload from admin (created automatically)
apex.db            Your content, chats & leads (created on first run)
```

## Going live (later)

Any host that runs Python works (Render, Railway, Fly.io, a small VPS, PythonAnywhere).
Point it at `python3 server.py`, set the `PORT` it gives you, put it behind HTTPS, and
connect your domain. Back up `apex.db` and `uploads/` to keep your data.
