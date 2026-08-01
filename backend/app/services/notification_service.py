from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationChannel, NotificationType


class NotificationService:
    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: UUID,
        title: str,
        body: str,
        notification_type: NotificationType = NotificationType.SYSTEM,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        link: Optional[str] = None,
        icon: Optional[str] = None,
        data: Optional[dict] = None,
        commit: bool = True,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            title=title,
            body=body,
            notification_type=notification_type,
            channel=channel,
            link=link,
            icon=icon,
            data=data or {},
        )
        db.add(notification)
        if commit:
            await db.commit()
        await db.refresh(notification)
        return notification

    @staticmethod
    async def create_many(
        db: AsyncSession,
        user_ids: list[UUID],
        title: str,
        body: str,
        notification_type: NotificationType = NotificationType.SYSTEM,
        link: Optional[str] = None,
        data: Optional[dict] = None,
    ) -> int:
        for user_id in user_ids:
            db.add(
                Notification(
                    user_id=user_id,
                    title=title,
                    body=body,
                    notification_type=notification_type,
                    link=link,
                    data=data or {},
                )
            )
        await db.commit()
        return len(user_ids)

    @staticmethod
    async def mark_read(db: AsyncSession, user_id: UUID, notification_id: UUID) -> bool:
        result = await db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        notification = result.scalar_one_or_none()
        if not notification:
            return False
        notification.is_read = True
        notification.read_at = func.now()
        await db.commit()
        return True

    @staticmethod
    async def mark_all_read(db: AsyncSession, user_id: UUID) -> int:
        result = await db.execute(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        notifications = result.scalars().all()
        for n in notifications:
            n.is_read = True
            n.read_at = func.now()
        await db.commit()
        return len(notifications)

    @staticmethod
    async def unread_count(db: AsyncSession, user_id: UUID) -> int:
        result = await db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        return result.scalar_one()