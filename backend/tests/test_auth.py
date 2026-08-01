"""Authentication flow tests."""


async def test_register_creates_account(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@test.io",
            "password": "StrongPass123!",
            "full_name": "Alice Tester",
            "username": "alice_test",
        },
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user"]["email"] == "alice@test.io"
    assert data["user"]["role"] == "student"
    assert data["user"]["is_verified"] is False


async def test_register_duplicate_email_rejected(client):
    payload = {
        "email": "bob@test.io",
        "password": "StrongPass123!",
        "full_name": "Bob Tester",
        "username": "bob_test",
    }
    first = await client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/api/v1/auth/register", json=payload)
    assert second.status_code in (400, 409)


async def test_login_success(client):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "carol@test.io",
            "password": "StrongPass123!",
            "full_name": "Carol Tester",
            "username": "carol_test",
        },
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "carol@test.io", "password": "StrongPass123!"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["access_token"]


async def test_login_wrong_password_rejected(client):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "dave@test.io",
            "password": "StrongPass123!",
            "full_name": "Dave Tester",
            "username": "dave_test",
        },
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "dave@test.io", "password": "WrongPass123!"},
    )
    assert response.status_code == 401


async def test_me_requires_auth(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_with_token(client):
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "erin@test.io",
            "password": "StrongPass123!",
            "full_name": "Erin Tester",
            "username": "erin_test",
        },
    )
    token = register.json()["data"]["access_token"]

    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["data"]["email"] == "erin@test.io"


async def test_refresh_token_flow(client):
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "frank@test.io",
            "password": "StrongPass123!",
            "full_name": "Frank Tester",
            "username": "frank_test",
        },
    )
    refresh_token = register.json()["data"]["refresh_token"]

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200
    assert response.json()["data"]["access_token"]


async def test_logout_revokes_session(client):
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "grace@test.io",
            "password": "StrongPass123!",
            "full_name": "Grace Tester",
            "username": "grace_test",
        },
    )
    token = register.json()["data"]["access_token"]
    refresh_token = register.json()["data"]["refresh_token"]
    headers = {"Authorization": f"Bearer {token}"}

    logout = await client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 200

    refresh_after = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_after.status_code == 401
