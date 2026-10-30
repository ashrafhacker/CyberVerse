# CyberVerse Production-Readiness Mission — Checkpoint

> 12-phase audit / repair / deploy mission. This file is the durable checkpoint
> across sessions. Update it at the end of every working session.
>
> Rules in force: additive/reversible DB changes only (never touch Neon data
> destructively), no secrets in chat or git, free-tier infra only, tests before
> any merge/deploy.

## Current state (updated 2026-10-30, post-deploy)

- **Branch:** `deploy/render-migration` = `main` = **`04315a2`** (pushed; Render +
  Vercel deployed from it).
- **Phase:** PHASE 1 audit complete. Dashboard root cause FIXED, TESTED and
  DEPLOYED. Awaiting: signed-in e2e verify, backup-drive verify, Clerk webhook
  secret, DNS phase.
- **Production now:** backend Render free tier `cyberverse-api.onrender.com`
  (deployed from main 04315a2; MCP discovery advertises
  `resource: https://cyberverse-api.onrender.com/mcp` — blitz retired ✅);
  frontend Vercel prod `cyberverse-neohacker-proejects.vercel.app`
  (deployment `cyberverse-1o9ahegz4…`, bundle bakes
  `https://cyberverse-api.onrender.com/api/v1`, zero blitz ✅).
  Custom domains `cyberverse.qd.je` / `api.cyberverse.qd.je`: DNS still not
  configured (PHASE DNS, pending provider identification).

## Deployed this session

1. `3cd05b8` — frontend auth state machine: bounded auto-retry (max 4,
   exponential backoff) replaces the unbounded 2s loop; 7-state `AuthStatus`;
   token-free `error`; manual `retry()`; `AuthProblemScreen` (Retry + safe
   Sign out); dashboard renders distinct states instead of eternal spinner.
   +5 tests (96/96 pass; backend 75/75; tsc 0; lint 0; build 0).
2. `04315a2` — `NEXT_PUBLIC_API_URL` corrected to include `/api/v1` (routes
   only exist under /api/v1: root /auth/me=404, /api/v1/auth/me=401, verified
   live). Fixed the wrong value my earlier 4dc4a94 had committed.
3. Vercel env replaced (all scopes): `NEXT_PUBLIC_API_URL` =
   `https://cyberverse-api.onrender.com/api/v1` (Production/Preview/Dev),
   `BACKEND_URL` = `https://cyberverse-api.onrender.com` (Production/Preview).
   Frontend redeployed via CLI; live bundle re-scanned: onrender only.
4. Pushed `deploy/render-migration` + fast-forwarded `main` (571f0be → 04315a2).

## Verified live (evidence)

- Render `/health` 200 (v2.1.0-pro, deployed from main 04315a2).
- MCP `.well-known/oauth-protected-resource/mcp` → onrender resource URI.
- Vercel production bundle chunk scan: `onrender/api/v1` present, no blitz.
- Headless Firefox visit to live `/dashboard`: settles in **5.4s**,
  redirects signed-out visitor to `/login?redirect=%2Fdashboard`, login page
  renders, `stuck_on_spinner: false` (was: infinite "establishing secure
  connection..."). Screenshot: /tmp/opencode/dashboard-final.png.
- CORS allowlist + security headers on Render (earlier audit, unchanged).

## Blocked / awaiting user

- **Backup drive** ("New Volume", sda2, NTFS) unmounted; `udisksctl` hung, sudo
  needs password. Mission rule: existing-hosting deletion forbidden until
  backup verified. No existing hosting deleted — rule honored.
- **`CLERK_WEBHOOK_SECRET`** (whsec_…) must be added in Render dashboard by
  user (secrets never pass through chat).
- Confirm the exposed Clerk **test** key (`sk_test_…`, seen in Vercel env
  listing) was rotated. Vercel prod is still on Clerk TEST keys — switching to
  live keys is a separate approval-gated step.
- **DNS provider for `qd.je`** not identified from repo; DNS phase blocked
  until user names the provider.

## Findings (1–4) status

1. blitz URLs — fixed (4dc4a94), now fully retired from prod (verified).
2. Backup unverified — BLOCKED (unchanged); no deletions made.
3. Dashboard infinite loading — **FIXED, TESTED, DEPLOYED, E2E-VERIFIED**
   (signed-out path). Signed-in path unit-tested; live signed-in e2e still
   needs a user session (never requested in chat).
4. Clerk test keys in prod — FLAGGED, awaiting rotation confirmation.

## Pending (next session)

- PHASE DNS: user names `qd.je` provider; point apex → Vercel, `api.` CNAME →
  Render; then custom domains in both dashboards; move Clerk redirect URLs.
- Signed-in e2e once user re-authenticates on the live site.
- Backend: decide Celery worker vs sync email fallback (Render blueprint has
  no worker; celery-worker.py exists for local).
- Alembic-vs-create_all drift guard for the 10 game tables (currently
  created only by startup `create_all`).
- Table-count claim in docs: prod has **85** tables (74 via migrations +
  10 game via create_all + alembic_version), not 75 — fix docs when touched.
- Free-tier realities: Render cold start ~30–50s (frontend 30s fetch timeout +
  bounded auth retries cover most of it; manual Retry covers the rest).
