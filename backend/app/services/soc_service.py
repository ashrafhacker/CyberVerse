"""
SOC simulator service: alert queue and incident lifecycle.

Implements the specification's SOC workflow with statuses
new → investigating → contained → recovering → resolved → closed,
analyst notes, MITRE mapping, and per-user scoping.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.soc import IncidentNote, SOCAlert, SOCIncident
from app.models.user import User, UserRole


class SOCError(ValueError):
    pass


def _incident_dict(incident: SOCIncident) -> dict:
    return {
        "id": incident.id,
        "case_number": incident.case_number,
        "title": incident.title,
        "description": incident.description,
        "severity": incident.severity,
        "priority": incident.priority,
        "status": incident.status,
        "mitre_mapping": incident.mitre_mapping or [],
        "affected_assets": incident.affected_assets or [],
        "evidence_ids": incident.evidence_ids or [],
        "root_cause": incident.root_cause,
        "containment_actions": incident.containment_actions or [],
        "remediation_plan": incident.remediation_plan,
        "analyst_notes": incident.analyst_notes or [],
        "timeline": incident.timeline or [],
        "opened_at": incident.opened_at,
        "resolved_at": incident.resolved_at,
        "closed_at": incident.closed_at,
        "updated_at": incident.updated_at,
    }


class SOCService:
    MANAGER_ROLES = {UserRole.MODERATOR, UserRole.ADMINISTRATOR, UserRole.DEVELOPER, UserRole.SUPER_ADMIN}

    @staticmethod
    async def list_alerts(
        db: AsyncSession,
        severity: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ):
        query = select(SOCAlert)
        if severity:
            query = query.where(SOCAlert.severity == severity)
        if status:
            query = query.where(SOCAlert.status == status)
        total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
        rows = (
            (await db.execute(query.order_by(SOCAlert.timestamp.desc()).offset((page - 1) * page_size).limit(page_size)))
            .scalars()
            .all()
        )
        return rows, total

    @staticmethod
    async def get_incident(db: AsyncSession, incident_id: UUID, user: User) -> SOCIncident:
        incident = await db.get(SOCIncident, incident_id)
        if not incident:
            raise SOCError("Incident not found")
        return incident

    @staticmethod
    async def create_incident(db: AsyncSession, user: User, data: dict) -> SOCIncident:
        alert_ids = [UUID(x) for x in data.pop("alert_ids", []) or []]
        incident = SOCIncident(
            id=uuid4(),
            case_number=f"INC-{uuid4().hex[:8].upper()}",
            title=data["title"],
            description=data["description"],
            severity=data.get("severity", "medium"),
            priority=data.get("priority", "medium"),
            created_by=user.id,
            owner_id=user.id,
        )
        incident.timeline = [{"at": datetime.now(UTC).isoformat(), "action": "incident.created", "by": str(user.id)}]
        db.add(incident)
        await db.flush()
        if alert_ids:
            alerts = (
                (await db.execute(select(SOCAlert).where(SOCAlert.id.in_(alert_ids)))).scalars().all()
            )
            for alert in alerts:
                alert.incident_id = incident.id
                alert.status = "assigned"
        await db.commit()
        await db.refresh(incident)
        return incident

    @staticmethod
    async def update_incident(db: AsyncSession, incident: SOCIncident, user: User, updates: dict) -> SOCIncident:
        transitions = {
            "investigating": {"new", "assigned"},
            "contained": {"investigating"},
            "recovering": {"contained"},
            "resolved": {"recovering", "contained"},
            "closed": {"resolved"},
        }
        if "status" in updates and updates["status"] != incident.status:
            new_status = updates["status"]
            allowed = transitions.get(new_status, set())
            if incident.status not in allowed and new_status != "new":
                raise SOCError(f"Cannot move incident from {incident.status} to {new_status}")
            if new_status == "resolved":
                incident.resolved_at = datetime.now(UTC)
            if new_status == "closed":
                incident.closed_at = datetime.now(UTC)
            if new_status == "new":
                incident.resolved_at = None
                incident.closed_at = None
        for k, v in updates.items():
            if k == "status":
                continue
            setattr(incident, k, v)
        incident.analyst_notes = [
            *incident.analyst_notes,
            {"at": datetime.now(UTC).isoformat(), "by": str(user.id),
             "change": str(updates.get("status") or ",".join(k for k in updates))},
        ]
        incident.timeline = [
            *incident.timeline,
            {"at": datetime.now(UTC).isoformat(), "action": "incident.updated",
             "status": incident.status, "by": str(user.id)},
        ]
        await db.commit()
        await db.refresh(incident)
        return incident

    @staticmethod
    async def add_note(db: AsyncSession, incident: SOCIncident, user: User, body: str) -> IncidentNote:
        note = IncidentNote(incident_id=incident.id, author_id=user.id, body=body)
        db.add(note)
        incident.analyst_notes = [
            *incident.analyst_notes,
            {"at": datetime.now(UTC).isoformat(), "by": str(user.id), "note": body},
        ]
        await db.commit()
        await db.refresh(note)
        return note
