# Taking payments on apexweb.ca (Stripe)

Your site has a built-in payment page at **`www.apexweb.ca/pay`**. Clients pick a
package or type the amount you agreed on, then pay by **Apple Pay, Google Pay, Visa,
Mastercard, or Amex** — no account needed on their end. Money is deposited to your bank
by Stripe. You just send them the link.

It stays in "being set up" mode until you add your Stripe key (one-time, below).

## One-time setup (~10–15 min)

1. **Create a Stripe account** → https://stripe.com → Sign up.
2. **Activate payments**: in the Stripe Dashboard, complete "Activate account" — your
   business details and a bank account for payouts. (You can test before this is done;
   you need it finished to accept *real* money.)
3. **Get your Secret key**: Stripe Dashboard → **Developers → API keys** →
   **Secret key**. It starts with `sk_live_...` (real) or `sk_test_...` (testing).
   Click **Reveal** and copy it.
4. **Add it to your site**: Render → your `apex-web-development` service →
   **Environment** → **Add Environment Variable**:
   - Key: `STRIPE_SECRET_KEY`
   - Value: paste your `sk_live_...` key
   - **Save** (the site redeploys automatically).
5. That's it — `www.apexweb.ca/pay` is now live for real payments.

> Currency is already set to **CAD**. To change it, edit the `STRIPE_CURRENCY`
> variable in Render (e.g. `usd`).

## How you'll use it

- Agree on a price with a client.
- Send them **`https://www.apexweb.ca/pay`**.
- They tap your package or enter the amount, add an optional note, and pay.
- You get an email from Stripe, the money shows in your Stripe balance, and it pays out
  to your bank on Stripe's schedule (usually a couple of business days).

## Testing first (optional)

Use your `sk_test_...` key instead of the live one, then on `/pay` use Stripe's test
card `4242 4242 4242 4242`, any future expiry, any CVC. No real money moves. Swap in the
`sk_live_...` key when you're ready for real payments.

## Apple Pay

Apple Pay shows up automatically in the Stripe checkout on Apple devices — Stripe
registers your domain for you when using Checkout. Nothing extra to configure.

## Notes

- Your site never sees or stores card numbers — Stripe handles all of it (this keeps you
  secure and PCI-compliant by default).
- Refunds, receipts, and payout history all live in your Stripe Dashboard.
- Want recurring billing for the $49/mo Care Plan, or PayPal as a second option? Both can
  be added later.
