from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.lab import LabEvidenceItem, LabHomeProfile, LabReport, LabScenarioInstance, LabSession
from app.schemas.base import APIResponse
from app.schemas.lab import (
    LabEventCreate,
    LabEvidenceCollect,
    LabFacilityOut,
    LabHomeAttestationCreate,
    LabHomeProfileCreate,
    LabMissionOut,
    LabNoteCreate,
    LabObjectiveSubmission,
    LabReportCreate,
    LabSessionCreate,
    LabSessionOut,
    LabWorldOut,
)
from app.services.lab_service import LabSafetyError, LabService

router = APIRouter()


@router.get("/facilities", response_model=APIResponse[list[LabFacilityOut]])
async def list_facilities(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    facilities = await LabService.list_facilities(db)
    return APIResponse(data=[LabFacilityOut.model_validate({**facility.__dict__, "unlocked": True}) for facility in facilities])


@router.get("/missions", response_model=APIResponse[list[LabMissionOut]])
async def list_lab_missions(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    facility: str | None = Query(None),
):
    missions = await LabService.list_missions(db, facility=facility)
    return APIResponse(data=[LabMissionOut.model_validate(mission.__dict__) for mission in missions])


@router.post("/sessions", response_model=APIResponse[LabSessionOut], status_code=status.HTTP_201_CREATED)
async def start_lab_session(
    payload: LabSessionCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    try:
        session = await LabService.start_session(
            db,
            user,
            payload.mission_id,
            payload.mission_slug,
            payload.facility,
            payload.difficulty,
            payload.mode,
            payload.seed,
            payload.mentor_level,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except LabSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return APIResponse(data=LabSessionOut.model_validate(session.__dict__))


@router.get("/sessions", response_model=APIResponse[list[LabSessionOut]])
async def list_lab_sessions(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LabSession).where(LabSession.user_id == user.id).order_by(LabSession.started_at.desc()))
    sessions = result.scalars().all()
    return APIResponse(data=[LabSessionOut.model_validate(session.__dict__) for session in sessions])


@router.get("/sessions/{session_id}", response_model=APIResponse[LabSessionOut])
async def get_lab_session(session_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    try:
        session = await LabService.get_session_for_user(db, session_id, user)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return APIResponse(data=LabSessionOut.model_validate(session.__dict__))


@router.get("/sessions/{session_id}/world", response_model=APIResponse[LabWorldOut])
async def get_lab_world(session_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    try:
        session = await LabService.get_session_for_user(db, session_id, user)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    world = await LabService.get_world(db, session)
    return APIResponse(data=LabWorldOut.model_validate(world))


@router.post("/sessions/{session_id}/events", response_model=APIResponse[dict], status_code=status.HTTP_201_CREATED)
async def record_lab_event(
    session_id: UUID,
    payload: LabEventCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    try:
        session = await LabService.get_session_for_user(db, session_id, user)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    event = await LabService.record_event(db, session, user, payload.model_dump())
    return APIResponse(data={"id": str(event.id), "event_type": event.event_type})


@router.get("/sessions/{session_id}/evidence", response_model=APIResponse[list[dict]])
async def list_lab_evidence(session_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    try:
        session = await LabService.get_session_for_user(db, session_id, user)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    result = await db.execute(select(LabEvidenceItem).where(LabEvidenceItem.session_id == session.id))
    evidence = result.scalars().all()
    return APIResponse(
        data=[
            {
                "id": str(item.id),
                "evidence_key": item.evidence_key,
                "title": item.title,
                "evidence_type": item.evidence_type,
                "collected_at": item.collected_at.isoformat() if item.collected_at else None,
                "is_required": item.is_required,
            }
            for item in evidence
        ]
    )


@router.post("/sessions/{session_id}/evidence", response_model=APIResponse[dict])
async def collect_lab_evidence(
    session_id: UUID,
    payload: LabEvidenceCollect,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    try:
        session = await LabService.get_session_for_user(db, session_id, user)
        evidence = await LabService.collect_evidence(db, session, user, payload.evidence_key)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return APIResponse(data={"id": str(evidence.id), "evidence_key": evidence.evidence_key, "collected": True})


@router.post("/sessions/{session_id}/objectives/{objective_id}/submit", response_model=APIResponse[dict])
async def submit_lab_objective(
    session_id: UUID,
    objective_id: str,
    payload: LabObjectiveSubmission,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    try:
        session = await LabService.get_session_for_user(db, session_id, user)
        result = await LabService.submit_objective(db, session, user, objective_id, payload.model_dump())
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return APIResponse(data=result)


@router.get("/sessions/{session_id}/timeline", response_model=APIResponse[list[dict]])
async def get_lab_timeline(session_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    session = await LabService.get_session_for_user(db, session_id, user)
    world = await LabService.get_world(db, session)
    return APIResponse(data=world["alerts"] + world["evidence"])


@router.post("/sessions/{session_id}/notes", response_model=APIResponse[dict], status_code=status.HTTP_201_CREATED)
async def add_lab_note(
    session_id: UUID,
    payload: LabNoteCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    try:
        session = await LabService.get_session_for_user(db, session_id, user)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    note = await LabService.add_note(db, session, user, payload.model_dump())
    return APIResponse(data={"id": str(note.id), "body": note.body})


@router.post("/sessions/{session_id}/report", response_model=APIResponse[dict], status_code=status.HTTP_201_CREATED)
async def submit_lab_report(
    session_id: UUID,
    payload: LabReportCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    try:
        session = await LabService.get_session_for_user(db, session_id, user)
        report = await LabService.submit_report(db, session, user, payload.model_dump())
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return APIResponse(data={"id": str(report.id), "submitted_at": report.submitted_at.isoformat()})


@router.post("/sessions/{session_id}/complete", response_model=APIResponse[dict])
async def complete_lab_session(session_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    try:
        session = await LabService.get_session_for_user(db, session_id, user)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return APIResponse(data=await LabService.complete_session(db, session, user))


@router.get("/sessions/{session_id}/debrief", response_model=APIResponse[dict])
async def get_lab_debrief(session_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    try:
        session = await LabService.get_session_for_user(db, session_id, user)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return APIResponse(data=LabService.debrief_payload(session))


@router.post("/sessions/{session_id}/mentor/explain", response_model=APIResponse[dict])
async def mentor_explain(session_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    await LabService.get_session_for_user(db, session_id, user)
    return APIResponse(
        data={
            "answer": "Work from the alert to the identity, then pivot through logs, mailbox activity, endpoint state, containment, and report quality.",
            "safety": "This guidance applies only to the current fictional CyberVerse lab session.",
        }
    )


@router.post("/sessions/{session_id}/mentor/hint", response_model=APIResponse[dict])
async def mentor_hint(session_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    await LabService.get_session_for_user(db, session_id, user)
    return APIResponse(data={"hint": "Check whether the suspicious sign-in was followed by mailbox rule creation or session reuse."})


@router.get("/home-labs", response_model=APIResponse[list[dict]])
async def list_home_labs(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LabHomeProfile).where(LabHomeProfile.user_id == user.id))
    profiles = result.scalars().all()
    return APIResponse(data=[{"id": str(profile.id), "name": profile.name, "lab_type": profile.lab_type, "status": profile.status, "read_only": profile.read_only} for profile in profiles])


@router.post("/home-labs/attestations", response_model=APIResponse[dict], status_code=status.HTTP_201_CREATED)
async def create_home_lab_attestation(
    payload: LabHomeAttestationCreate,
    request: Request,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    try:
        attestation = await LabService.create_attestation(
            db,
            user,
            payload.acknowledged,
            payload.attestation_text,
            request.client.host if request.client else None,
            request.headers.get("user-agent"),
        )
    except LabSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return APIResponse(data={"id": str(attestation.id), "acknowledged": attestation.acknowledged})


@router.post("/home-labs", response_model=APIResponse[dict], status_code=status.HTTP_201_CREATED)
async def create_home_lab_profile(
    payload: LabHomeProfileCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    try:
        profile = await LabService.create_home_profile(db, user, payload.model_dump())
    except LabSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return APIResponse(data={"id": str(profile.id), "name": profile.name, "status": profile.status, "read_only": profile.read_only})
