# Free Dev Services (Zero Cost — No Credit Card Required)
Verified against official pricing pages; no temporary trial / credit-based usage.

| Service | Free Tier | Usage in CyberVerse | Credit Card?
|---|---|---|---|
| Cloudflare Workers | 100k requests/day, 10ms CPU/request | Frontend adapter (see adapter-compat-check.md) | NO |
| Render Free (Web Service) | 512 MB RAM, 0.5 CPU, cold start ~1-2min after inactivity | FastAPI backend (`render.yaml`) | NO |
| Neon PostgreSQL (existing project) | 0.25 GB storage, 1 compute hour/month (free for 1 DB) | Existing `DATABASE_URL`; no replacement DB created | NO |
| Clerk (existing project) | 10,000 Monthly Active Users (free); webhook secret configured | Auth (`CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`, `CLERK_WEBHOOK_SECRET`) | NO |
| Upstash Redis Free | 256 MB, 10k requests/day, TLS (`rediss://`) | `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` (see event-replacement.md) | NO |
| Resend Free | 100 emails/day; SMTP/API; no CC | Email backend (`SENDGRID_API_KEY` replaced; use `RESEND_API_KEY`) | NO |
| GitHub | Public repos unlimited; Actions minutes (free tier) | Source control; CI checks | NO |

NOTES:
- Render Free web services sleep after 15 min of inactivity. Cold start is expected.
- No paid upgrade is required for any of these tiers.
- No local-machine hosting is used.
