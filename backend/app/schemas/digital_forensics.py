from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

CASE_STATUSES = "^(open|investigating|contained|closed)$"
CASE_SEVERITIES = "^(low|medium|high|critical)$"
EVIDENCE_STATUSES = "^(pending|verified|compromised)$"
EVIDENCE_CATEGORIES = "^(disk_image|memory_dump|log_file|network_capture|document|mobile|other)$"


class ForensicCaseCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=10000)
    severity: str = Field(default="medium", pattern=CASE_SEVERITIES)


class ForensicCaseOut(BaseModel):
    id: UUID
    case_number: str
    title: str
    description: str
    severity: str
    status: str
    opened_at: datetime
    closed_at: datetime | None = None
    evidence_count: int = 0


class ForensicEvidenceCreate(BaseModel):
    case_id: UUID
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(default="other", pattern=EVIDENCE_CATEGORIES)
    hash_sha256: str | None = Field(default=None, max_length=64, pattern="^[0-9a-fA-F]*$")
    size_bytes: int | None = Field(default=None, ge=0)
    source_host: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=4000)


class ForensicEvidenceOut(BaseModel):
    id: UUID
    case_id: UUID
    name: str
    category: str
    hash_sha256: str | None = None
    size_bytes: int | None = None
    source_host: str | None = None
    status: str
    notes: str | None = None
    collected_by: UUID | None = None


class EvidenceStatusUpdate(BaseModel):
    status: str = Field(pattern=EVIDENCE_STATUSES)


class TimelineEntryCreate(BaseModel):
    action: str = Field(min_length=1, max_length=80)
    actor: str = Field(min_length=1, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)
