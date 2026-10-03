"""
Realistic scenario generator for CyberVerse Labs.

Generates fictional company profiles, multi-asset network topologies,
multiple identities, rich logs, correlated alerts, and evidence items
based on a mission template's facility type and generation rules.

All generated content is safety-validated: reserved IP ranges, training
email domains (``.cyberverse.test``), no real malware, no public targeting.
"""

from __future__ import annotations

import ipaddress
import random
from typing import Any

# Reserved / documentation ranges only — never public internet.
ALLOWED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("192.0.2.0/24"),   # TEST-NET-1
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3
]

COMPANY_ROOTS = [
    "Northstar", "Blue Harbor", "Summit Vale", "Copperline", "Aster Ridge",
    "Granite Peak", "Ironwood", "Cobalt Bay", "Meridian Line", "Pinegrove",
]
COMPANY_SUFFIXES = {
    "manufacturing": ["Fabrication Group", "Industrial", "Components"],
    "finance": ["Credit Union", "Financial", "Bancorp"],
    "healthcare": ["Health Network", "Medical Center", "Care Systems"],
    "technology": ["Technologies", "Systems", "Labs"],
    "education": ["University", "Academy", "Institute"],
    "ecommerce": ["Commerce", "Retail Group", "Marketplace"],
    "media": ["Media Group", "Studios", "Broadcasting"],
    "government": ["County", "Municipal", "Agency"],
    "aerospace": ["Aerospace", "Aviation", "Defense Systems"],
    "legal": ["Legal Partners", "Law Group"],
    "defense": ["Defense Systems", "Aerospace"],
    "hr": ["Solutions"],
    "startup": ["Labs", "AI", "Cloud"],
}
COMPANY_REGIONS = ["fictional-us-east", "fictional-us-west", "fictional-eu-north", "fictional-ap-south"]

USER_NAMES = [
    "Maya Chen", "Jordan Ellis", "Rina Patel", "Owen Brooks", "Sasha Romero",
    "Dev Kumar", "Lena Novak", "Marcus Reed", "Priya Shah", "Tom Alvarez",
    "Nora Lindgren", "Felix Park", "Ava Morgan", "Kai Tanaka", "Iris Dahl",
]
USER_ROLES = [
    "Finance Manager", "HR Coordinator", "Operations Lead", "IT Administrator",
    "Software Engineer", "Sales Representative", "Marketing Specialist",
    "Facilities Manager", "Executive Assistant", "Procurement Analyst",
]
DEPARTMENTS = ["Finance", "Human Resources", "Operations", "IT", "Engineering", "Sales", "Marketing", "Executive"]

HOSTNAME_PREFIXES = ["hq", "dc", "srv", "edge", "core", "ws", "app", "db", "fw", "sw"]


def _domain_for_company(company_name: str) -> str:
    """Return a training-safe email domain derived from the company name."""
    return f"{company_name.lower().replace(' ', '-')}.cyberverse.test"


def _random_ip(rng: random.Random, subnet: str = "10") -> str:
    """Generate a random private/TEST-NET IP for fictional assets."""
    if subnet == "10":
        return f"10.{rng.randint(10, 200)}.{rng.randint(0, 250)}.{rng.randint(20, 240)}"
    if subnet == "172":
        return f"172.{rng.randint(16, 31)}.{rng.randint(0, 250)}.{rng.randint(20, 240)}"
    if subnet == "192168":
        return f"192.168.{rng.randint(1, 250)}.{rng.randint(20, 240)}"
    # TEST-NET ranges for "external" fictional endpoints
    return rng.choice(["192.0.2.44", "198.51.100.77", "203.0.113.22", "198.51.100.44"])


def _make_identity(rng: random.Random, idx: int, company_domain: str, department: str | None = None) -> dict[str, Any]:
    name = rng.choice(USER_NAMES)
    dept = department or rng.choice(DEPARTMENTS)
    role = rng.choice(USER_ROLES)
    return {
        "id": f"user-{idx:03d}",
        "display_name": name,
        "role": role,
        "department": dept,
        "email": f"{name.lower().replace(' ', '.')}@{company_domain}",
        "mfa_enrolled": rng.choice([True, True, False]),
        "account_status": rng.choice(["active", "active", "active", "locked"]),
    }


def _make_asset(
    rng: random.Random,
    idx: int,
    company_prefix: str,
    asset_type: str,
    owner_id: str | None = None,
    subnet: str = "10",
) -> dict[str, Any]:
    asset_specs = {
        "windows_workstation": {
            "services": ["edr_agent", "office_suite", "vpn_client"],
            "criticality": "medium",
        },
        "linux_server": {
            "services": ["ssh", "nginx", "postgres"],
            "criticality": "high",
        },
        "windows_server": {
            "services": ["active_directory", "dns", "file_sharing"],
            "criticality": "high",
        },
        "domain_controller": {
            "services": ["active_directory", "kerberos", "ldap", "dns"],
            "criticality": "critical",
        },
        "file_server": {
            "services": ["smb", "nfs", "backup_agent"],
            "criticality": "high",
        },
        "web_server": {
            "services": ["http", "https", "php-fpm"],
            "criticality": "high",
        },
        "database_server": {
            "services": ["postgres", "redis"],
            "criticality": "critical",
        },
        "firewall": {
            "services": ["firewall", "ips", "vpn_gateway"],
            "criticality": "critical",
        },
        "switch": {
            "services": ["stp", "vlan", "snmp"],
            "criticality": "high",
        },
        "router": {
            "services": ["ospf", "bgp", "snmp"],
            "criticality": "critical",
        },
        "cloud_vm": {
            "services": ["cloud_agent", "docker", "nginx"],
            "criticality": "high",
        },
        "k8s_node": {
            "services": ["kubelet", "containerd", "proxy"],
            "criticality": "high",
        },
        "sandbox_vm": {
            "services": ["malware_sandbox", "broker"],
            "criticality": "medium",
        },
        "forensics_workstation": {
            "services": ["forensics_tools", "write_blocker"],
            "criticality": "medium",
        },
    }
    spec = asset_specs.get(asset_type, {"services": ["generic"], "criticality": "medium"})
    prefix = rng.choice(HOSTNAME_PREFIXES)
    hostname = f"{company_prefix}-{prefix}-{idx:03d}"
    return {
        "id": f"asset-{idx:03d}",
        "hostname": hostname,
        "type": asset_type,
        "ip_address": _random_ip(rng, subnet),
        "location": rng.choice(["hq-floor-1", "hq-floor-2", "datacenter", "cloud-tenant", "branch-office"]),
        "criticality": spec["criticality"],
        "owner_user_id": owner_id,
        "services": spec["services"],
        "tags": ["managed", asset_type],
    }


# Facility-specific topology builders -------------------------------------------------

def _topology_soc(rng: random.Random) -> dict[str, Any]:
    return {
        "sites": ["headquarters", "branch-office", "cloud-tenant"],
        "segments": ["corp", "server", "vpn", "cloud", "dmz"],
        "edges": [["vpn", "corp"], ["corp", "server"], ["server", "cloud"], ["corp", "dmz"], ["dmz", "cloud"]],
        "siem_collectors": ["corp", "server", "dmz", "cloud"],
        "monitoring": {"edr": True, "siem": True, "email_security": True, "netflow": True},
    }


def _topology_enterprise(rng: random.Random) -> dict[str, Any]:
    return {
        "sites": ["headquarters", "branch-office", "datacenter", "cloud-tenant"],
        "segments": ["corp", "server", "dmz", "vpn", "cloud", "admin"],
        "edges": [["vpn", "corp"], ["corp", "server"], ["corp", "admin"], ["server", "dmz"], ["server", "cloud"], ["dmz", "cloud"]],
        "active_directory": {"domain": "corp.local", "forest": "corp.local", "trusts": []},
        "monitoring": {"edr": True, "siem": True, "dc_audit": True, "netflow": True},
    }


def _topology_forensics(rng: random.Random) -> dict[str, Any]:
    return {
        "sites": ["forensics-lab"],
        "segments": ["evidence-custody", "analysis", "write-blocker", "isolated"],
        "edges": [["evidence-custody", "analysis"], ["analysis", "write-blocker"], ["analysis", "isolated"]],
        "evidence_chain": {"write_blocker": True, "hash_verification": True, "custody_log": True},
        "monitoring": {"audit": True, "hashing": True},
    }


def _topology_malware(rng: random.Random) -> dict[str, Any]:
    return {
        "sites": ["malware-lab"],
        "segments": ["sandbox", "analysis", "isolated", "sample-storage"],
        "edges": [["sample-storage", "sandbox"], ["sandbox", "analysis"], ["analysis", "isolated"]],
        "safety": {"network_isolation": True, "no_real_malware": True, "behavioral_replay": True},
        "monitoring": {"sandbox_logs": True, "pcap": True, "process_trace": True},
    }


def _topology_cloud(rng: random.Random) -> dict[str, Any]:
    regions = rng.sample(["fictional-us-east-1", "fictional-eu-west-1", "fictional-ap-south-1"], k=rng.randint(2, 3))
    return {
        "sites": regions,
        "segments": ["vpc-prod", "vpc-mgmt", "subnet-public", "subnet-private", "subnet-db"],
        "edges": [["subnet-public", "vpc-prod"], ["vpc-prod", "subnet-private"], ["subnet-private", "subnet-db"], ["vpc-mgmt", "vpc-prod"]],
        "services": ["iam", "storage", "compute", "kubernetes", "logging", "secrets"],
        "monitoring": {"cloudtrail": True, "config": True, "guardduty": True, "vpc_flow": True},
    }


def _topology_secure_coding(rng: random.Random) -> dict[str, Any]:
    return {
        "sites": ["dev-workstation"],
        "segments": ["dev", "ci", "repo"],
        "edges": [["dev", "ci"], ["ci", "repo"], ["dev", "repo"]],
        "pipeline": {"sast": True, "dast": True, "dependency_scan": True, "secret_scan": True},
        "monitoring": {"audit": True, "pipeline_logs": True},
    }


def _topology_network_defense(rng: random.Random) -> dict[str, Any]:
    return {
        "sites": ["headquarters", "datacenter", "branch-office"],
        "segments": ["corp", "server", "guest", "dmz", "mgmt", "iot"],
        "edges": [["corp", "server"], ["corp", "guest"], ["corp", "dmz"], ["guest", "dmz"], ["mgmt", "server"], ["iot", "mgmt"]],
        "devices": {"firewalls": 2, "switches": 4, "routers": 2, "ids_ips": 2},
        "monitoring": {"netflow": True, "ids": True, "syslog": True, "pcap": True},
    }


TOPOLOGY_BUILDERS = {
    "soc": _topology_soc,
    "enterprise": _topology_enterprise,
    "forensics": _topology_forensics,
    "malware": _topology_malware,
    "cloud": _topology_cloud,
    "secure_coding": _topology_secure_coding,
    "network_defense": _topology_network_defense,
}


def _assets_for_facility(facility: str, rng: random.Random, company_prefix: str, primary_user_id: str) -> list[dict[str, Any]]:
    """Build a realistic asset inventory appropriate to the facility type."""
    idx = 1
    assets: list[dict[str, Any]] = []
    primary = primary_user_id

    def add(asset_type: str, owner: str | None = None, subnet: str = "10") -> None:
        nonlocal idx
        assets.append(_make_asset(rng, idx, company_prefix, asset_type, owner or primary, subnet))
        idx += 1

    if facility == "soc":
        add("windows_workstation")
        add("linux_server")
        add("firewall", None)
        add("switch", None)
    elif facility == "enterprise":
        add("domain_controller", None)
        add("domain_controller", None)
        add("file_server", None)
        add("windows_workstation")
        add("linux_server")
        add("firewall", None)
        add("switch", None)
    elif facility == "forensics":
        add("forensics_workstation", None)
        add("windows_workstation")
        add("linux_server", None)
    elif facility == "malware":
        add("sandbox_vm", None)
        add("forensics_workstation", None)
        add("linux_server", None)
    elif facility == "cloud":
        add("cloud_vm", None)
        add("k8s_node", None)
        add("k8s_node", None)
        add("cloud_vm", None)
    elif facility == "secure_coding":
        add("windows_workstation")
        add("linux_server", None)
    elif facility == "network_defense":
        add("firewall", None)
        add("firewall", None)
        add("switch", None)
        add("switch", None)
        add("router", None)
        add("web_server", None)
    return assets


def _logs_for_facility(
    facility: str,
    rng: random.Random,
    affected_user: dict[str, Any],
    assets: list[dict[str, Any]],
    evidence_blueprint: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build realistic, correlated log entries keyed to evidence and assets."""
    user_id = affected_user["id"]
    workstation = next((a for a in assets if a["type"] == "windows_workstation"), assets[0])
    external_ip = _random_ip(rng, "testnet")
    ts = lambda n: f"2026-0{rng.randint(3, 8)}-{rng.randint(10, 28)}T{rng.randint(0, 5):02d}:{rng.randint(10, 59):02d}:{rng.randint(10, 59):02d}Z"

    base_logs: list[dict[str, Any]] = []

    if facility == "soc":
        base_logs = [
            {"id": "log-auth-001", "type": "auth", "source_ip": external_ip, "result": "success", "user_id": user_id, "timestamp": ts(1), "event": "interactive_login", "workstation": workstation["hostname"]},
            {"id": "log-auth-002", "type": "auth", "source_ip": workstation["ip_address"], "result": "success", "user_id": user_id, "timestamp": ts(2), "event": "mailbox_rule_created"},
            {"id": "log-mail-001", "type": "email", "event": "mailbox_forwarding_rule_created", "user_id": user_id, "timestamp": ts(3), "forward_to": external_ip},
            {"id": "log-fw-001", "type": "firewall", "src_ip": external_ip, "dst_ip": workstation["ip_address"], "port": 443, "action": "allow", "timestamp": ts(4)},
            {"id": "log-edr-001", "type": "endpoint", "asset_id": workstation["id"], "event": "process_scan", "result": "clean", "timestamp": ts(5)},
        ]
    elif facility == "enterprise":
        dc = next((a for a in assets if a["type"] == "domain_controller"), assets[0])
        srv = next((a for a in assets if a["type"] == "file_server"), assets[1] if len(assets) > 1 else assets[0])
        base_logs = [
            {"id": "log-kerb-001", "type": "kerberos", "dc": dc["hostname"], "event": "preauth_failed", "user_id": user_id, "count": rng.randint(40, 200), "timestamp": ts(1)},
            {"id": "log-kerb-002", "type": "kerberos", "dc": dc["hostname"], "event": "as_req_success", "source_ip": external_ip, "user_id": user_id, "timestamp": ts(2)},
            {"id": "log-kerb-003", "type": "kerberos", "dc": dc["hostname"], "event": "tgs_req", "spn": "MSSQLSvc/srv-002:1433", "user_id": user_id, "timestamp": ts(3)},
            {"id": "log-ps-001", "type": "powershell", "asset_id": srv["id"], "event": "remote_session", "user_id": user_id, "command": "Invoke-Command -ComputerName srv-002", "timestamp": ts(4)},
            {"id": "log-smb-001", "type": "smb", "src": workstation["hostname"], "dst": srv["hostname"], "action": "share_access", "timestamp": ts(5)},
            {"id": "log-4624-001", "type": "windows_security", "event_id": 4624, "logon_type": 3, "source_ip": external_ip, "user_id": user_id, "timestamp": ts(6)},
        ]
    elif facility == "forensics":
        base_logs = [
            {"id": "log-mft-001", "type": "filesystem", "asset_id": workstation["id"], "event": "file_created", "path": "C:\\Users\\Public\\svcupd.exe", "timestamp": ts(1)},
            {"id": "log-mft-002", "type": "filesystem", "asset_id": workstation["id"], "event": "file_deleted", "path": "C:\\Temp\\payload.bin", "timestamp": ts(2)},
            {"id": "log-prefetch-001", "type": "prefetch", "asset_id": workstation["id"], "binary": "svcupd.exe", "last_run": ts(3)},
            {"id": "log-sched-001", "type": "scheduled_task", "asset_id": workstation["id"], "task": "\\Microsoft\\Windows\\UpdateSync", "command": "rundll32.exe update.dll,Start", "timestamp": ts(4)},
            {"id": "log-usb-001", "type": "device", "asset_id": workstation["id"], "event": "usb_inserted", "timestamp": ts(5)},
        ]
    elif facility == "malware":
        sandbox = next((a for a in assets if a["type"] == "sandbox_vm"), assets[0])
        base_logs = [
            {"id": "log-detonation-001", "type": "sandbox", "asset_id": sandbox["id"], "event": "detonation_started", "sample_hash": "sha256:9f8a" + format(rng.randint(0, 0xFFFFFF), "06x"), "timestamp": ts(1)},
            {"id": "log-file-001", "type": "filesystem", "asset_id": sandbox["id"], "event": "file_dropped", "path": "C:\\ProgramData\\cache.bin", "timestamp": ts(2)},
            {"id": "log-reg-001", "type": "registry", "asset_id": sandbox["id"], "event": "key_created", "key": "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\\Updater", "timestamp": ts(3)},
            {"id": "log-proc-001", "type": "process", "asset_id": sandbox["id"], "parent": "svchost.exe", "child": "cache.bin", "timestamp": ts(4)},
            {"id": "log-net-001", "type": "network", "asset_id": sandbox["id"], "dst_ip": external_ip, "dst_port": 8443, "beacon_interval": 60, "timestamp": ts(5)},
        ]
    elif facility == "cloud":
        vm = next((a for a in assets if a["type"] == "cloud_vm"), assets[0])
        base_logs = [
            {"id": "log-ct-001", "type": "cloudtrail", "event": "AttachRolePolicy", "user_id": user_id, "role": "DeveloperRole", "policy": "AdministratorAccess", "timestamp": ts(1)},
            {"id": "log-ct-002", "type": "cloudtrail", "event": "AssumeRole", "source_ip": external_ip, "role": "AdminRole", "user_id": user_id, "timestamp": ts(2)},
            {"id": "log-s3-001", "type": "storage", "bucket": "public-assets-bucket", "event": "PutBucketAcl", "acl": "public-read", "user_id": user_id, "timestamp": ts(3)},
            {"id": "log-k8s-001", "type": "k8s_audit", "event": "pod_hostpath", "namespace": "default", "pod": "debug-pod", "mount": "/host", "user_id": user_id, "timestamp": ts(4)},
            {"id": "log-vpc-001", "type": "vpc_flow", "src": vm["ip_address"], "dst": external_ip, "port": 443, "bytes": rng.randint(10**8, 10**9), "action": "ACCEPT", "timestamp": ts(5)},
        ]
    elif facility == "secure_coding":
        base_logs = [
            {"id": "log-git-001", "type": "git", "event": "commit", "author": affected_user["email"], "message": "fix auth flow", "files": ["auth.py", "config.py"], "timestamp": ts(1)},
            {"id": "log-sast-001", "type": "sast", "event": "finding", "rule": "SQL_INJECTION", "severity": "high", "file": "auth.py", "line": rng.randint(20, 80), "timestamp": ts(2)},
            {"id": "log-ci-001", "type": "ci", "event": "build_failed", "stage": "security_scan", "timestamp": ts(3)},
            {"id": "log-secret-001", "type": "secret_scan", "event": "leaked_key", "file": "config.py", "pattern": "AKIA[0-9A-Z]{16}", "timestamp": ts(4)},
        ]
    elif facility == "network_defense":
        fw = next((a for a in assets if a["type"] == "firewall"), assets[0])
        sw = next((a for a in assets if a["type"] == "switch"), assets[0])
        web = next((a for a in assets if a["type"] == "web_server"), assets[0])
        base_logs = [
            {"id": "log-fw-001", "type": "firewall", "device": fw["hostname"], "rule": "ANY-ANY-ALLOW", "src_zone": "any", "dst_zone": "any", "action": "allow", "timestamp": ts(1)},
            {"id": "log-fw-002", "type": "firewall", "device": fw["hostname"], "rule": "guest-to-server", "src_zone": "guest", "dst_zone": "server", "action": "allow", "timestamp": ts(2)},
            {"id": "log-ids-001", "type": "ids", "signature": "ET POLICY suspicious", "severity": "low", "count": rng.randint(500, 2000), "timestamp": ts(3)},
            {"id": "log-web-001", "type": "web_access", "device": web["hostname"], "method": "POST", "path": "/upload.php", "status": 200, "source_ip": external_ip, "timestamp": ts(4)},
            {"id": "log-vlan-001", "type": "switch", "device": sw["hostname"], "event": "trunk_misconfig", "port": "Gi0/24", "vlan": "all", "timestamp": ts(5)},
        ]
    return base_logs


def _alerts_for_facility(
    facility: str,
    rng: random.Random,
    affected_user: dict[str, Any],
    assets: list[dict[str, Any]],
    evidence_blueprint: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build correlated alerts tied to the scenario evidence blueprint."""
    workstation = next((a for a in assets if a["type"] == "windows_workstation"), assets[0])
    user_id = affected_user["id"]

    alert_map = {
        "soc": [
            {"id": "alert-001", "title": "Impossible travel followed by mailbox rule creation", "severity": "high", "source": "identity", "asset_id": workstation["id"], "user_id": user_id, "status": "open"},
            {"id": "alert-002", "title": "Suspicious email campaign detected", "severity": "medium", "source": "email", "user_id": user_id, "status": "open"},
        ],
        "enterprise": [
            {"id": "alert-001", "title": "Kerberos brute force / kerberoasting detected", "severity": "high", "source": "ad_security", "user_id": user_id, "status": "open"},
            {"id": "alert-002", "title": "Pass-the-hash lateral movement", "severity": "critical", "source": "endpoint", "asset_id": workstation["id"], "user_id": user_id, "status": "open"},
        ],
        "forensics": [
            {"id": "alert-001", "title": "Suspicious executable on workstation disk", "severity": "high", "source": "disk_forensics", "asset_id": workstation["id"], "status": "open"},
            {"id": "alert-002", "title": "Unparented process in memory dump", "severity": "high", "source": "memory_forensics", "asset_id": workstation["id"], "status": "open"},
        ],
        "malware": [
            {"id": "alert-001", "title": "Sandbox detonation: persistence and C2 beacon detected", "severity": "high", "source": "sandbox", "status": "open"},
            {"id": "alert-002", "title": "Periodic C2 beaconing from endpoint", "severity": "high", "source": "network", "asset_id": workstation["id"], "status": "open"},
        ],
        "cloud": [
            {"id": "alert-001", "title": "IAM privilege escalation: AdministratorAccess attached", "severity": "critical", "source": "cloudtrail", "user_id": user_id, "status": "open"},
            {"id": "alert-002", "title": "Public storage bucket exposure detected", "severity": "high", "source": "config", "status": "open"},
            {"id": "alert-003", "title": "Kubernetes pod with hostPath mount", "severity": "high", "source": "k8s_audit", "user_id": user_id, "status": "open"},
        ],
        "secure_coding": [
            {"id": "alert-001", "title": "SAST: SQL injection in authentication module", "severity": "high", "source": "sast", "user_id": user_id, "status": "open"},
            {"id": "alert-002", "title": "Secret scan: cloud access key in repository", "severity": "critical", "source": "secret_scan", "status": "open"},
        ],
        "network_defense": [
            {"id": "alert-001", "title": "Firewall ANY-ANY-ALLOW rule detected", "severity": "high", "source": "firewall_audit", "status": "open"},
            {"id": "alert-002", "title": "Guest VLAN reaching server zone", "severity": "high", "source": "segmentation", "status": "open"},
            {"id": "alert-003", "title": "IDS alert noise: excessive low-severity events", "severity": "medium", "source": "ids", "status": "open"},
        ],
    }
    return alert_map.get(facility, [
        {"id": "alert-001", "title": "Security alert requires triage", "severity": "medium", "source": "general", "user_id": user_id, "status": "open"}
    ])


def generate_realistic_scenario(template: dict[str, Any], seed: str) -> dict[str, Any]:
    """
    Generate a full fictional scenario for a mission template.

    The scenario includes company profile, topology, multi-asset inventory,
    multiple identities, correlated logs, alerts, evidence items, objectives,
    and safety metadata.
    """
    rng = random.Random(seed)
    rules = template.get("generation_rules", {})
    facility = rules.get("facility", "soc")
    industries = rules.get("industries") or ["manufacturing", "finance", "healthcare"]
    company_sizes = rules.get("company_sizes") or ["small", "mid_market"]

    industry = rng.choice(industries)
    company_name = f"{rng.choice(COMPANY_ROOTS)} {rng.choice(COMPANY_SUFFIXES.get(industry, ['Group']))}"
    company_domain = _domain_for_company(company_name)
    company_prefix = company_name.split(maxsplit=1)[0].lower()
    company = {
        "name": company_name,
        "industry": industry,
        "size": rng.choice(company_sizes),
        "region": rng.choice(COMPANY_REGIONS),
        "domain": company_domain,
    }

    # Identities: primary affected user + a few colleagues for realism
    affected_dept = rng.choice(DEPARTMENTS)
    affected_user = _make_identity(rng, rng.randint(21, 89), company_domain, affected_dept)
    identities = [affected_user]
    for i in range(rng.randint(2, 4)):
        identities.append(_make_identity(rng, rng.randint(100, 199), company_domain))

    # Assets tailored to facility
    assets = _assets_for_facility(facility, rng, company_prefix, affected_user["id"])

    # Topology tailored to facility
    topology_builder = TOPOLOGY_BUILDERS.get(facility, _topology_soc)
    topology = topology_builder(rng)
    topology["company"] = company_name

    # Logs and alerts
    logs = _logs_for_facility(facility, rng, affected_user, assets, template.get("evidence_blueprint", []))
    alerts = _alerts_for_facility(facility, rng, affected_user, assets, template.get("evidence_blueprint", []))

    # Evidence items from blueprint, enriched with asset/source-tool linkage
    source_tool_map = {
        "alert": "soc-dashboard",
        "log": "soc-siem",
        "email": "email-security",
        "endpoint": "endpoint-console",
        "pcap": "pcap-viewer",
        "netflow": "netflow-analyzer",
        "memory": "memory-analyzer",
        "disk": "disk-analyzer",
        "malware": "sandbox",
        "ioc": "ioc-extractor",
        "yara": "yara-editor",
        "cloud": "cloud-console",
        "iam": "iam-explorer",
        "firewall": "firewall-console",
        "ids": "ids-console",
        "code": "ide",
        "chart": "soc-dashboard",
        "map": "case-management",
        "timeline": "timeline-builder",
        "browser": "browser-forensics",
        "cookie": "cookie-viewer",
        "custody": "case-management",
        "intel": "soc-siem",
        "url": "url-analyzer",
        "backup": "backup-console",
        "repo": "repo-audit-tool",
    }
    evidence = []
    for item in template.get("evidence_blueprint", []):
        ev_type = item.get("type", "log")
        evidence.append({
            **item,
            "id": f"ev-{item['key']}",
            "source_tool": source_tool_map.get(ev_type, "case-management"),
            "source_asset_id": assets[0]["id"] if assets else "asset-001",
            "fictional": True,
            "collected": False,
        })

    return {
        "company_profile": company,
        "topology": topology,
        "assets": assets,
        "identities": identities,
        "logs": logs,
        "alerts": alerts,
        "evidence": evidence,
        "objectives": template.get("objectives", []),
        "safety_metadata": {
            "fictional_only": True,
            "uses_reserved_domains": True,
            "contains_real_malware": False,
            "targets_public_internet": False,
        },
    }
