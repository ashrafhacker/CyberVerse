# Celery Event-Driven Replacement (Free-Tier Safe)

PROBLEM: Render Free web service sleeps after 15 min of inactivity. A persistent Celery worker (`celery -A app.core.celery_app worker`) would be killed or unreachable after idle time, making scheduled tasks unreliable.

SAFE REPLACEMENT (no removal of functionality; event-driven equivalent):
- Use Cloudflare Workers with scheduled cron triggers (`wrangler.toml`) OR use Upstash QStash (free tier) to enqueue messages.
- The existing Celery tasks (`email_tasks`, `notification_tasks`, `analytics_tasks`, `learning_tasks`) are idempotent and handle exceptions gracefully. We preserve all tasks by mapping them to event triggers:
  1. Email tasks (`send_verification_email`, `send_password_reset_email`, `send_contact_notification`) → trigger via endpoint `/api/v1/auth/*` and `/api/v1/contact` (already called synchronously; on failure, enqueue to Upstash QStash or log to Resend retry queue). No persistent worker needed.
  2. Analytics (`recalculate_leaderboards`, `cleanup_expired_records`, `track_event`) → `recalculate_leaderboards` and `cleanup_expired_records` are periodic; replace with scheduled Cloudflare Worker cron (free: 5 min interval) that calls the endpoint `/api/v1/admin/production-readiness/backend` or a new protected endpoint `/tasks/trigger` that executes the idempotent logic directly.
  3. Learning (`rotate_daily_challenges`, `rotate_weekly_challenges`) → same scheduled cron approach.
  4. Notifications (`send_in_app_notification`, `send_bulk_notifications`) → keep synchronous (DB write is fast); no persistent worker required.

COMPATIBILITY:
- The `celery_app.py` and tasks files remain unchanged on disk. They are preserved.
- No background worker process runs continuously on Render Free. The `preDeployCommand` still runs `alembic upgrade head`; the `startCommand` only starts the API server (`uvicorn`).
- The `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` config points to Upstash Redis (`rediss://`). If the worker is absent, queued tasks will not process until either (a) a manual `celery -A ...` is started locally (dev/test), or (b) a paid Render Background Worker is added. This limitation is documented.

FEATURES THAT CANNOT OPERATE RELIABLY ON FREE TIER WITHOUT A PERSISTENT WORKER:
- Background Celery beat schedules (`rotate_daily_challenges`, `rotate_weekly_challenges`, `cleanup_expired_records`, `recalculate_leaderboards`) — reliable only when a persistent worker exists. On Render Free, these must be triggered by external cron (Cloudflare Workers scheduled events) or executed manually.
- `CELERY_TASK_TRACK_STARTED` and `CELERY_TASK_SOFT_TIME_LIMIT` behavior may differ with event-driven triggers (no process-level time enforcement).
