# Security posture — Apex Web Development

How this site answers the "how can it be abused / exploited / fail?" questions.

## Authorization & Access Control — *can users reach data that isn't theirs?*
- Every `/api/admin/*` endpoint checks a server-side session before doing anything;
  unauthenticated requests get `401`.
- Visitor chats are gated by an unguessable 96-bit conversation id (`secrets.token_hex`).
  You can't read a conversation without holding its id.
- All public content (`/api/content`) is read-only; only authenticated admin writes.

## Rate Limiting — *can the APIs be spammed / brute-forced?*
- In-memory per-IP sliding-window limiter (`rate_ok`):
  - **Login:** 8 / 5 min  → blocks password brute-forcing (returns `429`).
  - **Contact form:** 6 / 10 min  → blocks lead spam.
  - **Chat:** start 15 / 5 min, send 40 / 5 min  → blocks flood/DB-stuffing.
  - **Payments:** 15 / 10 min  → blocks checkout-session abuse.
- Failed logins also sleep 0.5s (timing/throttle).

## Secrets Management — *are keys/credentials exposed?*
- `STRIPE_SECRET_KEY` and `DATABASE_URL` live only in Render env vars — never in code,
  never in git (`.gitignore` excludes the DB; repo is private).
- Card data never touches the server — Stripe Checkout handles it (PCI scope stays off us).
- Admin password stored as PBKDF2-HMAC-SHA256 (120k iterations) + per-record salt.
- Stripe error text is logged server-side but **not** returned to the browser (generic
  message only), so internal details don't leak.

## Token / Session Security — *what if a session token is stolen?*
- Session cookie is `HttpOnly` (JS can't read it), `SameSite=Lax`, and `Secure` in
  production (HTTPS only).
- Sessions are random 192-bit tokens stored server-side and **expire after 30 days**
  (checked on every request — stale/stolen tokens stop working).
- **Revocation:** logout deletes the token; changing your password **invalidates every
  other session** immediately. So if a token is ever stolen, change your password.

## Resilience — *can one request take the system down?*
- Request bodies over **12 MB are rejected** (`413`) before being read → no memory-DoS.
- Photo uploads capped at 8 MB and validated as images.
- Input is length-bounded and type-checked; payment amounts are clamped ($1–$50,000).
- All SQL is parameterized (no injection); user content is HTML-escaped on render (no XSS).
- Security headers on every response: `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`.

## Your part (operational)
- **Change the default admin password** (`changeme123`) at `/admin → Settings`.
- Keep your Stripe key only in Render; if it ever leaks, roll it in the Stripe dashboard.
- Stripe Dashboard is the source of truth for payments/refunds.

## Known trade-offs (acceptable at this scale, revisit if traffic grows)
- Rate limiting is per-process in memory — fine for a single Render instance; a multi-
  instance setup would want shared (Redis) limits.
- One DB connection per request — simple and safe; add pooling under heavy load.
