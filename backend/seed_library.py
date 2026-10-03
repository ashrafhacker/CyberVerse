import asyncio
import os
import sys
from uuid import uuid4

# Add the parent directory to sys.path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import async_session_maker

RESOURCES = [
    {
        "title": "Intro to Web Hacking",
        "description": "Learn the fundamentals of web vulnerabilities including XSS, SQLi, and CSRF.",
        "category": "Web Security",
        "resource_type": "course",
        "difficulty": "beginner",
        "provider": "CyberVerse Academy",
        "url": "/courses/web-hacking-101",
        "tags": ["web", "xss", "sqli", "beginner"],
        "is_free": True,
        "is_published": True,
    },
    {
        "title": "Linux Privilege Escalation",
        "description": "Comprehensive guide to elevating privileges on Linux systems using misconfigurations.",
        "category": "Privilege Escalation",
        "resource_type": "article",
        "difficulty": "intermediate",
        "provider": "Security Labs",
        "url": "https://example.com/linux-privesc",
        "tags": ["linux", "privesc", "intermediate"],
        "is_free": True,
        "is_published": True,
    },
    {
        "title": "Network Traffic Analysis",
        "description": "Practice analyzing PCAP files to identify malicious activities and data exfiltration.",
        "category": "Network Security",
        "resource_type": "lab",
        "difficulty": "advanced",
        "provider": "BlueTeam Training",
        "url": "/labs/network-analysis",
        "tags": ["network", "pcap", "wireshark", "advanced"],
        "is_free": True,
        "is_published": True,
    },
    {
        "title": "Google Dorking Mastery",
        "description": "Use advanced search operators to find sensitive information exposed on the public internet.",
        "category": "OSINT",
        "resource_type": "tool",
        "difficulty": "beginner",
        "provider": "CyberVerse Tools",
        "url": "/tools/dorker",
        "tags": ["osint", "dorking", "recon", "beginner"],
        "is_free": True,
        "is_published": True,
    },
    {
        "title": "Malware Reverse Engineering",
        "description": "Decompile and analyze real-world malware samples in a secure sandbox environment.",
        "category": "Reverse Engineering",
        "resource_type": "course",
        "difficulty": "advanced",
        "provider": "Reverser Hub",
        "url": "/courses/malware-analysis",
        "tags": ["malware", "reversing", "ghidra", "advanced"],
        "is_free": True,
        "is_published": True,
    },
    {
        "title": "Cloud Security Posture",
        "description": "Learn how to secure AWS and Azure environments against common misconfigurations.",
        "category": "Cloud Security",
        "resource_type": "article",
        "difficulty": "intermediate",
        "provider": "CloudSec Masters",
        "url": "https://example.com/cloud-security",
        "tags": ["cloud", "aws", "azure", "intermediate"],
        "is_free": True,
        "is_published": True,
    }
]

async def seed_library():
    async with async_session_maker() as db:
        # Check if already populated
        res = await db.execute(text("SELECT count(*) FROM library_resources"))
        if res.scalar() > 0:
            print("Library resources already exist. Skipping seed.")
            return

        for data in RESOURCES:
            query = text("""
                INSERT INTO library_resources 
                (id, title, description, category, resource_type, difficulty, provider, url, tags, is_free, is_published, view_count, created_at, updated_at) 
                VALUES 
                (:id, :title, :description, :category, :resource_type, :difficulty, :provider, :url, :tags, :is_free, :is_published, 0, now(), now())
            """)
            await db.execute(query, {
                "id": str(uuid4()),
                "title": data["title"],
                "description": data["description"],
                "category": data["category"],
                "resource_type": data["resource_type"],
                "difficulty": data["difficulty"],
                "provider": data["provider"],
                "url": data["url"],
                "tags": data["tags"],
                "is_free": data["is_free"],
                "is_published": data["is_published"],
            })
            
        await db.commit()
        print(f"Successfully added {len(RESOURCES)} library resources!")

if __name__ == "__main__":
    asyncio.run(seed_library())
