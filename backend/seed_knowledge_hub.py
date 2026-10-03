import asyncio
from app.core.database import get_db_context
from sqlalchemy import text

resources = [
    {
        "title": "Microsoft Learn",
        "description": "Official learning paths and documentation for Microsoft technologies including Azure.",
        "category": "Cloud",
        "resource_type": "course",
        "difficulty": "intermediate",
        "provider": "Microsoft",
        "url": "https://learn.microsoft.com",
        "tags": ["cloud", "azure", "microsoft"],
        "is_free": True,
        "is_published": True,
    },
    {
        "title": "AWS Skill Builder",
        "description": "Free and paid digital training and certification for Amazon Web Services.",
        "category": "Cloud",
        "resource_type": "course",
        "difficulty": "intermediate",
        "provider": "AWS",
        "url": "https://skillbuilder.aws",
        "tags": ["cloud", "aws", "amazon"],
        "is_free": True,
        "is_published": True,
    },
    {
        "title": "Google Cloud Skills Boost",
        "description": "Learn Google Cloud Platform through hands-on labs and certifications.",
        "category": "Cloud",
        "resource_type": "course",
        "difficulty": "intermediate",
        "provider": "Google",
        "url": "https://www.cloudskillsboost.google",
        "tags": ["cloud", "gcp", "google"],
        "is_free": True,
        "is_published": True,
    },
    {
        "title": "OWASP Foundation",
        "description": "The Open Worldwide Application Security Project (OWASP). Free resources on web application security.",
        "category": "Cybersecurity",
        "resource_type": "article",
        "difficulty": "intermediate",
        "provider": "OWASP",
        "url": "https://owasp.org",
        "tags": ["security", "web", "owasp", "appsec"],
        "is_free": True,
        "is_published": True,
    },
    {
        "title": "MITRE ATT&CK",
        "description": "A globally-accessible knowledge base of adversary tactics and techniques.",
        "category": "Cybersecurity",
        "resource_type": "article",
        "difficulty": "advanced",
        "provider": "MITRE",
        "url": "https://attack.mitre.org",
        "tags": ["threat-intel", "framework", "mitre", "tactics", "techniques"],
        "is_free": True,
        "is_published": True,
    },
    {
        "title": "NIST Cybersecurity Framework",
        "description": "Standards, guidelines, and best practices to manage cybersecurity risk.",
        "category": "Cybersecurity",
        "resource_type": "article",
        "difficulty": "advanced",
        "provider": "NIST",
        "url": "https://www.nist.gov/cyberframework",
        "tags": ["framework", "risk", "compliance", "nist"],
        "is_free": True,
        "is_published": True,
    },
    {
        "title": "CIS Benchmarks",
        "description": "Consensus-based best practices for the secure configuration of systems.",
        "category": "Cybersecurity",
        "resource_type": "article",
        "difficulty": "advanced",
        "provider": "Center for Internet Security",
        "url": "https://www.cisecurity.org/cis-benchmarks",
        "tags": ["compliance", "hardening", "benchmarks", "cis"],
        "is_free": True,
        "is_published": True,
    },
    {
        "title": "Python Documentation",
        "description": "Official documentation for the Python programming language.",
        "category": "Programming",
        "resource_type": "article",
        "difficulty": "beginner",
        "provider": "Python Software Foundation",
        "url": "https://docs.python.org/3/",
        "tags": ["programming", "python", "scripting"],
        "is_free": True,
        "is_published": True,
    },
    {
        "title": "MDN Web Docs",
        "description": "Resources for developers, by developers. HTML, CSS, JavaScript and APIs.",
        "category": "Programming",
        "resource_type": "article",
        "difficulty": "beginner",
        "provider": "Mozilla",
        "url": "https://developer.mozilla.org/",
        "tags": ["web", "javascript", "html", "css", "mdn"],
        "is_free": True,
        "is_published": True,
    },
    {
        "title": "Docker Documentation",
        "description": "Official documentation for Docker containers and related tools.",
        "category": "Cloud",
        "resource_type": "article",
        "difficulty": "intermediate",
        "provider": "Docker",
        "url": "https://docs.docker.com/",
        "tags": ["containers", "docker", "devops"],
        "is_free": True,
        "is_published": True,
    },
    {
        "title": "Kubernetes Documentation",
        "description": "Official documentation for Kubernetes orchestration.",
        "category": "Cloud",
        "resource_type": "article",
        "difficulty": "advanced",
        "provider": "CNCF",
        "url": "https://kubernetes.io/docs/",
        "tags": ["containers", "kubernetes", "orchestration", "k8s"],
        "is_free": True,
        "is_published": True,
    },
]

async def seed():
    async with get_db_context() as db:
        for r in resources:
            stmt = text('''
            INSERT INTO library_resources (id, title, description, category, resource_type, difficulty, provider, url, tags, is_free, is_published, view_count, created_at, updated_at)
            VALUES (gen_random_uuid(), :title, :description, :category, :resource_type, :difficulty, :provider, :url, :tags, :is_free, :is_published, 0, NOW(), NOW())
            ''')
            await db.execute(stmt, r)
        print(f"Seeded {len(resources)} Knowledge Hub resources successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
