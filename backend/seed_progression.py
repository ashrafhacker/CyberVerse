"""Seed skill-tree branches and this week's daily/weekly quests.

Skill branches are normally created lazily by SkillService.ensure_branches(); this
script also materializes them up front. Daily/weekly quests use the existing
DailyChallenge / WeeklyChallenge models.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select  # noqa: E402

from app.core.database import async_session_maker  # noqa: E402
from app.models.achievement import DailyChallenge, WeeklyChallenge  # noqa: E402
from app.models.skill import SkillBranch  # noqa: E402
from app.services.skill_service import SkillService  # noqa: E402

DAILY = [
    ("Learn a lesson", "Complete any lesson to keep learning.", "lesson", 1, 40, 15),
    ("Solve a lab objective", "Submit one lab objective successfully.", "lab", 1, 60, 20),
    ("Answer a quiz question", "Attempt a knowledge quiz.", "quiz", 1, 30, 10),
    ("Review an alert", "Open the SOC simulator and triage one alert.", "soc", 1, 25, 10),
]

WEEKLY = [
    ("Weekly Lab Streak", "Complete at least 5 lab objectives this week across any labs.", [
        {"title": "Complete 5 lab objectives", "target": 5, "metric": "lab_objectives"},
    ], 250, 100, False),
    ("Threat Hunter Week", "Investigate one full SOC incident through to resolved status.", [
        {"title": "Resolve an incident", "target": 1, "metric": "incident_resolved"},
    ], 300, 150, False),
]


async def seed():
    async with async_session_maker() as db:
        branches = await SkillService.ensure_branches(db)
        print(f"Ensured {len(branches)} skill branches.")

        now = datetime.now(timezone.utc)

        daily_count = await db.scalar(select(func.count()).select_from(DailyChallenge))
        if daily_count == 0:
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            for title, desc, task_type, req, xp, coins in DAILY:
                db.add(DailyChallenge(
                    challenge_date=today, title=title, description=desc,
                    task_type=task_type, task_requirement=req, xp_reward=xp, coins_reward=coins,
                    is_active=True,
                ))
            print(f"Seeded {len(DAILY)} daily challenges.")
        else:
            print("Daily challenges already exist; skipping.")

        weekly_count = await db.scalar(select(func.count()).select_from(WeeklyChallenge))
        if weekly_count == 0:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=now.weekday())
            end = start + timedelta(days=7)
            for title, desc, objectives, xp, coins, is_premium in WEEKLY:
                db.add(WeeklyChallenge(
                    start_date=start, end_date=end, title=title, description=desc,
                    objectives=objectives, xp_reward=xp, coins_reward=coins, is_active=True, is_premium=is_premium,
                ))
            print(f"Seeded {len(WEEKLY)} weekly challenges.")
        else:
            print("Weekly challenges already exist; skipping.")

        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
