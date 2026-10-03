from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.lab import (
    LabEvidenceItem,
    LabHomeProfile,
    LabScenarioInstance,
    LabSession,
)
from app.schemas.base import APIResponse
from app.schemas.lab import (
    LabAnalysisOut,
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


async def _session_payload(db: AsyncSession, session: LabSession) -> dict:
    """Build the serialized session payload with mission slug and difficulty."""
    from app.models.lab import LabMissionTemplate

    payload = {**session.__dict__}
    payload["difficulty"] = (session.extra_data or {}).get("difficulty", "beginner")
    try:
        scenario = await db.get(LabScenarioInstance, session.scenario_id)
        if scenario:
            template = await db.get(LabMissionTemplate, scenario.template_id)
            payload["mission_slug"] = template.slug if template else None
    except Exception:
        payload["mission_slug"] = None
    return payload


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
    return APIResponse(data=LabSessionOut.model_validate(await _session_payload(db, session)))


@router.get("/sessions", response_model=APIResponse[list[LabSessionOut]])
async def list_lab_sessions(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LabSession).where(LabSession.user_id == user.id).order_by(LabSession.started_at.desc()))
    sessions = result.scalars().all()
    return APIResponse(
        data=[LabSessionOut.model_validate(await _session_payload(db, s)) for s in sessions]
    )


@router.get("/sessions/{session_id}", response_model=APIResponse[LabSessionOut])
async def get_lab_session(session_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    try:
        session = await LabService.get_session_for_user(db, session_id, user)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return APIResponse(data=LabSessionOut.model_validate(await _session_payload(db, session)))


@router.get("/sessions/{session_id}/world", response_model=APIResponse[LabWorldOut])
async def get_lab_world(session_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    try:
        session = await LabService.get_session_for_user(db, session_id, user)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    world = await LabService.get_world(db, session)
    return APIResponse(data=LabWorldOut.model_validate(world))


@router.get("/sessions/{session_id}/analysis", response_model=APIResponse[LabAnalysisOut])
async def get_lab_analysis(session_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Generate (or return cached) Neo Analysis narrative for the session."""
    try:
        session = await LabService.get_session_for_user(db, session_id, user)
        analysis = await LabService.analyze_session(db, session, user)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return APIResponse(data=LabAnalysisOut.model_validate(analysis))


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
    try:
        world = await LabService.get_world(db, session)
        from app.models.lab import LabEvent, LabEvidenceItem
        from app.services.neo_analysis_service import NeoAnalysisService

        evidence_result = await db.execute(
            select(LabEvidenceItem).where(
                LabEvidenceItem.session_id == session.id,
                LabEvidenceItem.collected_at.is_not(None),
            )
        )
        collected_keys = {item.evidence_key for item in evidence_result.scalars().all()}
        events_result = await db.execute(select(LabEvent).where(LabEvent.session_id == session.id))
        event_log = [
            {"event_type": e.event_type, "tool_id": e.tool_id}
            for e in events_result.scalars().all()
        ]
        analysis = NeoAnalysisService.analyze(
            scenario=world,
            collected_keys=collected_keys,
            event_log=event_log,
            objective_state=session.objective_state,
        )
        return APIResponse(
            data=analysis["timeline"] + [
                {"kind": "evidence", "key": e.get("key"), "title": e.get("title"), "phase": "containment", "timestamp": None}
                for e in world["evidence"]
            ]
        )
    except Exception:
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


@router.get("/sessions/{session_id}/reports", response_model=APIResponse[dict], summary="Generated incident report JSON")
async def get_lab_report(session_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    try:
        session = await LabService.get_session_for_user(db, session_id, user)
        from app.services.reports import ReportService

        data = await ReportService.build_for_session(db, session, user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return APIResponse[dict](data=data)


@router.get("/sessions/{session_id}/reports/export", summary="Export incident report as HTML or PDF")
async def export_lab_report(
    session_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    format: str = Query("html", pattern="^(html|pdf)$"),
):
    try:
        session = await LabService.get_session_for_user(db, session_id, user)
        from app.services.reports import ReportBuilder, ReportService

        data = await ReportService.build_for_session(db, session, user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    from fastapi.responses import HTMLResponse, Response

    if format == "html":
        return HTMLResponse(content=ReportBuilder.render_html(data))
    pdf = await ReportBuilder.to_pdf(data)
    if pdf is None:
        raise HTTPException(status_code=501, detail="PDF rendering is not available; use format=html")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report-{session_id}.pdf"'},
    )


async def _lab_context(db: AsyncSession, session) -> str:
    world = await LabService.get_world(db, session)
    company = world.get("company", {})
    alerts = world.get("alerts", [])
    objectives = world.get("objectives", [])
    objective_names = ", ".join(
        f"{o.get('id')} ({o.get('title', '')})" for o in objectives[:5]
    )
    return (
        f"You are assisting a student inside the fictional CyberVerse lab "
        f"'{session.current_facility_slug}' (mentor level: {session.mentor_level}). "
        f"Company: {company.get('name', 'N/A')}. Open alerts: "
        f"{', '.join(a.get('title', a.get('id', '')) for a in alerts[:5]) or 'none yet'}. "
        f"Objectives: {objective_names or 'not loaded'}. "
        f"Give a short, educational nudge that only references this fictional scenario."
    )


@router.post("/sessions/{session_id}/mentor/explain", response_model=APIResponse[dict])
async def mentor_explain(session_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    session = await LabService.get_session_for_user(db, session_id, user)
    try:
        from app.services.ai_service import AIService

        ai = AIService()
        context = await _lab_context(db, session)
        result = await ai.chat(
            [
                {
                    "role": "user",
                    "content": "Explain how I should approach this investigation step by step — what to check first, and why.",
                }
            ],
            context=context,
        )
        answer = result["reply"]
    except Exception:
        answer = "Work from the alert to the identity, then pivot through logs, mailbox activity, endpoint state, containment, and report quality."
    return APIResponse(
        data={
            "answer": answer,
            "safety": "This guidance applies only to the current fictional CyberVerse lab session.",
        }
    )


@router.post("/sessions/{session_id}/mentor/hint", response_model=APIResponse[dict])
async def mentor_hint(session_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    session = await LabService.get_session_for_user(db, session_id, user)
    try:
        from app.services.ai_service import AIService

        ai = AIService()
        context = await _lab_context(db, session)
        hint = await ai.generate_hint(
            f"Lab session {session.current_facility_slug}", context, hint_level=2
        )
    except Exception:
        hint = "Check whether the suspicious sign-in was followed by mailbox rule creation or session reuse."
    return APIResponse(data={"hint": hint})


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
