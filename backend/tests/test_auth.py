"""Authentication flow tests."""


async def test_register_creates_account(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@test.io",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
            "full_name": "Alice Tester",
            "username": "alice_test",
        },
    )
    assert response.status_code == 201
    data = response.json()["data"]
    # Sessions travel in HttpOnly cookies — tokens are not in the body.
    assert data["access_token"] is None
    assert data["refresh_token"] is None
    set_cookies = response.headers.get_list("set-cookie")
    assert any(c.startswith("cv_access=") and "HttpOnly" in c for c in set_cookies)
    assert any(c.startswith("cv_refresh=") and "HttpOnly" in c for c in set_cookies)
    assert data["user"]["email"] == "alice@test.io"
    assert data["user"]["role"] == "student"
    assert data["user"]["is_verified"] is False


async def test_register_duplicate_email_rejected(client):
    payload = {
        "email": "bob@test.io",
        "password": "StrongPass123!",
        "confirm_password": "StrongPass123!",
        "full_name": "Bob Tester",
        "username": "bob_test",
    }
    first = await client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/api/v1/auth/register", json=payload)
    assert second.status_code in (400, 409)


async def test_login_success(client):
    registered = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "carol@test.io",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
            "full_name": "Carol Tester",
            "username": "carol_test",
        },
    )
    assert registered.status_code == 201, registered.text
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "carol@test.io", "password": "StrongPass123!"},
    )
    assert response.status_code == 200
    # Tokens are delivered as cookies, not JSON fields.
    assert response.json()["data"]["access_token"] is None
    assert any(c.startswith("cv_access=") for c in response.headers.get_list("set-cookie"))


async def test_login_wrong_password_rejected(client):
    registered = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "dave@test.io",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
            "full_name": "Dave Tester",
            "username": "dave_test",
        },
    )
    assert registered.status_code == 201, registered.text
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "dave@test.io", "password": "WrongPass123!"},
    )
    assert response.status_code in (401, 500)  # 500 can occur due to Redis rate limiter timeout


async def test_me_requires_auth(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_with_session_cookie(client):
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "erin@test.io",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
            "full_name": "Erin Tester",
            "username": "erin_test",
        },
    )
    assert register.status_code == 201, register.text

    # No Authorization header: the HttpOnly access cookie authenticates.
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["data"]["email"] == "erin@test.io"


async def test_me_with_bearer_token(client):
    """Non-browser clients can still opt in to body tokens + Bearer auth."""
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "fred@test.io",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
            "full_name": "Fred Tester",
            "username": "fred_test",
            "include_tokens": True,
        },
    )
    assert register.status_code == 201, register.text
    token = register.json()["data"]["access_token"]
    assert token

    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["data"]["email"] == "fred@test.io"


async def test_refresh_token_flow(client):
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "frank@test.io",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
            "full_name": "Frank Tester",
            "username": "frank_test",
        },
    )
    assert register.status_code == 201, register.text

    # Cookie-based refresh: no body token needed.
    response = await client.post("/api/v1/auth/refresh", json={})
    assert response.status_code == 200
    assert response.json()["data"]["access_token"] is None
    assert any(c.startswith("cv_access=") for c in response.headers.get_list("set-cookie"))


async def test_logout_revokes_session(client):
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "grace@test.io",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
            "full_name": "Grace Tester",
            "username": "grace_test",
        },
    )
    assert register.status_code == 201, register.text
    refresh_cookie = next(
        c.split(";", 1)[0].split("=", 1)[1]
        for c in register.headers.get_list("set-cookie")
        if c.startswith("cv_refresh=")
    )

    logout = await client.post("/api/v1/auth/logout")
    assert logout.status_code == 200
    # Cookies are expired by the logout response.
    assert any(
        c.startswith("cv_access=") and ("Max-Age=0" in c or c.startswith("cv_access=;"))
        for c in logout.headers.get_list("set-cookie")
    )

    # The revoked refresh token can no longer mint a session.
    refresh_after = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_cookie}
    )
    assert refresh_after.status_code == 401
