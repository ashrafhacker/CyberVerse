import calendar
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.config import settings
from app.core.database import get_db
from app.models.premium import (
    Coupon,
    Payment,
    PaymentStatus,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)
from app.models.user import User, UserRole
from app.schemas.base import APIResponse
from app.services import youpi_service

logger = structlog.get_logger(__name__)

router = APIRouter()


def _add_months(start: datetime, months: int) -> datetime:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return start.replace(year=year, month=month, day=day)


def _period_end(start: datetime, interval: str | None, count: int | None) -> datetime | None:
    interval = (interval or "month").lower()
    count = max(1, int(count or 1))
    if interval in {"lifetime", "forever"}:
        return None
    if interval == "day":
        return start + timedelta(days=count)
    if interval == "week":
        return start + timedelta(weeks=count)
    if interval == "year":
        return _add_months(start, 12 * count)
    return _add_months(start, count)


def _parse_gateway_time(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed


def _event_value(payload: dict, key: str) -> str:
    value = payload.get(key)
    return str(value).upper() if value is not None else ""


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
    if not youpi_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="YouPI PG is not configured (YOUPI_MERCHANT_ID / YOUPI_WEBHOOK_SECRET)",
        )

    try:
        plan_id = UUID(request.plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan ID") from None

    plan_result = await db.execute(
        select(SubscriptionPlan).where(
            SubscriptionPlan.id == plan_id,
            SubscriptionPlan.is_active.is_(True),
        )
    )
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if plan.price_currency.upper() != settings.YOUPI_CURRENCY.upper():
        raise HTTPException(
            status_code=400,
            detail=f"YouPI supports {settings.YOUPI_CURRENCY} plans only",
        )

    discount = Decimal("0")
    coupon_code = request.coupon_code.upper() if request.coupon_code else None
    if coupon_code:
        coupon_result = await db.execute(select(Coupon).where(Coupon.code == coupon_code))
        coupon = coupon_result.scalar_one_or_none()
        if not coupon or not coupon.is_active:
            raise HTTPException(status_code=400, detail="Invalid coupon code")
        if coupon.max_uses is not None and coupon.used_count >= coupon.max_uses:
            raise HTTPException(status_code=400, detail="Coupon usage limit reached")
        if coupon.discount_type == "percentage":
            discount = Decimal(plan.price_amount) * Decimal(coupon.discount_value) / Decimal("100")
        else:
            discount = Decimal(coupon.discount_value)
        coupon.used_count += 1

    final_amount = max(Decimal("0"), Decimal(plan.price_amount) - discount)
    if final_amount <= 0:
        raise HTTPException(status_code=400, detail="Checkout total must be greater than zero")

    metadata = {
        "plan_id": str(plan.id),
        "plan_slug": plan.slug,
        "user_id": str(user.id),
    }
    if coupon_code:
        metadata["coupon_code"] = coupon_code

    payment = Payment(
        user_id=user.id,
        status=PaymentStatus.PENDING,
        amount=final_amount,
        currency=settings.YOUPI_CURRENCY,
        payment_method="upi",
        provider="youpi",
        description=f"CyberVerse {plan.name} Plan",
        meta_data=metadata,
    )
    db.add(payment)
    await db.flush()

    return_url = settings.YOUPI_RETURN_URL or f"{settings.FRONTEND_URL.rstrip('/')}/dashboard"

    try:
        gateway = await youpi_service.create_payment(
            order_id=str(payment.id),
            amount=final_amount,
            description=payment.description or "CyberVerse subscription",
            customer_name=getattr(user, "full_name", None),
            customer_email=user.email,
            return_url=return_url,
            metadata={**metadata, "payment_id": str(payment.id)},
        )
    except youpi_service.YoupiGatewayError as exc:
        logger.error(
            "youpi.checkout_failed",
            payment_id=str(payment.id),
            status_code=exc.status_code,
            body=exc.body,
        )
        await db.rollback()
        raise HTTPException(
            status_code=502,
            detail="Payment gateway unavailable; please try again",
        ) from exc

    payment.payment_intent_id = str(gateway["paymentId"])
    payment.meta_data = {
        **metadata,
        "youpi_payment_id": str(gateway["paymentId"]),
        "youpi_status": gateway.get("status"),
        "youpi_checkout_url": gateway["checkoutUrl"],
    }
    await db.commit()

    return APIResponse[dict](
        data={
            "checkout_url": gateway["checkoutUrl"],
            "payment_id": str(payment.id),
            "provider": "youpi",
            "amount": youpi_service.format_amount(final_amount),
            "currency": settings.YOUPI_CURRENCY,
            "plan_name": plan.name,
            "discount_applied": discount > 0,
        }
    )


@router.post("/webhook/youpi", include_in_schema=False)
async def youpi_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle signed YouPI PG webhooks.

    Fulfillment happens only on ``RECONCILED`` (bank-statement matched).
    ``OBSERVED_SUCCESS`` and ``MANUAL_REVIEW`` deliberately leave the payment
    pending until reconciliation.
    """
    if not settings.YOUPI_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="YouPI webhook secret is not configured")

    raw_body = await request.body()
    if not youpi_service.verify_webhook_signature(
        raw_body, request.headers.get("X-Gateway-Signature")
    ):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw_body)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid webhook payload") from None
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    event = _event_value(payload, "event")
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    order_id = metadata.get("payment_id") or payload.get("orderId")
    try:
        payment_id = UUID(str(order_id))
    except (TypeError, ValueError):
        logger.warning("youpi.webhook_invalid_order", event=event, order_id=order_id)
        return {"received": True, "ignored": "invalid_order_id"}

    result = await db.execute(
        select(Payment).where(Payment.id == payment_id).with_for_update()
    )
    payment = result.scalar_one_or_none()
    if payment is None or payment.provider != "youpi":
        logger.warning(
            "youpi.webhook_unknown_payment",
            event=event,
            payment_id=str(payment_id),
        )
        return {"received": True, "ignored": "unknown_payment"}

    meta = dict(payment.meta_data or {})
    delivery_id = request.headers.get("X-Gateway-Delivery-Id") or str(
        payload.get("deliveryId") or ""
    )
    seen = list(meta.get("youpi_delivery_ids") or [])
    if delivery_id and delivery_id in seen:
        return {"received": True, "duplicate": True}
    if delivery_id:
        meta["youpi_delivery_ids"] = (seen + [delivery_id])[-20:]

    gateway_payment_id = str(payload.get("paymentId") or "")
    utr = payload.get("utr")
    method = _event_value(payload, "method")
    settlement_state = _event_value(payload, "settlementState")
    meta.update(
        {
            "youpi_last_event": event,
            "youpi_last_event_at": datetime.now(UTC).isoformat(),
        }
    )
    if gateway_payment_id:
        meta["youpi_payment_id"] = gateway_payment_id
    if utr:
        meta["youpi_utr"] = str(utr)
    if method:
        meta["youpi_method"] = method
    if settlement_state:
        meta["youpi_settlement_state"] = settlement_state
    payment.meta_data = meta

    if event == "RECONCILED":
        try:
            paid_amount = Decimal(str(payload.get("amount")))
        except (InvalidOperation, TypeError, ValueError):
            paid_amount = None

        if paid_amount is None or paid_amount != Decimal(payment.amount):
            meta["youpi_fulfillment"] = "amount_mismatch"
            payment.meta_data = meta
            await db.commit()
            logger.error(
                "youpi.webhook_amount_mismatch",
                payment_id=str(payment.id),
                expected=str(payment.amount),
                received=payload.get("amount"),
            )
            return {"received": True, "ignored": "amount_mismatch"}

        currency = _event_value(payload, "currency")
        if currency and currency != payment.currency.upper():
            meta["youpi_fulfillment"] = "currency_mismatch"
            payment.meta_data = meta
            await db.commit()
            logger.error(
                "youpi.webhook_currency_mismatch",
                payment_id=str(payment.id),
                expected=payment.currency,
                received=currency,
            )
            return {"received": True, "ignored": "currency_mismatch"}

        if method and method != "UPI":
            meta["youpi_fulfillment"] = f"ignored_method_{method.lower()}"
            payment.meta_data = meta
            await db.commit()
            return {"received": True, "ignored": "non_upi_method"}

        if settlement_state and settlement_state != "RECONCILED":
            meta["youpi_fulfillment"] = "awaiting_settlement"
            payment.meta_data = meta
            await db.commit()
            return {"received": True, "ignored": "not_settled"}

        if payment.status == PaymentStatus.REFUNDED:
            meta["youpi_fulfillment"] = "refunded"
            payment.meta_data = meta
            await db.commit()
            return {"received": True, "ignored": "refunded"}

        if payment.status == PaymentStatus.COMPLETED:
            meta["youpi_fulfillment"] = "already_fulfilled"
            payment.meta_data = meta
            await db.commit()
            return {"received": True, "duplicate": True}

        plan_id_raw = meta.get("plan_id")
        try:
            plan_id = UUID(str(plan_id_raw))
        except (TypeError, ValueError):
            plan_id = None
        if plan_id is None:
            logger.error(
                "youpi.webhook_missing_plan",
                payment_id=str(payment.id),
                metadata=metadata,
            )
            meta["youpi_fulfillment"] = "missing_plan"
            payment.meta_data = meta
            await db.commit()
            return {"received": True, "ignored": "missing_plan"}

        plan = await db.get(SubscriptionPlan, plan_id)
        if plan is None:
            logger.error(
                "youpi.webhook_plan_not_found",
                payment_id=str(payment.id),
                plan_id=str(plan_id),
            )
            raise HTTPException(
                status_code=500, detail="Subscription plan not found"
            ) from None

        now = datetime.now(UTC)
        subscription = Subscription(
            user_id=payment.user_id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=now,
            current_period_end=_period_end(
                now, plan.billing_interval, plan.billing_interval_count
            ),
            meta_data={
                "provider": "youpi",
                "order_id": str(payment.id),
                "youpi_payment_id": gateway_payment_id,
                "utr": str(utr) if utr else None,
            },
        )
        db.add(subscription)
        await db.flush()

        payment.subscription_id = subscription.id
        payment.status = PaymentStatus.COMPLETED
        payment.paid_at = _parse_gateway_time(payload.get("completedAt")) or now
        payment.failure_reason = None

        user = await db.get(User, payment.user_id)
        if user and user.role in {UserRole.GUEST, UserRole.STUDENT}:
            user.role = UserRole.PREMIUM_STUDENT

        meta["youpi_fulfillment"] = "fulfilled"
        payment.meta_data = meta
        await db.commit()
        logger.info(
            "youpi.payment_fulfilled",
            payment_id=str(payment.id),
            subscription_id=str(subscription.id),
            user_id=str(payment.user_id),
        )
        return {"received": True, "status": "fulfilled"}

    if event == "FAILED":
        if payment.status == PaymentStatus.PENDING:
            payment.status = PaymentStatus.FAILED
            reason = payload.get("failureReason") or payload.get("reason") or "Payment failed"
            payment.failure_reason = str(reason)[:300]
        meta["youpi_fulfillment"] = "failed"
    elif event in {"EXPIRED", "CANCELLED"}:
        if payment.status == PaymentStatus.PENDING:
            payment.status = PaymentStatus.CANCELLED
            payment.failure_reason = event.title()[:300]
        meta["youpi_fulfillment"] = event.lower()
    elif event in {"OBSERVED_SUCCESS", "MANUAL_REVIEW"}:
        meta["youpi_fulfillment"] = "pending_reconciliation"
    elif event == "SUCCESS":
        meta["youpi_fulfillment"] = "ignored_success_event"
    else:
        meta["youpi_fulfillment"] = "ignored_event"

    payment.meta_data = meta
    await db.commit()
    return {"received": True, "event": event}


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
