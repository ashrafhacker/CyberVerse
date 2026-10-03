from __future__ import annotations

import hashlib
import ipaddress
import random
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import GameHighScore, GameIndustryTemplate, GameSession, GameStatus
from app.models.user import User


class GameSafetyError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Static catalogs — device types, industry templates, difficulty configs
# ---------------------------------------------------------------------------

DEVICE_CATALOG: dict[str, dict[str, Any]] = {
    "firewall": {
        "label": "Firewall",
        "services": ["iptables", "dnsmasq"],
        "ports": [22, 443, 8443],
        "weaknesses": ["overly permissive rule set", "management interface on WAN", "default admin password"],
        "defense_actions": ["review_rules", "restrict_management", "enable_logging"],
        "segment": "edge",
    },
    "router": {
        "label": "Router",
        "services": ["SSH", "SNMP", "BGP"],
        "ports": [22, 161, 179],
        "weaknesses": ["SNMP v2c community string", "weak SSH ciphers", "no ACL on VTY lines"],
        "defense_actions": ["upgrade_snmpv3", "harden_ssh", "apply_vty_acl"],
        "segment": "edge",
    },
    "switch": {
        "label": "Switch",
        "services": ["SSH", "CDP", "STP"],
        "ports": [22, 80, 161],
        "weaknesses": ["CDP broadcast enabled", "VLAN hopping risk", "spanning-tree not hardened"],
        "defense_actions": ["disable_cdp", "protect_stp", "enable_port_security"],
        "segment": "edge",
    },
    "ad": {
        "label": "Active Directory",
        "services": ["LDAP", "Kerberos", "SMB"],
        "ports": [389, 636, 445, 88],
        "weaknesses": ["Kerberoasting exposure", "no LAPS on workstations", "excessive Domain Admin count"],
        "defense_actions": ["enable_laps", "reduce_da_count", "set_kerberos_aes"],
        "segment": "core",
    },
    "linux_server": {
        "label": "Linux Server",
        "services": ["SSH", "HTTPd", "PostgreSQL"],
        "ports": [22, 80, 443, 5432],
        "weaknesses": ["password auth on SSH", "outdated OpenSSL", "world-readable /etc/shadow"],
        "defense_actions": ["disable_password_auth", "update_packages", "fix_permissions"],
        "segment": "internal",
    },
    "windows_server": {
        "label": "Windows Server",
        "services": ["RDP", "SMB", "WinRM"],
        "ports": [3389, 445, 5985],
        "weaknesses": ["SMBv1 enabled", "RDP exposed externally", "missing security patches"],
        "defense_actions": ["disable_smbv1", "restrict_rdp", "apply_patches"],
        "segment": "internal",
    },
    "dns": {
        "label": "DNS Server",
        "services": ["DNS", "mDNS"],
        "ports": [53, 5353],
        "weaknesses": ["open recursive resolution", "no DNSSEC", "zone transfer allowed"],
        "defense_actions": ["restrict_recursion", "enable_dnssec", "block_zone_transfer"],
        "segment": "edge",
    },
    "dhcp": {
        "label": "DHCP Server",
        "services": ["DHCP", "BOOTP"],
        "ports": [67, 68],
        "weaknesses": ["no DHCP snooping", "rogue DHCP possibility", "no NAC enforcement"],
        "defense_actions": ["enable_snooping", "deploy_nac", "isolate_subnet"],
        "segment": "internal",
    },
    "web_server": {
        "label": "Web Server",
        "services": ["HTTP", "HTTPS", "HTTP/2"],
        "ports": [80, 443, 8080, 8443],
        "weaknesses": ["outdated Apache Struts (CVE-2017-5638)", "weak TLS 1.0", "directory listing enabled"],
        "defense_actions": ["patch_struts", "enforce_tls13", "disable_listing"],
        "segment": "dmz",
    },
    "database": {
        "label": "Database",
        "services": ["MySQL", "PostgreSQL", "MSSQL"],
        "ports": [3306, 5432, 1433],
        "weaknesses": ["default credentials", "no encryption at rest", "excessive user privileges"],
        "defense_actions": ["rotate_credentials", "enable_tde", "least_privilege"],
        "segment": "core",
    },
    "email_server": {
        "label": "Email Server",
        "services": ["SMTP", "IMAP", "POP3"],
        "ports": [25, 587, 993],
        "weaknesses": ["no SPF/DKIM/DMARC", "weak TLS 1.0 cipher", "open relay misconfiguration"],
        "defense_actions": ["configure_dmarc", "harden_tls", "close_relay"],
        "segment": "dmz",
    },
    "vpn": {
        "label": "VPN Gateway",
        "services": ["IPsec", "OpenVPN", "WireGuard"],
        "ports": [500, 1194, 51820],
        "weaknesses": ["weak PSK", "no MFA", "split-tunnel enabled"],
        "defense_actions": ["rotate_psk", "enforce_mfa", "disable_split_tunnel"],
        "segment": "edge",
    },
    "siem": {
        "label": "SIEM",
        "services": ["Elasticsearch", "Kibana", "Logstash"],
        "ports": [9200, 5601, 5044],
        "weaknesses": ["default Elasticsearch auth", "no TLS on ingest", "uncorrelated alerts"],
        "defense_actions": ["enable_rbac", "enforce_tls", "add_correlation_rules"],
        "segment": "core",
    },
    "cloud": {
        "label": "Cloud Resource",
        "services": ["S3 API", "EC2 Metadata", "Lambda"],
        "ports": [443, 8443],
        "weaknesses": ["public S3 bucket", "overly permissive IAM role", "no VPC flow logs"],
        "defense_actions": ["make_private", "least_privilege_iam", "enable_flow_logs"],
        "segment": "cloud",
    },
    "iot": {
        "label": "IoT Device",
        "services": ["MQTT", "Telnet", "HTTP"],
        "ports": [1883, 23, 80],
        "weaknesses": ["default credentials", "firmware outdated", "no network isolation"],
        "defense_actions": ["rotate_credentials", "update_firmware", "isolate_vlan"],
        "segment": "iot",
    },
    "wireless_ap": {
        "label": "Wireless AP",
        "services": ["WiFi", "RADIUS"],
        "ports": [1812, 1813],
        "weaknesses": ["WPA2-PSK only", "no WPA3", "rogue AP risk"],
        "defense_actions": ["enable_wpa3", "enable_8021x", "scan_rogues"],
        "segment": "edge",
    },
    "backup": {
        "label": "Backup System",
        "services": ["rsync", "Borg", "Bacula"],
        "ports": [22, 873, 9102],
        "weaknesses": ["rsync no access list", "no encryption", "no 3-2-1 rule"],
        "defense_actions": ["apply_acl", "enable_encryption", "implement_321"],
        "segment": "core",
    },
    "monitoring": {
        "label": "Monitoring System",
        "services": ["SNMP", "ICMP", "NRPE"],
        "ports": [161, 5666, 443],
        "weaknesses": ["SNMP community public", "no auth on NRPE", "exposed dashboard"],
        "defense_actions": ["secure_snmpv3", "enable_nrpe_ssl", "restrict_dashboard"],
        "segment": "internal",
    },
}

INDUSTRY_TEMPLATES: list[dict[str, Any]] = [
    {
        "slug": "bank",
        "name": "Bank",
        "description": "High-security financial institution with core banking systems.",
        "icon": "Landmark",
        "min_level": 3,
        "departments": ["Retail Banking", "Investments", "Compliance", "IT Security", "Customer Service"],
        "device_mix": ["firewall", "router", "switch", "ad", "database", "web_server", "email_server", "vpn", "siem", "backup", "monitoring", "cloud"],
        "alert_profile": {"impossible_travel": 0.8, "data_exfiltration": 0.6, "phishing_click": 0.5, "malware_detection": 0.3},
    },
    {
        "slug": "hospital",
        "name": "Hospital",
        "description": "Healthcare network with medical devices, EHR systems, and IoT.",
        "icon": "HeartPulse",
        "min_level": 2,
        "departments": ["Emergency", "Radiology", "Pharmacy", "IT", "Administration"],
        "device_mix": ["firewall", "router", "switch", "ad", "database", "web_server", "iot", "wireless_ap", "backup", "monitoring"],
        "alert_profile": {"iot_anomaly": 0.7, "ransomware": 0.5, "impossible_travel": 0.4, "phishing_click": 0.3},
    },
    {
        "slug": "airport",
        "name": "Airport",
        "description": "Critical infrastructure with flight systems, passenger WiFi, and SCADA.",
        "icon": "Plane",
        "min_level": 4,
        "departments": ["Operations", "Security", "IT", "Maintenance", "Retail"],
        "device_mix": ["firewall", "router", "switch", "ad", "database", "web_server", "vpn", "wireless_ap", "iot", "siem", "monitoring"],
        "alert_profile": {"scada_anomaly": 0.6, "rogue_ap": 0.5, "impossible_travel": 0.4, "data_exfiltration": 0.3},
    },
    {
        "slug": "school",
        "name": "School",
        "description": "Educational campus with student labs, faculty network, and library systems.",
        "icon": "GraduationCap",
        "min_level": 1,
        "departments": ["Faculty", "Student IT", "Library", "Administration"],
        "device_mix": ["router", "switch", "ad", "linux_server", "web_server", "database", "wireless_ap", "monitoring"],
        "alert_profile": {"phishing_click": 0.6, "malware_detection": 0.4, "impossible_travel": 0.2},
    },
    {
        "slug": "military",
        "name": "Military Base",
        "description": "Defense facility with air-gapped networks and strict compliance.",
        "icon": "Shield",
        "min_level": 5,
        "departments": ["Command", "Intel", "IT Security", "Logistics"],
        "device_mix": ["firewall", "router", "switch", "ad", "database", "siem", "vpn", "backup", "monitoring"],
        "alert_profile": {"data_exfiltration": 0.7, "impossible_travel": 0.6, "lateral_movement": 0.5},
    },
    {
        "slug": "cloud_datacenter",
        "name": "Cloud Data Center",
        "description": "Hyperscale cloud provider with multi-tenant infrastructure.",
        "icon": "Cloud",
        "min_level": 4,
        "departments": ["DevOps", "SRE", "Security", "Network Engineering"],
        "device_mix": ["firewall", "router", "switch", "linux_server", "database", "web_server", "cloud", "siem", "backup", "monitoring"],
        "alert_profile": {"iam_abuse": 0.6, "container_escape": 0.4, "data_exfiltration": 0.5, "impossible_travel": 0.3},
    },
    {
        "slug": "isp",
        "name": "ISP",
        "description": "Internet Service Provider with BGP backbone and customer access.",
        "icon": "Globe",
        "min_level": 4,
        "departments": ["Network Operations", "Customer Support", "Abuse", "Engineering"],
        "device_mix": ["router", "switch", "dns", "dhcp", "web_server", "email_server", "vpn", "monitoring", "siem"],
        "alert_profile": {"ddos": 0.6, "dns_amplification": 0.4, "bgp_hijack": 0.3, "data_exfiltration": 0.2},
    },
    {
        "slug": "factory",
        "name": "Smart Factory",
        "description": "Manufacturing facility with OT/IT convergence and IIoT devices.",
        "icon": "Factory",
        "min_level": 3,
        "departments": ["Production", "Quality", "Maintenance", "IT Security"],
        "device_mix": ["firewall", "router", "switch", "linux_server", "database", "iot", "monitoring", "backup", "wireless_ap"],
        "alert_profile": {"scada_anomaly": 0.6, "iot_anomaly": 0.5, "malware_detection": 0.4, "ransomware": 0.3},
    },
    {
        "slug": "soc",
        "name": "SOC Center",
        "description": "Security Operations Center with full defensive toolkit.",
        "icon": "ShieldCheck",
        "min_level": 2,
        "departments": ["Tier 1 Analysts", "Tier 2 Analysts", "Threat Hunting", "Incident Response", "Engineering"],
        "device_mix": ["firewall", "router", "siem", "linux_server", "windows_server", "monitoring", "backup", "vpn", "ad"],
        "alert_profile": {"impossible_travel": 0.5, "lateral_movement": 0.5, "malware_detection": 0.4, "data_exfiltration": 0.3},
    },
    {
        "slug": "university",
        "name": "University",
        "description": "Academic institution with research labs and open network culture.",
        "icon": "BookOpen",
        "min_level": 1,
        "departments": ["Computer Science", "Research", "IT", "Administration", "Library"],
        "device_mix": ["router", "switch", "ad", "linux_server", "database", "web_server", "dns", "dhcp", "wireless_ap", "backup", "monitoring"],
        "alert_profile": {"phishing_click": 0.5, "malware_detection": 0.3, "impossible_travel": 0.2, "rogue_ap": 0.2},
    },
]

COMPANY_ROOTS = ["Northstar", "Blue Harbor", "Summit Vale", "Copperline", "Aster Ridge", "Granite Peak", "Meridian", "Silverwood"]
COMPANY_SUFFIXES = ["Industries", "Group", "Holdings", "Systems", "Networks", "Solutions", "Technologies"]
EMPLOYEE_NAMES = ["Maya Chen", "Jordan Ellis", "Rina Patel", "Owen Brooks", "Sara Khan", "Dev Arora", "Lena Volkov", "Marcus Webb", "Priya Rao", "Ethan Cole"]
ROLES = ["Finance Manager", "HR Coordinator", "Operations Lead", "Software Engineer", "System Administrator", "Security Analyst"]
COMPANY_SIZES = ["startup", "smb", "enterprise", "multinational"]

DIFFICULTY_CONFIG: dict[str, dict[str, Any]] = {
    "beginner": {"energy": 14, "hint_level": "full", "detection_rate": 0.1, "time_limit": 120, "min_security": 1, "max_security": 3},
    "intermediate": {"energy": 12, "hint_level": "partial", "detection_rate": 0.25, "time_limit": 90, "min_security": 2, "max_security": 4},
    "advanced": {"energy": 10, "hint_level": "minimal", "detection_rate": 0.4, "time_limit": 75, "min_security": 3, "max_security": 5},
    "expert": {"energy": 8, "hint_level": "none", "detection_rate": 0.55, "time_limit": 60, "min_security": 3, "max_security": 5},
}

ACTION_COST: dict[str, int] = {
    "scan": 1,
    "exploit": 2,
    "pivot": 2,
    "defend": 1,
    "harden": 2,
    "investigate": 1,
    "patch": 2,
    "contain": 3,
    "report": 0,
}

ACTION_REWARDS: dict[str, int] = {
    "scan": 10,
    "exploit": 50,
    "pivot": 30,
    "defend": 15,
    "harden": 40,
    "investigate": 20,
    "patch": 35,
    "contain": 60,
    "report": 25,
}

ALERT_TEMPLATES = [
    {"key": "impossible_travel", "title": "Impossible travel sign-in detected", "severity": "high", "source": "identity"},
    {"key": "data_exfiltration", "title": "Large data transfer to external host", "severity": "critical", "source": "network"},
    {"key": "phishing_click", "title": "User clicked suspected phishing link", "severity": "medium", "source": "email"},
    {"key": "malware_detection", "title": "EDR flagged suspicious process execution", "severity": "high", "source": "endpoint"},
    {"key": "lateral_movement", "title": "Suspicious SMB scanning between hosts", "severity": "high", "source": "network"},
    {"key": "iot_anomaly", "title": "IoT device communicating with unknown C2", "severity": "critical", "source": "iot"},
    {"key": "scada_anomaly", "title": "SCADA system command outside normal hours", "severity": "critical", "source": "ot"},
    {"key": "rogue_ap", "title": "Rogue wireless access point detected", "severity": "medium", "source": "wireless"},
    {"key": "ddos", "title": "Volumetric DDoS attack in progress", "severity": "high", "source": "network"},
    {"key": "iam_abuse", "title": "IAM role used from unexpected region", "severity": "high", "source": "cloud"},
    {"key": "container_escape", "title": "Potential container escape detected", "severity": "critical", "source": "cloud"},
    {"key": "bgp_hijack", "title": "BGP prefix hijack suspected", "severity": "critical", "source": "network"},
    {"key": "dns_amplification", "title": "DNS amplification attack detected", "severity": "high", "source": "dns"},
    {"key": "ransomware", "title": "Mass file encryption activity detected", "severity": "critical", "source": "endpoint"},
]

BUSINESS_EVENT_TEMPLATES = [
    {"type": "employee_login", "description": "Employee {name} logged in from {ip}"},
    {"type": "software_update", "description": "Security patch deployed on {hostname}"},
    {"type": "email_traffic", "description": "Bulk email campaign sent from marketing"},
    {"type": "service_outage", "description": "Service {service} temporarily unavailable"},
    {"type": "maintenance_window", "description": "Scheduled maintenance on {hostname}"},
    {"type": "help_desk", "description": "Ticket opened: {description}"},
    {"type": "new_hire", "description": "New employee {name} onboarded in {department}"},
    {"type": "policy_change", "description": "Security policy updated: {description}"},
]

AI_ANALYSTS = [
    {"id": "analyst-1", "name": "ARIA", "role": "SOC Tier 1 Analyst", "status": "available"},
    {"id": "analyst-2", "name": "VEX", "role": "SOC Tier 2 Analyst", "status": "available"},
    {"id": "analyst-3", "name": "ORION", "role": "Threat Hunter", "status": "available"},
    {"id": "analyst-4", "name": "NOVA", "role": "Incident Responder", "status": "available"},
    {"id": "analyst-5", "name": "ECHO", "role": "Cloud Security Engineer", "status": "available"},
]


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class GameService:
    GENERATOR_VERSION = "enterprise-v1"

    # ------------------------------------------------------------------
    # Seed / setup helpers
    # ------------------------------------------------------------------

    @classmethod
    def make_seed(cls, user_id: UUID, industry: str, difficulty: str) -> str:
        digest = hashlib.sha256(f"{user_id}:{industry}:{difficulty}:{uuid4()}".encode()).hexdigest()[:8].upper()
        return f"cv-{industry[:12]}-{digest}"

    @classmethod
    async def ensure_default_content(cls, db: AsyncSession) -> None:
        result = await db.execute(select(GameIndustryTemplate).limit(1))
        if result.scalar_one_or_none():
            return
        for tmpl in INDUSTRY_TEMPLATES:
            db.add(GameIndustryTemplate(
                slug=tmpl["slug"],
                name=tmpl["name"],
                description=tmpl["description"],
                device_mix=tmpl["device_mix"],
                departments=tmpl["departments"],
                alert_profile=tmpl["alert_profile"],
                icon=tmpl.get("icon"),
                min_level=tmpl.get("min_level", 1),
            ))
        await db.commit()

    # ------------------------------------------------------------------
    # Enterprise generation
    # ------------------------------------------------------------------

    @classmethod
    def generate_enterprise(cls, seed: str, industry: str, difficulty: str, level: int = 1) -> dict[str, Any]:
        rng = random.Random(seed)
        tmpl = next((t for t in INDUSTRY_TEMPLATES if t["slug"] == industry), INDUSTRY_TEMPLATES[0])
        diff_cfg = DIFFICULTY_CONFIG.get(difficulty, DIFFICULTY_CONFIG["beginner"])

        company_name = f"{rng.choice(COMPANY_ROOTS)} {rng.choice(COMPANY_SUFFIXES)}"
        company_size = rng.choice(COMPANY_SIZES)
        departments = list(tmpl["departments"])
        num_employees = {"startup": rng.randint(8, 25), "smb": rng.randint(50, 150), "enterprise": rng.randint(500, 2000), "multinational": rng.randint(5000, 25000)}[company_size]

        # Build employees
        employees = []
        for i in range(min(num_employees, rng.randint(5, 12))):
            employees.append({
                "id": f"emp-{i+1:03d}",
                "display_name": rng.choice(EMPLOYEE_NAMES),
                "role": rng.choice(ROLES),
                "department": rng.choice(departments),
                "email": f"emp{i+1:03d}@{company_name.lower().replace(' ', '-')}.cyberverse.test",
            })

        # Build network nodes
        segments = ["dmz", "edge", "internal", "core", "cloud", "iot"]
        device_mix = tmpl["device_mix"]
        min_sec = diff_cfg["min_security"]
        max_sec = diff_cfg["max_security"]
        base_node_count = min(len(device_mix) + level, 18)
        chosen_types = device_mix[:base_node_count] if len(device_mix) >= base_node_count else device_mix + ["linux_server"] * (base_node_count - len(device_mix))

        nodes: list[dict[str, Any]] = []
        used_ips: set[str] = set()
        for i, dtype in enumerate(chosen_types):
            catalog = DEVICE_CATALOG[dtype]
            segment = catalog["segment"]
            ip = cls._generate_ip(rng, segment, i, used_ips)
            used_ips.add(ip)
            hostname = f"{company_name.split(maxsplit=1)[0].lower()}-{dtype[:3]}-{i+1:02d}"
            weakness = rng.choice(catalog["weaknesses"])
            nodes.append({
                "id": f"node-{i+1:02d}",
                "name": hostname,
                "device_type": dtype,
                "label": catalog["label"],
                "segment": segment,
                "services": catalog["services"],
                "ports": catalog["ports"],
                "weakness": weakness,
                "weaknesses": catalog["weaknesses"],
                "defense_actions": catalog["defense_actions"],
                "security": rng.randint(min_sec, max_sec),
                "ip_address": ip,
                "status": "hidden",
                "config": cls._generate_config(rng, dtype, company_name),
                "logs": cls._generate_logs(rng, dtype, weakness),
                "department": rng.choice(departments),
                "hardened": False,
                "compromised": False,
                "investigated": False,
            })

        # Build links between nodes based on segments
        links = cls._build_links(nodes, rng)

        # Generate alerts based on industry profile
        alerts = cls._generate_alerts(rng, tmpl["alert_profile"], nodes, employees, difficulty)

        # Generate business events
        business_events = cls._generate_business_events(rng, nodes, employees, num_employees)

        # Generate objectives based on game mode
        objectives = cls._generate_objectives(rng, industry, difficulty, nodes, alerts)

        company_profile = {
            "name": company_name,
            "industry": tmpl["name"],
            "size": company_size,
            "departments": departments,
            "employees": employees,
            "employee_count": num_employees,
            "region": "fictional-us-east",
        }

        topology = {
            "segments": segments,
            "sites": ["headquarters", "branch-office", "cloud-tenant"] if company_size in ("enterprise", "multinational") else ["headquarters"],
            "edges": [["dmz", "edge"], ["edge", "internal"], ["internal", "core"], ["internal", "cloud"], ["edge", "iot"]],
        }

        return {
            "company_profile": company_profile,
            "topology": topology,
            "nodes": nodes,
            "links": links,
            "alerts": alerts,
            "business_events": business_events,
            "objectives": objectives,
            "defense_state": {
                "hardened_nodes": [],
                "contained_nodes": [],
                "patched_nodes": [],
                "investigated_nodes": [],
                "resolved_alerts": [],
            },
            "world_events": [],
            "energy": diff_cfg["energy"],
            "safety_metadata": {
                "fictional_only": True,
                "uses_reserved_domains": True,
                "contains_real_malware": False,
                "targets_public_internet": False,
                "generator_version": cls.GENERATOR_VERSION,
            },
        }

    @classmethod
    def generate_soc_scenario(cls, seed: str, difficulty: str, level: int = 1) -> dict[str, Any]:
        enterprise = cls.generate_enterprise(seed, "soc", difficulty, level)
        enterprise["ai_analysts"] = list(AI_ANALYSTS)
        enterprise["incident_queue"] = [a for a in enterprise["alerts"] if a["severity"] in ("high", "critical")]
        enterprise["objectives"] = cls._generate_soc_objectives(seed, enterprise["alerts"], enterprise["nodes"])
        return enterprise

    @classmethod
    def generate_random_enterprise(cls, difficulty: str = "beginner", game_mode: str = "offensive") -> dict[str, Any]:
        seed = f"cv-random-{uuid4().hex[:8].upper()}"
        industry = random.choice(INDUSTRY_TEMPLATES)["slug"]
        if game_mode == "soc":
            data = cls.generate_soc_scenario(seed, difficulty)
        else:
            data = cls.generate_enterprise(seed, industry, difficulty)
        data["scenario_seed"] = seed
        data["industry"] = industry
        data["game_mode"] = game_mode
        data["difficulty"] = difficulty
        return data

    # ------------------------------------------------------------------
    # IP / config / log / link / alert / event / objective generators
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_ip(rng: random.Random, segment: str, index: int, used: set[str]) -> str:
        ranges = {
            "dmz": (10, 10),
            "edge": (10, 20),
            "internal": (172, 16),
            "core": (172, 24),
            "cloud": (192, 168),
            "iot": (192, 168),
        }
        first, second = ranges.get(segment, (10, 10))
        while True:
            ip = f"{first}.{second + (index % 5)}.{rng.randint(0, 20)}.{rng.randint(10, 250)}"
            if ip not in used:
                return ip

    @staticmethod
    def _generate_config(rng: random.Random, dtype: str, company: str) -> dict[str, Any]:
        return {
            "os": rng.choice(["Ubuntu 22.04 LTS", "Windows Server 2019", "Debian 12", "RHEL 9", "Cisco IOS-XE"]) if dtype in ("router", "switch", "firewall") else rng.choice(["Ubuntu 22.04 LTS", "Windows Server 2019", "CentOS 8"]),
            "uptime": f"{rng.randint(1, 365)}d {rng.randint(0, 23)}h",
            "last_patch": f"{rng.randint(1, 90)} days ago",
            "open_services": rng.randint(2, 6),
        }

    @staticmethod
    def _generate_logs(rng: random.Random, dtype: str, weakness: str) -> list[dict[str, Any]]:
        logs = []
        for i in range(rng.randint(3, 7)):
            logs.append({
                "id": f"log-{dtype}-{i+1}",
                "timestamp": f"2026-08-{rng.randint(1,7)}T{rng.randint(0,23):02d}:{rng.randint(0,59):02d}:{rng.randint(0,59):02d}Z",
                "level": rng.choice(["INFO", "WARN", "ERROR"]),
                "message": rng.choice([
                    f"Authentication attempt from 10.0.{rng.randint(1,10)}.{rng.randint(10,200)}",
                    f"Service {rng.choice(['ssh','http','dns','smb'])} responded normally",
                    f"Config change detected: {weakness}",
                    f"Connection from {rng.randint(10,200)}.{rng.randint(10,200)}.{rng.randint(10,200)}.{rng.randint(10,200)}",
                    "Scheduled backup completed",
                    "Health check passed",
                ]),
            })
        return logs

    @staticmethod
    def _build_links(nodes: list[dict[str, Any]], rng: random.Random) -> list[dict[str, str]]:
        segment_order = {"dmz": 0, "edge": 1, "internal": 2, "core": 3, "cloud": 4, "iot": 4}
        links: list[dict[str, str]] = []
        connected = {nodes[0]["id"]} if nodes else set()
        for node in nodes[1:]:
            candidates = [n for n in nodes if n["id"] in connected and segment_order.get(n["segment"], 99) <= segment_order.get(node["segment"], 99)]
            if not candidates:
                candidates = [n for n in nodes if n["id"] in connected]
            if candidates:
                source = rng.choice(candidates)
                links.append({"from": source["id"], "to": node["id"]})
                connected.add(node["id"])
        # Ensure core nodes are connected to internal
        core_nodes = [n for n in nodes if n["segment"] == "core"]
        internal_nodes = [n for n in nodes if n["segment"] == "internal"]
        for core in core_nodes:
            if not any(l["to"] == core["id"] or l["from"] == core["id"] for l in links) and internal_nodes:
                src = rng.choice(internal_nodes)
                links.append({"from": src["id"], "to": core["id"]})
        return links

    @staticmethod
    def _generate_alerts(rng: random.Random, alert_profile: dict[str, float], nodes: list[dict[str, Any]], employees: list[dict[str, Any]], difficulty: str) -> list[dict[str, Any]]:
        diff_cfg = DIFFICULTY_CONFIG.get(difficulty, DIFFICULTY_CONFIG["beginner"])
        detection_rate = diff_cfg["detection_rate"]
        alerts: list[dict[str, Any]] = []
        for alert_key, probability in alert_profile.items():
            if rng.random() < probability:
                tmpl = next((t for t in ALERT_TEMPLATES if t["key"] == alert_key), ALERT_TEMPLATES[0])
                asset = rng.choice(nodes) if nodes else None
                user = rng.choice(employees) if employees else None
                alerts.append({
                    "id": f"alert-{len(alerts)+1:03d}",
                    "key": alert_key,
                    "title": tmpl["title"],
                    "severity": tmpl["severity"],
                    "source": tmpl["source"],
                    "asset_id": asset["id"] if asset else None,
                    "asset_name": asset["name"] if asset else None,
                    "user_id": user["id"] if user else None,
                    "user_name": user["display_name"] if user else None,
                    "status": "open",
                    "detected": rng.random() < detection_rate,
                    "timestamp": datetime.now(UTC).isoformat(),
                })
        return alerts

    @staticmethod
    def _generate_business_events(rng: random.Random, nodes: list[dict[str, Any]], employees: list[dict[str, Any]], total_employees: int) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for _ in range(rng.randint(4, 8)):
            tmpl = rng.choice(BUSINESS_EVENT_TEMPLATES)
            node = rng.choice(nodes) if nodes else None
            emp = rng.choice(employees) if employees else None
            desc = tmpl["description"].format(
                name=emp["display_name"] if emp else "Unknown",
                ip=f"10.{rng.randint(1,40)}.{rng.randint(0,10)}.{rng.randint(20,220)}",
                hostname=node["name"] if node else "unknown-host",
                service=rng.choice(["HTTP", "DNS", "SMTP", "VPN"]),
                description=rng.choice(["VPN access requested", "Password reset needed", "New software install", "Suspicious email report"]),
                department=emp["department"] if emp else "IT",
            )
            events.append({
                "id": f"event-{len(events)+1:03d}",
                "type": tmpl["type"],
                "description": desc,
                "timestamp": datetime.now(UTC).isoformat(),
                "affected_assets": [node["id"]] if node and rng.random() < 0.5 else [],
            })
        return events

    @staticmethod
    def _generate_objectives(rng: random.Random, industry: str, difficulty: str, nodes: list[dict[str, Any]], alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        objectives: list[dict[str, Any]] = []
        # Always include recon
        objectives.append({
            "id": "obj-recon",
            "title": "Network Reconnaissance",
            "description": "Scan at least 3 nodes to map the network topology.",
            "type": "scan",
            "target_count": 3,
            "xp": 50,
            "completed": False,
        })
        # Exploitation or hardening
        if difficulty in ("beginner", "intermediate"):
            objectives.append({
                "id": "obj-exploit-edge",
                "title": "Compromise Edge Devices",
                "description": "Exploit at least 2 edge/DMZ nodes.",
                "type": "exploit",
                "target_count": 2,
                "xp": 100,
                "completed": False,
            })
        # Alert triage
        if alerts:
            objectives.append({
                "id": "obj-alerts",
                "title": "Investigate Security Alerts",
                "description": f"Investigate {min(len(alerts), 3)} of {len(alerts)} open alerts.",
                "type": "investigate",
                "target_count": min(len(alerts), 3),
                "xp": 80,
                "completed": False,
            })
        # Hardening
        objectives.append({
            "id": "obj-harden",
            "title": "Harden Critical Systems",
            "description": "Apply hardening to at least 2 core/internal systems.",
            "type": "harden",
            "target_count": 2,
            "xp": 90,
            "completed": False,
        })
        # Report
        objectives.append({
            "id": "obj-report",
            "title": "Submit Final Report",
            "description": "Complete and submit your assessment report.",
            "type": "report",
            "target_count": 1,
            "xp": 60,
            "completed": False,
        })
        return objectives

    @staticmethod
    def _generate_soc_objectives(seed: str, alerts: list[dict[str, Any]], nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rng = random.Random(seed + "-soc")
        objectives: list[dict[str, Any]] = [
            {
                "id": "obj-triage",
                "title": "Triage Incoming Alerts",
                "description": f"Review and triage {min(len(alerts), 3)} alerts from the queue.",
                "type": "investigate",
                "target_count": min(len(alerts), 3),
                "xp": 80,
                "completed": False,
            },
            {
                "id": "obj-contain",
                "title": "Contain Active Incidents",
                "description": "Contain at least 2 compromised systems.",
                "type": "contain",
                "target_count": 2,
                "xp": 120,
                "completed": False,
            },
            {
                "id": "obj-harden-soc",
                "title": "Harden Defenses",
                "description": "Apply hardening to at least 3 systems.",
                "type": "harden",
                "target_count": 3,
                "xp": 100,
                "completed": False,
            },
            {
                "id": "obj-patch",
                "title": "Apply Security Patches",
                "description": "Patch at least 2 vulnerable systems.",
                "type": "patch",
                "target_count": 2,
                "xp": 80,
                "completed": False,
            },
            {
                "id": "obj-soc-report",
                "title": "Produce Executive Report",
                "description": "Generate an executive incident report.",
                "type": "report",
                "target_count": 1,
                "xp": 70,
                "completed": False,
            },
        ]
        return objectives

    # ------------------------------------------------------------------
    # Action application
    # ------------------------------------------------------------------

    @classmethod
    def apply_action(cls, state: dict[str, Any], node_id: str, action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        nodes: list[dict[str, Any]] = state.get("nodes", [])
        node = next((n for n in nodes if n["id"] == node_id), None)
        if not node:
            return {"message": "[x] node not found", "state": state, "score_delta": 0}

        cost = ACTION_COST.get(action, 1)
        energy = state.get("energy_remaining", state.get("energy", 10))
        if energy < cost:
            return {"message": "[x] insufficient energy", "state": state, "score_delta": 0}

        reward = ACTION_REWARDS.get(action, 0)
        rng = random.Random()

        if action == "scan":
            return cls._action_scan(state, node, cost, reward)
        if action == "exploit":
            return cls._action_exploit(state, node, cost, reward, rng)
        if action == "pivot":
            return cls._action_pivot(state, node, cost, reward, rng)
        if action == "defend":
            return cls._action_defend(state, node, cost, reward)
        if action == "harden":
            return cls._action_harden(state, node, cost, reward)
        if action == "investigate":
            return cls._action_investigate(state, node, cost, reward)
        if action == "patch":
            return cls._action_patch(state, node, cost, reward)
        if action == "contain":
            return cls._action_contain(state, node, cost, reward)
        if action == "report":
            return cls._action_report(state, node, cost, reward)
        return {"message": f"[x] unknown action: {action}", "state": state, "score_delta": 0}

    @staticmethod
    def _action_scan(state: dict[str, Any], node: dict[str, Any], cost: int, reward: int) -> dict[str, Any]:
        if node["status"] in ("scanned", "accessed", "compromised", "hardened", "defended"):
            return {"message": f"[i] {node['name']} already scanned", "state": state, "score_delta": 0, "energy_cost": 0}
        node["status"] = "scanned"
        state["nodes"] = [n if n["id"] != node["id"] else node for n in state["nodes"]]
        state["energy_remaining"] = state.get("energy_remaining", state.get("energy", 10)) - cost
        state["score"] = state.get("score", 0) + reward
        msg = f"[+] scan {node['name']}: {node['label']} | services: {', '.join(node['services'])} | ports: {', '.join(str(p) for p in node['ports'])} | weakness: {node['weakness']}"
        return {"message": msg, "state": state, "score_delta": reward, "energy_cost": cost}

    @staticmethod
    def _action_exploit(state: dict[str, Any], node: dict[str, Any], cost: int, reward: int, rng: random.Random) -> dict[str, Any]:
        if node["status"] != "scanned":
            return {"message": f"[i] scan {node['name']} first", "state": state, "score_delta": 0, "energy_cost": 0}
        if node.get("hardened"):
            return {"message": f"[x] {node['name']} is hardened — exploit blocked", "state": state, "score_delta": 0, "energy_cost": 0}
        chance = max(0.25, 0.95 - node["security"] * 0.12)
        if rng.random() < chance:
            node["status"] = "compromised"
            node["compromised"] = True
            state["nodes"] = [n if n["id"] != node["id"] else node for n in state["nodes"]]
            state["energy_remaining"] = state.get("energy_remaining", state.get("energy", 10)) - cost
            state["score"] = state.get("score", 0) + reward + node["security"] * 10
            msg = f"[!] access granted to {node['name']} — {node['weakness']} exploited"
            # Generate new alert
            state.setdefault("alerts", []).append({
                "id": f"alert-exploit-{node['id']}",
                "key": "lateral_movement",
                "title": f"Compromise detected on {node['name']}",
                "severity": "high",
                "source": "network",
                "asset_id": node["id"],
                "asset_name": node["name"],
                "status": "open",
                "detected": rng.random() < 0.4,
                "timestamp": datetime.now(UTC).isoformat(),
            })
            return {"message": msg, "state": state, "score_delta": reward + node["security"] * 10, "energy_cost": cost}
        state["energy_remaining"] = state.get("energy_remaining", state.get("energy", 10)) - cost
        msg = f"[x] exploit failed on {node['name']} — firewall blocked the payload"
        return {"message": msg, "state": state, "score_delta": 0, "energy_cost": cost}

    @staticmethod
    def _action_pivot(state: dict[str, Any], node: dict[str, Any], cost: int, reward: int, rng: random.Random) -> dict[str, Any]:
        if not node.get("compromised"):
            return {"message": f"[i] {node['name']} must be compromised first to pivot", "state": state, "score_delta": 0, "energy_cost": 0}
        links: list[dict[str, str]] = state.get("links", [])
        connected_ids = {l["to"] for l in links if l["from"] == node["id"]} | {l["from"] for l in links if l["to"] == node["id"]}
        pivot_targets = [n for n in state["nodes"] if n["id"] in connected_ids and n["status"] == "hidden"]
        if not pivot_targets:
            return {"message": f"[i] no hidden nodes adjacent to {node['name']}", "state": state, "score_delta": 0, "energy_cost": 0}
        target = rng.choice(pivot_targets)
        target["status"] = "scanned"
        state["nodes"] = [n if n["id"] != target["id"] else target for n in state["nodes"]]
        state["energy_remaining"] = state.get("energy_remaining", state.get("energy", 10)) - cost
        state["score"] = state.get("score", 0) + reward
        msg = f"[+] pivoted from {node['name']} to {target['name']} — discovered {target['label']}"
        return {"message": msg, "state": state, "score_delta": reward, "energy_cost": cost}

    @staticmethod
    def _action_defend(state: dict[str, Any], node: dict[str, Any], cost: int, reward: int) -> dict[str, Any]:
        if node.get("hardened"):
            return {"message": f"[i] {node['name']} already defended", "state": state, "score_delta": 0, "energy_cost": 0}
        node["status"] = "defended"
        state["nodes"] = [n if n["id"] != node["id"] else node for n in state["nodes"]]
        state["energy_remaining"] = state.get("energy_remaining", state.get("energy", 10)) - cost
        state["score"] = state.get("score", 0) + reward
        defense_state = state.setdefault("defense_state", {"hardened_nodes": [], "contained_nodes": [], "patched_nodes": [], "investigated_nodes": [], "resolved_alerts": []})
        if node["id"] not in defense_state.get("hardened_nodes", []):
            defense_state.setdefault("hardened_nodes", []).append(node["id"])
        msg = f"[+] defended {node['name']} — security posture improved"
        return {"message": msg, "state": state, "score_delta": reward, "energy_cost": cost}

    @staticmethod
    def _action_harden(state: dict[str, Any], node: dict[str, Any], cost: int, reward: int) -> dict[str, Any]:
        if node.get("hardened"):
            return {"message": f"[i] {node['name']} already hardened", "state": state, "score_delta": 0, "energy_cost": 0}
        if node["status"] == "hidden":
            return {"message": f"[i] scan {node['name']} first to identify hardening needs", "state": state, "score_delta": 0, "energy_cost": 0}
        node["hardened"] = True
        node["status"] = "hardened" if node["status"] != "compromised" else node["status"]
        node["security"] = min(5, node["security"] + 1)
        state["nodes"] = [n if n["id"] != node["id"] else node for n in state["nodes"]]
        state["energy_remaining"] = state.get("energy_remaining", state.get("energy", 10)) - cost
        state["score"] = state.get("score", 0) + reward
        defense_state = state.setdefault("defense_state", {"hardened_nodes": [], "contained_nodes": [], "patched_nodes": [], "investigated_nodes": [], "resolved_alerts": []})
        if node["id"] not in defense_state.get("hardened_nodes", []):
            defense_state.setdefault("hardened_nodes", []).append(node["id"])
        msg = f"[+] hardened {node['name']} — applied: {', '.join(node['defense_actions'][:2])}"
        return {"message": msg, "state": state, "score_delta": reward, "energy_cost": cost}

    @staticmethod
    def _action_investigate(state: dict[str, Any], node: dict[str, Any], cost: int, reward: int) -> dict[str, Any]:
        if node.get("investigated"):
            return {"message": f"[i] {node['name']} already investigated", "state": state, "score_delta": 0, "energy_cost": 0}
        node["investigated"] = True
        state["nodes"] = [n if n["id"] != node["id"] else node for n in state["nodes"]]
        state["energy_remaining"] = state.get("energy_remaining", state.get("energy", 10)) - cost
        state["score"] = state.get("score", 0) + reward
        defense_state = state.setdefault("defense_state", {"hardened_nodes": [], "contained_nodes": [], "patched_nodes": [], "investigated_nodes": [], "resolved_alerts": []})
        if node["id"] not in defense_state.get("investigated_nodes", []):
            defense_state.setdefault("investigated_nodes", []).append(node["id"])
        # Resolve alerts for this asset
        resolved = 0
        for alert in state.get("alerts", []):
            if alert.get("asset_id") == node["id"] and alert["status"] == "open":
                alert["status"] = "investigated"
                resolved += 1
        msg = f"[+] investigated {node['name']} — found {len(node['logs'])} log entries, resolved {resolved} alert(s)"
        return {"message": msg, "state": state, "score_delta": reward, "energy_cost": cost}

    @staticmethod
    def _action_patch(state: dict[str, Any], node: dict[str, Any], cost: int, reward: int) -> dict[str, Any]:
        if node.get("hardened"):
            return {"message": f"[i] {node['name']} already patched and hardened", "state": state, "score_delta": 0, "energy_cost": 0}
        node["hardened"] = True
        node["status"] = "hardened"
        node["security"] = min(5, node["security"] + 2)
        node["weakness"] = "patched — no known weaknesses"
        state["nodes"] = [n if n["id"] != node["id"] else node for n in state["nodes"]]
        state["energy_remaining"] = state.get("energy_remaining", state.get("energy", 10)) - cost
        state["score"] = state.get("score", 0) + reward
        defense_state = state.setdefault("defense_state", {"hardened_nodes": [], "contained_nodes": [], "patched_nodes": [], "investigated_nodes": [], "resolved_alerts": []})
        if node["id"] not in defense_state.get("patched_nodes", []):
            defense_state.setdefault("patched_nodes", []).append(node["id"])
        msg = f"[+] patched {node['name']} — security level raised to {node['security']}/5"
        return {"message": msg, "state": state, "score_delta": reward, "energy_cost": cost}

    @staticmethod
    def _action_contain(state: dict[str, Any], node: dict[str, Any], cost: int, reward: int) -> dict[str, Any]:
        if not node.get("compromised"):
            return {"message": f"[i] {node['name']} is not compromised — no containment needed", "state": state, "score_delta": 0, "energy_cost": 0}
        node["compromised"] = False
        node["status"] = "defended"
        node["security"] = min(5, node["security"] + 1)
        state["nodes"] = [n if n["id"] != node["id"] else node for n in state["nodes"]]
        state["energy_remaining"] = state.get("energy_remaining", state.get("energy", 10)) - cost
        state["score"] = state.get("score", 0) + reward
        defense_state = state.setdefault("defense_state", {"hardened_nodes": [], "contained_nodes": [], "patched_nodes": [], "investigated_nodes": [], "resolved_alerts": []})
        if node["id"] not in defense_state.get("contained_nodes", []):
            defense_state.setdefault("contained_nodes", []).append(node["id"])
        # Resolve alerts for this asset
        for alert in state.get("alerts", []):
            if alert.get("asset_id") == node["id"] and alert["status"] in ("open", "investigated"):
                alert["status"] = "resolved"
        msg = f"[+] contained {node['name']} — compromise neutralized, sessions revoked"
        return {"message": msg, "state": state, "score_delta": reward, "energy_cost": cost}

    @staticmethod
    def _action_report(state: dict[str, Any], node: dict[str, Any], cost: int, reward: int) -> dict[str, Any]:
        state["energy_remaining"] = state.get("energy_remaining", state.get("energy", 10)) - cost
        state["score"] = state.get("score", 0) + reward
        msg = "[+] report submitted — assessment documented"
        return {"message": msg, "state": state, "score_delta": reward, "energy_cost": cost}

    # ------------------------------------------------------------------
    # Objective checking
    # ------------------------------------------------------------------

    @classmethod
    def check_objectives(cls, state: dict[str, Any]) -> list[dict[str, Any]]:
        updates: list[dict[str, Any]] = []
        nodes = state.get("nodes", [])
        defense_state = state.get("defense_state", {})
        for obj in state.get("objectives", []):
            if obj.get("completed"):
                continue
            count = 0
            if obj["type"] == "scan":
                count = sum(1 for n in nodes if n["status"] in ("scanned", "accessed", "compromised", "hardened", "defended"))
            elif obj["type"] == "exploit":
                count = sum(1 for n in nodes if n.get("compromised") and n["segment"] in ("edge", "dmz"))
            elif obj["type"] == "investigate":
                count = len(defense_state.get("investigated_nodes", []))
            elif obj["type"] == "harden":
                count = len(defense_state.get("hardened_nodes", []))
            elif obj["type"] == "contain":
                count = len(defense_state.get("contained_nodes", []))
            elif obj["type"] == "patch":
                count = len(defense_state.get("patched_nodes", []))
            elif obj["type"] == "report":
                count = 1 if any(a.get("action") == "report" for a in state.get("player_actions_log", [])) else 0
            if count >= obj.get("target_count", 1):
                obj["completed"] = True
                updates.append({"objective_id": obj["id"], "title": obj["title"], "completed": True, "xp": obj.get("xp", 0)})
        return updates

    # ------------------------------------------------------------------
    # World event tick
    # ------------------------------------------------------------------

    @classmethod
    def tick_world(cls, state: dict[str, Any]) -> list[dict[str, Any]]:
        rng = random.Random(f"{state.get('scenario_seed', 'tick')}-{state.get('current_tick', 0)}")
        events: list[dict[str, Any]] = []
        nodes = state.get("nodes", [])
        employees = state.get("company_profile", {}).get("employees", [])

        # Generate 1-2 world events per tick
        for _ in range(rng.randint(1, 2)):
            tmpl = rng.choice(BUSINESS_EVENT_TEMPLATES)
            node = rng.choice(nodes) if nodes else None
            emp = rng.choice(employees) if employees else None
            desc = tmpl["description"].format(
                name=emp["display_name"] if emp else "Unknown",
                ip=f"10.{rng.randint(1,40)}.{rng.randint(0,10)}.{rng.randint(20,220)}",
                hostname=node["name"] if node else "unknown",
                service=rng.choice(["HTTP", "DNS", "SMTP", "VPN"]),
                description=rng.choice(["VPN access requested", "Password reset needed", "Suspicious email reported"]),
                department=emp["department"] if emp else "IT",
            )
            events.append({
                "id": f"wevent-{state.get('current_tick', 0)}-{len(events)}",
                "type": tmpl["type"],
                "description": desc,
                "timestamp": datetime.now(UTC).isoformat(),
                "affected_assets": [node["id"]] if node and rng.random() < 0.3 else [],
            })

        # Occasionally generate new alert
        if rng.random() < 0.3 and nodes:
            alert_tmpl = rng.choice(ALERT_TEMPLATES)
            node = rng.choice(nodes)
            state.setdefault("alerts", []).append({
                "id": f"alert-tick-{state.get('current_tick', 0)}",
                "key": alert_tmpl["key"],
                "title": alert_tmpl["title"],
                "severity": alert_tmpl["severity"],
                "source": alert_tmpl["source"],
                "asset_id": node["id"],
                "asset_name": node["name"],
                "status": "open",
                "detected": True,
                "timestamp": datetime.now(UTC).isoformat(),
            })
            events.append({
                "id": f"wevent-alert-{state.get('current_tick', 0)}",
                "type": "security_alert",
                "description": f"New alert: {alert_tmpl['title']} on {node['name']}",
                "timestamp": datetime.now(UTC).isoformat(),
                "affected_assets": [node["id"]],
            })

        state.setdefault("world_events", []).extend(events)
        state["current_tick"] = state.get("current_tick", 0) + 1
        return events

    # ------------------------------------------------------------------
    # Safety validation
    # ------------------------------------------------------------------

    @classmethod
    def validate_safety(cls, scenario: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        safety = scenario.get("safety_metadata", {})
        if not safety.get("fictional_only"):
            errors.append("Scenario must be fictional only.")
        if safety.get("contains_real_malware"):
            errors.append("Real malware is not allowed.")
        if safety.get("targets_public_internet"):
            errors.append("Public internet targeting is not allowed.")
        for asset in scenario.get("nodes", []):
            ip_value = asset.get("ip_address")
            if ip_value and not cls.is_allowed_training_ip(ip_value):
                errors.append(f"Asset {asset.get('id')} uses disallowed IP {ip_value}.")
        for identity in scenario.get("company_profile", {}).get("employees", []):
            email = identity.get("email", "")
            if email and not email.endswith(".cyberverse.test"):
                errors.append(f"Identity {identity.get('id')} uses non-training email domain.")
        return errors

    @staticmethod
    def is_allowed_training_ip(ip_value: str) -> bool:
        try:
            ip = ipaddress.ip_address(ip_value)
        except ValueError:
            return False
        allowed = [
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("172.16.0.0/12"),
            ipaddress.ip_network("192.168.0.0/16"),
            ipaddress.ip_network("192.0.2.0/24"),
            ipaddress.ip_network("198.51.100.0/24"),
            ipaddress.ip_network("203.0.113.0/24"),
        ]
        return any(ip in network for network in allowed)

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    @classmethod
    async def start_session(cls, db: AsyncSession, user: User, difficulty: str, game_mode: str, industry: str | None, seed: str | None, level: int) -> GameSession:
        await cls.ensure_default_content(db)
        chosen_industry = industry or random.choice(INDUSTRY_TEMPLATES)["slug"]
        scenario_seed = seed or cls.make_seed(user.id, chosen_industry, difficulty)

        if game_mode == "soc":
            data = cls.generate_soc_scenario(scenario_seed, difficulty, level)
        else:
            data = cls.generate_enterprise(scenario_seed, chosen_industry, difficulty, level)

        errors = cls.validate_safety(data)
        if errors:
            raise GameSafetyError(f"Safety validation failed: {'; '.join(errors)}")

        diff_cfg = DIFFICULTY_CONFIG.get(difficulty, DIFFICULTY_CONFIG["beginner"])
        session = GameSession(
            user_id=user.id,
            scenario_seed=scenario_seed,
            company_profile=data["company_profile"],
            topology=data["topology"],
            nodes=data["nodes"],
            links=data["links"],
            alerts=data["alerts"],
            business_events=data["business_events"],
            objectives=data["objectives"],
            player_actions_log=[],
            defense_state=data["defense_state"],
            world_events=data.get("world_events", []),
            energy_remaining=diff_cfg["energy"],
            score=0,
            xp_awarded=0,
            coins_awarded=0,
            status=GameStatus.ACTIVE.value,
            difficulty=difficulty,
            game_mode=game_mode,
            industry=chosen_industry,
            current_tick=0,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @classmethod
    async def get_session_for_user(cls, db: AsyncSession, session_id: UUID, user: User) -> GameSession:
        result = await db.execute(select(GameSession).where(GameSession.id == session_id, GameSession.user_id == user.id))
        session = result.scalar_one_or_none()
        if not session:
            raise LookupError("Game session not found")
        return session

    @classmethod
    async def apply_session_action(cls, db: AsyncSession, session: GameSession, user: User, node_id: str, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        if session.status != GameStatus.ACTIVE.value:
            return {"message": "[x] session is not active", "score_delta": 0, "energy_cost": 0, "energy_remaining": session.energy_remaining}

        state = {
            "nodes": session.nodes,
            "links": session.links,
            "alerts": session.alerts,
            "business_events": session.business_events,
            "objectives": session.objectives,
            "defense_state": session.defense_state,
            "world_events": session.world_events,
            "energy_remaining": session.energy_remaining,
            "score": session.score,
            "scenario_seed": session.scenario_seed,
            "current_tick": session.current_tick,
            "player_actions_log": session.player_actions_log,
        }

        result = cls.apply_action(state, node_id, action, payload)

        # Log the action
        session.player_actions_log = [*session.player_actions_log, {
            "node_id": node_id,
            "action": action,
            "payload": payload,
            "message": result["message"],
            "timestamp": datetime.now(UTC).isoformat(),
        }]
        session.nodes = state["nodes"]
        session.alerts = state["alerts"]
        session.defense_state = state["defense_state"]
        session.world_events = state.get("world_events", [])
        session.energy_remaining = state.get("energy_remaining", session.energy_remaining)
        session.score = state.get("score", session.score)

        # Check objectives
        objective_updates = cls.check_objectives(state)
        session.objectives = state["objectives"]

        # Check win condition (all objectives completed)
        all_completed = all(o.get("completed") for o in session.objectives)
        phase = "won" if all_completed else "playing"
        if session.energy_remaining <= 0 and not all_completed:
            phase = "lost"

        await db.commit()
        await db.refresh(session)

        return {
            "session_id": str(session.id),
            "message": result["message"],
            "score_delta": result.get("score_delta", 0),
            "energy_cost": result.get("energy_cost", 0),
            "energy_remaining": session.energy_remaining,
            "objective_updates": objective_updates,
            "phase": phase,
        }

    @classmethod
    async def complete_session(cls, db: AsyncSession, session: GameSession, user: User) -> dict[str, Any]:
        if session.status == GameStatus.COMPLETED.value:
            return cls.debrief_payload(session)

        nodes = session.nodes or []
        defense_state = session.defense_state or {}
        objectives = session.objectives or []

        completed_objectives = sum(1 for o in objectives if o.get("completed"))
        total_objectives = max(len(objectives), 1)
        obj_pct = completed_objectives / total_objectives

        hardened = len(defense_state.get("hardened_nodes", []))
        contained = len(defense_state.get("contained_nodes", []))
        patched = len(defense_state.get("patched_nodes", []))
        investigated = len(defense_state.get("investigated_nodes", []))

        score = max(0, int(session.score * obj_pct + (hardened + contained + patched + investigated) * 5))
        session.score = score
        session.xp_awarded = score * 3
        session.coins_awarded = score
        session.status = GameStatus.COMPLETED.value
        session.completed_at = datetime.now(UTC)

        # Save high score
        hs = GameHighScore(
            user_id=user.id,
            level=1,
            score=score,
            game_mode=session.game_mode,
            industry=session.industry,
        )
        db.add(hs)
        await db.commit()
        return cls.debrief_payload(session)

    @staticmethod
    def debrief_payload(session: GameSession) -> dict[str, Any]:
        score = session.score or 0
        grade = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 55 else "Needs Practice"
        objectives = session.objectives or []
        completed = [o["title"] for o in objectives if o.get("completed")]
        missed = [o["title"] for o in objectives if not o.get("completed")]
        return {
            "session_id": str(session.id),
            "score": score,
            "grade": grade,
            "xp_awarded": session.xp_awarded,
            "coins_awarded": session.coins_awarded,
            "strengths": completed or ["Participated in the simulation"],
            "missed_items": missed,
            "learning_summary": f"You completed {len(completed)}/{len(objectives)} objectives in the {session.industry} {session.game_mode} scenario.",
            "recommended_lessons": ["network-security-fundamentals", "incident-response-basics", "security-hardening-guide"],
            "career_feedback": f"This maps to {session.game_mode} cybersecurity workflows for {session.industry} environments.",
        }

    @classmethod
    async def get_leaderboard(cls, db: AsyncSession, game_mode: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        from app.models.user import Profile
        stmt = select(GameHighScore, Profile).join(Profile, GameHighScore.user_id == Profile.user_id)
        if game_mode:
            stmt = stmt.where(GameHighScore.game_mode == game_mode)
        stmt = stmt.order_by(GameHighScore.score.desc()).limit(limit)
        result = await db.execute(stmt)
        rows = result.all()
        return [
            {
                "user_id": str(hs.user_id),
                "username": prof.username,
                "score": hs.score,
                "level": hs.level,
                "game_mode": hs.game_mode,
                "industry": hs.industry,
            }
            for hs, prof in rows
        ]
