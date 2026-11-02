#!/usr/bin/env python3
"""
Provision the CyberVerse merchant account on a running YouPI PG instance.

YouPI stores the receiving UPI VPA and webhook target on the merchant account,
not on individual payments. Run this once after starting YouPI and whenever the
UPI ID, webhook URL, or webhook secret changes::

    cd backend
    python scripts/configure_youpi.py

Required environment (see .env.example):
    YOUPI_API_URL, YOUPI_MERCHANT_ID, YOUPI_UPI_ID,
    YOUPI_WEBHOOK_URL, YOUPI_WEBHOOK_SECRET, YOUPI_ADMIN_TOKEN
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import NoReturn
from urllib.parse import urlparse

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings

LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def _secret(value: object) -> str:
    if value is None:
        return ""
    getter = getattr(value, "get_secret_value", None)
    return getter() if callable(getter) else str(value)


def _fail(message: str) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def _validate(args: argparse.Namespace, admin_token: str, webhook_secret: str) -> None:
    """Reject incomplete configuration and warn about loopback webhooks."""
    if not admin_token:
        _fail("YOUPI_ADMIN_TOKEN is not set (must match YouPI's ADMIN_API_TOKEN)")
    if not webhook_secret:
        _fail("YOUPI_WEBHOOK_SECRET is not set")
    if not args.api_url:
        _fail("YOUPI_API_URL is not set")
    if not args.merchant_id:
        _fail("YOUPI_MERCHANT_ID is not set")
    if not args.upi_id:
        _fail("YOUPI_UPI_ID is not set")
    if not args.webhook_url:
        _fail("YOUPI_WEBHOOK_URL is not set")

    host = (urlparse(args.webhook_url).hostname or "").lower()
    if host in LOOPBACK_HOSTS:
        print(
            "warning: webhook URL points to loopback. Start YouPI with "
            "YOUPI_ALLOW_PRIVATE_WEBHOOKS=true or deliveries will be SSRF-blocked.",
            file=sys.stderr,
        )


def main() -> None:
    """Push merchant settings to YouPI and verify the readback."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default=settings.YOUPI_API_URL)
    parser.add_argument("--merchant-id", default=settings.YOUPI_MERCHANT_ID)
    parser.add_argument("--upi-id", default=settings.YOUPI_UPI_ID)
    parser.add_argument("--payee-name", default="CyberVerse")
    parser.add_argument("--webhook-url", default=settings.YOUPI_WEBHOOK_URL)
    parser.add_argument("--admin-token", default=None)
    args = parser.parse_args()

    admin_token = args.admin_token or _secret(settings.YOUPI_ADMIN_TOKEN)
    webhook_secret = _secret(settings.YOUPI_WEBHOOK_SECRET)

    _validate(args, admin_token, webhook_secret)

    payload = {
        "merchantId": args.merchant_id,
        "upiId": args.upi_id,
        "payeeName": args.payee_name,
        "webhookUrl": args.webhook_url,
        "webhookSecret": webhook_secret,
    }
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        with httpx.Client(
            base_url=args.api_url.rstrip("/"),
            timeout=settings.YOUPI_TIMEOUT_SECONDS,
        ) as client:
            response = client.post("/api/v1/admin/all-settings", json=payload, headers=headers)
            if response.is_error:
                _fail(f"YouPI returned {response.status_code}: {response.text[:500]}")

            current = client.get(
                "/api/v1/admin/all-settings",
                params={"merchantId": args.merchant_id},
                headers=headers,
            )
    except httpx.HTTPError as exc:
        _fail(f"could not reach YouPI at {args.api_url}: {exc}")

    if current.is_error:
        _fail(f"YouPI settings readback returned {current.status_code}: {current.text[:500]}")

    saved = current.json()
    print("YouPI merchant configured:")
    print(f"  merchant_id: {saved.get('merchantId', args.merchant_id)}")
    print(f"  upi_id:      {saved.get('upiId', '')}")
    print(f"  payee_name:  {saved.get('payeeName', '')}")
    print(f"  webhook_url: {saved.get('webhookUrl', '')}")

    if saved.get("upiId") != args.upi_id:
        _fail("readback upiId does not match the requested value")
    if saved.get("webhookUrl") != args.webhook_url:
        _fail("readback webhookUrl does not match the requested value")


if __name__ == "__main__":
    main()
