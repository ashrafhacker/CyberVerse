"""Admin dashboard endpoints: RBAC-guarded management surfaces.

Security contract (Phase B, docs/ADMIN_MISSION_PHASE_A.md):
- Every route requires an authenticated admin-tier user (``require_admin``)
  or super admin (``require_super_admin``) — enforced server-side only.
- Role/status mutations apply the shared hierarchy guard
  (``ensure_can_modify``): self-change -> 400, actor rank <= target rank
  (and actor not super admin) -> 403.
- Every mutation writes an audit row via ``AuditService``.
- Path ids are UUID-typed: malformed ids return 422, never 500.
- ``WS /stream`` authenticates via ``?token=`` and closes with 4401/4403
  on auth failure (accept-then-close).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    ROLE_HIERARCHY,
    _resolve_user,
    can_modify,
    ensure_can_modify,
    require_admin,
    require_super_admin,
)
from app.core.config import settings
from app.core.database import get_db, get_db_context
from app.core.redis import healthcheck
from app.models.analytics import AppSetting, FeatureFlag
from app.models.notification import Announcement
from app.models.premium import Payment, PaymentStatus, Subscription, SubscriptionPlan
from app.models.session import AuditLog, LoginHistory, Session
from app.models.support import SupportTicket, TicketMessage, TicketPriority, TicketStatus
from app.models.user import User, UserRole, UserStatus
from app.schemas.base import APIResponse, MessageResponse
from app.services.admin_events import AdminEventHub
from app.services.audit_service import AuditService

router = APIRouter()


# --------------------------------------------------------------------------
# Request schemas
# --------------------------------------------------------------------------


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    body: str = Field(..., min_length=10, max_length=5000)
    announcement_type: str = Field("general", max_length=50)
    is_pinned: bool = False
    is_draft: bool = True


class AnnouncementUpdate(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=200)
    body: str | None = Field(None, min_length=10, max_length=5000)
    announcement_type: str | None = Field(None, max_length=50)
    is_pinned: bool | None = None
    is_draft: bool | None = None


class FeatureFlagUpdate(BaseModel):
    enabled: bool | None = None
    rollout_percentage: int | None = Field(None, ge=0, le=100)


class SettingCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=200)
    value: dict
    description: str | None = Field(None, max_length=2000)
    is_public: bool = False


class SettingUpdate(BaseModel):
    value: dict
    description: str | None = Field(None, max_length=2000)


class UserRoleUpdate(BaseModel):
    role: str = Field(..., min_length=1, max_length=50)


class UserStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=50)


class BulkStatusUpdate(BaseModel):
    user_ids: list[UUID] = Field(..., min_length=1, max_length=50)
    status: str = Field(..., min_length=1, max_length=50)


class TicketReplyCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class TicketUpdate(BaseModel):
    status: str | None = None
    priority: str | None = None
    assignee_id: UUID | None = None


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _enum_val(value):
    return value.value if hasattr(value, "value") else value


def _serialize_announcement(a: Announcement) -> dict:
    return {
        "id": str(a.id),
        "title": a.title,
        "body": a.body,
        "announcement_type": a.announcement_type,
        "is_pinned": a.is_pinned,
        "is_draft": a.is_draft,
        "is_active": a.is_active,
        "image_url": a.image_url,
        "link": a.link,
        "publish_at": _iso(a.publish_at),
        "published_at": _iso(a.published_at),
        "expires_at": _iso(a.expires_at),
        "created_at": _iso(a.created_at),
        "updated_at": _iso(a.updated_at),
    }


def _serialize_ticket(
    t: SupportTicket,
    requester_email: str | None = None,
) -> dict:
    return {
        "id": str(t.id),
        "ticket_number": t.ticket_number,
        "user_id": str(t.user_id),
        "requester_email": requester_email,
        "subject": t.subject,
        "description": t.description,
        "category": _enum_val(t.category),
        "status": _enum_val(t.status),
        "priority": _enum_val(t.priority),
        "assignee_id": str(t.assignee_id) if t.assignee_id else None,
        "first_response_at": _iso(t.first_response_at),
        "resolved_at": _iso(t.resolved_at),
        "closed_at": _iso(t.closed_at),
        "created_at": _iso(t.created_at),
        "updated_at": _iso(t.updated_at),
    }


def _parse_enum(enum_cls, raw: str, label: str):
    try:
        return enum_cls(raw)
    except ValueError as err:
        raise HTTPException(
            status_code=400, detail=f"Invalid {label}: {raw}"
        ) from err


# --------------------------------------------------------------------------
# Overview
# --------------------------------------------------------------------------


@router.get("/overview", response_model=APIResponse[dict], summary="Admin overview")
async def admin_overview(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    total_users = (
        await db.execute(select(func.count(User.id)))
    ).scalar_one()
    pending_tickets = (
        await db.execute(
            select(func.count(SupportTicket.id)).where(
                SupportTicket.status.in_(["open", "pending"])
            )
        )
    ).scalar_one()
    active_subscriptions = (
        await db.execute(
            select(func.count(Subscription.id)).where(
                Subscription.status.in_(["active", "trial"])
            )
        )
    ).scalar_one()
    published_announcements = (
        await db.execute(
            select(func.count(Announcement.id)).where(
                Announcement.is_active.is_(True),
                Announcement.is_draft.is_(False),
            )
        )
    ).scalar_one()

    # Real health probes — no hardcoded values.
    try:
        await db.execute(text("SELECT 1"))
        database_health = "ok"
    except Exception:  # noqa: BLE001 — health probe must not 500
        database_health = "degraded"
    redis_health = "ok" if await healthcheck() else "degraded"

    return APIResponse[dict](
        data={
            "counts": {
                "total_users": total_users,
                "pending_tickets": pending_tickets,
                "active_subscriptions": active_subscriptions,
                "published_announcements": published_announcements,
            },
            "system_health": {
                "status": (
                    "operational"
                    if database_health == "ok" and redis_health == "ok"
                    else "degraded"
                ),
                "services": {
                    "api": "ok",
                    "database": database_health,
                    "redis": redis_health,
                    "celery": "unknown",
                },
            },
        }
    )


# --------------------------------------------------------------------------
# User management (admin tier)
# --------------------------------------------------------------------------


@router.get("/users", response_model=APIResponse[dict], summary="List users (admin)")
async def admin_users(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: str | None = Query(None, max_length=50),
    status: str | None = Query(None, max_length=50),
    search: str | None = Query(None, max_length=200),
):
    stmt = select(User)
    count_stmt = select(func.count(User.id))
    if role:
        stmt = stmt.where(User.role == _parse_enum(UserRole, role, "role"))
        count_stmt = count_stmt.where(User.role == _parse_enum(UserRole, role, "role"))
    if status:
        stmt = stmt.where(User.status == _parse_enum(UserStatus, status, "status"))
        count_stmt = count_stmt.where(
            User.status == _parse_enum(UserStatus, status, "status")
        )
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(User.email.ilike(pattern) | User.full_name.ilike(pattern))
        count_stmt = count_stmt.where(
            User.email.ilike(pattern) | User.full_name.ilike(pattern)
        )
    total = (await db.execute(count_stmt)).scalar_one()
    result = await db.execute(
        stmt.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return APIResponse[dict](
        data={
            "users": [_serialize_user(u) for u in result.scalars().all()],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


def _serialize_user(u: User) -> dict:
    return {
        "id": str(u.id),
        "email": u.email,
        "full_name": u.full_name,
        "avatar_url": u.avatar_url,
        "role": _enum_val(u.role),
        "status": _enum_val(u.status),
        "is_verified": u.is_verified,
        "last_login": _iso(u.last_login),
        "created_at": _iso(u.created_at),
    }


@router.patch(
    "/users/{user_id}/role",
    response_model=MessageResponse,
    summary="Update a user role (super admin)",
)
async def admin_update_role(
    user_id: UUID,
    request: UserRoleUpdate,
    actor: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    target = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    new_role = _parse_enum(UserRole, request.role, "role")
    ensure_can_modify(actor, target)

    before = {"role": _enum_val(target.role)}
    target.role = new_role
    await db.commit()
    await AuditService.log(
        db,
        action="user.role_updated",
        resource_type="user",
        resource_id=str(target.id),
        user_id=actor.id,
        before=before,
        after={"role": _enum_val(new_role)},
        meta={"admin": str(actor.id)},
    )
    return MessageResponse(message=f"Role updated to {request.role}")


@router.patch(
    "/users/{user_id}/status",
    response_model=MessageResponse,
    summary="Update a user status (admin)",
)
async def admin_update_status(
    user_id: UUID,
    request: UserStatusUpdate,
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    target = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    new_status = _parse_enum(UserStatus, request.status, "status")
    ensure_can_modify(actor, target)

    before = {"status": _enum_val(target.status)}
    target.status = new_status
    await db.commit()
    await AuditService.log(
        db,
        action="user.status_updated",
        resource_type="user",
        resource_id=str(target.id),
        user_id=actor.id,
        before=before,
        after={"status": _enum_val(new_status)},
        meta={"admin": str(actor.id)},
    )
    return MessageResponse(message=f"Status updated to {request.status}")


@router.post(
    "/users/bulk-status",
    response_model=APIResponse[dict],
    summary="Bulk update user statuses (admin)",
)
async def admin_bulk_status(
    request: BulkStatusUpdate,
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    new_status = _parse_enum(UserStatus, request.status, "status")
    result = await db.execute(select(User).where(User.id.in_(request.user_ids)))
    targets = {u.id: u for u in result.scalars().all()}

    updated = 0
    skipped: list[dict] = []
    # dict.fromkeys dedupes while preserving order.
    for uid in dict.fromkeys(request.user_ids):
        target = targets.get(uid)
        if target is None:
            skipped.append({"id": str(uid), "reason": "not_found"})
            continue
        if actor.id == target.id:
            skipped.append({"id": str(uid), "reason": "self"})
            continue
        if not can_modify(actor, target):
            skipped.append({"id": str(uid), "reason": "protected"})
            continue
        target.status = new_status
        updated += 1
    await db.commit()

    await AuditService.log(
        db,
        action="user.bulk_status_updated",
        resource_type="user",
        user_id=actor.id,
        after={
            "status": _enum_val(new_status),
            "updated": updated,
            "skipped": skipped,
        },
        meta={"admin": str(actor.id)},
    )
    return APIResponse[dict](data={"updated": updated, "skipped": skipped})


# --------------------------------------------------------------------------
# User login control: sessions & login history (admin)
# --------------------------------------------------------------------------


async def _require_target_user(db: AsyncSession, user_id: UUID) -> User:
    target = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    return target


def _session_row(s: Session) -> dict:
    return {
        "id": str(s.id),
        "ip_address": s.ip_address,
        "user_agent": (s.user_agent or "")[:200],
        "location": s.location,
        "device_info": s.device_info or {},
        "created_at": _iso(s.created_at),
        "expires_at": _iso(s.expires_at),
    }


@router.get(
    "/users/{user_id}/sessions",
    response_model=APIResponse[list],
    summary="List a user's active login sessions (admin)",
)
async def admin_list_user_sessions(
    user_id: UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await _require_target_user(db, user_id)
    now = datetime.now(UTC)
    rows = (
        await db.execute(
            select(Session)
            .where(
                Session.user_id == user_id,
                Session.is_revoked.is_(False),
                Session.expires_at > now,
            )
            .order_by(Session.created_at.desc())
            .limit(100)
        )
    ).scalars().all()
    return APIResponse[list](data=[_session_row(s) for s in rows])


@router.delete(
    "/users/{user_id}/sessions/{session_id}",
    response_model=MessageResponse,
    summary="Revoke one of a user's login sessions (admin force logout)",
)
async def admin_revoke_user_session(
    user_id: UUID,
    session_id: UUID,
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await _require_target_user(db, user_id)
    session = (
        await db.execute(
            select(Session).where(Session.id == session_id, Session.user_id == user_id)
        )
    ).scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.is_revoked:
        raise HTTPException(status_code=409, detail="Session already revoked")

    session.is_revoked = True
    session.revoked_at = datetime.now(UTC)
    session.revoked_by = str(actor.id)
    await db.commit()

    await AuditService.log(
        db,
        action="user.session_revoked",
        resource_type="session",
        resource_id=str(session_id),
        user_id=actor.id,
        after={"target_user": str(user_id), "revoked_by": str(actor.id)},
        meta={"admin": str(actor.id)},
    )
    return MessageResponse(message="Session revoked")


@router.post(
    "/users/{user_id}/sessions/revoke-all",
    response_model=APIResponse[dict],
    summary="Revoke all of a user's active sessions (force logout everywhere)",
)
async def admin_revoke_all_user_sessions(
    user_id: UUID,
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    target = await _require_target_user(db, user_id)
    if target.id == actor.id:
        raise HTTPException(status_code=400, detail="Cannot force logout yourself")

    now = datetime.now(UTC)
    rows = (
        await db.execute(
            select(Session).where(
                Session.user_id == user_id,
                Session.is_revoked.is_(False),
                Session.expires_at > now,
            )
        )
    ).scalars().all()
    for s in rows:
        s.is_revoked = True
        s.revoked_at = now
        s.revoked_by = str(actor.id)
    await db.commit()

    await AuditService.log(
        db,
        action="user.sessions_revoked_all",
        resource_type="user",
        resource_id=str(user_id),
        user_id=actor.id,
        after={"target_user": str(user_id), "revoked_count": len(rows)},
        meta={"admin": str(actor.id)},
    )
    return APIResponse[dict](data={"revoked": len(rows)})


@router.get(
    "/users/{user_id}/login-history",
    response_model=APIResponse[list],
    summary="List a user's login history (admin)",
)
async def admin_user_login_history(
    user_id: UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
):
    await _require_target_user(db, user_id)
    rows = (
        await db.execute(
            select(LoginHistory)
            .where(LoginHistory.user_id == user_id)
            .order_by(LoginHistory.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return APIResponse[list](
        data=[
            {
                "id": str(h.id),
                "success": h.success,
                "ip_address": h.ip_address,
                "user_agent": (h.user_agent or "")[:200],
                "location": h.location,
                "method": h.method,
                "failure_reason": h.failure_reason,
                "created_at": _iso(h.created_at),
            }
            for h in rows
        ]
    )


# --------------------------------------------------------------------------
# Audit logs
# --------------------------------------------------------------------------


def _audit_log_row(l: AuditLog) -> dict:
    return {
        "id": str(l.id),
        "user_id": str(l.user_id) if l.user_id else None,
        "action": l.action,
        "resource_type": l.resource_type,
        "resource_id": l.resource_id,
        "ip_address": l.ip_address,
        "user_agent": l.user_agent,
        "before": l.before,
        "after": l.after,
        "metadata": l.meta_data or {},
        "created_at": _iso(l.created_at),
    }


@router.get(
    "/audit-logs", response_model=APIResponse[dict], summary="List audit logs"
)
async def admin_audit_logs(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: str | None = Query(None, max_length=100),
    user_id: str | None = Query(None, max_length=36),
    resource_type: str | None = Query(None, max_length=50),
    date_from: str | None = Query(None, max_length=10),
    date_to: str | None = Query(None, max_length=10),
):
    filters = []
    if action:
        filters.append(AuditLog.action == action)
    if user_id:
        try:
            uid = UUID(user_id)
        except ValueError as err:
            raise HTTPException(status_code=400, detail="Invalid user_id") from err
        filters.append(AuditLog.user_id == uid)
    if resource_type:
        filters.append(AuditLog.resource_type == resource_type)
    if date_from:
        try:
            d = date.fromisoformat(date_from)
        except ValueError as err:
            raise HTTPException(status_code=400, detail="Invalid date_from") from err
        filters.append(
            AuditLog.created_at >= datetime.combine(d, time.min, tzinfo=UTC)
        )
    if date_to:
        try:
            d = date.fromisoformat(date_to)
        except ValueError as err:
            raise HTTPException(status_code=400, detail="Invalid date_to") from err
        filters.append(
            AuditLog.created_at
            < datetime.combine(d + timedelta(days=1), time.min, tzinfo=UTC)
        )

    stmt = select(AuditLog)
    count_stmt = select(func.count(AuditLog.id))
    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)
    total = (await db.execute(count_stmt)).scalar_one()
    result = await db.execute(
        stmt.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return APIResponse[dict](
        data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "logs": [_audit_log_row(l) for l in result.scalars().all()],
        }
    )


# --------------------------------------------------------------------------
# Tickets
# --------------------------------------------------------------------------


@router.get("/tickets", response_model=APIResponse[list], summary="List tickets")
async def admin_tickets(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status", max_length=20),
):
    stmt = (
        select(SupportTicket, User.email.label("requester_email"))
        .join(User, SupportTicket.user_id == User.id, isouter=True)
    )
    if status_filter:
        stmt = stmt.where(
            SupportTicket.status == _parse_enum(TicketStatus, status_filter, "status")
        )
    result = await db.execute(
        stmt.order_by(SupportTicket.created_at.desc()).limit(100)
    )
    rows = result.all()
    return APIResponse[list](
        data=[
            {
                **_serialize_ticket(t, requester_email=email),
            }
            for t, email in rows
        ]
    )


@router.get(
    "/tickets/{ticket_id}", response_model=APIResponse[dict], summary="Ticket detail"
)
async def admin_ticket_detail(
    ticket_id: UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            select(SupportTicket, User.email.label("requester_email"))
            .join(User, SupportTicket.user_id == User.id, isouter=True)
            .where(SupportTicket.id == ticket_id)
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket, requester_email = row
    messages = (
        await db.execute(
            select(TicketMessage)
            .where(TicketMessage.ticket_id == ticket_id)
            .order_by(TicketMessage.created_at.asc())
        )
    ).scalars().all()
    return APIResponse[dict](
        data={
            **_serialize_ticket(ticket, requester_email=requester_email),
            "messages": [
                {
                    "id": str(m.id),
                    "author_id": str(m.author_id),
                    "content": m.content,
                    "is_staff_reply": m.is_staff_reply,
                    "created_at": _iso(m.created_at),
                }
                for m in messages
            ],
        }
    )


@router.post(
    "/tickets/{ticket_id}/reply",
    response_model=APIResponse[dict],
    status_code=201,
    summary="Reply to a ticket (admin)",
)
async def admin_ticket_reply(
    ticket_id: UUID,
    request: TicketReplyCreate,
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    ticket = (
        await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
    ).scalar_one_or_none()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    message = TicketMessage(
        ticket_id=ticket.id,
        author_id=actor.id,
        content=request.content,
        is_staff_reply=True,
    )
    db.add(message)
    now = datetime.now(UTC)
    if ticket.first_response_at is None:
        ticket.first_response_at = now
    await db.commit()

    await AuditService.log(
        db,
        action="ticket.replied",
        resource_type="ticket",
        resource_id=str(ticket.id),
        user_id=actor.id,
        after={"message_id": str(message.id)},
        meta={"admin": str(actor.id)},
    )
    return APIResponse[dict](
        data={
            "id": str(message.id),
            "ticket_id": str(ticket.id),
            "content": message.content,
            "is_staff_reply": True,
            "first_response_at": _iso(ticket.first_response_at),
            "created_at": _iso(message.created_at),
        }
    )


@router.patch(
    "/tickets/{ticket_id}", response_model=APIResponse[dict], summary="Update ticket"
)
async def admin_ticket_update(
    ticket_id: UUID,
    request: TicketUpdate,
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    ticket = (
        await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
    ).scalar_one_or_none()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Validate everything before mutating.
    new_status = (
        _parse_enum(TicketStatus, request.status, "status")
        if request.status is not None
        else None
    )
    new_priority = (
        _parse_enum(TicketPriority, request.priority, "priority")
        if request.priority is not None
        else None
    )
    assignee: User | None = None
    if request.assignee_id is not None:
        assignee = (
            await db.execute(select(User).where(User.id == request.assignee_id))
        ).scalar_one_or_none()
        if assignee is None:
            raise HTTPException(status_code=404, detail="Assignee not found")

    before = {
        "status": _enum_val(ticket.status),
        "priority": _enum_val(ticket.priority),
        "assignee_id": str(ticket.assignee_id) if ticket.assignee_id else None,
    }

    now = datetime.now(UTC)
    if new_status is not None:
        ticket.status = new_status
        if new_status is TicketStatus.RESOLVED and ticket.resolved_at is None:
            ticket.resolved_at = now
        if new_status is TicketStatus.CLOSED and ticket.closed_at is None:
            ticket.closed_at = now
    if new_priority is not None:
        ticket.priority = new_priority
    if assignee is not None:
        ticket.assignee_id = assignee.id
    await db.commit()

    after = {
        "status": _enum_val(ticket.status),
        "priority": _enum_val(ticket.priority),
        "assignee_id": str(ticket.assignee_id) if ticket.assignee_id else None,
    }
    await AuditService.log(
        db,
        action="ticket.updated",
        resource_type="ticket",
        resource_id=str(ticket.id),
        user_id=actor.id,
        before=before,
        after=after,
        meta={"admin": str(actor.id)},
    )
    return APIResponse[dict](data=_serialize_ticket(ticket))


# --------------------------------------------------------------------------
# Subscriptions
# --------------------------------------------------------------------------


@router.get(
    "/subscriptions", response_model=APIResponse[list], summary="List subscriptions"
)
async def admin_subscriptions(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription, User.email, SubscriptionPlan.name)
        .outerjoin(User, Subscription.user_id == User.id)
        .outerjoin(SubscriptionPlan, Subscription.plan_id == SubscriptionPlan.id)
        .order_by(Subscription.created_at.desc())
        .limit(100)
    )
    rows = result.all()
    return APIResponse[list](
        data=[
            {
                "id": str(s.id),
                "user_id": str(s.user_id),
                "plan_id": str(s.plan_id) if s.plan_id else None,
                "user_email": email,
                "plan_name": plan_name,
                "status": _enum_val(s.status),
                "current_period_start": _iso(s.current_period_start),
                "current_period_end": _iso(s.current_period_end),
                "created_at": _iso(s.created_at),
            }
            for s, email, plan_name in rows
        ]
    )


@router.get(
    "/payments", response_model=APIResponse[dict], summary="List payments with revenue stats (admin)"
)
async def admin_payments(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(200, ge=1, le=500),
):
    """Admin payments ledger: recent payment rows plus aggregate revenue stats."""
    rows = (
        await db.execute(
            select(Payment).order_by(Payment.created_at.desc()).limit(limit)
        )
    ).scalars().all()

    user_ids = {p.user_id for p in rows if p.user_id}
    emails: dict[UUID, str] = {}
    if user_ids:
        emails = dict(
            (await db.execute(select(User.id, User.email).where(User.id.in_(user_ids)))).all()
        )

    by_status: dict[str, int] = {}
    gross_completed = 0.0
    refunded = 0.0
    for p in rows:
        st = _enum_val(p.status)
        by_status[st] = by_status.get(st, 0) + 1
        if p.status == PaymentStatus.COMPLETED:
            gross_completed += float(p.amount)
        elif p.status == PaymentStatus.REFUNDED:
            refunded += float(p.amount)

    return APIResponse[dict](
        data={
            "stats": {
                "total": len(rows),
                "by_status": by_status,
                "gross_completed": round(gross_completed, 2),
                "refunded": round(refunded, 2),
                "currency": rows[0].currency if rows else "USD",
            },
            "payments": [
                {
                    "id": str(p.id),
                    "user_id": str(p.user_id) if p.user_id else None,
                    "user_email": emails.get(p.user_id),
                    "payment_intent_id": p.payment_intent_id,
                    "status": _enum_val(p.status),
                    "amount": float(p.amount),
                    "currency": p.currency,
                    "payment_method": p.payment_method,
                    "provider": p.provider,
                    "description": p.description,
                    "failure_reason": p.failure_reason,
                    "paid_at": _iso(p.paid_at),
                    "refunded_at": _iso(p.refunded_at),
                    "created_at": _iso(p.created_at),
                }
                for p in rows
            ],
        }
    )


# --------------------------------------------------------------------------
# Feature flags
# --------------------------------------------------------------------------


@router.get(
    "/feature-flags", response_model=APIResponse[list], summary="List feature flags"
)
async def admin_feature_flags(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    flags = (await db.execute(select(FeatureFlag))).scalars().all()
    return APIResponse[list](
        data=[
            {
                "id": str(f.id),
                "key": f.key,
                "description": f.description,
                "enabled": f.enabled,
                "rollout_percentage": f.rollout_percentage,
                "created_at": _iso(f.created_at),
                "updated_at": _iso(f.updated_at),
            }
            for f in flags
        ]
    )


@router.patch(
    "/feature-flags/{flag_id}",
    response_model=APIResponse[dict],
    summary="Update a feature flag",
)
async def admin_update_feature_flag(
    flag_id: UUID,
    request: FeatureFlagUpdate,
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    flag = (
        await db.execute(select(FeatureFlag).where(FeatureFlag.id == flag_id))
    ).scalar_one_or_none()
    if flag is None:
        raise HTTPException(status_code=404, detail="Feature flag not found")

    before = {"enabled": flag.enabled, "rollout_percentage": flag.rollout_percentage}
    if request.enabled is not None:
        flag.enabled = request.enabled
    if request.rollout_percentage is not None:
        flag.rollout_percentage = request.rollout_percentage
    flag.updated_by = str(actor.id)
    await db.commit()

    await AuditService.log(
        db,
        action="feature_flag.updated",
        resource_type="feature_flag",
        resource_id=str(flag.id),
        user_id=actor.id,
        before=before,
        after={
            "enabled": flag.enabled,
            "rollout_percentage": flag.rollout_percentage,
        },
        meta={"admin": str(actor.id)},
    )
    return APIResponse[dict](
        data={
            "id": str(flag.id),
            "key": flag.key,
            "description": flag.description,
            "enabled": flag.enabled,
            "rollout_percentage": flag.rollout_percentage,
            "updated_at": _iso(flag.updated_at),
        }
    )


# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------


def _serialize_setting(s: AppSetting) -> dict:
    return {
        "id": str(s.id),
        "key": s.key,
        "value": s.value,
        "description": s.description,
        "is_public": s.is_public,
        "updated_by": s.updated_by,
        "created_at": _iso(s.created_at),
        "updated_at": _iso(s.updated_at),
    }


@router.get("/settings", response_model=APIResponse[list], summary="List settings")
async def admin_settings(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    settings = (
        await db.execute(select(AppSetting).order_by(AppSetting.key.asc()))
    ).scalars().all()
    return APIResponse[list](data=[_serialize_setting(s) for s in settings])


@router.post(
    "/settings", response_model=APIResponse[dict], status_code=201, summary="Create setting"
)
async def admin_create_setting(
    request: SettingCreate,
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = (
        await db.execute(select(AppSetting).where(AppSetting.key == request.key))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Setting key already exists")

    setting = AppSetting(
        key=request.key,
        value=request.value,
        description=request.description,
        is_public=request.is_public,
        updated_by=str(actor.id),
    )
    db.add(setting)
    await db.commit()
    await db.refresh(setting)

    await AuditService.log(
        db,
        action="setting.created",
        resource_type="setting",
        resource_id=str(setting.id),
        user_id=actor.id,
        after={"key": setting.key, "value": setting.value},
        meta={"admin": str(actor.id)},
    )
    return APIResponse[dict](data=_serialize_setting(setting))


@router.put(
    "/settings/{setting_id}",
    response_model=APIResponse[dict],
    summary="Update a setting",
)
async def admin_update_setting(
    setting_id: UUID,
    request: SettingUpdate,
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    setting = (
        await db.execute(select(AppSetting).where(AppSetting.id == setting_id))
    ).scalar_one_or_none()
    if setting is None:
        raise HTTPException(status_code=404, detail="Setting not found")

    before = {"value": setting.value}
    setting.value = request.value
    if request.description is not None:
        setting.description = request.description
    setting.updated_by = str(actor.id)
    await db.commit()

    await AuditService.log(
        db,
        action="setting.updated",
        resource_type="setting",
        resource_id=str(setting.id),
        user_id=actor.id,
        before=before,
        after={"value": setting.value},
        meta={"admin": str(actor.id)},
    )
    return APIResponse[dict](data=_serialize_setting(setting))


# --------------------------------------------------------------------------
# Announcements
# --------------------------------------------------------------------------


@router.get(
    "/announcements", response_model=APIResponse[list], summary="List announcements"
)
async def admin_announcements(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    announcements = (
        await db.execute(
            select(Announcement).order_by(Announcement.created_at.desc())
        )
    ).scalars().all()
    return APIResponse[list](
        data=[_serialize_announcement(a) for a in announcements]
    )


@router.post(
    "/announcements",
    response_model=APIResponse[dict],
    status_code=201,
    summary="Create announcement",
)
async def admin_create_announcement(
    request: AnnouncementCreate,
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(UTC)
    announcement = Announcement(
        title=request.title,
        body=request.body,
        announcement_type=request.announcement_type,
        is_pinned=request.is_pinned,
        is_draft=request.is_draft,
        author_id=actor.id,
        publish_at=None if request.is_draft else now,
        published_at=None if request.is_draft else now,
    )
    db.add(announcement)
    await db.commit()
    await db.refresh(announcement)

    await AuditService.log(
        db,
        action="announcement.created",
        resource_type="announcement",
        resource_id=str(announcement.id),
        user_id=actor.id,
        after={"title": announcement.title, "is_draft": announcement.is_draft},
        meta={"admin": str(actor.id)},
    )
    return APIResponse[dict](
        data={"id": str(announcement.id), "title": announcement.title}
    )


@router.patch(
    "/announcements/{announcement_id}",
    response_model=APIResponse[dict],
    summary="Update announcement",
)
async def admin_update_announcement(
    announcement_id: UUID,
    request: AnnouncementUpdate,
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    announcement = (
        await db.execute(
            select(Announcement).where(Announcement.id == announcement_id)
        )
    ).scalar_one_or_none()
    if announcement is None:
        raise HTTPException(status_code=404, detail="Announcement not found")

    before = {
        "title": announcement.title,
        "body": announcement.body,
        "announcement_type": announcement.announcement_type,
        "is_pinned": announcement.is_pinned,
        "is_draft": announcement.is_draft,
        "is_active": announcement.is_active,
    }

    payload = request.model_dump(exclude_unset=True)
    now = datetime.now(UTC)
    for field in ("title", "body", "announcement_type", "is_pinned", "is_draft"):
        if field in payload and payload[field] is not None:
            setattr(announcement, field, payload[field])
    if payload.get("is_draft") is False:
        if announcement.published_at is None:
            announcement.published_at = now
        if announcement.publish_at is None:
            announcement.publish_at = now
    await db.commit()

    after = {
        "title": announcement.title,
        "body": announcement.body,
        "announcement_type": announcement.announcement_type,
        "is_pinned": announcement.is_pinned,
        "is_draft": announcement.is_draft,
        "is_active": announcement.is_active,
    }
    await AuditService.log(
        db,
        action="announcement.updated",
        resource_type="announcement",
        resource_id=str(announcement.id),
        user_id=actor.id,
        before=before,
        after=after,
        meta={"admin": str(actor.id)},
    )
    return APIResponse[dict](data=_serialize_announcement(announcement))


@router.delete(
    "/announcements/{announcement_id}",
    response_model=APIResponse[dict],
    summary="Delete announcement (soft)",
)
async def admin_delete_announcement(
    announcement_id: UUID,
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    announcement = (
        await db.execute(
            select(Announcement).where(Announcement.id == announcement_id)
        )
    ).scalar_one_or_none()
    if announcement is None:
        raise HTTPException(status_code=404, detail="Announcement not found")

    announcement.is_active = False
    await db.commit()

    await AuditService.log(
        db,
        action="announcement.deleted",
        resource_type="announcement",
        resource_id=str(announcement.id),
        user_id=actor.id,
        before={"is_active": True},
        after={"is_active": False},
        meta={"admin": str(actor.id)},
    )
    return APIResponse[dict](
        data={"id": str(announcement.id), "deleted": True}
    )


# --------------------------------------------------------------------------
# Live event stream (F20)
# --------------------------------------------------------------------------


@router.websocket("/stream")
async def admin_stream(websocket: WebSocket, token: str | None = Query(None)):
    """Live admin event stream fed by AuditService.

    Accept-then-close contract:
    - no/invalid token  -> close 4401
    - valid token below the admin tier -> close 4403
    - admin tier -> stream ``audit`` events (30s ping keepalive).
    """
    await websocket.accept()
    user: User | None = None
    if token:
        try:
            async with get_db_context() as db:
                user = await _resolve_user(db, token)
        except Exception:  # noqa: BLE001 — any auth failure -> 4401
            user = None
    if user is None:
        await websocket.close(code=4401)
        return
    if ROLE_HIERARCHY.get(user.role, 0) < ROLE_HIERARCHY[UserRole.ADMINISTRATOR]:
        await websocket.close(code=4403)
        return

    queue = AdminEventHub.subscribe()
    try:
        await websocket.send_json({"type": "connected", "user_id": str(user.id)})
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
            except TimeoutError:
                await websocket.send_json({"type": "ping"})
                continue
            await websocket.send_json(event)
    except Exception:  # noqa: BLE001 — client disconnect ends the loop
        pass
    finally:
        AdminEventHub.unsubscribe(queue)
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001 — already closed
            pass

# ============================================================================
# Production Readiness Center — Phase 8 (+8 new endpoints, read-only only)
# ============================================================================

@router.get(
    "/production-readiness",
    response_model=APIResponse[dict],
    summary="Production readiness status",
)
async def admin_production_readiness(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Read-only aggregate readiness dashboard."""
    checks = {}
    overall = "operational"
    checks["backup"] = await _pr_check_backup(db)
    checks["clerk_auth"] = await _pr_check_clerk_auth()
    if checks["clerk_auth"]["status"] in ("degraded", "blocked"): overall = "degraded"
    checks["backend"] = await _pr_check_backend()
    if checks["backend"]["status"] in ("degraded", "blocked"): overall = "degraded"
    checks["database"] = await _pr_check_db(db)
    if checks["database"]["status"] in ("degraded", "blocked"): overall = "degraded"
    checks["dns"] = await _pr_check_dns()
    if checks["dns"]["status"] in ("degraded", "blocked"): overall = "degraded"
    checks["clerk_webhooks"] = await _pr_check_webhook(db)
    if checks["clerk_webhooks"]["status"] in ("degraded", "blocked"): overall = "degraded"
    checks["cors"] = await _pr_check_cors()
    checks["security"] = await _pr_check_security()
    statuses = [v["status"] for v in checks.values() if isinstance(v, dict) and "status" in v]
    if any(s == "blocked" for s in statuses): overall = "blocked"
    elif any(s == "degraded" for s in statuses): overall = "degraded"
    elif any(s == "warning" for s in statuses): overall = "warning"
    elif "not_checked" in statuses: overall = "not_checked"
    else: overall = "operational"
    return APIResponse[dict](data={"overall_status": overall, "checks": checks})

@router.get("/production-readiness/backup", response_model=APIResponse[dict], summary="Backup verification logs (read-only)")
async def admin_backup_logs(_: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return APIResponse[dict](data={"status":"not_checked","details":"Actual backup metadata and integrity verification unavailable via this endpoint","last_checked":datetime.now(UTC).isoformat(),"warning":"Verify via dedicated backup system — not derived from audit logs","logs":[]})

@router.get("/production-readiness/clerk", response_model=APIResponse[dict], summary="Clerk auth health (read-only)")
async def admin_clerk_auth_logs(_: User = Depends(require_admin)):
    return APIResponse[dict](data=await _pr_check_clerk_auth())

@router.get("/production-readiness/backend", response_model=APIResponse[dict], summary="FastAPI backend health")
async def admin_backend_health(_: User = Depends(require_admin)): return APIResponse[dict](data=await _pr_check_backend())

@router.get("/production-readiness/database", response_model=APIResponse[dict], summary="Neon PostgreSQL health (read-only SELECT 1)")
async def admin_database_health(_: User = Depends(require_admin), db: AsyncSession = Depends(get_db)): return APIResponse[dict](data=await _pr_check_db(db))

@router.get("/production-readiness/dns", response_model=APIResponse[dict], summary="DNS verification")
async def admin_dns_health(_: User = Depends(require_admin)): return APIResponse[dict](data=await _pr_check_dns())

@router.get("/production-readiness/clerk-webhooks", response_model=APIResponse[dict], summary="Clerk webhook health (read-only)")
async def admin_clerk_webhook_health(_: User = Depends(require_admin), db: AsyncSession = Depends(get_db)): return APIResponse[dict](data=await _pr_check_webhook(db))

@router.get("/production-readiness/cors", response_model=APIResponse[dict], summary="CORS validation")
async def admin_cors_health(_: User = Depends(require_admin)): return APIResponse[dict](data=await _pr_check_cors())

@router.get("/production-readiness/security", response_model=APIResponse[dict], summary="Security audit (read-only; no secrets returned)")
async def admin_security_health(_: User = Depends(require_admin)): return APIResponse[dict](data=await _pr_check_security())

# Helper functions
async def _pr_check_backup(db: AsyncSession) -> dict:
    return {"status":"not_checked","details":"Actual backup metadata and integrity verification unavailable via this endpoint","last_checked":datetime.now(UTC).isoformat(),"warning":"Verify via dedicated backup system — not derived from audit logs"}

async def _pr_check_clerk_auth() -> dict:
    # Never claim authentication works merely because a secret/publishable key exists.
    # Actual connectivity requires a verified session/connection — unavailable here.
    return {"status":"not_checked","details":"Clerk authentication connectivity not verified via this endpoint (no session/token used; publishable key presence alone is insufficient)","last_checked":datetime.now(UTC).isoformat(),"warning":"Verify Clerk health through Clerk Dashboard or real session authentication"}

async def _pr_check_backend() -> dict:
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            base = (settings.PUBLIC_API_URL or "http://127.0.0.1:8000").rstrip("/")
            res = await client.get(f"{base}/health", timeout=5.0)
            if res.status_code == 200:
                data = res.json()
                return {"status":"pass","details":f"FastAPI healthy: {data.get('status')}","latency_ms":data.get("latency_ms"),"last_checked":datetime.now(UTC).isoformat(),"warning":None}
            return {"status":"degraded","details":f"/health returned {res.status_code}","last_checked":datetime.now(UTC).isoformat(),"warning":None}
    except Exception as e:
        return {"status":"degraded","details":f"Self-check unreachable: {str(e)[:200]}","last_checked":datetime.now(UTC).isoformat(),"warning":None}

async def _pr_check_db(db: AsyncSession) -> dict:
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        return {"status":"pass","details":"Read-only SELECT 1 executed successfully on existing async session","last_checked":datetime.now(UTC).isoformat(),"warning":None}
    except Exception as e:
        return {"status":"degraded","details":"Database SELECT 1 failed","last_checked":datetime.now(UTC).isoformat(),"warning":"Connection or query error — no raw exception or credentials exposed"}

async def _pr_check_dns() -> dict:
    try:
        import socket
        domain = (settings.FRONTEND_URL or "").replace("https://", "").replace("http://", "").split("/")[0]
        if not domain: return {"status":"not_checked","details":"FRONTEND_URL not configured","last_checked":datetime.now(UTC).isoformat(),"warning":None}
        ipv4 = socket.gethostbyname(domain)
        return {"status":"pass","details":f"DNS resolved for {domain}: {ipv4}","last_checked":datetime.now(UTC).isoformat(),"warning":None}
    except Exception as e:
        return {"status":"degraded","details":f"DNS resolution failed: {str(e)[:200]}","last_checked":datetime.now(UTC).isoformat(),"warning":None}

async def _pr_check_webhook(db: AsyncSession) -> dict:
    # Do not treat generic Clerk audit log entries as proof of webhook delivery.
    # If delivery evidence is unavailable, return not_checked.
    secret = getattr(settings, "CLERK_WEBHOOK_SECRET", None)
    if not secret or str(secret).startswith("whsec_test"):
        return {"status":"blocked","details":"Clerk webhook signing secret not configured or is test value","last_checked":datetime.now(UTC).isoformat(),"warning":"Configure production webhook secret; webhook delivery must be verified separately — not from audit logs"}
    # Secret exists but no delivery evidence available via this endpoint
    return {"status":"not_checked","details":"Webhook signing secret configured; webhook delivery evidence unavailable via this endpoint (do not assume success from secret presence or audit logs)","last_checked":datetime.now(UTC).isoformat(),"warning":"Verify delivery via Clerk Dashboard webhook logs"}

async def _pr_check_cors() -> dict:
    origins = getattr(settings, "CORS_ORIGINS", [])
    if "*" in origins:
        return {"status":"warning","details":f"CORS contains wildcard; origins: {origins}","last_checked":datetime.now(UTC).isoformat(),"warning":"Wildcard CORS origin detected"}
    return {"status":"pass","details":f"CORS origins normalized: {origins}","last_checked":datetime.now(UTC).isoformat(),"warning":None}

async def _pr_check_security() -> dict:
    issues = []; warnings_list = []
    jwt_secret = getattr(settings, "JWT_SECRET_KEY", None)
    jwt_secret_value = (
        jwt_secret.get_secret_value()
        if hasattr(jwt_secret, "get_secret_value")
        else ("" if jwt_secret is None else str(jwt_secret))
    )
    if not jwt_secret_value: issues.append("JWT_SECRET_KEY missing")
    elif jwt_secret_value in ("your-secret-key", "test-secret-key", "") or jwt_secret_value.startswith("change-me"): issues.append("JWT_SECRET_KEY is default/test value")
    if getattr(settings, "DEBUG", False): issues.append("DEBUG enabled")
    if "*" in getattr(settings, "CORS_ORIGINS", []): issues.append("Wildcard CORS")
    status = "blocked" if issues else ("warning" if warnings_list else "pass")
    return {"status":status,"details":f"Issues: {len(issues)}, Warnings: {len(warnings_list)} (no secret values returned)","issues":issues,"warnings":warnings_list,"last_checked":datetime.now(UTC).isoformat()}
