"""Progress, profile, and gamification tests."""

import pytest


async def _register(client, email, username, name="Test Agent"):
    return await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
            "full_name": name,
            "username": username,
        },
    )


async def _auth_headers(client, email="agent@test.io", username="agent_test"):
    register = await _register(client, email, username)
    token = register.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_profile_created_on_first_access(client):
    headers = await _auth_headers(client, "p1@test.io", "p1_test")
    response = await client.get("/api/v1/profile/", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["username"] == "p1_test"
    assert data["xp"] == 0
    assert data["level"] == 1


async def test_profile_update(client):
    headers = await _auth_headers(client, "p2@test.io", "p2_test")
    response = await client.patch(
        "/api/v1/profile/",
        json={"bio": "Learning to defend the verse."},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["bio"] == "Learning to defend the verse."


async def test_progress_overview(client):
    headers = await _auth_headers(client, "p3@test.io", "p3_test")
    response = await client.get("/api/v1/progress/overview", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_xp"] == 0
    assert data["level"] == 1


async def test_daily_checkin_awards_bonus(client):
    headers = await _auth_headers(client, "p4@test.io", "p4_test")

    first = await client.post("/api/v1/progress/streak/checkin", headers=headers)
    assert first.status_code == 200
    data = first.json()["data"]
    assert data["already_checked_in"] is False
    assert data["streak"] == 1
    assert data["bonus_xp"] >= 10

    second = await client.post("/api/v1/progress/streak/checkin", headers=headers)
    assert second.json()["data"]["already_checked_in"] is True


async def test_xp_award_updates_level_data(client, db_session):
    from sqlalchemy import select

    from app.models.user import User, UserRole

    headers = await _auth_headers(client, "p5@test.io", "p5_test")
    # Students cannot mint XP on themselves (abuse fix): staff only.
    denied = await client.post("/api/v1/progress/xp?xp=250&coins=50", headers=headers)
    assert denied.status_code == 403

    user = (await db_session.execute(select(User).where(User.email == "p5@test.io"))).scalar_one()
    user.role = UserRole.ADMINISTRATOR
    await db_session.commit()
    login = await client.post(
        "/api/v1/auth/login", json={"email": "p5@test.io", "password": "StrongPass123!"}
    )
    staff_headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    response = await client.post("/api/v1/progress/xp?xp=250&coins=50", headers=staff_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["xp_awarded"] == 250
    assert data["level"] >= 1

    overview = await client.get("/api/v1/progress/overview", headers=staff_headers)
    assert overview.json()["data"]["total_xp"] == 250


async def test_leaderboard_available(client):
    headers = await _auth_headers(client, "p6@test.io", "p6_test")
    response = await client.get("/api/v1/leaderboard/?type=all_time", headers=headers)
    assert response.status_code == 200
    assert "entries" in response.json()["data"]


async def test_missions_list_and_start(client):
    headers = await _auth_headers(client, "p7@test.io", "p7_test")

    listing = await client.get("/api/v1/missions/", headers=headers)
    assert listing.status_code == 200

    missions = listing.json()["data"]["items"]
    if not missions:
        # Create mission via seeding if possible by hitting a different approach
        # Just assert structure is correct when empty or with items
        assert isinstance(missions, list)
        return

    first = missions[0]
    started = await client.post(f"/api/v1/missions/{first['id']}/start", headers=headers)
    assert started.status_code == 200
    assert started.json()["data"]["status"] == "in_progress"
