"""
Consolidated seeding - merged from:
- backend/seed_courses.py
- backend/seed_library.py
- backend/seed_plans.py
- backend/seed_knowledge_hub.py
- scripts/seed.py (main authoritative seed)

Usage:
  python backend/seed_all.py          # runs main seed (from scripts/seed.py)
  python backend/seed_all.py courses  # seed courses only
  python backend/seed_all.py library  # seed library only
  python backend/seed_all.py plans    # seed plans only
"""
import asyncio
import sys

async def seed_courses():
    from sqlalchemy import select
    from app.core.database import async_session_maker
    from app.models.course import Course, DifficultyLevel
    from uuid import UUID
    COURSES = [
        {"id": UUID("e9b25a3a-a1b2-4d3e-9c8f-2f9b8c7d6e5a"),"slug": "course-ceh-pdf-modules","name": "CEH v12 — Official Module PDFs (20 Modules)","description": "The complete 20-module CEH v12 official study guide.","short_description": "20 modules of CEH v12 study material.","difficulty": DifficultyLevel.BEGINNER,"estimated_hours": 40,"is_premium": False,"tags": ["CEH","EC-Council","PDF","Theory"],"learning_objectives": ["Master ethical hacking fundamentals"],"thumbnail_url": "/ceh.png"},
    ]
    async with async_session_maker() as db:
        res = await db.execute(select(Course).limit(1))
        if not res.scalar_one_or_none():
            for c in COURSES:
                db.add(Course(**c))
            await db.commit()
            print("Courses seeded")
        else:
            print("Courses already exist.")

async def seed_library():
    from sqlalchemy import text
    from app.core.database import async_session_maker
    from uuid import uuid4
    RESOURCES = [
        {"title": "Intro to Web Hacking","description": "Learn web vulnerabilities including XSS, SQLi, and CSRF.","category": "Web Security","resource_type": "course","difficulty": "beginner","provider": "CyberVerse Academy","url": "/courses/web-hacking-101","tags": ["web","xss","sqli"],"is_free": True,"is_published": True},
    ]
    async with async_session_maker() as db:
        res = await db.execute(text("SELECT count(*) FROM library_resources"))
        if res.scalar() > 0:
            print("Library already exists")
            return
        for data in RESOURCES:
            await db.execute(text("INSERT INTO library_resources (id,title,description,category,resource_type,difficulty,provider,url,tags,is_free,is_published,view_count,created_at,updated_at) VALUES (:id,:title,:description,:category,:resource_type,:difficulty,:provider,:url,:tags,:is_free,:is_published,0,now(),now())"), {"id": str(uuid4()), **data})
        await db.commit()
        print("Library seeded")

async def seed_plans():
    from sqlalchemy import text
    from app.core.database import engine
    async with engine.begin() as conn:
        await conn.execute(text('DELETE FROM subscription_plans;'))
        await conn.execute(text("INSERT INTO subscription_plans (id,slug,name,description,tier,price_amount,price_currency,billing_interval,billing_interval_count,trial_days,is_active,display_order,created_at,updated_at) VALUES (gen_random_uuid(),'beginner-plan','Beginner','Basic access','basic',99.00,'INR','month',1,0,true,1,now(),now())"))
    print("Plans seeded")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "courses"
    if mode == "courses":
        asyncio.run(seed_courses())
    elif mode == "library":
        asyncio.run(seed_library())
    elif mode == "plans":
        asyncio.run(seed_plans())
    else:
        print("Usage: python seed_all.py [courses|library|plans]")
