"""
Seed the 20 CEH v12 PDF modules + one PDF lesson each into
the real schema (tables: courses / modules / lessons).

The old database/seeds/learning_paths_seed.sql targets a nonexistent
`course_modules` table and never ran — this script replaces it.

Usage:
  cd backend && python seed_ceh_modules.py
"""
import asyncio

# (order, title, description) — from learning_paths_seed.sql
MODULES = [
    (1, "Module 01 – Introduction to Ethical Hacking",
     "Fundamentals of security, ethical hacking phases, types of hackers, legal implications, and the CEH methodology."),
    (2, "Module 02 – Footprinting and Reconnaissance",
     "Passive and active reconnaissance techniques, OSINT, Google hacking, whois, DNS enumeration, and social engineering vectors."),
    (3, "Module 03 – Scanning Networks",
     "Network scanning techniques, port scanning, OS fingerprinting, ping sweeps, vulnerability scanning, and countermeasures."),
    (4, "Module 04 – Enumeration",
     "NetBIOS, SNMP, LDAP, NTP, SMTP, and DNS enumeration techniques, tools, and defensive strategies."),
    (5, "Module 05 – Vulnerability Analysis",
     "Vulnerability assessment concepts, classification systems (CVE, CVSS), scanning tools, and vulnerability management lifecycle."),
    (6, "Module 06 – System Hacking",
     "Password cracking, privilege escalation, maintaining access, hiding files, covering tracks, and steganography."),
    (7, "Module 07 – Malware Threats",
     "Trojans, viruses, worms, ransomware, fileless malware, malware analysis techniques, and countermeasures."),
    (8, "Module 08 – Sniffing",
     "Network sniffing concepts, passive/active sniffing, ARP poisoning, MAC flooding, DNS poisoning, and detection tools."),
    (9, "Module 09 – Social Engineering",
     "Social engineering attacks, phishing, vishing, identity theft, impersonation, and human-based attack defenses."),
    (10, "Module 10 – Denial-of-Service",
     "DoS and DDoS attacks, botnets, attack tools, DDoS mitigation, and protection strategies."),
    (11, "Module 11 – Session Hijacking",
     "Session hijacking techniques, cross-site scripting, packet analysis, TCP/IP hijacking, and session fixation."),
    (12, "Module 12 – Evading IDS, Firewalls, and Honeypots",
     "Firewall types, IDS evasion, honeypots, detection methods, and bypass techniques."),
    (13, "Module 13 – Hacking Web Servers",
     "Web server attacks, misconfiguration exploitation, patch management, web server security auditing."),
    (14, "Module 14 – Hacking Web Applications",
     "OWASP Top 10, web application attacks, authentication bypass, XSS, CSRF, file inclusion, and input validation."),
    (15, "Module 15 – SQL Injection",
     "SQL injection types, blind SQLi, time-based attacks, automated tools, detection, and prevention."),
    (16, "Module 16 – Hacking Wireless Networks",
     "Wireless concepts, WEP/WPA/WPA2 attacks, rogue AP, evil twin, wireless IDS evasion."),
    (17, "Module 17 – Hacking Mobile Platforms",
     "Android/iOS attack vectors, mobile device management, OWASP Mobile Top 10, mobile pen testing."),
    (18, "Module 18 – IoT and OT Hacking",
     "IoT architecture, attack surfaces, IoT hacking methodology, OT/SCADA security, and defensive countermeasures."),
    (19, "Module 19 – Cloud Computing",
     "Cloud models, cloud attacks, container security, serverless security, cloud pen testing, and AWS/Azure security."),
    (20, "Module 20 – Cryptography",
     "Encryption algorithms, PKI, digital signatures, disk encryption, cryptanalysis, and quantum cryptography."),
]

COURSE_SLUG = "course-ceh-pdf-modules"


async def main() -> None:
    from sqlalchemy import select

    from app.core.cache import course_cache
    from app.core.database import async_session_maker
    from app.models.course import ContentType, Course, Lesson, Module

    async with async_session_maker() as db:
        res = await db.execute(select(Course).where(Course.slug == COURSE_SLUG))
        course = res.scalar_one_or_none()
        if not course:
            print(f"Course '{COURSE_SLUG}' not found — run seed_all.py first.")
            return

        existing = await db.execute(select(Module.id).where(Module.course_id == course.id).limit(1))
        if existing.scalar_one_or_none():
            print("Modules already seeded — skipping insert (deleting stale structure cache).")
        else:
            for order, title, desc in MODULES:
                label = f"CEH v12 - Module{order:02d}.pdf"
                asset = f"ceh-v12/pdfs/{label}"
                module = Module(
                    course_id=course.id,
                    name=title,
                    description=desc,
                    short_description=desc[:497],
                    estimated_minutes=120,
                    order=order,
                    meta_data={
                        "resource_type": "pdf",
                        "resource_label": label,
                        "asset_path": asset,
                    },
                )
                db.add(module)
                await db.flush()  # assign module.id

                db.add(
                    Lesson(
                        module_id=module.id,
                        lesson_type=ContentType.LESSON,
                        name=title,
                        description=desc,
                        short_description=desc[:497],
                        content={},
                        resources=[{"type": "pdf", "title": label, "path": asset}],
                        estimated_minutes=120,
                        xp_reward=50,
                        coins_reward=10,
                        order=1,
                        is_premium=False,
                    )
                )
            await db.commit()
            print("Seeded 20 modules + 20 PDF lessons.")

        # Invalidate the cached course structure so the API serves fresh data.
        await course_cache.delete(f"structure:{course.id}")
        print(f"Structure cache invalidated for {course.id}")


if __name__ == "__main__":
    asyncio.run(main())
