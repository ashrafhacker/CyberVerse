"""Certificate issuance, listing, and verification for CyberVerse."""

import secrets
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.certificate import (
    Certificate,
    CertificateStatus,
    CertificateTemplate,
    CertificateType,
)
from app.models.progress import Enrollment
from app.services.notification_service import NotificationService


class CertificateService:
    """Handles certificate templates, issuance, and verification codes."""

    DEFAULT_COURSE_TEMPLATE_SLUG = "course-completion"

    @staticmethod
    async def _get_or_create_course_template(db: AsyncSession) -> CertificateTemplate:
        result = await db.execute(
            select(CertificateTemplate).where(
                CertificateTemplate.slug == CertificateService.DEFAULT_COURSE_TEMPLATE_SLUG
            )
        )
        template = result.scalar_one_or_none()
        if template:
            return template

        template = CertificateTemplate(
            slug=CertificateService.DEFAULT_COURSE_TEMPLATE_SLUG,
            name="CyberVerse Course Completion",
            description="Awarded for completing a full CyberVerse course.",
            template_type=CertificateType.COURSE,
            is_active=True,
        )
        db.add(template)
        await db.flush()
        return template

    @staticmethod
    def _generate_code() -> str:
        return secrets.token_hex(16).upper()

    @staticmethod
    async def issue_course_certificate(
        db: AsyncSession,
        user_id: UUID,
        course,
        enrollment: Enrollment | None = None,
    ) -> Certificate | None:
        """Auto-issue a course-completion certificate (idempotent)."""
        if not course:
            return None

        template = await CertificateService._get_or_create_course_template(db)
        source_id = str(course.id)

        existing_result = await db.execute(
            select(Certificate).where(
                Certificate.user_id == user_id,
                Certificate.template_id == template.id,
                Certificate.source_id == source_id,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            if existing.status != CertificateStatus.ISSUED:
                existing.status = CertificateStatus.ISSUED
                existing.issued_at = datetime.now(UTC)
                await db.flush()
            return existing

        from app.models.user import User

        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        certificate = Certificate(
            user_id=user_id,
            template_id=template.id,
            enrollment_id=enrollment.id if enrollment else None,
            source_type="course",
            source_id=source_id,
            verification_code=CertificateService._generate_code(),
            status=CertificateStatus.ISSUED,
            full_name=user.full_name if user else "CyberVerse Student",
            issued_at=datetime.now(UTC),
        )
        db.add(certificate)
        await db.flush()

        await NotificationService.create(
            db,
            user_id,
            "Course completed — certificate earned!",
            f"You earned a CyberVerse certificate for completing {course.name}.",
            link="/certificates",
            icon="award",
            commit=False,
        )
        return certificate

    @staticmethod
    async def list_user_certificates(
        db: AsyncSession, user_id: UUID
    ) -> list[tuple[Certificate, CertificateTemplate]]:
        result = await db.execute(
            select(Certificate, CertificateTemplate)
            .join(CertificateTemplate, CertificateTemplate.id == Certificate.template_id)
            .where(
                Certificate.user_id == user_id,
                Certificate.status == CertificateStatus.ISSUED,
            )
            .order_by(Certificate.issued_at.desc())
        )
        return result.all()

    @staticmethod
    async def get_user_certificate(
        db: AsyncSession, user_id: UUID, certificate_id: UUID
    ) -> Certificate | None:
        result = await db.execute(
            select(Certificate).where(
                Certificate.id == certificate_id,
                Certificate.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def verify_code(db: AsyncSession, code: str) -> Certificate | None:
        result = await db.execute(
            select(Certificate).where(Certificate.verification_code == code.strip().upper())
        )
        return result.scalar_one_or_none()
