from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CVESummary(BaseModel):
    cve_id: str
    description: str
    severity: str
    cvss_score: float | None = None
    cwe_id: str | None = None
    attack_vector: str | None = None
    published_date: datetime | None = None
    source: str = "NVD/CISA"


class CVEDetail(CVESummary):
    id: UUID
    cvss_vector: str | None = None
    cwe_name: str | None = None
    complexity: str | None = None
    affected_products: list[str]
    references: list[str]
    mitigations: list[str]
    confidence: str
    techniques: list[str] = Field(default_factory=list)


class AttackTechniqueOut(BaseModel):
    technique_id: str
    name: str
    tactic: str
    platform: str | None = None
    description: str
    mitigation: str | None = None
    url: str | None = None


class ThreatIndicatorOut(BaseModel):
    id: UUID
    indicator_type: str
    indicator_value: str
    description: str | None = None
    threat_actor: str | None = None
    tags: list[str]
    source: str
    confidence: str
    created_at: datetime


class ThreatIntelCreate(BaseModel):
    cve_id: str = Field(pattern=r"CVE-\d{4}-\d{4,7}", description="e.g. CVE-2023-1234")
    description: str = Field(min_length=10)
    cvss_score: float | None = Field(default=None, ge=0, le=10)
    cvss_vector: str | None = None
    severity: str = "unknown"
    cwe_id: str | None = None
    cwe_name: str | None = None
    attack_vector: str | None = None
    complexity: str | None = None
    affected_products: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    mitigations: list[str] = Field(default_factory=list)
    technique_ids: list[str] = Field(default_factory=list)
