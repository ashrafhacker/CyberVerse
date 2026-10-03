from __future__ import annotations

import hashlib
import ipaddress
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab import (
    LabAuditLog,
    LabEvent,
    LabEvidenceItem,
    LabFacility,
    LabHomeAttestation,
    LabHomeProfile,
    LabMissionTemplate,
    LabNote,
    LabReport,
    LabScenarioInstance,
    LabSession,
    LabSessionStatus,
)
from app.models.user import User
from app.services.lab_missions import ALL_MISSIONS
from app.services.lab_scenario_gen import generate_realistic_scenario


class LabSafetyError(ValueError):
    pass


class LabService:
    GENERATOR_VERSION = "labs-generator-v1"

    FACILITIES = [
        ("soc", "Security Operations Center", "Triage alerts, investigate incidents, collect evidence, and manage cases.", "soc", "LVL_SOC"),
        ("enterprise-network", "Enterprise Network Lab", "Defend a fictional enterprise with offices, servers, cloud, identity, and network devices.", "enterprise", "LVL_EnterpriseNetwork"),
        ("digital-forensics", "Digital Forensics Lab", "Analyze synthetic disk, memory, browser, email, mobile, and log evidence.", "forensics", "LVL_DigitalForensics"),
        ("malware-analysis", "Malware Analysis Lab", "Analyze harmless training samples through static traits and simulated behavior replay.", "malware", "LVL_MalwareAnalysis"),
        ("cloud-security", "Cloud Security Lab", "Review fictional IAM, storage, compute, Kubernetes, logging, secrets, and network controls.", "cloud", "LVL_CloudSecurity"),
        ("secure-coding", "Secure Coding Lab", "Fix vulnerable demo code in Python, JavaScript, Java, C#, and C++.", "secure_coding", "LVL_SecureCoding"),
        ("network-defense", "Network Defense Lab", "Perform asset discovery, hardening, detection, incident response, and recovery planning.", "network_defense", "LVL_NetworkDefense"),
    ]

    DEFAULT_SLUG = "soc-suspicious-login-triage"

    @classmethod
    async def ensure_default_content(cls, db: AsyncSession) -> None:
        result = await db.execute(select(LabFacility).where(LabFacility.slug == "soc"))
        if result.scalar_one_or_none():
            return

        facility_by_slug: dict[str, LabFacility] = {}
        for slug, name, description, facility_type, map_name in cls.FACILITIES:
            facility = LabFacility(
                slug=slug,
                name=name,
                description=description,
                facility_type=facility_type,
                ue5_map_name=map_name,
                unlock_rules={},
                extra_data={"built_in": True},
            )
            db.add(facility)
            facility_by_slug[slug] = facility

        await db.flush()
        for facility_slug, missions in ALL_MISSIONS.items():
            facility = facility_by_slug.get(facility_slug)
            if not facility:
                continue
            for template_data in missions:
                db.add(
                    LabMissionTemplate(
                        facility_id=facility.id,
                        is_published=True,
                        **template_data,
                    )
                )
        await db.commit()

    @classmethod
    async def list_facilities(cls, db: AsyncSession) -> list[LabFacility]:
        await cls.ensure_default_content(db)
        result = await db.execute(select(LabFacility).order_by(LabFacility.min_level, LabFacility.name))
        return list(result.scalars().all())

    @classmethod
    async def list_missions(cls, db: AsyncSession, facility: str | None = None) -> list[LabMissionTemplate]:
        await cls.ensure_default_content(db)
        stmt = select(LabMissionTemplate).where(LabMissionTemplate.is_published.is_(True))
        if facility:
            facility_result = await db.execute(select(LabFacility).where(LabFacility.slug == facility))
            lab_facility = facility_result.scalar_one_or_none()
            if lab_facility:
                stmt = stmt.where(LabMissionTemplate.facility_id == lab_facility.id)
        result = await db.execute(stmt.order_by(LabMissionTemplate.difficulty, LabMissionTemplate.title))
        return list(result.scalars().all())

    @classmethod
    async def get_template(cls, db: AsyncSession, mission_id: UUID | None, mission_slug: str | None) -> LabMissionTemplate:
        await cls.ensure_default_content(db)
        if mission_id:
            result = await db.execute(select(LabMissionTemplate).where(LabMissionTemplate.id == mission_id))
        elif mission_slug:
            result = await db.execute(select(LabMissionTemplate).where(LabMissionTemplate.slug == mission_slug))
        else:
            result = await db.execute(select(LabMissionTemplate).where(LabMissionTemplate.slug == cls.DEFAULT_SLUG))
        template = result.scalar_one_or_none()
        if not template or not template.is_published:
            raise LookupError("Lab mission not found")
        return template

    @classmethod
    async def start_session(
        cls,
        db: AsyncSession,
        user: User,
        mission_id: UUID | None,
        mission_slug: str | None,
        facility: str,
        difficulty: str,
        mode: str,
        seed: str | None,
        mentor_level: str,
    ) -> LabSession:
        template = await cls.get_template(db, mission_id, mission_slug)
        scenario_seed = seed or cls.make_seed(user.id, template.slug, difficulty)
        scenario = await cls.get_or_create_scenario(db, template, scenario_seed)
        if scenario.validation_status != "valid":
            raise LabSafetyError("Generated scenario failed safety validation")

        facility_result = await db.execute(select(LabFacility).where(LabFacility.id == template.facility_id))
        lab_facility = facility_result.scalar_one()
        session = LabSession(
            user_id=user.id,
            scenario_id=scenario.id,
            mode=mode,
            mentor_level=mentor_level,
            current_facility_slug=facility or lab_facility.slug,
            objective_state={objective["id"]: "not_started" for objective in scenario.generated_objectives},
            tool_state={tool["id"]: {"opened": False} for tool in template.tools},
            save_state={},
            extra_data={"difficulty": difficulty},
        )
        db.add(session)
        await db.flush()

        for evidence in scenario.generated_evidence:
            db.add(
                LabEvidenceItem(
                    session_id=session.id,
                    evidence_key=evidence["key"],
                    title=evidence["title"],
                    evidence_type=evidence["type"],
                    source_tool=evidence.get("source_tool"),
                    source_asset_id=evidence.get("source_asset_id"),
                    content=evidence,
                    hash_value=cls.hash_payload(evidence),
                    is_required=evidence.get("required", False),
                )
            )

        await cls.audit(db, user.id, "lab.session.started", "lab_session", str(session.id), True)
        await db.commit()
        await db.refresh(session)
        return session

    @classmethod
    def make_seed(cls, user_id: UUID, slug: str, difficulty: str) -> str:
        digest = hashlib.sha256(f"{user_id}:{slug}:{difficulty}:{uuid4()}".encode()).hexdigest()[:8].upper()
        return f"cv-{slug[:12]}-{digest}"

    @classmethod
    async def get_or_create_scenario(
        cls, db: AsyncSession, template: LabMissionTemplate, seed: str
    ) -> LabScenarioInstance:
        result = await db.execute(
            select(LabScenarioInstance).where(
                LabScenarioInstance.template_id == template.id,
                LabScenarioInstance.seed == seed,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        data = cls.generate_scenario(template, seed)
        errors = cls.validate_scenario(data)
        scenario = LabScenarioInstance(
            template_id=template.id,
            seed=seed,
            generator_version=cls.GENERATOR_VERSION,
            company_profile=data["company_profile"],
            topology=data["topology"],
            generated_assets=data["assets"],
            generated_identities=data["identities"],
            generated_logs=data["logs"],
            generated_alerts=data["alerts"],
            generated_evidence=data["evidence"],
            generated_objectives=data["objectives"],
            safety_metadata=data["safety_metadata"],
            validation_status="invalid" if errors else "valid",
            validation_errors=errors,
        )
        db.add(scenario)
        await db.flush()
        return scenario

    @classmethod
    def generate_scenario(cls, template: LabMissionTemplate, seed: str) -> dict:
        """Generate a realistic, fictional scenario using the facility-aware generator."""
        template_data = {
            "objectives": template.objectives,
            "evidence_blueprint": template.evidence_blueprint,
            "generation_rules": template.generation_rules or {},
        }
        return generate_realistic_scenario(template_data, seed)

    @classmethod
    def validate_scenario(cls, scenario: dict) -> list[str]:
        errors: list[str] = []
        safety = scenario.get("safety_metadata", {})
        if not safety.get("fictional_only"):
            errors.append("Scenario must be fictional only.")
        if safety.get("contains_real_malware"):
            errors.append("Real malware is not allowed.")
        if safety.get("targets_public_internet"):
            errors.append("Public internet targeting is not allowed.")
        for asset in scenario.get("assets", []):
            ip_value = asset.get("ip_address")
            if ip_value and not cls.is_allowed_training_ip(ip_value):
                errors.append(f"Asset {asset.get('id')} uses disallowed IP {ip_value}.")
        for identity in scenario.get("identities", []):
            email = identity.get("email", "")
            if email and not email.endswith(".cyberverse.test"):
                errors.append(f"Identity {identity.get('id')} uses non-training email domain.")
        return errors

    @staticmethod
    def is_allowed_training_ip(ip_value: str) -> bool:
        ip = ipaddress.ip_address(ip_value)
        allowed = [
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("172.16.0.0/12"),
            ipaddress.ip_network("192.168.0.0/16"),
            ipaddress.ip_network("192.0.2.0/24"),
            ipaddress.ip_network("198.51.100.0/24"),
            ipaddress.ip_network("203.0.113.0/24"),
        ]
        return any(ip in network for network in allowed)

    @staticmethod
    def hash_payload(payload: dict) -> str:
        """
        Canonical, order-independent content hash for forensic evidence integrity.

        Uses a stable sort on keys so that identical logical evidence always hashes
        to the same value regardless of insertion order or nested dict ordering.
        """
        import json

        def _canonical(obj):
            if isinstance(obj, dict):
                return {k: _canonical(v) for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))}
            if isinstance(obj, (list, tuple)):
                return [_canonical(v) for v in obj]
            return obj

        canonical = json.dumps(
            _canonical(payload), sort_keys=True, separators=(",", ":"), default=str
        )
        return hashlib.sha256(canonical.encode()).hexdigest()

    @classmethod
    async def get_session_for_user(cls, db: AsyncSession, session_id: UUID, user: User) -> LabSession:
        result = await db.execute(select(LabSession).where(LabSession.id == session_id, LabSession.user_id == user.id))
        session = result.scalar_one_or_none()
        if not session:
            raise LookupError("Lab session not found")
        return session

    @classmethod
    async def get_world(cls, db: AsyncSession, session: LabSession) -> dict:
        scenario = await db.get(LabScenarioInstance, session.scenario_id)
        template = await db.get(LabMissionTemplate, scenario.template_id)
        return {
            "session_id": session.id,
            "scenario_seed": scenario.seed,
            "facility": session.current_facility_slug,
            "company": scenario.company_profile,
            "topology": scenario.topology,
            "assets": scenario.generated_assets,
            "identities": scenario.generated_identities,
            "logs": scenario.generated_logs,
            "alerts": scenario.generated_alerts,
            "evidence": scenario.generated_evidence,
            "objectives": scenario.generated_objectives,
            "tool_manifest": template.tools,
            "safety_metadata": scenario.safety_metadata,
        }

    @classmethod
    async def analyze_session(cls, db: AsyncSession, session: LabSession, user: User) -> dict:
        """
        Run the deterministic Neo Analysis correlation over a lab session.

        Correlates the scenario's logs/alerts/evidence with the player's
        collected evidence and recorded events into a narrative analyst view.
        The result is cached on the session's ``extra_data`` and returned.
        """
        scenario = await db.get(LabScenarioInstance, session.scenario_id)
        if not scenario:
            raise LookupError("Lab scenario not found")

        # Collected evidence keys
        evidence_result = await db.execute(
            select(LabEvidenceItem).where(
                LabEvidenceItem.session_id == session.id,
                LabEvidenceItem.collected_at.is_not(None),
            )
        )
        collected_keys = {
            item.evidence_key for item in evidence_result.scalars().all()
        }

        # Player-recorded events (tool usage / commands)
        events_result = await db.execute(
            select(LabEvent).where(LabEvent.session_id == session.id).order_by(LabEvent.server_time)
        )
        event_log = [
            {
                "event_type": e.event_type,
                "tool_id": e.tool_id,
                "target_id": e.target_id,
                "payload": e.payload,
                "server_time": e.server_time.isoformat() if e.server_time else None,
            }
            for e in events_result.scalars().all()
        ]

        from app.services.neo_analysis_service import NeoAnalysisService

        analysis = NeoAnalysisService.analyze(
            scenario={

                    "company_profile": scenario.company_profile,
                    "facility": session.current_facility_slug,
                    "assets": scenario.generated_assets,
                    "identities": scenario.generated_identities,
                    "logs": scenario.generated_logs,
                    "alerts": scenario.generated_alerts,
                    "evidence": scenario.generated_evidence

            },
            collected_keys=collected_keys,
            event_log=event_log,
            objective_state=session.objective_state,
        )

        # Cache the latest analysis on the session metadata (lightweight replay cache).
        session.extra_data = {**(session.extra_data or {}), "neo_analysis": analysis}
        await cls.audit(db, user.id, "lab.analysis.generated", "lab_session", str(session.id), True)
        await db.commit()
        return analysis

    @classmethod
    async def record_event(cls, db: AsyncSession, session: LabSession, user: User, event_data: dict) -> LabEvent:
        event = LabEvent(session_id=session.id, user_id=user.id, **event_data)
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event

    @classmethod
    async def collect_evidence(cls, db: AsyncSession, session: LabSession, user: User, evidence_key: str) -> LabEvidenceItem:
        result = await db.execute(
            select(LabEvidenceItem).where(
                LabEvidenceItem.session_id == session.id,
                LabEvidenceItem.evidence_key == evidence_key,
            )
        )
        evidence = result.scalar_one_or_none()
        if not evidence:
            raise LookupError("Evidence not found")
        if not evidence.collected_at:
            evidence.collected_by = user.id
            evidence.collected_at = datetime.now(UTC)
            evidence.custody = [{"user_id": str(user.id), "action": "collected", "at": evidence.collected_at.isoformat()}]
            await cls.audit(db, user.id, "lab.evidence.collected", "lab_evidence", str(evidence.id), True)
            await db.commit()
            await db.refresh(evidence)
        return evidence

    @classmethod
    async def submit_objective(
        cls, db: AsyncSession, session: LabSession, user: User, objective_id: str, submission: dict
    ) -> dict:
        scenario = await db.get(LabScenarioInstance, session.scenario_id)
        objective = next((item for item in scenario.generated_objectives if item["id"] == objective_id), None)
        if not objective:
            raise LookupError("Objective not found")
        evidence_keys = set(submission.get("evidence_ids", []))
        actions = {action.get("action") for action in submission.get("actions", [])}
        required_evidence = set(objective.get("required_evidence", []))
        required_actions = set(objective.get("required_actions", []))
        passed = required_evidence.issubset(evidence_keys) and required_actions.issubset(actions)
        session.objective_state = {**(session.objective_state or {}), objective_id: "completed" if passed else "attempted"}
        await cls.audit(db, user.id, "lab.objective.submitted", "lab_objective", objective_id, passed)
        await db.commit()
        return {
            "passed": passed,
            "objective_completed": passed,
            "missing_evidence": sorted(required_evidence - evidence_keys),
            "missing_actions": sorted(required_actions - actions),
            "xp_earned": objective.get("xp", 0) if passed else 0,
        }

    @classmethod
    async def submit_report(cls, db: AsyncSession, session: LabSession, user: User, report_data: dict) -> LabReport:
        report = LabReport(session_id=session.id, user_id=user.id, **report_data)
        try:
            analysis = await cls.analyze_session(db, session, user)
            report.mentor_feedback = {
                "analyst": "Neo",
                "generated_with": analysis.get("generated_with"),
                "overview": analysis.get("overview"),
                "confidence": analysis.get("confidence"),
                "coverage": analysis.get("coverage"),
                "predominant_phase": analysis.get("predominant_phase"),
                "recommendations": analysis.get("recommendations", []),
            }
        except Exception:
            report.mentor_feedback = {}
        db.add(report)
        await cls.audit(db, user.id, "lab.report.submitted", "lab_report", str(session.id), True)
        await db.commit()
        await db.refresh(report)
        return report

    @classmethod
    async def complete_session(cls, db: AsyncSession, session: LabSession, user: User) -> dict:
        already_completed = session.status == LabSessionStatus.COMPLETED.value
        completed = sum(1 for status in (session.objective_state or {}).values() if status == "completed")
        total = max(len(session.objective_state or {}), 1)
        score = round((completed / total) * 90)
        report_result = await db.execute(select(LabReport).where(LabReport.session_id == session.id))
        if report_result.scalar_one_or_none():
            score = min(100, score + 10)
        session.status = LabSessionStatus.COMPLETED.value
        session.completed_at = datetime.now(UTC)
        session.score = score
        session.xp_awarded = score * 5
        session.coins_awarded = score
        await cls.audit(db, user.id, "lab.session.completed", "lab_session", str(session.id), True)

        if not already_completed and score > 0:
            from app.services.progress_service import ProgressService

            progress = await ProgressService.get_or_create_player_progress(db, user.id)
            progress.labs_completed += 1
            await ProgressService.award_xp(
                db, user.id, xp=session.xp_awarded, coins=session.coins_awarded
            )

        # Generate the Neo Analysis debrief (deterministic, offline-safe) so the
        # debrief/feed includes a correlated analyst narrative.
        if not (session.extra_data or {}).get("neo_analysis"):
            try:
                await cls.analyze_session(db, session, user)
            except Exception:
                pass

        await db.commit()
        return cls.debrief_payload(session)

    @staticmethod
    def debrief_payload(session: LabSession) -> dict:
        score = session.score or 0
        neo = (session.extra_data or {}).get("neo_analysis") or {}
        return {
            "score": score,
            "grade": "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 55 else "Needs Practice",
            "xp_awarded": session.xp_awarded,
            "coins_awarded": session.coins_awarded,
            "strengths": ["Worked inside the authorized fictional lab scope.", "Used structured evidence and objective submissions."],
            "missed_items": [] if score >= 85 else ["Review the required evidence and containment actions before closing the case."],
            "learning_summary": "You practiced defensive triage, evidence handling, containment, and reporting.",
            "recommended_lessons": ["identity-security-basics", "incident-response-fundamentals"],
            "career_feedback": "This maps to SOC analyst and incident response workflows.",
            "neo_analysis": {
                "overview": neo.get("overview"),
                "confidence": neo.get("confidence"),
                "coverage": neo.get("coverage"),
                "predominant_phase": neo.get("predominant_phase"),
                "timeline_count": len(neo.get("timeline") or []),
                "kill_chain_phases": [
                    {"label": ks.get("label"), "event_count": ks.get("event_count")}
                    for ks in (neo.get("kill_chain") or [])
                ],
            } if neo else None,
        }

    @classmethod
    async def add_note(cls, db: AsyncSession, session: LabSession, user: User, note_data: dict) -> LabNote:
        note = LabNote(session_id=session.id, user_id=user.id, **note_data)
        db.add(note)
        await db.commit()
        await db.refresh(note)
        return note

    @classmethod
    async def create_attestation(
        cls, db: AsyncSession, user: User, acknowledged: bool, text: str, ip_address: str | None, user_agent: str | None
    ) -> LabHomeAttestation:
        if not acknowledged:
            raise LabSafetyError("Home lab authorization must be acknowledged.")
        attestation = LabHomeAttestation(
            user_id=user.id,
            acknowledged=True,
            acknowledged_at=datetime.now(UTC),
            attestation_text=text,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(attestation)
        await cls.audit(db, user.id, "lab.home.attested", "lab_home_attestation", None, True)
        await db.commit()
        await db.refresh(attestation)
        return attestation

    @classmethod
    async def create_home_profile(cls, db: AsyncSession, user: User, data: dict) -> LabHomeProfile:
        attestation = await db.get(LabHomeAttestation, data["attestation_id"])
        if not attestation or attestation.user_id != user.id or not attestation.acknowledged:
            raise LabSafetyError("A valid ownership or authorization attestation is required.")
        cls.validate_home_scope(data["scope"])
        profile = LabHomeProfile(user_id=user.id, status="inactive", **data)
        db.add(profile)
        await cls.audit(db, user.id, "lab.home.profile.created", "lab_home_profile", None, True)
        await db.commit()
        await db.refresh(profile)
        return profile

    @classmethod
    def validate_home_scope(cls, scope: dict) -> None:
        cidrs = scope.get("cidrs") or []
        if not cidrs:
            raise LabSafetyError("Home lab scope must include at least one CIDR.")
        for cidr in cidrs:
            network = ipaddress.ip_network(cidr, strict=False)
            if not (network.is_private or network.is_loopback):
                raise LabSafetyError("Home lab scope must use private or local networks only.")

    @staticmethod
    async def audit(
        db: AsyncSession,
        user_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: str | None,
        allowed: bool,
        reason: str | None = None,
    ) -> None:
        db.add(
            LabAuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                allowed=allowed,
                reason=reason,
                extra_data={},
            )
        )
