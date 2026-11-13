"""YouPI-PG webhook fulfillment: RECONCILED-only activation + idempotency.

The live staging probes verified the signature/ignore/reject paths, but the
154-test suite had zero coverage of the fulfillment path. These tests pin the
three behaviors that matter for real money:

1. A correctly signed ``event=RECONCILED`` webhook marks the pending Payment
   COMPLETED, upserts one ACTIVE subscription (~30d monthly period) and
   promotes the user to ``premium_student`` — and an immediate replay of the
   same delivery id is deduplicated (no second subscription).
2. An amount mismatch is rejected (fail-closed): Payment stays PENDING, no
   subscription, no role change.
"""

import hashlib
import hmac
import json
from datetime import timedelta

import pytest
from pydantic import SecretStr
from sqlalchemy import select

from app.core.config import settings
from app.models.premium import (
    Payment,
    PaymentStatus,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)
from app.models.user import User, UserRole

WEBHOOK_SECRET = "whsec_test_secret"
WEBHOOK_PATH = "/api/v1/premium/webhook/youpi"
UTR = "123456789012"


@pytest.fixture
def youpi_settings(monkeypatch):
    """Deterministic webhook secret so tests can sign payloads themselves."""
    monkeypatch.setattr(settings, "YOUPI_WEBHOOK_SECRET", SecretStr(WEBHOOK_SECRET))


async def _auth_headers(client, email, username):
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
            "full_name": "Webhook Tester",
            "username": username,
        },
    )
    token = register.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _make_plan(db_session, slug):
    plan = SubscriptionPlan(
        slug=slug,
        name="Premium Test",
        description="test plan",
        price_amount=499,
        price_currency="INR",
        features=[],
        permissions=[],
        is_active=True,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return plan


async def _seed_pending_payment(db_session, *, user_id, order_id, plan, amount=499):
    payment = Payment(
        user_id=user_id,
        payment_intent_id=order_id,
        status=PaymentStatus.PENDING,
        amount=amount,
        currency="INR",
        payment_method="upi",
        provider="youpi",
        description="CyberVerse Premium Test Plan",
        meta_data={"plan_id": str(plan.id), "plan_tier": "monthly"},
    )
    db_session.add(payment)
    await db_session.commit()
    return payment


def _reconciled_body(*, order_id, delivery_id, amount, amount_paise):
    payload = {
        "event": "RECONCILED",
        "settlementState": "RECONCILED",
        "method": "UPI",
        "orderId": order_id,
        "amount": amount,
        "amountPaise": amount_paise,
        "utr": UTR,
        "paymentId": "pay_test_0001",
        "deliveryId": delivery_id,
    }
    return json.dumps(payload).encode("utf-8")


def _signed_headers(body: bytes) -> dict:
    sig = "sha256=" + hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return {"Content-Type": "application/json", "X-Gateway-Signature": sig}


async def _get_user(db_session, email):
    result = await db_session.execute(select(User).where(User.email == email))
    return result.scalar_one()


async def _get_payment(db_session, order_id):
    result = await db_session.execute(
        select(Payment).where(Payment.payment_intent_id == order_id)
    )
    return result.scalar_one()


async def _subscriptions_for(db_session, user_id):
    result = await db_session.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    return list(result.scalars().all())


async def test_reconciled_webhook_fulfills_subscription_and_deduplicates_replay(
    client, db_session, youpi_settings
):
    email = "wh_fulfill@test.io"
    await _auth_headers(client, email, "wh_fulfill_test")
    user = await _get_user(db_session, email)
    plan = await _make_plan(db_session, "premium-wh-fulfill")
    order_id = "CV-WH-FULFILL-0001"
    delivery_id = "dlv-wh-fulfill-0001"
    await _seed_pending_payment(
        db_session, user_id=user.id, order_id=order_id, plan=plan
    )

    body = _reconciled_body(
        order_id=order_id, delivery_id=delivery_id, amount="499.00", amount_paise=49900
    )
    res = await client.post(WEBHOOK_PATH, content=body, headers=_signed_headers(body))
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["status"] == "ok"
    assert data["premium_activated"] is True

    # Pending payment is now COMPLETED with the delivery/UTR recorded.
    payment = await _get_payment(db_session, order_id)
    assert payment.status == PaymentStatus.COMPLETED
    assert payment.payment_method == "upi"
    assert payment.provider == "youpi"
    assert payment.paid_at is not None
    assert payment.meta_data["youpi_delivery_id"] == delivery_id
    assert payment.meta_data["youpi_utr"] == UTR

    # Exactly one ACTIVE subscription with a ~30d monthly period, linked back
    # to the payment.
    subscriptions = await _subscriptions_for(db_session, user.id)
    assert len(subscriptions) == 1
    subscription = subscriptions[0]
    assert subscription.status == SubscriptionStatus.ACTIVE
    assert subscription.plan_id == plan.id
    assert payment.subscription_id == subscription.id
    period = subscription.current_period_end - subscription.current_period_start
    assert timedelta(days=29) <= period <= timedelta(days=31)

    # User was promoted to premium_student.
    await db_session.refresh(user)
    assert user.role == UserRole.PREMIUM_STUDENT

    # Replay of the same delivery id is acknowledged but never fulfilled twice.
    replay = await client.post(WEBHOOK_PATH, content=body, headers=_signed_headers(body))
    assert replay.status_code == 200, replay.text
    replay_data = replay.json()["data"]
    assert replay_data["status"] == "ok"
    assert replay_data["deduplicated"] is True
    assert len(await _subscriptions_for(db_session, user.id)) == 1


async def test_reconciled_webhook_amount_mismatch_is_rejected(
    client, db_session, youpi_settings
):
    email = "wh_mismatch@test.io"
    await _auth_headers(client, email, "wh_mismatch_test")
    user = await _get_user(db_session, email)
    plan = await _make_plan(db_session, "premium-wh-mismatch")
    order_id = "CV-WH-MISMATCH-0001"
    delivery_id = "dlv-wh-mismatch-0001"
    await _seed_pending_payment(
        db_session, user_id=user.id, order_id=order_id, plan=plan
    )

    # Gateway reports ₹1 against a ₹499 order → rejected, nothing fulfilled.
    body = _reconciled_body(
        order_id=order_id, delivery_id=delivery_id, amount="1.00", amount_paise=100
    )
    res = await client.post(WEBHOOK_PATH, content=body, headers=_signed_headers(body))
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["status"] == "rejected"
    assert data["reason"] == "amount_mismatch"

    payment = await _get_payment(db_session, order_id)
    assert payment.status == PaymentStatus.PENDING
    assert payment.paid_at is None
    assert "youpi_delivery_id" not in (payment.meta_data or {})

    assert await _subscriptions_for(db_session, user.id) == []

    await db_session.refresh(user)
    assert user.role == UserRole.STUDENT
