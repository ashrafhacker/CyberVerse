from datetime import UTC
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.progress import LessonProgress
from app.schemas.base import APIResponse
from app.services.progress_service import ProgressService

router = APIRouter()


class UpdateLessonProgressRequest(BaseModel):
    status: str = Field(..., pattern="^(not_started|in_progress|completed)$")
    progress_percentage: int | None = Field(None, ge=0, le=100)
    time_spent_seconds: int = Field(0, ge=0)
    # Playback telemetry used to verify completion of video lessons:
    position_seconds: float | None = Field(None, ge=0)
    watched_seconds: float | None = Field(None, ge=0)


# A lesson may only be marked completed once the learner has actually
# consumed at least this percentage of its content (video watch-through
# ratio tracked by the player, or an explicit action for PDFs).
COMPLETION_MIN_PERCENT = 90


@router.get("/overview", response_model=APIResponse[dict], summary="Get player progress overview")
async def progress_overview(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    progress = await ProgressService.get_or_create_player_progress(db, user.id)
    return APIResponse[dict](
        data={
            "total_xp": progress.total_xp,
            "total_coins": progress.total_coins,
            "level": progress.current_level,
            "lessons_completed": progress.lessons_completed,
            "missions_completed": progress.missions_completed,
            "quizzes_passed": progress.quizzes_passed,
            "labs_completed": progress.labs_completed,
            "learning_streak": progress.learning_streak,
            "longest_streak": progress.longest_streak,
            "time_spent_seconds": progress.time_spent_seconds,
            "statistics": progress.statistics,
            "current_mission_id": str(progress.current_mission_id) if progress.current_mission_id else None,
            "current_course_id": str(progress.current_course_id) if progress.current_course_id else None,
        }
    )


@router.get("/lessons", response_model=APIResponse[list], summary="List lesson progress")
async def list_lesson_progress(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LessonProgress)
        .where(LessonProgress.user_id == user.id)
        .order_by(LessonProgress.updated_at.desc())
    )
    entries = result.scalars().all()
    return APIResponse[list](
        data=[
            {
                "lesson_id": str(lp.lesson_id),
                "status": lp.status.value if hasattr(lp.status, "value") else lp.status,
                "progress_percentage": lp.progress_percentage,
                "xp_earned": lp.xp_earned,
                "coins_earned": lp.coins_earned,
                "attempts": lp.attempts,
                "time_spent_seconds": lp.time_spent_seconds,
                "last_position": lp.last_position,
                "completed_at": lp.completed_at.isoformat() if lp.completed_at else None,
                "updated_at": lp.updated_at.isoformat() if lp.updated_at else None,
            }
            for lp in entries
        ]
    )


@router.post("/lessons/{lesson_id}", response_model=APIResponse[dict], summary="Update lesson progress")
async def update_lesson_progress(
    lesson_id: UUID,
    request: UpdateLessonProgressRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    # ── Completion verification ────────────────────────────────────────────
    # Never trust a bare "completed" flag: require that the learner has
    # actually watched/read at least COMPLETION_MIN_PERCENT of the lesson.
    # The percentage is the max of what the client reports now and what the
    # server has already accumulated (progress only ever moves forward).
    if request.status == "completed":
        existing = await db.execute(
            select(LessonProgress.progress_percentage).where(
                LessonProgress.user_id == user.id,
                LessonProgress.lesson_id == lesson_id,
            )
        )
        stored_pct = existing.scalar_one_or_none() or 0
        effective_pct = max(request.progress_percentage or 0, stored_pct)
        if effective_pct < COMPLETION_MIN_PERCENT:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Completion not verified: only {effective_pct}% of this lesson "
                    f"has been consumed — watch at least {COMPLETION_MIN_PERCENT}% "
                    "before marking it complete."
                ),
            )

    lesson_progress = await ProgressService.update_lesson_progress(
        db,
        user_id=user.id,
        lesson_id=lesson_id,
        status=request.status,
        progress_percentage=request.progress_percentage,
        time_spent=request.time_spent_seconds,
        position_seconds=request.position_seconds,
        watched_seconds=request.watched_seconds,
    )
    return APIResponse[dict](
        data={
            "lesson_id": str(lesson_progress.lesson_id),
            "status": lesson_progress.status.value if hasattr(lesson_progress.status, "value") else lesson_progress.status,
            "progress_percentage": lesson_progress.progress_percentage,
            "xp_earned": lesson_progress.xp_earned,
            "coins_earned": lesson_progress.coins_earned,
        }
    )


@router.get("/recommendations", response_model=APIResponse[list], summary="Get learning recommendations")
async def get_recommendations(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    from app.services.ai_service import AIService

    ai = AIService()
    recommendations = await ai.recommend_learning_path(db, user.id)
    return APIResponse[list](data=recommendations)


@router.post("/streak/checkin", response_model=APIResponse[dict], summary="Daily learning check-in")
async def daily_checkin(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime

    progress = await ProgressService.get_or_create_player_progress(db, user.id)
    now = datetime.now(UTC)
    today = now.date()

    last_day = progress.last_active_day
    if last_day and last_day.date() == today:
        return APIResponse[dict](
            data={"already_checked_in": True, "streak": progress.learning_streak}
        )

    if last_day and (today - last_day.date()).days == 1:
        progress.learning_streak += 1
    else:
        progress.learning_streak = 1

    progress.longest_streak = max(progress.longest_streak, progress.learning_streak)
    progress.last_active_day = now

    bonus_xp = min(10 + (progress.learning_streak - 1) * 5, 100)
    bonus_coins = min(5 + (progress.learning_streak - 1) * 2, 50)

    rewards = await ProgressService.award_xp(db, user.id, bonus_xp, bonus_coins)

    return APIResponse[dict](
        data={
            "already_checked_in": False,
            "streak": progress.learning_streak,
            "longest_streak": progress.longest_streak,
            "bonus_xp": bonus_xp,
            "bonus_coins": bonus_coins,
            "level": rewards["level"],
        }
    )


@router.post("/xp", response_model=APIResponse[dict], summary="Award XP/coins (game server callback)")
async def award_xp(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    xp: int = 0,
    coins: int = 0,
):

    if xp < 0 or coins < 0 or xp > 100000 or coins > 100000:
        raise HTTPException(status_code=400, detail="Invalid reward amounts")
    result = await ProgressService.award_xp(db, user.id, xp, coins)
    return APIResponse[dict](data=result)
