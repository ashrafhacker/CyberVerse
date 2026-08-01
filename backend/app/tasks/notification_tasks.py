from celery import shared_task


@shared_task(name="app.tasks.notification_tasks.send_in_app_notification")
def send_in_app_notification(user_id: str, title: str, body: str, notification_type: str = "system", link: str | None = None):
    """Create an in-app notification for a user (runs in worker context)."""
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.core.database import engine
    from app.models.notification import Notification

    async def _create():
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            db.add(
                Notification(
                    user_id=user_id,
                    title=title,
                    body=body,
                    notification_type=notification_type,
                    link=link,
                )
            )
            await db.commit()

    asyncio.run(_create())
    return {"user_id": user_id, "title": title}


@shared_task(name="app.tasks.notification_tasks.send_bulk_notifications")
def send_bulk_notifications(user_ids: list[str], title: str, body: str, notification_type: str = "system"):
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.core.database import engine
    from app.models.notification import Notification

    async def _create_many():
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            for user_id in user_ids:
                db.add(
                    Notification(
                        user_id=user_id,
                        title=title,
                        body=body,
                        notification_type=notification_type,
                    )
                )
            await db.commit()

    asyncio.run(_create_many())
    return {"count": len(user_ids)}