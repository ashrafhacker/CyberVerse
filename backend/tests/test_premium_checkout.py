"""YouPI-PG checkout: server-side gateway session creation (fail-closed).

Regression tests for the enroll fix: the browser SDK refuses to open a modal
unless the payment was created server-side with trusted order data. So
``/premium/checkout`` must create the gateway session BEFORE consuming the
coupon or writing a pending Payment row, and must fail closed
(``youpi_enabled=False`` + ``gateway_code``) whenever the gateway refuses —
including the ``OBSERVERS_UNHEALTHY`` and unreachable cases.
"""

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import select

from app.core.config import settings
from app.models.premium import Coupon, Payment, SubscriptionPlan

MERCHANT_ID = "00000000-0000-0000-0000-000000000001"


async def _auth_headers(client, email, username):
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
            "full_name": "Checkout Tester",
            "username": username,
        },
    )
    token = register.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def youpi_settings(monkeypatch):
    """Staging-shaped YouPI config: everything present, merchant key = webhook secret."""
    monkeypatch.setattr(settings, "YOUPI_API_DOMAIN", "https://pay.example")
    monkeypatch.setattr(settings, "YOUPI_MERCHANT_PUBLIC_KEY", "pk_test_example")
    monkeypatch.setattr(settings, "YOUPI_MERCHANT_ID", MERCHANT_ID)
    monkeypatch.setattr(settings, "YOUPI_MERCHANT_API_KEY", None)
    monkeypatch.setattr(settings, "YOUPI_WEBHOOK_SECRET", SecretStr("whsec_test_secret"))
    monkeypatch.setattr(settings, "YOUPI_CURRENCY", "INR")


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


async def _make_coupon(db_session, code, value):
    coupon = Coupon(
        code=code,
        discount_type="fixed",
        discount_value=value,
        used_count=0,
        is_active=True,
    )
    db_session.add(coupon)
    await db_session.commit()
    await db_session.refresh(coupon)
    return coupon


async def test_checkout_creates_gateway_session(client, db_session, youpi_settings, monkeypatch):
    headers = await _auth_headers(client, "co1@test.io", "co1_test")
    plan = await _make_plan(db_session, "premium-co1")
    await _make_coupon(db_session, "SAVE10", 10)

    captured: dict = {}
    original_post = httpx.AsyncClient.post

    async def fake_post(self, url, *args, **kwargs):
        if not str(url).startswith("https://pay.example"):
            return await original_post(self, url, *args, **kwargs)
        captured["url"] = str(url)
        captured["headers"] = kwargs.get("headers") or {}
        captured["json"] = kwargs.get("json") or {}

        class _Resp:
            status_code = 201

            def json(self):
                return {
                    "paymentId": "pay_abc123",
                    "orderId": captured["json"].get("orderId"),
                    "checkoutUrl": "http://localhost:7000/checkout/pay_abc123",
                }

        return _Resp()

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    res = await client.post(
        "/api/v1/premium/checkout",
        json={"plan_id": str(plan.id), "coupon_code": "SAVE10"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()["data"]

    assert data["youpi_enabled"] is True
    assert data["payment_id"] == "pay_abc123"
    assert data["checkout_url"]
    assert data["order_id"].startswith("CV-")

    # Gateway request contract: portal proxy path + merchant auth headers.
    assert captured["url"] == "https://pay.example/api/v1/payments"
    assert captured["headers"]["X-Merchant-Id"] == MERCHANT_ID
    assert captured["headers"]["X-Merchant-Key"] == "whsec_test_secret"
    assert captured["json"]["amount"] == "489.00"  # 499 - 10 coupon
    assert captured["json"]["currency"] == "INR"

    # Pending Payment row persisted with the gateway payment id; coupon burned.
    payment = (
        await db_session.execute(
            select(Payment).where(Payment.payment_intent_id == data["order_id"])
        )
    ).scalar_one()
    assert payment.meta_data["youpi_payment_id"] == "pay_abc123"
    coupon = (
        await db_session.execute(select(Coupon).where(Coupon.code == "SAVE10"))
    ).scalar_one()
    assert coupon.used_count == 1


async def test_checkout_fails_closed_when_gateway_refuses(
    client, db_session, youpi_settings, monkeypatch
):
    headers = await _auth_headers(client, "co2@test.io", "co2_test")
    plan = await _make_plan(db_session, "premium-co2")
    await _make_coupon(db_session, "SAVE20", 10)

    original_post = httpx.AsyncClient.post

    async def fake_post(self, url, *args, **kwargs):
        if not str(url).startswith("https://pay.example"):
            return await original_post(self, url, *args, **kwargs)

        class _Resp:
            status_code = 503

            def json(self):
                return {"code": "OBSERVERS_UNHEALTHY", "error": "Observers not ready"}

        return _Resp()

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    res = await client.post(
        "/api/v1/premium/checkout",
        json={"plan_id": str(plan.id), "coupon_code": "SAVE20"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()["data"]

    assert data["youpi_enabled"] is False
    assert data["youpi_unavailable_reason"] == "session_creation_failed"
    assert data["gateway_code"] == "OBSERVERS_UNHEALTHY"

    # Fail-closed: no pending Payment row and the coupon was NOT consumed.
    payments = (await db_session.execute(select(Payment))).scalars().all()
    assert payments == []
    coupon = (
        await db_session.execute(select(Coupon).where(Coupon.code == "SAVE20"))
    ).scalar_one()
    assert coupon.used_count == 0


async def test_checkout_fails_closed_when_gateway_unreachable(
    client, db_session, youpi_settings, monkeypatch
):
    headers = await _auth_headers(client, "co3@test.io", "co3_test")
    plan = await _make_plan(db_session, "premium-co3")

    original_post = httpx.AsyncClient.post

    async def fake_post(self, url, *args, **kwargs):
        if not str(url).startswith("https://pay.example"):
            return await original_post(self, url, *args, **kwargs)
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    res = await client.post(
        "/api/v1/premium/checkout",
        json={"plan_id": str(plan.id)},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()["data"]

    assert data["youpi_enabled"] is False
    assert data["youpi_unavailable_reason"] == "session_creation_failed"
    assert data["gateway_code"] == "GATEWAY_UNREACHABLE"

    payments = (await db_session.execute(select(Payment))).scalars().all()
    assert payments == []


async def test_checkout_not_configured_without_merchant_id(
    client, db_session, youpi_settings, monkeypatch
):
    # Staging before YOUPI_MERCHANT_ID is set: must short-circuit as
    # not_configured rather than attempting a doomed gateway call.
    monkeypatch.setattr(settings, "YOUPI_MERCHANT_ID", None)
    headers = await _auth_headers(client, "co4@test.io", "co4_test")
    plan = await _make_plan(db_session, "premium-co4")

    res = await client.post(
        "/api/v1/premium/checkout",
        json={"plan_id": str(plan.id)},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()["data"]

    assert data["youpi_enabled"] is False
    assert data["youpi_unavailable_reason"] == "not_configured"

    payments = (await db_session.execute(select(Payment))).scalars().all()
    assert payments == []
