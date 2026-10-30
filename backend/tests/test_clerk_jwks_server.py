"""Real JWKS-server tests for Clerk session-token verification.

Unlike ``test_clerk.py`` (which mocks ``_get_signing_jwk``), these tests run
the ENTIRE verification path against a controlled local JWKS server:

  * a real HTTP server serves ``/.well-known/jwks.json`` on 127.0.0.1
  * ``_fetch_jwks`` performs a real httpx GET against it
  * the in-process cache, kid lookup, force-refresh/rotation logic run for real
  * tokens are really RS256-signed with a real 2048-bit RSA key

The single bypass is ``clerk_frontend_api()`` (patched to the local server
origin), because the production derivation hardcodes ``https://``; the
derivation itself is covered by ``test_clerk_frontend_api_decodes_publishable_key``
and was verified live against production (pk_live_ -> clerk.cyberverse.com).

Covers: valid token acceptance, JWKS key rotation, expired tokens, wrong
issuer, wrong signing key, and JWKS-server outage handling.
"""

from __future__ import annotations

import base64
import json
import threading
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt as jose_jwt

from app.core import clerk as clerk_mod
from app.core.clerk import ClerkError, verify_clerk_session_token


def _b64url_uint(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _pem(private_key) -> bytes:
    return private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def _jwk(private_key, kid: str) -> dict:
    pub = private_key.public_key().public_numbers()
    return {
        "kty": "RSA",
        "use": "sig",
        "kid": kid,
        "alg": "RS256",
        "n": _b64url_uint(pub.n),
        "e": _b64url_uint(pub.e),
    }


@pytest.fixture(scope="module")
def rsa_keys():
    """Two real RSA keys: key-1 (initial) and key-2 (rotation target)."""
    key1 = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key2 = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return {
        "key1": (key1, _jwk(key1, "srv-key-1")),
        "key2": (key2, _jwk(key2, "srv-key-2")),
    }


class _JWKSHandler(BaseHTTPRequestHandler):
    """Serves a mutable JWKS payload and counts hits (rotation = swap payload)."""

    payload: dict = {"keys": []}
    hits: int = 0

    def do_GET(self) -> None:  # noqa: N802 — http.server API
        if self.path == "/.well-known/jwks.json":
            type(self).hits += 1
            body = json.dumps(type(self).payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

    def log_message(self, *args) -> None:  # silence request logging in pytest
        pass


@pytest.fixture()
def jwks_server(rsa_keys):
    """Controlled JWKS server: (origin, keys) with per-test hit reset."""
    _JWKSHandler.payload = {"keys": [rsa_keys["key1"][1]]}
    _JWKSHandler.hits = 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), _JWKSHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_address[1]}"
    yield origin, rsa_keys
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


@pytest.fixture(autouse=True)
def _reset_jwks_module_state():
    """Run every test with a cold in-process JWKS cache (and leave it cold)."""
    clerk_mod._jwks_cache.clear()
    clerk_mod._jwks_fetched_at = 0.0
    yield
    clerk_mod._jwks_cache.clear()
    clerk_mod._jwks_fetched_at = 0.0


def _signed(private_key, kid: str, claims: dict) -> str:
    return jose_jwt.encode(claims, _pem(private_key), algorithm="RS256", headers={"kid": kid})


def _claims(origin: str, minutes: int = 5, sub: str = "user_srv_1", iss: str | None = None) -> dict:
    now = datetime.now(UTC)
    return {
        "sub": sub,
        "iss": iss or origin,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
    }


async def test_valid_token_accepted_via_real_jwks_server(jwks_server, monkeypatch):
    origin, keys = jwks_server
    monkeypatch.setattr(clerk_mod, "clerk_frontend_api", lambda: origin, raising=False)
    key1, _ = keys["key1"]
    token = _signed(key1, "srv-key-1", _claims(origin))

    payload = await verify_clerk_session_token(token)

    assert payload["sub"] == "user_srv_1"
    assert _JWKSHandler.hits == 1  # fetched over real HTTP, not mocked
    # Cache is now warm in-process.
    assert "srv-key-1" in clerk_mod._jwks_cache


async def test_jwks_rotation_new_kid_forces_refresh_and_is_accepted(jwks_server, monkeypatch):
    origin, keys = jwks_server
    monkeypatch.setattr(clerk_mod, "clerk_frontend_api", lambda: origin, raising=False)
    key1, _ = keys["key1"]
    key2, _ = keys["key2"]

    # First token pins the cache on key-1.
    first = _signed(key1, "srv-key-1", _claims(origin))
    await verify_clerk_session_token(first)
    assert _JWKSHandler.hits == 1

    # Clerk rotates: the server now only serves key-2.
    _JWKSHandler.payload = {"keys": [keys["key2"][1]]}

    second = _signed(key2, "srv-key-2", _claims(origin, sub="user_srv_2"))
    payload = await verify_clerk_session_token(second)

    assert payload["sub"] == "user_srv_2"
    assert _JWKSHandler.hits == 2  # unknown kid forced a real refresh


async def test_expired_token_rejected_via_real_jwks(jwks_server, monkeypatch):
    origin, keys = jwks_server
    monkeypatch.setattr(clerk_mod, "clerk_frontend_api", lambda: origin, raising=False)
    key1, _ = keys["key1"]
    token = _signed(key1, "srv-key-1", _claims(origin, minutes=-5))

    with pytest.raises(ClerkError, match="expired"):
        await verify_clerk_session_token(token)


async def test_wrong_issuer_rejected_via_real_jwks(jwks_server, monkeypatch):
    origin, keys = jwks_server
    monkeypatch.setattr(clerk_mod, "clerk_frontend_api", lambda: origin, raising=False)
    key1, _ = keys["key1"]
    token = _signed(key1, "srv-key-1", _claims(origin, iss="https://attacker.example"))

    with pytest.raises(ClerkError, match="Invalid Clerk token"):
        await verify_clerk_session_token(token)


async def test_wrong_signing_key_rejected_via_real_jwks(jwks_server, monkeypatch):
    origin, keys = jwks_server
    monkeypatch.setattr(clerk_mod, "clerk_frontend_api", lambda: origin, raising=False)
    key2, _ = keys["key2"]  # attacker's key; server only trusts key-1
    token = _signed(key2, "srv-key-1", _claims(origin))  # forged kid header

    with pytest.raises(ClerkError, match="Invalid Clerk token"):
        await verify_clerk_session_token(token)
    assert _JWKSHandler.hits == 1  # no refresh loop on a bad signature


async def test_jwks_server_outage_maps_to_clerk_error(jwks_server, monkeypatch):
    origin, keys = jwks_server
    monkeypatch.setattr(clerk_mod, "clerk_frontend_api", lambda: origin, raising=False)
    key1, _ = keys["key1"]
    token = _signed(key1, "srv-key-1", _claims(origin))

    # Cold cache + dead JWKS endpoint must surface as ClerkError (which auth
    # deps map to 401/503), never an unhandled 500. Point at a freshly-closed
    # port so the real httpx fetch gets connection-refused.
    import socket

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    dead_port = sock.getsockname()[1]
    sock.close()
    dead_origin = f"http://127.0.0.1:{dead_port}"
    monkeypatch.setattr(clerk_mod, "clerk_frontend_api", lambda: dead_origin, raising=False)

    with pytest.raises(ClerkError, match="Unable to fetch Clerk JWKS"):
        await verify_clerk_session_token(token)
