"""
Mission template definitions for CyberVerse Labs.

Each template declares objectives, tools, an evidence blueprint, scoring rubric,
safety rules, and generation rules used by ``LabService.generate_scenario`` to
build a realistic, fictional scenario instance.

All content is fictional and safety-validated (reserved IP ranges, training
email domains, no real malware, no public targeting).
"""

from __future__ import annotations

SAFETY_RULES = {
    "fictional_only": True,
    "no_public_targets": True,
    "no_real_malware": True,
    "uses_reserved_domains": True,
}


def _rubric(objective_points: int = 80, evidence_points: int = 10, report_points: int = 10, hint_penalty: int = 5):
    return {
        "objective_points": objective_points,
        "evidence_points": evidence_points,
        "report_points": report_points,
        "hint_penalty": hint_penalty,
    }


# --------------------------------------------------------------------------- #
# SOC Operations Center
# --------------------------------------------------------------------------- #
SOC_MISSIONS = [
    {
        "slug": "soc-suspicious-login-triage",
        "title": "Suspicious Login Triage",
        "mission_type": "incident_response",
        "difficulty": "beginner",
        "estimated_minutes": 25,
        "story_context": (
            "A fictional manufacturing company reports an impossible-travel sign-in followed by "
            "suspicious mailbox activity. Triage the alert, collect evidence, contain the account, "
            "and write a short report."
        ),
        "objectives": [
            {"id": "obj-triage-alert", "title": "Triage the alert", "required_evidence": ["alert-impossible-travel"], "required_actions": [], "xp": 50},
            {"id": "obj-confirm-compromise", "title": "Confirm account compromise", "required_evidence": ["auth-log-impossible-travel", "mailbox-rule-created"], "required_actions": [], "xp": 80},
            {"id": "obj-contain-account", "title": "Contain the affected identity", "required_evidence": ["auth-log-impossible-travel"], "required_actions": ["disable_identity", "revoke_sessions"], "xp": 100},
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
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "Alert triage, identity investigation, email review, containment, and report writing.", "career": "SOC Tier 1 and incident response fundamentals."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "soc", "company_sizes": ["small", "mid_market"], "industries": ["manufacturing", "finance", "healthcare"]},
    },
    {
        "slug": "soc-phishing-email-investigation",
        "title": "Phishing Email Investigation",
        "mission_type": "phishing_analysis",
        "difficulty": "beginner",
        "estimated_minutes": 30,
        "story_context": (
            "Several employees forwarded a suspicious email claiming their payroll direct deposit "
            "needs re-verification. Analyze headers, extract the credential harvesting link, and "
            "block the sender domain."
        ),
        "objectives": [
            {"id": "obj-analyze-headers", "title": "Analyze email headers", "required_evidence": ["phish-email-headers"], "required_actions": [], "xp": 50},
            {"id": "obj-extract-url", "title": "Extract credential harvesting URL", "required_evidence": ["phish-harvest-url", "phish-sender-reputation"], "required_actions": [], "xp": 70},
            {"id": "obj-identify-victims", "title": "Identify affected users", "required_evidence": ["phish-click-log"], "required_actions": [], "xp": 80},
            {"id": "obj-block-sender", "title": "Contain and block the phishing campaign", "required_evidence": ["phish-sender-reputation"], "required_actions": ["block_sender_domain", "quarantine_emails"], "xp": 100},
        ],
        "tools": [
            {"id": "soc-dashboard", "name": "Live Security Dashboard", "type": "dashboard"},
            {"id": "email-security", "name": "Email Security Console", "type": "email"},
            {"id": "soc-siem", "name": "Simulated SIEM", "type": "siem"},
            {"id": "url-analyzer", "name": "URL Sandbox Analyzer", "type": "sandbox"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "phish-email-headers", "title": "Phishing email headers", "type": "email", "required": True},
            {"key": "phish-harvest-url", "title": "Credential harvesting URL", "type": "url", "required": True},
            {"key": "phish-sender-reputation", "title": "Sender domain reputation report", "type": "intel", "required": True},
            {"key": "phish-click-log", "title": "Mailbox click activity log", "type": "log", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "Email header analysis, URL extraction, victim identification, and campaign containment.", "career": "SOC phishing analyst workflow."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "soc", "company_sizes": ["small", "mid_market"], "industries": ["finance", "healthcare", "education"]},
    },
    {
        "slug": "soc-ransomware-initial-response",
        "title": "Ransomware Initial Response",
        "mission_type": "incident_response",
        "difficulty": "intermediate",
        "estimated_minutes": 45,
        "story_context": (
            "EDR flags mass file encryption activity on a file server and a ransom note appears on "
            "shared drives. Triage the outbreak, isolate affected hosts, and preserve evidence "
            "before recovery begins."
        ),
        "objectives": [
            {"id": "obj-triage-encryption", "title": "Triage mass encryption alert", "required_evidence": ["ransom-edr-alert"], "required_actions": [], "xp": 60},
            {"id": "obj-patient-zero", "title": "Identify patient zero entry point", "required_evidence": ["ransom-initial-access-log", "ransom-phish-correlation"], "required_actions": [], "xp": 100},
            {"id": "obj-isolate-hosts", "title": "Isolate affected hosts", "required_evidence": ["ransom-edr-alert"], "required_actions": ["isolate_endpoint", "disable_identity"], "xp": 120},
            {"id": "obj-preserve-evidence", "title": "Preserve forensic evidence", "required_evidence": ["ransom-encryption-log", "ransom-process-tree"], "required_actions": [], "xp": 90},
        ],
        "tools": [
            {"id": "soc-dashboard", "name": "Live Security Dashboard", "type": "dashboard"},
            {"id": "soc-siem", "name": "Simulated SIEM", "type": "siem"},
            {"id": "endpoint-console", "name": "Endpoint Monitoring", "type": "endpoint"},
            {"id": "file-server-console", "name": "File Server Console", "type": "file"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "ransom-edr-alert", "title": "EDR mass encryption alert", "type": "alert", "required": True},
            {"key": "ransom-initial-access-log", "title": "Initial access authentication log", "type": "log", "required": True},
            {"key": "ransom-phish-correlation", "title": "Phishing correlation evidence", "type": "email", "required": True},
            {"key": "ransom-encryption-log", "title": "File server encryption log", "type": "log", "required": True},
            {"key": "ransom-process-tree", "title": "Malicious process tree", "type": "endpoint", "required": False},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "Ransomware triage, patient-zero identification, host isolation, and evidence preservation.", "career": "SOC ransomware response and IR coordination."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "soc", "company_sizes": ["mid_market", "enterprise"], "industries": ["manufacturing", "healthcare", "finance"]},
    },
    {
        "slug": "soc-insider-threat-detection",
        "title": "Insider Threat Detection",
        "mission_type": "threat_hunting",
        "difficulty": "advanced",
        "estimated_minutes": 50,
        "story_context": (
            "UEBA flags a departing engineer accessing source repositories outside business hours "
            "and staging large archives to a personal cloud share. Investigate intent, exfiltration "
            "paths, and preserve a defensible timeline."
        ),
        "objectives": [
            {"id": "obj-ueba-triage", "title": "Triage UEBA anomaly", "required_evidence": ["ueba-anomaly-alert"], "required_actions": [], "xp": 60},
            {"id": "obj-repo-access", "title": "Corroborate repository access", "required_evidence": ["repo-audit-log", "after-hours-access-log"], "required_actions": [], "xp": 90},
            {"id": "obj-exfil-path", "title": "Identify exfiltration path", "required_evidence": ["archive-creation-log", "cloud-upload-log"], "required_actions": [], "xp": 110},
            {"id": "obj-contain-insider", "title": "Contain and preserve evidence", "required_evidence": ["ueba-anomaly-alert"], "required_actions": ["revoke_sessions", "disable_identity"], "xp": 100},
        ],
        "tools": [
            {"id": "soc-dashboard", "name": "Live Security Dashboard", "type": "dashboard"},
            {"id": "soc-siem", "name": "Simulated SIEM", "type": "siem"},
            {"id": "ueba-engine", "name": "UEBA Engine", "type": "ueba"},
            {"id": "repo-audit-tool", "name": "Repository Audit Console", "type": "repo"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "ueba-anomaly-alert", "title": "UEBA behavioral anomaly", "type": "alert", "required": True},
            {"key": "repo-audit-log", "title": "Repository access audit log", "type": "log", "required": True},
            {"key": "after-hours-access-log", "title": "After-hours access log", "type": "log", "required": True},
            {"key": "archive-creation-log", "title": "Archive staging log", "type": "log", "required": True},
            {"key": "cloud-upload-log", "title": "Personal cloud upload log", "type": "log", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "Insider threat triage, access corroboration, exfiltration path identification, and containment.", "career": "Insider threat analyst and HR/legal collaboration."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "soc", "company_sizes": ["mid_market", "enterprise"], "industries": ["technology", "finance", "aerospace"]},
    },
    {
        "slug": "soc-ddos-traffic-response",
        "title": "DDoS Traffic Response",
        "mission_type": "incident_response",
        "difficulty": "intermediate",
        "estimated_minutes": 35,
        "story_context": (
            "The website faces a volumetric SYN flood with DNS amplification. Analyze NetFlow, "
            "identify amplifiers, and implement edge scrubbing and rate-limit rules."
        ),
        "objectives": [
            {"id": "obj-traffic-baseline", "title": "Establish traffic baseline and peak", "required_evidence": ["netflow-spike-chart"], "required_actions": [], "xp": 60},
            {"id": "obj-identify-vector", "title": "Identify attack vector and amplifiers", "required_evidence": ["syn-flood-pcap", "dns-amp-log"], "required_actions": [], "xp": 100},
            {"id": "obj-mitigate", "title": "Implement mitigation", "required_evidence": ["syn-flood-pcap"], "required_actions": ["enable_scrubbing", "apply_rate_limit"], "xp": 110},
        ],
        "tools": [
            {"id": "soc-dashboard", "name": "Live Security Dashboard", "type": "dashboard"},
            {"id": "soc-siem", "name": "Simulated SIEM", "type": "siem"},
            {"id": "netflow-analyzer", "name": "NetFlow Analyzer", "type": "netflow"},
            {"id": "pcap-viewer", "name": "Packet Capture Viewer", "type": "pcap"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "netflow-spike-chart", "title": "NetFlow spike visualization", "type": "netflow", "required": True},
            {"key": "syn-flood-pcap", "title": "SYN flood packet capture", "type": "pcap", "required": True},
            {"key": "dns-amp-log", "title": "DNS amplification log", "type": "log", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "DDoS traffic analysis, vector identification, and mitigation implementation.", "career": "Network defense and SOC coordination during volumetric attacks."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "soc", "company_sizes": ["mid_market", "enterprise"], "industries": ["ecommerce", "finance", "media"]},
    },
]


# --------------------------------------------------------------------------- #
# Enterprise Network Lab
# --------------------------------------------------------------------------- #
ENTERPRISE_MISSIONS = [
    {
        "slug": "ent-ad-compromise-investigation",
        "title": "Active Directory Compromise Investigation",
        "mission_type": "incident_response",
        "difficulty": "advanced",
        "estimated_minutes": 55,
        "story_context": (
            "Multiple Kerberos pre-auth failures followed by a successful AS-REQ from an unusual "
            "subnet suggest a brute-force or kerberoasting attempt against domain accounts. Trace "
            "the lateral movement, privilege escalation, and contain the compromise."
        ),
        "objectives": [
            {"id": "obj-ad-triage", "title": "Triage DC security alerts", "required_evidence": ["dc-failed-auth-log", "dc-asreq-spike"], "required_actions": [], "xp": 70},
            {"id": "obj-kerberoast", "title": "Identify kerberoasting artifacts", "required_evidence": ["kerb-tgs-log", "suspicious-spn-query"], "required_actions": [], "xp": 110},
            {"id": "obj-lateral", "title": "Trace lateral movement", "required_evidence": ["ps-remote-log", "service-account-misuse"], "required_actions": [], "xp": 110},
            {"id": "obj-contain-dc", "title": "Contain and reset compromised accounts", "required_evidence": ["kerb-tgs-log"], "required_actions": ["disable_identity", "reset_password", "revoke_tickets"], "xp": 120},
        ],
        "tools": [
            {"id": "ad-console", "name": "Active Directory Console", "type": "directory"},
            {"id": "dc-monitor", "name": "Domain Controller Monitor", "type": "monitor"},
            {"id": "soc-siem", "name": "Simulated SIEM", "type": "siem"},
            {"id": "kerb-analyzer", "name": "Kerberos Analyzer", "type": "kerberos"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "dc-failed-auth-log", "title": "DC failed authentication log", "type": "log", "required": True},
            {"key": "dc-asreq-spike", "title": "AS-REQ request spike", "type": "log", "required": True},
            {"key": "kerb-tgs-log", "title": "Suspicious TGS request log", "type": "log", "required": True},
            {"key": "suspicious-spn-query", "title": "Suspicious SPN query", "type": "log", "required": True},
            {"key": "ps-remote-log", "title": "PowerShell remoting log", "type": "log", "required": True},
            {"key": "service-account-misuse", "title": "Service account misuse log", "type": "log", "required": False},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "AD attack triage, kerberoasting detection, lateral movement tracing, and containment.", "career": "Enterprise incident response and Active Directory hardening."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "enterprise", "company_sizes": ["mid_market", "enterprise"], "industries": ["finance", "government", "healthcare"]},
    },
    {
        "slug": "ent-lateral-movement-detection",
        "title": "Lateral Movement Detection",
        "mission_type": "threat_hunting",
        "difficulty": "intermediate",
        "estimated_minutes": 40,
        "story_context": (
            "Hunt for pass-the-hash and WMI lateral movement between workstations following a "
            "credential theft. Map the movement, identify compromised hosts, and contain the spread."
        ),
        "objectives": [
            {"id": "obj-pth-hunt", "title": "Detect pass-the-hash artifacts", "required_evidence": ["pth-logon-log"], "required_actions": [], "xp": 100},
            {"id": "obj-wmi-hunt", "title": "Detect WMI lateral movement", "required_evidence": ["wmi-remote-log", "scheduled-task-log"], "required_actions": [], "xp": 90},
            {"id": "obj-host-map", "title": "Map compromised host chain", "required_evidence": ["host-chain-map"], "required_actions": [], "xp": 80},
            {"id": "obj-contain-spread", "title": "Contain the lateral spread", "required_evidence": ["pth-logon-log"], "required_actions": ["isolate_endpoint", "disable_identity"], "xp": 110},
        ],
        "tools": [
            {"id": "ad-console", "name": "Active Directory Console", "type": "directory"},
            {"id": "endpoint-console", "name": "Endpoint Monitoring", "type": "endpoint"},
            {"id": "soc-siem", "name": "Simulated SIEM", "type": "siem"},
            {"id": "hunt-console", "name": "Threat Hunt Console", "type": "hunt"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "pth-logon-log", "title": "Pass-the-hash logon log", "type": "log", "required": True},
            {"key": "wmi-remote-log", "title": "WMI remote execution log", "type": "log", "required": True},
            {"key": "scheduled-task-log", "title": "Remote scheduled task log", "type": "log", "required": True},
            {"key": "host-chain-map", "title": "Compromised host chain map", "type": "map", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "Pass-the-hash and WMI detection, host chain mapping, and containment.", "career": "Threat hunting and lateral movement analysis."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "enterprise", "company_sizes": ["mid_market", "enterprise"], "industries": ["finance", "manufacturing", "government"]},
    },
    {
        "slug": "ent-data-exfiltration-investigation",
        "title": "Data Exfiltration Investigation",
        "mission_type": "incident_response",
        "difficulty": "advanced",
        "estimated_minutes": 50,
        "story_context": (
            "Firewall logs show an internal host uploading 14GB to an unknown external endpoint over "
            "an encrypted tunnel at 2 AM. Identify the exfiltration channel, affected data, and "
            "block the destination."
        ),
        "objectives": [
            {"id": "obj-fw-triage", "title": "Triage firewall upload alert", "required_evidence": ["fw-upload-alert"], "required_actions": [], "xp": 70},
            {"id": "obj-channel", "title": "Identify exfiltration channel", "required_evidence": ["encrypted-tunnel-log", "dns-tunnel-log"], "required_actions": [], "xp": 110},
            {"id": "obj-data-scope", "title": "Determine affected data scope", "required_evidence": ["db-access-log", "file-access-log"], "required_actions": [], "xp": 100},
            {"id": "obj-block-dest", "title": "Block destination and contain host", "required_evidence": ["fw-upload-alert"], "required_actions": ["block_destination", "isolate_endpoint"], "xp": 100},
        ],
        "tools": [
            {"id": "firewall-console", "name": "Firewall Console", "type": "firewall"},
            {"id": "soc-siem", "name": "Simulated SIEM", "type": "siem"},
            {"id": "dns-analyzer", "name": "DNS Analyzer", "type": "dns"},
            {"id": "db-audit-tool", "name": "Database Audit Console", "type": "database"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "fw-upload-alert", "title": "Firewall upload alert", "type": "alert", "required": True},
            {"key": "encrypted-tunnel-log", "title": "Encrypted tunnel log", "type": "log", "required": True},
            {"key": "dns-tunnel-log", "title": "DNS tunneling log", "type": "log", "required": True},
            {"key": "db-access-log", "title": "Database access log", "type": "log", "required": True},
            {"key": "file-access-log", "title": "File access log", "type": "log", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "Exfiltration triage, channel identification, data scoping, and containment.", "career": "Incident response and data loss prevention."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "enterprise", "company_sizes": ["mid_market", "enterprise"], "industries": ["finance", "healthcare", "technology"]},
    },
    {
        "slug": "ent-dns-tunneling-detection",
        "title": "DNS Tunneling Detection",
        "mission_type": "threat_hunting",
        "difficulty": "intermediate",
        "estimated_minutes": 35,
        "story_context": (
            "DNS query volume to a single subdomain spiked with long encoded labels suggesting "
            "covert C2 or data exfiltration. Decode queries, identify the channel, and block it."
        ),
        "objectives": [
            {"id": "obj-dns-spike", "title": "Detect anomalous DNS volume", "required_evidence": ["dns-volume-spike-chart"], "required_actions": [], "xp": 70},
            {"id": "obj-decode", "title": "Decode tunneled queries", "required_evidence": ["decoded-dns-payload", "dns-tunnel-log"], "required_actions": [], "xp": 110},
            {"id": "obj-block", "title": "Block tunneling domain", "required_evidence": ["decoded-dns-payload"], "required_actions": ["block_destination", "block_sender_domain"], "xp": 90},
        ],
        "tools": [
            {"id": "dns-analyzer", "name": "DNS Analyzer", "type": "dns"},
            {"id": "soc-siem", "name": "Simulated SIEM", "type": "siem"},
            {"id": "pcap-viewer", "name": "Packet Capture Viewer", "type": "pcap"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "dns-volume-spike-chart", "title": "DNS volume spike chart", "type": "chart", "required": True},
            {"key": "decoded-dns-payload", "title": "Decoded DNS payload", "type": "log", "required": True},
            {"key": "dns-tunnel-log", "title": "DNS tunneling evidence", "type": "log", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "DNS anomaly detection, payload decoding, and domain blocking.", "career": "Network threat hunting and DNS security."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "enterprise", "company_sizes": ["small", "mid_market"], "industries": ["technology", "finance", "education"]},
    },
]


# --------------------------------------------------------------------------- #
# Digital Forensics Lab
# --------------------------------------------------------------------------- #
FORENSICS_MISSIONS = [
    {
        "slug": "df-disk-image-analysis",
        "title": "Disk Image Analysis",
        "mission_type": "forensics",
        "difficulty": "intermediate",
        "estimated_minutes": 45,
        "story_context": (
            "A compromised employee workstation disk image needs timeline reconstruction. Identify "
            "deleted files, prefetch artifacts, scheduled task persistence, and build a defensible "
            "timeline."
        ),
        "objectives": [
            {"id": "obj-filesystem", "title": "Examine filesystem and MFT", "required_evidence": ["mft-records"], "required_actions": [], "xp": 80},
            {"id": "obj-deleted", "title": "Recover deleted files", "required_evidence": ["recovered-deleted-files"], "required_actions": [], "xp": 100},
            {"id": "obj-prefetch", "title": "Analyze prefetch artifacts", "required_evidence": ["prefetch-records"], "required_actions": [], "xp": 80},
            {"id": "obj-timeline", "title": "Build super timeline", "required_evidence": ["super-timeline"], "required_actions": [], "xp": 100},
        ],
        "tools": [
            {"id": "disk-analyzer", "name": "Disk Image Analyzer", "type": "disk"},
            {"id": "mft-explorer", "name": "MFT Explorer", "type": "mft"},
            {"id": "timeline-builder", "name": "Timeline Builder", "type": "timeline"},
            {"id": "prefetch-viewer", "name": "Prefetch Viewer", "type": "prefetch"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "mft-records", "title": "MFT records", "type": "disk", "required": True},
            {"key": "recovered-deleted-files", "title": "Recovered deleted files", "type": "disk", "required": True},
            {"key": "prefetch-records", "title": "Prefetch records", "type": "disk", "required": True},
            {"key": "super-timeline", "title": "Super timeline", "type": "timeline", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "Disk forensics, file recovery, prefetch analysis, and timeline construction.", "career": "Digital forensics examiner fundamentals."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "forensics", "company_sizes": ["small", "mid_market"], "industries": ["finance", "legal", "healthcare"]},
    },
    {
        "slug": "df-memory-forensics-investigation",
        "title": "Memory Forensics Investigation",
        "mission_type": "forensics",
        "difficulty": "advanced",
        "estimated_minutes": 40,
        "story_context": (
            "A finance server memory dump shows an unparented svchost process. Use volatility-style "
            "analysis to find injected code, hidden network connections, and the malware footprint."
        ),
        "objectives": [
            {"id": "obj-process", "title": "Identify malicious process", "required_evidence": ["mem-process-list"], "required_actions": [], "xp": 90},
            {"id": "obj-injection", "title": "Detect code injection", "required_evidence": ["mem-injection-artifact"], "required_actions": [], "xp": 110},
            {"id": "obj-netconn", "title": "Find hidden network connections", "required_evidence": ["mem-netconn"], "required_actions": [], "xp": 90},
            {"id": "obj-footprint", "title": "Extract malware footprint", "required_evidence": ["mem-malware-footprint"], "required_actions": [], "xp": 100},
        ],
        "tools": [
            {"id": "memory-analyzer", "name": "Memory Analyzer", "type": "memory"},
            {"id": "process-tree", "name": "Process Tree Viewer", "type": "process"},
            {"id": "netconn-viewer", "name": "Network Connection Viewer", "type": "network"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "mem-process-list", "title": "Memory process list", "type": "memory", "required": True},
            {"key": "mem-injection-artifact", "title": "Code injection artifact", "type": "memory", "required": True},
            {"key": "mem-netconn", "title": "Hidden network connections", "type": "memory", "required": True},
            {"key": "mem-malware-footprint", "title": "Malware footprint", "type": "memory", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "Memory analysis, injection detection, hidden connections, and malware footprinting.", "career": "Memory forensics and malware reverse engineering."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "forensics", "company_sizes": ["mid_market", "enterprise"], "industries": ["finance", "government", "aerospace"]},
    },
    {
        "slug": "df-browser-artifact-analysis",
        "title": "Browser Artifact Analysis",
        "mission_type": "forensics",
        "difficulty": "beginner",
        "estimated_minutes": 25,
        "story_context": (
            "A contractor is suspected of accessing restricted resources. Analyze Chrome and Edge "
            "artifacts to extract history, cookies, downloads, and form data across browsers."
        ),
        "objectives": [
            {"id": "obj-history", "title": "Extract browsing history", "required_evidence": ["browser-history"], "required_actions": [], "xp": 70},
            {"id": "obj-cookies", "title": "Analyze cookies and sessions", "required_evidence": ["browser-cookies"], "required_actions": [], "xp": 80},
            {"id": "obj-downloads", "title": "Identify downloads", "required_evidence": ["browser-downloads"], "required_actions": [], "xp": 80},
            {"id": "obj-forms", "title": "Extract form and search data", "required_evidence": ["browser-form-data"], "required_actions": [], "xp": 70},
        ],
        "tools": [
            {"id": "browser-forensics", "name": "Browser Forensics Tool", "type": "browser"},
            {"id": "cookie-viewer", "name": "Cookie Viewer", "type": "cookie"},
            {"id": "timeline-builder", "name": "Timeline Builder", "type": "timeline"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "browser-history", "title": "Browsing history", "type": "browser", "required": True},
            {"key": "browser-cookies", "title": "Cookie store", "type": "browser", "required": True},
            {"key": "browser-downloads", "title": "Download list", "type": "browser", "required": True},
            {"key": "browser-form-data", "title": "Form data", "type": "browser", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "Browser artifact extraction and timeline correlation.", "career": "End-user forensics and insider investigations."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "forensics", "company_sizes": ["small", "mid_market"], "industries": ["legal", "finance", "education"]},
    },
    {
        "slug": "df-email-forensics",
        "title": "Email Forensics",
        "mission_type": "forensics",
        "difficulty": "intermediate",
        "estimated_minutes": 30,
        "story_context": (
            "A harassment complaint requires deep email analysis. Parse RFC-822 headers, reconstruct "
            "routing, identify spoofing, and preserve evidence with chain-of-custody."
        ),
        "objectives": [
            {"id": "obj-parse-headers", "title": "Parse RFC-822 headers", "required_evidence": ["parsed-email-headers"], "required_actions": [], "xp": 80},
            {"id": "obj-routing", "title": "Reconstruct routing path", "required_evidence": ["email-routing-map"], "required_actions": [], "xp": 90},
            {"id": "obj-spoof", "title": "Identify spoofing indicators", "required_evidence": ["spoofing-indicators"], "required_actions": [], "xp": 100},
            {"id": "obj-custody", "title": "Preserve evidence with chain-of-custody", "required_evidence": ["custody-chain"], "required_actions": [], "xp": 80},
        ],
        "tools": [
            {"id": "email-forensics", "name": "Email Forensics Tool", "type": "email"},
            {"id": "header-analyzer", "name": "Header Analyzer", "type": "header"},
            {"id": "timeline-builder", "name": "Timeline Builder", "type": "timeline"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "parsed-email-headers", "title": "Parsed email headers", "type": "email", "required": True},
            {"key": "email-routing-map", "title": "Email routing map", "type": "map", "required": True},
            {"key": "spoofing-indicators", "title": "Spoofing indicators", "type": "log", "required": True},
            {"key": "custody-chain", "title": "Chain-of-custody record", "type": "custody", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "Email header parsing, routing reconstruction, and spoofing detection.", "career": "Email forensics and legal evidence handling."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "forensics", "company_sizes": ["small", "mid_market"], "industries": ["legal", "hr", "government"]},
    },
]


# --------------------------------------------------------------------------- #
# Malware Analysis Lab
# --------------------------------------------------------------------------- #
MALWARE_MISSIONS = [
    {
        "slug": "ma-static-analysis-suspicious-binary",
        "title": "Static Analysis of Suspicious Binary",
        "mission_type": "malware_analysis",
        "difficulty": "intermediate",
        "estimated_minutes": 40,
        "story_context": (
            "A suspicious PDF attachment contains an embedded executable with obfuscated JavaScript. "
            "Perform static analysis: extract strings, examine PE headers, identify obfuscation, and "
            "generate a YARA rule."
        ),
        "objectives": [
            {"id": "obj-extract-strings", "title": "Extract embedded strings", "required_evidence": ["ma-strings-output"], "required_actions": [], "xp": 80},
            {"id": "obj-pe-headers", "title": "Examine PE headers", "required_evidence": ["ma-pe-headers"], "required_actions": [], "xp": 90},
            {"id": "obj-obfuscation", "title": "Identify obfuscation", "required_evidence": ["ma-obfuscation-report"], "required_actions": [], "xp": 100},
            {"id": "obj-yara", "title": "Generate YARA detection rule", "required_evidence": ["ma-yara-rule"], "required_actions": [], "xp": 100},
        ],
        "tools": [
            {"id": "disassembler", "name": "Static Disassembler", "type": "disasm"},
            {"id": "string-extractor", "name": "String Extractor", "type": "strings"},
            {"id": "pe-analyzer", "name": "PE Header Analyzer", "type": "pe"},
            {"id": "yara-editor", "name": "YARA Rule Editor", "type": "yara"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "ma-strings-output", "title": "Extracted strings", "type": "malware", "required": True},
            {"key": "ma-pe-headers", "title": "PE header analysis", "type": "malware", "required": True},
            {"key": "ma-obfuscation-report", "title": "Obfuscation report", "type": "malware", "required": True},
            {"key": "ma-yara-rule", "title": "YARA detection rule", "type": "yara", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "Static analysis, string extraction, PE inspection, and YARA rule creation.", "career": "Malware analyst reverse engineering fundamentals."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "malware", "company_sizes": ["small", "mid_market"], "industries": ["technology", "finance", "government"]},
    },
    {
        "slug": "ma-behavioral-analysis-c2",
        "title": "Behavioral Analysis and C2 Communication",
        "mission_type": "malware_analysis",
        "difficulty": "advanced",
        "estimated_minutes": 45,
        "story_context": (
            "Detonate a harmless training sample in an isolated sandbox. Observe filesystem changes, "
            "registry persistence, and C2 beaconing to fictional infrastructure."
        ),
        "objectives": [
            {"id": "obj-detonate", "title": "Detonate sample in sandbox", "required_evidence": ["ma-sandbox-report"], "required_actions": [], "xp": 80},
            {"id": "obj-persistence", "title": "Identify persistence mechanism", "required_evidence": ["ma-persistence-artifact"], "required_actions": [], "xp": 100},
            {"id": "obj-c2", "title": "Analyze C2 communication", "required_evidence": ["ma-c2-traffic", "ma-c2-protocol"], "required_actions": [], "xp": 110},
            {"id": "obj-iocs", "title": "Extract network and host IOCs", "required_evidence": ["ma-ioc-list"], "required_actions": [], "xp": 90},
        ],
        "tools": [
            {"id": "sandbox", "name": "Malware Sandbox", "type": "sandbox"},
            {"id": "pcap-viewer", "name": "Packet Capture Viewer", "type": "pcap"},
            {"id": "registry-viewer", "name": "Registry Viewer", "type": "registry"},
            {"id": "ioc-extractor", "name": "IOC Extractor", "type": "ioc"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "ma-sandbox-report", "title": "Sandbox detonation report", "type": "malware", "required": True},
            {"key": "ma-persistence-artifact", "title": "Persistence artifact", "type": "malware", "required": True},
            {"key": "ma-c2-traffic", "title": "C2 traffic capture", "type": "pcap", "required": True},
            {"key": "ma-c2-protocol", "title": "C2 protocol analysis", "type": "malware", "required": True},
            {"key": "ma-ioc-list", "title": "Extracted IOC list", "type": "ioc", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "Dynamic detonation, persistence discovery, C2 analysis, and IOC extraction.", "career": "Malware analyst dynamic analysis and threat intelligence."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "malware", "company_sizes": ["small", "mid_market"], "industries": ["technology", "defense", "finance"]},
    },
    {
        "slug": "ma-c2-traffic-identification",
        "title": "C2 Traffic Identification",
        "mission_type": "malware_analysis",
        "difficulty": "intermediate",
        "estimated_minutes": 35,
        "story_context": (
            "An endpoint shows periodic beaconing every 60 seconds to a rotating set of IPs. "
            "Analyze the traffic, decode the C2 protocol, extract infrastructure, and create "
            "detection rules."
        ),
        "objectives": [
            {"id": "obj-beacon", "title": "Identify beaconing pattern", "required_evidence": ["beacon-pattern-chart"], "required_actions": [], "xp": 90},
            {"id": "obj-protocol", "title": "Decode C2 protocol", "required_evidence": ["decoded-c2-payload"], "required_actions": [], "xp": 110},
            {"id": "obj-infra", "title": "Extract C2 infrastructure", "required_evidence": ["c2-infrastructure-list"], "required_actions": [], "xp": 80},
            {"id": "obj-rules", "title": "Create detection rules", "required_evidence": ["c2-detection-rule"], "required_actions": [], "xp": 90},
        ],
        "tools": [
            {"id": "pcap-viewer", "name": "Packet Capture Viewer", "type": "pcap"},
            {"id": "netflow-analyzer", "name": "NetFlow Analyzer", "type": "netflow"},
            {"id": "yara-editor", "name": "YARA Rule Editor", "type": "yara"},
            {"id": "ioc-extractor", "name": "IOC Extractor", "type": "ioc"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "beacon-pattern-chart", "title": "Beaconing pattern chart", "type": "chart", "required": True},
            {"key": "decoded-c2-payload", "title": "Decoded C2 payload", "type": "pcap", "required": True},
            {"key": "c2-infrastructure-list", "title": "C2 infrastructure list", "type": "ioc", "required": True},
            {"key": "c2-detection-rule", "title": "C2 detection rule", "type": "yara", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "Beacon detection, protocol decoding, infrastructure extraction, and rule creation.", "career": "Network threat analysis and detection engineering."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "malware", "company_sizes": ["mid_market", "enterprise"], "industries": ["finance", "technology", "defense"]},
    },
]


# --------------------------------------------------------------------------- #
# Cloud Security Lab
# --------------------------------------------------------------------------- #
CLOUD_MISSIONS = [
    {
        "slug": "cloud-iam-privilege-escalation",
        "title": "IAM Privilege Escalation Investigation",
        "mission_type": "incident_response",
        "difficulty": "advanced",
        "estimated_minutes": 45,
        "story_context": (
            "A developer account suddenly holds administrator privileges. Review CloudTrail-style "
            "events, identify the escalation path, and remediate the over-permissive policy."
        ),
        "objectives": [
            {"id": "obj-cloudtrail-triage", "title": "Triage CloudTrail alerts", "required_evidence": ["cloudtrail-escalation-event"], "required_actions": [], "xp": 80},
            {"id": "obj-policy", "title": "Identify over-permissive policy", "required_evidence": ["iam-policy-document"], "required_actions": [], "xp": 100},
            {"id": "obj-path", "title": "Trace escalation path", "required_evidence": ["escalation-path-map"], "required_actions": [], "xp": 100},
            {"id": "obj-remediate", "title": "Remediate IAM policies", "required_evidence": ["iam-policy-document"], "required_actions": ["revoke_sessions", "apply_least_privilege"], "xp": 110},
        ],
        "tools": [
            {"id": "cloud-console", "name": "Cloud Console", "type": "cloud"},
            {"id": "iam-explorer", "name": "IAM Policy Explorer", "type": "iam"},
            {"id": "cloudtrail-viewer", "name": "CloudTrail Event Viewer", "type": "cloudtrail"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "cloudtrail-escalation-event", "title": "CloudTrail escalation event", "type": "cloud", "required": True},
            {"key": "iam-policy-document", "title": "IAM policy document", "type": "iam", "required": True},
            {"key": "escalation-path-map", "title": "Escalation path map", "type": "map", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "Cloud IAM investigation, escalation path tracing, and least-privilege remediation.", "career": "Cloud security engineer and IAM governance."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "cloud", "company_sizes": ["mid_market", "enterprise"], "industries": ["technology", "finance", "media"]},
    },
    {
        "slug": "cloud-misconfigured-storage-exposure",
        "title": "Misconfigured Storage Exposure",
        "mission_type": "configuration_audit",
        "difficulty": "intermediate",
        "estimated_minutes": 30,
        "story_context": (
            "A storage bucket with public read access exposes PII. Identify the misconfiguration, "
            "audit access logs, remediate permissions, and notify affected data subjects."
        ),
        "objectives": [
            {"id": "obj-bucket-triage", "title": "Identify public bucket exposure", "required_evidence": ["bucket-acl-report"], "required_actions": [], "xp": 90},
            {"id": "obj-access-audit", "title": "Audit access logs", "required_evidence": ["bucket-access-log"], "required_actions": [], "xp": 80},
            {"id": "obj-remediate-bucket", "title": "Remediate permissions", "required_evidence": ["bucket-acl-report"], "required_actions": ["apply_least_privilege", "block_public_access"], "xp": 100},
        ],
        "tools": [
            {"id": "cloud-console", "name": "Cloud Console", "type": "cloud"},
            {"id": "storage-explorer", "name": "Storage Explorer", "type": "storage"},
            {"id": "cloudtrail-viewer", "name": "CloudTrail Event Viewer", "type": "cloudtrail"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "bucket-acl-report", "title": "Bucket ACL report", "type": "cloud", "required": True},
            {"key": "bucket-access-log", "title": "Bucket access log", "type": "cloud", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "Cloud storage exposure triage, access auditing, and remediation.", "career": "Cloud security and data protection."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "cloud", "company_sizes": ["small", "mid_market"], "industries": ["finance", "healthcare", "technology"]},
    },
    {
        "slug": "cloud-k8s-pod-escape-investigation",
        "title": "Kubernetes Pod Escape Investigation",
        "mission_type": "incident_response",
        "difficulty": "advanced",
        "estimated_minutes": 40,
        "story_context": (
            "A pod with hostPath mounts shows suspicious activity suggesting container escape. "
            "Review RBAC, audit logs, and restrict the cluster to prevent node compromise."
        ),
        "objectives": [
            {"id": "obj-pod-triage", "title": "Triage pod security alert", "required_evidence": ["k8s-audit-event"], "required_actions": [], "xp": 90},
            {"id": "obj-rbac", "title": "Review RBAC and pod security", "required_evidence": ["k8s-rbac-report"], "required_actions": [], "xp": 100},
            {"id": "obj-escape", "title": "Confirm container escape", "required_evidence": ["host-path-evidence"], "required_actions": [], "xp": 110},
            {"id": "obj-restrict", "title": "Restrict cluster policies", "required_evidence": ["k8s-rbac-report"], "required_actions": ["apply_least_privilege", "enable_pod_security"], "xp": 100},
        ],
        "tools": [
            {"id": "k8s-console", "name": "Kubernetes Console", "type": "k8s"},
            {"id": "cloud-console", "name": "Cloud Console", "type": "cloud"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "k8s-audit-event", "title": "K8s audit event", "type": "cloud", "required": True},
            {"key": "k8s-rbac-report", "title": "RBAC report", "type": "cloud", "required": True},
            {"key": "host-path-evidence", "title": "HostPath mount evidence", "type": "cloud", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "Container escape investigation, RBAC review, and cluster hardening.", "career": "Container security and DevSecOps."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "cloud", "company_sizes": ["mid_market", "enterprise"], "industries": ["technology", "finance", "ecommerce"]},
    },
    {
        "slug": "cloud-credential-theft-investigation",
        "title": "Cloud Credential Theft Investigation",
        "mission_type": "incident_response",
        "difficulty": "intermediate",
        "estimated_minutes": 35,
        "story_context": (
            "An access key appears in a public repository commit. Rotate keys, review usage logs, "
            "identify actions taken with the stolen key, and revoke all active sessions."
        ),
        "objectives": [
            {"id": "obj-key-leak", "title": "Confirm leaked access key", "required_evidence": ["repo-leaked-key"], "required_actions": [], "xp": 80},
            {"id": "obj-usage", "title": "Review key usage logs", "required_evidence": ["key-usage-log"], "required_actions": [], "xp": 100},
            {"id": "obj-impact", "title": "Assess impact of stolen actions", "required_evidence": ["key-action-summary"], "required_actions": [], "xp": 90},
            {"id": "obj-rotate", "title": "Rotate and revoke credentials", "required_evidence": ["repo-leaked-key"], "required_actions": ["revoke_sessions", "rotate_keys"], "xp": 110},
        ],
        "tools": [
            {"id": "cloud-console", "name": "Cloud Console", "type": "cloud"},
            {"id": "cloudtrail-viewer", "name": "CloudTrail Event Viewer", "type": "cloudtrail"},
            {"id": "repo-audit-tool", "name": "Repository Audit Console", "type": "repo"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "repo-leaked-key", "title": "Leaked key evidence", "type": "repo", "required": True},
            {"key": "key-usage-log", "title": "Key usage CloudTrail log", "type": "cloud", "required": True},
            {"key": "key-action-summary", "title": "Stolen key action summary", "type": "cloud", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "Credential leak investigation, usage review, impact assessment, and rotation.", "career": "Cloud security incident response."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "cloud", "company_sizes": ["small", "mid_market"], "industries": ["technology", "finance", "startup"]},
    },
]


# --------------------------------------------------------------------------- #
# Secure Coding Lab
# --------------------------------------------------------------------------- #
SECURE_CODING_MISSIONS = [
    {
        "slug": "sc-sql-injection-remediation",
        "title": "SQL Injection Remediation",
        "mission_type": "secure_coding",
        "difficulty": "beginner",
        "estimated_minutes": 25,
        "story_context": (
            "A login form concatenates user input into SQL queries. Analyze the vulnerable query, "
            "demonstrate exploitation safely, and remediate with parameterized queries."
        ),
        "objectives": [
            {"id": "obj-find-vuln", "title": "Identify SQL injection vulnerability", "required_evidence": ["vulnerable-query-snippet"], "required_actions": [], "xp": 80},
            {"id": "obj-demonstrate", "title": "Demonstrate exploitation safely", "required_evidence": ["sqli-payload-evidence"], "required_actions": [], "xp": 70},
            {"id": "obj-remediate", "title": "Implement parameterized queries", "required_evidence": ["patched-query-snippet"], "required_actions": ["apply_parameterized_query"], "xp": 110},
        ],
        "tools": [
            {"id": "ide", "name": "Code Editor", "type": "ide"},
            {"id": "sast-scanner", "name": "SAST Scanner", "type": "sast"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "vulnerable-query-snippet", "title": "Vulnerable query snippet", "type": "code", "required": True},
            {"key": "sqli-payload-evidence", "title": "SQLi payload evidence", "type": "code", "required": True},
            {"key": "patched-query-snippet", "title": "Patched query snippet", "type": "code", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "SQL injection discovery, exploitation, and remediation with parameterized queries.", "career": "Secure coding and application security fundamentals."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "secure_coding", "company_sizes": ["small", "mid_market"], "industries": ["technology", "finance", "ecommerce"]},
    },
    {
        "slug": "sc-xss-vulnerability-patching",
        "title": "XSS Vulnerability Patching",
        "mission_type": "secure_coding",
        "difficulty": "beginner",
        "estimated_minutes": 25,
        "story_context": (
            "A comment field renders user input without encoding, enabling reflected XSS. Identify "
            "the sink, apply output encoding, and add a content security policy."
        ),
        "objectives": [
            {"id": "obj-find-sink", "title": "Identify XSS sink", "required_evidence": ["xss-sink-snippet"], "required_actions": [], "xp": 80},
            {"id": "obj-patch", "title": "Apply output encoding", "required_evidence": ["patched-output-snippet"], "required_actions": ["apply_output_encoding"], "xp": 100},
            {"id": "obj-csp", "title": "Add content security policy", "required_evidence": ["csp-header"], "required_actions": ["apply_csp"], "xp": 90},
        ],
        "tools": [
            {"id": "ide", "name": "Code Editor", "type": "ide"},
            {"id": "sast-scanner", "name": "SAST Scanner", "type": "sast"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "xss-sink-snippet", "title": "XSS sink snippet", "type": "code", "required": True},
            {"key": "patched-output-snippet", "title": "Patched output snippet", "type": "code", "required": True},
            {"key": "csp-header", "title": "Content security policy header", "type": "code", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "XSS discovery, output encoding, and CSP implementation.", "career": "Web application security engineering."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "secure_coding", "company_sizes": ["small", "mid_market"], "industries": ["ecommerce", "media", "technology"]},
    },
    {
        "slug": "sc-broken-authentication-fix",
        "title": "Broken Authentication Fix",
        "mission_type": "secure_coding",
        "difficulty": "intermediate",
        "estimated_minutes": 35,
        "story_context": (
            "Session tokens never expire and credential recovery uses guessable questions. Implement "
            "token rotation, rate limiting, and MFA enforcement."
        ),
        "objectives": [
            {"id": "obj-session-audit", "title": "Audit session management", "required_evidence": ["session-audit-report"], "required_actions": [], "xp": 90},
            {"id": "obj-token-rotation", "title": "Implement token rotation", "required_evidence": ["token-rotation-snippet"], "required_actions": ["apply_token_rotation"], "xp": 100},
            {"id": "obj-mfa", "title": "Enforce MFA", "required_evidence": ["mfa-enforcement-snippet"], "required_actions": ["enforce_mfa"], "xp": 100},
        ],
        "tools": [
            {"id": "ide", "name": "Code Editor", "type": "ide"},
            {"id": "sast-scanner", "name": "SAST Scanner", "type": "sast"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "session-audit-report", "title": "Session audit report", "type": "code", "required": True},
            {"key": "token-rotation-snippet", "title": "Token rotation snippet", "type": "code", "required": True},
            {"key": "mfa-enforcement-snippet", "title": "MFA enforcement snippet", "type": "code", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "Authentication audit, token rotation, and MFA enforcement.", "career": "Application security and identity engineering."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "secure_coding", "company_sizes": ["mid_market", "enterprise"], "industries": ["finance", "healthcare", "technology"]},
    },
    {
        "slug": "sc-api-idor-remediation",
        "title": "API IDOR Remediation",
        "mission_type": "secure_coding",
        "difficulty": "intermediate",
        "estimated_minutes": 30,
        "story_context": (
            "An API returns records by sequential ID without authorization checks, enabling IDOR. "
            "Add authorization middleware and validate object ownership."
        ),
        "objectives": [
            {"id": "obj-idor-find", "title": "Identify IDOR vulnerability", "required_evidence": ["idor-endpoint-report"], "required_actions": [], "xp": 90},
            {"id": "obj-authz", "title": "Add authorization middleware", "required_evidence": ["authz-middleware-snippet"], "required_actions": ["apply_authorization"], "xp": 110},
            {"id": "obj-validate", "title": "Validate object ownership", "required_evidence": ["ownership-check-snippet"], "required_actions": ["validate_ownership"], "xp": 90},
        ],
        "tools": [
            {"id": "ide", "name": "Code Editor", "type": "ide"},
            {"id": "sast-scanner", "name": "SAST Scanner", "type": "sast"},
            {"id": "api-tester", "name": "API Tester", "type": "api"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "idor-endpoint-report", "title": "IDOR endpoint report", "type": "code", "required": True},
            {"key": "authz-middleware-snippet", "title": "Authorization middleware snippet", "type": "code", "required": True},
            {"key": "ownership-check-snippet", "title": "Ownership check snippet", "type": "code", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "IDOR discovery, authorization middleware, and ownership validation.", "career": "API security engineering."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "secure_coding", "company_sizes": ["small", "mid_market"], "industries": ["technology", "finance", "healthcare"]},
    },
]


# --------------------------------------------------------------------------- #
# Network Defense Lab
# --------------------------------------------------------------------------- #
NETWORK_DEFENSE_MISSIONS = [
    {
        "slug": "nd-firewall-rule-audit",
        "title": "Firewall Rule Audit and Hardening",
        "mission_type": "configuration_audit",
        "difficulty": "beginner",
        "estimated_minutes": 25,
        "story_context": (
            "A perimeter firewall has accumulated overly permissive ANY rules. Audit the ruleset, "
            "identify shadowed and redundant rules, and implement least-privilege hardening."
        ),
        "objectives": [
            {"id": "obj-ruleset-audit", "title": "Audit the firewall ruleset", "required_evidence": ["fw-ruleset-report"], "required_actions": [], "xp": 80},
            {"id": "obj-shadowed", "title": "Identify shadowed and redundant rules", "required_evidence": ["shadowed-rules-report"], "required_actions": [], "xp": 90},
            {"id": "obj-harden", "title": "Implement least-privilege hardening", "required_evidence": ["harden-ruleset-report"], "required_actions": ["apply_least_privilege", "remove_shadowed_rules"], "xp": 110},
        ],
        "tools": [
            {"id": "firewall-console", "name": "Firewall Console", "type": "firewall"},
            {"id": "ruleset-analyzer", "name": "Ruleset Analyzer", "type": "ruleset"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "fw-ruleset-report", "title": "Firewall ruleset report", "type": "firewall", "required": True},
            {"key": "shadowed-rules-report", "title": "Shadowed rules report", "type": "firewall", "required": True},
            {"key": "harden-ruleset-report", "title": "Hardened ruleset report", "type": "firewall", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "Firewall ruleset auditing, shadowed rule identification, and hardening.", "career": "Network security engineering and firewall management."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "network_defense", "company_sizes": ["small", "mid_market"], "industries": ["manufacturing", "finance", "education"]},
    },
    {
        "slug": "nd-ids-ips-tuning",
        "title": "IDS/IPS Tuning and Detection",
        "mission_type": "configuration_audit",
        "difficulty": "intermediate",
        "estimated_minutes": 35,
        "story_context": (
            "The IDS generates excessive false positives. Analyze the alert noise, tune signature "
            "thresholds, and validate tuned rules against replay traffic."
        ),
        "objectives": [
            {"id": "obj-noise-analysis", "title": "Analyze alert noise", "required_evidence": ["ids-noise-report"], "required_actions": [], "xp": 80},
            {"id": "obj-tune", "title": "Tune signature thresholds", "required_evidence": ["tuned-signatures"], "required_actions": ["tune_signatures"], "xp": 100},
            {"id": "obj-validate", "title": "Validate against replay traffic", "required_evidence": ["validation-report"], "required_actions": [], "xp": 90},
        ],
        "tools": [
            {"id": "ids-console", "name": "IDS/IPS Console", "type": "ids"},
            {"id": "pcap-viewer", "name": "Packet Capture Viewer", "type": "pcap"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "ids-noise-report", "title": "IDS noise report", "type": "ids", "required": True},
            {"key": "tuned-signatures", "title": "Tuned signatures", "type": "ids", "required": True},
            {"key": "validation-report", "title": "Validation report", "type": "ids", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "IDS noise analysis, signature tuning, and validation.", "career": "Detection engineering and SOC tuning."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "network_defense", "company_sizes": ["mid_market", "enterprise"], "industries": ["finance", "technology", "government"]},
    },
    {
        "slug": "nd-segmentation-review",
        "title": "Network Segmentation Review",
        "mission_type": "configuration_audit",
        "difficulty": "intermediate",
        "estimated_minutes": 30,
        "story_context": (
            "An audit finds guest Wi-Fi can reach the server VLAN. Verify VLAN and ACL segmentation, "
            "identify gaps, and enforce isolation between trust zones."
        ),
        "objectives": [
            {"id": "obj-vlan-map", "title": "Map VLAN and zone structure", "required_evidence": ["vlan-zone-map"], "required_actions": [], "xp": 80},
            {"id": "obj-gap-find", "title": "Identify segmentation gaps", "required_evidence": ["segmentation-gap-report"], "required_actions": [], "xp": 100},
            {"id": "obj-enforce", "title": "Enforce zone isolation", "required_evidence": ["segmentation-gap-report"], "required_actions": ["apply_least_privilege", "enforce_zone_isolation"], "xp": 100},
        ],
        "tools": [
            {"id": "firewall-console", "name": "Firewall Console", "type": "firewall"},
            {"id": "switch-console", "name": "Switch Console", "type": "switch"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "vlan-zone-map", "title": "VLAN zone map", "type": "map", "required": True},
            {"key": "segmentation-gap-report", "title": "Segmentation gap report", "type": "firewall", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "VLAN mapping, segmentation gap identification, and zone isolation.", "career": "Network architecture and zero-trust implementation."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "network_defense", "company_sizes": ["mid_market", "enterprise"], "industries": ["manufacturing", "healthcare", "finance"]},
    },
    {
        "slug": "nd-incident-response-recovery",
        "title": "Incident Response and Recovery",
        "mission_type": "incident_response",
        "difficulty": "advanced",
        "estimated_minutes": 45,
        "story_context": (
            "A web server is compromised via a vulnerable plugin. Determine the attack vector, isolate "
            "the host, restore from a verified backup, and document the incident timeline."
        ),
        "objectives": [
            {"id": "obj-vector", "title": "Determine attack vector", "required_evidence": ["web-server-access-log", "exploit-evidence"], "required_actions": [], "xp": 90},
            {"id": "obj-isolate", "title": "Isolate compromised host", "required_evidence": ["web-server-access-log"], "required_actions": ["isolate_endpoint"], "xp": 100},
            {"id": "obj-restore", "title": "Restore from verified backup", "required_evidence": ["backup-restore-report"], "required_actions": ["restore_backup"], "xp": 90},
            {"id": "obj-timeline", "title": "Document incident timeline", "required_evidence": ["incident-timeline"], "required_actions": [], "xp": 80},
        ],
        "tools": [
            {"id": "firewall-console", "name": "Firewall Console", "type": "firewall"},
            {"id": "soc-siem", "name": "Simulated SIEM", "type": "siem"},
            {"id": "backup-console", "name": "Backup Console", "type": "backup"},
            {"id": "case-management", "name": "Case Management", "type": "case"},
        ],
        "evidence_blueprint": [
            {"key": "web-server-access-log", "title": "Web server access log", "type": "log", "required": True},
            {"key": "exploit-evidence", "title": "Exploit evidence", "type": "log", "required": True},
            {"key": "backup-restore-report", "title": "Backup restore report", "type": "backup", "required": True},
            {"key": "incident-timeline", "title": "Incident timeline", "type": "timeline", "required": True},
        ],
        "scoring_rubric": _rubric(),
        "debrief_rubric": {"summary": "Attack vector analysis, isolation, backup restoration, and timeline documentation.", "career": "Network incident response and recovery operations."},
        "safety_rules": SAFETY_RULES,
        "generation_rules": {"facility": "network_defense", "company_sizes": ["small", "mid_market"], "industries": ["ecommerce", "media", "education"]},
    },
]


# Aggregate registry: facility slug -> list of mission templates
ALL_MISSIONS: dict[str, list[dict]] = {
    "soc": SOC_MISSIONS,
    "enterprise-network": ENTERPRISE_MISSIONS,
    "digital-forensics": FORENSICS_MISSIONS,
    "malware-analysis": MALWARE_MISSIONS,
    "cloud-security": CLOUD_MISSIONS,
    "secure-coding": SECURE_CODING_MISSIONS,
    "network-defense": NETWORK_DEFENSE_MISSIONS,
}
