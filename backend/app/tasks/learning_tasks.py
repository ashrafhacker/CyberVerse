from datetime import datetime, timedelta, timezone

from celery import shared_task


@shared_task(name="app.tasks.learning_tasks.rotate_daily_challenges")
def rotate_daily_challenges() -> dict:
    import asyncio
    import random

    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.core.database import engine
    from app.models.achievement import DailyChallenge

    TASKS = [
        ("Complete a lesson", "lesson", 1, 60, 25),
        ("Pass a quiz", "quiz", 1, 80, 30),
        ("Complete a mission", "mission", 1, 100, 50),
        ("Spend 15 minutes learning", "time", 900, 40, 15),
        ("Complete a practice lab", "lab", 1, 90, 40),
    ]

    async def _run():
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        today = datetime.now(timezone.utc).date()

        async with session_factory() as db:
            # Archive old challenges
            await db.execute(
                delete(DailyChallenge).where(
                    DailyChallenge.challenge_date < datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
                )
            )

            for _ in range(3):
                task_type, name, requirement, xp, coins = random.choice(TASKS)
                db.add(
                    DailyChallenge(
                        challenge_date=datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc),
                        title=f"Daily: {name.capitalize()}",
                        description=f"Complete {requirement} {name}(s) today to earn {xp} XP and {coins} coins.",
                        task_type=task_type,
                        task_requirement=requirement,
                        xp_reward=xp,
                        coins_reward=coins,
                        is_active=True,
                    )
                )
            await db.commit()
            return 3

    count = asyncio.run(_run())
    return {"daily_challenges_created": count}


@shared_task(name="app.tasks.learning_tasks.rotate_weekly_challenges")
def rotate_weekly_challenges() -> dict:
    import asyncio

    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.core.database import engine
    from app.models.achievement import WeeklyChallenge

    async def _run():
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)

        async with session_factory() as db:
            await db.execute(
                delete(WeeklyChallenge).where(WeeklyChallenge.end_date < now)
            )
            db.add(
                WeeklyChallenge(
                    start_date=start,
                    end_date=end,
                    title="Weekly Challenge: Security Operations Week",
                    description=(
                        "Complete 5 lessons, 2 quizzes, and 1 mission to earn bonus XP "
                        "and an exclusive weekly badge."
                    ),
                    objectives=[
                        {"type": "lesson", "requirement": 5},
                        {"type": "quiz", "requirement": 2},
                        {"type": "mission", "requirement": 1},
                    ],
                    xp_reward=500,
                    coins_reward=200,
                    is_active=True,
                )
            )
            await db.commit()
            return 1

    count = asyncio.run(_run())
    return {"weekly_challenges_created": count}