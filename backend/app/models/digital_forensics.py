"""
Digital Forensics models for investigation case management.

Stores only cryptographic hashes and chain-of-custody metadata.
Raw evidence payloads never leave the client; the API accepts only
the metadata needed for audit trails and timeline reconstruction.
"""

from datetime import UTC, datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ForensicCase(Base):
    __tablename__ = "forensic_cases"
    __table_args__ = (
        Index("ix_forensic_cases_status", "status"),
        Index("ix_forensic_cases_owner_id", "owner_id"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    case_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    owner_id: Mapped[PGUUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    created_by: Mapped[PGUUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    chain_of_custody: Mapped[list] = mapped_column(
        MutableList.as_mutable(JSONB), default=list, nullable=False
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    evidence_items: Mapped[list["ForensicEvidence"]] = relationship(
        back_populates="case", cascade="all, delete-orphan", lazy="selectin"
    )


class ForensicEvidence(Base):
    __tablename__ = "forensic_evidence"
    __table_args__ = (
        Index("ix_forensic_evidence_case_id", "case_id"),
        Index("ix_forensic_evidence_status", "status"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("forensic_cases.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    hash_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source_host: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    collected_by: Mapped[PGUUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    chain_of_custody: Mapped[list] = mapped_column(
        MutableList.as_mutable(JSONB), default=list, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    case: Mapped[Optional["ForensicCase"]] = relationship(back_populates="evidence_items")
