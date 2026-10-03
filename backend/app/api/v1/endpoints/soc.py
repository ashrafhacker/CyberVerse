from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.soc import SOCAlert, SOCIncident
from app.schemas.base import APIResponse, PaginatedResponse
from app.schemas.soc import (
    IncidentNoteCreate,
    IncidentNoteOut,
    SOCIncidentCreate,
    SOCIncidentOut,
    SOCIncidentUpdate,
)
from app.services.soc_service import SOCError, SOCService, _incident_dict

router = APIRouter()


def _alert_dict(a: SOCAlert) -> dict:
    return {
        "id": a.id,
        "title": a.title,
        "description": a.description,
        "severity": a.severity,
        "confidence": a.confidence,
        "asset": a.asset,
        "source": a.source,
        "status": a.status,
        "mitre_technique_id": a.mitre_technique_id,
        "timestamp": a.timestamp,
    }


@router.get("/alerts", response_model=APIResponse[PaginatedResponse], summary="List SOC alerts")
async def list_alerts(
    _: CurrentUser,
    db: AsyncSession = Depends(get_db),
    severity: str = Query(None),
    status: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    rows, total = await SOCService.list_alerts(db, severity, status, page, page_size)
    data = PaginatedResponse.create([_alert_dict(a) for a in rows], total, page, page_size)
    return APIResponse[PaginatedResponse](data=data)


@router.get("/incidents", response_model=APIResponse[PaginatedResponse], summary="List incidents")
async def list_incidents(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    status: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = select(SOCIncident).where(SOCIncident.owner_id == user.id)
    if status:
        query = query.where(SOCIncident.status == status)
    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = (await db.execute(query.order_by(SOCIncident.opened_at.desc()).offset((page - 1) * page_size).limit(page_size))).scalars().all()

    out = []
    for inc in rows:
        alert_count = (
            await db.scalar(select(func.count()).select_from(SOCAlert).where(SOCAlert.incident_id == inc.id))
        ) or 0
        out.append({**_incident_dict(inc), "alert_count": alert_count})
    data = PaginatedResponse.create(out, total, page, page_size)
    return APIResponse[PaginatedResponse](data=data)


@router.post("/incidents", response_model=APIResponse[SOCIncidentOut], status_code=201, summary="Create an incident from alerts")
async def create_incident(
    payload: SOCIncidentCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    try:
        incident = await SOCService.create_incident(db, user, payload.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return APIResponse[SOCIncidentOut](data=SOCIncidentOut.model_validate({**_incident_dict(incident), "alert_count": len(payload.alert_ids)}))


@router.get("/incidents/{incident_id}", response_model=APIResponse[SOCIncidentOut], summary="Get an incident")
async def get_incident(incident_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    try:
        incident = await SOCService.get_incident(db, incident_id, user)
        alert_count = (await db.scalar(select(func.count()).select_from(SOCAlert).where(SOCAlert.incident_id == incident.id))) or 0
    except SOCError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return APIResponse[SOCIncidentOut](data=SOCIncidentOut.model_validate({**_incident_dict(incident), "alert_count": alert_count}))


@router.patch("/incidents/{incident_id}", response_model=APIResponse[SOCIncidentOut], summary="Update incident lifecycle")
async def update_incident(
    incident_id: UUID,
    payload: SOCIncidentUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    try:
        incident = await SOCService.get_incident(db, incident_id, user)
        incident = await SOCService.update_incident(db, incident, user, payload.model_dump(exclude_none=True))
        alert_count = (await db.scalar(select(func.count()).select_from(SOCAlert).where(SOCAlert.incident_id == incident.id))) or 0
    except SOCError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return APIResponse[SOCIncidentOut](data=SOCIncidentOut.model_validate({**_incident_dict(incident), "alert_count": alert_count}))


@router.post("/incidents/{incident_id}/notes", response_model=APIResponse[IncidentNoteOut], status_code=201, summary="Add an analyst note")
async def add_note(
    incident_id: UUID,
    payload: IncidentNoteCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    try:
        incident = await SOCService.get_incident(db, incident_id, user)
        note = await SOCService.add_note(db, incident, user, payload.body)
    except SOCError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return APIResponse[IncidentNoteOut](
        data=IncidentNoteOut.model_validate(
            {"id": note.id, "author_id": note.author_id, "body": note.body, "created_at": note.created_at}
        )
    )
