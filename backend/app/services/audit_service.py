from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import AuditLog


class AuditService:
    @staticmethod
    async def log(
        db: AsyncSession,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[UUID] = None,
        before: Optional[dict] = None,
        after: Optional[dict] = None,
        meta: Optional[dict] = None,
        commit: bool = True,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            before=before,
            after=after,
            metadata=meta or {},
        )
        db.add(entry)
        if commit:
            await db.commit()
        return entry