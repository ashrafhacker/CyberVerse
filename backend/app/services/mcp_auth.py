"""Clerk OAuth token verification for CyberVerse MCP (resource-audience model)."""
from __future__ import annotations

from typing import Optional

from jose import JWTError, jwt

from app.core.clerk import ClerkError, clerk_frontend_api, _fetch_jwks
from app.core.config import settings

_RESOURCE_AUDIENCE = "https://opencode"
_CLERK_ISSUER = clerk_frontend_api()


class MCPAuthError(Exception):
    pass


async def verify_oauth_token(token: str) -> dict:
    """Verify a Clerk OAuth access token (not session token) for CyberVerse MCP.

    Requires:
      - `typ` claim == "at+JWT" (access token, not session token)
      - `iss` == Clerk instance URL (issuer from JWKS)
      - `aud` == exact resource audience (https://opencode)
      - `exp` > current time
    Raises MCPAuthError with appropriate message for each failure mode.
    """
    if not token:
        raise MCPAuthError("missing_token")
    # Reject session tokens (missing `typ` or not `at+JWT`)
    # We decode unverified first ONLY to read claims for the challenge message,
    # but the real verification uses JWKS RS256.
    try:
        unverified = jwt.get_unverified_claims(token)
    except JWTError as exc:
        raise MCPAuthError("invalid_token_format") from exc

    token_type = unverified.get("typ")
    if token_type != "at+JWT":
        raise MCPAuthError(f"invalid_token_type: expected 'at+JWT', got {token_type!r}")

    # Audience check
    audience = unverified.get("aud")
    if audience != _RESOURCE_AUDIENCE:
        raise MCPAuthError(
            f"invalid_audience: expected {_RESOURCE_AUDIENCE}, got {audience!r}"
        )

    # Expiry check (before JWKS fetch to fail fast)
    exp = unverified.get("exp")
    if exp is None:
        raise MCPAuthError("missing_exp")

    # JWKS verification (RS256) — never authorize from unverified claims
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise MCPAuthError("invalid_token_format") from exc
    if header.get("alg") != "RS256":
        raise MCPAuthError(f"unexpected_alg: {header.get('alg')!r}")
    from app.core.clerk import _get_signing_jwk, _CLERK_ALGORITHM
    jwk = await _get_signing_jwk(header.get("kid"))
    try:
        payload = jwt.decode(
            token,
            jwk,
            algorithms=[_CLERK_ALGORITHM],
            audience=_RESOURCE_AUDIENCE,
            issuer=_CLERK_ISSUER,
            options={"verify_exp": True},
        )
    except JWTError as exc:
        raise MCPAuthError(f"jwt_verification_failed: {exc}") from exc
    # After verification: enforce access-token type and audience again from verified payload
    if payload.get("typ") != "at+JWT":
        raise MCPAuthError(f"invalid_token_type_verified: expected 'at+JWT', got {payload.get('typ')!r}")
    if payload.get("aud") != _RESOURCE_AUDIENCE:
        raise MCPAuthError(f"invalid_audience_verified: expected {_RESOURCE_AUDIENCE}, got {payload.get('aud')!r}")
    return payload
