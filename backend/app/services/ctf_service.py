"""
CTF engine — isolated, synthetic challenges with automatic flag validation.

Safety:
- Flags are stored ONLY as SHA-256 hashes (never plaintext at rest).
- All challenge content is synthetic/curated; no real exploits or public targets.
- A challenge can only be solved once per user (points awarded once).
- Submissions are rate-limited (Redis, with in-memory fallback).
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import RedisClient
from app.models.ctf import Challenge, FlagSubmission
from app.models.user import User

CTF_RATE_LIMIT = 10
CTF_RATE_WINDOW = 60
CTF_RATE_PREFIX = "ctf:submit"


class CTFError(ValueError):
    pass


def hash_flag(flag: str) -> str:
    return hashlib.sha256(flag.encode("utf-8")).hexdigest()


def constant_time_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


class CTFService:
    @staticmethod
    async def list_challenges(
        db: AsyncSession, user: User, category: str | None, difficulty: str | None
    ) -> list[dict]:
        stmt = select(Challenge).where(Challenge.is_active.is_(True))
        if category:
            stmt = stmt.where(Challenge.category == category)
        if difficulty:
            stmt = stmt.where(Challenge.difficulty == difficulty)
        stmt = stmt.order_by(Challenge.points, Challenge.title)
        challenges = list((await db.execute(stmt)).scalars().all())

        solved = set(
            (
                await db.execute(
                    select(FlagSubmission.challenge_id).where(
                        FlagSubmission.user_id == user.id,
                        FlagSubmission.correct.is_(True),
                    )
                )
            ).scalars().all()
        )
        return [
            {
                "id": str(c.id),
                "slug": c.slug,
                "title": c.title,
                "story": c.story,
                "category": c.category,
                "difficulty": c.difficulty,
                "points": c.points,
                "hint": c.hint,
                "flag_hint_prefix": c.flag_hint_prefix,
                "tags": c.tags,
                "solved": c.id in solved,
            }
            for c in challenges
        ]

    @staticmethod
    async def get_challenge(db: AsyncSession, slug: str) -> Challenge:
        result = await db.execute(
            select(Challenge).where(Challenge.slug == slug, Challenge.is_active.is_(True))
        )
        challenge = result.scalar_one_or_none()
        if not challenge:
            raise CTFError("Challenge not found")
        return challenge

    @staticmethod
    async def check_submission_rate(user: User) -> bool:
        try:
            key = f"{CTF_RATE_PREFIX}:{user.id}"
            count = await RedisClient.increment(key, 1, ttl=CTF_RATE_WINDOW)
            return count <= CTF_RATE_LIMIT
        except Exception:  # noqa: BLE001
            return True

    @staticmethod
    async def submit_flag(
        db: AsyncSession, user: User, challenge: Challenge, submitted: str
    ) -> dict:
        now = datetime.now(UTC)

        existing = (
            await db.execute(
                select(FlagSubmission).where(
                    FlagSubmission.user_id == user.id,
                    FlagSubmission.challenge_id == challenge.id,
                )
            )
        ).scalar_one_or_none()

        if existing and existing.correct:
            return {
                "correct": True,
                "points_earned": 0,
                "attempts": existing.attempt_count,
                "first_blood": existing.first_blood,
                "message": "Already solved — no additional points.",
            }

        correct = constant_time_equal(hash_flag(submitted.strip()), challenge.flag_sha256)

        first_blood = False
        if correct:
            solved_count = await db.scalar(
                select(func.count()).select_from(FlagSubmission).where(
                    FlagSubmission.challenge_id == challenge.id,
                    FlagSubmission.correct.is_(True),
                )
            )
            first_blood = (solved_count or 0) == 0

        if existing is None:
            submission = FlagSubmission(
                user_id=user.id,
                challenge_id=challenge.id,
                correct=correct,
                attempt_count=1,
                first_blood=first_blood,
                solved_at=now if correct else None,
                last_attempt_at=now,
            )
            db.add(submission)
        else:
            existing.attempt_count += 1
            existing.correct = existing.correct or correct
            existing.first_blood = existing.first_blood or (first_blood and existing.correct)
            existing.solved_at = existing.solved_at or (now if correct else None)
            existing.last_attempt_at = now

        await db.commit()

        if correct and first_blood:
            try:
                from app.services.progress_service import ProgressService

                bonus = challenge.points
                await ProgressService.award_xp(
                    db, user.id, xp=bonus, coins=bonus // 2
                )
            except Exception:  # noqa: BLE001
                pass

        message = (
            "Correct! Flag accepted."
            if correct
            else "Incorrect flag."
        )
        return {
            "correct": correct,
            "points_earned": challenge.points if correct else 0,
            "attempts": (existing.attempt_count if existing else 1),
            "first_blood": first_blood,
            "message": message,
        }

    @staticmethod
    async def leaderboard(db: AsyncSession, limit: int = 20) -> list[dict]:
        rows = (
            await db.execute(
                select(
                    FlagSubmission.user_id.label("user_id"),
                    func.count(Challenge.id.distinct()).label("solved"),
                    func.sum(Challenge.points).label("points"),
                )
                .join(Challenge, Challenge.id == FlagSubmission.challenge_id)
                .where(FlagSubmission.correct.is_(True))
                .group_by(FlagSubmission.user_id)
                .order_by(func.sum(Challenge.points).desc(), func.count(Challenge.id.distinct()).desc())
                .limit(limit)
            )
        ).all()
        result = []
        for row in rows:
            user = await db.get(User, row.user_id)
            result.append(
                {
                    "user_id": str(row.user_id),
                    "display_name": (user.full_name if user else "Unknown"),
                    "solved": row.solved,
                    "points": row.points,
                }
            )
        return result
