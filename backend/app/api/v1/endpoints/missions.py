from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.mission import Mission, MissionObjective, MissionProgress, ObjectiveProgress
from app.schemas.base import APIResponse, PaginatedResponse
from app.services.course_service import CourseService
from app.services.progress_service import ProgressService

router = APIRouter()


class ObjectiveSubmission(BaseModel):
    objective_id: UUID
    data: dict = Field(default_factory=dict)


@router.get("/", response_model=APIResponse[PaginatedResponse], summary="List missions")
async def list_missions(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    mission_type: str = Query(None),
):
    missions, total = await CourseService.list_missions(
        db, mission_type=mission_type, page=page, page_size=page_size
    )

    items = [
        {
            "id": str(m.id),
            "slug": m.slug,
            "name": m.name,
            "short_description": m.short_description,
            "mission_type": m.mission_type.value if hasattr(m.mission_type, "value") else m.mission_type,
            "difficulty": m.difficulty.value if hasattr(m.difficulty, "value") else m.difficulty,
            "estimated_minutes": m.estimated_minutes,
            "xp_reward": m.xp_reward,
            "coins_reward": m.coins_reward,
            "is_premium": m.is_premium,
            "tags": m.tags,
            "thumbnail_url": m.thumbnail_url,
        }
        for m in missions
    ]

    data = PaginatedResponse.create(items, total, page, page_size)
    return APIResponse[PaginatedResponse](data=data)


@router.get("/daily", response_model=APIResponse[list], summary="Get today's daily challenges")
async def get_daily_challenges(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone

    from app.models.achievement import DailyChallenge

    today = datetime.now(timezone.utc).date()
    result = await db.execute(
        select(DailyChallenge).where(
            DailyChallenge.challenge_date >= today.strftime("%Y-%m-%d"),
            DailyChallenge.is_active.is_(True),
        )
    )
    challenges = result.scalars().all()
    return APIResponse[list](
        data=[
            {
                "id": str(c.id),
                "title": c.title,
                "description": c.description,
                "task_type": c.task_type,
                "task_requirement": c.task_requirement,
                "xp_reward": c.xp_reward,
                "coins_reward": c.coins_reward,
            }
            for c in challenges
        ]
    )


@router.get("/weekly", response_model=APIResponse[list], summary="Get weekly challenges")
async def get_weekly_challenges(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone

    from app.models.achievement import WeeklyChallenge

    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(WeeklyChallenge).where(
            WeeklyChallenge.start_date <= now,
            WeeklyChallenge.end_date >= now,
            WeeklyChallenge.is_active.is_(True),
        )
    )
    challenges = result.scalars().all()
    return APIResponse[list](
        data=[
            {
                "id": str(c.id),
                "title": c.title,
                "description": c.description,
                "objectives": c.objectives,
                "xp_reward": c.xp_reward,
                "coins_reward": c.coins_reward,
                "end_date": c.end_date.isoformat() if c.end_date else None,
            }
            for c in challenges
        ]
    )


@router.get("/{mission_id}", response_model=APIResponse[dict], summary="Get mission details")
async def get_mission(
    mission_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Mission).where(Mission.id == mission_id))
    mission = result.scalar_one_or_none()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    objective_result = await db.execute(
        select(MissionObjective)
        .where(MissionObjective.mission_id == mission_id)
        .order_by(MissionObjective.order)
    )
    objectives = objective_result.scalars().all()

    return APIResponse[dict](
        data={
            "id": str(mission.id),
            "slug": mission.slug,
            "name": mission.name,
            "description": mission.description,
            "background_story": mission.background_story,
            "mission_type": mission.mission_type.value if hasattr(mission.mission_type, "value") else mission.mission_type,
            "difficulty": mission.difficulty.value if hasattr(mission.difficulty, "value") else mission.difficulty,
            "estimated_minutes": mission.estimated_minutes,
            "xp_reward": mission.xp_reward,
            "coins_reward": mission.coins_reward,
            "is_repeatable": mission.is_repeatable,
            "objectives": [
                {
                    "id": str(o.id),
                    "name": o.name,
                    "description": o.description,
                    "objective_type": o.objective_type.value if hasattr(o.objective_type, "value") else o.objective_type,
                    "order": o.order,
                    "xp_reward": o.xp_reward,
                    "coins_reward": o.coins_reward,
                }
                for o in objectives
            ],
        }
    )


@router.post("/{mission_id}/start", response_model=APIResponse[dict], summary="Start a mission")
async def start_mission(
    mission_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    mission_result = await db.execute(select(Mission).where(Mission.id == mission_id))
    mission = mission_result.scalar_one_or_none()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    progress_result = await db.execute(
        select(MissionProgress).where(
            MissionProgress.user_id == user.id,
            MissionProgress.mission_id == mission_id,
        )
    )
    progress = progress_result.scalar_one_or_none()

    if not progress:
        from datetime import datetime, timezone

        progress = MissionProgress(
            user_id=user.id,
            mission_id=mission_id,
            status="in_progress",
            started_at=datetime.now(timezone.utc),
        )
        db.add(progress)
        await db.commit()
        await db.refresh(progress)

    player_progress = await ProgressService.get_or_create_player_progress(db, user.id)
    player_progress.current_mission_id = mission_id
    await db.commit()

    return APIResponse[dict](
        data={
            "mission_progress_id": str(progress.id),
            "status": progress.status,
            "current_objective_index": progress.current_objective_index,
        }
    )


@router.post("/{mission_id}/objectives/submit", response_model=APIResponse[dict], summary="Submit objective completion")
async def submit_objective(
    mission_id: UUID,
    submission: ObjectiveSubmission,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone

    objective_result = await db.execute(
        select(MissionObjective).where(
            MissionObjective.id == submission.objective_id,
            MissionObjective.mission_id == mission_id,
        )
    )
    objective = objective_result.scalar_one_or_none()
    if not objective:
        raise HTTPException(status_code=404, detail="Objective not found")

    progress_result = await db.execute(
        select(MissionProgress).where(
            MissionProgress.user_id == user.id,
            MissionProgress.mission_id == mission_id,
        )
    )
    progress = progress_result.scalar_one_or_none()
    if not progress:
        raise HTTPException(status_code=404, detail="Mission not started. Start the mission first.")

    # Simulated validation against the objective's validation rules
    validation_rules = objective.validation or {}
    passed = True
    if validation_rules.get("require_key"):
        submitted_key = submission.data.get(validation_rules.get("require_key"))
        if submitted_key != validation_rules.get("expected_value"):
            passed = False

    op_result = await db.execute(
        select(ObjectiveProgress).where(
            ObjectiveProgress.mission_progress_id == progress.id,
            ObjectiveProgress.objective_id == objective.id,
        )
    )
    op = op_result.scalar_one_or_none()

    if passed:
        if not op:
            op = ObjectiveProgress(
                mission_progress_id=progress.id,
                objective_id=objective.id,
                status="completed",
                completed_at=datetime.now(timezone.utc),
            )
            db.add(op)
        elif op.status != "completed":
            op.status = "completed"
            op.completed_at = datetime.now(timezone.utc)
        else:
            return APIResponse[dict](data={"passed": True, "already_completed": True})

        progress.current_objective_index += 1
        await ProgressService.award_xp(db, user.id, objective.xp_reward, objective.coins_reward)

        # Check mission completion
        total_objectives = (
            await db.execute(
                select(MissionObjective.id).where(MissionObjective.mission_id == mission_id)
            )
        ).scalars().all()
        completed_count = (
            await db.execute(
                select(ObjectiveProgress.id).where(
                    ObjectiveProgress.mission_progress_id == progress.id,
                    ObjectiveProgress.status == "completed",
                )
            )
        ).scalars().all()

        mission_completed = len(completed_count) >= len(total_objectives)
        if mission_completed and progress.status != "completed":
            from datetime import datetime, timezone

            progress.status = "completed"
            progress.completed_at = datetime.now(timezone.utc)
            mission = (
                await db.execute(select(Mission).where(Mission.id == mission_id))
            ).scalar_one_or_none()
            if mission:
                player = await ProgressService.get_or_create_player_progress(db, user.id)
                player.missions_completed += 1
                await ProgressService.award_xp(
                    db, user.id, mission.xp_reward, mission.coins_reward
                )

        await db.commit()
        return APIResponse[dict](
            data={
                "passed": True,
                "objective_completed": True,
                "mission_completed": mission_completed,
                "xp_earned": objective.xp_reward,
                "coins_earned": objective.coins_reward,
            }
        )
    else:
        await db.commit()
        return APIResponse[dict](
            data={"passed": False, "objective_completed": False, "mission_completed": False}
        )


@router.get("/{mission_id}/progress", response_model=APIResponse[dict], summary="Get mission progress")
async def get_mission_progress(
    mission_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MissionProgress).where(
            MissionProgress.user_id == user.id,
            MissionProgress.mission_id == mission_id,
        )
    )
    progress = result.scalar_one_or_none()
    if not progress:
        raise HTTPException(status_code=404, detail="Mission not started")

    op_result = await db.execute(
        select(ObjectiveProgress).where(ObjectiveProgress.mission_progress_id == progress.id)
    )
    ops = op_result.scalars().all()

    return APIResponse[dict](
        data={
            "status": progress.status,
            "current_objective_index": progress.current_objective_index,
            "xp_earned": progress.xp_earned,
            "coins_earned": progress.coins_earned,
            "attempts": progress.attempts,
            "started_at": progress.started_at.isoformat() if progress.started_at else None,
            "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
            "objectives": [
                {
                    "objective_id": str(op.objective_id),
                    "status": op.status,
                    "completed_at": op.completed_at.isoformat() if op.completed_at else None,
                }
                for op in ops
            ],
        }
    )