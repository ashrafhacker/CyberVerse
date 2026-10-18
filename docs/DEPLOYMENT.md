# CyberVerse — Deployment Runbook

Target architecture (per project brief):

| Layer      | Provider            | State                                                        |
| ---------- | ------------------- | ------------------------------------------------------------ |
| Frontend   | Vercel              | CLI auth OK, but account **suspended (billing)** — deploy blocked |
| Backend    | Render              | `render.yaml` blueprint ready — **blocked on Render account** |
| Database   | Neon (us-east-1)    | **Migrated & verified** — `cyberverse` DB, 75 tables, head=`0007_library_enum_names` |
| Cache/jobs | Render Redis (default) or Upstash | Config via `REDIS_URL`/`CELERY_*` — no Upstash creds present |
| Assets     | Cloudflare R2       | **Blocked** — no R2 credentials on this machine              |
| Auth       | First-party JWT     | Verified E2E locally (login, rotation, RBAC, admin paths)    |
| Email      | SendGrid (existing) | Key present in local `.env`; delivery **not verified**       |
| Monitoring | Sentry              | **Not configured** — DSN in `.env` is a placeholder          |

---

## 1. What is already provisioned (Verified)

### Neon PostgreSQL — `cyberverse` database
- Existing Neon project `ep-nameless-glade-...us-east-1.aws.neon.tech` reused; **no new project created**.
- The default `neondb` database contains an unrelated chat-app schema (89 users) — **left untouched**.
- A separate `cyberverse` database was created (additive, non-destructive) and migrated:
  - `alembic upgrade head` → `0007_library_enum_names`, **75 tables**.
  - `app/core/config.py` remaps libpq-only URL params (`sslmode` → asyncpg `ssl`, drops `channel_binding`) so the Neon console connection string works as-is with asyncpg.
- Connection: use the **DIRECT (unpooled)** `DATABASE_URL_UNPOOLED`-style URL with `/cyberverse` path. The pooled `-pooler` URL works for runtime traffic; migrations should use the direct URL.

### Git
- Local repo initialized; branch **`repair/full-stack-production`** (3 commits on top of `origin/main`):
  - `ce75de0` backend: security hardening, contact endpoint, regression tests
  - `f12ac97` frontend: Nexus admin UI, SEO suite, UX hardening, perf
  - `d9a01ec` repo: deployment groundwork, docs, git hygiene
  - plus the config fix + deployment manifests commit.
- **Push is blocked**: no GitHub credentials on this machine
  (`fatal: could not read Username for 'https://github.com'`).
  To publish: `gh auth login` or `git remote set-url origin https://<TOKEN>@github.com/ashrafhacker/CyberVerse.git`
  (repo needs a token with `contents:write`), then
  `git push -u origin repair/full-stack-production`.

---

## 2. Backend on Render

`render.yaml` (repo root) defines the web service:

- `rootDir: backend`, Python runtime, `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2`
- `healthCheckPath: /health` (liveness); `/health/detailed` = readiness with DB/Redis checks
- `preDeployCommand: alembic upgrade head` — controlled, idempotent migration stage before traffic switch

### Environment variables (set in Render dashboard or blueprint)
| Key | Value source |
| --- | --- |
| `ENVIRONMENT=production`, `DEBUG=false`, `LOG_LEVEL=INFO` | fixed |
| `SECRET_KEY`, `JWT_SECRET_KEY` | `generateValue: true` |
| `DATABASE_URL` | Neon direct URL, path `/cyberverse` (pooled `-pooler` URL is fine for runtime) |
| `REDIS_URL` | Render Redis add-on (`redis://...`) or Upstash (`rediss://...`) |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | same Redis, separate DB indexes (e.g. `/1`, `/2`) |
| `CORS_ORIGINS` | JSON array, e.g. `'["https://<project>.vercel.app"]'` (wildcards rejected by validation) |
| `BCRYPT_ROUNDS=12`, `DATABASE_POOL_SIZE=5` | production sizing |
| `SENDGRID_API_KEY`, `CONTACT_FORM_RECIPIENT`, `SENTRY_DSN` | optional; app degrades gracefully when unset |

Free-tier notes: Render free web services sleep after inactivity (~15 min) and
offer 512 MB RAM — hence 2 workers. Expect a cold start on first request.
Postgres/Redis on Render are separate paid/instance choices; Neon + Upstash
free tiers are the intended substitutes.

### Deploy (once the Render account exists)
1. Render → New → Blueprint → connect the GitHub repo (needs the push above).
2. Render reads `render.yaml`, creates `cyberverse-api`, applies env vars.
3. First deploy runs `alembic upgrade head` (no-op: Neon DB is already at head).
4. Verify: `curl https://cyberverse-api.onrender.com/health` → `{"status":"ok"}`,
   then `/health/detailed` for DB/Redis.
5. Update `CORS_ORIGINS` with the real Vercel domain and redeploy if it differs.

---

## 3. Frontend on Vercel

> **Status: BLOCKED on billing.** The authenticated Vercel account
> (`bosserror1931-3672`, team `bosserror1931-gmailcoms-projects`) is suspended:
> *"To reactivate your subscription, add a valid payment method."* Read-only CLI
> calls work; project creation, `env add`, and deploys are rejected until the
> subscription is reactivated in the Vercel dashboard → Billing.

- Next.js app root: `frontend/` (project setting `rootDirectory: frontend`).
- `/api/:path*` rewrites to `BACKEND_URL` (server-side env, default `http://127.0.0.1:8000`).
- No `NEXT_PUBLIC_*` required for core operation (same-origin `/api` via rewrite).
- `frontend/.env.example` documents `BACKEND_URL` and optional `NEXT_PUBLIC_GA_ID`
  (analytics is consent-gated and a silent no-op until set).

### Deploy
```bash
cd frontend
vercel link --yes --project cyberverse
vercel env add BACKEND_URL production     # https://cyberverse-api.onrender.com
vercel --prod                             # or: vercel deploy --prod
```
Then set the backend `CORS_ORIGINS` to the assigned `*.vercel.app` domain.

Security headers (CSP, nosniff, Referrer-Policy, Permissions-Policy) ship from
`next.config.mjs` at build time. **Framing is deliberately permissive**
(`frame-ancestors *`, no `X-Frame-Options`) so the app renders inside embedded
views; before a real public launch with sensitive user data, re-add
`X-Frame-Options: DENY` + `frame-ancestors 'none'` there and rebuild.

---

## 4. CI/CD (GitHub Actions)

`.github/workflows/ci.yml` already runs: backend lint+tests (with Postgres/Redis
services), frontend lint/typecheck/tests/**production build**, Trivy fs scan,
gitleaks secret scan, Docker image builds to GHCR, and staging/production deploy
jobs. Repository secrets required for the deploy jobs:

- `RENDER_API_KEY`, `RENDER_STAGING_BACKEND_ID` (+ production service ID per the workflow)
- `VERCEL_TOKEN`, `VERCEL_PROJECT_ID`, `VERCEL_ORG_ID`

These cannot be created from this machine (no GitHub write access — see §1).

---

## 5. Rollback

- **Backend**: Render dashboard → service → Deploys → previous deploy → *Rollback*.
  Migrations are additive; if a migration must be undone, use
  `alembic downgrade -1` locally against the target DB (never blindly), or restore
  a Neon branch/point-in-time snapshot (Neon → Branches → restore).
- **Frontend**: Vercel → project → Deployments → previous *Ready* deployment →
  *Promote to Production* (instant rollback, no rebuild).
- **Database**: Neon keeps point-in-time history on paid tiers; on the free tier,
  take a `pg_dump` of `cyberverse` before any future destructive change:
  `pg_dump "$DATABASE_URL" -Fc -f cyberverse-$(date +%F).dump`.

---

## 6. Known blockers / not applicable

| Item | Status | Exact step to unblock |
| ---- | ------ | --------------------- |
| GitHub push | Blocked | Provide a PAT/`gh auth login`; push `repair/full-stack-production` |
| Vercel deploy | Blocked (billing) | Reactivate the Vercel subscription (add valid payment method), then run the §3 commands |
| Render account | Blocked | Create account → connect repo (blueprint auto-applies `render.yaml`) |
| Upstash Redis | Not configured | Create free DB → put `rediss://...` into `REDIS_URL`/`CELERY_*` (Render Redis add-on is the simpler default) |
| Cloudflare R2 | Blocked | Needs `R2_ACCOUNT_ID`/keys; `backend/.env.r2.example` documents the shape. Existing `cyberverse-assets` bucket must be reconciled by checksum before any upload — no bulk upload performed |
| Sentry | Not configured | Replace placeholder DSN in backend env |
| SendGrid delivery | Configured, not verified | Send one test message to an authorized recipient after setting the key in Render |
| Clerk | Not applicable | First-party JWT auth is implemented and verified; no second identity system introduced |
| Resend | Not applicable | SendGrid is the configured provider |
