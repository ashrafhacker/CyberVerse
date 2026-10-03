"""Seed the SOC simulator with a set of fictional, training-safe alerts.

All assets/domains are generic placeholders (example.test) and every alert
references MITRE ATT&CK techniques for educational correlation. No real systems
are targeted.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select  # noqa: E402

from app.core.database import async_session_maker  # noqa: E402
from app.models.soc import SOCAlert  # noqa: E402

ALERTS = [
    {
        "title": "Multiple failed logins followed by success",
        "description": "An account showed 12 failed authentication attempts then a successful login from an unusual source.",
        "severity": "medium",
        "confidence": 80,
        "asset": "SRV-LOGIN-01.example.test",
        "source": "Authentication service",
        "mitre_technique_id": "T1110",
        "event_details": {"failed_attempts": 12, "source_ip": "198.51.100.20"},
    },
    {
        "title": "Outbound connection to known-bad domain",
        "description": "A workstation initiated outbound DNS resolution and HTTPS to a suspicious domain.",
        "severity": "high",
        "confidence": 65,
        "asset": "WS-ENG-042.example.test",
        "source": "DNS proxy",
        "mitre_technique_id": "T1071",
        "event_details": {"domain": "update-verifier.example.test", "dest_port": 443},
    },
    {
        "title": "Suspicious PowerShell spawned by document",
        "description": "A productivity document spawned a PowerShell process that made a network call.",
        "severity": "high",
        "confidence": 60,
        "asset": "WS-SALES-011.example.test",
        "source": "Endpoint agent",
        "mitre_technique_id": "T1059",
        "event_details": {"parent": "winword", "child": "powershell.exe"},
    },
    {
        "title": "Port scan detected from internal host",
        "description": "An internal host performed a horizontal port scan across the subnet.",
        "severity": "medium",
        "confidence": 70,
        "asset": "WS-IT-007.example.test",
        "source": "Network IDS",
        "mitre_technique_id": "T1046",
        "event_details": {"targets": 124, "protocol": "tcp"},
    },
    {
        "title": "New local admin account created",
        "description": "A new account was added to the local administrators group on a server.",
        "severity": "medium",
        "confidence": 55,
        "asset": "SRV-DB-03.example.test",
        "source": "Identity platform",
        "mitre_technique_id": "T1136",
        "event_details": {"account": "svc-support", "group": "Administrators"},
    },
    {
        "title": "Sensitive file uploaded to external service",
        "description": "A user uploaded a sensitive file to a cloud file-sharing service.",
        "severity": "low",
        "confidence": 45,
        "asset": "WS-FIN-009.example.test",
        "source": "DLP agent",
        "mitre_technique_id": "T1567",
        "event_details": {"file_class": "PII", "service": "share.example.test"},
    },
    {
        "title": "Abnormal remote desktop session",
        "description": "A remote desktop session originated from an IP outside the approved range.",
        "severity": "high",
        "confidence": 75,
        "asset": "SRV-RDP-01.example.test",
        "source": "Network device",
        "mitre_technique_id": "T1021",
        "event_details": {"protocol": "rdp", "source_ip": "203.0.113.88"},
    },
]


async def seed():
    async with async_session_maker() as db:
        existing = await db.scalar(select(func.count()).select_from(SOCAlert))
        if existing and existing > 0:
            print(f"SOC already has {existing} alerts. Skipping.")
            return
        now = datetime.now(timezone.utc)
        for i, alert in enumerate(ALERTS):
            db.add(SOCAlert(
                id=uuid4(),
                title=alert["title"],
                description=alert["description"],
                severity=alert["severity"],
                confidence=alert["confidence"],
                asset=alert["asset"],
                source=alert["source"],
                status="new",
                mitre_technique_id=alert["mitre_technique_id"],
                event_details=alert["event_details"],
                timeline=[
                    {"at": (now - timedelta(minutes=len(ALERTS) - i)).isoformat(), "kind": "alert.triggered",
                     "severity": alert["severity"]}
                ],
                timestamp=now - timedelta(minutes=len(ALERTS) - i),
            ))
        await db.commit()
        print(f"Seeded {len(ALERTS)} SOC alerts.")


if __name__ == "__main__":
    asyncio.run(seed())
