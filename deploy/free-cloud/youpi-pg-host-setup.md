# YouPI-PG Persistent Host Setup (CyberVerse Payments)

**Status:** gateway live on the primary workstation at `~/youpi-pg` (persistent disk, since 2026-11-11) behind a Cloudflare quick tunnel → Checkout Portal. Quick-tunnel hostnames rotate on every restart; the current URL is printed by the `cloudflared tunnel --url http://localhost:7000` process log. Staging checkout stays fail-closed until the user completes the Merchant Admin steps (receiving account, merchant API key, webhook URL/secret) and the three `YOUPI_*` vars are set on Render staging.
**Scope:** CyberVerse staging only (`cyberverse-staging.vercel.app`). Production stays off-limits.

## Current deployment (2026-11-11)

- Host: this machine (`~/youpi-pg`, moved off tmpfs after the 2026-11-11 user approval). SQLite ledger + `.secrets/` live under the clone — never copied off-machine without approval.
- Run mode: `YOUPI_MODE=localhost` + `YOUPI_ALLOW_LOCALHOST_MODE=true` + `NODE_ENV=production` (explicit opt-in; dev tooling routes stay blocked). `CHECKOUT_FRAME_ANCESTORS=https://cyberverse-staging.vercel.app`.
- Public exposure: Cloudflare quick tunnel (`cloudflared tunnel --url http://localhost:7000`), port 7000 only. `:5000/:6001/:6002/:6003/:6100/:8090` stay localhost-bound (Merchant Admin is machine-local; open it at `http://localhost:6001`).
- Node runs as 24.19.0 (engines asks for >= 24.22.1 — warning only; upgrade before any long-term hosting).
- Machine must stay powered on and the tunnel process alive; the tunnel URL changes on restart (update Render `YOUPI_API_DOMAIN` after any restart).
**Not RBI/NPCI certified.** ~20 tx/day suggested. One payee VPA at a time. Fulfillment is RECONCILED-only (bank statement), never on webhook alone.

## Hard requirements (any host)

- **Node.js >= 24.22.1** (gateway `engines`; local dev machine had 24.19.0 — OK only as warning, not for the host).
- **Persistent disk for SQLite** (`SQLITE_DB_PATH`, default `./data/youpi_pg.sqlite`). A free/ephemeral instance wipes the payment ledger on restart — customer pays, gateway forgets. **Do not deploy to any free tier without a mounted disk.**
- **Public HTTPS domain** (SSL terminated at reverse proxy / Cloudflare Tunnel), pointed at port **7000** (Checkout Portal). The portal proxies `/api/_` to the Payment API, so one public port is enough.
- **Always-on process** (systemd / Render paid instance). Observers (Gmail :6003 / SMS :6002) are long-lived and pair outbound-only.
- Node modules: `npm install --allow-git=all` after rewriting `git+ssh://git@github.com/` → `git+https://github.com/` in `package-lock.json`.

## Install (Linux host)

```bash
git clone https://github.com/ashrafhacker/youpi-pg.git && cd youpi-pg
sed -i 's|git+ssh://git@github.com/|git+https://github.com/|g' package-lock.json
npm install --allow-git=all
cp .env.example .env   # then edit
```

`.env` essentials (never commit; no UPI ID here):

```
NODE_ENV=production
CLOUDFLARE_DOMAIN=pay.<your-domain>        # production boot refuses without this
DEPLOYMENT_PREFIX=pay
BASE_CHECKOUT_URL=https://pay.<your-domain>
BASE_PAYMENT_API_URL=https://pay.<your-domain>
SQLITE_DB_PATH=/var/lib/youpi-pg/youpi_pg.sqlite   # on the persistent disk
ENCRYPTION_MASTER_KEY=...                  # 32+ byte random
JWT_SECRET=...                             # random
CHECKOUT_FRAME_ANCESTORS=https://cyberverse-staging.vercel.app
```

`CHECKOUT_FRAME_ANCESTORS` is required: the CyberVerse frontend embeds `/checkout/:id` as an iframe, and production fences the page to the portal's own origin otherwise.

Then `npm start` (production mode; requires the domain above), reverse-proxy 443 → `localhost:7000`, and `curl https://pay.<your-domain>/health` is not a route — use `http://localhost:7000/youpi.js` (expect JS) and the Payment API via the proxy path.

## Option A — Render paid instance (starter + disk)

- New Web Service from `ashrafhacker/youpi-pg` (branch: default), plan **starter** (~$7/mo; the repo's `render.yaml` is a **free demo** — do not use it for real payments).
- Runtime Node 24.22.1, build `npm install --allow-git=all` (with the lockfile rewrite done via a `build` prefix or a one-time fork commit), start `npm start`.
- Attach a **persistent disk** (e.g. 1 GB at `/var/lib/youpi-pg`), set `SQLITE_DB_PATH=/var/lib/youpi-pg/youpi_pg.sqlite`.
- Render gives you one public port → route it to 7000 (single service; no internal port exposure needed for CyberVerse).
- Set `CLOUDFLARE_DOMAIN` to the Render hostname (or a custom subdomain CNAME'd to it).
- **Needs explicit user approval (standing paid service + real payment traffic).**

## Option B — Small VPS (Oracle Always-Free ARM / Hetzner CX22 / DO droplet)

- Ubuntu: install Node 24.22.1 (nodesource), clone per above, systemd unit running `npm start` as a dedicated user, `SQLITE_DB_PATH=/var/lib/youpi-pg/youpi_pg.sqlite`.
- HTTPS: Caddy or nginx reverse proxy for `pay.<domain>` → `localhost:7000` (needs DNS control of the domain) **or** Cloudflare Tunnel (`cloudflared tunnel --url localhost:7000`) if you don't want inbound 80/443 — tunnel config needs your Cloudflare login (the current MCP token sees zero zones).
- No recurring infra cost beyond the VPS; Oracle free ARM is genuinely $0.

## Option C — Home/office machine that stays on

- Same install as B, plus Cloudflare Tunnel for HTTPS (required — home IPs are CGNAT/dynamic and must not be port-forwarded).
- Machine must stay powered; observers and SQLite live there.

## Receiving account (UPI)

After first boot, open Merchant Admin (`https://<host>/admin` or `http://localhost:6001`) → **Receiving Accounts** tab and enter the payee UPI ID + payee name. That is the only place the VPA belongs. Never in the CyberVerse repo, any `.env`, the database, Render/Vercel config, screenshots, or notes. The user enters this step personally.

## Observer pairing (manual)

- Android SIM observer (:6002): pair the phone via the QR flow in Merchant Admin.
- Gmail observer (:6003): OAuth client + refresh token per gateway docs.

## After the host is live — CyberVerse staging wiring (approval-gated)

1. Render staging (`cyberverse-staging-api`) env: `YOUPI_API_DOMAIN=https://pay.<domain>`, `YOUPI_MERCHANT_PUBLIC_KEY=<gateway merchant key>`, `YOUPI_WEBHOOK_SECRET=<gateway webhook secret>` (from Merchant Admin).
2. Redeploy staging; verify `/api/v1/premium/checkout` reports `youpi_enabled: true` for an **INR** plan (staging seeds may still be USD → `currency_mismatch` until plans are priced in INR).
3. Webhook sanity: `POST /api/v1/premium/webhook/youpi` with a bad signature → 401.
4. ₹1 live test: scan QR → pay → watch for RECONCILED → confirm Payment auto-completes + subscription activates → verify in `/admin/payments`.
5. Only after the above: consider any production change (separately approved, production remains off-limits by default).

## Never do

- Free tiers without a disk; multiple payee VPAs (only one can pay at a time); charging production without a bank-reconciled RECONCILED event; committing the VPA, keys, or `.env`; reusing r2.env-style long-lived secrets without approval.
