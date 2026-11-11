import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationChannel, NotificationType

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: UUID,
        title: str,
        body: str,
        notification_type: NotificationType = NotificationType.SYSTEM,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        link: str | None = None,
        icon: str | None = None,
        data: dict | None = None,
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
        link: str | None = None,
        data: dict | None = None,
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
    async def notify_admins(
        db: AsyncSession,
        *,
        title: str,
        body: str,
        notification_type: NotificationType = NotificationType.SYSTEM,
        link: str | None = None,
        icon: str | None = None,
        data: dict | None = None,
        commit: bool = False,
    ) -> int:
        """Best-effort in-app notification to every administrator-ish user.

        Targets the same role set as the ``require_admin`` dependency
        (administrator / developer / super_admin). Never raises — a
        notification failure must not break the parent flow. When
        ``commit`` is False the rows join the caller's transaction; the
        caller is responsible for committing.

        Returns the number of admins notified (0 on failure).
        """
        from app.models.user import User, UserRole

        try:
            result = await db.execute(
                select(User.id).where(
                    User.role.in_(
                        [UserRole.ADMINISTRATOR, UserRole.DEVELOPER, UserRole.SUPER_ADMIN]
                    )
                )
            )
            admin_ids = [row[0] for row in result.all()]
            if not admin_ids:
                return 0
            for admin_id in admin_ids:
                db.add(
                    Notification(
                        user_id=admin_id,
                        title=title[:200],
                        body=body,
                        notification_type=notification_type,
                        link=link,
                        icon=icon,
                        data=data or {},
                    )
                )
            if commit:
                await db.commit()
            return len(admin_ids)
        except Exception:
            logger.exception("notify_admins failed for %r", title)
            return 0

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
