# CyberVerse Production-Readiness Mission — Checkpoint

> 12-phase audit / repair / deploy mission. This file is the durable checkpoint
> across sessions. Update it at the end of every working session.
>
> Rules in force: additive/reversible DB changes only (never touch Neon data
> destructively), no secrets in chat or git, free-tier infra only, tests before
> any merge/deploy, no push/deploy without passing tests + review.

## Current state (updated 2026-10-30)

- **Branch:** `deploy/render-migration` at `4dc4a94` **+ local merge of
  `origin/main` (571f0be)** — merge clean, all tests re-run green. **NOT pushed.**
- **Phase:** PHASE 1 (repo & infra audit) COMPLETE. PHASE 2 (backup verify)
  partially blocked. PHASE 3 root cause identified. Repair work not started.
- **Production today:** backend = Render free tier `cyberverse-api.onrender.com`
  (live, healthy, v2.1.0-pro, deployed from main 571f0be); frontend = Vercel
  `cyberverse-neohacker-proejects.vercel.app` (live but **hardcodes the dead
  blitz API URL** → dashboard infinite-loading bug); blitz backend = dead.
  Custom domains `cyberverse.qd.je` / `api.cyberverse.qd.je` = DNS not resolving.

## Completed

### PHASE 1 — Audit (all read-only)
- Backend architecture: 31 routers, auth via `app/api/deps.py` (Clerk RS256 +
  legacy HS256, lazy provisioning via `clerk_sync`, role hierarchy
  `require_role`/`require_admin`). Solid.
- Frontend auth flow audited: `lib/auth.tsx` (AuthProvider + useRequireAuth),
  `lib/api.ts`, dashboard page, TerminalCard LoadingScreen.
- **Dashboard "establishing secure connection..." root cause found** (see below).
- Clerk backend verification audited: `app/core/clerk.py` — RS256 pinned at
  header check AND decode, JWKS cache w/ TTL+lock+rotation-retry, lazy issuer
  (from main c2f314f), no token leakage. `mcp_auth.py` same pattern + aud/typ.
- All 4 `jwt.decode` sites pin `algorithms=[...]` → python-jose algorithm-
  confusion advisory (PYSEC-2026-4298) mitigated in practice.
- Alembic: 9 revisions, linear, **single head `0007_library_enum_names`**;
  prod `alembic_version` = same (verified read-only).
- Prod DB read-only inspection: **85 tables** (74 via migrations + 10 game
  tables via startup `create_all` + alembic_version). All game tables present.
- Infra: Render free tier live w/ web+redis+broker OK; CORS allowlist verified
  (Vercel origin allowed, evil origin denied); security headers strong
  (CSP/HSTS/XFO DENY/nosniff/referrer-policy).
- Vercel CLI authenticated (proj `cyberverse`, id prj_mkE4apirmrR3kE7mnY5DNThPG8m7).
- Tests: backend **75/75 pass**; frontend tsc 0, lint 0 (warnings), **build 0**,
  vitest **91/91 pass**; MCP+clerk subset **24/24 pass after main merge**.
- Deps: prod npm deps 0 vulns; 8 dev-only npm vulns (vitest/vite tooling);
  pip-audit: python-jose + ecdsa advisories, no upstream fix, mitigated (above).
- Git: remote = github.com/ashrafhacker/CyberVerse; merged origin/main
  (c2f314f lazy-issuer + 571f0be vercel.json drop) into branch — no conflicts.

## Key findings (severity-ordered)

1. **CRITICAL — Live frontend hardcodes dead blitz API URL.** Vercel env
   `NEXT_PUBLIC_API_URL` = blitz (bundle chunk 7621… confirms). blitz DNS dead
   → every API call NetworkError → `refreshUser` catch → `user=null` →
   `useRequireAuth` retries forever every 2s → dashboard
   `if (loading || !user) return <LoadingScreen/>` loops "establishing secure
   connection..." forever. Amplifying defects: no error state, unbounded retry,
   failed-profile treated as loading.
2. **HIGH — Prod MCP discovery still advertises blitz resource URI** (deploy is
   from main which lacks 4dc4a94). Verified live: `.well-known` returns blitz.
3. **HIGH — Vercel Production runs Clerk TEST keys** (sk_test_/pk_test_).
   Live keys exist (user-provided). Security-sensitive → needs user approval.
4. **MEDIUM — No Celery worker on Render** → emails/notifications silently
   dropped (`dispatch_email` fails gracefully). `CLERK_WEBHOOK_SECRET` missing
   → webhook user-sync can't verify (needs whsec_… value in Render env).
5. **MEDIUM — Schema drift risk:** 10 game tables exist only via startup
   `create_all`, not Alembic. Works today; column-level model changes on those
   tables would silently not apply. Needs a catch-up migration eventually.
6. **LOW** — docs claim "75 tables" (actual 85); dev-only npm vulns; rate
   limits configured but only wired to auth/AI routes; /health/detailed cold
   start 2.7s (free tier).
7. **BACKUP — external drive unmounted** ("New Volume" sda2 NTFS 68G); mount
   hung via udisksctl, sudo needs password → backup contents UNVERIFIED.

## Pending (next actions, in order)

1. PHASE 3/4 — frontend auth repair on branch: bounded retries, distinct states
   (loading / authenticated / logged-out / session-expired / backend-unavailable
   / profile-failed / auth-error), working Retry + safe sign-out, no token in
   logs. Tests for each state.
2. Push branch → PR → merge to main (after review) → Render auto-deploy →
   verify MCP `.well-known` advertises onrender URI + `POST /api/v1/mcp/` 200
   with `Bearer <at+JWT>`.
3. Update Vercel env `NEXT_PUBLIC_API_URL` (+`BACKEND_URL`) to onrender URL,
   redeploy frontend, verify dashboard loads past the loading screen.
4. PHASE 5+ — DNS (identify provider for qd.je), custom domains, Clerk live
   keys on Vercel (approval), Render env additions (whsec webhook secret),
   Celery worker or sync email fallback, docs updates.

## Blocked / needs user

- **Backup drive mount** (sudo password or manual mount of sda2) — cannot
  verify `/run/media/neo/New Volume/CyberVerse/` until then.
- **Clerk test-secret rotation** confirmation (earlier exposed sk_test_…).
- **`CLERK_WEBHOOK_SECRET`** value for Render (whsec_…) — user to add in
  dashboard (never in chat/git).
- **DNS provider** for `qd.je` (so `cyberverse.qd.je` + `api.cyberverse.qd.je`
  can be pointed without touching unrelated records).
- **Approval gates:** pushing to main (auto-deploys prod Render), switching
  Vercel prod to Clerk live keys, any paid add-on (none currently needed —
  Render free tier verified working).
