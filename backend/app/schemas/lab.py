from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class LabFacilityOut(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str
    facility_type: str
    min_level: int
    ue5_map_name: str | None = None
    unlocked: bool = True


class LabMissionOut(BaseModel):
    id: UUID
    facility_id: UUID
    slug: str
    title: str
    mission_type: str
    difficulty: str
    estimated_minutes: int
    story_context: str
    objectives: list[dict[str, Any]]
    tools: list[dict[str, Any]]


class LabSessionCreate(BaseModel):
    mission_id: UUID | None = None
    mission_slug: str | None = None
    facility: str = "soc"
    difficulty: str = "beginner"
    mode: str = "solo"
    seed: str | None = None
    mentor_level: str = "guided"


class LabSessionOut(BaseModel):
    id: UUID
    status: str
    mode: str
    mentor_level: str
    current_facility_slug: str
    mission_slug: str | None = None
    difficulty: str = "beginner"
    score: int | None = None
    xp_awarded: int
    coins_awarded: int
    started_at: datetime
    completed_at: datetime | None = None


class LabWorldOut(BaseModel):
    session_id: UUID
    scenario_seed: str
    facility: str
    company: dict[str, Any]
    topology: dict[str, Any]
    assets: list[dict[str, Any]]
    identities: list[dict[str, Any]]
    alerts: list[dict[str, Any]]
    logs: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]]
    objectives: list[dict[str, Any]]
    tool_manifest: list[dict[str, Any]]
    safety_metadata: dict[str, Any]


class LabEventCreate(BaseModel):
    event_type: str = Field(min_length=3, max_length=100)
    client_time: datetime | None = None
    tool_id: str | None = None
    target_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class LabObjectiveSubmission(BaseModel):
    answer_type: str = "structured_action"
    actions: list[dict[str, Any]] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    notes: str | None = None


class LabEvidenceCollect(BaseModel):
    evidence_key: str
    note: str | None = None


class LabNoteCreate(BaseModel):
    title: str | None = None
    body: str = Field(min_length=1)
    linked_evidence_ids: list[str] = Field(default_factory=list)
    linked_target_id: str | None = None


class LabReportCreate(BaseModel):
    executive_summary: str = Field(min_length=10)
    technical_findings: str = Field(min_length=10)
    containment_actions: str | None = None
    remediation_plan: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class LabHomeAttestationCreate(BaseModel):
    acknowledged: bool
    attestation_text: str = Field(min_length=20)


class LabAnalysisOut(BaseModel):
    generated_with: str
    analyst: str
    company: str | None = None
    facility: str | None = None
    overview: str
    confidence: int
    coverage: dict[str, Any]
    predominant_phase: str
    kill_chain: list[dict[str, Any]]
    timeline: list[dict[str, Any]]
    recommendations: list[str]
    entities: dict[str, Any]
    safety_metadata: dict[str, Any]


class LabHomeProfileCreate(BaseModel):
    attestation_id: UUID
    name: str = Field(min_length=2, max_length=120)
    lab_type: str
    scope: dict[str, Any]
    read_only: bool = True
    expires_at: datetime | None = None
