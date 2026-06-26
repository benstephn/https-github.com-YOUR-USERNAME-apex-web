# Deploying Apex to Render (free)

Netlify can't run the Python server (chat, `/admin`, uploads), so we use **Render**,
which can — and gives you a live link. There are two short steps: get the code on
GitHub, then point Render at it.

---

## Step 1 — Put the code on GitHub

1. Go to **https://github.com/new** and create a new **empty** repo
   (name it e.g. `apex-web`, leave "Add a README" **unchecked**). Click **Create repository**.
2. GitHub shows you a URL like `https://github.com/YOURNAME/apex-web.git`. Copy it.
3. In Terminal, run these (replace the URL with yours):

   ```bash
   cd /Users/benstephan/Documents/cooper/apex
   git remote add origin https://github.com/YOURNAME/apex-web.git
   git push -u origin main
   ```

   (If GitHub asks for a password, use a **Personal Access Token**, not your
   account password: github.com → Settings → Developer settings → Personal access
   tokens → Tokens (classic) → Generate, tick `repo`, paste it as the password.)

---

## Step 2 — Deploy on Render

**Easiest — one-click link.** Once your repo is on GitHub, open this in your browser
(swap in your repo URL):

```
https://render.com/deploy?repo=https://github.com/YOURNAME/apex-web
```

Render reads `render.yaml`, sets everything up, and after ~1–2 minutes gives you a
live link like `https://apex-web-development.onrender.com`.

**Or manually:** render.com → **New +** → **Web Service** → connect your GitHub repo
(or paste its URL under "Public Git Repository") → it auto-fills from `render.yaml` →
**Create Web Service**.

---

## After it's live

- Your site: `https://<your-app>.onrender.com`
- Admin:     `https://<your-app>.onrender.com/admin`  (default password `changeme123` —
  change it under **Settings** immediately).
- Add your own domain later in Render → **Settings → Custom Domains**.

### ⚠️ Important: data on the free plan
Render's **free** plan has a temporary filesystem — every time the app redeploys or
wakes from sleep, `apex.db` and uploaded photos **reset to defaults**. That's fine for
testing, but for a real business site you'll lose chat history, leads, edits, and photos.

To make it permanent (recommended once you're happy with it):
- Upgrade the service to **Starter ($7/mo)** and add a small **Persistent Disk**
  mounted at the project folder, **or**
- Ask me to switch storage to a free hosted Postgres database so data survives forever.

Free instances also **sleep after ~15 min** of no traffic and take ~30s to wake on the
first visit. The paid plan removes that too.
