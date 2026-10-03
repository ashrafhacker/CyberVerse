from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, FlexibleArray


class CVE(Base):
    __tablename__ = "cves"
    __table_args__ = (
        UniqueConstraint("cve_id", name="uq_cves_cve_id"),
        Index("ix_cves_severity", "severity"),
        Index("ix_cves_published_date", "published_date"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    cve_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    cvss_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    cvss_vector: Mapped[str | None] = mapped_column(String(300), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    cwe_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    cwe_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    attack_vector: Mapped[str | None] = mapped_column(String(40), nullable=True)
    complexity: Mapped[str | None] = mapped_column(String(40), nullable=True)
    affected_products: Mapped[list] = mapped_column(FlexibleArray(str), default=list, nullable=False)
    references: Mapped[list] = mapped_column(FlexibleArray(str), default=list, nullable=False)
    mitigations: Mapped[list] = mapped_column(FlexibleArray(str), default=list, nullable=False)
    published_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    source: Mapped[str] = mapped_column(String(120), default="NVD/CISA", nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), default="high", nullable=False)

    techniques: Mapped[list["AttackTechnique"]] = relationship(
        secondary="cve_attack_techniques", back_populates="cves"
    )


class AttackTechnique(Base):
    __tablename__ = "attack_techniques"
    __table_args__ = (
        UniqueConstraint("technique_id", name="uq_attack_techniques_id"),
        Index("ix_attack_techniques_tactic", "tactic"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    technique_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    tactic: Mapped[str] = mapped_column(String(120), nullable=False)
    platform: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    mitigation: Mapped[str | None] = mapped_column(Text, nullable=True)
    detection: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    data_sources: Mapped[list] = mapped_column(FlexibleArray(str), default=list, nullable=False)

    cves: Mapped[list["CVE"]] = relationship(
        secondary="cve_attack_techniques", back_populates="techniques"
    )


class CVEAttackTechnique(Base):
    __tablename__ = "cve_attack_techniques"
    __table_args__ = (Index("ix_cve_attack_techniques_cve", "cve_id"),)

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    cve_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("cves.id", ondelete="CASCADE"), nullable=False
    )
    technique_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("attack_techniques.id", ondelete="CASCADE"), nullable=False
    )


class ThreatIndicator(Base):
    __tablename__ = "threat_indicators"
    __table_args__ = (
        UniqueConstraint("indicator_value", "indicator_type", name="uq_threat_indicators"),
        Index("ix_threat_indicators_type", "indicator_type"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    indicator_type: Mapped[str] = mapped_column(String(40), nullable=False)
    indicator_value: Mapped[str] = mapped_column(String(600), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    threat_actor: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tags: Mapped[list] = mapped_column(FlexibleArray(str), default=list, nullable=False)
    source: Mapped[str] = mapped_column(String(120), default="MISP feeding", nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
