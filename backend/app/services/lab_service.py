from __future__ import annotations

import hashlib
import ipaddress
import random
from datetime import datetime, timezone
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

    DEFAULT_SOC_TEMPLATE = {
        "slug": "soc-suspicious-login-triage",
        "title": "Suspicious Login Triage",
        "mission_type": "incident_response",
        "difficulty": "beginner",
        "estimated_minutes": 25,
        "story_context": (
            "A fictional manufacturing company reports an impossible-travel sign-in followed by suspicious "
            "mailbox activity. Triage the alert, collect evidence, contain the account, and write a short report."
        ),
        "objectives": [
            {
                "id": "obj-triage-alert",
                "title": "Triage the alert",
                "required_evidence": ["alert-impossible-travel"],
                "required_actions": [],
                "xp": 50,
            },
            {
                "id": "obj-confirm-compromise",
                "title": "Confirm account compromise",
                "required_evidence": ["auth-log-impossible-travel", "mailbox-rule-created"],
                "required_actions": [],
                "xp": 80,
            },
            {
                "id": "obj-contain-account",
                "title": "Contain the affected identity",
                "required_evidence": ["auth-log-impossible-travel"],
                "required_actions": ["disable_identity", "revoke_sessions"],
                "xp": 100,
            },
        ],
        "tools": [
            {"id": "soc-dashboard", "name": "Live Security Dashboard", "type": "dashboard"},
            {"id": "soc-siem", "name": "Simulated SIEM", "type": "siem"},
            {"id": "endpoint-console", "name": "Endpoint Monitoring", "type": "endpoint"},
            {"id": "email-security", "name": "Email Security Console", "type": "email"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "alert-impossible-travel", "title": "Impossible travel alert", "type": "alert", "required": True},
            {"key": "auth-log-impossible-travel", "title": "Authentication log pivot", "type": "log", "required": True},
            {"key": "mailbox-rule-created", "title": "Suspicious mailbox forwarding rule", "type": "email", "required": True},
            {"key": "endpoint-clean-check", "title": "Endpoint process review", "type": "endpoint", "required": False},
        ],
        "scoring_rubric": {
            "objective_points": 80,
            "evidence_points": 10,
            "report_points": 10,
            "hint_penalty": 5,
        },
        "debrief_rubric": {
            "summary": "Alert triage, identity investigation, email review, containment, and report writing.",
            "career": "SOC Tier 1 and incident response fundamentals.",
        },
        "safety_rules": {
            "fictional_only": True,
            "no_public_targets": True,
            "no_real_malware": True,
        },
    }

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
        soc = facility_by_slug["soc"]
        db.add(
            LabMissionTemplate(
                facility_id=soc.id,
                is_published=True,
                generation_rules={"company_sizes": ["small", "mid_market"], "industries": ["manufacturing", "finance", "healthcare"]},
                **cls.DEFAULT_SOC_TEMPLATE,
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
            result = await db.execute(select(LabMissionTemplate).where(LabMissionTemplate.slug == cls.DEFAULT_SOC_TEMPLATE["slug"]))
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
        rng = random.Random(seed)
        industries = template.generation_rules.get("industries") or ["manufacturing", "finance", "healthcare"]
        company_roots = ["Northstar", "Blue Harbor", "Summit Vale", "Copperline", "Aster Ridge"]
        suffixes = ["Fabrication Group", "Health Network", "Credit Union", "Logistics", "Research Labs"]
        company = {
            "name": f"{rng.choice(company_roots)} {rng.choice(suffixes)}",
            "industry": rng.choice(industries),
            "size": rng.choice(template.generation_rules.get("company_sizes") or ["small", "mid_market"]),
            "region": "fictional-us-east",
        }
        user_number = rng.randint(21, 89)
        affected_user = {
            "id": f"user-{user_number:03}",
            "display_name": rng.choice(["Maya Chen", "Jordan Ellis", "Rina Patel", "Owen Brooks"]),
            "role": rng.choice(["Finance Manager", "HR Coordinator", "Operations Lead"]),
            "department": rng.choice(["Finance", "Human Resources", "Operations"]),
            "email": f"user{user_number}@{company['name'].lower().replace(' ', '-')}.cyberverse.test",
        }
        workstation = {
            "id": "asset-001",
            "hostname": f"{company['name'].split()[0].lower()}-hq-wks-{rng.randint(10,99)}",
            "type": "windows_workstation",
            "ip_address": f"10.{rng.randint(10, 40)}.{rng.randint(0, 10)}.{rng.randint(20, 220)}",
            "location": "hq-floor-2",
            "criticality": "medium",
            "owner_user_id": affected_user["id"],
            "services": ["edr_agent", "office_suite", "vpn_client"],
            "tags": ["managed", affected_user["department"].lower().replace(" ", "-")],
        }
        alerts = [
            {
                "id": "alert-001",
                "title": "Impossible travel followed by mailbox rule creation",
                "severity": "high",
                "source": "identity",
                "asset_id": workstation["id"],
                "user_id": affected_user["id"],
                "status": "open",
            }
        ]
        logs = [
            {"id": "log-auth-001", "type": "auth", "source_ip": "198.51.100.44", "result": "success", "user_id": affected_user["id"]},
            {"id": "log-mail-001", "type": "email", "event": "mailbox_rule_created", "user_id": affected_user["id"]},
        ]
        evidence = []
        for item in template.evidence_blueprint:
            evidence.append(
                {
                    **item,
                    "id": f"ev-{item['key']}",
                    "source_tool": cls.source_tool_for_evidence(item["type"]),
                    "source_asset_id": workstation["id"],
                    "fictional": True,
                }
            )
        return {
            "company_profile": company,
            "topology": {
                "sites": ["headquarters", "branch-office", "cloud-tenant"],
                "segments": ["corp", "server", "vpn", "cloud"],
                "edges": [["vpn", "corp"], ["corp", "server"], ["server", "cloud"]],
            },
            "assets": [workstation],
            "identities": [affected_user],
            "logs": logs,
            "alerts": alerts,
            "evidence": evidence,
            "objectives": template.objectives,
            "safety_metadata": {
                "fictional_only": True,
                "uses_reserved_domains": True,
                "contains_real_malware": False,
                "targets_public_internet": False,
            },
        }

    @staticmethod
    def source_tool_for_evidence(evidence_type: str) -> str:
        return {
            "alert": "soc-dashboard",
            "log": "soc-siem",
            "email": "email-security",
            "endpoint": "endpoint-console",
        }.get(evidence_type, "case-management")

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
        return hashlib.sha256(repr(sorted(payload.items())).encode()).hexdigest()

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
            "alerts": scenario.generated_alerts,
            "evidence": scenario.generated_evidence,
            "objectives": scenario.generated_objectives,
            "tool_manifest": template.tools,
            "safety_metadata": scenario.safety_metadata,
        }

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
            evidence.collected_at = datetime.now(timezone.utc)
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
        db.add(report)
        await cls.audit(db, user.id, "lab.report.submitted", "lab_report", str(session.id), True)
        await db.commit()
        await db.refresh(report)
        return report

    @classmethod
    async def complete_session(cls, db: AsyncSession, session: LabSession, user: User) -> dict:
        completed = sum(1 for status in (session.objective_state or {}).values() if status == "completed")
        total = max(len(session.objective_state or {}), 1)
        score = round((completed / total) * 90)
        report_result = await db.execute(select(LabReport).where(LabReport.session_id == session.id))
        if report_result.scalar_one_or_none():
            score = min(100, score + 10)
        session.status = LabSessionStatus.COMPLETED.value
        session.completed_at = datetime.now(timezone.utc)
        session.score = score
        session.xp_awarded = score * 5
        session.coins_awarded = score
        await cls.audit(db, user.id, "lab.session.completed", "lab_session", str(session.id), True)
        await db.commit()
        return cls.debrief_payload(session)

    @staticmethod
    def debrief_payload(session: LabSession) -> dict:
        score = session.score or 0
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
            acknowledged_at=datetime.now(timezone.utc),
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
