"""YouPI-PG webhook *negative* (fail-closed) path coverage.

The companion suite (``test_youpi_webhook_fulfillment.py``) proves the happy
path: a correctly signed ``event=RECONCILED`` UPI payload activates premium
and replays are deduplicated. These tests pin everything *before* that point
so a misconfigured gateway, a forged payload, or a lazy retry can never
activate premium:

* signature enforcement — missing, wrong-secret and V2-mismatch deliveries
  are rejected with 401 before any handler logic runs;
* malformed bodies — undecodable JSON or a non-object payload → 400;
* non-reconciled events (``OBSERVED_SUCCESS``, non-UPI methods, other
  settlement states) are acknowledged-but-ignored, never fulfilled;
* missing delivery id / order id / UTR or an unknown order → rejected, the
  pending payment is left untouched;
* a second delivery id for an already-completed order is deduplicated,
  never double-fulfilled.
"""

import hashlib
import hmac
import json

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

WEBHOOK_SECRET = "whsec_test_negative_secret"
WEBHOOK_PATH = "/api/v1/premium/webhook/youpi"
UTR = "987654321012"


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


def _reconciled_body(*, order_id, delivery_id, amount="499.00", amount_paise=49900,
                     utr=UTR, event="RECONCILED", settlement_state="RECONCILED",
                     method="UPI"):
    payload = {
        "event": event,
        "settlementState": settlement_state,
        "method": method,
        "orderId": order_id,
        "amount": amount,
        "amountPaise": amount_paise,
        "utr": utr,
        "paymentId": "pay_test_neg_0001",
        "deliveryId": delivery_id,
    }
    return json.dumps(payload).encode("utf-8")


def _signed_headers(body: bytes) -> dict:
    sig = "sha256=" + hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return {"Content-Type": "application/json", "X-Gateway-Signature": sig}


def _signed_headers_v2(body: bytes, timestamp: str) -> dict:
    headers = _signed_headers(body)
    signed_payload = timestamp.encode("utf-8") + b"." + body
    sig_v2 = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), signed_payload, hashlib.sha256
    ).hexdigest()
    headers["X-Gateway-Signature-V2"] = sig_v2
    headers["X-Gateway-Timestamp"] = timestamp
    return headers


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


async def _get_user(db_session, email):
    result = await db_session.execute(select(User).where(User.email == email))
    return result.scalar_one()


async def test_missing_signature_is_401(client, db_session, youpi_settings):
    body = _reconciled_body(order_id="CV-WH-NEG-0001", delivery_id="dlv-neg-0001")
    res = await client.post(
        WEBHOOK_PATH,
        content=body,
        headers={"Content-Type": "application/json"},  # no X-Gateway-Signature
    )
    assert res.status_code == 401


async def test_wrong_secret_signature_is_401_and_creates_nothing(
    client, db_session, youpi_settings
):
    email = "wh_neg_wrongsig@test.io"
    await _auth_headers(client, email, "wh_neg_wrongsig")
    user = await _get_user(db_session, email)
    plan = await _make_plan(db_session, "premium-wh-neg-wrongsig")
    await _seed_pending_payment(db_session, user_id=user.id,
                                order_id="CV-WH-NEG-0002", plan=plan)

    body = _reconciled_body(order_id="CV-WH-NEG-0002", delivery_id="dlv-neg-0002")
    forged = "sha256=" + hmac.new(b"some-other-secret", body, hashlib.sha256).hexdigest()
    res = await client.post(
        WEBHOOK_PATH,
        content=body,
        headers={"Content-Type": "application/json", "X-Gateway-Signature": forged},
    )
    assert res.status_code == 401

    payment = await _get_payment(db_session, "CV-WH-NEG-0002")
    assert payment.status == PaymentStatus.PENDING
    assert await _subscriptions_for(db_session, user.id) == []


async def test_v2_signature_mismatch_is_401(client, db_session, youpi_settings):
    body = _reconciled_body(order_id="CV-WH-NEG-0003", delivery_id="dlv-neg-0003")
    headers = _signed_headers(body)
    headers["X-Gateway-Signature-V2"] = (
        "sha256=" + hmac.new(b"not-the-secret", body, hashlib.sha256).hexdigest()
    )
    headers["X-Gateway-Timestamp"] = "1700000000"
    res = await client.post(WEBHOOK_PATH, content=body, headers=headers)
    assert res.status_code == 401


async def test_valid_v2_signature_is_accepted_and_ignored_event_not_fulfilled(
    client, db_session, youpi_settings
):
    """V1+V2 correct → passes the signature gate; non-RECONCILED event is ignored."""
    email = "wh_neg_v2@test.io"
    await _auth_headers(client, email, "wh_neg_v2")
    user = await _get_user(db_session, email)
    plan = await _make_plan(db_session, "premium-wh-neg-v2")
    await _seed_pending_payment(db_session, user_id=user.id,
                                order_id="CV-WH-NEG-0004", plan=plan)

    body = _reconciled_body(
        order_id="CV-WH-NEG-0004", delivery_id="dlv-neg-0004", event="OBSERVED_SUCCESS"
    )
    res = await client.post(WEBHOOK_PATH, content=body,
                            headers=_signed_headers_v2(body, "1700000000"))
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "ignored"

    payment = await _get_payment(db_session, "CV-WH-NEG-0004")
    assert payment.status == PaymentStatus.PENDING
    assert await _subscriptions_for(db_session, user.id) == []


async def test_malformed_json_is_400(client, db_session, youpi_settings):
    body = b"{not-json"
    res = await client.post(WEBHOOK_PATH, content=body, headers=_signed_headers(body))
    assert res.status_code == 400


async def test_non_dict_json_is_400(client, db_session, youpi_settings):
    body = b"[1, 2, 3]"
    res = await client.post(WEBHOOK_PATH, content=body, headers=_signed_headers(body))
    assert res.status_code == 400


async def test_observed_success_is_ignored_never_fulfilled(
    client, db_session, youpi_settings
):
    email = "wh_neg_obs@test.io"
    await _auth_headers(client, email, "wh_neg_obs")
    user = await _get_user(db_session, email)
    plan = await _make_plan(db_session, "premium-wh-neg-obs")
    await _seed_pending_payment(db_session, user_id=user.id,
                                order_id="CV-WH-NEG-0005", plan=plan)

    body = _reconciled_body(
        order_id="CV-WH-NEG-0005", delivery_id="dlv-neg-0005",
        event="OBSERVED_SUCCESS", settlement_state="OBSERVED_SUCCESS",
    )
    res = await client.post(WEBHOOK_PATH, content=body, headers=_signed_headers(body))
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "ignored"

    payment = await _get_payment(db_session, "CV-WH-NEG-0005")
    assert payment.status == PaymentStatus.PENDING
    assert payment.paid_at is None
    assert await _subscriptions_for(db_session, user.id) == []


async def test_non_upi_method_is_ignored(
    client, db_session, youpi_settings
):
    email = "wh_neg_card@test.io"
    await _auth_headers(client, email, "wh_neg_card")
    user = await _get_user(db_session, email)
    plan = await _make_plan(db_session, "premium-wh-neg-card")
    await _seed_pending_payment(db_session, user_id=user.id,
                                order_id="CV-WH-NEG-0006", plan=plan)

    body = _reconciled_body(
        order_id="CV-WH-NEG-0006", delivery_id="dlv-neg-0006", method="CARD",
    )
    res = await client.post(WEBHOOK_PATH, content=body, headers=_signed_headers(body))
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "ignored"

    payment = await _get_payment(db_session, "CV-WH-NEG-0006")
    assert payment.status == PaymentStatus.PENDING
    assert await _subscriptions_for(db_session, user.id) == []


async def test_missing_delivery_id_is_rejected(client, db_session, youpi_settings):
    email = "wh_neg_nodeliv@test.io"
    await _auth_headers(client, email, "wh_neg_nodeliv")
    user = await _get_user(db_session, email)
    plan = await _make_plan(db_session, "premium-wh-neg-nodeliv")
    await _seed_pending_payment(db_session, user_id=user.id,
                                order_id="CV-WH-NEG-0007", plan=plan)

    body = _reconciled_body(order_id="CV-WH-NEG-0007", delivery_id="")
    res = await client.post(WEBHOOK_PATH, content=body, headers=_signed_headers(body))
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "rejected"
    assert res.json()["data"]["reason"] == "missing_delivery_id"

    payment = await _get_payment(db_session, "CV-WH-NEG-0007")
    assert payment.status == PaymentStatus.PENDING


async def test_missing_order_id_is_rejected(client, db_session, youpi_settings):
    body = _reconciled_body(order_id="", delivery_id="dlv-neg-0008")
    res = await client.post(WEBHOOK_PATH, content=body, headers=_signed_headers(body))
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "rejected"
    assert res.json()["data"]["reason"] == "missing_order_id"


async def test_invalid_utr_is_rejected(client, db_session, youpi_settings):
    email = "wh_neg_utr@test.io"
    await _auth_headers(client, email, "wh_neg_utr")
    user = await _get_user(db_session, email)
    plan = await _make_plan(db_session, "premium-wh-neg-utr")
    await _seed_pending_payment(db_session, user_id=user.id,
                                order_id="CV-WH-NEG-0009", plan=plan)

    # 11 digits — fails the handler's re.fullmatch(r"\d{12}", utr) gate.
    body = _reconciled_body(order_id="CV-WH-NEG-0009", delivery_id="dlv-neg-0009",
                            utr="12345678901")
    res = await client.post(WEBHOOK_PATH, content=body, headers=_signed_headers(body))
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "rejected"
    assert res.json()["data"]["reason"] == "invalid_utr"

    payment = await _get_payment(db_session, "CV-WH-NEG-0009")
    assert payment.status == PaymentStatus.PENDING
    assert payment.paid_at is None


async def test_unknown_order_is_rejected(client, db_session, youpi_settings):
    body = _reconciled_body(order_id="CV-WH-NEG-UNKNOWN", delivery_id="dlv-neg-0010")
    res = await client.post(WEBHOOK_PATH, content=body, headers=_signed_headers(body))
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "rejected"
    assert res.json()["data"]["reason"] == "unknown_order"


async def test_second_delivery_id_for_completed_order_is_deduplicated(
    client, db_session, youpi_settings
):
    email = "wh_neg_dup@test.io"
    await _auth_headers(client, email, "wh_neg_dup")
    user = await _get_user(db_session, email)
    plan = await _make_plan(db_session, "premium-wh-neg-dup")
    await _seed_pending_payment(db_session, user_id=user.id,
                                order_id="CV-WH-NEG-0011", plan=plan)

    # First delivery fulfills.
    first = _reconciled_body(order_id="CV-WH-NEG-0011", delivery_id="dlv-neg-0011")
    res = await client.post(WEBHOOK_PATH, content=first, headers=_signed_headers(first))
    assert res.status_code == 200, res.text
    assert res.json()["data"]["premium_activated"] is True

    # A *different* delivery id for the same already-completed order is
    # acknowledged as a duplicate, never fulfilled again.
    replay = _reconciled_body(order_id="CV-WH-NEG-0011", delivery_id="dlv-neg-0011b")
    res = await client.post(WEBHOOK_PATH, content=replay, headers=_signed_headers(replay))
    assert res.status_code == 200, res.text
    body = res.json()["data"]
    assert body["status"] == "ok"
    assert body["deduplicated"] is True

    subscriptions = await _subscriptions_for(db_session, user.id)
    assert len(subscriptions) == 1
    assert subscriptions[0].status == SubscriptionStatus.ACTIVE
