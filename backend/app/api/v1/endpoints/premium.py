import hashlib
import hmac
import json
import logging
import re
import secrets
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.premium import Coupon, Payment, Subscription, SubscriptionPlan
from app.schemas.base import APIResponse

router = APIRouter()
logger = logging.getLogger(__name__)


async def _create_youpi_session(
    order_id: str,
    *,
    amount: float,
    currency: str,
    plan: SubscriptionPlan,
) -> tuple[dict | None, str | None]:
    """Create the payment session on the YouPI-PG gateway (server-side).

    The browser SDK refuses to open a modal unless the payment was created on
    the server with trusted order data, so the session is created here through
    the checkout portal's ``/api/*`` proxy. Returns ``(session, None)`` on
    success or ``(None, gateway_error_code)`` on any failure; callers must fail
    closed — no coupon burn and no pending Payment row on failure.
    """
    from app.core.config import settings

    domain = (settings.YOUPI_API_DOMAIN or "").rstrip("/")
    merchant_id = (settings.YOUPI_MERCHANT_ID or "").strip()
    merchant_key = (
        settings.YOUPI_MERCHANT_API_KEY.get_secret_value()
        if settings.YOUPI_MERCHANT_API_KEY
        else (
            settings.YOUPI_WEBHOOK_SECRET.get_secret_value()
            if settings.YOUPI_WEBHOOK_SECRET
            else ""
        )
    )
    payload = {
        "orderId": order_id,
        "amount": f"{amount:.2f}",
        "currency": (currency or "INR").upper(),
        "metadata": {
            "plan_id": str(plan.id),
            "plan_name": plan.name,
            "source": "cyberverse",
        },
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=8.0)) as client:
            resp = await client.post(
                f"{domain}/api/v1/payments",
                json=payload,
                headers={"X-Merchant-Id": merchant_id, "X-Merchant-Key": merchant_key},
            )
    except httpx.HTTPError as exc:
        logger.warning(
            "YouPI gateway unreachable while creating %s (%s)", order_id, type(exc).__name__
        )
        return None, "GATEWAY_UNREACHABLE"

    if resp.status_code >= 400:
        # Log only the error code — never the merchant key or response body.
        code = f"HTTP_{resp.status_code}"
        try:
            body = resp.json()
            if isinstance(body, dict) and body.get("code"):
                code = str(body["code"])
        except ValueError:
            pass
        logger.warning("YouPI gateway rejected session %s: %s", order_id, code)
        return None, code

    try:
        session = resp.json()
    except ValueError:
        logger.warning("YouPI gateway returned a non-JSON body for %s", order_id)
        return None, "BAD_GATEWAY_RESPONSE"
    if not isinstance(session, dict) or not session.get("paymentId"):
        logger.warning("YouPI gateway returned no paymentId for %s", order_id)
        return None, "NO_PAYMENT_ID"
    return session, None


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

    discount = 0.0
    coupon = None
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

    final_amount = max(0.0, float(plan.price_amount) - discount)
    amount_in_paise = int(round(final_amount * 100))

    from app.core.config import settings
    from app.models.premium import PaymentStatus

    youpi_configured = bool(
        settings.YOUPI_API_DOMAIN
        and settings.YOUPI_MERCHANT_PUBLIC_KEY
        and settings.YOUPI_MERCHANT_ID
        and (settings.YOUPI_MERCHANT_API_KEY or settings.YOUPI_WEBHOOK_SECRET)
    )
    plan_currency = (plan.price_currency or "").upper()
    currency_ok = plan_currency == (settings.YOUPI_CURRENCY or "INR").upper()
    unavailable_reason: str | None = None
    if not youpi_configured:
        unavailable_reason = "not_configured"
    elif not currency_ok:
        unavailable_reason = "currency_mismatch"
        logger.warning(
            "YouPI checkout blocked for plan %s: price_currency=%s != YOUPI_CURRENCY=%s",
            plan.slug,
            plan_currency,
            settings.YOUPI_CURRENCY,
        )

    base_payload = {
        "amount": final_amount,
        "amount_paise": amount_in_paise,
        "currency": plan.price_currency,
        "name": "CyberVerse",
        "description": f"CyberVerse {plan.name} Plan",
        "plan_name": plan.name,
        "discount_applied": discount > 0,
    }

    if unavailable_reason:
        # Nothing is charged and no pending order is created; the coupon is
        # not consumed either. The frontend shows a payments-unavailable state.
        return APIResponse[dict](
            data={
                "youpi_enabled": False,
                "youpi_unavailable_reason": unavailable_reason,
                "pay_domain": None,
                "merchant_public_key": None,
                "order_id": None,
                **base_payload,
            }
        )

    # Fail closed BEFORE any DB writes: without a gateway session the browser
    # SDK cannot open a modal, so burning the coupon or creating a pending
    # Payment row would only leave garbage behind on every failed attempt.
    order_id = f"CV-{secrets.token_hex(8)}"
    session, session_error = await _create_youpi_session(
        order_id,
        amount=final_amount,
        currency=plan_currency,
        plan=plan,
    )
    if session_error is not None:
        return APIResponse[dict](
            data={
                "youpi_enabled": False,
                "youpi_unavailable_reason": "session_creation_failed",
                "gateway_code": session_error,
                "pay_domain": None,
                "merchant_public_key": None,
                "order_id": None,
                **base_payload,
            }
        )

    if coupon is not None:
        coupon.used_count += 1

    plan_tier = str(plan.tier.value if hasattr(plan.tier, "value") else plan.tier).lower()
    payment = Payment(
        user_id=user.id,
        payment_intent_id=order_id,
        status=PaymentStatus.PENDING,
        amount=final_amount,
        currency=plan_currency,
        payment_method="upi",
        provider="youpi",
        description=f"CyberVerse {plan.name} Plan",
        meta_data={
            "plan_id": str(plan.id),
            "plan_name": plan.name,
            "plan_tier": plan_tier,
            "coupon_code": (request.coupon_code or "").upper() or None,
            "discount_applied": discount > 0,
            "youpi_payment_id": session["paymentId"],
        },
    )
    db.add(payment)
    await db.commit()

    return APIResponse[dict](
        data={
            "youpi_enabled": True,
            "pay_domain": (settings.YOUPI_API_DOMAIN or "").rstrip("/"),
            "merchant_public_key": settings.YOUPI_MERCHANT_PUBLIC_KEY,
            "order_id": order_id,
            "payment_id": session["paymentId"],
            "checkout_url": session.get("checkoutUrl"),
            **base_payload,
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


@router.post("/webhook/youpi", summary="YouPI-PG webhook — activate premium on bank reconciliation")
async def youpi_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receive YouPI-PG gateway webhooks.

    Fail-closed: requires ``YOUPI_WEBHOOK_SECRET`` to be configured and a valid
    HMAC-SHA256 signature of the *raw* request body in the ``X-Gateway-Signature``
    header (``sha256=<hex>``). If the gateway also sends ``X-Gateway-Signature-V2``
    (HMAC of ``<timestamp>.<raw body>``) it is verified as well.

    Settlement trust: YouPI-PG is an observer-based gateway. OBSERVED_SUCCESS is
    NOT proof of payment. This handler only acts on ``event=RECONCILED`` +
    ``settlementState=RECONCILED`` + ``method=UPI``, matched against our own
    pending order, with the amount (paise) and a 12-digit UTR validated.
    Delivery idempotency is keyed on the gateway's stable ``X-Gateway-Delivery-Id``
    (never the timestamp). On a valid reconciliation it marks the pending payment
    COMPLETED, upserts an ACTIVE subscription (period derived from the plan tier),
    upgrades the user to premium_student (unless they hold a privileged role),
    audits and notifies admins. Everything else is acknowledged with HTTP 200 so
    the gateway stops retrying, and is recorded for review instead of fulfilled.
    """
    from uuid import UUID

    from app.core.config import settings
    from app.models.notification import NotificationType
    from app.models.premium import PaymentStatus, SubscriptionStatus
    from app.models.user import User, UserRole
    from app.services.audit_service import AuditService
    from app.services.notification_service import NotificationService

    secret = settings.YOUPI_WEBHOOK_SECRET
    if not secret:
        raise HTTPException(status_code=503, detail="YouPI-PG webhook is not configured")

    raw = await request.body()
    secret_bytes = secret.get_secret_value().encode("utf-8")

    sig_v1 = request.headers.get("x-gateway-signature", "")
    sig_v1_hex = sig_v1.removeprefix("sha256=").strip().lower()
    expected_v1 = hmac.new(secret_bytes, raw, hashlib.sha256).hexdigest()
    if not sig_v1_hex or not hmac.compare_digest(expected_v1, sig_v1_hex):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    sig_v2 = request.headers.get("x-gateway-signature-v2")
    if sig_v2:
        ts = request.headers.get("x-gateway-timestamp", "")
        signed_payload = f"{ts}.".encode("utf-8") + raw
        expected_v2 = hmac.new(secret_bytes, signed_payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_v2, sig_v2.removeprefix("sha256=").strip().lower()):
            raise HTTPException(status_code=401, detail="Invalid V2 webhook signature")

    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Malformed webhook payload") from None
    if not isinstance(event, dict):
        raise HTTPException(status_code=400, detail="Malformed webhook payload")

    delivery_id = str(
        event.get("deliveryId") or request.headers.get("x-gateway-delivery-id") or ""
    ).strip()
    event_type = str(event.get("event") or "").strip().upper()
    settlement_state = str(event.get("settlementState") or "").strip().upper()
    method = str(event.get("method") or "").strip().upper()
    order_id = str(event.get("orderId") or "").strip()
    amount_str = str(event.get("amount") or "").strip()
    amount_paise_raw = event.get("amountPaise")
    utr = str(event.get("utr") or "").strip()
    gateway_payment_id = str(event.get("paymentId") or "").strip()

    async def _audit(action: str, *, resource_id: str | None, user_id, meta: dict) -> None:
        try:
            await AuditService.log(
                db,
                action=action,
                resource_type="payment",
                resource_id=resource_id,
                user_id=user_id,
                meta=meta,
                commit=False,
            )
        except Exception:
            logger.warning("Audit log for youpi webhook failed", exc_info=True)

    async def _rejected(
        reason: str, *, meta: dict | None = None, notify: bool = True
    ) -> APIResponse[dict]:
        await _audit(
            "youpi.rejected",
            resource_id=order_id or None,
            user_id=None,
            meta={"reason": reason, **(meta or {})},
        )
        if notify:
            await NotificationService.notify_admins(
                db,
                title="YouPI-PG webhook needs review",
                body=(
                    f"Webhook rejected ({reason}) for order {order_id or 'unknown'}. "
                    "No premium was granted."
                ),
                notification_type=NotificationType.PREMIUM,
                icon="alert-triangle",
                link="/admin/payments",
                data={"reason": reason, "order_id": order_id or None, **(meta or {})},
                commit=False,
            )
        await db.commit()
        return APIResponse[dict](data={"status": "rejected", "reason": reason})

    # Only bank-reconciled UPI events may activate premium. Everything else
    # (OBSERVED_SUCCESS firings, non-UPI methods, other event types) is logged
    # for review but never fulfilled.
    if event_type != "RECONCILED" or settlement_state != "RECONCILED" or method != "UPI":
        await _audit(
            "youpi.ignored",
            resource_id=order_id or None,
            user_id=None,
            meta={
                "event": event_type,
                "settlement_state": settlement_state,
                "method": method,
                "delivery_id": delivery_id or None,
            },
        )
        await db.commit()
        return APIResponse[dict](data={"status": "ignored", "event": event_type})

    if not delivery_id:
        return await _rejected("missing_delivery_id")
    if not order_id:
        return await _rejected("missing_order_id")
    if not re.fullmatch(r"\d{12}", utr):
        return await _rejected("invalid_utr", meta={"utr": utr[:20]})

    # Idempotency: same delivery id seen before → acknowledge without
    # double-fulfilling. Also short-circuit an already-completed order.
    dup_result = await db.execute(
        select(Payment.id).where(Payment.meta_data["youpi_delivery_id"].astext == delivery_id)
    )
    if dup_result.scalar_one_or_none() is not None:
        return APIResponse[dict](data={"status": "ok", "deduplicated": True})

    result = await db.execute(select(Payment).where(Payment.payment_intent_id == order_id))
    payment = result.scalar_one_or_none()
    if payment is None:
        return await _rejected("unknown_order", meta={"order_id": order_id})
    if payment.status == PaymentStatus.COMPLETED:
        await _audit(
            "youpi.duplicate_order",
            resource_id=order_id,
            user_id=payment.user_id,
            meta={"delivery_id": delivery_id},
        )
        await db.commit()
        return APIResponse[dict](data={"status": "ok", "deduplicated": True})

    expected_paise = int(round(float(payment.amount) * 100))
    try:
        payload_paise = int(amount_paise_raw)
    except (TypeError, ValueError):
        payload_paise = -1
    try:
        payload_float_paise = int(round(float(amount_str) * 100))
    except (TypeError, ValueError):
        payload_float_paise = -1
    if payload_paise != expected_paise or payload_float_paise != expected_paise:
        return await _rejected(
            "amount_mismatch",
            meta={
                "expected_paise": expected_paise,
                "amount_paise": amount_paise_raw,
                "amount": amount_str,
            },
        )

    now = datetime.now(UTC)
    payment.status = PaymentStatus.COMPLETED
    payment.paid_at = now
    payment.payment_method = "upi"
    payment.provider = "youpi"
    payment.failure_reason = None
    payment.meta_data = {
        **(payment.meta_data or {}),
        "youpi_delivery_id": delivery_id,
        "youpi_payment_id": gateway_payment_id or None,
        "youpi_utr": utr,
        "youpi_event": event_type,
        "youpi_settlement_state": settlement_state,
    }

    # Resolve the plan the pending order was created for.
    plan = None
    plan_id_raw = (payment.meta_data or {}).get("plan_id")
    if plan_id_raw:
        try:
            plan = await db.get(SubscriptionPlan, UUID(str(plan_id_raw)))
        except Exception:
            plan = None

    period_end = None
    if plan is not None:
        tier_value = str(plan.tier.value if hasattr(plan.tier, "value") else plan.tier).lower()
        period_days = {"monthly": 30, "quarterly": 90, "annual": 365, "lifetime": 36500}.get(
            tier_value, 30
        )
        period_end = now + timedelta(days=period_days)

        sub_result = await db.execute(
            select(Subscription).where(
                Subscription.user_id == payment.user_id,
                Subscription.plan_id == plan.id,
                Subscription.status.in_(
                    [
                        SubscriptionStatus.PENDING,
                        SubscriptionStatus.TRIAL,
                        SubscriptionStatus.ACTIVE,
                        SubscriptionStatus.PAST_DUE,
                    ]
                ),
            )
        )
        subscription = sub_result.scalar_one_or_none()
        if subscription is None:
            subscription = Subscription(
                user_id=payment.user_id,
                plan_id=plan.id,
                status=SubscriptionStatus.ACTIVE,
                current_period_start=now,
                current_period_end=period_end,
                cancel_at_period_end=False,
                meta_data={"source": "youpi_webhook"},
            )
            db.add(subscription)
        else:
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.current_period_start = now
            subscription.current_period_end = period_end
            subscription.cancel_at_period_end = False
            subscription.meta_data = {
                **(subscription.meta_data or {}),
                "source": "youpi_webhook",
            }
        await db.flush()
        payment.subscription_id = subscription.id

    premium_activated = False
    user = await db.get(User, payment.user_id)
    if user is not None and user.role in (UserRole.GUEST, UserRole.STUDENT):
        user.role = UserRole.PREMIUM_STUDENT
        premium_activated = True

    await _audit(
        "youpi.payment.reconciled",
        resource_id=order_id,
        user_id=payment.user_id,
        meta={
            "amount_paise": expected_paise,
            "utr": utr,
            "delivery_id": delivery_id,
            "plan_id": plan_id_raw,
            "premium_activated": premium_activated,
            "subscription_period_end": period_end.isoformat() if period_end else None,
        },
    )
    await NotificationService.notify_admins(
        db,
        title="Premium activated via YouPI-PG",
        body=(
            f"INR {float(payment.amount):.2f} (UPI, UTR {utr}) reconciled for order {order_id}. "
            + (
                "Subscription created/extended and user promoted to premium_student."
                if premium_activated
                else "Subscription created/extended; user role unchanged."
            )
        ),
        notification_type=NotificationType.PREMIUM,
        icon="credit-card",
        link="/admin/payments",
        data={
            "order_id": order_id,
            "utr": utr,
            "delivery_id": delivery_id,
            "premium_activated": premium_activated,
        },
        commit=False,
    )
    await db.commit()
    return APIResponse[dict](
        data={
            "status": "ok",
            "event": event_type,
            "order_id": order_id,
            "premium_activated": premium_activated,
        }
    )
