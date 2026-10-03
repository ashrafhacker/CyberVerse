"""Seed the threat-intelligence module with curated CVE / MITRE ATT&CK / indicator data.

CVE entries are taken from NVD (public domain U.S. government data). MITRE ATT&CK
technique identifiers/descriptions are from the official MITRE ATT&CK knowledge base.
Indicators are synthetic examples for training only.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select  # noqa: E402

from app.core.database import async_session_maker  # noqa: E402
from app.models.threat_intel import AttackTechnique, CVE, ThreatIndicator  # noqa: E402

TECHNIQUES = [
    ("T1059", "Command and Scripting Interpreter", "Execution", "linux", "Adversaries may abuse command and script interpreters to execute commands, scripts, or binaries.", "Use application control where appropriate.", "https://attack.mitre.org/techniques/T1059/", ["Process Creation", "Command Execution"]),
    ("T1078", "Valid Accounts", "Defense Evasion", "linux", "Adversaries may obtain and abuse valid credentials to access systems.", "Implement MFA and monitor for anomalous authentication.", "https://attack.mitre.org/techniques/T1078/", ["Authentication Logs"]),
    ("T1566", "Phishing", "Initial Access", "windows", "Adversaries may send phishing messages to gain access to victim systems.", "Use email gateways and user awareness training.", "https://attack.mitre.org/techniques/T1566/", ["Email Gateway", "URL Reputation"]),
    ("T1046", "Network Service Discovery", "Discovery", "linux", "Adversaries may scan for services running on remote hosts.", "Limit exposure of unnecessary services.", "https://attack.mitre.org/techniques/T1046/", ["Network Traffic"]),
    ("T1021", "Remote Services", "Lateral Movement", "windows", "Adversaries may use valid or stolen credentials to access remote services.", "Restrict remote access and use network segmentation.", "https://attack.mitre.org/techniques/T1021/", ["Net Logon", "Authentication Logs"]),
    ("T1110", "Brute Force", "Credential Access", "linux", "Adversaries may use brute-force techniques to gain access to accounts.", "Enforce account lockout and monitor failed logins.", "https://attack.mitre.org/techniques/T1110/", ["Authentication Logs"]),
    ("T1027", "Obfuscated Files or Information", "Defense Evasion", "windows", "Adversaries may obfuscate files or information to evade detection.", "Monitor for unusual file modifications.", "https://attack.mitre.org/techniques/T1027/", ["File Monitoring"]),
    ("T1548", "Abuse Elevation Control Mechanism", "Privilege Escalation", "linux", "Adversaries may circumvent mechanisms intended to control elevated privileges.", "Audit privilege use and enforce least privilege.", "https://attack.mitre.org/techniques/T1548/", ["Process Creation", "Audit Logs"]),
]

# CVE entries are real, factual public-domain descriptions from NVD.
CVE_ROWS = [
    ("CVE-2023-44487",
     "A rapid reset attack (HTTP/2 stream reset abuse) can enable denial of service against HTTP/2 web servers.",
     7.5, "high", "CWE-400", "Uncontrolled Resource Consumption", "network", "high",
     ["HTTP/2 servers", "web servers"], ["https://www.cisa.gov/news-events/alerts/2023/10/10/http2-rapid-reset-attack"],
     ["Limit stream reset rate", "Apply vendor patches"], ["T1498"],
     datetime(2023, 10, 10, tzinfo=timezone.utc)),
    ("CVE-2021-44228",
     "Apache Log4j2 vulnerable to JNDI remote code execution via crafted log messages.",
     10.0, "critical", "CWE-502", "Deserialization of Untrusted Data", "network", "high",
     ["Apache Log4j 2.x"], ["https://nvd.nist.gov/vuln/detail/CVE-2021-44228"],
     ["Upgrade to Log4j 2.17.1+", "Set log4j2.formatMsgNoLookups=true"], ["T1203", "T1059"],
     datetime(2021, 12, 10, tzinfo=timezone.utc)),
    ("CVE-2022-22965",
     "Spring Framework RCE via data binding on a class, leading to access to writable fields.",
     9.8, "critical", "CWE-94", "Improper Control of Generation of Code", "network", "high",
     ["Spring Framework 5.3.x"], ["https://nvd.nist.gov/vuln/detail/CVE-2022-22965"],
     ["Upgrade to patched Spring", "Disable binding of Class class"], ["T1059"],
     datetime(2022, 3, 31, tzinfo=timezone.utc)),
    ("CVE-2023-23397",
     "Microsoft Outlook elevation of privilege via crafted meeting invitation triggering NTLM credential theft.",
     9.8, "critical", "CWE-294", "Authentication Bypass by Capture-replay", "network", "high",
     ["Microsoft Outlook"], ["https://nvd.nist.gov/vuln/detail/CVE-2023-23397"],
     ["Apply Microsoft patch", "Add registry key to warn on unsafe opening"], ["T1137", "T1021"],
     datetime(2023, 3, 14, tzinfo=timezone.utc)),
    ("CVE-2023-27350",
     "PaperCut MF/NG improper access control allowing unauthenticated RCE in some configurations.",
     9.8, "critical", "CWE-287", "Improper Authentication", "network", "high",
     ["PaperCut MF/NG"], ["https://nvd.nist.gov/vuln/detail/CVE-2023-27350"],
     ["Upgrade to patched version", "Restrict management UI exposure"], ["T1133", "T1190"],
     datetime(2023, 4, 26, tzinfo=timezone.utc)),
]

INDICATORS = [
    ("ipv4", "203.0.113.50", "Synthetic scanning host (documentation range).", "Training range", ["recon"], "medium"),
    ("domain", "update-verifier.example.test", "Synthetic suspicious domain.", "Training", ["phishing"], "low"),
    ("sha256", "a" * 64, "Example file hash placeholder.", "Training", ["malware"], "low"),
    ("ipv4", "198.51.100.7", "Synthetic C2 callback (documentation range).", "Training", ["c2"], "medium"),
]


async def seed():
    async with async_session_maker() as db:
        tech_count = await db.scalar(select(func.count()).select_from(AttackTechnique))
        if tech_count == 0:
            tech_by_id = {}
            for tid, name, tactic, platform, desc, mitigation, url, sources in TECHNIQUES:
                t = AttackTechnique(
                    id=uuid4(), technique_id=tid, name=name, tactic=tactic, platform=platform,
                    description=desc, mitigation=mitigation, url=url, data_sources=sources,
                )
                tech_by_id[tid] = t
                db.add(t)
            print(f"Seeded {len(TECHNIQUES)} MITRE ATT&CK techniques.")
            await db.flush()

            cve_count = await db.scalar(select(func.count()).select_from(CVE))
            if cve_count == 0:
                for (cve_id, desc, cvss, sev, cwe, cwe_name, vec, comp, products, refs, mitig, techs, published) in CVE_ROWS:
                    cve = CVE(
                        id=uuid4(), cve_id=cve_id, description=desc, cvss_score=cvss, cvss_vector=None,
                        severity=sev, cwe_id=cwe, cwe_name=cwe_name, attack_vector=vec, complexity=comp,
                        affected_products=products, references=refs, mitigations=mitig,
                        published_date=published, source="NVD/CISA", confidence="high",
                    )
                    cve.techniques = [tech_by_id[t] for t in techs if t in tech_by_id]
                    db.add(cve)
                print(f"Seeded {len(CVE_ROWS)} CVEs.")
            await db.commit()
        else:
            print("Threat training techniques already exist; skipping seed.")

        ind_count = await db.scalar(select(func.count()).select_from(ThreatIndicator))
        if ind_count == 0:
            for (itype, value, desc, actor, tags, conf) in INDICATORS:
                db.add(ThreatIndicator(
                    id=uuid4(), indicator_type=itype, indicator_value=value, description=desc,
                    threat_actor=actor, tags=tags, source="MISP feeding", confidence=conf,
                ))
            await db.commit()
            print(f"Seeded {len(INDICATORS)} threat indicators.")


if __name__ == "__main__":
    asyncio.run(seed())
