import asyncio
import os
import sys
from uuid import UUID

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.course import Course, DifficultyLevel

COURSES = [
    {
        "id": UUID("e9b25a3a-a1b2-4d3e-9c8f-2f9b8c7d6e5a"),
        "slug": "course-ceh-pdf-modules",
        "name": "CEH v12 — Official Module PDFs (20 Modules)",
        "description": "The complete 20-module CEH v12 official study guide covering all exam domains.",
        "short_description": "20 modules of CEH v12 study material.",
        "difficulty": DifficultyLevel.BEGINNER,
        "estimated_hours": 40,
        "is_premium": False,
        "tags": ["CEH", "EC-Council", "PDF", "Theory"],
        "learning_objectives": ["Master ethical hacking fundamentals", "Understand network scanning"],
        "thumbnail_url": "/ceh.png"
    },
    {
        "id": UUID("f8a14b29-b0c3-5e4d-8d7e-1e8a9b6c5d4f"),
        "slug": "course-ceh-system-network",
        "name": "CEH v12 — System & Network Security (Video)",
        "description": "System penetration testing, malware threats, network sniffing, ARP poisoning, session hijacking, and evading IDS / firewalls.",
        "short_description": "Advanced system and network security techniques.",
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "estimated_hours": 25,
        "is_premium": True,
        "tags": ["CEH", "System Hacking", "Malware", "Network"],
        "learning_objectives": ["Analyze malware threats", "Evade IDS and firewalls"],
        "thumbnail_url": "/network.png"
    },
    {
        "id": UUID("d7c35a18-c9b2-6f5e-7e6d-0d9a8b5c4e3a"),
        "slug": "course-ceh-advanced-cybersec",
        "name": "CEH v12 — Advanced Cybersecurity (Video)",
        "description": "Web server attacks, web application hacking, SQL injection, wireless network hacking, mobile platform hacking, cloud computing security.",
        "short_description": "Deep dive into web and cloud security.",
        "difficulty": DifficultyLevel.ADVANCED,
        "estimated_hours": 35,
        "is_premium": True,
        "tags": ["CEH", "Web Hacking", "SQL Injection", "Wireless"],
        "learning_objectives": ["Exploit web apps", "Perform SQL injection", "Hack wireless networks"],
        "thumbnail_url": "/web.png"
    },
    {
        "id": UUID("c6b24a07-d8a1-7e6f-6f5c-9c8a7b4d3f2b"),
        "slug": "course-burp-suite",
        "name": "Burp Suite Live Practical",
        "description": "Hands-on sessions with Burp Suite Pro: OTP bypass, account takeover via IDOR, automated form flooding, response manipulation.",
        "short_description": "Master Burp Suite Pro.",
        "difficulty": DifficultyLevel.ADVANCED,
        "estimated_hours": 15,
        "is_premium": True,
        "tags": ["Burp Suite", "Web Hacking", "OTP Bypass", "IDOR"],
        "learning_objectives": ["Bypass OTPs", "Manipulate responses", "Automate form flooding"],
        "thumbnail_url": "/burp.png"
    },
    {
        "id": UUID("b5a139f6-e790-8d7e-5e4b-8b7a6c5e2a1c"),
        "slug": "course-http-debugger",
        "name": "HTTP Debugger Pro Basics",
        "description": "Learn to intercept and manipulate HTTP traffic with HTTP Debugger Pro, including API parameter tampering.",
        "short_description": "HTTP Interception and Debugging.",
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "estimated_hours": 5,
        "is_premium": False,
        "tags": ["HTTP", "Traffic Interception", "API Hacking"],
        "learning_objectives": ["Intercept HTTP traffic", "Tamper with API parameters"],
        "thumbnail_url": "/http.png"
    }
]

async def seed_courses():
    async with async_session_maker() as db:
        res = await db.execute(select(Course).limit(1))
        if not res.scalar_one_or_none():
            for c in COURSES:
                course = Course(**c)
                db.add(course)
            await db.commit()
            print("Courses seeded successfully!")
        else:
            print("Courses already exist.")

if __name__ == "__main__":
    asyncio.run(seed_courses())
