"""
Clerk authentication integration.

Clerk is the primary authentication authority for CyberVerse: it signs users
in/out and issues short-lived RS256 **session tokens** (JWTs signed by the
instance). This module verifies those tokens statelessly against the instance
JWKS and can fetch user details from the Clerk Backend API for syncing a local
``users`` row.

Postgres remains the *record* authority (roles, progress, XP …); Clerk is the
*identity* authority. A local user is keyed by ``users.provider_id`` which holds
the Clerk user id (``user_…``).
"""

from __future__ import annotations

import asyncio
import base64
import time
from typing import Any

import httpx
from jose import JWTError, jwt

from app.core.config import settings

# Clerk session tokens are RS256-signed by the instance's JWKS.
_CLERK_ALGORITHM = "RS256"
_JWKS_URL_PATH = "/.well-known/jwks.json"
_CLERK_API_BASE = "https://api.clerk.com/v1"
_JWKS_CACHE_TTL_SECONDS = 3600
_JWKS_FETCH_TIMEOUT_SECONDS = 5.0

# In-process JWKS cache: kid -> JWK dict, plus a fetch timestamp + lock so
# concurrent requests don't stampede the JWKS endpoint on a cold cache.
_jwks_cache: dict[str, dict[str, Any]] = {}
_jwks_fetched_at: float = 0.0
_jwks_lock = asyncio.Lock()


class ClerkError(Exception):
    """Raised when Clerk configuration, token verification, or API calls fail."""


def clerk_frontend_api() -> str:
    """Derive the instance frontend-API origin from the publishable key.

    The publishable key is ``pk_test_<base64(domain)>`` or ``pk_live_<base64>``.
    Decoding the payload yields the instance domain (e.g.
    ``suited-verdict-3663.clerk.accounts.dev``).
    """
    pk = settings.CLERK_PUBLISHABLE_KEY
    if not pk:
        raise ClerkError("CLERK_PUBLISHABLE_KEY is not configured")
    parts = pk.split("_", 2)
    if len(parts) < 3 or not parts[2]:
        raise ClerkError("CLERK_PUBLISHABLE_KEY is malformed")
    payload = parts[2]
    payload += "=" * (-len(payload) % 4)  # restore base64 padding
    try:
        domain = base64.b64decode(payload).decode("utf-8")
    except Exception as exc:  # noqa: BLE001 — malformed key
        raise ClerkError("CLERK_PUBLISHABLE_KEY payload is not valid base64") from exc
    if not domain:
        raise ClerkError("CLERK_PUBLISHABLE_KEY decoded to an empty domain")
    return f"https://{domain}"


async def _fetch_jwks(force: bool = False) -> None:
    """Fetch and cache the instance JWKS."""
    global _jwks_fetched_at
    if not force and _jwks_cache and (time.monotonic() - _jwks_fetched_at) < _JWKS_CACHE_TTL_SECONDS:
        return
    url = f"{clerk_frontend_api()}{_JWKS_URL_PATH}"
    try:
        async with httpx.AsyncClient(timeout=_JWKS_FETCH_TIMEOUT_SECONDS) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        # Surface as ClerkError so callers (auth deps) map it to 401/503
        # instead of leaking a 500 on a JWKS outage or DNS failure.
        raise ClerkError(f"Unable to fetch Clerk JWKS: {exc}") from exc
    keys = data.get("keys", [])
    _jwks_cache.clear()
    for jwk in keys:
        kid = jwk.get("kid")
        if kid:
            _jwks_cache[kid] = jwk
    _jwks_fetched_at = time.monotonic()


async def _get_signing_jwk(kid: str | None) -> dict[str, Any]:
    """Return the JWK for ``kid``, refreshing the cache on a miss."""
    if not kid:
        raise ClerkError("Clerk token missing 'kid' header")
    # Serve from cache when fresh; otherwise refresh.
    if (time.monotonic() - _jwks_fetched_at) >= _JWKS_CACHE_TTL_SECONDS or kid not in _jwks_cache:
        async with _jwks_lock:
            # Double-check inside the lock to avoid a redundant refresh.
            if (time.monotonic() - _jwks_fetched_at) >= _JWKS_CACHE_TTL_SECONDS or kid not in _jwks_cache:
                await _fetch_jwks(force=kid not in _jwks_cache and bool(_jwks_cache))
    jwk = _jwks_cache.get(kid)
    if not jwk:
        raise ClerkError(f"No signing key for token kid {kid!r}")
    return jwk


async def verify_clerk_session_token(token: str) -> dict[str, Any]:
    """Verify a Clerk session token and return its claims.

    Validates the RS256 signature against the instance JWKS, the issuer, and
    the expiry. Returns the decoded payload (``sub`` is the Clerk user id).

    Raises:
        ClerkError: If the token is invalid, expired, or unverifiable.
    """
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise ClerkError("Malformed Clerk token") from exc
    if header.get("alg") != _CLERK_ALGORITHM:
        raise ClerkError(f"Unexpected Clerk token algorithm {header.get('alg')!r}")

    jwk = await _get_signing_jwk(header.get("kid"))
    frontend_api = clerk_frontend_api()
    try:
        payload = jwt.decode(
            token,
            jwk,
            algorithms=[_CLERK_ALGORITHM],
            issuer=frontend_api,
            options={"verify_aud": False},  # session tokens have no meaningful aud
        )
    except JWTError as exc:
        # A key-rotation race can surface as an unknown kid → force one refresh + retry once.
        if "kid" in str(exc).lower():
            async with _jwks_lock:
                await _fetch_jwks(force=True)
            jwk = _jwks_cache.get(header.get("kid", ""))
            if not jwk:
                raise ClerkError("Clerk token key not found after refresh") from exc
            try:
                payload = jwt.decode(
                    token,
                    jwk,
                    algorithms=[_CLERK_ALGORITHM],
                    issuer=frontend_api,
                    options={"verify_aud": False},
                )
            except JWTError as retry_exc:
                raise ClerkError(f"Invalid Clerk token: {retry_exc}") from retry_exc
        else:
            raise ClerkError(f"Invalid Clerk token: {exc}") from exc

    if not payload.get("sub"):
        raise ClerkError("Clerk token missing 'sub' claim")
    return payload


async def get_clerk_user(clerk_user_id: str) -> dict[str, Any]:
    """Fetch a user record from the Clerk Backend API.

    Returns the raw Clerk user object. Used to populate the local ``users`` row
    on first sight (lazy sync) or via webhook.

    Raises:
        ClerkError: If the secret key is missing or the API call fails.
    """
    secret = settings.CLERK_SECRET_KEY
    if not secret:
        raise ClerkError("CLERK_SECRET_KEY is not configured")
    url = f"{_CLERK_API_BASE}/users/{clerk_user_id}"
    async with httpx.AsyncClient(timeout=_JWKS_FETCH_TIMEOUT_SECONDS) as client:
        resp = await client.get(
            url,
            headers={"Authorization": f"Bearer {secret.get_secret_value()}"},
        )
        if resp.status_code != 200:
            raise ClerkError(f"Clerk Backend API returned {resp.status_code} for user {clerk_user_id}")
        return resp.json()


def primary_email(clerk_user: dict[str, Any]) -> str | None:
    """Extract the primary (verified) email address from a Clerk user object."""
    email_addresses = clerk_user.get("email_addresses") or []
    primary_id = clerk_user.get("primary_email_address_id")
    for addr in email_addresses:
        if primary_id and addr.get("id") == primary_id:
            return (addr.get("email_address") or "").lower() or None
    # Fallback: first address
    if email_addresses:
        return (email_addresses[0].get("email_address") or "").lower() or None
    return None


def email_verified(clerk_user: dict[str, Any]) -> bool:
    """Whether the primary email is verified per Clerk."""
    email_addresses = clerk_user.get("email_addresses") or []
    primary_id = clerk_user.get("primary_email_address_id")
    for addr in email_addresses:
        if primary_id and addr.get("id") == primary_id:
            verification = addr.get("verification") or {}
            return verification.get("status") == "verified"
    return False
