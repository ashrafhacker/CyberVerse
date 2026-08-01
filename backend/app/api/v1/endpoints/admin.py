from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_admin, require_super_admin
from app.core.database import get_db
from app.models.analytics import AppSetting, FeatureFlag
from app.models.notification import Announcement
from app.models.premium import Coupon, Subscription, SubscriptionPlan
from app.models.session import AuditLog
from app.models.support import SupportTicket, TicketMessage
from app.models.user import User, UserRole
from app.schemas.base import APIResponse, MessageResponse

router = APIRouter()


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    body: str = Field(..., min_length=10, max_length=5000)
    announcement_type: str = Field("general", max_length=50)
    is_pinned: bool = False
    is_draft: bool = True


class FeatureFlagUpdate(BaseModel):
    enabled: bool | None = None
    rollout_percentage: int | None = Field(None, ge=0, le=100)


class SettingUpdate(BaseModel):
    value: dict


class UserRoleUpdate(BaseModel):
    role: str = Field(..., min_length=1, max_length=50)


class UserStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=50)


@router.get("/overview", response_model=APIResponse[dict], summary="Admin overview dashboard")
async def admin_overview(
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    total_users = (await db.execute(select(func.count(User.id)))).scalar_one()
    pending_tickets = (
        await db.execute(
            select(func.count(SupportTicket.id)).where(SupportTicket.status.in_(["open", "pending"]))
        )
    ).scalar_one()
    active_subscriptions = (
        await db.execute(
            select(func.count(Subscription.id)).where(Subscription.status.in_(["active", "trial"]))
        )
    ).scalar_one()
    published_announcements = (
        await db.execute(
            select(func.count(Announcement.id)).where(
                Announcement.is_draft.is_(False),
                Announcement.is_active.is_(True),
            )
        )
    ).scalar_one()

    return APIResponse[dict](
        data={
            "total_users": total_users,
            "pending_tickets": pending_tickets,
            "active_subscriptions": active_subscriptions,
            "published_announcements": published_announcements,
            "system_health": {
                "status": "operational",
                "services": {
                    "api": "ok",
                    "database": "ok",
                    "redis": "ok",
                    "celery": "ok",
                },
            },
        }
    )


@router.get("/users", response_model=APIResponse[dict], summary="List all users with pagination")
async def admin_users(
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    role: str = Query(None),
):
    stmt = select(User)
    count_stmt = select(func.count(User.id))

    if search:
        like = f"%{search}%"
        stmt = stmt.where(User.email.ilike(like) | User.full_name.ilike(like))
        count_stmt = count_stmt.where(User.email.ilike(like) | User.full_name.ilike(like))
    if role:
        stmt = stmt.where(User.role == role)
        count_stmt = count_stmt.where(User.role == role)

    total = (await db.execute(count_stmt)).scalar_one()
    result = await db.execute(
        stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    users = result.scalars().all()

    return APIResponse[dict](
        data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "users": [
                {
                    "id": str(u.id),
                    "email": u.email,
                    "full_name": u.full_name,
                    "role": u.role.value if hasattr(u.role, "value") else u.role,
                    "status": u.status.value if hasattr(u.status, "value") else u.status,
                    "is_verified": u.is_verified,
                    "is_2fa_enabled": u.is_2fa_enabled,
                    "last_login": u.last_login.isoformat() if u.last_login else None,
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                }
                for u in users
            ],
        }
    )


@router.patch("/users/{user_id}/role", response_model=MessageResponse, summary="Update user role")
async def admin_update_role(
    user_id: str,
    request: UserRoleUpdate,
    _: CurrentUser = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    from uuid import UUID

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        user.role = UserRole(request.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {request.role}")

    await db.commit()

    from app.services.audit_service import AuditService

    await AuditService.log(
        db,
        action="user.role_updated",
        resource_type="user",
        resource_id=str(user.id),
        user_id=_.id,
        after={"role": request.role},
        meta={"admin": str(_.id)},
    )
    return MessageResponse(message=f"Role updated to {request.role}")


@router.patch("/users/{user_id}/status", response_model=MessageResponse, summary="Update user status")
async def admin_update_status(
    user_id: str,
    request: UserStatusUpdate,
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from uuid import UUID

    from app.models.user import UserStatus

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        user.status = UserStatus(request.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")

    await db.commit()
    return MessageResponse(message=f"Status updated to {request.status}")


@router.get("/audit-logs", response_model=APIResponse[dict], summary="View audit logs")
async def admin_audit_logs(
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: str = Query(None),
):
    stmt = select(AuditLog)
    count_stmt = select(func.count(AuditLog.id))
    if action:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)
    total = (await db.execute(count_stmt)).scalar_one()

    result = await db.execute(
        stmt.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    logs = result.scalars().all()

    return APIResponse[dict](
        data={
            "total": total,
            "page": page,
            "logs": [
                {
                    "id": str(l.id),
                    "user_id": str(l.user_id) if l.user_id else None,
                    "action": l.action,
                    "resource_type": l.resource_type,
                    "resource_id": l.resource_id,
                    "ip_address": l.ip_address,
                    "created_at": l.created_at.isoformat() if l.created_at else None,
                }
                for l in logs
            ],
        }
    )


@router.get("/tickets", response_model=APIResponse[dict], summary="List all support tickets")
async def admin_tickets(
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    status_filter: str = Query(None, alias="status"),
):
    stmt = select(SupportTicket)
    if status_filter:
        stmt = stmt.where(SupportTicket.status == status_filter)
    result = await db.execute(stmt.order_by(SupportTicket.created_at.desc()).limit(100))
    tickets = result.scalars().all()

    return APIResponse[dict](
        data=[
            {
                "id": str(t.id),
                "ticket_number": t.ticket_number,
                "user_id": str(t.user_id),
                "subject": t.subject,
                "status": t.status.value if hasattr(t.status, "value") else t.status,
                "priority": t.priority.value if hasattr(t.priority, "value") else t.priority,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tickets
        ]
    )


@router.get("/subscriptions", response_model=APIResponse[dict], summary="List subscriptions")
async def admin_subscriptions(
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription).order_by(Subscription.created_at.desc()).limit(100)
    )
    subscriptions = result.scalars().all()

    return APIResponse[dict](
        data=[
            {
                "id": str(s.id),
                "user_id": str(s.user_id),
                "plan_id": str(s.plan_id),
                "status": s.status.value if hasattr(s.status, "value") else s.status,
                "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in subscriptions
        ]
    )


@router.get("/feature-flags", response_model=APIResponse[list], summary="List feature flags")
async def admin_feature_flags(
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FeatureFlag).order_by(FeatureFlag.created_at.desc()))
    flags = result.scalars().all()
    return APIResponse[list](
        data=[
            {
                "id": str(f.id),
                "key": f.key,
                "enabled": f.enabled,
                "rollout_percentage": f.rollout_percentage,
                "description": f.description,
            }
            for f in flags
        ]
    )


@router.patch("/feature-flags/{flag_id}", response_model=APIResponse[dict], summary="Update feature flag")
async def admin_update_flag(
    flag_id: str,
    request: FeatureFlagUpdate,
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from uuid import UUID

    result = await db.execute(select(FeatureFlag).where(FeatureFlag.id == UUID(flag_id)))
    flag = result.scalar_one_or_none()
    if not flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")

    if request.enabled is not None:
        flag.enabled = request.enabled
    if request.rollout_percentage is not None:
        flag.rollout_percentage = request.rollout_percentage
    await db.commit()

    return APIResponse[dict](
        data={
            "id": str(flag.id),
            "key": flag.key,
            "enabled": flag.enabled,
            "rollout_percentage": flag.rollout_percentage,
        }
    )


@router.get("/settings", response_model=APIResponse[list], summary="List application settings")
async def admin_settings(
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AppSetting).order_by(AppSetting.created_at.desc()))
    settings = result.scalars().all()
    return APIResponse[list](
        data=[
            {"id": str(s.id), "key": s.key, "value": s.value, "is_public": s.is_public}
            for s in settings
        ]
    )


@router.put("/settings/{setting_id}", response_model=APIResponse[dict], summary="Update application setting")
async def admin_update_setting(
    setting_id: str,
    request: SettingUpdate,
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from uuid import UUID

    result = await db.execute(select(AppSetting).where(AppSetting.id == UUID(setting_id)))
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    setting.value = request.value
    setting.updated_by = str(_.id)
    await db.commit()
    return APIResponse[dict](data={"id": str(setting.id), "key": setting.key, "value": setting.value})


@router.post("/announcements", response_model=APIResponse[dict], summary="Create an announcement")
async def admin_create_announcement(
    request: AnnouncementCreate,
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone

    announcement = Announcement(
        author_id=_.id,
        title=request.title,
        body=request.body,
        announcement_type=request.announcement_type,
        is_pinned=request.is_pinned,
        is_draft=request.is_draft,
        publish_at=None if request.is_draft else datetime.now(timezone.utc),
        published_at=None if request.is_draft else datetime.now(timezone.utc),
    )
    db.add(announcement)
    await db.commit()
    await db.refresh(announcement)
    return APIResponse[dict](data={"id": str(announcement.id), "title": announcement.title})


@router.get("/announcements", response_model=APIResponse[list], summary="List announcements")
async def admin_list_announcements(
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Announcement).order_by(Announcement.created_at.desc()).limit(100)
    )
    announcements = result.scalars().all()
    return APIResponse[list](
        data=[
            {
                "id": str(a.id),
                "title": a.title,
                "announcement_type": a.announcement_type,
                "is_draft": a.is_draft,
                "is_pinned": a.is_pinned,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in announcements
        ]
    )