"""
Incident report generator for CyberVerse Labs.

Produces a professional, structured incident report (HTML, with optional PDF)
from a lab session's report + Neo Analysis payload. All content is derived from
the student's own fictional lab session; no third-party data is fetched.

Sections follow the spec: Executive Summary, Incident Overview, Affected
Assets, Timeline, Indicators, Attack Techniques (kill chain), Root Cause,
Evidence, Impact, Containment, Remediation, Lessons Learned.
"""

from __future__ import annotations

import html
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab import LabEvidenceItem, LabReport, LabScenarioInstance, LabSession


class ReportBuilder:
    @staticmethod
    def _h(value, fallback: str = "Not provided") -> str:
        return html.escape(str(value)) if value else fallback

    @staticmethod
    async def build(
        db: AsyncSession, session: LabSession, report: LabReport | None, user_id: UUID | None = None
    ) -> dict:
        scenario = await db.get(LabScenarioInstance, session.scenario_id)
        neo = (session.extra_data or {}).get("neo_analysis") or {}
        if not neo:
            # Lazy-generate a deterministic analysis if none cached.
            try:
                from app.models.user import User
                from app.services.lab_service import LabService

                lookup = report.user_id if report else user_id
                user = await db.get(User, lookup) if lookup else None
                if user is None:
                    user = User(id=lookup, username="analyst", email="analyst@cyberverse.local")
                neo = await LabService.analyze_session(db, session, user) or {}
            except Exception:  # noqa: BLE001
                neo = {}

        evidence_result = await db.execute(
            select(LabEvidenceItem).where(LabEvidenceItem.session_id == session.id)
        )
        evidence_rows = evidence_result.scalars().all()
        collected = [e for e in evidence_rows if e.collected_at]
        evidence_list = [
            {
                "title": e.title,
                "type": e.evidence_type,
                "collected": bool(e.collected_at),
                "source_tool": e.source_tool,
            }
            for e in collected
        ]

        entities = neo.get("entities") or {}
        kill_chain = neo.get("kill_chain") or []
        timeline = neo.get("timeline") or []

        return {
            "report_id": str(report.id) if report else None,
            "generated_at": datetime.now(UTC).isoformat(),
            "analyst": "Neo",
            "session": {
                "id": str(session.id),
                "facility": session.current_facility_slug,
                "status": session.status,
                "score": session.score,
                "difficulty": (session.extra_data or {}).get("difficulty", "beginner"),
            },
            "company": (scenario.company_profile if scenario else {}) or {},
            "executive_summary": (
                ReportBuilder._h(report.executive_summary, "No executive summary was recorded.")
                if report else ReportBuilder._h(neo.get("overview"))
            ),
            "overview": ReportBuilder._h(neo.get("overview")),
            "technical_findings": (
                ReportBuilder._h(report.technical_findings)
                if report else "Findings were derived from the Neo Analysis correlation."
            ),
            "containment_actions": ReportBuilder._h(
                report.containment_actions if report else None,
                "Containment actions were not recorded.",
            ),
            "remediation_plan": ReportBuilder._h(
                report.remediation_plan if report else None,
                "See recommended remediation steps below.",
            ),
            "timeline": timeline,
            "kill_chain": kill_chain,
            "indicators": [
                {
                    "title": e.get("title"),
                    "phase": e.get("phase"),
                    "count": e.get("event_count"),
                }
                for e in kill_chain
            ],
            "recommendations": neo.get("recommendations") or [],
            "evidence": evidence_list,
            "entities": {
                "assets": entities.get("assets", []),
                "identities": entities.get("identities", []),
            },
            "coverage": neo.get("coverage"),
            "confidence": neo.get("confidence"),
            "safety_metadata": neo.get("safety_metadata"),
        }

    @staticmethod
    def render_html(data: dict) -> str:
        def li(items) -> str:
            return "".join(f"<li>{ReportBuilder._h(i)}</li>" for i in items) if items else "<li>None</li>"

        def tables_rows(rows, cols) -> str:
            if not rows:
                return "<tr><td>None</td></tr>"
            return "".join(
                "<tr>" + "".join(f"<td>{ReportBuilder._h(r.get(c) or r.get('title') or '')}</td>" for c in cols) + "</tr>"
                for r in rows
            )

        timeline_rows = "".join(
            f"<tr><td>{ReportBuilder._h(t.get('timestamp') or '-')}</td>"
            f"<td>{ReportBuilder._h(t.get('kind'))}</td>"
            f"<td>{ReportBuilder._h(t.get('phase'))}</td>"
            f"<td>{ReportBuilder._h(t.get('title'))}</td>"
            f"<td>{ReportBuilder._h(t.get('severity'))}</td></tr>"
            for t in data.get("timeline", [])
        ) or "<tr><td colspan='5'>No timeline events.</td></tr>"

        kill_rows = "".join(
            f"<tr><td>{ReportBuilder._h(k.get('label'))}</td>"
            f"<td>{ReportBuilder._h(k.get('summary'))}</td>"
            f"<td>{k.get('event_count', 0)}</td></tr>"
            for k in data.get("kill_chain", [])
        ) or "<tr><td colspan='3'>No kill-chain phases mapped.</td></tr>"

        evidence_rows = "".join(
            f"<tr><td>{ReportBuilder._h(e.get('title'))}</td>"
            f"<td>{ReportBuilder._h(e.get('type'))}</td>"
            f"<td>{ReportBuilder._h(e.get('source_tool'))}</td>"
            f"<td>{'Yes' if e.get('collected') else 'No'}</td></tr>"
            for e in data.get("evidence", [])
        ) or "<tr><td colspan='4'>No evidence collected.</td></tr>"

        return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>CyberVerse Incident Report — {ReportBuilder._h(data.get('company', {}).get('name', 'N/A'))}</title>
<style>
 body {{ font-family: Arial, Helvetica, sans-serif; color: #1a1a1a; margin: 2em; line-height: 1.5; }}
 h1 {{ border-bottom: 3px solid #0f766e; padding-bottom: .3em; }}
 h2 {{ color: #0f766e; margin-top: 1.2em; border-bottom: 1px solid #ccc; }}
 table {{ border-collapse: collapse; width: 100%; margin: .5em 0; }}
 th, td {{ border: 1px solid #ccc; padding: .4em .6em; text-align: left; font-size: .9em; }}
 th {{ background: #f0fdfa; }}
 .meta {{ color: #555; font-size: .85em; }}
 .muted {{ color: #666; }}
</style></head><body>
<h1>CyberVerse Incident Report</h1>
<div class="meta">Generated {ReportBuilder._h(data.get('generated_at'))} · Analyst: {ReportBuilder._h(data.get('analyst'))} · Report ID: {ReportBuilder._h(data.get('report_id'))}</div>
<div class="meta">Company: {ReportBuilder._h(data.get('company', {}).get('name', 'N/A'))} · Facility: {ReportBuilder._h(data.get('session', {}).get('facility'))} · Score: {ReportBuilder._h(data.get('session', {}).get('score'))}</div>

<h2>1. Executive Summary</h2>
<p>{ReportBuilder._h(data.get('executive_summary'), 'No summary provided.')}</p>

<h2>2. Incident Overview</h2>
<p>{ReportBuilder._h(data.get('overview'), 'No overview available.')}</p>
<p class="muted">Confidence: {data.get('confidence', 'n/a')}% · Evidence coverage: {data.get('coverage') or {}}</p>

<h2>3. Technical Findings</h2>
<p>{ReportBuilder._h(data.get('technical_findings'))}</p>

<h2>4. Attack Techniques (Kill Chain)</h2>
<table><tr><th>Phase</th><th>Summary</th><th>Events</th></tr>{kill_rows}</table>

<h2>5. Timeline</h2>
<table><tr><th>Timestamp</th><th>Kind</th><th>Phase</th><th>Event</th><th>Severity</th></tr>{timeline_rows}</table>

<h2>6. Indicators</h2>
<table><tr><th>Phase</th><th>Indicator</th><th>Count</th></tr>{tables_rows(data.get('indicators', []), ['phase', 'title', 'count'])}</table>

<h2>7. Evidence</h2>
<table><tr><th>Title</th><th>Type</th><th>Source Tool</th><th>Collected</th></tr>{evidence_rows}</table>

<h2>8. Affected Assets</h2>
<table><tr><th>Hostname</th><th>Type</th><th>Criticality</th></tr>{tables_rows(data.get('entities', {}).get('assets', []), ['hostname', 'type', 'criticality'])}</table>

<h2>9. Containment</h2>
<p>{ReportBuilder._h(data.get('containment_actions'))}</p>

<h2>10. Remediation</h2>
<ul>{li(data.get('recommendations') or [ReportBuilder._h(data.get('remediation_plan'))])}</ul>

<h2>11. Lessons Learned</h2>
<ul>{li([f"Investigation mapped {len(data.get('kill_chain', []))} kill-chain phases.", f"Coverage: {data.get('coverage') or {}}."])}</ul>

<p class="muted">Simulation data only — this report describes a fictional CyberVerse lab scenario.</p>
</body></html>"""

    @staticmethod
    async def to_pdf(data: dict) -> bytes | None:
        """Return PDF bytes if a PDF renderer is available, else None."""
        try:
            import weasyprint  # type: ignore

            return weasyprint.HTML(string=ReportBuilder.render_html(data)).write_pdf()
        except Exception:  # noqa: BLE001
            return None


class ReportService:
    @staticmethod
    async def get_session_report(db: AsyncSession, session: LabSession) -> LabReport | None:
        result = await db.execute(select(LabReport).where(LabReport.session_id == session.id))
        return result.scalar_one_or_none()

    @staticmethod
    async def build_for_session(db: AsyncSession, session: LabSession, user_id: UUID) -> dict:
        report = await ReportService.get_session_report(db, session)
        return await ReportBuilder.build(db, session, report)
