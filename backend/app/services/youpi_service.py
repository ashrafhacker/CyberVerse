"""
YouPI PG client and webhook helpers.

YouPI is a self-hosted UPI payment gateway. The merchant UPI VPA is configured
on the gateway's receiving account (see ``scripts/configure_youpi.py``); it is
not sent per payment.
"""

from __future__ import annotations

import hashlib
import hmac
from decimal import Decimal

import httpx

from app.core.config import settings


class YoupiGatewayError(RuntimeError):
    """Raised when the YouPI gateway cannot create a payment."""

    def __init__(self, message: str, *, status_code: int = 502, body: str | None = None):
        """Store the HTTP status and bounded response body for API mapping."""
        super().__init__(message)
        self.status_code = status_code
        self.body = body


def is_configured() -> bool:
    """Return True when checkout and webhook verification can be used."""
    return bool(
        settings.YOUPI_API_URL
        and settings.YOUPI_MERCHANT_ID
        and settings.YOUPI_WEBHOOK_SECRET
    )


def _headers(idempotency_key: str) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Merchant-Id": settings.YOUPI_MERCHANT_ID,
        "Idempotency-Key": idempotency_key,
    }
    if settings.YOUPI_WEBHOOK_SECRET:
        headers["X-Merchant-Key"] = settings.YOUPI_WEBHOOK_SECRET.get_secret_value()
    return headers


def format_amount(amount: Decimal | float | str) -> str:
    """Format an INR amount with exactly two decimal places."""
    return str(Decimal(str(amount)).quantize(Decimal("0.01")))


async def create_payment(  # noqa: PLR0913
    *,
    order_id: str,
    amount: Decimal | float | str,
    description: str,
    customer_name: str | None,
    customer_email: str | None,
    return_url: str,
    metadata: dict,
) -> dict:
    """
    Create a YouPI payment and return the gateway response.

    ``order_id`` doubles as the gateway order identifier. The caller must use a
    stable idempotency key so retries cannot create duplicate payments.
    """
    payload = {
        "orderId": order_id,
        "amount": format_amount(amount),
        "currency": settings.YOUPI_CURRENCY,
        "description": description,
        "returnUrl": return_url,
        "metadata": metadata,
    }
    customer = {}
    if customer_name:
        customer["name"] = customer_name
    if customer_email:
        customer["email"] = customer_email
    if customer:
        payload["customer"] = customer

    try:
        async with httpx.AsyncClient(
            base_url=settings.YOUPI_API_URL.rstrip("/"),
            timeout=settings.YOUPI_TIMEOUT_SECONDS,
        ) as client:
            response = await client.post(
                "/api/v1/payments",
                json=payload,
                headers=_headers(order_id),
            )
    except httpx.HTTPError as exc:
        message = f"Could not reach YouPI PG: {exc}"
        raise YoupiGatewayError(message) from exc

    if response.is_error:
        detail = response.text[:500]
        message = f"YouPI PG rejected the payment ({response.status_code})"
        raise YoupiGatewayError(message, status_code=502, body=detail)

    try:
        data = response.json()
    except ValueError as exc:
        message = "YouPI PG returned an invalid JSON response"
        raise YoupiGatewayError(message) from exc

    if not data.get("checkoutUrl") or not data.get("paymentId"):
        message = "YouPI PG response is missing checkoutUrl/paymentId"
        raise YoupiGatewayError(message)

    return data


def verify_webhook_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Verify ``X-Gateway-Signature: sha256=<hex>`` against the raw body."""
    if not signature_header or not settings.YOUPI_WEBHOOK_SECRET:
        return False

    signature = signature_header.strip()
    if signature.startswith("sha256="):
        signature = signature[len("sha256=") :]

    expected = hmac.new(
        settings.YOUPI_WEBHOOK_SECRET.get_secret_value().encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
