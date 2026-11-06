import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import AuditLog
from app.services.admin_events import AdminEventHub

logger = logging.getLogger(__name__)


class AuditService:
    @staticmethod
    async def log(
        db: AsyncSession,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        user_id: UUID | None = None,
        before: dict | None = None,
        after: dict | None = None,
        meta: dict | None = None,
        commit: bool = True,
    ) -> AuditLog:
        """Persist an audit row and publish it to the admin live stream.

        The JSONB column is mapped as ``meta_data`` (column name
        ``metadata``); passing ``metadata=`` to the constructor would be
        silently swallowed by the declarative base — never do that.
        """
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            before=before,
            after=after,
            meta_data=meta or {},
        )
        db.add(entry)
        if commit:
            await db.commit()
        try:
            AdminEventHub.publish(
                {
                    "type": "audit",
                    "action": action,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "user_id": str(user_id) if user_id else None,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            )
        except Exception:  # noqa: BLE001 — the stream must never break writes
            logger.warning("admin_event_publish_failed", exc_info=True)
        return entry
