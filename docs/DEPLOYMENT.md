# CyberVerse — Deployment Runbook

> **Status as of 2026-10-30** — frontend live on Vercel; backend **migrating
> from blitz → Render free tier** (`render.yaml` blueprint; deployment
> verification pending — see §6/§7). All `blitz.cloud` URLs are retired.
> Target API domain: `https://api.cyberverse.qd.je` (DNS verification pending).

Target architecture:

| Layer      | Provider            | State                                                        |
| ---------- | ------------------- | ------------------------------------------------------------ |
| Frontend   | Vercel (team `neohacker-proejects`, project `cyberverse`) | **Live** — https://cyberverse-neohacker-proejects.vercel.app (also `cyberverse-beta.vercel.app`). The Vercel GitHub integration deploys every push to `main` (Production) and every branch push (Preview). |
| Backend    | Render free tier (blueprint `render.yaml`, service `cyberverse-api`) | **Migrating** — target URL `https://cyberverse-api.onrender.com` (custom domain `api.cyberverse.qd.je` pending DNS). Previous blitz backend retired 2026-10-30. See §6. |
| Database   | Neon (us-east-1)    | **Live & verified** — project `crimson-firefly-97189410`, branch `cyberverse-production`, DB `cyberverse`, 75 tables, head=`0007_library_enum_names`. The unrelated `neondb` DB is untouched. |
| Cache/jobs | Render Redis (default) or Upstash | Config via `REDIS_URL`/`CELERY_*` — created with the Render service; no Upstash creds present |
| Git       | GitHub `ashrafhacker/CyberVerse` (public) | **Live** — `main` tracks the latest CI-green commit, pushed over HTTPS with the `gh` keyring token (`gh auth setup-git`) |
| Assets     | Cloudflare R2       | **Blocked** — no R2 credentials on this machine              |
| Auth       | Clerk (RS256 session tokens) | **Live** — instance `suited-vervet-3663` (`pk_test_…`); switch to `pk_live_`/`sk_live_` before real launch |
| Email      | SendGrid (existing) | Key present in local `.env`; delivery **not verified**       |
| Monitoring | Sentry              | **Not configured** — DSN in `.env` is a placeholder          |

---

## 1. What is already provisioned (Verified)

### Neon PostgreSQL — `cyberverse` database
- Neon project `crimson-firefly-97189410` ("neohacker51"), branch
  `cyberverse-production`, endpoint `ep-silent-art-anexjm85.c-6.us-east-1.aws.neon.tech`.
  **No new project created.**
- The default `neondb` database contains an unrelated chat-app schema (89 users) — **left untouched**.
- A separate `cyberverse` database was created (additive, non-destructive) and migrated:
  - `alembic upgrade head` → `0007_library_enum_names`, **75 tables**.
  - `app/core/config.py` remaps libpq-only URL params (`sslmode` → asyncpg `ssl`, drops `channel_binding`) so the Neon console connection string works as-is with asyncpg.
- Connection: use the **DIRECT (unpooled)** `DATABASE_URL_UNPOOLED`-style URL with `/cyberverse` path. The pooled `-pooler` URL works for runtime traffic; migrations should use the direct URL.

### Git — GitHub `ashrafhacker/CyberVerse`
- Public repo on the personal account; `main` is the only deployed branch.
- Push over HTTPS: `gh auth setup-git` wires the `gh` CLI keyring token as the
  credential helper (token has `repo` scope; survives filesystem cleanups).
- CI (`ci.yml`) runs on every push to `main`: backend lint+tests, frontend
  lint+typecheck+tests, gitleaks+Trivy, Docker images to GHCR, then
  **Deploy to Production** (Render step only). Deploy steps are guarded by
  `if: env.<SECRET> != ''` so the pipeline stays green while credentials are
  missing. The frontend is deployed by Vercel's **GitHub integration**, not CI
  — the old CI `vercel --prod` step failed with "scope-not-accessible" (stale
  token) and duplicated the integration's build for the same commit, so it was
  removed 2026-10-27.
- Required GitHub Actions secrets (repo `ashrafhacker/CyberVerse`):
  | Secret | State |
  | --- | --- |
  | `VERCEL_TOKEN`, `VERCEL_PROJECT_ID`, `VERCEL_ORG_ID` | set but **unused** — the token no longer passes Vercel auth (`scope-not-accessible`); frontend deploys go through the Vercel GitHub integration. Safe to delete, or replace with a fresh dashboard token if CI-owned deploys are ever wanted again |
  | `CLERK_PUBLISHABLE_KEY` (Actions *variable*) | **set** — build-time pk source |
  | `RENDER_API_KEY`, `RENDER_PROD_BACKEND_ID` | not set — Render billing pending |

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

> **Status: LIVE in production.** Authenticated as `bosserrorneo-8234`, team
> `neohacker-proejects` (hobby), project `cyberverse` (`prj_mkE4apirmrR3kE7mnY5DNThPG8m7`).
> Production alias: https://cyberverse-neohacker-proejects.vercel.app
> (also aliased as https://cyberverse-beta.vercel.app).

- Next.js app root: `frontend/` (project setting `rootDirectory: frontend`).
- `/api/:path*` rewrites to `BACKEND_URL` (server-side env, default `http://127.0.0.1:8000`).
- No `NEXT_PUBLIC_*` required for core operation (same-origin `/api` via rewrite).
- `frontend/.env.example` documents `BACKEND_URL` and optional `NEXT_PUBLIC_GA_ID`
  (analytics is consent-gated and a silent no-op until set).

### Deploy
```bash
# From the REPO ROOT — the Vercel project's Root Directory is "frontend",
# so the upload must contain the frontend/ subdir (deploying from frontend/
# fails with "Root Directory frontend does not exist").
vercel link --yes --project cyberverse --scope neohacker-proejects
vercel deploy --prod --yes
```
Every push to `main` deploys automatically through the **Vercel GitHub
integration** (Production); branch pushes create Preview deployments. CI does
not push to Vercel.

Then set the backend `CORS_ORIGINS` to the assigned `*.vercel.app` domain.

Security headers (CSP, nosniff, Referrer-Policy, Permissions-Policy) ship from
`next.config.mjs` at build time. **Framing is deliberately permissive**
(`frame-ancestors *`, no `X-Frame-Options`) so the app renders inside embedded
views; before a real public launch with sensitive user data, re-add
`X-Frame-Options: DENY` + `frame-ancestors 'none'` there and rebuild.

---

## 4. CI/CD (GitHub Actions)

`.github/workflows/ci.yml` runs: backend lint+tests (with Postgres/Redis
services), frontend lint/typecheck/tests/**production build**, Trivy fs scan,
gitleaks secret scan, Docker image builds to GHCR, and staging/production deploy
jobs. Every step is guarded by `if: env.<SECRET> != ''`, so the pipeline stays
green until each credential exists.

- **Deploy to Production** (push to `main`): Render step stays skipped until
  `RENDER_API_KEY`/`RENDER_PROD_BACKEND_ID` are set. The frontend deploys via
  the Vercel GitHub integration (verified 2026-10-27: pushes `a1a3b17` and
  `3904346` each produced a Production deployment with `source=github-push`).
- **Deploy to Staging** (push to `develop`): Render step guarded the same way;
  Vercel previews come from the GitHub integration.
- Repository secrets required for the deploy jobs: `RENDER_API_KEY`,
  `RENDER_STAGING_BACKEND_ID`, `RENDER_PROD_BACKEND_ID`.
  Set with: `gh secret set NAME --repo ashrafhacker/CyberVerse`.

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
| GitHub push | **Done** | `gh auth setup-git` (keyring token) + `git push origin main` to `ashrafhacker/CyberVerse` |
| Vercel deploy | **Done** | Live in production; the Vercel GitHub integration redeploys every push to `main` (the duplicate CI `vercel --prod` step was removed 2026-10-27 — its token no longer authenticated) |
| Render backend | **Superseded by blitz (§7)** — Render stays blocked (billing) | `POST /v1/services` returns **HTTP 402: "Payment information is required…"**. Only revisit Render if leaving blitz; the production backend is `cyberverse-api` on blitz (§7). CI still carries the Render deploy steps as no-ops (`if: env.RENDER_API_KEY != ''`). |
| GH Pages | Not applicable | The frontend is a dynamic Next.js app (server rewrites proxy `/api/*` to the backend); a static GH Pages copy would be a non-functional duplicate of the Vercel deployment. Use the Vercel URL. |
| Upstash Redis | Not configured | Create free DB → put `rediss://...` into `REDIS_URL`/`CELERY_*` (Render Redis add-on is the simpler default) |
| Cloudflare R2 | Blocked | Needs `R2_ACCOUNT_ID`/keys; `backend/.env.r2.example` documents the shape. Existing `cyberverse-assets` bucket must be reconciled by checksum before any upload — no bulk upload performed |
| Sentry | Not configured | Replace placeholder DSN in backend env |
| SendGrid delivery | Configured, not verified | Send one test message to an authorized recipient after setting the key in the hosting env (blitz, §7) |
| Clerk | Configured, dashboard step pending | Backend verifies RS256 session tokens (JWKS), syncs users via `/auth/me` lazy provision + `POST /api/v1/auth/clerk/webhook`. Set `CLERK_PUBLISHABLE_KEY`/`CLERK_SECRET_KEY` in Render, then in **Clerk Dashboard → Webhooks** add endpoint `https://cyberverse-api.onrender.com/api/v1/auth/clerk/webhook` with the `whsec_…` secret placed in `CLERK_WEBHOOK_SECRET`. Events: `user.created`, `user.updated`, `user.deleted`. Switch the instance to **production keys** (`pk_live_`/`sk_live_`) before launch |
| Resend | Not applicable | SendGrid is the configured provider |

---

## 7. blitz backend runbook (**RETIRED 2026-10-30** — historical reference only)

> ⚠️ **Deprecated.** The blitz backend was retired on 2026-10-30 when the stack
> moved to Render free tier. Do not use the URLs/commands below for new work;
> they are kept only for rollback archaeology. Current backend facts live in §6
> and `render.yaml`.

**Identity (historical)**

| Item | Value |
| ---- | ----- |
| Platform | blitz — **Free plan** (`€0`; do not upgrade: limits below) |
| App | `cyberverse-api`, id `6985e3bc-0cbd-4ab2-8bcf-36d38c3ee24b`, project `CyberVerse` |
| Public URL | https://cyberverse-api.cyberverse.blitz.cloud |
| Build source | GitHub `ashrafhacker/CyberVerse` `main` — push triggers an automatic build+deploy (verified: pushes `8341af6` and `a37e675` each produced a blitz build without any manual step) |
| Latest deployed build | `a37e675` "fix: merge frontend url into cors" (build `e6144d00`, finished 2026-10-28T05:26:11Z) |
| Redis | blitz Redis, id `9559e0e6-cd4b-4193-91d6-68fa80ea7a36`, wired via `REDIS_URL` |
| Uptime Kuma | separate blitz app `fb85a590-ce26-4558-a552-28d4809cec21` |

**Free-plan limits (verify in the blitz dashboard before scaling)**

| Limit | Value | Last checked |
| ----- | ----- | ------------ |
| Apps | 2 / 5 used | 2026-10-27 |
| DB slots | 1 / 1 used (Neon is external — the slot is the blitz-managed Redis) | 2026-10-27 |
| RAM per app | 512 MB | 2026-10-27 |
| Build minutes | 6 / 300 this period (reset 2026-11-01) | 2026-10-27 |

**Wake behavior:** free apps sleep on idle. A request after idle wakes the app —
expect cold-start latency (DB check ~2 s on the first call) and re-test after
~60 s. `blitz env set` does **not** restart the app; `blitz restart --yes` does,
and requests immediately after a restart can still hit the old process for up to
~1 min. One-line remote command form:
`blitz run cyberverse-api --yes -- sh -c '<cmd>'`.

**Env vars (names only — values live in the blitz dashboard, never in git/chat):**

`DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`,
`CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`, `CLERK_WEBHOOK_SECRET` (**missing** —
see §6), `CORS_ORIGINS`, `FRONTEND_URL`, `SENTRY_DSN`, `ENVIRONMENT`, plus the
app/feature settings. Inventory taken 2026-10-28: 25 names total. No
SendGrid/SMTP key and no AI provider key are set (see §6).

**CORS (verified 2026-10-28, both curl preflight and a real browser fetch):**

`CORS_ORIGINS` is a JSON list of exactly these five origins:

1. `https://cyberverse-neohacker-proejects.vercel.app` (production frontend)
2. `https://cyberverse-beta.vercel.app`
3. `https://cyberverse.vercel.app`
4. `http://localhost:3000`
5. `http://localhost:3001`

`FRONTEND_URL` is merged into the allow-list at startup by the
`_merge_frontend_cors` validator in `backend/app/core/config.py` (`a37e675`), so
changing `FRONTEND_URL` can never lock the frontend out again. CORS behavior:
`OPTIONS` preflight from an allowed origin → 200 with `access-control-allow-origin`
echoing that origin; credentialed `GET` from an allowed origin → 401 (signed out)
with ACAO + `access-control-allow-credentials: true` + `access-control-expose-headers`.
Disallowed origins get no ACAO header. Adding an origin = `blitz env set
CORS_ORIGINS '<json list>'` + `blitz restart --yes` + re-test after ~60 s.

**Celery — documented, no worker (intentional):** broker
(`celery_broker: ok` in `/health/detailed`, producer connects) is VERIFIED;
there is **no worker process** on the free app, so queued tasks are never
consumed. Nothing currently enqueues work in the request path. Before enabling
any feature that relies on background tasks, either run a worker (separate
command/process in the app) or revisit the plan.

**Endpoints verified against the deployed build (2026-10-28):**
`GET /health`, `GET /health/detailed` (db/redis/celery_broker all `ok`),
`GET /api/v1/...` routing, Clerk JWKS, `POST /api/v1/ai/chat` (offline fallback
truthful reply; schema-invalid body → 422; auth-gated AI routes → 401).
