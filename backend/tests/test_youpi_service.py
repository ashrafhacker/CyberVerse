"""Unit tests for the YouPI PG client and webhook helpers."""

from __future__ import annotations

import hashlib
import hmac

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import settings
from app.services import youpi_service


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        ("99", "99.00"),
        ("99.5", "99.50"),
        (99, "99.00"),
        ("0.01", "0.01"),
    ],
)
def test_format_amount(amount, expected):
    """Format rupee amounts as two-decimal strings."""
    assert youpi_service.format_amount(amount) == expected


def test_verify_webhook_signature_accepts_prefixed_and_bare_hex(monkeypatch):
    """Accept both YouPI signature header encodings."""
    monkeypatch.setattr(settings, "YOUPI_WEBHOOK_SECRET", SecretStr("whsec_test"))
    body = b'{"event":"RECONCILED"}'
    signature = hmac.new(b"whsec_test", body, hashlib.sha256).hexdigest()

    assert youpi_service.verify_webhook_signature(body, f"sha256={signature}")
    assert youpi_service.verify_webhook_signature(body, signature)


def test_verify_webhook_signature_rejects_bad_or_missing_values(monkeypatch):
    """Reject invalid signatures and an unconfigured secret."""
    monkeypatch.setattr(settings, "YOUPI_WEBHOOK_SECRET", SecretStr("whsec_test"))
    body = b"{}"

    assert not youpi_service.verify_webhook_signature(body, None)
    assert not youpi_service.verify_webhook_signature(body, "sha256=deadbeef")
    monkeypatch.setattr(settings, "YOUPI_WEBHOOK_SECRET", None)
    assert not youpi_service.verify_webhook_signature(body, "sha256=deadbeef")


def test_is_configured_requires_a_webhook_secret(monkeypatch):
    """Report configured only when the webhook secret is present."""
    monkeypatch.setattr(settings, "YOUPI_WEBHOOK_SECRET", None)
    assert not youpi_service.is_configured()
    monkeypatch.setattr(settings, "YOUPI_WEBHOOK_SECRET", SecretStr("whsec_test"))
    assert youpi_service.is_configured()


class _FakeAsyncClient:
    last_request: dict | None = None

    def __init__(self, **kwargs):
        self.base_url = kwargs.get("base_url")
        self.timeout = kwargs.get("timeout")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, *, json, headers):
        type(self).last_request = {"url": url, "json": json, "headers": headers}
        return httpx.Response(
            201,
            json={"paymentId": "pay_123", "checkoutUrl": "https://pay.example/checkout"},
            request=httpx.Request("POST", "http://youpi.test"),
        )


@pytest.mark.asyncio
async def test_create_payment_posts_expected_payload(monkeypatch):
    """Send the YouPI order payload and return its checkout URL."""
    monkeypatch.setattr(settings, "YOUPI_MERCHANT_ID", "merchant-1")
    monkeypatch.setattr(settings, "YOUPI_WEBHOOK_SECRET", SecretStr("whsec_test"))
    monkeypatch.setattr(settings, "YOUPI_CURRENCY", "INR")
    monkeypatch.setattr(youpi_service.httpx, "AsyncClient", _FakeAsyncClient)

    result = await youpi_service.create_payment(
        order_id="order-1",
        amount="99",
        description="CyberVerse Plan",
        customer_name="Test User",
        customer_email="test@example.com",
        return_url="https://app.example/dashboard",
        metadata={"payment_id": "order-1"},
    )

    assert result["paymentId"] == "pay_123"
    assert result["checkoutUrl"] == "https://pay.example/checkout"
    request = _FakeAsyncClient.last_request
    assert request["url"] == "/api/v1/payments"
    assert request["json"]["amount"] == "99.00"
    assert request["json"]["orderId"] == "order-1"
    assert request["json"]["customer"] == {"name": "Test User", "email": "test@example.com"}
    assert request["headers"]["X-Merchant-Id"] == "merchant-1"
    assert request["headers"]["X-Merchant-Key"] == "whsec_test"
    assert request["headers"]["Idempotency-Key"] == "order-1"
