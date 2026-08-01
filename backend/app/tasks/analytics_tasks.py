from datetime import datetime, timedelta, timezone

from celery import shared_task


@shared_task(name="app.tasks.analytics_tasks.recalculate_leaderboards")
def recalculate_leaderboards() -> dict:
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.core.database import engine
    from app.services.leaderboard_service import LeaderboardService

    async def _run():
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            board = await LeaderboardService.get_or_create_weekly(db)
            count = await LeaderboardService.rebuild_board(db, board)
            return count

    count = asyncio.run(_run())
    return {"entries_rebuilt": count}


@shared_task(name="app.tasks.analytics_tasks.cleanup_expired_records")
def cleanup_expired_records() -> dict:
    import asyncio

    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.core.database import engine
    from app.models.session import Session

    async def _run():
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=30)
        async with session_factory() as db:
            result = await db.execute(
                delete(Session).where(
                    Session.refresh_expires_at < now,
                    Session.is_revoked.is_(True),
                )
            )
            await db.commit()
            return result.rowcount

    deleted = asyncio.run(_run())
    return {"sessions_cleaned": deleted}


@shared_task(name="app.tasks.analytics_tasks.track_event")
def track_event(user_id: str | None, event_type: str, properties: dict | None = None):
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.core.database import engine
    from app.models.analytics import AnalyticsEvent

    async def _create():
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            db.add(
                AnalyticsEvent(
                    user_id=user_id,
                    event_type=event_type,
                    properties=properties or {},
                )
            )
            await db.commit()

    asyncio.run(_create())
    return {"event_type": event_type}