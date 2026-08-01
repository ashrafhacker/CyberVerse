from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.progress import LessonProgress, PlayerProgress
from app.models.user import Profile


class LevelSystem:
    """XP and leveling rules for CyberVerse."""

    BASE_XP = 100
    XP_GROWTH = 1.15
    MAX_LEVEL = 100

    @staticmethod
    def xp_for_level(level: int) -> int:
        """XP required to reach a given level."""
        if level <= 1:
            return 0
        return int(LevelSystem.BASE_XP * (LevelSystem.XP_GROWTH ** (level - 2)))

    @staticmethod
    def level_from_xp(total_xp: int) -> int:
        level = 1
        while level < LevelSystem.MAX_LEVEL:
            next_level_xp = LevelSystem.xp_for_level(level + 1)
            if total_xp < next_level_xp:
                break
            level += 1
        return level

    @staticmethod
    def progress_to_next_level(total_xp: int) -> dict:
        level = LevelSystem.level_from_xp(total_xp)
        current_xp = LevelSystem.xp_for_level(level)
        next_xp = LevelSystem.xp_for_level(level + 1) if level < LevelSystem.MAX_LEVEL else current_xp
        span = max(1, next_xp - current_xp)
        progress = min(100, int((total_xp - current_xp) / span * 100))
        return {
            "level": level,
            "current_xp": total_xp,
            "current_level_xp": current_xp,
            "next_level_xp": next_xp,
            "xp_into_level": total_xp - current_xp,
            "xp_needed": next_xp - total_xp,
            "progress_percent": progress,
        }


class ProgressService:
    @staticmethod
    async def get_or_create_player_progress(db: AsyncSession, user_id: UUID) -> PlayerProgress:
        result = await db.execute(
            select(PlayerProgress).where(PlayerProgress.user_id == user_id)
        )
        progress = result.scalar_one_or_none()
        if not progress:
            progress = PlayerProgress(user_id=user_id)
            db.add(progress)
            await db.commit()
            await db.refresh(progress)
        return progress

    @staticmethod
    async def award_xp(db: AsyncSession, user_id: UUID, xp: int, coins: int = 0) -> dict:
        progress = await ProgressService.get_or_create_player_progress(db, user_id)
        progress.total_xp += xp
        progress.total_coins += coins

        profile_result = await db.execute(select(Profile).where(Profile.user_id == user_id))
        profile = profile_result.scalar_one_or_none()
        if profile:
            profile.xp += xp
            profile.coins += coins
            old_level = profile.level
            profile.level = LevelSystem.level_from_xp(profile.xp)

        new_level = LevelSystem.level_from_xp(progress.total_xp)
        leveled_up = new_level > progress.current_level
        progress.current_level = new_level

        await db.commit()

        return {
            "xp_awarded": xp,
            "coins_awarded": coins,
            "total_xp": progress.total_xp,
            "total_coins": progress.total_coins,
            "level": new_level,
            "leveled_up": leveled_up,
            "level_info": LevelSystem.progress_to_next_level(progress.total_xp),
        }

    @staticmethod
    async def update_lesson_progress(
        db: AsyncSession,
        user_id: UUID,
        lesson_id: UUID,
        status: str,
        progress_percentage: Optional[int] = None,
        time_spent: int = 0,
    ) -> LessonProgress:
        result = await db.execute(
            select(LessonProgress).where(
                LessonProgress.user_id == user_id,
                LessonProgress.lesson_id == lesson_id,
            )
        )
        lesson_progress = result.scalar_one_or_none()

        if not lesson_progress:
            lesson_progress = LessonProgress(
                user_id=user_id,
                lesson_id=lesson_id,
                status=status,
            )
            db.add(lesson_progress)

        if status == "in_progress" and lesson_progress.status != "completed":
            lesson_progress.status = "in_progress"
        elif status == "completed":
            was_completed = lesson_progress.status == "completed"
            lesson_progress.status = "completed"
            lesson_progress.completed_at = func.now()
            if not was_completed:
                # Award rewards on first completion
                await ProgressService._award_lesson_completion(db, user_id, lesson_id)

        if progress_percentage is not None:
            lesson_progress.progress_percentage = max(
                lesson_progress.progress_percentage or 0, progress_percentage
            )
        lesson_progress.time_spent_seconds += time_spent
        lesson_progress.attempts += 1

        await db.commit()
        await db.refresh(lesson_progress)
        return lesson_progress

    @staticmethod
    async def _award_lesson_completion(db: AsyncSession, user_id: UUID, lesson_id: UUID) -> None:
        from app.models.course import Lesson

        result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
        lesson = result.scalar_one_or_none()
        if not lesson:
            return

        progress = await ProgressService.get_or_create_player_progress(db, user_id)
        progress.lessons_completed += 1
        await ProgressService.award_xp(
            db, user_id, xp=lesson.xp_reward, coins=lesson.coins_reward
        )