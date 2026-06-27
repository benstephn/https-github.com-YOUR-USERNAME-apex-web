# Launch checklist — apexweb.ca (Neon + GitHub + Render + GoDaddy)

Your data is now permanent (stored in a cloud Postgres database), so chat, leads,
admin edits and photos are never lost. Follow these four phases in order. Anywhere it
says "use the exact value it shows you," trust the dashboard over this doc.

⚠️ `apexweb.ca` already points somewhere. When you change DNS in Phase 4, the domain
will start showing THIS site instead. That's intended — just know the old page goes away.

---

## Phase 1 — Free database (Neon) · ~3 min
1. Go to **https://neon.tech** → sign up (free, you can use your GitHub login).
2. Create a project — name it `apex`, pick the region closest to Calgary (US West).
3. On the project dashboard, copy the **connection string** — it starts with
   `postgresql://...`. This is your `DATABASE_URL`. Keep it somewhere handy for Phase 3.

## Phase 2 — Code to GitHub · ~3 min
1. Go to **https://github.com/new** → create an **empty** repo named `apex-web`
   (Private is fine). Do **not** add a README/.gitignore. Click Create.
2. In Terminal, paste these (swap in your repo URL from the page):
   ```bash
   cd /Users/benstephan/Documents/cooper/apex
   git remote add origin https://github.com/YOURNAME/apex-web.git
   git branch -M main
   git push -u origin main
   ```
   If it asks for a password, that's a **Personal Access Token**, not your login:
   github.com → Settings → Developer settings → Personal access tokens →
   Tokens (classic) → Generate new → tick `repo` → use that as the password.

## Phase 3 — Deploy on Render · ~5 min
1. Go to **https://render.com** → sign up (use "Sign in with GitHub").
2. **New +** → **Blueprint** → pick your `apex-web` repo → Render reads `render.yaml`.
3. It will ask for **DATABASE_URL** — paste the Neon string from Phase 1.
4. Click **Apply / Create**. Wait ~2–3 min for the build.
5. You'll get a link like `https://apex-web-development.onrender.com`. Open it, then
   open `/admin` (password `changeme123`) — change the password under **Settings**.

## Phase 4 — Connect www.apexweb.ca (GoDaddy) · ~10 min + DNS wait
1. In Render → your service → **Settings → Custom Domains → Add Custom Domain**.
   Add **www.apexweb.ca** and **apexweb.ca**. Render shows the exact records to create.
2. In **GoDaddy** → My Products → your domain → **DNS / Manage DNS**:
   - **CNAME** — Name: `www` → Value: `apex-web-development.onrender.com`
     (use the exact `.onrender.com` host Render shows). Save.
   - **Root domain** (`apexweb.ca`): GoDaddy can't CNAME the root, so either
     **(a)** add an **A record** — Name: `@` → Value: the IP Render shows (e.g. `216.24.57.1`), or
     **(b)** use GoDaddy **Forwarding** to send `apexweb.ca` → `https://www.apexweb.ca`.
3. Back in Render, it verifies automatically and issues free HTTPS. DNS can take
   anywhere from a few minutes to an hour to go live.

---

## After launch
- **Remove the sleep:** Render's free plan sleeps after ~15 min idle (first visitor
  waits ~30–50s). For a business site, upgrade that service to **Starter ($7/mo)** to
  keep it always-on. Your data is safe either way (it lives in Neon, not on Render).
- Edit content anytime at `www.apexweb.ca/admin`.
- Future updates: edit files locally → `git push` → Render redeploys automatically.
