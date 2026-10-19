# CyberVerse — Deployment Runbook

> **Status as of 2026-10-19** — the stack is live except the backend, which is
> blocked on Render billing (one dashboard action, see §6).

Target architecture:

| Layer      | Provider            | State                                                        |
| ---------- | ------------------- | ------------------------------------------------------------ |
| Frontend   | Vercel (team `neohacker-proejects`, project `cyberverse`) | **Live** — https://cyberverse-neohacker-proejects.vercel.app (also `cyberverse-beta.vercel.app`). CI deploys on every push to `main`. |
| Backend    | Render              | Service **not created** — API creation reaches HTTP 402 (payment info required). Script ready, see §6. |
| Database   | Neon (us-east-1)    | **Live & verified** — project `crimson-firefly-97189410`, branch `cyberverse-production`, DB `cyberverse`, 75 tables, head=`0007_library_enum_names`. The unrelated `neondb` DB is untouched. |
| Cache/jobs | Render Redis (default) or Upstash | Config via `REDIS_URL`/`CELERY_*` — created with the Render service; no Upstash creds present |
| Git       | GitHub `ashrafhacker/CyberVerse` (public) | **Live** — `main` = `221665f`, pushed over HTTPS with the `gh` keyring token (`gh auth setup-git`) |
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
  **Deploy to Production** (Vercel). Deploy steps are guarded by
  `if: env.<SECRET> != ''` so the pipeline stays green while credentials are
  missing.
- Required GitHub Actions secrets (repo `ashrafhacker/CyberVerse`):
  | Secret | State |
  | --- | --- |
  | `VERCEL_TOKEN` | **set** (bosserrorneo-8234 CLI token) |
  | `VERCEL_PROJECT_ID` | **set** (`prj_mkE4apirmrR3kE7mnY5DNThPG8m7`) |
  | `VERCEL_ORG_ID` | **set** (`team_QuUUlV8KlBko8I8bFBz7V0wf`) |
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
> `neohacker-proejects` (hobby), project `cyververse` (`prj_mkE4apirmrR3kE7mnY5DNThPG8m7`).
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
Every push to `main` also deploys automatically via the CI `Deploy to Production`
job (uses the `VERCEL_TOKEN` Actions secret).

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

- **Deploy to Production** (push to `main`): Vercel step is **active** (verified
  2026-10-19, run `39230649046` → deployment `cyberverse-3is9omlg4`); Render
  step stays skipped until `RENDER_API_KEY`/`RENDER_PROD_BACKEND_ID` are set.
- **Deploy to Staging** (push to `develop`): both steps guarded the same way.
- Repository secrets required for the deploy jobs (see §1 table for state):
  `RENDER_API_KEY`, `RENDER_STAGING_BACKEND_ID`, `RENDER_PROD_BACKEND_ID`,
  `VERCEL_TOKEN`, `VERCEL_PROJECT_ID`, `VERCEL_ORG_ID`.
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
| Vercel deploy | **Done** | Live in production; CI redeploys on every push to `main` |
| Render backend | Blocked (billing) | `POST /v1/services` with the correct `servicePOST` payload returns **HTTP 402: "Payment information is required… https://dashboard.render.com/billing"**. Add a card, then run `python3 /tmp/opencode/render_create3.py` (or `render_create.py` — same payload) to create `cyberverse-api`; afterwards set GitHub secrets `RENDER_API_KEY` + `RENDER_PROD_BACKEND_ID` so CI can trigger deploys. If Render then asks for a connected Git account, connect GitHub once in the dashboard (New → Web Service → pick `ashrafhacker/CyberVerse`). |
| GH Pages | Not applicable | The frontend is a dynamic Next.js app (server rewrites proxy `/api/*` to the backend); a static GH Pages copy would be a non-functional duplicate of the Vercel deployment. Use the Vercel URL. |
| Upstash Redis | Not configured | Create free DB → put `rediss://...` into `REDIS_URL`/`CELERY_*` (Render Redis add-on is the simpler default) |
| Cloudflare R2 | Blocked | Needs `R2_ACCOUNT_ID`/keys; `backend/.env.r2.example` documents the shape. Existing `cyberverse-assets` bucket must be reconciled by checksum before any upload — no bulk upload performed |
| Sentry | Not configured | Replace placeholder DSN in backend env |
| SendGrid delivery | Configured, not verified | Send one test message to an authorized recipient after setting the key in Render |
| Clerk | Configured, dashboard step pending | Backend verifies RS256 session tokens (JWKS), syncs users via `/auth/me` lazy provision + `POST /api/v1/auth/clerk/webhook`. Set `CLERK_PUBLISHABLE_KEY`/`CLERK_SECRET_KEY` in Render, then in **Clerk Dashboard → Webhooks** add endpoint `https://cyberverse-api.onrender.com/api/v1/auth/clerk/webhook` with the `whsec_…` secret placed in `CLERK_WEBHOOK_SECRET`. Events: `user.created`, `user.updated`, `user.deleted`. Switch the instance to **production keys** (`pk_live_`/`sk_live_`) before launch |
| Resend | Not applicable | SendGrid is the configured provider |
