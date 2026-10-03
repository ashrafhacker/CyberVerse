from datetime import UTC
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.progress import LessonProgress, PlayerProgress
from app.models.user import Profile


class LevelSystem:
    """XP and leveling rules for CyberVerse."""

    BASE_XP = 100
    XP_GROWTH = 1.15
    MAX_LEVEL = 100

    RANKS = [
        (50, "Cyberverse Elite"),
        (40, "Senior Security Engineer"),
        (30, "Security Engineer"),
        (20, "Security Specialist"),
        (10, "Security Analyst"),
        (5, "Junior Analyst"),
        (1, "Cyber Recruit"),
    ]

    @classmethod
    def rank_for_level(cls, level: int) -> str:
        for threshold, title in cls.RANKS:
            if level >= threshold:
                return title
        return "Cyber Recruit"

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
    async def award_xp(
        db: AsyncSession,
        user_id: UUID,
        xp: int,
        coins: int = 0,
        source_type: str | None = None,
        source_id: str | None = None,
        reason: str = "",
    ) -> dict:
        from app.models.xp_transaction import XpTransaction

        # Idempotency: identical source cannot award twice
        if source_type is not None:
            existing = await db.execute(
                select(XpTransaction).where(
                    XpTransaction.user_id == user_id,
                    XpTransaction.source_type == source_type,
                    XpTransaction.source_id == (source_id or ""),
                )
            )
            if existing.scalar_one_or_none() is not None:
                return {"xp_awarded": 0, "coins_awarded": 0, "duplicate": True}
            db.add(
                XpTransaction(
                    user_id=user_id,
                    source_type=source_type,
                    source_id=source_id or "",
                    amount=xp,
                    reason=reason,
                )
            )

        progress = await ProgressService.get_or_create_player_progress(db, user_id)
        progress.total_xp += xp
        progress.total_coins += coins

        profile_result = await db.execute(select(Profile).where(Profile.user_id == user_id))
        profile = profile_result.scalar_one_or_none()
        if profile:
            profile.xp += xp
            profile.coins += coins
            profile.level = LevelSystem.level_from_xp(profile.xp)
            profile.rank = LevelSystem.rank_for_level(profile.level)

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
            "rank": LevelSystem.rank_for_level(new_level),
            "leveled_up": leveled_up,
            "level_info": LevelSystem.progress_to_next_level(progress.total_xp),
        }

    @staticmethod
    async def update_lesson_progress(
        db: AsyncSession,
        user_id: UUID,
        lesson_id: UUID,
        status: str,
        progress_percentage: int | None = None,
        time_spent: int = 0,
        position_seconds: float | None = None,
        watched_seconds: float | None = None,
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
                rewards = await ProgressService._award_lesson_completion(db, user_id, lesson_id)
                lesson_progress.xp_earned += rewards.get("xp", 0)
                lesson_progress.coins_earned += rewards.get("coins", 0)

        if progress_percentage is not None:
            lesson_progress.progress_percentage = max(
                lesson_progress.progress_percentage or 0, progress_percentage
            )
        # Playback telemetry — lets the player resume where the learner left
        # off and gives the completion check an auditable watch record.
        if position_seconds is not None or watched_seconds is not None:
            last_position = dict(lesson_progress.last_position or {})
            if position_seconds is not None:
                last_position["seconds"] = round(float(position_seconds), 1)
            if watched_seconds is not None:
                last_position["watched_seconds"] = round(float(watched_seconds), 1)
            lesson_progress.last_position = last_position
        lesson_progress.time_spent_seconds += time_spent
        lesson_progress.attempts += 1

        await db.commit()
        await db.refresh(lesson_progress)
        return lesson_progress

    @staticmethod
    async def _award_lesson_completion(db: AsyncSession, user_id: UUID, lesson_id: UUID) -> dict:
        from app.models.course import Lesson

        result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
        lesson = result.scalar_one_or_none()
        if not lesson:
            return {"xp": 0, "coins": 0}

        progress = await ProgressService.get_or_create_player_progress(db, user_id)
        progress.lessons_completed += 1
        await ProgressService.award_xp(
            db, user_id, xp=lesson.xp_reward, coins=lesson.coins_reward
        )
        await ProgressService._maybe_complete_course(db, user_id, lesson.module_id)
        return {"xp": lesson.xp_reward, "coins": lesson.coins_reward}

    @staticmethod
    async def _maybe_complete_course(db: AsyncSession, user_id: UUID, module_id: UUID) -> None:
        """
        If every lesson of a course is completed, finalize the enrollment
        and auto-issue a certificate.
        """
        from app.models.course import Course, Lesson, Module
        from app.models.progress import Enrollment, LessonProgress
        from app.services.certificate_service import CertificateService

        module_result = await db.execute(select(Module).where(Module.id == module_id))
        module = module_result.scalar_one_or_none()
        if not module:
            return
        course_id = module.course_id

        total_result = await db.execute(
            select(func.count(Lesson.id)).where(Lesson.module_id.in_(
                select(Module.id).where(Module.course_id == course_id)
            ))
        )
        total = total_result.scalar_one()

        done_result = await db.execute(
            select(func.count(LessonProgress.id)).where(
                LessonProgress.user_id == user_id,
                LessonProgress.status == "completed",
                LessonProgress.lesson_id.in_(
                    select(Lesson.id).where(Lesson.module_id.in_(
                        select(Module.id).where(Module.course_id == course_id)
                    ))
                ),
            )
        )
        done = done_result.scalar_one()
        if total == 0 or done < total:
            return

        course_result = await db.execute(select(Course).where(Course.id == course_id))
        course = course_result.scalar_one_or_none()
        if not course:
            return

        enrollment_result = await db.execute(
            select(Enrollment).where(
                Enrollment.user_id == user_id,
                Enrollment.course_id == course_id,
            )
        )
        enrollment = enrollment_result.scalar_one_or_none()
        if not enrollment:
            enrollment = Enrollment(
                user_id=user_id,
                course_id=course_id,
                status="in_progress",
            )
            db.add(enrollment)
            await db.flush()

        if enrollment.status != "completed":
            enrollment.status = "completed"
            enrollment.progress_percentage = 100
            from datetime import datetime

            enrollment.completed_at = datetime.now(UTC)

        await CertificateService.issue_course_certificate(db, user_id, course, enrollment)
        await db.flush()
