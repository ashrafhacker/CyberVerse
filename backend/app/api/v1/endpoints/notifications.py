from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.notification import Announcement, Notification
from app.schemas.base import APIResponse, MessageResponse, PaginatedResponse
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get(
    "/announcements",
    response_model=APIResponse[list],
    summary="List published announcements (public)",
)
async def list_published_announcements(db: AsyncSession = Depends(get_db)):
    """Public feed: published, active announcements only (drafts and soft-
    deleted items are never exposed)."""
    result = await db.execute(
        select(Announcement)
        .where(
            Announcement.is_active.is_(True),
            Announcement.is_draft.is_(False),
        )
        .order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc())
        .limit(50)
    )
    announcements = result.scalars().all()
    return APIResponse[list](
        data=[
            {
                "id": str(a.id),
                "title": a.title,
                "body": a.body,
                "announcement_type": a.announcement_type,
                "is_pinned": a.is_pinned,
                "image_url": a.image_url,
                "link": a.link,
                "published_at": a.published_at.isoformat() if a.published_at else None,
                "expires_at": a.expires_at.isoformat() if a.expires_at else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in announcements
        ]
    )


@router.get("/", response_model=APIResponse[PaginatedResponse], summary="List my notifications")
async def list_notifications(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
):
    stmt = select(Notification).where(Notification.user_id == user.id)
    count_stmt = select(func.count(Notification.id)).where(Notification.user_id == user.id)

    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
        count_stmt = count_stmt.where(Notification.is_read.is_(False))

    total = (await db.execute(count_stmt)).scalar_one()
    result = await db.execute(
        stmt.order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    notifications = result.scalars().all()

    items = [
        {
            "id": str(n.id),
            "notification_type": n.notification_type.value if hasattr(n.notification_type, "value") else n.notification_type,
            "title": n.title,
            "body": n.body,
            "icon": n.icon,
            "link": n.link,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifications
    ]

    data = PaginatedResponse.create(items, total, page, page_size)
    return APIResponse[PaginatedResponse](data=data)


@router.get("/unread-count", response_model=APIResponse[dict], summary="Get unread notification count")
async def unread_count(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    count = await NotificationService.unread_count(db, user.id)
    return APIResponse[dict](data={"unread": count})


@router.post("/{notification_id}/read", response_model=APIResponse[dict], summary="Mark notification as read")
async def mark_read(
    notification_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    success = await NotificationService.mark_read(db, user.id, notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return APIResponse[dict](data={"read": True})


@router.post("/read-all", response_model=APIResponse[dict], summary="Mark all notifications as read")
async def mark_all_read(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    count = await NotificationService.mark_all_read(db, user.id)
    return APIResponse[dict](data={"marked_read": count})


@router.delete("/{notification_id}", response_model=MessageResponse, summary="Delete a notification")
async def delete_notification(
    notification_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_dismissed = True
    notification.dismissed_at = func.now()
    await db.commit()
    return MessageResponse(message="Notification dismissed")
