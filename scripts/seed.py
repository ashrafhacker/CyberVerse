"""CyberVerse seed script.

Creates the baseline content a fresh deployment needs:
- super admin account
- subscription plans
- a published learning path with one course, module, lessons + quiz
- missions with objectives (including one with a validation rule)
- achievements, FAQ items, encyclopedia articles, app settings

Usage:
    python scripts/seed.py
    # env: DATABASE_URL must point at the target database
    # run from the repo root; requires backend dependencies installed
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.database import Base, create_engine, async_session_maker  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.achievement import Achievement  # noqa: E402
from app.models.analytics import AppSetting, CyberEncyclopediaArticle  # noqa: E402
from app.models.course import (  # noqa: E402
    ContentStatus,
    Course,
    Lesson,
    LearningPath,
    Module,
    Quiz,
    QuizQuestion,
)
from app.models.mission import Mission, MissionObjective  # noqa: E402
from app.models.premium import SubscriptionPlan  # noqa: E402
from app.models.progress import PlayerProgress  # noqa: E402
from app.models.support import FAQItem  # noqa: E402
from app.models.user import Profile, User, UserRole, UserStatus  # noqa: E402

ADMIN_EMAIL = "admin@cyberverse.io"
ADMIN_PASSWORD = "ChangeMe123!"
ADMIN_NAME = "CyberVerse Admin"


async def seed_admin(db: AsyncSession) -> None:
    result = await db.execute(select(User).where(User.email == ADMIN_EMAIL))
    if result.scalar_one_or_none():
        print("[skip] admin already exists")
        return

    admin = User(
        email=ADMIN_EMAIL,
        password_hash=hash_password(ADMIN_PASSWORD),
        full_name=ADMIN_NAME,
        role=UserRole.SUPER_ADMIN,
        status=UserStatus.ACTIVE,
        is_verified=True,
    )
    db.add(admin)
    await db.flush()

    db.add(Profile(user_id=admin.id, username="cyberverse_admin", bio="Platform administrator"))
    db.add(PlayerProgress(user_id=admin.id))
    await db.commit()
    print(f"[ok] admin created ({ADMIN_EMAIL})")


async def seed_plans(db: AsyncSession) -> None:
    result = await db.execute(select(SubscriptionPlan))
    if result.scalars().first():
        print("[skip] plans exist")
        return

    db.add_all(
        [
            SubscriptionPlan(
                name="Free",
                slug="free",
                description="Core learning paths and daily challenges.",
                tier="monthly",
                price_amount=0.0,
                price_currency="USD",
                billing_interval="month",
                billing_interval_count=1,
                features=["core_courses", "daily_challenges", "leaderboard"],
                permissions=["student"],
                is_active=True,
                display_order=0,
            ),
            SubscriptionPlan(
                name="Premium",
                slug="premium",
                description="Advanced labs, AI tutor, unlimited quiz attempts.",
                tier="monthly",
                price_amount=9.0,
                price_currency="USD",
                billing_interval="month",
                billing_interval_count=1,
                features=[
                    "advanced_labs",
                    "ai_tutor",
                    "unlimited_attempts",
                    "early_content",
                ],
                permissions=["premium_student"],
                is_active=True,
                display_order=1,
            ),
        ]
    )
    await db.commit()
    print("[ok] subscription plans seeded")


async def seed_learning_content(db: AsyncSession) -> None:
    result = await db.execute(
        select(LearningPath).where(LearningPath.slug == "cybersecurity-foundations")
    )
    if result.scalar_one_or_none():
        print("[skip] learning path exists")
        return

    path = LearningPath(
        slug="cybersecurity-foundations",
        name="Cybersecurity Foundations",
        description=(
            "Master the core concepts every security professional needs: "
            "networks, cryptography, threats, and defensive fundamentals."
        ),
        short_description="Start here — zero experience required.",
        difficulty="beginner",
        estimated_hours=8,
        learning_objectives=[
            "Explain core security concepts",
            "Read and understand network traffic",
            "Recognize common attack types",
            "Apply basic hardening practices",
        ],
        tags=["foundations", "networking", "cryptography"],
        status=ContentStatus.PUBLISHED,
        order=1,
    )
    db.add(path)
    await db.flush()

    course = Course(
        learning_path_id=path.id,
        slug="intro-to-cybersecurity",
        name="Introduction to Cybersecurity",
        description=(
            "A hands-on introduction: how the internet works, where attacks happen, "
            "and how defenders think."
        ),
        short_description="The on-ramp to the CyberVerse.",
        difficulty="beginner",
        estimated_hours=4,
        learning_objectives=[
            "Understand basic networking concepts",
            "Identify common vulnerabilities",
            "Explain the defender mindset",
        ],
        tags=["intro", "basics"],
        status=ContentStatus.PUBLISHED,
        order=1,
    )
    db.add(course)
    await db.flush()

    module = Module(
        course_id=course.id,
        name="The Fundamentals",
        description="Networks, threats, and the defender mindset.",
        short_description="Module 1 of Introduction to Cybersecurity.",
        estimated_minutes=90,
        order=1,
    )
    db.add(module)
    await db.flush()

    lesson_data = [
        {
            "name": "How the Internet Works",
            "description": "Packets, IP addresses, DNS, and protocols.",
            "content": {
                "blocks": [
                    {"type": "text", "text": "The internet is a network of networks. Devices talk using protocols such as TCP/IP, and names are resolved through DNS."},
                    {"type": "text", "text": "Every device has an IP address, like a mailing address for data."},
                    {"type": "text", "text": "DNS translates human-friendly names (cyberverse.io) into IP addresses."},
                ]
            },
            "estimated_minutes": 20,
            "xp_reward": 25,
            "coins_reward": 10,
            "order": 1,
        },
        {
            "name": "Common Threats",
            "description": "Phishing, malware, social engineering, and more.",
            "content": {
                "blocks": [
                    {"type": "text", "text": "Threats come in many forms. Phishing tricks people into revealing credentials."},
                    {"type": "text", "text": "Malware is software designed to cause harm or steal data."},
                    {"type": "text", "text": "Defenders use layered controls to detect and stop attacks."},
                ]
            },
            "estimated_minutes": 25,
            "xp_reward": 30,
            "coins_reward": 15,
            "order": 2,
        },
        {
            "name": "The Defender Mindset",
            "description": "Think like an attacker, defend like a professional.",
            "content": {
                "blocks": [
                    {"type": "text", "text": "Defenders assume breach: systems will be attacked, so we prepare, detect, and respond."},
                    {"type": "text", "text": "The CIA triad — Confidentiality, Integrity, Availability — guides every decision."},
                    {"type": "text", "text": "In CyberVerse, you practice all of this in safe, simulated environments."},
                ]
            },
            "estimated_minutes": 20,
            "xp_reward": 25,
            "coins_reward": 10,
            "order": 3,
        },
    ]

    lessons = []
    for data in lesson_data:
        lesson = Lesson(module_id=module.id, **data)
        db.add(lesson)
        await db.flush()
        lessons.append(lesson)

    quiz = Quiz(
        lesson_id=lessons[-1].id,
        name="Defender Mindset Check",
        description="Five questions on the core concepts of this module.",
        passing_score=60,
        max_attempts=3,
        xp_reward=50,
        coins_reward=20,
    )
    db.add(quiz)
    await db.flush()

    db.add_all(
        [
            QuizQuestion(
                quiz_id=quiz.id,
                question_type="single",
                question="Which of the following is a core principle of the CIA triad?",
                options=[
                    {"id": "a", "text": "Confidentiality"},
                    {"id": "b", "text": "Compilation"},
                    {"id": "c", "text": "Classification"},
                    {"id": "d", "text": "Compliance"},
                ],
                correct_answer={"id": "a"},
                points=20,
                order=1,
            ),
            QuizQuestion(
                quiz_id=quiz.id,
                question_type="single",
                question="What does DNS do?",
                options=[
                    {"id": "a", "text": "Encrypts network traffic"},
                    {"id": "b", "text": "Translates domain names to IP addresses"},
                    {"id": "c", "text": "Blocks malware"},
                    {"id": "d", "text": "Routes packets between continents"},
                ],
                correct_answer={"id": "b"},
                points=20,
                order=2,
            ),
            QuizQuestion(
                quiz_id=quiz.id,
                question_type="single",
                question="Which attack relies on tricking a person?",
                options=[
                    {"id": "a", "text": "Phishing"},
                    {"id": "b", "text": "Packet sniffing"},
                    {"id": "c", "text": "Port scanning"},
                    {"id": "d", "text": "DNS lookup"},
                ],
                correct_answer={"id": "a"},
                points=20,
                order=3,
            ),
            QuizQuestion(
                quiz_id=quiz.id,
                question_type="true_false",
                question="The 'assume breach' mindset means systems will be attacked.",
                options=[
                    {"id": "t", "text": "True"},
                    {"id": "f", "text": "False"},
                ],
                correct_answer={"id": "t"},
                points=20,
                order=4,
            ),
            QuizQuestion(
                quiz_id=quiz.id,
                question_type="single",
                question="In CyberVerse, where do practical activities happen?",
                options=[
                    {"id": "a", "text": "In simulated sandboxes and authorized labs"},
                    {"id": "b", "text": "On real production systems"},
                    {"id": "c", "text": "On any internet-connected device"},
                    {"id": "d", "text": "In corporate offices"},
                ],
                correct_answer={"id": "a"},
                points=20,
                order=5,
            ),
        ]
    )
    await db.commit()
    print("[ok] learning path + course + module + lessons + quiz seeded")


async def seed_missions(db: AsyncSession) -> None:
    result = await db.execute(select(Mission).where(Mission.slug == "intro-recon-mission"))
    if result.scalar_one_or_none():
        print("[skip] missions exist")
        return

    mission = Mission(
        slug="intro-recon-mission",
        name="Operation: First Contact",
        description=(
            "Your first briefing: investigate a fictional web application "
            "inside the CyberVerse sandbox and confirm it is exposed."
        ),
        short_description="Learn recon the safe way.",
        mission_type="story",
        difficulty="beginner",
        estimated_minutes=15,
        xp_reward=100,
        coins_reward=40,
        is_repeatable=False,
        background_story=(
            "An intern at fictional company 'NovaMart' left a test server running. "
            "The agency wants you to confirm the exposure — inside the sandbox only."
        ),
        status="published",
        prerequisites=[],
        tags=["recon", "beginner"],
    )
    db.add(mission)
    await db.flush()

    db.add_all(
        [
            MissionObjective(
                mission_id=mission.id,
                name="Verify the target is reachable",
                description="Ping the sandbox host sandbox-novamart.sim.cyberverse and note the response.",
                objective_type="terminal",
                order=1,
                xp_reward=50,
                coins_reward=20,
                validation={"require_key": "response", "expected_value": "pong"},
            ),
            MissionObjective(
                mission_id=mission.id,
                name="Identify the exposed service",
                description="Determine which service is exposed on the test server (hint: it's HTTP).",
                objective_type="investigate",
                order=2,
                xp_reward=50,
                coins_reward=20,
                validation={"require_key": "service", "expected_value": "http"},
            ),
        ]
    )
    await db.commit()
    print("[ok] missions seeded")


async def seed_achievements(db: AsyncSession) -> None:
    result = await db.execute(select(Achievement).where(Achievement.slug == "first-steps"))
    if result.scalar_one_or_none():
        print("[skip] achievements exist")
        return

    db.add_all(
        [
            Achievement(
                slug="first-steps",
                name="First Steps",
                description="Complete your first lesson.",
                category="learning",
                icon="footprints",
                rarity="common",
                xp_reward=50,
                coins_reward=10,
                criteria_type="lessons_completed",
                criteria_value=1,
            ),
            Achievement(
                slug="mission-accomplished",
                name="Mission Accomplished",
                description="Complete your first mission.",
                category="mission",
                icon="target",
                rarity="rare",
                xp_reward=100,
                coins_reward=25,
                criteria_type="missions_completed",
                criteria_value=1,
            ),
            Achievement(
                slug="streak-7",
                name="Consistent Operator",
                description="Maintain a 7-day learning streak.",
                category="challenge",
                icon="flame",
                rarity="epic",
                xp_reward=250,
                coins_reward=50,
                criteria_type="streak_days",
                criteria_value=7,
            ),
        ]
    )
    await db.commit()
    print("[ok] achievements seeded")


async def seed_misc(db: AsyncSession) -> None:
    result = await db.execute(select(FAQItem).limit(1))
    if result.scalars().first():
        print("[skip] faq/settings/articles exist")
        return

    db.add_all(
        [
            FAQItem(
                question="Is everything in CyberVerse legal?",
                answer=(
                    "Yes. Every mission runs inside CyberVerse's own simulated environments "
                    "or labs you own and explicitly authorize. No real third-party systems are ever touched."
                ),
                category="general",
                is_published=True,
                order=1,
            ),
            FAQItem(
                question="Do I need prior experience?",
                answer="No. Learning paths start from zero and build up progressively.",
                category="learning",
                is_published=True,
                order=2,
            ),
            FAQItem(
                question="Can I connect my own lab?",
                answer=(
                    "Yes — once Safe Labs ships, you can connect VMs, Docker labs, or home labs "
                    "after verifying ownership and declaring scope."
                ),
                category="labs",
                is_published=True,
                order=3,
            ),
        ]
    )

    db.add_all(
        [
            CyberEncyclopediaArticle(
                slug="phishing",
                title="Phishing",
                summary="Deceptive messages that trick users into revealing credentials or running malware.",
                content=(
                    "Phishing is a social engineering attack delivered by email, SMS, or messaging. "
                    "Defenders reduce risk through awareness training, email filtering, and MFA."
                ),
                topic="attacks",
                difficulty="beginner",
                is_published=True,
            ),
            CyberEncyclopediaArticle(
                slug="defense-in-depth",
                title="Defense in Depth",
                summary="Layered security controls so no single failure compromises the system.",
                content=(
                    "Defense in depth uses overlapping controls: firewalls, EDR, MFA, segmentation, "
                    "backups, and incident response plans."
                ),
                topic="defense",
                difficulty="beginner",
                is_published=True,
            ),
        ]
    )

    db.add_all(
        [
            AppSetting(key="platform.name", value={"value": "CyberVerse"}, is_public=True),
            AppSetting(
                key="onboarding.mission_enabled",
                value={"value": True},
                is_public=False,
            ),
            AppSetting(
                key="security.allow_labs",
                value={"value": False},
                is_public=False,
            ),
        ]
    )
    await db.commit()
    print("[ok] faq + encyclopedia + settings seeded")


async def main() -> None:
    engine = create_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as db:
        await seed_admin(db)
        await seed_plans(db)
        await seed_learning_content(db)
        await seed_missions(db)
        await seed_achievements(db)
        await seed_misc(db)

    await engine.dispose()
    print("\nSeed complete. Default admin: %s / %s" % (ADMIN_EMAIL, ADMIN_PASSWORD))


if __name__ == "__main__":
    asyncio.run(main())
