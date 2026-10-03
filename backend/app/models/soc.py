from datetime import UTC, datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, FlexibleArray


class SOCAlert(Base):
    __tablename__ = "soc_alerts"
    __table_args__ = (
        Index("ix_soc_alerts_severity", "severity"),
        Index("ix_soc_alerts_status", "status"),
        Index("ix_soc_alerts_timestamp", "timestamp"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="low", nullable=False)
    confidence: Mapped[float] = mapped_column(Integer, default=50, nullable=False)
    asset: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="new", nullable=False)
    mitre_technique_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    event_details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    timeline: Mapped[list] = mapped_column(ARRAY(JSONB), default=list, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    assigned_to: Mapped[PGUUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    incident_id: Mapped[PGUUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("soc_incidents.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    incident: Mapped[Optional["SOCIncident"]] = relationship(back_populates="alerts")


class SOCIncident(Base):
    __tablename__ = "soc_incidents"
    __table_args__ = (
        Index("ix_soc_incidents_status", "status"),
        Index("ix_soc_incidents_severity", "severity"),
        Index("ix_soc_incidents_opened_at", "opened_at"),
    )

    STATUSES = ("new", "investigating", "contained", "recovering", "resolved", "closed")

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    case_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="new", nullable=False)
    mitre_mapping: Mapped[list] = mapped_column(FlexibleArray(str), default=list, nullable=False)
    affected_assets: Mapped[list] = mapped_column(FlexibleArray(str), default=list, nullable=False)
    evidence_ids: Mapped[list] = mapped_column(FlexibleArray(str), default=list, nullable=False)
    analyst_notes: Mapped[list] = mapped_column(ARRAY(JSONB), default=list, nullable=False)
    timeline: Mapped[list] = mapped_column(ARRAY(JSONB), default=list, nullable=False)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    containment_actions: Mapped[list] = mapped_column(FlexibleArray(str), default=list, nullable=False)
    remediation_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[PGUUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    created_by: Mapped[PGUUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    alerts: Mapped[list["SOCAlert"]] = relationship(back_populates="incident")


class IncidentNote(Base):
    __tablename__ = "incident_notes"

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    incident_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("soc_incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[PGUUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
