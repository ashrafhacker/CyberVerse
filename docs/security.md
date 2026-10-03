# CyberVerse Security

## Threat Model

CyberVerse is an educational platform with **no real-world attack surface** — all practical content runs in simulated sandboxes. The application itself, however, stores accounts, progress, and payment data, so it follows standard web application hardening.

| Asset | Risk | Mitigation |
|-------|------|------------|
| User accounts | Credential stuffing, brute force | bcrypt, rate limiting, lockout, 2FA |
| Session tokens | Theft, fixation | Server-side sessions, rotation, revocation |
| PII (email, name) | Data breach | Minimal collection, encryption at rest, access control |
| Payments | Fraud | Stripe hosted checkout, webhook signature verification |
| AI integration | Prompt injection, cost abuse | System prompts, rate limits, fallback modes |
| Admin actions | Privilege escalation | RBAC hierarchy, audit logging, super_admin isolation |

## Authentication

- Passwords hashed with **bcrypt** (12 rounds) in `app/core/security.py`
- JWT access tokens: 30-minute lifetime, HS256, `sub` = user id, role embedded
- Refresh tokens are opaque values stored in the `sessions` table; rotation invalidates old tokens
- Account lockout after N failed logins (`failed_login_attempts`, `locked_until`)
- Every login writes to `login_history` and registers/updates a `Device`
- 2FA: TOTP via `pyotp`, backed up by hashed recovery codes
- Email verification required before privileged operations (`require_verified`)

## Authorization (RBAC)

Role hierarchy enforced in `app/api/deps.py`:

```
guest < student < premium_student < instructor < moderator < administrator < developer < super_admin
```

- `require_role(min_role)` rejects users below the threshold with 403
- `require_super_admin` guards role changes and destructive ops
- Instructor endpoints enforce **content ownership** (creator_id) — authors cannot edit others' courses

## API Security

- **Rate limiting** (`app/core/redis.py`): per-user + per-IP fixed windows on auth endpoints (login 5/min, register 3/min, refresh 10/min, password reset 3/hr)
- **Input validation**: Pydantic v2 schemas with strict length/range/pattern constraints; rejected payloads never reach handlers
- **SQL injection**: impossible via SQLAlchemy expression language; raw SQL only in Alembic migrations
- **IDOR**: all user-scoped queries filter on `user_id == current_user.id`
- **CORS**: explicit origin allowlist from env (`CORS_ORIGINS`)
- **JSON body size**: FastAPI default limits + nginx/Caddy proxy limits

## Data Protection

- Secrets only via environment variables (`backend/.env.example` documents all keys; real `.env` is gitignored)
- `SECRET_KEY` / `JWT_SECRET_KEY` must be ≥64 random chars in production
- Payment data never touches our servers — Stripe Checkout handles card entry
- Email addresses and names are the only PII collected; no phone/address data
- Structured logs redact emails, tokens, and card fragments

## Frontend Hardening

- Next.js headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy` (see `next.config.mjs`)
- Caddy adds HSTS + CSP in production (see `devops/Caddyfile`)
- No `dangerouslySetInnerHTML`; all user content rendered as text
- Tokens in localStorage (MVP) — production hardening: HttpOnly cookies + CSRF tokens
- `next lint` and `tsc --noEmit` run in CI

## Infrastructure

- Docker images run as non-root user, slim base images
- Health checks on all services; compose secrets via env_file
- Caddy terminates TLS with automatic Let's Encrypt certificates
- Database credentials rotated; never committed

## CI/CD Security Gates

`.github/workflows/ci.yml` (devops/ci.yml):
1. `ruff` + `black` lint
2. Backend tests against ephemeral Postgres + Redis
3. Frontend lint + typecheck + tests
4. **Trivy** filesystem scan (fails on CRITICAL/HIGH)
5. **gitleaks** secret scan (fails on leaked secrets)
6. Image build + push to GHCR (immutable `$sha` tags)
7. Deploy to staging (develop) / production (main)

## Incident Response

1. **Detect** — Sentry (optional `SENTRY_DSN`), structured logs, `/health` monitoring
2. **Contain** — revoke sessions (`/auth/sessions`), suspend user via admin, rotate secrets
3. **Forensics** — `audit_logs` + `login_history` provide the trail
4. **Recover** — password reset flow, restore from Supabase point-in-time backup
5. **Learn** — postmortem doc + regression test

## Responsible Disclosure

CyberVerse hosts **no real attack infrastructure**. If you find a vulnerability in the platform itself, contact security@cyberverse.io (placeholder) — we operate a coordinated disclosure policy and never pursue legal action against good-faith reporters.
