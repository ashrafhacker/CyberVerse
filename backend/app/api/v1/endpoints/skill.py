from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.schemas.base import APIResponse
from app.schemas.skill import SkillBranchOut, SkillProgressOut
from app.services.skill_service import SkillService

router = APIRouter()


@router.get("/branches", response_model=APIResponse[list[SkillBranchOut]], summary="Skill tree branches")
async def list_branches(_: CurrentUser, db: AsyncSession = Depends(get_db)):
    branches = await SkillService.ensure_branches(db)
    return APIResponse[list[SkillBranchOut]](
        data=[
            SkillBranchOut.model_validate(
                {
                    "id": b.id,
                    "slug": b.slug,
                    "name": b.name,
                    "description": b.description,
                    "icon": b.icon,
                    "max_level": b.max_level,
                    "prerequisites": b.prerequisites,
                    "display_order": b.display_order,
                }
            )
            for b in branches
        ]
    )


@router.get("", response_model=APIResponse[SkillProgressOut], summary="Learner skill progress and rank")
async def get_progress(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    data = await SkillService.progress(db, user.id)
    return APIResponse[SkillProgressOut](
        data=SkillProgressOut.model_validate(data)
    )
