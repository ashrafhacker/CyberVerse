"""Seed the Cyber Arsenal with legitimate free/open-source security tools.

Only tools that are open source, free, or have a legitimate free tier are
included. All URLs point to official project/vendor sites and every entry is
flagged with a ``verified`` timestamp reflecting editorial review.

Run from the repo root:  python seed_arsenal.py   (backend venv activated)
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select  # noqa: E402

from app.core.database import async_session_maker  # noqa: E402
from app.models.tool import Tool, ToolCategory  # noqa: E402

VERIFIED = datetime.now(timezone.utc)

CATEGORIES = [
    ("network", "Network", "Traffic capture, analysis, and network defense.", 0),
    ("web-security", "Web Security", "Testing and hardening web applications.", 1),
    ("soc", "SOC & Detection", "SIEM, alerting, and security operations.", 2),
    ("ids-ips", "IDS / IPS", "Network intrusion detection and prevention.", 3),
    ("osint", "OSINT", "Open-source intelligence gathering.", 4),
    ("forensics", "Digital Forensics", "Disk, memory, and artifact analysis.", 5),
    ("reverse-engineering", "Reverse Engineering", "Disassembly and binary analysis.", 6),
    ("malware-analysis", "Malware Analysis", "Static and dynamic sample analysis.", 7),
    ("cloud-security", "Cloud Security", "Cloud posture and misconfiguration scanning.", 8),
    ("container-security", "Container Security", "Image and runtime scanning.", 9),
    ("code-security", "Code Security", "SAST, secret scanning, and secure coding.", 10),
    ("vulnerability-assessment", "Vulnerability Assessment", "Scanner and vuln management.", 11),
    ("threat-intelligence", "Threat Intelligence", "IOC sharing and intel platforms.", 12),
    ("cryptography", "Cryptography", "Hashing and password cracking (authorized use).", 13),
    ("linux-security", "Linux Security", "Host hardening and auditing.", 14),
    ("windows-security", "Windows Security", "Windows endpoint auditing.", 15),
    ("ctf", "CTF", "Capture-the-flag tooling.", 16),
    ("privacy", "Privacy / Security", "Privacy-enhancing tools.", 17),
]


def _tool(name, slug, cat, desc, license_name, open_source, free_tier, os_list,
          difficulty, official, docs=None, tutorial=None, tags=None):
    return {
        "category_slug": cat,
        "slug": slug,
        "name": name,
        "description": desc,
        "license_name": license_name,
        "open_source": open_source,
        "free_tier": free_tier,
        "supported_os": os_list,
        "difficulty": difficulty,
        "official_url": official,
        "docs_url": docs,
        "tutorial_url": tutorial,
        "tags": tags or [],
        "is_published": True,
        "verified_at": VERIFIED,
    }


TOOLS = [
    _tool("Nmap", "nmap", "network", "Network discovery and security scanning.",
          "NPSL (open source)", True, True, ["linux", "macos", "windows", "bsd"], "beginner",
          "https://nmap.org/", "https://nmap.org/docs.html", None, ["recon", "scanning", "port"]),
    _tool("Wireshark", "wireshark", "network", "Packet capture and analysis.",
          "GPL-2.0", True, True, ["linux", "macos", "windows"], "beginner",
          "https://www.wireshark.org/", "https://www.wireshark.org/docs/", None, ["pcap", "traffic"]),
    _tool("tcpdump", "tcpdump", "network", "Command-line packet capture.",
          "BSD-3-Clause", True, True, ["linux", "macos", "bsd"], "intermediate",
          "https://www.tcpdump.org/", "https://www.tcpdump.org/manpages/tcpdump.1.html", None, ["pcap", "cli"]),
    _tool("Zeek", "zeek", "network", "Security monitoring framework for network traffic.",
          "BSD-3-Clause", True, True, ["linux", "macos", "freebsd"], "advanced",
          "https://zeek.org/", "https://docs.zeek.org/", None, ["ids", "analytics", "log"]),
    _tool("Suricata", "suricata", "ids-ips", "High-performance network IDS/IPS and NSM.",
          "GPL-2.0", True, True, ["linux", "freebsd", "windows"], "intermediate",
          "https://suricata.io/", "https://docs.suricata.io/", None, ["ids", "ips", "signatures"]),
    _tool("Snort", "snort", "ids-ips", "Open-source network intrusion detection and prevention.",
          "GPL-2.0", True, True, ["linux", "windows"], "intermediate",
          "https://www.snort.org/", "https://www.snort.org/documents", None, ["ids", "ips", "snort"]),
    _tool("OWASP ZAP", "owasp-zap", "web-security", "Web application security scanner and proxy.",
          "Apache-2.0", True, True, ["linux", "macos", "windows"], "intermediate",
          "https://www.zaproxy.org/", "https://www.zaproxy.org/docs/", None, ["web", "scanning", "proxy", "owasp"]),
    _tool("Wazuh", "wazuh", "soc", "Open-source security platform (SIEM + XDR + HIDS).",
          "GPL-2.0", True, True, ["linux", "macos", "windows"], "advanced",
          "https://wazuh.com/", "https://documentation.wazuh.com/", None, ["siem", "hids", "xdr"]),
    _tool("Security Onion", "security-onion", "soc", "Free and open Linux distro for security monitoring.",
          "GPL-2.0 / Free", True, True, ["linux"], "advanced",
          "https://securityonion.net/", "https://docs.securityonion.net/", None, ["nsm", "siem", "distro"]),
    _tool("Autopsy", "autopsy", "forensics", "Graphical digital forensics platform.",
          "Apache-2.0", True, True, ["linux", "macos", "windows"], "intermediate",
          "https://www.sleuthkit.org/autopsy/", "https://www.sleuthkit.org/autopsy/docs.php", None, ["forensics", "disk"]),
    _tool("Volatility", "volatility", "forensics", "Advanced memory forensics framework.",
          "GPL-2.0", True, True, ["linux", "macos", "windows"], "advanced",
          "https://volatilityfoundation.org/", "https://volatility3.readthedocs.io/", None, ["memory", "ram"]),
    _tool("Ghidra", "ghidra", "reverse-engineering", "Software reverse-engineering suite from NSA.",
          "Apache-2.0", True, True, ["linux", "macos", "windows"], "advanced",
          "https://ghidra-sre.org/", "https://ghidra.re/ghidra_docs/", None, ["reversing", "disassembler", "decompiler"]),
    _tool("Radare2", "radare2", "reverse-engineering", "Command-line binary analysis framework.",
          "LGPL-3.0", True, True, ["linux", "macos", "windows", "bsd"], "advanced",
          "https://rada.re/n/", "https://book.rada.re/", None, ["reversing", "debugger"]),
    _tool("Cutter", "cutter", "reverse-engineering", "GUI for the radare2 reversing framework.",
          "GPL-3.0", True, True, ["linux", "macos", "windows"], "advanced",
          "https://cutter.re/", "https://cutter.re/docs/", None, ["reversing", "gui"]),
    _tool("John the Ripper", "john-the-ripper", "cryptography", "Password cracking tool (authorized testing only).",
          "GPL-2.0", True, True, ["linux", "macos", "windows"], "intermediate",
          "https://www.openwall.com/john/", "https://www.openwall.com/john/doc/", None, ["password", "hash", "cracking"]),
    _tool("Hashcat", "hashcat", "cryptography", "Advanced password recovery tool.",
          "MIT", True, True, ["linux", "macos", "windows"], "intermediate",
          "https://hashcat.net/hashcat/", "https://hashcat.net/wiki/", None, ["password", "hash", "cracking"]),
    _tool("Greenbone Community Edition", "greenbone-community-edition", "vulnerability-assessment",
          "Open Vulnerability Assessment Scanner (OpenVAS) community edition.",
          "GPL-2.0 (community)", True, True, ["linux"], "advanced",
          "https://www.greenbone.net/en/community-edition/", "https://greenbone.github.io/docs/", None, ["vulnerability", "openvas", "scanning"]),
    _tool("Trivy", "trivy", "container-security", "Comprehensive container and filesystem vulnerability scanner.",
          "Apache-2.0", True, True, ["linux", "macos", "windows"], "beginner",
          "https://trivy.dev/", "https://aquasecurity.github.io/trivy/", None, ["container", "scanner", "cve"]),
    _tool("Grype", "grype", "container-security", "Vulnerability scanner for container images and filesystems.",
          "Apache-2.0", True, True, ["linux", "macos", "windows"], "beginner",
          "https://grype.dev/", "https://github.com/anchore/grype", None, ["container", "scanner", "cve"]),
    _tool("Gitleaks", "gitleaks", "code-security", "Detect hardcoded secrets in git repositories.",
          "MIT", True, True, ["linux", "macos", "windows"], "beginner",
          "https://gitleaks.io/", "https://github.com/gitleaks/gitleaks", None, ["secret", "git", "scanning"]),
    _tool("Semgrep Community Edition", "semgrep-community-edition", "code-security",
          "Lightweight static analysis for many languages (free community edition).",
          "LGPL-2.1 (engine), free tier", True, True, ["linux", "macos", "windows"], "intermediate",
          "https://semgrep.dev/", "https://semgrep.dev/docs/", None, ["sast", "static", "code"]),
    _tool("Bandit", "bandit", "code-security", "Security linter for Python source code.",
          "Apache-2.0", True, True, ["linux", "macos", "windows"], "beginner",
          "https://bandit.readthedocs.io/", "https://bandit.readthedocs.io/", None, ["python", "sast", "lint"]),
    _tool("Prowler", "prowler", "cloud-security", "AWS/Azure/GCP security assessments with CIS/guardrails.",
          "Apache-2.0", True, True, ["linux", "macos"], "advanced",
          "https://prowler.com/", "https://docs.prowler.com/", None, ["cloud", "aws", "azure", "gcp", "cis"]),
    _tool("ScoutSuite", "scoutsuite", "cloud-security", "Multi-cloud security auditing toolset.",
          "GPL-2.0", True, True, ["linux", "macos", "windows"], "advanced",
          "https://github.com/nccgroup/ScoutSuite", "https://github.com/nccgroup/ScoutSuite/wiki", None, ["cloud", "audit", "aws", "gcp", "azure"]),
    _tool("theHarvester", "theharvester", "osint", "E-mail, subdomain, and names gatherer for OSINT.",
          "GPL-3.0", True, True, ["linux", "macos", "windows"], "beginner",
          "https://github.com/laramies/theHarvester", "https://github.com/laramies/theHarvester", None, ["osint", "recon", "email"]),
    _tool("SpiderFoot OSS", "spiderfoot-oss", "osint", "Automated OSINT and threat-intelligence collection.",
          "MIT", True, True, ["linux", "macos", "windows"], "intermediate",
          "https://www.spiderfoot.net/", "https://github.com/smicallef/spiderfoot", None, ["osint", "recon", "automation"]),
    _tool("MISP", "misp", "threat-intelligence", "Malware Information Sharing Platform.",
          "AGPL-3.0", True, True, ["linux"], "advanced",
          "https://www.misp-project.org/", "https://www.misp-project.org/documentation/", None, ["intel", "ioc", "sharing"]),
    _tool("MITRE ATT&CK", "mitre-attack", "threat-intelligence", "Knowledge base of adversary tactics and techniques (reference).",
          "CC BY 4.0 / free", True, True, ["web"], "beginner",
          "https://attack.mitre.org/", "https://attack.mitre.org/resources/", None, ["mitre", "frameworks", "reference"]),
    _tool("OWASP", "owasp", "web-security", "OWASP Foundation security resources and projects.",
          "CC BY-SA 4.0 / free", True, True, ["web"], "beginner",
          "https://owasp.org/", "https://owasp.org/www-project-top-ten/", None, ["owasp", "reference", "web"]),
    _tool("NVD", "nvd", "threat-intelligence", "NIST National Vulnerability Database (reference).",
          "Public domain / US Gov", True, True, ["web"], "beginner",
          "https://nvd.nist.gov/", "https://nvd.nist.gov/general", None, ["cve", "vulnerability", "reference"]),
    _tool("CVE", "cve", "threat-intelligence", "CVE list of publicly disclosed vulnerabilities (reference).",
          "Public domain / free", True, True, ["web"], "beginner",
          "https://www.cve.org/", "https://www.cve.org/ResourcesSupport/Glossary", None, ["cve", "reference"]),
]


async def seed():
    async with async_session_maker() as db:
        existing = await db.scalar(select(func.count()).select_from(ToolCategory))
        if existing and existing > 0:
            print("Arsenal categories already exist. Skipping category seed.")

        category_by_slug = {}
        for slug, name, desc, order in CATEGORIES:
            res = await db.execute(select(ToolCategory).where(ToolCategory.slug == slug))
            cat = res.scalar_one_or_none()
            if not cat:
                cat = ToolCategory(id=uuid4(), slug=slug, name=name, description=desc, display_order=order)
                db.add(cat)
                await db.flush()
            category_by_slug[slug] = cat

        tool_count = await db.scalar(select(func.count()).select_from(Tool))
        if tool_count and tool_count > 0:
            print(f"Arsenal already has {tool_count} tools. Skipping tool seed.")
            await db.commit()
            return

        for data in TOOLS:
            cat = category_by_slug[data.pop("category_slug")]
            db.add(Tool(id=uuid4(), category_id=cat.id, **data))
        await db.commit()
        print(f"Seeded {len(TOOLS)} tools and {len(CATEGORIES)} categories.")


if __name__ == "__main__":
    asyncio.run(seed())
