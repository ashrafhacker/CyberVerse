import enum
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LabFacilityType(str, enum.Enum):
    SOC = "soc"
    ENTERPRISE = "enterprise"
    FORENSICS = "forensics"
    MALWARE = "malware"
    CLOUD = "cloud"
    SECURE_CODING = "secure_coding"
    NETWORK_DEFENSE = "network_defense"


class LabSessionStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class LabFacility(Base):
    __tablename__ = "lab_facilities"
    __table_args__ = (
        Index("ix_lab_facilities_slug", "slug", unique=True),
        Index("ix_lab_facilities_type", "facility_type"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    facility_type: Mapped[str] = mapped_column(String(50), nullable=False)
    min_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unlock_rules: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    ue5_map_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    extra_data: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class LabMissionTemplate(Base):
    __tablename__ = "lab_mission_templates"
    __table_args__ = (
        Index("ix_lab_mission_templates_slug", "slug", unique=True),
        Index("ix_lab_mission_templates_facility_id", "facility_id"),
        Index("ix_lab_mission_templates_type", "mission_type"),
        Index("ix_lab_mission_templates_published", "is_published"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    facility_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("lab_facilities.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    mission_type: Mapped[str] = mapped_column(String(80), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(40), default="beginner", nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    story_context: Mapped[str] = mapped_column(Text, nullable=False)
    objectives: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    tools: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    evidence_blueprint: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    generation_rules: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    scoring_rubric: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    debrief_rubric: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    safety_rules: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[PGUUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class LabScenarioInstance(Base):
    __tablename__ = "lab_scenario_instances"
    __table_args__ = (
        UniqueConstraint("template_id", "seed", name="uq_lab_scenario_template_seed"),
        Index("ix_lab_scenario_template_id", "template_id"),
        Index("ix_lab_scenario_validation_status", "validation_status"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    template_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("lab_mission_templates.id", ondelete="CASCADE"), nullable=False
    )
    seed: Mapped[str] = mapped_column(String(120), nullable=False)
    generator_version: Mapped[str] = mapped_column(String(80), nullable=False)
    company_profile: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    topology: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    generated_assets: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    generated_identities: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    generated_logs: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    generated_alerts: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    generated_evidence: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    generated_objectives: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    safety_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    validation_errors: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class LabSession(Base):
    __tablename__ = "lab_sessions"
    __table_args__ = (
        Index("ix_lab_sessions_user_id", "user_id"),
        Index("ix_lab_sessions_scenario_id", "scenario_id"),
        Index("ix_lab_sessions_status", "status"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    scenario_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("lab_scenario_instances.id", ondelete="CASCADE"), nullable=False
    )
    mode: Mapped[str] = mapped_column(String(40), default="solo", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default=LabSessionStatus.ACTIVE.value, nullable=False)
    mentor_level: Mapped[str] = mapped_column(String(40), default="guided", nullable=False)
    current_facility_slug: Mapped[str] = mapped_column(String(80), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    abandoned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    xp_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coins_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tool_state: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    objective_state: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    save_state: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    extra_data: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class LabEvent(Base):
    __tablename__ = "lab_events"
    __table_args__ = (
        Index("ix_lab_events_session_id", "session_id"),
        Index("ix_lab_events_event_type", "event_type"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("lab_sessions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[PGUUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    client_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    server_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class LabEvidenceItem(Base):
    __tablename__ = "lab_evidence_items"
    __table_args__ = (
        UniqueConstraint("session_id", "evidence_key", name="uq_lab_evidence_session_key"),
        Index("ix_lab_evidence_session_id", "session_id"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("lab_sessions.id", ondelete="CASCADE"), nullable=False
    )
    evidence_key: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_tool: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_asset_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    content: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    hash_value: Mapped[str | None] = mapped_column(String(128), nullable=True)
    custody: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    collected_by: Mapped[PGUUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class LabNote(Base):
    __tablename__ = "lab_notes"
    __table_args__ = (Index("ix_lab_notes_session_id", "session_id"),)

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("lab_sessions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    linked_evidence_ids: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    linked_target_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class LabReport(Base):
    __tablename__ = "lab_reports"

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("lab_sessions.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    user_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    technical_findings: Mapped[str] = mapped_column(Text, nullable=False)
    containment_actions: Mapped[str | None] = mapped_column(Text, nullable=True)
    remediation_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_ids: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    mentor_feedback: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    instructor_feedback: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    grade: Mapped[str | None] = mapped_column(String(20), nullable=True)


class LabHomeAttestation(Base):
    __tablename__ = "lab_home_attestations"
    __table_args__ = (Index("ix_lab_home_attestations_user_id", "user_id"),)

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    attestation_text: Mapped[str] = mapped_column(Text, nullable=False)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class LabHomeProfile(Base):
    __tablename__ = "lab_home_profiles"
    __table_args__ = (Index("ix_lab_home_profiles_user_id", "user_id"),)

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    attestation_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("lab_home_attestations.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    lab_type: Mapped[str] = mapped_column(String(80), nullable=False)
    scope: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="inactive", nullable=False)
    read_only: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class LabAuditLog(Base):
    __tablename__ = "lab_audit_logs"
    __table_args__ = (
        Index("ix_lab_audit_logs_user_id", "user_id"),
        Index("ix_lab_audit_logs_action", "action"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[PGUUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    session_id: Mapped[PGUUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("lab_sessions.id", ondelete="SET NULL"), nullable=True
    )
    home_profile_id: Mapped[PGUUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("lab_home_profiles.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    allowed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
