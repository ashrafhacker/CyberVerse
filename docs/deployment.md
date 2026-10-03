# CyberVerse Deployment

## Target Architecture (production)

| Service | Host | Notes |
|---------|------|-------|
| Frontend | Vercel | Next.js static/edge, `NEXT_PUBLIC_API_URL` |
| Backend API | Render | uvicorn, 4 workers, auto-deploy on main |
| PostgreSQL | Supabase | Managed, point-in-time backups |
| Redis | Render/Upstash | Cache + rate limiting + Celery broker |
| Celery | Render worker | async email/notifications/analytics |
| Caddy | VPS | TLS termination, API routing (self-host option) |

## Backend Deploy (Render)

1. Create a **Web Service** from the repo root `backend/`
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
2. Add environment variables from `backend/.env.example`
3. Run migrations once: `alembic upgrade head` (startup job)
4. Create a **Worker** for Celery: `celery -A app.core.celery_app.celery_app worker --loglevel=INFO`
5. Create a **Cron Job** for beat: `celery -A app.core.celery_app.celery_app beat --loglevel=INFO`

## Frontend Deploy (Vercel)

```bash
# Local
npm run build
npx vercel --prod

# CI (GitHub Actions) — see devops/ci.yml
npx vercel --prod --yes --token $VERCEL_TOKEN --scope $VERCEL_ORG_ID
```

Env vars:
- `NEXT_PUBLIC_API_URL=https://api.cyberverse.io/api/v1`

## Self-Hosted Option (Docker Compose)

```bash
# Production stack: postgres + redis + backend + celery + beat + frontend + caddy
docker compose -f docker/docker-compose.prod.yml up -d

# Development stack with hot reload
docker compose -f docker/docker-compose.dev.yml up
```

Requirements: create `backend/.env`, set `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `NEXT_PUBLIC_API_URL`.

## CI/CD Pipeline

See `devops/ci.yml` — runs on every push/PR to main & develop:

```
lint (ruff, black, eslint, tsc)
  → tests (pytest vs ephemeral PG+Redis, vitest)
  → security (trivy, gitleaks)
  → build images (GHCR, sha-tagged)
  → deploy staging (develop) / production (main)
```

## Environment Checklist

- [ ] `DEBUG=false`, `ENVIRONMENT=production`
- [ ] Strong `SECRET_KEY` + `JWT_SECRET_KEY` (≥64 random chars)
- [ ] `DATABASE_URL` → managed Postgres (Supabase), SSL required
- [ ] `CORS_ORIGINS` lists only real frontend domains
- [ ] `STRIPE_SECRET_KEY` + webhook secret configured
- [ ] `SENDGRID_API_KEY` verified sender domain
- [ ] `OPENAI_API_KEY` (optional — fallback mode works without it)
- [ ] Sentry DSN for error tracking (optional)

## Health & Monitoring

- `GET /health` — API liveness (used by Render/docker healthchecks)
- `GET /health/db` — DB connectivity
- Structured JSON logs to stdout; forward to a log aggregator
- Uptime checks on `/health` from an external monitor (e.g., UptimeRobot)

## Rollback Strategy

- **Frontend**: Vercel instant rollback to previous deployment
- **Backend**: redeploy previous image tag `ghcr.io/<repo>/backend:<prev-sha>`
- **Database**: Supabase PITR restore; migrations are forward-only with additive-first policy
- **Feature flags** (`feature_flags` table) allow disabling risky features without deploy

## Release Process

1. Merge to `develop` → staging deploy → smoke test
2. Tag `release/vX.Y.Z`
3. Merge to `main` → production deploy
4. Verify `/health`, login flow, one mission completion
5. Announce via admin announcement endpoint
