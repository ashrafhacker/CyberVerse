"""Clerk auth integration tests.

Covers the three security-critical pieces of the Clerk migration:
1. Publishable-key decoding + RS256 session-token verification (JWKS mocked).
2. Lazy local-user provisioning through /auth/me and sync_clerk_user
   (create + link-by-email paths).
3. The svix-signed Clerk webhook (signature verifier + full endpoint flow).

No real network calls: JWKS/Backend API are mocked; crypto is real
(cryptography keypair + python-jose signing).
"""

import base64
import hashlib
import hmac
import json
import time
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt as jose_jwt
from pydantic import SecretStr
from sqlalchemy import select
from unittest.mock import AsyncMock

from app.core.clerk import ClerkError, clerk_frontend_api, verify_clerk_session_token
from app.core.config import settings
from app.models.user import AuthProvider, Profile, User, UserRole, UserStatus
from app.services.clerk_sync import sync_clerk_user

# Test publishable key: pk_test_ + base64("example.clerk.accounts.dev")
_DOMAIN = "example.clerk.accounts.dev"
_PK = "pk_test_" + base64.urlsafe_b64encode(_DOMAIN.encode()).decode().rstrip("=")
_FRONTEND_API = f"https://{_DOMAIN}"


def _b64url_uint(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


@pytest.fixture(scope="module")
def rsa_keypair():
    """A real 2048-bit RSA key exported as a public JWK (what the JWKS serves)."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "use": "sig",
        "kid": "test-key-1",
        "alg": "RS256",
        "n": _b64url_uint(pub.n),
        "e": _b64url_uint(pub.e),
    }
    return private_key, jwk


def _clerk_clerk_user(
    clerk_id: str = "user_clerk_1", email: str = "clerkuser@test.io"
) -> dict:
    """A Clerk Backend API user object."""
    return {
        "id": clerk_id,
        "email_addresses": [
            {
                "id": "ema_1",
                "email_address": email,
                "verification": {"status": "verified"},
            }
        ],
        "primary_email_address_id": "ema_1",
        "first_name": "Clerk",
        "last_name": "User",
        "username": "clerkuser",
        "image_url": "https://img.example/avatar.png",
    }


# ---------------------------------------------------------------------------
# 1) Publishable key decoding
# ---------------------------------------------------------------------------


def test_clerk_frontend_api_decodes_publishable_key(monkeypatch):
    monkeypatch.setattr(settings, "CLERK_PUBLISHABLE_KEY", _PK, raising=False)
    assert clerk_frontend_api() == _FRONTEND_API


def test_clerk_frontend_api_rejects_malformed_key(monkeypatch):
    monkeypatch.setattr(settings, "CLERK_PUBLISHABLE_KEY", "garbage", raising=False)
    with pytest.raises(ClerkError):
        clerk_frontend_api()


def test_clerk_frontend_api_requires_config(monkeypatch):
    monkeypatch.setattr(settings, "CLERK_PUBLISHABLE_KEY", None, raising=False)
    with pytest.raises(ClerkError):
        clerk_frontend_api()


# ---------------------------------------------------------------------------
# 2) RS256 session-token verification
# ---------------------------------------------------------------------------


async def test_verify_clerk_session_token_valid(monkeypatch, rsa_keypair):
    private_key, jwk = rsa_keypair
    monkeypatch.setattr(settings, "CLERK_PUBLISHABLE_KEY", _PK, raising=False)

    async def fake_get_jwk(kid):
        assert kid == "test-key-1"
        return jwk

    monkeypatch.setattr("app.core.clerk._get_signing_jwk", fake_get_jwk)

    now = datetime.now(UTC)
    token = jose_jwt.encode(
        {
            "sub": "user_clerk_123",
            "iss": _FRONTEND_API,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key-1"},
    )

    claims = await verify_clerk_session_token(token)
    assert claims["sub"] == "user_clerk_123"
    assert claims["iss"] == _FRONTEND_API


async def test_verify_clerk_token_rejects_wrong_signing_key(monkeypatch, rsa_keypair):
    """Right kid (so the JWK resolves) but signed by a different key → reject."""
    _, jwk = rsa_keypair
    monkeypatch.setattr(settings, "CLERK_PUBLISHABLE_KEY", _PK, raising=False)
    monkeypatch.setattr("app.core.clerk._get_signing_jwk", AsyncMock(return_value=jwk))

    attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(UTC)
    token = jose_jwt.encode(
        {
            "sub": "user_attacker",
            "iss": _FRONTEND_API,
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        },
        attacker_key,
        algorithm="RS256",
        headers={"kid": "test-key-1"},
    )

    with pytest.raises(ClerkError):
        await verify_clerk_session_token(token)


async def test_verify_clerk_token_rejects_hs256(monkeypatch):
    """HS256 tokens must be rejected before any key lookup (alg pinning)."""
    monkeypatch.setattr(settings, "CLERK_PUBLISHABLE_KEY", _PK, raising=False)
    token = jose_jwt.encode({"sub": "user_x"}, "legacy-secret", algorithm="HS256")
    with pytest.raises(ClerkError):
        await verify_clerk_session_token(token)


async def test_verify_clerk_token_rejects_wrong_issuer(monkeypatch, rsa_keypair):
    private_key, jwk = rsa_keypair
    monkeypatch.setattr(settings, "CLERK_PUBLISHABLE_KEY", _PK, raising=False)
    monkeypatch.setattr("app.core.clerk._get_signing_jwk", AsyncMock(return_value=jwk))

    now = datetime.now(UTC)
    token = jose_jwt.encode(
        {
            "sub": "user_clerk_123",
            "iss": "https://evil.example.com",
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key-1"},
    )
    with pytest.raises(ClerkError):
        await verify_clerk_session_token(token)


# ---------------------------------------------------------------------------
# 3) Lazy provisioning through /auth/me with a Clerk token
# ---------------------------------------------------------------------------


async def test_me_with_clerk_token_provisions_local_user(
    client, db_session, monkeypatch, rsa_keypair
):
    private_key, _ = rsa_keypair
    now = datetime.now(UTC)
    token = jose_jwt.encode(
        {
            "sub": "user_sync_1",
            "iss": _FRONTEND_API,
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key-1"},
    )

    monkeypatch.setattr(
        "app.api.deps.verify_clerk_session_token",
        AsyncMock(return_value={"sub": "user_sync_1"}),
    )
    monkeypatch.setattr(
        "app.core.clerk.get_clerk_user",
        AsyncMock(return_value=_clerk_clerk_user("user_sync_1")),
    )

    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["email"] == "clerkuser@test.io"
    assert data["role"] == "student"
    assert data["is_verified"] is True

    # The local row is keyed by the Clerk user id and has profile + progress.
    result = await db_session.execute(
        select(User).where(User.provider_id == "user_sync_1")
    )
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.provider == AuthProvider.CLERK
    prof = await db_session.execute(
        select(Profile).where(Profile.user_id == user.id)
    )
    assert prof.scalar_one_or_none() is not None


async def test_me_with_clerk_token_rejects_invalid_token(client, monkeypatch, rsa_keypair):
    """Unverifiable RS256 token → 401 (no local provision, no 500)."""
    from app.core.clerk import ClerkError

    private_key, _ = rsa_keypair
    now = datetime.now(UTC)
    token = jose_jwt.encode(
        {"sub": "user_nope", "iss": _FRONTEND_API, "exp": int(now.timestamp())},
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key-1"},
    )
    # Simulate an unreachable/empty JWKS: verification raises ClerkError,
    # which deps must translate to 401 (not 500).
    monkeypatch.setattr(
        "app.core.clerk._get_signing_jwk",
        AsyncMock(side_effect=ClerkError("JWKS unavailable")),
    )
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 4) sync_clerk_user: create + link-by-email
# ---------------------------------------------------------------------------


async def test_sync_creates_local_user_with_profile_and_progress(db_session):
    user = await sync_clerk_user(
        db_session, "user_new_1", clerk_user=_clerk_clerk_user("user_new_1")
    )
    assert user.email == "clerkuser@test.io"
    assert user.provider == AuthProvider.CLERK
    assert user.provider_id == "user_new_1"
    assert user.role == UserRole.STUDENT
    assert user.status == UserStatus.ACTIVE
    assert user.is_verified is True
    assert user.full_name == "Clerk User"

    prof = await db_session.execute(
        select(Profile).where(Profile.user_id == user.id)
    )
    assert prof.scalar_one_or_none() is not None

    from app.models.progress import PlayerProgress

    prog = await db_session.execute(
        select(PlayerProgress).where(PlayerProgress.user_id == user.id)
    )
    assert prog.scalar_one_or_none() is not None


async def test_sync_links_existing_account_by_email(db_session):
    """A pre-Clerk account with the same email is linked, not duplicated —
    id, role and all FK data survive."""
    existing = User(
        email="legacy@test.io",
        full_name="Legacy User",
        role=UserRole.ADMINISTRATOR,
        status=UserStatus.ACTIVE,
        is_verified=True,
        provider=AuthProvider.EMAIL,
    )
    db_session.add(existing)
    await db_session.commit()
    existing_id = existing.id

    clerk_user = {
        "id": "user_link_9",
        "email_addresses": [
            {"id": "ema_2", "email_address": "legacy@test.io",
             "verification": {"status": "verified"}}
        ],
        "primary_email_address_id": "ema_2",
        "first_name": "Legacy",
        "last_name": "User",
    }
    user = await sync_clerk_user(db_session, "user_link_9", clerk_user=clerk_user)

    assert user.id == existing_id
    assert user.role == UserRole.ADMINISTRATOR  # RBAC preserved
    assert user.provider == AuthProvider.CLERK
    assert user.provider_id == "user_link_9"

    # No duplicate row was created for that email.
    result = await db_session.execute(
        select(User).where(User.email == "legacy@test.io")
    )
    rows = result.scalars().all()
    assert len(rows) == 1


async def test_sync_rejects_clerk_user_without_email(db_session):
    clerk_user = {"id": "user_no_email", "email_addresses": []}
    with pytest.raises(ValueError):
        await sync_clerk_user(db_session, "user_no_email", clerk_user=clerk_user)


# ---------------------------------------------------------------------------
# 5) Webhook signature verification (svix HMAC-SHA256, stdlib)
# ---------------------------------------------------------------------------


def _sign(secret: str, svix_id: str, ts: str, payload: str) -> str:
    signed = f"{svix_id}.{ts}.{payload}".encode()
    return base64.b64encode(
        hmac.new(secret.encode(), signed, hashlib.sha256).digest()
    ).decode()


def test_svix_signature_accepts_valid_signature():
    from app.api.v1.endpoints.auth import _verify_svix_signature

    secret = "whsec_test"
    ts = str(int(time.time()))
    payload = json.dumps({"type": "user.created", "data": {"id": "user_1"}})
    sig = _sign(secret, "msg_1", ts, payload)

    assert _verify_svix_signature(secret, "msg_1", ts, payload, f"v1,{sig}")
    # Un-prefixed signature also accepted (svix allows both forms).
    assert _verify_svix_signature(secret, "msg_1", ts, payload, sig)


def test_svix_signature_rejects_tampering_and_wrong_secret():
    from app.api.v1.endpoints.auth import _verify_svix_signature

    secret = "whsec_test"
    ts = str(int(time.time()))
    payload = json.dumps({"type": "user.created", "data": {"id": "user_1"}})
    sig = _sign(secret, "msg_1", ts, payload)

    # Tampered payload.
    assert not _verify_svix_signature(
        secret, "msg_1", ts, payload + "x", f"v1,{sig}"
    )
    # Wrong secret.
    assert not _verify_svix_signature(
        "whsec_wrong", "msg_1", ts, payload, f"v1,{sig}"
    )
    # Wrong svix-id.
    assert not _verify_svix_signature(secret, "msg_2", ts, payload, f"v1,{sig}")


def test_svix_signature_rejects_forged_and_stale_timestamps():
    from app.api.v1.endpoints.auth import _verify_svix_signature

    secret = "whsec_test"
    now = int(time.time())
    payload = "{}"

    # Non-numeric timestamp.
    assert not _verify_svix_signature(secret, "msg_1", "not-a-number", payload, "v1,x")
    # Stale timestamp (>5 min) — replay protection.
    old_ts = str(now - 3600)
    old_sig = _sign(secret, "msg_1", old_ts, payload)
    assert not _verify_svix_signature(secret, "msg_1", old_ts, payload, f"v1,{old_sig}")


# ---------------------------------------------------------------------------
# 6) Webhook endpoint end-to-end
# ---------------------------------------------------------------------------


async def test_webhook_endpoint_provisions_user(client, monkeypatch):
    monkeypatch.setattr(
        settings, "CLERK_WEBHOOK_SECRET", SecretStr("whsec_endpoint"), raising=False
    )
    payload = json.dumps(
        {"type": "user.created", "data": _clerk_clerk_user("user_hook_1")}
    )
    ts = str(int(time.time()))
    sig = _sign("whsec_endpoint", "msg_hook_1", ts, payload)

    resp = await client.post(
        "/api/v1/auth/clerk/webhook",
        content=payload,
        headers={
            "svix-id": "msg_hook_1",
            "svix-timestamp": ts,
            "svix-signature": f"v1,{sig}",
            "content-type": "application/json",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_webhook_endpoint_rejects_bad_signature(client, monkeypatch):
    monkeypatch.setattr(
        settings, "CLERK_WEBHOOK_SECRET", SecretStr("whsec_endpoint"), raising=False
    )
    payload = json.dumps({"type": "user.created", "data": {"id": "user_evil"}})
    ts = str(int(time.time()))

    resp = await client.post(
        "/api/v1/auth/clerk/webhook",
        content=payload,
        headers={
            "svix-id": "msg_1",
            "svix-timestamp": ts,
            "svix-signature": "v1,bm90YXNpZ25hdHVyZQ==",
            "content-type": "application/json",
        },
    )
    assert resp.status_code == 400


async def test_webhook_endpoint_rejects_missing_headers(client, monkeypatch):
    monkeypatch.setattr(
        settings, "CLERK_WEBHOOK_SECRET", SecretStr("whsec_endpoint"), raising=False
    )
    resp = await client.post(
        "/api/v1/auth/clerk/webhook",
        content=json.dumps({"type": "user.created", "data": {"id": "user_x"}}),
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 400
