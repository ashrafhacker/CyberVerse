from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import AuditLog


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
