from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class IncidentNoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class IncidentNoteOut(BaseModel):
    id: UUID
    author_id: UUID | None = None
    body: str
    created_at: datetime


class SOCAlertOut(BaseModel):
    id: UUID
    title: str
    description: str
    severity: str
    confidence: int
    asset: str | None = None
    source: str | None = None
    status: str
    mitre_technique_id: str | None = None
    timestamp: datetime


class SOCIncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10)
    severity: str = "medium"
    priority: str = "medium"
    alert_ids: list[UUID] = Field(default_factory=list)


class SOCIncidentUpdate(BaseModel):
    status: str | None = Field(
        default=None, pattern="^(new|investigating|contained|recovering|resolved|closed)$"
    )
    severity: str | None = None
    priority: str | None = None
    description: str | None = None
    mitre_mapping: list[str] | None = None
    affected_assets: list[str] | None = None
    root_cause: str | None = None
    containment_actions: list[str] | None = None
    remediation_plan: str | None = None


class SOCIncidentOut(BaseModel):
    id: UUID
    case_number: str
    title: str
    description: str
    severity: str
    priority: str
    status: str
    mitre_mapping: list[str]
    affected_assets: list[str]
    root_cause: str | None = None
    containment_actions: list[str]
    remediation_plan: str | None = None
    opened_at: datetime
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    updated_at: datetime
    analyst_notes: list[dict] = Field(default_factory=list)
    timeline: list[dict] = Field(default_factory=list)
    alert_count: int = 0
