"""Digital Forensics API endpoints for case and evidence management."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.schemas.base import APIResponse, PaginatedResponse
from app.schemas.digital_forensics import (
    EvidenceStatusUpdate,
    ForensicCaseCreate,
    ForensicEvidenceCreate,
    TimelineEntryCreate,
)
from app.services.digital_forensics_service import (
    DigitalForensicsError,
    DigitalForensicsService,
    _case_dict,
    _evidence_dict,
)

router = APIRouter()


@router.get("/cases", response_model=APIResponse[PaginatedResponse], summary="List forensic cases")
async def list_cases(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(None),
    severity: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    rows, total = await DigitalForensicsService.list_cases(
        db, user.id, status=status, severity=severity, search=search, page=page, page_size=page_size
    )
    data = PaginatedResponse.create([_case_dict(c) for c in rows], total, page, page_size)
    return APIResponse[PaginatedResponse](data=data)


@router.post("/cases", response_model=APIResponse[dict], status_code=201, summary="Create forensic case")
async def create_case(
    payload: ForensicCaseCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    case = await DigitalForensicsService.create_case(
        db,
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        owner_id=user.id,
        created_by=user.id,
    )
    return APIResponse[dict](data=_case_dict(case))


@router.get("/cases/{case_id}", response_model=APIResponse[dict], summary="Get forensic case")
async def get_case(
    case_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    case = await DigitalForensicsService.get_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return APIResponse[dict](data=_case_dict(case))


@router.get("/cases/{case_id}/evidence", response_model=APIResponse[list[dict]], summary="List evidence for case")
async def list_evidence_by_case(
    case_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(None),
):
    evidence = await DigitalForensicsService.list_evidence_by_case(db, case_id, status=status)
    return APIResponse[list[dict]](data=[_evidence_dict(ev) for ev in evidence])


@router.post("/evidence", response_model=APIResponse[dict], status_code=201, summary="Create evidence")
async def create_evidence(
    payload: ForensicEvidenceCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    try:
        evidence = await DigitalForensicsService.create_evidence(
            db,
            case_id=payload.case_id,
            name=payload.name,
            category=payload.category,
            hash_sha256=payload.hash_sha256,
            size_bytes=payload.size_bytes,
            source_host=payload.source_host,
            collected_by=user.id,
            notes=payload.notes,
        )
    except DigitalForensicsError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return APIResponse[dict](data=_evidence_dict(evidence))


@router.patch("/evidence/{evidence_id}/status", response_model=APIResponse[dict], summary="Update evidence status")
async def update_evidence_status(
    evidence_id: UUID,
    payload: EvidenceStatusUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    try:
        evidence = await DigitalForensicsService.update_evidence_status(
            db, evidence_id=evidence_id, status=payload.status
        )
    except DigitalForensicsError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return APIResponse[dict](data=_evidence_dict(evidence))


@router.post("/evidence/{evidence_id}/timeline", response_model=APIResponse[dict], summary="Add timeline entry")
async def add_timeline_entry(
    evidence_id: UUID,
    payload: TimelineEntryCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    try:
        entry = await DigitalForensicsService.add_timeline_entry(
            db,
            evidence_id=evidence_id,
            action=payload.action,
            actor=payload.actor,
            notes=payload.notes,
        )
    except DigitalForensicsError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return APIResponse[dict](data=entry)


@router.get("/cases/{case_id}/summary", response_model=APIResponse[dict], summary="Get case summary")
async def get_case_summary(
    case_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    try:
        summary = await DigitalForensicsService.get_case_summary(db, case_id=case_id)
    except DigitalForensicsError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return APIResponse[dict](data=summary)


@router.patch("/cases/{case_id}/close", response_model=APIResponse[dict], summary="Close forensic case")
async def close_case(
    case_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    try:
        case = await DigitalForensicsService.close_case(db, case_id=case_id)
    except DigitalForensicsError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return APIResponse[dict](data=_case_dict(case))
