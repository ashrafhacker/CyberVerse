# Environment Variable Checklist (No Secret Values Printed)

REQUIRED (must be set in Render dashboard / .env.local / Cloudflare secret):
- ENVIRONMENT = production
- DEBUG = false
- SECRET_KEY = (generate; 32+ chars; SecretStr-masked in logs)
- JWT_SECRET_KEY = (generate; 32+ chars)
- DATABASE_URL = postgresql://... (Neon existing project; sync URL for Alembic; computed `database_url_async` used at runtime)
- REDIS_URL = rediss://... (Upstash Redis free; TLS required)
- CELERY_BROKER_URL = redis://... or rediss://... (same Redis; use db index 1 for broker, 2 for result)
- CELERY_RESULT_BACKEND = redis://... (db 2)
- CLERK_PUBLISHABLE_KEY = (existing Clerk project)
- CLERK_SECRET_KEY = (SecretStr; existing Clerk project)
- CLERK_WEBHOOK_SECRET = (SecretStr; guard only — do not emit in responses; verified by admin endpoint at line 1235)
- CORS_ORIGINS = ["https://cyberverse-neohacker-proejects.vercel.app"] (update after frontend deploy)
- FRONTEND_URL = https://cyberverse-neohacker-proejects.vercel.app (match CORS)
- BCRYPT_ROUNDS = 12
- DATABASE_POOL_SIZE = 5 (Render free RAM limit; lower from default 20)
- LOG_LEVEL = INFO

OPTIONAL / FREE-TIER REPLACEMENTS:
- SENDGRID_API_KEY = (current supported email provider; Resend is not implemented in settings)
- EMAIL_BACKEND = sendgrid, console, or dummy (resend is not a supported literal)
- CONTACT_FORM_RECIPIENT = (existing support inbox)
- SENTRY_DSN = (optional; free tier available)
- REDIS_MAX_CONNECTIONS = 5 (optional; code default is 50, minimum is 5)
- CELERY_TASK_TIME_LIMIT = 300; CELERY_TASK_SOFT_TIME_LIMIT = 270 (code defaults)

NOT SET / NOT REQUIRED (no secret exposure risk):
- R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY / R2_ENDPOINT_URL (optional media storage; not required for readiness)
- OPENAI_API_KEY / GEMINI_API_KEY (optional AI; no impact on readiness)
- RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET (optional payments; not required)
- GOOGLE_CLIENT_ID / GITHUB_CLIENT_ID (optional OAuth; not required)
- PROMETHEUS_ENABLED = false (free tier; no metrics server needed)
