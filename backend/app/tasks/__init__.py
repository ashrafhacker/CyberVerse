"""
CyberVerse Celery Tasks Package.

Contains all Celery tasks for asynchronous processing including:
- Email delivery (verification, password reset)
- In-app and bulk notifications
- Analytics (leaderboard recalculation, expired session cleanup, event tracking)
- Learning content rotation (daily/weekly challenges)

Tasks are designed to be idempotent and handle missing optional dependencies gracefully.
"""

import asyncio
import logging
import random
from datetime import UTC, datetime, timedelta

from celery import shared_task
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker

logger = logging.getLogger(__name__)

# -------------------------------------------------------
# Email tasks (merged from email_tasks.py)
# -------------------------------------------------------


def dispatch_email(task, *args, **kwargs):
    """Dispatch a Celery email task without crashing the request."""
    from app.core.config import settings  # noqa: PLC0415

    if settings.ENVIRONMENT == "testing":
        logger.info("email_dispatch_skipped", extra={"task": "send_verification_email"})
        return None
    try:
        return task.delay(*args, **kwargs)
    except Exception as exc:
        logger.warning("email_dispatch_failed", extra={"task": "send_verification_email", "error": str(exc)})
        return None


@shared_task(name="app.tasks.email_tasks.send_verification_email")
@shared_task(name="app.tasks.send_verification_email")
def send_verification_email(email: str, token: str) -> dict:
    """Send email verification link to new user."""
    try:
        import sendgrid  # noqa: PLC0415
        from sendgrid.helpers.mail import Mail  # noqa: PLC0415

        from app.core.config import settings  # noqa: PLC0415
        sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        message = Mail(
            from_email=(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME),
            to_emails=email,
            subject="Verify your CyberVerse account",
            html_content=(
                f"<h2>Welcome to CyberVerse!</h2>"
                f"<p>Click the link below to verify your email address:</p>"
                f"<p><a href='https://cyberverse.io/verify-email?token={token}'>Verify Email</a></p>"
            ),
        )
        response = sg.send(message)
        return {"email": email, "status_code": response.status_code}
    except Exception as exc:
        import structlog  # noqa: PLC0415

        structlog.get_logger(__name__).warning("email_skipped", email=email, error=str(exc))
        return {"email": email, "status": "skipped", "error": str(exc)}


@shared_task(name="app.tasks.email_tasks.send_password_reset_email")
@shared_task(name="app.tasks.send_password_reset_email")
def send_password_reset_email(email: str, token: str) -> dict:
    """Send password reset link to user."""
    try:
        import sendgrid  # noqa: PLC0415
        from sendgrid.helpers.mail import Mail  # noqa: PLC0415

        from app.core.config import settings  # noqa: PLC0415
        sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        message = Mail(
            from_email=(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME),
            to_emails=email,
            subject="Reset your CyberVerse password",
            html_content=(
                f"<p>Click the link below to reset your password:</p>"
                f"<p><a href='https://cyberverse.io/reset-password?token={token}'>Reset Password</a></p>"
                f"<p>This link expires in 1 hour.</p>"
            ),
        )
        response = sg.send(message)
        return {"email": email, "status_code": response.status_code}
    except Exception as exc:
        import structlog  # noqa: PLC0415

        structlog.get_logger(__name__).warning("email_skipped", email=email, error=str(exc))
        return {"email": email, "status": "skipped", "error": str(exc)}

# -------------------------------------------------------
# Notification tasks (merged from notification_tasks.py)
# -------------------------------------------------------


@shared_task(name="app.tasks.notification_tasks.send_in_app_notification")
@shared_task(name="app.tasks.send_in_app_notification")
def send_in_app_notification(user_id: str, title: str, body: str, notification_type: str = "system", link: str | None = None):
    """Create an in-app notification for a user."""
    from app.core.database import engine  # noqa: PLC0415
    from app.models.notification import Notification  # noqa: PLC0415

    async def _create():
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            db.add(Notification(user_id=user_id, title=title, body=body, notification_type=notification_type, link=link))
            await db.commit()

    asyncio.run(_create())
    return {"user_id": user_id, "title": title}


@shared_task(name="app.tasks.notification_tasks.send_bulk_notifications")
@shared_task(name="app.tasks.send_bulk_notifications")
def send_bulk_notifications(user_ids: list[str], title: str, body: str, notification_type: str = "system"):
    """Create bulk in-app notifications for multiple users."""
    from app.core.database import engine  # noqa: PLC0415
    from app.models.notification import Notification  # noqa: PLC0415

    async def _create_many():
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            for user_id in user_ids:
                db.add(Notification(user_id=user_id, title=title, body=body, notification_type=notification_type))
            await db.commit()

    asyncio.run(_create_many())
    return {"count": len(user_ids)}

# -------------------------------------------------------
# Analytics tasks (merged from analytics_tasks.py)
# -------------------------------------------------------


@shared_task(name="app.tasks.analytics_tasks.recalculate_leaderboards")
@shared_task(name="app.tasks.recalculate_leaderboards")
def recalculate_leaderboards() -> dict:
    """Recalculate weekly leaderboard rankings."""
    from app.core.database import engine  # noqa: PLC0415
    from app.services.leaderboard_service import LeaderboardService  # noqa: PLC0415

    async def _run():
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            board = await LeaderboardService.get_or_create_weekly(db)
            return await LeaderboardService.rebuild_board(db, board)

    return {"entries_rebuilt": asyncio.run(_run())}


@shared_task(name="app.tasks.analytics_tasks.cleanup_expired_records")
@shared_task(name="app.tasks.cleanup_expired_records")
def cleanup_expired_records() -> dict:
    """Clean up expired revoked sessions."""
    from app.core.database import engine  # noqa: PLC0415
    from app.models.session import Session  # noqa: PLC0415

    async def _run():
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        now = datetime.now(UTC)
        async with session_factory() as db:
            result = await db.execute(delete(Session).where(Session.refresh_expires_at < now, Session.is_revoked.is_(True)))
            await db.commit()
            return result.rowcount

    deleted = asyncio.run(_run())
    return {"sessions_cleaned": deleted}


@shared_task(name="app.tasks.analytics_tasks.track_event")
@shared_task(name="app.tasks.track_event")
def track_event(user_id: str | None, event_type: str, properties: dict | None = None):
    """Track an analytics event."""
    from app.core.database import engine  # noqa: PLC0415
    from app.models.analytics import AnalyticsEvent  # noqa: PLC0415

    async def _create():
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            db.add(AnalyticsEvent(user_id=user_id, event_type=event_type, properties=properties or {}))
            await db.commit()

    asyncio.run(_create())
    return {"event_type": event_type}

# -------------------------------------------------------
# Learning tasks (merged from learning_tasks.py)
# -------------------------------------------------------


@shared_task(name="app.tasks.learning_tasks.rotate_daily_challenges")
@shared_task(name="app.tasks.rotate_daily_challenges")
def rotate_daily_challenges() -> dict:
    """Rotate daily challenges - remove expired and create new ones."""
    from app.core.database import engine  # noqa: PLC0415
    from app.models.achievement import DailyChallenge  # noqa: PLC0415

    tasks = [
        ("Complete a lesson", "lesson", 1, 60, 25),
        ("Pass a quiz", "quiz", 1, 80, 30),
        ("Complete a mission", "mission", 1, 100, 50),
        ("Spend 15 minutes learning", "time", 900, 40, 15),
        ("Complete a practice lab", "lab", 1, 90, 40),
    ]

    async def _run():
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        today = datetime.now(UTC).date()
        async with session_factory() as db:
            await db.execute(delete(DailyChallenge).where(DailyChallenge.challenge_date < datetime.combine(today, datetime.min.time(), tzinfo=UTC)))
            for _ in range(3):
                task_type, name, requirement, xp, coins = random.choice(tasks)
                db.add(DailyChallenge(
                    challenge_date=datetime.combine(today, datetime.min.time(), tzinfo=UTC),
                    title=f"Daily: {name.capitalize()}",
                    description=f"Complete {requirement} {name}(s) today to earn {xp} XP and {coins} coins.",
                    task_type=task_type, task_requirement=requirement, xp_reward=xp, coins_reward=coins, is_active=True,
                ))
            await db.commit()
            return 3

    count = asyncio.run(_run())
    return {"daily_challenges_created": count}


@shared_task(name="app.tasks.learning_tasks.rotate_weekly_challenges")
@shared_task(name="app.tasks.rotate_weekly_challenges")
def rotate_weekly_challenges() -> dict:
    """Rotate weekly challenges - remove expired and create new one."""
    from sqlalchemy.ext.asyncio import async_sessionmaker as _async_sessionmaker  # noqa: PLC0415

    from app.core.database import engine  # noqa: PLC0415
    from app.models.achievement import WeeklyChallenge  # noqa: PLC0415

    async def _run():
        session_factory = _async_sessionmaker(engine, expire_on_commit=False)
        now = datetime.now(UTC)
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
        async with session_factory() as db:
            await db.execute(delete(WeeklyChallenge).where(WeeklyChallenge.end_date < now))
            db.add(WeeklyChallenge(
                start_date=start, end_date=end, title="Weekly Challenge: Security Operations Week",
                description="Complete 5 lessons, 2 quizzes, and 1 mission to earn bonus XP and an exclusive weekly badge.",
                objectives=[{"type": "lesson", "requirement": 5}, {"type": "quiz", "requirement": 2}, {"type": "mission", "requirement": 1}],
                xp_reward=500, coins_reward=200, is_active=True,
            ))
            await db.commit()
            return 1

    count = asyncio.run(_run())
    return {"weekly_challenges_created": count}
