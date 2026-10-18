"""Seed starter game challenges (incl. 'getting-started' linked from /game).

Usage:
    cd backend && PYTHONPATH=/home/neo/CyberVerse/backend ./.venv/bin/python ../scripts/seed_game_challenges.py
Idempotent: existing slugs are skipped.
"""

import asyncio
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.game import ChallengeDifficulty, ChallengeStatus, GameChallenge


def flag_hash(flag: str) -> str:
    return hashlib.sha256(flag.encode()).hexdigest()


CHALLENGES = [
    {
        "title": "Getting Started",
        "slug": "getting-started",
        "description": "Learn how CyberVerse challenges work: read the brief, inspect the page, find the hidden flag, and submit it. No tools needed — just curiosity.",
        "category": "web",
        "difficulty": ChallengeDifficulty.BEGINNER,
        "points": 50,
        "xp": 50,
        "time_limit": 30,
        "status": ChallengeStatus.PUBLISHED,
        "is_published": True,
        "flag": "CV{welcome_to_the_cyberverse}",
        "hints": [
            "Flags look like CV{...}.",
            "View the page source — developers leave comments.",
            "Search the HTML for 'CV{'.",
        ],
        "environment_config": {},
    },
    {
        "title": "Cookie Inspector",
        "slug": "cookie-inspector",
        "description": "A demo shop hides a discount flag in its cookies. Open devtools, inspect storage, and submit the flag.",
        "category": "web",
        "difficulty": ChallengeDifficulty.BEGINNER,
        "points": 100,
        "xp": 100,
        "time_limit": 30,
        "status": ChallengeStatus.PUBLISHED,
        "is_published": True,
        "flag": "CV{cookies_are_tasty}",
        "hints": ["Open browser devtools (F12).", "Look under Application > Cookies."],
        "environment_config": {},
    },
    {
        "title": "Caesar's Secret",
        "slug": "caesar-secret",
        "description": "An intercepted message was encrypted with a Caesar cipher. Shift the letters back and recover the flag.",
        "category": "crypto",
        "difficulty": ChallengeDifficulty.BEGINNER,
        "points": 100,
        "xp": 100,
        "time_limit": 30,
        "status": ChallengeStatus.PUBLISHED,
        "is_published": True,
        "flag": "CV{et_tu_brute_force}",
        "hints": ["Caesar shifts each letter by a fixed number.", "Try all 25 shifts."],
        "environment_config": {},
    },
]


async def main() -> None:
    async with async_session_maker() as db:
        for item in CHALLENGES:
            exists = await db.execute(
                select(GameChallenge).where(GameChallenge.slug == item["slug"])
            )
            if exists.scalar_one_or_none():
                print(f"[skip] {item['slug']} exists")
                continue
            flag = item.pop("flag")
            db.add(GameChallenge(flag_hash=flag_hash(flag), **item))
            print(f"[ok] {item['slug']} seeded")
        await db.commit()
    print("game challenges seed complete")


if __name__ == "__main__":
    asyncio.run(main())
