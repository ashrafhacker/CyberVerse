from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_admin
from app.core.database import get_db
from app.models.analytics import AnalyticsEvent
from app.models.user import User, UserRole
from app.models.progress import PlayerProgress
from app.schemas.base import APIResponse

router = APIRouter()


def _date_range(days: int) -> tuple[datetime, datetime]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return start, end


@router.get("/overview", response_model=APIResponse[dict], summary="Platform analytics overview (admin)")
async def analytics_overview(
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    start, end = _date_range(days)

    total_users = (await db.execute(select(func.count(User.id)))).scalar_one()
    new_users = (
        await db.execute(select(func.count(User.id)).where(User.created_at >= start))
    ).scalar_one()
    active_users = (
        await db.execute(select(func.count(User.id)).where(User.last_login >= start))
    ).scalar_one()
    premium_users = (
        await db.execute(
            select(func.count(User.id)).where(User.role.in_([UserRole.PREMIUM_STUDENT]))
        )
    ).scalar_one()
    total_xp = (
        await db.execute(select(func.coalesce(func.sum(PlayerProgress.total_xp), 0)))
    ).scalar_one()

    event_count = (
        await db.execute(
            select(func.count(AnalyticsEvent.id)).where(AnalyticsEvent.created_at >= start)
        )
    ).scalar_one()

    return APIResponse[dict](
        data={
            "period_days": days,
            "total_users": total_users,
            "new_users": new_users,
            "active_users": active_users,
            "premium_users": premium_users,
            "total_xp_distributed": total_xp,
            "event_count": event_count,
        }
    )


@router.get("/dau", response_model=APIResponse[list], summary="Daily active users (admin)")
async def daily_active_users(
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    start, _ = _date_range(days)
    result = await db.execute(
        select(func.date(User.last_login), func.count(User.id))
        .where(User.last_login >= start)
        .group_by(func.date(User.last_login))
        .order_by(func.date(User.last_login))
    )
    return APIResponse[list](
        data=[{"date": str(day), "count": count} for day, count in result.all()]
    )


@router.get("/events", response_model=APIResponse[dict], summary="Event analytics (admin)")
async def event_analytics(
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    start, _ = _date_range(days)
    result = await db.execute(
        select(AnalyticsEvent.event_type, func.count(AnalyticsEvent.id))
        .where(AnalyticsEvent.created_at >= start)
        .group_by(AnalyticsEvent.event_type)
        .order_by(func.count(AnalyticsEvent.id).desc())
        .limit(20)
    )
    return APIResponse[dict](
        data={
            "events": [
                {"event_type": event_type, "count": count}
                for event_type, count in result.all()
            ]
        }
    )


@router.get("/progression", response_model=APIResponse[dict], summary="XP distribution analytics (admin)")
async def xp_distribution(
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(
            func.width_bucket(PlayerProgress.total_xp, 0, 100000, 10).label("bucket"),
            func.count(PlayerProgress.id),
        )
        .group_by("bucket")
        .order_by("bucket")
    )
    buckets = result.all()

    return APIResponse[dict](
        data={
            "distribution": [
                {
                    "bucket": bucket,
                    "min_xp": bucket * 10000,
                    "max_xp": (bucket + 1) * 10000,
                    "users": count,
                }
                for bucket, count in buckets
            ]
        }
    )


@router.get("/revenue", response_model=APIResponse[dict], summary="Revenue summary (admin)")
async def revenue_summary(
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.premium import Payment

    result = await db.execute(
        select(
            func.coalesce(func.sum(Payment.amount), 0),
            func.count(Payment.id),
        ).where(Payment.status == "completed")
    )
    total_revenue, total_payments = result.one()

    monthly = await db.execute(
        select(
            func.date_trunc("month", Payment.created_at).label("month"),
            func.sum(Payment.amount),
        )
        .where(Payment.status == "completed")
        .group_by("month")
        .order_by("month")
        .limit(12)
    )

    return APIResponse[dict](
        data={
            "total_revenue": str(total_revenue),
            "total_payments": total_payments,
            "monthly": [
                {"month": str(m), "amount": str(amount)}
                for m, amount in monthly.all()
            ],
        }
    )