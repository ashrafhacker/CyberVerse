from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from celery import Celery

from app.core.config import settings


def _ensure_tls_params(url: str) -> str:
    """Normalise rediss:// Redis URLs so Celery does not crash at startup.

    Render Free KV serves a TLS-enabled endpoint (scheme ``rediss://``), which
    makes the Celery result backend require a valid ``ssl_cert_reqs`` query
    parameter. Celery rejects both a missing parameter and one set to anything
    other than ``CERT_REQUIRED``/``CERT_OPTIONAL``/``CERT_NONE`` with the same
    ``E_REDIS_SSL_CERT_REQS_MISSING_INVALID`` error, so this helper replaces
    any existing value (case-insensitively) and any invalid string with
    ``CERT_REQUIRED``. An explicit invalid value configured by hand would only
    leave the service broken, so overriding is the safe behaviour.

    ``CERT_REQUIRED`` pins TLS verification against the public CA chain
    (Cloudflare, which issues Render KV certs). If the handshake fails, flip
    the constant below to ``CERT_NONE`` (or ``CERT_OPTIONAL``) and redeploy.
    Idempotent and safe to run on every process.
    """
    if not url.startswith("rediss://"):
        return url
    parts = urlparse(url)
    params = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() != "ssl_cert_reqs"
    ]
    params.append(("ssl_cert_reqs", "CERT_REQUIRED"))
    return urlunparse((parts[0], parts[1], parts[2], parts[3], urlencode(params), ""))


celery_app = Celery(
    "cyberverse",
    broker=_ensure_tls_params(settings.CELERY_BROKER_URL),
    backend=_ensure_tls_params(settings.CELERY_RESULT_BACKEND),
    include=[
        "app.tasks",
        "app.tasks.email_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.analytics_tasks",
        "app.tasks.learning_tasks",
    ],
)
# Belt-and-braces: Celery maps the `broker=`/`backend=` kwargs onto the conf,
# but the worker reads `conf.result_backend`/`conf.broker_url`. Force the
# normalised values into conf explicitly so the banner-time backend build
# always sees the verified TLS configuration, regardless of key mapping order.
celery_app.conf.update(
    broker_url=_ensure_tls_params(settings.CELERY_BROKER_URL),
    result_backend=_ensure_tls_params(settings.CELERY_RESULT_BACKEND),
)

celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=True,
    task_track_started=settings.CELERY_TASK_TRACK_STARTED,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_TASK_TIME_LIMIT - 30,
    broker_connection_retry_on_startup=True,
    task_default_queue="cyberverse",
    task_routes={
        "app.tasks.email_tasks.*": {"queue": "emails"},
        "app.tasks.notification_tasks.*": {"queue": "notifications"},
        "app.tasks.analytics_tasks.*": {"queue": "analytics"},
        "app.tasks.learning_tasks.*": {"queue": "learning"},
    },
    task_queues={
        "cyberverse": {"exchange": "cyberverse", "binding_key": "cyberverse"},
        "emails": {"exchange": "emails", "binding_key": "emails"},
        "notifications": {"exchange": "notifications", "binding_key": "notifications"},
        "analytics": {"exchange": "analytics", "binding_key": "analytics"},
        "learning": {"exchange": "learning", "binding_key": "learning"},
    },
)

celery_app.conf.beat_schedule = {
    "daily-challenge-rotation": {
        "task": "app.tasks.learning_tasks.rotate_daily_challenges",
        "schedule": 24 * 60 * 60,
    },
    "weekly-challenge-rotation": {
        "task": "app.tasks.learning_tasks.rotate_weekly_challenges",
        "schedule": 7 * 24 * 60 * 60,
    },
    "leaderboard-recalculation": {
        "task": "app.tasks.analytics_tasks.recalculate_leaderboards",
        "schedule": 60 * 60,
    },
    "cleanup-expired-tokens": {
        "task": "app.tasks.analytics_tasks.cleanup_expired_records",
        "schedule": 6 * 60 * 60,
    },
}
