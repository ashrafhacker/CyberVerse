from celery import Celery

from app.core.config import settings


celery_app = Celery(
    "cyberverse",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.email_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.analytics_tasks",
        "app.tasks.learning_tasks",
    ],
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