"""
Digital Forensics service: case and evidence management.

Implements case CRUD, evidence capture (metadata only — raw payloads
never reach the API), chain-of-custody tracking and status transitions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.digital_forensics import ForensicCase, ForensicEvidence


class DigitalForensicsError(ValueError):
    """Raised when a digital forensics operation cannot complete."""


def _case_number() -> str:
    return f"CF-{datetime.now(UTC).strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}"


def _case_dict(case: ForensicCase) -> dict:
    return {
        "id": case.id,
        "case_number": case.case_number,
        "title": case.title,
        "description": case.description,
        "severity": case.severity,
        "status": case.status,
        "opened_at": case.opened_at,
        "closed_at": case.closed_at,
        "evidence_count": len(case.evidence_items or []),
    }


def _evidence_dict(ev: ForensicEvidence) -> dict:
    return {
        "id": ev.id,
        "case_id": ev.case_id,
        "name": ev.name,
        "category": ev.category,
        "hash_sha256": ev.hash_sha256,
        "size_bytes": ev.size_bytes,
        "source_host": ev.source_host,
        "status": ev.status,
        "notes": ev.notes,
        "collected_by": ev.collected_by,
        "chain_of_custody": ev.chain_of_custody or [],
    }


class DigitalForensicsService:
    """Service for managing forensic cases and evidence."""

    @staticmethod
    async def create_case(
        db: AsyncSession,
        title: str,
        description: str,
        severity: str = "medium",
        owner_id: UUID | None = None,
        created_by: UUID | None = None,
    ) -> ForensicCase:
        case = ForensicCase(
            case_number=_case_number(),
            title=title,
            description=description,
            severity=severity,
            owner_id=owner_id,
            created_by=created_by,
        )
        db.add(case)
        await db.flush()
        return case

    @staticmethod
    async def get_case(db: AsyncSession, case_id: UUID) -> ForensicCase | None:
        result = await db.execute(
            select(ForensicCase)
            .where(ForensicCase.id == case_id)
            .options(selectinload(ForensicCase.evidence_items))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_cases(
        db: AsyncSession,
        owner_id: UUID,
        status: str | None = None,
        severity: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ForensicCase], int]:
        filters = [
            or_(ForensicCase.owner_id == owner_id, ForensicCase.created_by == owner_id)
        ]
        if status:
            filters.append(ForensicCase.status == status)
        if severity:
            filters.append(ForensicCase.severity == severity)
        if search:
            like = f"%{search}%"
            filters.append(
                or_(ForensicCase.title.ilike(like), ForensicCase.description.ilike(like),
                    ForensicCase.case_number.ilike(like))
            )

        total = (
            await db.execute(
                select(func.count()).select_from(ForensicCase).where(*filters)
            )
        ).scalar_one()

        rows = (
            await db.execute(
                select(ForensicCase)
                .where(*filters)
                .options(selectinload(ForensicCase.evidence_items))
                .order_by(ForensicCase.opened_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        return list(rows), total

    @staticmethod
    async def create_evidence(
        db: AsyncSession,
        case_id: UUID,
        name: str,
        category: str,
        hash_sha256: str | None = None,
        size_bytes: int | None = None,
        source_host: str | None = None,
        collected_by: UUID | None = None,
        notes: str | None = None,
    ) -> ForensicEvidence:
        case = await DigitalForensicsService.get_case(db, case_id)
        if case is None:
            raise DigitalForensicsError(f"Case {case_id} not found")

        evidence = ForensicEvidence(
            case_id=case_id,
            name=name,
            category=category,
            hash_sha256=hash_sha256.lower() if hash_sha256 else None,
            size_bytes=size_bytes,
            source_host=source_host,
            collected_by=collected_by,
            notes=notes,
        )
        db.add(evidence)
        await db.flush()
        return evidence

    @staticmethod
    async def get_evidence(db: AsyncSession, evidence_id: UUID) -> ForensicEvidence | None:
        result = await db.execute(
            select(ForensicEvidence).where(ForensicEvidence.id == evidence_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_evidence_by_case(
        db: AsyncSession,
        case_id: UUID,
        status: str | None = None,
    ) -> list[ForensicEvidence]:
        stmt = select(ForensicEvidence).where(ForensicEvidence.case_id == case_id)
        if status:
            stmt = stmt.where(ForensicEvidence.status == status)
        rows = (await db.execute(stmt.order_by(ForensicEvidence.created_at.asc()))).scalars().all()
        return list(rows)

    @staticmethod
    async def update_evidence_status(
        db: AsyncSession,
        evidence_id: UUID,
        status: str,
    ) -> ForensicEvidence:
        evidence = await DigitalForensicsService.get_evidence(db, evidence_id)
        if evidence is None:
            raise DigitalForensicsError(f"Evidence {evidence_id} not found")
        evidence.status = status
        evidence.updated_at = datetime.now(UTC)
        await db.flush()
        return evidence

    @staticmethod
    async def add_timeline_entry(
        db: AsyncSession,
        evidence_id: UUID,
        action: str,
        actor: str,
        notes: str | None = None,
    ) -> dict:
        evidence = await DigitalForensicsService.get_evidence(db, evidence_id)
        if evidence is None:
            raise DigitalForensicsError(f"Evidence {evidence_id} not found")

        entry = {
            "evidence_id": str(evidence.id),
            "case_id": str(evidence.case_id),
            "action": action,
            "actor": actor,
            "timestamp": datetime.now(UTC).isoformat(),
            "notes": notes,
        }
        evidence.chain_of_custody = [*(evidence.chain_of_custody or []), entry]
        evidence.updated_at = datetime.now(UTC)
        await db.flush()
        return entry

    @staticmethod
    async def get_case_summary(db: AsyncSession, case_id: UUID) -> dict:
        case = await DigitalForensicsService.get_case(db, case_id)
        if case is None:
            raise DigitalForensicsError(f"Case {case_id} not found")

        evidence_items = await DigitalForensicsService.list_evidence_by_case(db, case_id)

        return {
            "case": _case_dict(case) | {"evidence_count": len(evidence_items)},
            "evidence_count": len(evidence_items),
            "evidence": [_evidence_dict(ev) for ev in evidence_items],
        }

    @staticmethod
    async def close_case(db: AsyncSession, case_id: UUID) -> ForensicCase:
        case = await DigitalForensicsService.get_case(db, case_id)
        if case is None:
            raise DigitalForensicsError(f"Case {case_id} not found")
        case.status = "closed"
        case.closed_at = datetime.now(UTC)
        case.updated_at = datetime.now(UTC)
        await db.flush()
        return case
