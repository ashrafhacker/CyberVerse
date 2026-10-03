"""
Neo Analysis — deterministic incident-correlation engine for CyberVerse Labs.

Turns a generated session's raw telemetry (logs, alerts, evidence, assets,
identities) into a structured, educational analyst narrative: a kill-chain
timeline, evidence-to-phase correlations, an executive overview, and
containment/remediation recommendations.

This service is fully deterministic and offline — it never calls an external
model and never references real software, malware, or public systems. Every
log/alert/evidence item is tagged with a training-safe kill-chain phase and a
human-readable narrative that a student can triage inside the fictional lab.

Safety: all reasoning is scoped to the session's own fictional scenario.
"""

from __future__ import annotations

from typing import Any

# Kill-chain / analysis phases used for correlation. Order matters (display).
PHASES = [
    ("initial_access", "Initial Access"),
    ("reconnaissance", "Discovery & Recon"),
    ("privilege_escalation", "Privilege Escalation"),
    ("credential_access", "Credential Access"),
    ("lateral_movement", "Lateral Movement"),
    ("defense_evasion", "Defense Evasion"),
    ("persistence", "Persistence"),
    ("command_control", "Command & Control"),
    ("exfiltration", "Exfiltration / Impact"),
    ("containment", "Containment & Remediation"),
]

PHASE_ORDER = {phase: idx for idx, (phase, _) in enumerate(PHASES)}

# Adduce a phase from a telemetry type (log/alert `type` / `source`).
TYPE_TO_PHASE: dict[str, str] = {
    # generic auth / identity
    "auth": "initial_access",
    "authentication": "initial_access",
    "login": "initial_access",
    "identity": "initial_access",
    "email": "initial_access",
    "mailbox": "initial_access",
    # discovery / recon
    "scanner": "reconnaissance",
    "scan": "reconnaissance",
    "recon": "reconnaissance",
    "port_scan": "reconnaissance",
    "web_access": "reconnaissance",
    "web": "reconnaissance",
    # privilege escalation
    "privilege": "privilege_escalation",
    "sudo": "privilege_escalation",
    "iam": "privilege_escalation",
    "role": "privilege_escalation",
    "group": "privilege_escalation",
    # credential access
    "credential": "credential_access",
    "creds": "credential_access",
    "kerberos": "credential_access",
    "kerberoast": "credential_access",
    "password": "credential_access",
    "secret_scan": "credential_access",
    "secret": "credential_access",
    "hash": "credential_access",
    # lateral movement
    "lateral": "lateral_movement",
    "smb": "lateral_movement",
    "rdp": "lateral_movement",
    "wmi": "lateral_movement",
    "pass_the_hash": "lateral_movement",
    "psexec": "lateral_movement",
    "powershell": "lateral_movement",
    # defense evasion
    "evasion": "defense_evasion",
    "antivirus": "defense_evasion",
    "disable": "defense_evasion",
    "log_clearing": "defense_evasion",
    "amsi": "defense_evasion",
    # persistence
    "persistence": "persistence",
    "registry": "persistence",
    "scheduled_task": "persistence",
    "startup": "persistence",
    "service": "persistence",
    "install": "persistence",
    "dropper": "persistence",
    "malware": "persistence",
    "sandbox": "persistence",
    "detonation": "persistence",
    "filesystem": "persistence",
    "file": "persistence",
    "mft": "persistence",
    "prefetch": "persistence",
    "device": "persistence",
    "usb": "persistence",
    # command & control
    "c2": "command_control",
    "beacon": "command_control",
    "network": "command_control",
    "vpc_flow": "command_control",
    "firewall": "command_control",
    "ids": "command_control",
    "netflow": "command_control",
    # exfiltration / impact
    "exfil": "exfiltration",
    "data_exfil": "exfiltration",
    "storage": "exfiltration",
    "s3": "exfiltration",
    "impact": "exfiltration",
    "ransomware": "exfiltration",
    # cloud audit as defense observation
    "cloudtrail": "defense_evasion",
    "audit": "reconnaissance",
    "k8s_audit": "privilege_escalation",
    # secure coding / static checks
    "git": "reconnaissance",
    "sast": "defense_evasion",
    "ci": "defense_evasion",
    "code": "reconnaissance",
    # generic fallbacks
    "endpoint": "persistence",
    "process": "persistence",
    "windows_security": "initial_access",
    "switch": "lateral_movement",
    "router": "reconnaissance",
    "vlan": "lateral_movement",
    "segmentation": "defense_evasion",
    "firewall_audit": "defense_evasion",
    "ids": "command_control",
}

# Keyword hints that refine a telemetry type into a more precise phase.
KEYWORD_TO_PHASE: list[tuple[str, str]] = [
    ("beacon", "command_control"),
    ("forward", "exfiltration"),
    ("exfil", "exfiltration"),
    ("brute", "credential_access"),
    ("kerberoast", "credential_access"),
    ("hash", "credential_access"),
    ("privilege", "privilege_escalation"),
    ("escalat", "privilege_escalation"),
    ("hostpath", "privilege_escalation"),
    ("administratoraccess", "privilege_escalation"),
    ("bucket", "exfiltration"),
    ("public-read", "exfiltration"),
    ("scheduled", "persistence"),
    ("run\\", "persistence"),
    ("registry", "persistence"),
    ("dropped", "persistence"),
    ("persist", "persistence"),
    ("rule_created", "initial_access"),
]

# Narrative per phase (educational, tool-agnostic).
PHASE_NARRATIVE: dict[str, str] = {
    "initial_access": "The adversary obtained a foothold, typically via a sign-in, mailbox rule, or exposed web path.",
    "reconnaissance": "The adversary mapped the environment by scanning endpoints, network segments, or source repositories.",
    "privilege_escalation": "The adversary raised privileges beyond the initial account, e.g. attaching privileged policies or mounting host paths.",
    "credential_access": "The adversary harvested or cracked credentials, such as Kerberos tickets, hashes, or leaked keys.",
    "lateral_movement": "The adversary moved across hosts and services using legitimately-shaped remote procedures.",
    "defense_evasion": "The adversary altered, disabled, or bypassed detection and audit controls.",
    "persistence": "The adversary established a repeatable foothold via scheduled tasks, registry/startup, or dropped payloads.",
    "command_control": "The adversary maintained a channel back to external infrastructure (C2 beacons).",
    "exfiltration": "The adversary reached the impact stage: data exposure, exfiltration, or destructive actions.",
    "containment": "Recommended response phase: isolate, contain, remediate, and report the incident.",
}


def _phase_for_item(item: dict[str, Any]) -> str:
    """Best-effort phase adduction for a log/alert/evidence dict."""
    # Prefer an explicit optional phase hint if provided by the generator.
    explicit = item.get("phase")
    if explicit and explicit in PHASE_ORDER:
        return explicit

    # Broad matches beat narrow ones, so check keywords first (they carry more signal).
    text = (
        " ".join(
            str(item.get(k, "")) for k in ("title", "event", "rule", "task", "command", "signature")
        )
    ).lower()

    for keyword, phase in KEYWORD_TO_PHASE:
        if keyword in text:
            return phase

    type_value = str(item.get("type") or item.get("source") or "").lower()
    if type_value in TYPE_TO_PHASE:
        return TYPE_TO_PHASE[type_value]

    return "initial_access"


def _ts_key(item: dict[str, Any]) -> str:
    return str(item.get("timestamp") or item.get("last_run") or "")


class NeoAnalysisService:
    """Builds a structured analyst narrative for a lab scenario + session state."""

    @staticmethod
    def analyze(
        scenario: dict[str, Any],
        collected_keys: set[str],
        event_log: list[dict[str, Any]],
        objective_state: dict[str, Any] | None,
    ) -> dict[str, Any]:
        logs = scenario.get("logs") or []
        alerts = scenario.get("alerts") or []
        evidence = scenario.get("evidence") or []
        assets = scenario.get("assets") or []
        identities = scenario.get("identities") or []
        company = scenario.get("company_profile") or {}

        collected_evidence = [e for e in evidence if e.get("key") in collected_keys]
        collected_map = {e.get("key"): e for e in collected_evidence}

        # --- Timeline: merge alerts + logs, sorted by timestamp, annotated ---
        timeline: list[dict[str, Any]] = []
        for item in alerts:
            timeline.append(
                {
                    "id": item.get("id"),
                    "timestamp": _ts_key(item),
                    "kind": "alert",
                    "title": item.get("title", item.get("id")),
                    "severity": item.get("severity", "medium"),
                    "phase": _phase_for_item(item),
                    "item_type": item.get("source"),
                }
            )
        for item in logs:
            timeline.append(
                {
                    "id": item.get("id"),
                    "timestamp": _ts_key(item),
                    "kind": "log",
                    "title": item.get("event", item.get("id")),
                    "severity": "info",
                    "phase": _phase_for_item(item),
                    "item_type": item.get("type"),
                }
            )
        timeline.sort(key=lambda t: (t["timestamp"] or "", PHASE_ORDER.get(t["phase"], 99)))

        # --- Kill chain: aggregate events per phase, richest first ---
        phase_events: dict[str, list[dict[str, Any]]] = {}
        for event in timeline:
            phase_events.setdefault(event["phase"], []).append(event)
        kill_chain: list[dict[str, Any]] = []
        for phase, label in PHASES:
            events = phase_events.get(phase)
            if not events:
                continue
            alert_count = sum(1 for e in events if e["kind"] == "alert")
            critical = any(e.get("severity") in ("critical", "high") for e in events)
            kill_chain.append(
                {
                    "phase": phase,
                    "label": label,
                    "summary": PHASE_NARRATIVE.get(phase, ""),
                    "event_count": len(events),
                    "alert_count": alert_count,
                    "critical": critical,
                    "evidence": [
                        {
                            "id": ev["id"],
                            "title": ev["title"],
                            "collected": ev.get("key") in collected_keys,
                        }
                        for ev in evidence
                        if _phase_for_item(ev) == phase
                    ],
                    "events": [
                        {
                            "id": e["id"],
                            "title": e["title"],
                            "kind": e["kind"],
                            "severity": e["severity"],
                            "timestamp": e["timestamp"],
                        }
                        for e in events[:8]
                    ],
                }
            )

        # Predominant phase = the one with the most correlated telemetry.
        predominant = max(phase_events.items(), key=lambda kv: len(kv[1]))[0] if phase_events else "initial_access"

        # --- Executive overview ---
        total_evidence = len(evidence)
        collected_count = len(collected_evidence)
        coverage = (collected_count / total_evidence) if total_evidence else 0.0
        completed = sum(1 for s in (objective_state or {}).values() if s == "completed")
        total_objectives = max(len(objective_state or {}), 1)
        confidence = round(40 + coverage * 50 + (completed / total_objectives) * 10)

        overview = (
            f"Within the fictional environment for {company.get('name', 'the organization')}, "
            f"Neo identified a multi-phase incident centered on {predominant.replace('_', ' ')}. "
            f"{sum(1 for e in timeline if e['kind'] == 'alert')} alerts and "
            f"{sum(1 for e in timeline if e['kind'] == 'log')} log events were correlated. "
            f"{collected_count} of {total_evidence} evidence items were collected "
            f"({round(coverage * 100)}% coverage), yielding a confidence estimate of {confidence}%."
        )

        # --- Recommendations based on dominant phases present ---
        active_phases = {k["phase"] for k in kill_chain}
        recommendations: list[str] = []
        if "initial_access" in active_phases:
            recommendations.append("Reset the affected account's credentials and revoke any mailbox forwarding or rules.")
        if "credential_access" in active_phases or "privilege_escalation" in active_phases:
            recommendations.append("Audit privileged roles and rotate credentials; enforce MFA on administrative accounts.")
        if "lateral_movement" in active_phases:
            recommendations.append("Segment the network and restrict remote administration tooling to management zones.")
        if "persistence" in active_phases:
            recommendations.append("Review scheduled tasks, startup entries, and dropped binaries, then remove persistence.")
        if "command_control" in active_phases:
            recommendations.append("Block the observed C2 infrastructure and enable network-traffic baseline alerts.")
        if "exfiltration" in active_phases:
            recommendations.append("Revoke public access on exposed storage, review audit logs, and contain affected hosts.")
        if "defense_evasion" in active_phases:
            recommendations.append("Re-enable security tooling and alert on telemetry or audit-coverage gaps.")
        if not recommendations:
            recommendations.append("Produce a containment-and-remediation plan and complete the investigation report.")

        return {
            "generated_with": "neo-analysis-deterministic-v1",
            "analyst": "Neo",
            "company": company.get("name"),
            "facility": scenario.get("facility", "soc"),
            "overview": overview,
            "confidence": min(99, confidence),
            "coverage": {"collected": collected_count, "total": total_evidence, "percent": round(coverage * 100)},
            "predominant_phase": predominant,
            "kill_chain": kill_chain,
            "timeline": timeline,
            "recommendations": recommendations,
            "entities": {
                "assets": [
                    {"id": a.get("id"), "hostname": a.get("hostname"), "type": a.get("type"), "criticality": a.get("criticality")}
                    for a in assets
                ],
                "identities": [
                    {"id": i.get("id"), "display_name": i.get("display_name"), "role": i.get("role"), "email": i.get("email")}
                    for i in identities
                ],
            },
            "safety_metadata": {
                "fictional_only": True,
                "generated_from_scenario": True,
                "contains_real_malware": False,
                "targets_public_internet": False,
            },
        }


def correlate_events(scenario: dict[str, Any], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Map player-recorded lab events onto consecutive kill-chain phases.

    Returns a lightweight "analyst note" style sequence used to reflect the
    player's investigative path in the debrief.
    """
    order = []
    seen: set[str] = set()
    for event in events:
        event_type = str(event.get("event_type") or event.get("type") or "").lower()
        phase = TYPE_TO_PHASE.get(event_type, "initial_access")
        idx = PHASE_ORDER.get(phase, 0)
        key = f"{idx}:{event_type}"
        if key in seen:
            continue
        seen.add(key)
        order.append(
            {
                "phase": phase,
                "label": dict(PHASES)[phase],
                "action": event_type,
                "tool_id": event.get("tool_id"),
            }
        )
    order.sort(key=lambda o: PHASE_ORDER.get(o["phase"], 0))
    return order
