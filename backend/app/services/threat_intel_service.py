"""
Threat-intelligence service: CVE, MITRE ATT&CK techniques, and indicators.

All CVE/MITRE data in the database originates from official public sources
(NVD, CISA, MITRE). This service provides read/query access plus privileged
curation endpoints; it does not scrape arbitrary external hosts at runtime.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.threat_intel import CVE, AttackTechnique, ThreatIndicator


class ThreatIntelError(ValueError):
    pass


def _cve_dict(cve: CVE) -> dict:
    return {
        "id": cve.id,
        "cve_id": cve.cve_id,
        "description": cve.description,
        "severity": cve.severity,
        "cvss_score": cve.cvss_score,
        "cvss_vector": cve.cvss_vector,
        "cwe_id": cve.cwe_id,
        "cwe_name": cve.cwe_name,
        "attack_vector": cve.attack_vector,
        "complexity": cve.complexity,
        "affected_products": cve.affected_products or [],
        "references": cve.references or [],
        "mitigations": cve.mitigations or [],
        "published_date": cve.published_date,
        "source": cve.source,
        "confidence": cve.confidence,
        "techniques": [t.technique_id for t in cve.techniques] if cve.techniques else [],
    }


class ThreatIntelService:
    @staticmethod
    async def search_cves(
        db: AsyncSession,
        search: str | None = None,
        severity: str | None = None,
        cwe_id: str | None = None,
        technique_id: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ):
        query = select(CVE)
        if search:
            like = f"%{search}%"
            query = query.where(CVE.cve_id.ilike(like) | CVE.description.ilike(like))
        if severity:
            query = query.where(CVE.severity == severity)
        if cwe_id:
            query = query.where(CVE.cwe_id == cwe_id)
        total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
        query = query.order_by(CVE.published_date.desc().nullslast()).offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(query)).scalars().all()
        return [c.cve_id for c in rows], total

    @staticmethod
    async def get_cve(db: AsyncSession, cve_id: str) -> CVE:
        result = await db.execute(select(CVE).where(CVE.cve_id == cve_id))
        cve = result.scalar_one_or_none()
        if not cve:
            raise ThreatIntelError("CVE not found")
        await db.refresh(cve, attribute_names=["techniques"])
        return cve

    @staticmethod
    async def list_techniques(db: AsyncSession, tactic: str | None = None) -> list[AttackTechnique]:
        query = select(AttackTechnique)
        if tactic:
            query = query.where(AttackTechnique.tactic == tactic)
        return (await db.execute(query.order_by(AttackTechnique.tactic, AttackTechnique.technique_id))).scalars().all()

    @staticmethod
    async def list_indicators(
        db: AsyncSession, indicator_type: str | None = None, page: int = 1, page_size: int = 20
    ):
        query = select(ThreatIndicator)
        if indicator_type:
            query = query.where(ThreatIndicator.indicator_type == indicator_type)
        total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
        rows = (
            (await db.execute(query.order_by(ThreatIndicator.created_at.desc()).offset((page - 1) * page_size).limit(page_size)))
            .scalars()
            .all()
        )
        return rows, total

    @staticmethod
    async def create_cve(db: AsyncSession, data: dict) -> CVE:
        existing = await db.execute(select(CVE).where(CVE.cve_id == data["cve_id"]))
        if existing.scalar_one_or_none():
            raise ThreatIntelError("CVE already exists")
        technique_ids = data.pop("technique_ids", []) or []
        cve = CVE(**data)
        db.add(cve)
        await db.flush()
        if technique_ids:
            techniques = (
                (await db.execute(select(AttackTechnique).where(AttackTechnique.technique_id.in_(technique_ids))))
                .scalars()
                .all()
            )
            cve.techniques = list(techniques)
        await db.commit()
        await db.refresh(cve)
        return cve

    @staticmethod
    async def upsert_technique(db: AsyncSession, technique_id: str, data: dict) -> AttackTechnique:
        result = await db.execute(select(AttackTechnique).where(AttackTechnique.technique_id == technique_id))
        tech = result.scalar_one_or_none()
        if tech:
            for k, v in data.items():
                setattr(tech, k, v)
            await db.commit()
            return tech
        tech = AttackTechnique(technique_id=technique_id, **data)
        db.add(tech)
        await db.commit()
        await db.refresh(tech)
        return tech
