import enum
from datetime import datetime, timezone
from typing import Optional, Dict
from uuid import uuid4

from sqlalchemy import (
    String,
    Text,
    DateTime,
    Boolean,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CertificateType(str, enum.Enum):
    COURSE = "course"
    LEARNING_PATH = "learning_path"
    MISSION = "mission"
    SKILL = "skill"
    PREMIUM = "premium"


class CertificateStatus(str, enum.Enum):
    PENDING = "pending"
    ISSUED = "issued"
    REVOKED = "revoked"
    EXPIRED = "expired"


class CertificateTemplate(Base):
    __tablename__ = "certificate_templates"
    __table_args__ = (
        Index("ix_certificate_templates_slug", "slug", unique=True),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    template_type: Mapped[CertificateType] = mapped_column(
        SQLEnum(CertificateType, native_enum=False),
        default=CertificateType.COURSE,
        nullable=False,
    )

    background_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    layout_config: Mapped[Dict] = mapped_column(JSONB, default=dict, nullable=False)

    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    metadata: Mapped[Dict] = mapped_column(JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    courses: Mapped[list] = relationship("Course", back_populates="certificate_template")  # noqa: F821
    certificates: Mapped[list] = relationship("Certificate", back_populates="template")


class Certificate(Base):
    __tablename__ = "certificates"
    __table_args__ = (
        UniqueConstraint("user_id", "template_id", "source_id", name="uq_certificate_user_template_source"),
        Index("ix_certificates_user_id", "user_id"),
        Index("ix_certificates_template_id", "template_id"),
        Index("ix_certificates_verification_code", "verification_code", unique=True),
        Index("ix_certificates_status", "status"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("certificate_templates.id", ondelete="RESTRICT"),
        nullable=False,
    )
    enrollment_id: Mapped[Optional[PGUUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("enrollments.id", ondelete="SET NULL"),
        nullable=True,
    )

    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # course, learning_path, mission
    source_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    verification_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    status: Mapped[CertificateStatus] = mapped_column(
        SQLEnum(CertificateStatus, native_enum=False),
        default=CertificateStatus.PENDING,
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    score: Mapped[Optional[int]] = mapped_column(nullable=True)
    issued_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    pdf_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    metadata: Mapped[Dict] = mapped_column(JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="certificates")  # noqa: F821
    template: Mapped["CertificateTemplate"] = relationship("CertificateTemplate", back_populates="certificates")
    enrollment: Mapped[Optional["Enrollment"]] = relationship("Enrollment", back_populates="certificate")  # noqa: F821