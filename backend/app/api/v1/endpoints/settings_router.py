from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.analytics import AppSetting
from app.schemas.base import APIResponse

router = APIRouter()


class UpdateSettingsRequest(BaseModel):
    settings: dict = Field(default_factory=dict)


class PrivacySettingsRequest(BaseModel):
    show_profile_publicly: bool = True
    show_achievements: bool = True
    show_leaderboard_rank: bool = True
    allow_friend_requests: bool = True
    allow_message_from_friends_only: bool = True
    allow_email_notifications: bool = True
    allow_push_notifications: bool = True
    allow_analytics: bool = True


@router.get("/", response_model=APIResponse[dict], summary="Get my settings")
async def get_settings(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import Profile

    result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = result.scalar_one_or_none()

    settings = profile.settings if profile else {}
    return APIResponse[dict](
        data={
            **settings,
            "account": {
                "email": user.email,
                "is_verified": user.is_verified,
                "is_2fa_enabled": user.is_2fa_enabled,
                "role": user.role.value if hasattr(user.role, "value") else user.role,
            },
        }
    )


@router.patch("/", response_model=APIResponse[dict], summary="Update my settings")
async def update_settings(
    request: UpdateSettingsRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import Profile

    result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = Profile(user_id=user.id, username=user.email.split("@")[0])
        db.add(profile)

    profile.settings = {**profile.settings, **request.settings}
    await db.commit()
    return APIResponse[dict](data=profile.settings)


@router.put("/privacy", response_model=APIResponse[dict], summary="Update privacy preferences")
async def update_privacy(
    request: PrivacySettingsRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import Profile

    result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = Profile(user_id=user.id, username=user.email.split("@")[0])
        db.add(profile)

    profile.settings = {**profile.settings, "privacy": request.model_dump()}
    await db.commit()
    return APIResponse[dict](data=request.model_dump())


@router.get("/public", response_model=APIResponse[dict], summary="Get public platform settings")
async def get_public_settings(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AppSetting).where(AppSetting.is_public.is_(True)))
    settings = result.scalars().all()
    return APIResponse[dict](
        data={s.key: s.value for s in settings}
    )
