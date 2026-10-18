"""Security regression tests: IDOR, RBAC, XP mint, SOC isolation, OAuth, refresh reuse."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.security import create_access_token
from app.models.user import User, UserRole

pytestmark = pytest.mark.asyncio


async def _register(client, email, name="Test User", username=None):
    username = username or email.split("@")[0].replace(".", "_").replace("-", "_")
    r = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
            "full_name": name,
            "username": username,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def _login(client, email, password="StrongPass123!"):
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["data"]


async def _promote(db_session, email, role: UserRole):
    user = (await db_session.execute(select(User).where(User.email == email))).scalar_one()
    user.role = role
    await db_session.commit()
    return user


def _uid(data):
    return data["user"]["id"]


# --- IDOR: user records -----------------------------------------------------


async def test_user_cannot_read_other_user(client):
    a = await _register(client, "idor-a@test.io")
    b = await _register(client, "idor-b@test.io")
    headers = {"Authorization": f"Bearer {b['access_token']}"}
    r = await client.get(f"/api/v1/users/{_uid(a)}", headers=headers)
    assert r.status_code == 404


async def test_user_self_read_redacted(client):
    a = await _register(client, "selfread@test.io")
    headers = {"Authorization": f"Bearer {a['access_token']}"}
    r = await client.get(f"/api/v1/users/{_uid(a)}", headers=headers)
    assert r.status_code == 200
    body = r.json()["data"]
    assert "email" not in body
    assert "is_2fa_enabled" not in body


async def test_moderator_can_read_user_with_email(client, db_session):
    a = await _register(client, "modtarget@test.io")
    m = await _register(client, "moduser@test.io")
    await _promote(db_session, "moduser@test.io", UserRole.MODERATOR)
    tokens = await _login(client, "moduser@test.io")
    r = await client.get(
        f"/api/v1/users/{_uid(a)}",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["email"] == "modtarget@test.io"


# --- RBAC: role changes -----------------------------------------------------


async def test_admin_cannot_grant_super_admin(client, db_session):
    await _register(client, "victim@test.io")
    await _register(client, "adminx@test.io")
    await _promote(db_session, "adminx@test.io", UserRole.ADMINISTRATOR)
    victim_id = (
        await db_session.execute(select(User.id).where(User.email == "victim@test.io"))
    ).scalar_one()
    tokens = await _login(client, "adminx@test.io")
    r = await client.patch(
        f"/api/v1/users/{victim_id}/role",
        params={"new_role": "super_admin"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 403


async def test_super_admin_can_change_role_but_not_self(client, db_session):
    await _register(client, "victim2@test.io")
    await _register(client, "supertest@test.io")
    await _promote(db_session, "supertest@test.io", UserRole.SUPER_ADMIN)
    tokens = await _login(client, "supertest@test.io")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    victim_id = (
        await db_session.execute(select(User.id).where(User.email == "victim2@test.io"))
    ).scalar_one()
    r = await client.patch(
        f"/api/v1/users/{victim_id}/role", params={"new_role": "moderator"}, headers=headers
    )
    assert r.status_code == 200
    me = (
        await db_session.execute(select(User.id).where(User.email == "supertest@test.io"))
    ).scalar_one()
    r = await client.patch(
        f"/api/v1/users/{me}/role", params={"new_role": "student"}, headers=headers
    )
    assert r.status_code == 400


async def test_register_ignores_role_field(client):
    r = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "norole@test.io",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
            "full_name": "No Role",
            "username": "norole",
            "role": "super_admin",
        },
    )
    assert r.status_code == 201
    assert r.json()["data"]["user"]["role"] == "student"


# --- XP mint -----------------------------------------------------------------


async def test_xp_mint_forbidden_for_student(client):
    a = await _register(client, "mint@test.io")
    r = await client.post(
        "/api/v1/progress/xp",
        params={"xp": 100000, "coins": 100000},
        headers={"Authorization": f"Bearer {a['access_token']}"},
    )
    assert r.status_code == 403


# --- SOC isolation ------------------------------------------------------------


async def test_soc_incident_owner_isolation(client):
    a = await _register(client, "soc-a@test.io")
    b = await _register(client, "soc-b@test.io")
    ha = {"Authorization": f"Bearer {a['access_token']}"}
    hb = {"Authorization": f"Bearer {b['access_token']}"}
    r = await client.post(
        "/api/v1/soc/incidents",
        json={
            "title": "Suspicious login burst",
            "description": "Ten failed logins from one IP in a minute.",
        },
        headers=ha,
    )
    assert r.status_code == 201, r.text
    incident_id = r.json()["data"]["id"]
    assert (await client.get(f"/api/v1/soc/incidents/{incident_id}", headers=hb)).status_code == 404
    assert (await client.get(f"/api/v1/soc/incidents/{incident_id}", headers=ha)).status_code == 200


# --- Tournament team membership -------------------------------------------------


async def test_tournament_register_requires_team_membership(client, db_session):
    await _register(client, "tcap@test.io")
    await _register(client, "tmem@test.io")
    await _register(client, "toutsider@test.io")
    await _promote(db_session, "tcap@test.io", UserRole.INSTRUCTOR)
    cap = await _login(client, "tcap@test.io")
    out = await _login(client, "toutsider@test.io")
    hc = {"Authorization": f"Bearer {cap['access_token']}"}
    ho = {"Authorization": f"Bearer {out['access_token']}"}
    t = await client.post(
        "/api/v1/game/tournaments",
        json={
            "name": "Sec Cup",
            "description": "Security regression tournament",
            "start_at": "2030-01-01T00:00:00Z",
            "end_at": "2030-02-01T00:00:00Z",
            "max_players": 100,
            "max_teams": 16,
            "rules": "No flag sharing",
        },
        headers=hc,
    )
    assert t.status_code == 201, t.text
    tid = t.json()["data"]["id"]
    team = await client.post(
        "/api/v1/game/teams",
        json={"name": "Cap Team", "tag": "CAPT", "description": "d"},
        headers=hc,
    )
    assert team.status_code == 201, team.text
    team_id = team.json()["data"]["id"]
    r = await client.post(
        f"/api/v1/game/tournaments/{tid}/register",
        json={"team_id": team_id},
        headers=ho,
    )
    assert r.status_code == 403


# --- OAuth forged token ----------------------------------------------------------


async def test_google_forged_token_rejected_when_verifier_says_no(client):
    from unittest.mock import patch

    class _Resp:
        status_code = 400
        text = "invalid"

        def json(self):
            return {}

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, url):
            return _Resp()

    with patch("httpx.AsyncClient", _Client):
        r = await client.post("/api/v1/auth/google", json={"credential": "forged.header.payload"})
    assert r.status_code == 400
    assert "access_token" not in r.text


# --- Refresh rotation --------------------------------------------------------------


async def test_refresh_reuse_kills_session(client):
    a = await _login(client, (await _register(client, "reuse@test.io"))["user"]["email"])
    r1 = a["refresh_token"]
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": r1})
    assert r.status_code == 200
    r2 = r.json()["data"]["refresh_token"]
    assert r2 != r1
    assert (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": r1})
    ).status_code == 401
    # theft response revoked everything, including the rotated token
    assert (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": r2})
    ).status_code == 401


# --- Expired / wrong-type tokens ------------------------------------------------------


async def test_expired_access_token_rejected(client, db_session):
    from uuid import UUID

    await _register(client, "expired@test.io")
    user_id = (
        await db_session.execute(select(User.id).where(User.email == "expired@test.io"))
    ).scalar_one()
    from datetime import timedelta

    token = create_access_token(str(user_id), expires_delta=timedelta(seconds=-1))
    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code in (401, 403)


async def test_wrong_password_is_401_not_500(client):
    await _register(client, "badpass@test.io")
    r = await client.post(
        "/api/v1/auth/login", json={"email": "badpass@test.io", "password": "WrongPass999!"}
    )
    assert r.status_code == 401
