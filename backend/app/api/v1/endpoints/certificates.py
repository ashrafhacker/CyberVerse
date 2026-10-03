from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.course import Course
from app.schemas.base import APIResponse
from app.services.certificate_service import CertificateService

router = APIRouter()


def _serialize(cert, template, course_name: str | None = None) -> dict:
    return {
        "id": str(cert.id),
        "template_slug": template.slug,
        "template_name": template.name,
        "template_description": template.description,
        "source_type": cert.source_type,
        "source_id": cert.source_id,
        "course_name": course_name,
        "full_name": cert.full_name,
        "verification_code": cert.verification_code,
        "status": cert.status.value if hasattr(cert.status, "value") else cert.status,
        "pdf_url": cert.pdf_url,
        "issued_at": cert.issued_at.isoformat() if cert.issued_at else None,
        "expires_at": cert.expires_at.isoformat() if cert.expires_at else None,
    }


@router.get("/", response_model=APIResponse[list], summary="List my certificates")
async def list_my_certificates(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    rows = await CertificateService.list_user_certificates(db, user.id)
    course_ids = [UUID(row.source_id) for row, _ in rows if row.source_id]
    courses: dict[str, str] = {}
    if course_ids:
        result = await db.execute(select(Course.id, Course.name).where(Course.id.in_(course_ids)))
        courses = {str(cid): name for cid, name in result.all()}

    return APIResponse[list](
        data=[
            _serialize(cert, template, courses.get(str(cert.source_id)))
            for cert, template in rows
        ]
    )


@router.get("/verify/{verification_code}", response_model=APIResponse[dict], summary="Verify a certificate")
async def verify_certificate(
    verification_code: str,
    db: AsyncSession = Depends(get_db),
):
    cert = await CertificateService.verify_code(db, verification_code)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")

    from app.models.certificate import CertificateTemplate

    template_result = await db.execute(
        select(CertificateTemplate).where(CertificateTemplate.id == cert.template_id)
    )
    template = template_result.scalar_one_or_none()

    course_name = None
    if cert.source_id:
        course_result = await db.execute(
            select(Course.name).where(Course.id == UUID(cert.source_id))
        )
        course_name = course_result.scalar_one_or_none()

    return APIResponse[dict](
        data=_serialize(
            cert,
            template,
            course_name,
        )
    )


@router.get("/{certificate_id}", response_model=APIResponse[dict], summary="Get one of my certificates")
async def get_my_certificate(
    certificate_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    cert = await CertificateService.get_user_certificate(db, user.id, certificate_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")

    from app.models.certificate import CertificateTemplate

    template_result = await db.execute(
        select(CertificateTemplate).where(CertificateTemplate.id == cert.template_id)
    )
    template = template_result.scalar_one_or_none()

    course_name = None
    if cert.source_id:
        course_result = await db.execute(
            select(Course.name).where(Course.id == UUID(cert.source_id))
        )
        course_name = course_result.scalar_one_or_none()

    return APIResponse[dict](
        data=_serialize(cert, template, course_name)
    )
