"""Cookie-session, refresh-rotation, logout, and CSRF regression tests.

Covers the localStorage -> HttpOnly cookie migration:

- login/register deliver the session as HttpOnly cookies (no body tokens)
- cookie-authenticated requests work; unauthenticated/expired tokens do not
- refresh rotates cookies, with a short reuse grace for concurrent tabs
- logout clears cookies and revokes the refresh token (no grace)
- state-changing cookie-authenticated requests require CSRF protection
  (origin allow-list + double-submit token), while Bearer/CLI clients and
  pre-auth bootstrap endpoints keep working
- legacy clients can migrate an existing localStorage refresh token by
  posting it to /auth/refresh, which answers with fresh cookies
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import update

from app.core.security import create_access_token
from app.models.session import Session

TEST_ORIGIN = "http://localhost:3000"
EVIL_ORIGIN = "https://evil.example"


def _set_cookie(response, name: str) -> str | None:
    for header in response.headers.get_list("set-cookie"):
        if header.startswith(f"{name}="):
            return header
    return None


def _cookie_value(response, name: str) -> str:
    header = _set_cookie(response, name)
    assert header, f"response did not set {name}"
    return header.split(";", 1)[0].split("=", 1)[1]


async def _register(client, email: str = "cookie@test.io", username: str = "cookie_test", **extra):
    payload = {
        "email": email,
        "password": "StrongPass123!",
        "confirm_password": "StrongPass123!",
        "full_name": "Cookie Tester",
        "username": username,
    }
    payload.update(extra)
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response


# ---------------------------------------------------------------------------
# Login: HttpOnly cookie transport, body tokens hidden
# ---------------------------------------------------------------------------


async def test_login_delivers_httponly_cookies_and_hides_body_tokens(client):
    register = await _register(client)

    access = _set_cookie(register, "cv_access")
    refresh = _set_cookie(register, "cv_refresh")
    csrf = _set_cookie(register, "cv_csrf")

    assert access and "HttpOnly" in access
    assert refresh and "HttpOnly" in refresh
    # Scoped: access covers the API, refresh only the auth sub-routes.
    assert "Path=/api/v1" in access
    assert "Path=/api/v1/auth" in refresh
    assert "SameSite=lax" in access and "SameSite=lax" in refresh
    # The CSRF cookie must stay readable by frontend JS.
    assert csrf and "HttpOnly" not in csrf

    data = register.json()["data"]
    assert data["access_token"] is None
    assert data["refresh_token"] is None

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "cookie@test.io", "password": "StrongPass123!"},
    )
    assert login.status_code == 200
    assert login.json()["data"]["access_token"] is None
    assert _set_cookie(login, "cv_access") and "HttpOnly" in _set_cookie(login, "cv_access")


async def test_body_tokens_require_explicit_opt_in(client):
    response = await _register(client, email="optin@test.io", username="optin", include_tokens=True)
    data = response.json()["data"]
    assert data["access_token"]
    assert data["refresh_token"]


# ---------------------------------------------------------------------------
# Cookie authentication & unauthorized access
# ---------------------------------------------------------------------------


async def test_cookie_authenticates_requests_without_authorization_header(client):
    await _register(client)
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["data"]["email"] == "cookie@test.io"


async def test_unauthenticated_request_is_rejected(client):
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 401
    logout = await client.post("/api/v1/auth/logout")
    assert logout.status_code == 401


async def test_expired_access_token_is_rejected(client):
    register = await _register(client, email="expired@test.io", username="expired_test")
    user_id = register.json()["data"]["user"]["id"]
    expired = create_access_token(user_id, expires_delta=timedelta(seconds=-5))

    # Bearer form of the expired token.
    bearer = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert bearer.status_code == 401

    # Same expired value presented as the access cookie.
    client.cookies.clear()
    as_cookie = await client.get(
        "/api/v1/auth/me", headers={"Cookie": f"cv_access={expired}"}
    )
    assert as_cookie.status_code == 401


# ---------------------------------------------------------------------------
# Refresh rotation
# ---------------------------------------------------------------------------


async def test_refresh_rotates_cookies(client):
    register = await _register(client)
    old_refresh = _cookie_value(register, "cv_refresh")
    old_access = _cookie_value(register, "cv_access")

    refreshed = await client.post("/api/v1/auth/refresh", json={})
    assert refreshed.status_code == 200
    new_refresh = _cookie_value(refreshed, "cv_refresh")
    new_access = _cookie_value(refreshed, "cv_access")
    assert new_refresh != old_refresh
    assert new_access != old_access
    assert refreshed.json()["data"]["access_token"] is None


async def test_rotated_refresh_token_reusable_within_grace_then_rejected(client, db_session):
    register = await _register(client, email="grace@test.io", username="grace_rot")
    first_refresh = _cookie_value(register, "cv_refresh")

    # Rotate once so first_refresh becomes the "old" token.
    rotated = await client.post("/api/v1/auth/refresh", json={})
    assert rotated.status_code == 200

    # Presenting the just-rotated token (a racing tab) succeeds inside the
    # grace window.
    client.cookies.clear()
    grace = await client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
    assert grace.status_code == 200

    # Backdate the revocation beyond the grace window: now it is rejected.
    await db_session.execute(
        update(Session)
        .where(Session.refresh_token == first_refresh)
        .values(revoked_at=datetime.now(UTC) - timedelta(seconds=3600))
    )
    await db_session.commit()

    client.cookies.clear()
    late = await client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
    assert late.status_code == 401


async def test_refresh_without_any_token_is_rejected(client):
    response = await client.post("/api/v1/auth/refresh", json={})
    assert response.status_code == 401


async def test_legacy_localstorage_refresh_token_migrates_to_cookies(client):
    """A pre-migration client posts its stored refresh JWT and gets cookies."""
    register = await _register(client, email="legacy@test.io", username="legacy_user")
    legacy_token = _cookie_value(register, "cv_refresh")

    # Simulate the old client: JWT in hand, no cookies in the jar.
    client.cookies.clear()

    migrated = await client.post("/api/v1/auth/refresh", json={"refresh_token": legacy_token})
    assert migrated.status_code == 200
    assert _set_cookie(migrated, "cv_access") and "HttpOnly" in _set_cookie(migrated, "cv_access")
    assert migrated.json()["data"]["access_token"] is None

    # The migrated cookie session now works on its own.
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


async def test_logout_clears_cookies_and_revokes_refresh_token(client):
    register = await _register(client, email="out@test.io", username="out_user")
    refresh_value = _cookie_value(register, "cv_refresh")

    logout = await client.post("/api/v1/auth/logout")
    assert logout.status_code == 200

    access_cleared = _set_cookie(logout, "cv_access")
    refresh_cleared = _set_cookie(logout, "cv_refresh")
    assert access_cleared and ("Max-Age=0" in access_cleared or "cv_access=;" in access_cleared)
    assert refresh_cleared and ("Max-Age=0" in refresh_cleared or "cv_refresh=;" in refresh_cleared)

    # Session cookie gone -> me is unauthorized.
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 401

    # Revoked refresh token cannot be replayed (logout has no reuse grace).
    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_value})
    assert replay.status_code == 401


# ---------------------------------------------------------------------------
# CSRF protection
# ---------------------------------------------------------------------------


async def test_csrf_endpoint_issues_readable_token(client):
    response = await client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    token = response.json()["data"]["csrf_token"]
    assert isinstance(token, str) and len(token) >= 20
    csrf_cookie = _set_cookie(response, "cv_csrf")
    assert csrf_cookie and "HttpOnly" not in csrf_cookie


async def test_cross_site_write_is_rejected_by_origin_check(client):
    await _register(client, email="csrf1@test.io", username="csrf1")
    response = await client.post("/api/v1/auth/logout", headers={"Origin": EVIL_ORIGIN})
    assert response.status_code == 403
    assert "origin" in response.json()["detail"].lower()


async def test_cookie_write_without_csrf_token_is_rejected(client):
    await _register(client, email="csrf2@test.io", username="csrf2")
    response = await client.post("/api/v1/auth/logout", headers={"Origin": TEST_ORIGIN})
    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]


async def test_cookie_write_with_csrf_token_succeeds(client):
    register = await _register(client, email="csrf3@test.io", username="csrf3")
    csrf_token = _cookie_value(register, "cv_csrf")

    response = await client.post(
        "/api/v1/auth/logout",
        headers={"Origin": TEST_ORIGIN, "X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 200


async def test_bootstrap_login_exempt_from_csrf_token_but_not_origin(client):
    # The database is function-scoped, so this test must create its own user
    # instead of relying on one registered by an earlier test.
    await _register(client, email="cookie@test.io", username="cookie_test")

    # Allowed origin, no CSRF header: bootstrap endpoints are exempt.
    ok = await client.post(
        "/api/v1/auth/login",
        json={"email": "cookie@test.io", "password": "StrongPass123!"},
        headers={"Origin": TEST_ORIGIN},
    )
    assert ok.status_code == 200

    # Cross-site login attempt is still blocked by the origin check.
    blocked = await client.post(
        "/api/v1/auth/login",
        json={"email": "cookie@test.io", "password": "StrongPass123!"},
        headers={"Origin": EVIL_ORIGIN},
    )
    assert blocked.status_code == 403


async def test_invalid_credentials_return_401_not_500(client):
    # A wrong password is an authentication failure, not a server outage.
    await _register(client, email="wrongpw@test.io", username="wrongpw")
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpw@test.io", "password": "NotThePassword1!"},
        headers={"Origin": TEST_ORIGIN},
    )
    assert response.status_code == 401


async def test_bearer_client_is_exempt_from_csrf_token(client):
    register = await _register(
        client, email="api@test.io", username="api_user", include_tokens=True
    )
    token = register.json()["data"]["access_token"]

    response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}", "Origin": TEST_ORIGIN},
    )
    # Authorization header => not an ambient-credential (cookie) request.
    assert response.status_code == 200


async def test_non_browser_client_without_origin_is_untouched(client):
    """No Origin/Referer header (curl, test suite) => no CSRF challenge."""
    await _register(client, email="cli@test.io", username="cli_user")
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 200
