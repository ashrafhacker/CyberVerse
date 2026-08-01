from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_admin
from app.core.database import get_db
from app.models.premium import Coupon, Payment, Subscription, SubscriptionPlan
from app.models.user import UserRole
from app.schemas.base import APIResponse

router = APIRouter()


class CheckoutRequest(BaseModel):
    plan_id: str = Field(..., min_length=1)
    coupon_code: str | None = None


class CouponRedeemRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)


@router.get("/plans", response_model=APIResponse[list], summary="List premium plans")
async def list_plans(
    _: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SubscriptionPlan)
        .where(SubscriptionPlan.is_active.is_(True))
        .order_by(SubscriptionPlan.display_order)
    )
    plans = result.scalars().all()
    return APIResponse[list](
        data=[
            {
                "id": str(p.id),
                "slug": p.slug,
                "name": p.name,
                "description": p.description,
                "tier": p.tier.value if hasattr(p.tier, "value") else p.tier,
                "price_amount": str(p.price_amount),
                "price_currency": p.price_currency,
                "billing_interval": p.billing_interval,
                "billing_interval_count": p.billing_interval_count,
                "trial_days": p.trial_days,
                "features": p.features,
            }
            for p in plans
        ]
    )


@router.get("/status", response_model=APIResponse[dict], summary="Get my subscription status")
async def my_subscription(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        return APIResponse[dict](
            data={
                "active": False,
                "role": user.role.value if hasattr(user.role, "value") else user.role,
            }
        )

    plan = (
        await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == subscription.plan_id))
    ).scalar_one_or_none()

    return APIResponse[dict](
        data={
            "active": subscription.status in ("active", "trial"),
            "status": subscription.status.value if hasattr(subscription.status, "value") else subscription.status,
            "plan": plan.name if plan else None,
            "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "role": user.role.value if hasattr(user.role, "value") else user.role,
        }
    )


@router.get("/billing-history", response_model=APIResponse[list], summary="Get billing history")
async def billing_history(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Payment)
        .where(Payment.user_id == user.id)
        .order_by(Payment.created_at.desc())
        .limit(50)
    )
    payments = result.scalars().all()
    return APIResponse[list](
        data=[
            {
                "id": str(p.id),
                "amount": str(p.amount),
                "currency": p.currency,
                "status": p.status.value if hasattr(p.status, "value") else p.status,
                "description": p.description,
                "receipt_url": p.receipt_url,
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in payments
        ]
    )


@router.post("/checkout", response_model=APIResponse[dict], summary="Create checkout session")
async def checkout(
    request: CheckoutRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    from uuid import UUID

    try:
        plan_id = UUID(request.plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan ID")

    plan_result = await db.execute(
        select(SubscriptionPlan).where(
            SubscriptionPlan.id == plan_id,
            SubscriptionPlan.is_active.is_(True),
        )
    )
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    discount = 0
    if request.coupon_code:
        coupon_result = await db.execute(
            select(Coupon).where(Coupon.code == request.coupon_code.upper())
        )
        coupon = coupon_result.scalar_one_or_none()
        if not coupon or not coupon.is_active:
            raise HTTPException(status_code=400, detail="Invalid coupon code")
        if coupon.discount_type == "percentage":
            discount = float(plan.price_amount) * float(coupon.discount_value) / 100
        else:
            discount = float(coupon.discount_value)
        coupon.used_count += 1
        await db.commit()

    final_amount = max(0, float(plan.price_amount) - discount)

    # In production, create a Stripe Checkout Session here.
    checkout_url = (
        "https://buy.stripe.com/test_" + str(plan_id).replace("-", "")[:16]
    )

    return APIResponse[dict](
        data={
            "checkout_url": checkout_url,
            "amount": final_amount,
            "currency": plan.price_currency,
            "plan_name": plan.name,
            "discount_applied": discount > 0,
        }
    )


@router.post("/coupons/redeem", response_model=APIResponse[dict], summary="Validate a coupon")
async def redeem_coupon(
    request: CouponRedeemRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Coupon).where(Coupon.code == request.code.upper(), Coupon.is_active.is_(True))
    )
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")

    return APIResponse[dict](
        data={
            "code": coupon.code,
            "discount_type": coupon.discount_type,
            "discount_value": str(coupon.discount_value),
        }
    )