
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_roles
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.base import APIResponse, PaginatedResponse
from app.schemas.threat_intel import (
    AttackTechniqueOut,
    CVEDetail,
    CVESummary,
    ThreatIndicatorOut,
    ThreatIntelCreate,
)
from app.services.threat_intel_service import ThreatIntelError, ThreatIntelService, _cve_dict

router = APIRouter()

MANAGER_ROLES = {UserRole.MODERATOR, UserRole.ADMINISTRATOR, UserRole.DEVELOPER, UserRole.SUPER_ADMIN}


@router.get("/cves", response_model=APIResponse[PaginatedResponse], summary="Search CVEs")
async def search_cves(
    _: CurrentUser,
    db: AsyncSession = Depends(get_db),
    search: str = Query(None),
    severity: str = Query(None),
    cwe_id: str = Query(None),
    technique_id: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
):
    cve_ids, total = await ThreatIntelService.search_cves(
        db, search, severity, cwe_id, technique_id, page, page_size
    )
    data = PaginatedResponse.create(cve_ids, total, page, page_size)
    return APIResponse[PaginatedResponse](data=data)


@router.get("/cves/{cve_id}", response_model=APIResponse[CVEDetail], summary="Get CVE detail")
async def get_cve(cve_id: str, _: CurrentUser, db: AsyncSession = Depends(get_db)):
    try:
        cve = await ThreatIntelService.get_cve(db, cve_id)
    except ThreatIntelError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return APIResponse[CVEDetail](data=CVEDetail.model_validate(_cve_dict(cve)))


@router.get("/techniques", response_model=APIResponse[list[AttackTechniqueOut]], summary="List MITRE ATT&CK techniques")
async def list_techniques(_: CurrentUser, tactic: str = Query(None), db: AsyncSession = Depends(get_db)):
    items = await ThreatIntelService.list_techniques(db, tactic)
    return APIResponse[list[AttackTechniqueOut]](
        data=[
            AttackTechniqueOut.model_validate(
                {
                    "technique_id": t.technique_id,
                    "name": t.name,
                    "tactic": t.tactic,
                    "platform": t.platform,
                    "description": t.description,
                    "mitigation": t.mitigation,
                    "url": t.url,
                }
            )
            for t in items
        ]
    )


@router.get("/indicators", response_model=APIResponse[PaginatedResponse], summary="List threat indicators")
async def list_indicators(
    _: CurrentUser,
    db: AsyncSession = Depends(get_db),
    indicator_type: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    rows, total = await ThreatIntelService.list_indicators(db, indicator_type, page, page_size)
    data = PaginatedResponse.create(
        [
            ThreatIndicatorOut.model_validate(
                {
                    "id": i.id,
                    "indicator_type": i.indicator_type,
                    "indicator_value": i.indicator_value,
                    "description": i.description,
                    "threat_actor": i.threat_actor,
                    "tags": i.tags,
                    "source": i.source,
                    "confidence": i.confidence,
                    "created_at": i.created_at,
                }
            )
            for i in rows
        ],
        total,
        page,
        page_size,
    )
    return APIResponse[PaginatedResponse](data=data)


@router.post("/cves", response_model=APIResponse[CVESummary], status_code=201, summary="Add a CVE (curator/admin)")
async def create_cve(
    payload: ThreatIntelCreate,
    _: User = Depends(require_roles(MANAGER_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    try:
        cve = await ThreatIntelService.create_cve(db, payload.model_dump())
    except ThreatIntelError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return APIResponse[CVESummary](
        data=CVESummary.model_validate(
            {
                "cve_id": cve.cve_id,
                "description": cve.description,
                "severity": cve.severity,
                "cvss_score": cve.cvss_score,
                "cwe_id": cve.cwe_id,
                "attack_vector": cve.attack_vector,
                "published_date": cve.published_date,
                "source": cve.source,
            }
        )
    )
