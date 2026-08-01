from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_moderator, require_admin
from app.core.database import get_db
from app.models.user import Profile, User, UserStatus
from app.schemas.auth import UserResponse
from app.schemas.base import APIResponse, MessageResponse, PaginatedResponse

router = APIRouter()


def _serialize_user(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
        "role": user.role.value if hasattr(user.role, "value") else user.role,
        "status": user.status.value if hasattr(user.status, "value") else user.status,
        "is_verified": user.is_verified,
        "is_2fa_enabled": user.is_2fa_enabled,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.get("/", response_model=APIResponse[PaginatedResponse], summary="List users (moderator+)")
async def list_users(
    _: CurrentUser = Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    role: str = Query(None),
    status_filter: str = Query(None, alias="status"),
):
    stmt = select(User)
    count_stmt = select(func.count(User.id))

    if search:
        stmt = stmt.where(User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%"))
        count_stmt = count_stmt.where(User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%"))
    if role:
        stmt = stmt.where(User.role == role)
        count_stmt = count_stmt.where(User.role == role)
    if status_filter:
        stmt = stmt.where(User.status == status_filter)
        count_stmt = count_stmt.where(User.status == status_filter)

    total = (await db.execute(count_stmt)).scalar_one()
    result = await db.execute(
        stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    users = result.scalars().all()

    data = PaginatedResponse.create(
        items=[_serialize_user(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )
    return APIResponse[PaginatedResponse](data=data)


@router.get("/{user_id}", response_model=APIResponse[dict], summary="Get user by ID")
async def get_user(
    user_id: UUID,
    _: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return APIResponse[dict](data=_serialize_user(user))


@router.patch("/{user_id}/status", response_model=APIResponse[dict], summary="Update user status (admin)")
async def update_user_status(
    user_id: UUID,
    new_status: UserStatus,
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = new_status
    await db.commit()
    await db.refresh(user)
    return APIResponse[dict](data=_serialize_user(user))


@router.patch("/{user_id}/role", response_model=APIResponse[dict], summary="Update user role (admin)")
async def update_user_role(
    user_id: UUID,
    new_role: str,
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import UserRole

    try:
        role = UserRole(new_role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {new_role}")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = role
    await db.commit()
    await db.refresh(user)
    return APIResponse[dict](data=_serialize_user(user))


@router.delete("/{user_id}", response_model=MessageResponse, summary="Soft-delete user (admin)")
async def delete_user(
    user_id: UUID,
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = UserStatus.INACTIVE
    from datetime import datetime, timezone
    user.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return MessageResponse(message="User deactivated")