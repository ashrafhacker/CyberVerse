from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.user import Profile
from app.schemas.base import APIResponse
from app.services.progress_service import LevelSystem, ProgressService

router = APIRouter()


class UpdateProfileRequest(BaseModel):
    username: str | None = Field(None, min_length=3, max_length=50)
    bio: str | None = Field(None, max_length=500)
    banner_url: str | None = Field(None, max_length=500)
    equipped_title: str | None = Field(None, max_length=100)
    equipped_badge: str | None = Field(None, max_length=100)
    settings: dict | None = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        if v and not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username may only contain letters, numbers, underscores and dashes")
        return v


class UpdateAvatarRequest(BaseModel):
    avatar_url: str = Field(..., max_length=500)


def _serialize_profile(p: Profile, user) -> dict:
    return {
        "user_id": str(p.user_id),
        "username": p.username,
        "bio": p.bio,
        "banner_url": p.banner_url,
        "avatar_url": user.avatar_url,
        "xp": p.xp,
        "coins": p.coins,
        "level": p.level,
        "rank": p.rank,
        "titles": p.titles,
        "badges": p.badges,
        "equipped_title": p.equipped_title,
        "equipped_badge": p.equipped_badge,
        "statistics": p.statistics,
        "settings": p.settings,
    }


@router.get("/", response_model=APIResponse[dict], summary="Get own profile")
async def get_my_profile(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = Profile(user_id=user.id, username=user.email.split("@")[0])
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return APIResponse[dict](data=_serialize_profile(profile, user))


@router.patch("/", response_model=APIResponse[dict], summary="Update own profile")
async def update_profile(
    request: UpdateProfileRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = Profile(user_id=user.id, username=user.email.split("@")[0])
        db.add(profile)

    if request.username:
        existing = await db.execute(
            select(Profile).where(Profile.username == request.username, Profile.user_id != user.id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Username already taken")
        profile.username = request.username
    if request.bio is not None:
        profile.bio = request.bio
    if request.banner_url is not None:
        profile.banner_url = request.banner_url
    if request.equipped_title is not None:
        profile.equipped_title = request.equipped_title
    if request.equipped_badge is not None:
        profile.equipped_badge = request.equipped_badge
    if request.settings is not None:
        profile.settings = {**profile.settings, **request.settings}

    await db.commit()
    await db.refresh(profile)
    return APIResponse[dict](data=_serialize_profile(profile, user))


@router.patch("/avatar", response_model=APIResponse[dict], summary="Update avatar URL")
async def update_avatar(
    request: UpdateAvatarRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    user.avatar_url = request.avatar_url
    await db.commit()
    return APIResponse[dict](data={"avatar_url": user.avatar_url})


@router.get("/level", response_model=APIResponse[dict], summary="Get level progress info")
async def get_level_info(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    progress = await ProgressService.get_or_create_player_progress(db, user.id)
    return APIResponse[dict](data=LevelSystem.progress_to_next_level(progress.total_xp))


@router.get("/{user_id}", response_model=APIResponse[dict], summary="Get public profile")
async def get_public_profile(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    from uuid import UUID

    try:
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    result = await db.execute(select(Profile).where(Profile.user_id == uid))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from app.models.user import User

    user_result = await db.execute(select(User).where(User.id == uid))
    user = user_result.scalar_one_or_none()

    data = _serialize_profile(profile, user)
    data.pop("settings", None)
    return APIResponse[dict](data=data)
