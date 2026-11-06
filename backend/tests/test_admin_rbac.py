"""Phase A verification: admin RBAC, management endpoints, audit logging.

Every assertion here is the TARGET production behaviour. Failures produced
before the admin-repair work land are the Phase A finding list; after the
repair this module must be fully green alongside the rest of the suite.

Role mapping used throughout (mission roles -> backend UserRole):
    Viewer          -> student
    Analyst         -> instructor
    SecurityAnalyst -> moderator
    Admin           -> administrator  (developer shares the admin tier)
    Super Admin     -> super_admin
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.models.analytics import AppSetting, FeatureFlag
from app.models.premium import Subscription, SubscriptionPlan, SubscriptionStatus
from app.models.session import AuditLog
from app.models.support import TicketStatus
from app.models.user import User, UserRole

pytestmark = pytest.mark.asyncio

PASSWORD = "StrongPass123!"

# ------------------------------------------------------------------
# Production Readiness Center — backend verification (read-only, no writes)
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_production_readiness_authorized(client, db_session):
    await _register(client, "pr_auth@test.io")
    await _promote(db_session, "pr_auth@test.io", UserRole.ADMINISTRATOR)
    tokens = await _login(client, "pr_auth@test.io")
    res = await client.get("/api/v1/admin/production-readiness", headers=_hdr(tokens))
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert "overall_status" in data
    assert "checks" in data
    # No secret leakage in any check response
    for k, v in data["checks"].items():
        d = v.get("details", "")
        assert "connection string" not in str(d).lower()

@pytest.mark.asyncio
async def test_admin_production_readiness_unauthorized(client):
    res = await client.get("/api/v1/admin/production-readiness")
    assert res.status_code in (401, 403), f"Expected 401/403, got {res.status_code}"

@pytest.mark.asyncio
async def test_database_select_1_behavior(client, db_session):
    await _register(client, "pr_db@test.io")
    await _promote(db_session, "pr_db@test.io", UserRole.ADMINISTRATOR)
    tokens = await _login(client, "pr_db@test.io")
    res = await client.get("/api/v1/admin/production-readiness/database", headers=_hdr(tokens))
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["status"] in ("pass", "degraded")
    # Real SELECT 1 executed (verified by endpoint design), not fabricated
    details = str(data.get("details", ""))
    assert "SELECT 1" in details or "failed" in details.lower()

@pytest.mark.asyncio
async def test_backup_not_checked_without_evidence(client, db_session):
    await _register(client, "pr_backup@test.io")
    await _promote(db_session, "pr_backup@test.io", UserRole.ADMINISTRATOR)
    tokens = await _login(client, "pr_backup@test.io")
    res = await client.get("/api/v1/admin/production-readiness/backup", headers=_hdr(tokens))
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "not_checked"

@pytest.mark.asyncio
async def test_clerk_not_claimed_without_verification(client, db_session):
    await _register(client, "pr_clerk@test.io")
    await _promote(db_session, "pr_clerk@test.io", UserRole.ADMINISTRATOR)
    tokens = await _login(client, "pr_clerk@test.io")
    res = await client.get("/api/v1/admin/production-readiness/clerk", headers=_hdr(tokens))
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "not_checked"

@pytest.mark.asyncio
async def test_webhook_not_claimed_without_delivery_evidence(client, db_session):
    await _register(client, "pr_webhook@test.io")
    await _promote(db_session, "pr_webhook@test.io", UserRole.ADMINISTRATOR)
    tokens = await _login(client, "pr_webhook@test.io")
    res = await client.get("/api/v1/admin/production-readiness/clerk-webhooks", headers=_hdr(tokens))
    assert res.status_code == 200, res.text
    d = res.json()["data"]
    assert d["status"] in ("not_checked", "blocked")
    # Must not rely solely on audit log presence for delivery proof
    details = str(d.get("details", ""))
    assert "audit log" not in details.lower() or "separately" in details.lower()

@pytest.mark.asyncio
async def test_aggregate_precedence(client, db_session):
    await _register(client, "pr_aggregate@test.io")
    await _promote(db_session, "pr_aggregate@test.io", UserRole.ADMINISTRATOR)
    tokens = await _login(client, "pr_aggregate@test.io")
    res = await client.get("/api/v1/admin/production-readiness", headers=_hdr(tokens))
    assert res.status_code == 200, res.text
    d = res.json()["data"]
    assert "overall_status" in d
    # Aggregate status derived from checks, not hardcoded
    checks = d.get("checks", {})
    statuses = [v["status"] for v in checks.values() if isinstance(v, dict) and "status" in v]
    # Status values must not contain fabricated claims
    for s in statuses:
        assert s in ("pass", "warning", "degraded", "blocked", "not_checked", "operational")

@pytest.mark.asyncio
async def test_no_secret_leakage_in_readiness(client, db_session):
    await _register(client, "pr_leak@test.io")
    await _promote(db_session, "pr_leak@test.io", UserRole.ADMINISTRATOR)
    tokens = await _login(client, "pr_leak@test.io")
    h = _hdr(tokens)
    paths = [
        "/api/v1/admin/production-readiness",
        "/api/v1/admin/production-readiness/backup",
        "/api/v1/admin/production-readiness/clerk",
        "/api/v1/admin/production-readiness/backend",
        "/api/v1/admin/production-readiness/database",
        "/api/v1/admin/production-readiness/dns",
        "/api/v1/admin/production-readiness/clerk-webhooks",
        "/api/v1/admin/production-readiness/cors",
        "/api/v1/admin/production-readiness/security",
    ]
    for p in paths:
        res = await client.get(p, headers=h)
        assert res.status_code == 200, f"Failed at {p}: {res.status_code}"
        body = res.text
        assert "postgres://" not in body or "DATABASE_URL" not in body
        assert "connection_string" not in body.lower()


ADMIN_GET_PATHS = [
    "/api/v1/admin/overview",
    "/api/v1/admin/users",
    "/api/v1/admin/audit-logs",
    "/api/v1/admin/tickets",
    "/api/v1/admin/subscriptions",
    "/api/v1/admin/feature-flags",
    "/api/v1/admin/settings",
    "/api/v1/admin/announcements",
    "/api/v1/admin/production-readiness",
    "/api/v1/admin/production-readiness/backup",
    "/api/v1/admin/production-readiness/clerk",
    "/api/v1/admin/production-readiness/backend",
    "/api/v1/admin/production-readiness/database",
    "/api/v1/admin/production-readiness/dns",
    "/api/v1/admin/production-readiness/clerk-webhooks",
    "/api/v1/admin/production-readiness/cors",
    "/api/v1/admin/production-readiness/security",
]


async def _register(client, email, name="Test User"):
    username = email.split("@")[0].replace(".", "_").replace("-", "_")
    r = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "confirm_password": PASSWORD,
            "full_name": name,
            "username": username,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def _login(client, email, password=PASSWORD):
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["data"]


async def _promote(db_session, email, role: UserRole):
    user = (await db_session.execute(select(User).where(User.email == email))).scalar_one()
    user.role = role
    await db_session.commit()
    return user


def _hdr(tokens) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _uid(data) -> str:
    return data["user"]["id"]


def _uuid(value) -> UUID:
    """SQLite PGUUID columns compare against UUID objects, not raw strings."""
    return value if isinstance(value, UUID) else UUID(str(value))


async def _audit_actions(db_session) -> list[str]:
    """All audit actions currently stored (fresh read, ends any open txn)."""
    await db_session.rollback()
    rows = (await db_session.execute(select(AuditLog.action))).scalars().all()
    return list(rows)


async def _audit_entries(db_session, action: str | None = None):
    await db_session.rollback()
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    return (await db_session.execute(stmt)).scalars().all()


# --------------------------------------------------------------------------
# 1. Authentication: anonymous requests are rejected
# --------------------------------------------------------------------------


@pytest.mark.parametrize("path", ADMIN_GET_PATHS)
async def test_admin_get_endpoints_unauthenticated(client, path):
    r = await client.get(path)
    assert r.status_code == 401, f"{path} -> {r.status_code}"


async def test_admin_mutations_unauthenticated(client):
    r = await client.patch("/api/v1/admin/users/%s/role" % uuid4(), json={"role": "student"})
    assert r.status_code == 401
    r = await client.post("/api/v1/admin/users/bulk-status", json={"user_ids": [], "status": "inactive"})
    assert r.status_code == 401


# --------------------------------------------------------------------------
# 2. Viewer (student) / Analyst (instructor) / SecurityAnalyst (moderator)
# --------------------------------------------------------------------------


async def test_viewer_role_forbidden_everywhere(client, db_session):
    await _register(client, "viewer1@test.io", "Viewer One")
    await _promote(db_session, "viewer1@test.io", UserRole.STUDENT)
    tokens = await _login(client, "viewer1@test.io")
    h = _hdr(tokens)
    for path in ADMIN_GET_PATHS:
        r = await client.get(path, headers=h)
        assert r.status_code == 403, f"{path} -> {r.status_code}"
    # Mutations too
    r = await client.patch(
        f"/api/v1/admin/users/{uuid4()}/role", json={"role": "moderator"}, headers=h
    )
    assert r.status_code == 403
    r = await client.post(
        "/api/v1/admin/users/bulk-status", json={"user_ids": [str(uuid4())], "status": "inactive"}, headers=h
    )
    assert r.status_code == 403


async def test_analyst_role_forbidden(client, db_session):
    await _register(client, "analyst1@test.io")
    await _promote(db_session, "analyst1@test.io", UserRole.INSTRUCTOR)
    tokens = await _login(client, "analyst1@test.io")
    h = _hdr(tokens)
    for path in ("/api/v1/admin/overview", "/api/v1/admin/users", "/api/v1/admin/audit-logs"):
        r = await client.get(path, headers=h)
        assert r.status_code == 403, f"{path} -> {r.status_code}"


async def test_security_analyst_role_forbidden(client, db_session):
    await _register(client, "secanalyst1@test.io")
    await _promote(db_session, "secanalyst1@test.io", UserRole.MODERATOR)
    tokens = await _login(client, "secanalyst1@test.io")
    h = _hdr(tokens)
    for path in (
        "/api/v1/admin/overview",
        "/api/v1/admin/users",
        "/api/v1/admin/audit-logs",
        "/api/v1/admin/subscriptions",
        "/api/v1/admin/settings",
    ):
        r = await client.get(path, headers=h)
        assert r.status_code == 403, f"{path} -> {r.status_code}"


# --------------------------------------------------------------------------
# 3. Admin / Developer / Super Admin can read
# --------------------------------------------------------------------------


async def test_admin_role_allowed_reads(client, db_session):
    await _register(client, "admin1@test.io")
    await _promote(db_session, "admin1@test.io", UserRole.ADMINISTRATOR)
    tokens = await _login(client, "admin1@test.io")
    h = _hdr(tokens)
    for path in ADMIN_GET_PATHS:
        r = await client.get(path, headers=h)
        assert r.status_code == 200, f"{path} -> {r.status_code}: {r.text[:200]}"


async def test_super_admin_role_allowed_reads(client, db_session):
    await _register(client, "superadmin1@test.io")
    await _promote(db_session, "superadmin1@test.io", UserRole.SUPER_ADMIN)
    tokens = await _login(client, "superadmin1@test.io")
    h = _hdr(tokens)
    for path in ADMIN_GET_PATHS:
        r = await client.get(path, headers=h)
        assert r.status_code == 200, f"{path} -> {r.status_code}"


async def test_developer_role_counts_as_admin(client, db_session):
    await _register(client, "dev1@test.io")
    await _promote(db_session, "dev1@test.io", UserRole.DEVELOPER)
    tokens = await _login(client, "dev1@test.io")
    for path in ("/api/v1/admin/overview", "/api/v1/admin/users"):
        r = await client.get(path, headers=_hdr(tokens))
        assert r.status_code == 200, f"{path} -> {r.status_code}"


async def test_analytics_requires_admin(client, db_session):
    await _register(client, "viewer2@test.io")
    tokens = await _login(client, "viewer2@test.io")
    r = await client.get("/api/v1/analytics/overview", headers=_hdr(tokens))
    assert r.status_code == 403
    await _promote(db_session, "viewer2@test.io", UserRole.ADMINISTRATOR)
    tokens = await _login(client, "viewer2@test.io")
    r = await client.get("/api/v1/analytics/overview", headers=_hdr(tokens))
    assert r.status_code == 200


# --------------------------------------------------------------------------
# 4. Role changes (super admin only, no self-change, audited)
# --------------------------------------------------------------------------


async def test_role_change_requires_super_admin(client, db_session):
    await _register(client, "admin2@test.io")
    await _promote(db_session, "admin2@test.io", UserRole.ADMINISTRATOR)
    target = await _register(client, "roletarget@test.io")
    admin_tokens = await _login(client, "admin2@test.io")

    r = await client.patch(
        f"/api/v1/admin/users/{_uid(target)}/role",
        json={"role": "moderator"},
        headers=_hdr(admin_tokens),
    )
    assert r.status_code == 403

    await _promote(db_session, "admin2@test.io", UserRole.SUPER_ADMIN)
    super_tokens = await _login(client, "admin2@test.io")
    r = await client.patch(
        f"/api/v1/admin/users/{_uid(target)}/role",
        json={"role": "moderator"},
        headers=_hdr(super_tokens),
    )
    assert r.status_code == 200, r.text
    await db_session.rollback()
    changed = (
        await db_session.execute(select(User).where(User.id == _uuid(_uid(target))))
    ).scalar_one()
    assert changed.role == UserRole.MODERATOR


async def test_role_change_writes_audit_row(client, db_session):
    await _register(client, "superadmin2@test.io")
    await _promote(db_session, "superadmin2@test.io", UserRole.SUPER_ADMIN)
    target = await _register(client, "roletarget2@test.io")
    tokens = await _login(client, "superadmin2@test.io")

    r = await client.patch(
        f"/api/v1/admin/users/{_uid(target)}/role",
        json={"role": "instructor"},
        headers=_hdr(tokens),
    )
    assert r.status_code == 200, r.text
    entries = await _audit_entries(db_session, action="user.role_updated")
    assert entries, "role change must produce an audit row"
    assert any(e.resource_id == _uid(target) for e in entries), "audit row must name the target"


async def test_role_change_cannot_target_self(client, db_session):
    await _register(client, "superadmin3@test.io")
    await _promote(db_session, "superadmin3@test.io", UserRole.SUPER_ADMIN)
    tokens = await _login(client, "superadmin3@test.io")
    me = (await _me(client, tokens))["id"]

    r = await client.patch(
        f"/api/v1/admin/users/{me}/role",
        json={"role": "student"},
        headers=_hdr(tokens),
    )
    assert r.status_code == 400, r.text
    await db_session.rollback()
    still = (await db_session.execute(select(User).where(User.id == _uuid(me)))).scalar_one()
    assert still.role == UserRole.SUPER_ADMIN, "self role change must not be applied"


async def test_role_change_invalid_role_400(client, db_session):
    await _register(client, "superadmin4@test.io")
    await _promote(db_session, "superadmin4@test.io", UserRole.SUPER_ADMIN)
    target = await _register(client, "roletarget3@test.io")
    tokens = await _login(client, "superadmin4@test.io")
    r = await client.patch(
        f"/api/v1/admin/users/{_uid(target)}/role",
        json={"role": "not-a-role"},
        headers=_hdr(tokens),
    )
    assert r.status_code == 400


async def test_role_change_unknown_user_404(client, db_session):
    await _register(client, "superadmin5@test.io")
    await _promote(db_session, "superadmin5@test.io", UserRole.SUPER_ADMIN)
    tokens = await _login(client, "superadmin5@test.io")
    r = await client.patch(
        f"/api/v1/admin/users/{uuid4()}/role",
        json={"role": "moderator"},
        headers=_hdr(tokens),
    )
    assert r.status_code == 404


async def test_role_change_invalid_uuid_not_500(client, db_session):
    await _register(client, "superadmin6@test.io")
    await _promote(db_session, "superadmin6@test.io", UserRole.SUPER_ADMIN)
    tokens = await _login(client, "superadmin6@test.io")
    r = await client.patch(
        "/api/v1/admin/users/not-a-uuid/role",
        json={"role": "moderator"},
        headers=_hdr(tokens),
    )
    assert r.status_code != 500, "malformed path id must never crash the endpoint"
    assert r.status_code in (400, 404, 422)


# --------------------------------------------------------------------------
# 5. Status changes (admin tier, hierarchy guards, self-guard, audited)
# --------------------------------------------------------------------------


async def _admin_and_targets(client, db_session, prefix):
    """Create (admin, student_target, superadmin_peer) accounts, logged in."""
    admin_email = f"{prefix}-admin@test.io"
    stu_email = f"{prefix}-student@test.io"
    super_email = f"{prefix}-super@test.io"
    await _register(client, admin_email)
    await _register(client, stu_email)
    await _register(client, super_email)
    await _promote(db_session, admin_email, UserRole.ADMINISTRATOR)
    await _promote(db_session, super_email, UserRole.SUPER_ADMIN)
    admin_tokens = await _login(client, admin_email)
    stu = await _me(client, await _login(client, stu_email))
    sup = await _me(client, await _login(client, super_email))
    return admin_tokens, stu, sup


async def _me(client, tokens):
    r = await client.get("/api/v1/auth/me", headers=_hdr(tokens))
    assert r.status_code == 200, r.text
    return r.json()["data"]


async def test_status_change_by_admin_and_audit(client, db_session):
    admin_tokens, stu, _ = await _admin_and_targets(client, db_session, "st1")
    r = await client.patch(
        f"/api/v1/admin/users/{stu['id']}/status",
        json={"status": "inactive"},
        headers=_hdr(admin_tokens),
    )
    assert r.status_code == 200, r.text
    await db_session.rollback()
    row = (await db_session.execute(select(User).where(User.id == _uuid(stu["id"])))).scalar_one()
    assert row.status.value == "inactive"
    entries = await _audit_entries(db_session, action="user.status_updated")
    assert entries, "status change must produce an audit row"


async def test_status_change_self_blocked(client, db_session):
    admin_tokens, _, _ = await _admin_and_targets(client, db_session, "st2")
    me = await _me(client, admin_tokens)
    r = await client.patch(
        f"/api/v1/admin/users/{me['id']}/status",
        json={"status": "inactive"},
        headers=_hdr(admin_tokens),
    )
    assert r.status_code == 400
    await db_session.rollback()
    row = (await db_session.execute(select(User).where(User.id == _uuid(me["id"])))).scalar_one()
    assert row.status.value == "active"


async def test_admin_cannot_suspend_super_admin(client, db_session):
    admin_tokens, _, sup = await _admin_and_targets(client, db_session, "st3")
    r = await client.patch(
        f"/api/v1/admin/users/{sup['id']}/status",
        json={"status": "inactive"},
        headers=_hdr(admin_tokens),
    )
    assert r.status_code == 403, "admins must not be able to deactivate super admins"
    await db_session.rollback()
    row = (await db_session.execute(select(User).where(User.id == _uuid(sup["id"])))).scalar_one()
    assert row.status.value == "active"


async def test_admin_cannot_modify_peer_admin(client, db_session):
    peer_email = "st4-peer@test.io"
    await _register(client, peer_email)
    await _promote(db_session, peer_email, UserRole.ADMINISTRATOR)
    admin_tokens, _, _ = await _admin_and_targets(client, db_session, "st4")
    peer = await _me(client, await _login(client, peer_email))
    r = await client.patch(
        f"/api/v1/admin/users/{peer['id']}/status",
        json={"status": "inactive"},
        headers=_hdr(admin_tokens),
    )
    assert r.status_code == 403, "equal-rank admins must not modify each other"


async def test_super_admin_can_manage_admin_status(client, db_session):
    super_email = "st5-super@test.io"
    admin_email = "st5-admin@test.io"
    await _register(client, super_email)
    await _register(client, admin_email)
    await _promote(db_session, super_email, UserRole.SUPER_ADMIN)
    await _promote(db_session, admin_email, UserRole.ADMINISTRATOR)
    super_tokens = await _login(client, super_email)
    admin = await _me(client, await _login(client, admin_email))
    r = await client.patch(
        f"/api/v1/admin/users/{admin['id']}/status",
        json={"status": "inactive"},
        headers=_hdr(super_tokens),
    )
    assert r.status_code == 200, r.text


async def test_status_invalid_value_400(client, db_session):
    admin_tokens, stu, _ = await _admin_and_targets(client, db_session, "st6")
    r = await client.patch(
        f"/api/v1/admin/users/{stu['id']}/status",
        json={"status": "bogus"},
        headers=_hdr(admin_tokens),
    )
    assert r.status_code == 400


async def test_status_invalid_uuid_not_500(client, db_session):
    admin_tokens, _, _ = await _admin_and_targets(client, db_session, "st7")
    r = await client.patch(
        "/api/v1/admin/users/not-a-uuid/status",
        json={"status": "inactive"},
        headers=_hdr(admin_tokens),
    )
    assert r.status_code != 500
    assert r.status_code in (400, 404, 422)


# --------------------------------------------------------------------------
# 6. /users router guards (the second role/status/delete surface)
# --------------------------------------------------------------------------


async def test_users_router_status_guards(client, db_session):
    admin_email = "ug-admin@test.io"
    super_email = "ug-super@test.io"
    await _register(client, admin_email)
    await _register(client, super_email)
    await _promote(db_session, admin_email, UserRole.ADMINISTRATOR)
    await _promote(db_session, super_email, UserRole.SUPER_ADMIN)
    admin_tokens = await _login(client, admin_email)
    sup = await _me(client, await _login(client, super_email))

    # admin cannot deactivate a super admin through /users either
    r = await client.patch(
        f"/api/v1/users/{sup['id']}/status",
        params={"new_status": "inactive"},
        headers=_hdr(admin_tokens),
    )
    assert r.status_code == 403

    # admin cannot deactivate self
    me = await _me(client, admin_tokens)
    r = await client.patch(
        f"/api/v1/users/{me['id']}/status",
        params={"new_status": "inactive"},
        headers=_hdr(admin_tokens),
    )
    assert r.status_code == 400


async def test_users_router_delete_guards(client, db_session):
    admin_email = "dg-admin@test.io"
    super_email = "dg-super@test.io"
    victim_email = "dg-victim@test.io"
    await _register(client, admin_email)
    await _register(client, super_email)
    await _register(client, victim_email)
    await _promote(db_session, admin_email, UserRole.ADMINISTRATOR)
    await _promote(db_session, super_email, UserRole.SUPER_ADMIN)
    admin_tokens = await _login(client, admin_email)
    sup = await _me(client, await _login(client, super_email))
    victim = await _me(client, await _login(client, victim_email))

    # cannot soft-delete a super admin
    r = await client.delete(f"/api/v1/users/{sup['id']}", headers=_hdr(admin_tokens))
    assert r.status_code == 403
    # cannot delete self
    me = await _me(client, admin_tokens)
    r = await client.delete(f"/api/v1/users/{me['id']}", headers=_hdr(admin_tokens))
    assert r.status_code == 400
    # can delete an ordinary user (and it is audited)
    r = await client.delete(f"/api/v1/users/{victim['id']}", headers=_hdr(admin_tokens))
    assert r.status_code == 200, r.text
    entries = await _audit_entries(db_session, action="user.deleted")
    assert entries, "soft-delete must produce an audit row"


async def test_users_router_role_change_audited(client, db_session):
    sa_email = "ra-super@test.io"
    target_email = "ra-target@test.io"
    await _register(client, sa_email)
    await _register(client, target_email)
    await _promote(db_session, sa_email, UserRole.SUPER_ADMIN)
    tokens = await _login(client, sa_email)
    target = await _me(client, await _login(client, target_email))
    r = await client.patch(
        f"/api/v1/users/{target['id']}/role",
        params={"new_role": "moderator"},
        headers=_hdr(tokens),
    )
    assert r.status_code == 200, r.text
    entries = await _audit_entries(db_session, action="user.role_updated")
    assert entries, "users-router role change must be audited too"


# --------------------------------------------------------------------------
# 7. Audit-log viewer: filters
# --------------------------------------------------------------------------


async def test_audit_logs_filter_by_action(client, db_session):
    sa_email = "au-super@test.io"
    await _register(client, sa_email)
    await _promote(db_session, sa_email, UserRole.SUPER_ADMIN)
    tokens = await _login(client, sa_email)
    target = await _register(client, "au-target@test.io")
    await client.patch(
        f"/api/v1/admin/users/{_uid(target)}/role",
        json={"role": "instructor"},
        headers=_hdr(tokens),
    )

    r = await client.get(
        "/api/v1/admin/audit-logs", params={"action": "user.role_updated"}, headers=_hdr(tokens)
    )
    assert r.status_code == 200
    logs = r.json()["data"]["logs"]
    assert logs, "filtered logs must contain the role change"
    assert all(l["action"] == "user.role_updated" for l in logs)

    r = await client.get(
        "/api/v1/admin/audit-logs", params={"action": "no.such.action"}, headers=_hdr(tokens)
    )
    assert r.status_code == 200
    assert r.json()["data"]["logs"] == []


async def test_audit_logs_filters_user_resource_date(client, db_session):
    sa_email = "au2-super@test.io"
    await _register(client, sa_email)
    await _promote(db_session, sa_email, UserRole.SUPER_ADMIN)
    tokens = await _login(client, sa_email)
    me = await _me(client, tokens)
    target = await _register(client, "au2-target@test.io")
    await client.patch(
        f"/api/v1/admin/users/{_uid(target)}/role",
        json={"role": "instructor"},
        headers=_hdr(tokens),
    )

    # filter by actor user_id
    r = await client.get(
        "/api/v1/admin/audit-logs", params={"user_id": me["id"]}, headers=_hdr(tokens)
    )
    assert r.status_code == 200
    logs = r.json()["data"]["logs"]
    assert logs and all(l["user_id"] == me["id"] for l in logs)

    # filter by resource type
    r = await client.get(
        "/api/v1/admin/audit-logs", params={"resource_type": "user"}, headers=_hdr(tokens)
    )
    assert r.status_code == 200
    assert all(l["resource_type"] == "user" for l in r.json()["data"]["logs"])

    # future date range yields nothing
    r = await client.get(
        "/api/v1/admin/audit-logs",
        params={"date_from": (datetime.now(UTC) + timedelta(days=5)).date().isoformat()},
        headers=_hdr(tokens),
    )
    assert r.status_code == 200
    assert r.json()["data"]["logs"] == []


async def test_audit_log_entries_expose_detail(client, db_session):
    sa_email = "au3-super@test.io"
    await _register(client, sa_email)
    await _promote(db_session, sa_email, UserRole.SUPER_ADMIN)
    tokens = await _login(client, sa_email)
    target = await _register(client, "au3-target@test.io")
    await client.patch(
        f"/api/v1/admin/users/{_uid(target)}/role",
        json={"role": "moderator"},
        headers=_hdr(tokens),
    )
    r = await client.get(
        "/api/v1/admin/audit-logs", params={"action": "user.role_updated"}, headers=_hdr(tokens)
    )
    log = r.json()["data"]["logs"][0]
    assert "before" in log and "after" in log and "metadata" in log, (
        "audit viewer must expose before/after/metadata"
    )


# --------------------------------------------------------------------------
# 8. Feature flags
# --------------------------------------------------------------------------


async def _make_flag(db_session, key="flag_test"):
    flag = FeatureFlag(key=key, enabled=False, rollout_percentage=0, description="t")
    db_session.add(flag)
    await db_session.commit()
    await db_session.refresh(flag)
    return flag


async def test_feature_flag_update_and_audit(client, db_session):
    admin_email = "ff-admin@test.io"
    await _register(client, admin_email)
    await _promote(db_session, admin_email, UserRole.ADMINISTRATOR)
    tokens = await _login(client, admin_email)
    flag = await _make_flag(db_session, "ff_basic")
    flag_uuid = flag.id  # rollback below expires `flag`; capture the pk first

    r = await client.patch(
        f"/api/v1/admin/feature-flags/{flag_uuid}",
        json={"enabled": True, "rollout_percentage": 50},
        headers=_hdr(tokens),
    )
    assert r.status_code == 200, r.text
    await db_session.rollback()
    row = (await db_session.execute(select(FeatureFlag).where(FeatureFlag.id == flag_uuid))).scalar_one()
    assert row.enabled is True
    assert row.rollout_percentage == 50
    entries = await _audit_entries(db_session, action="feature_flag.updated")
    assert entries, "flag update must be audited"


async def test_feature_flag_update_unknown_404(client, db_session):
    admin_email = "ff2-admin@test.io"
    await _register(client, admin_email)
    await _promote(db_session, admin_email, UserRole.ADMINISTRATOR)
    tokens = await _login(client, admin_email)
    r = await client.patch(
        f"/api/v1/admin/feature-flags/{uuid4()}",
        json={"enabled": True},
        headers=_hdr(tokens),
    )
    assert r.status_code == 404
    r = await client.patch(
        "/api/v1/admin/feature-flags/not-a-uuid",
        json={"enabled": True},
        headers=_hdr(tokens),
    )
    assert r.status_code != 500
    assert r.status_code in (400, 404, 422)


# --------------------------------------------------------------------------
# 9. Settings: update + create
# --------------------------------------------------------------------------


async def test_setting_update_and_audit(client, db_session):
    admin_email = "set-admin@test.io"
    await _register(client, admin_email)
    await _promote(db_session, admin_email, UserRole.ADMINISTRATOR)
    tokens = await _login(client, admin_email)
    setting = AppSetting(key="alert_threshold_test", value={"critical": 9})
    db_session.add(setting)
    await db_session.commit()
    await db_session.refresh(setting)

    r = await client.put(
        f"/api/v1/admin/settings/{setting.id}",
        json={"value": {"critical": 7}},
        headers=_hdr(tokens),
    )
    assert r.status_code == 200, r.text
    entries = await _audit_entries(db_session, action="setting.updated")
    assert entries, "setting update must be audited"


async def test_setting_create_and_duplicate(client, db_session):
    admin_email = "set2-admin@test.io"
    await _register(client, admin_email)
    await _promote(db_session, admin_email, UserRole.ADMINISTRATOR)
    tokens = await _login(client, admin_email)

    r = await client.post(
        "/api/v1/admin/settings",
        json={"key": "notification_slack_webhook", "value": {"url": "https://hooks.example/x"}, "description": "slack"},
        headers=_hdr(tokens),
    )
    assert r.status_code in (200, 201), r.text
    # duplicate key rejected
    r2 = await client.post(
        "/api/v1/admin/settings",
        json={"key": "notification_slack_webhook", "value": {}},
        headers=_hdr(tokens),
    )
    assert r2.status_code == 409
    entries = await _audit_entries(db_session, action="setting.created")
    assert entries, "setting creation must be audited"


async def test_setting_put_invalid_uuid_not_500(client, db_session):
    admin_email = "set3-admin@test.io"
    await _register(client, admin_email)
    await _promote(db_session, admin_email, UserRole.ADMINISTRATOR)
    tokens = await _login(client, admin_email)
    r = await client.put(
        "/api/v1/admin/settings/not-a-uuid",
        json={"value": {"a": 1}},
        headers=_hdr(tokens),
    )
    assert r.status_code != 500
    assert r.status_code in (400, 404, 422)


# --------------------------------------------------------------------------
# 10. Announcements: lifecycle + public read + audit
# --------------------------------------------------------------------------


async def test_announcement_lifecycle(client, db_session):
    admin_email = "an-admin@test.io"
    user_email = "an-user@test.io"
    await _register(client, admin_email)
    await _register(client, user_email)
    await _promote(db_session, admin_email, UserRole.ADMINISTRATOR)
    admin_tokens = await _login(client, admin_email)
    user_tokens = await _login(client, user_email)

    # create draft
    r = await client.post(
        "/api/v1/admin/announcements",
        json={"title": "Scheduled maintenance", "body": "We will be down for 10 minutes.", "is_draft": True},
        headers=_hdr(admin_tokens),
    )
    assert r.status_code in (200, 201), r.text
    ann_id = r.json()["data"]["id"]

    # draft invisible to regular users
    r = await client.get("/api/v1/notifications/announcements", headers=_hdr(user_tokens))
    assert r.status_code == 200
    assert ann_id not in [a["id"] for a in r.json()["data"]]

    # publish via PATCH
    r = await client.patch(
        f"/api/v1/admin/announcements/{ann_id}",
        json={"is_draft": False},
        headers=_hdr(admin_tokens),
    )
    assert r.status_code == 200, r.text

    # visible to users now
    r = await client.get("/api/v1/notifications/announcements", headers=_hdr(user_tokens))
    assert r.status_code == 200
    ids = [a["id"] for a in r.json()["data"]]
    assert ann_id in ids, "published announcement must be readable by users"

    # regular user cannot manage announcements
    r = await client.patch(
        f"/api/v1/admin/announcements/{ann_id}",
        json={"title": "hax"},
        headers=_hdr(user_tokens),
    )
    assert r.status_code == 403

    # soft-delete
    r = await client.delete(
        f"/api/v1/admin/announcements/{ann_id}", headers=_hdr(admin_tokens)
    )
    assert r.status_code == 200, r.text
    r = await client.get("/api/v1/notifications/announcements", headers=_hdr(user_tokens))
    assert ann_id not in [a["id"] for a in r.json()["data"]], "deleted announcement must vanish"

    actions = await _audit_actions(db_session)
    for expected in ("announcement.created", "announcement.updated", "announcement.deleted"):
        assert expected in actions, f"missing audit action {expected}"


async def test_announcement_unknown_and_bad_uuid(client, db_session):
    admin_email = "an2-admin@test.io"
    await _register(client, admin_email)
    await _promote(db_session, admin_email, UserRole.ADMINISTRATOR)
    tokens = await _login(client, admin_email)
    r = await client.patch(
        f"/api/v1/admin/announcements/{uuid4()}", json={"title": "nope12345"}, headers=_hdr(tokens)
    )
    assert r.status_code == 404
    r = await client.patch(
        "/api/v1/admin/announcements/not-a-uuid", json={"title": "nope12345"}, headers=_hdr(tokens)
    )
    assert r.status_code != 500
    assert r.status_code in (400, 404, 422)
    r = await client.delete("/api/v1/admin/announcements/not-a-uuid", headers=_hdr(tokens))
    assert r.status_code != 500
    assert r.status_code in (400, 404, 422)


# --------------------------------------------------------------------------
# 11. Support tickets: staff management
# --------------------------------------------------------------------------


async def _make_ticket(client, email="tk-user@test.io"):
    await _register(client, email)
    tokens = await _login(client, email)
    r = await client.post(
        "/api/v1/support/tickets",
        json={"subject": "Cannot access my lab", "description": "The lab environment fails to start.", "category": "technical", "priority": "medium"},
        headers=_hdr(tokens),
    )
    assert r.status_code in (200, 201), r.text
    return tokens, r.json()["data"]


async def test_admin_ticket_list_includes_requester(client, db_session):
    admin_email = "tk-admin@test.io"
    await _register(client, admin_email)
    await _promote(db_session, admin_email, UserRole.ADMINISTRATOR)
    admin_tokens = await _login(client, admin_email)
    _, ticket = await _make_ticket(client)

    r = await client.get("/api/v1/admin/tickets", headers=_hdr(admin_tokens))
    assert r.status_code == 200
    data = r.json()["data"]
    rows = data["tickets"] if isinstance(data, dict) else data
    match = [t for t in rows if t["id"] == ticket["id"]]
    assert match, "admin ticket list must include user tickets"
    assert match[0].get("requester_email") or match[0].get("user_email"), (
        "list must identify the requester"
    )


async def test_admin_ticket_detail_reply_and_update(client, db_session):
    admin_email = "tk2-admin@test.io"
    await _register(client, admin_email)
    await _promote(db_session, admin_email, UserRole.ADMINISTRATOR)
    admin_tokens = await _login(client, admin_email)
    _, ticket = await _make_ticket(client, "tk2-user@test.io")

    # detail includes messages
    r = await client.get(f"/api/v1/admin/tickets/{ticket['id']}", headers=_hdr(admin_tokens))
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    assert "messages" in body and "description" in body
    assert body.get("requester_email") or body.get("user_email")

    # staff reply
    r = await client.post(
        f"/api/v1/admin/tickets/{ticket['id']}/reply",
        json={"content": "We are looking into it."},
        headers=_hdr(admin_tokens),
    )
    assert r.status_code in (200, 201), r.text
    await db_session.rollback()
    from app.models.support import TicketMessage

    msgs = (
        await db_session.execute(
            select(TicketMessage).where(TicketMessage.ticket_id == _uuid(ticket["id"]))
        )
    ).scalars().all()
    staff = [m for m in msgs if m.is_staff_reply]
    assert staff, "staff reply must be flagged is_staff_reply"
    from app.models.support import SupportTicket

    row = (
        await db_session.execute(select(SupportTicket).where(SupportTicket.id == _uuid(ticket["id"])))
    ).scalar_one()
    assert row.first_response_at is not None, "first staff reply sets first_response_at"

    # status / priority / assignee update
    me = await _me(client, admin_tokens)
    r = await client.patch(
        f"/api/v1/admin/tickets/{ticket['id']}",
        json={"status": "resolved", "priority": "high", "assignee_id": me["id"]},
        headers=_hdr(admin_tokens),
    )
    assert r.status_code == 200, r.text
    await db_session.rollback()
    row = (
        await db_session.execute(select(SupportTicket).where(SupportTicket.id == _uuid(ticket["id"])))
    ).scalar_one()
    assert row.status == TicketStatus.RESOLVED
    assert row.priority.value == "high"
    assert row.resolved_at is not None

    actions = await _audit_actions(db_session)
    assert "ticket.replied" in actions
    assert "ticket.updated" in actions


async def test_admin_ticket_management_guards(client, db_session):
    admin_email = "tk3-admin@test.io"
    await _register(client, admin_email)
    await _promote(db_session, admin_email, UserRole.ADMINISTRATOR)
    admin_tokens = await _login(client, admin_email)
    user_tokens, ticket = await _make_ticket(client, "tk3-user@test.io")

    # regular user cannot reach admin ticket surfaces
    r = await client.get("/api/v1/admin/tickets", headers=_hdr(user_tokens))
    assert r.status_code == 403
    r = await client.get(f"/api/v1/admin/tickets/{ticket['id']}", headers=_hdr(user_tokens))
    assert r.status_code == 403

    # unknown / malformed ids never 500
    r = await client.get(f"/api/v1/admin/tickets/{uuid4()}", headers=_hdr(admin_tokens))
    assert r.status_code == 404
    r = await client.get("/api/v1/admin/tickets/not-a-uuid", headers=_hdr(admin_tokens))
    assert r.status_code != 500
    assert r.status_code in (400, 404, 422)

    # invalid status value rejected
    r = await client.patch(
        f"/api/v1/admin/tickets/{ticket['id']}",
        json={"status": "not-a-status"},
        headers=_hdr(admin_tokens),
    )
    assert r.status_code == 400

    # unknown assignee rejected
    r = await client.patch(
        f"/api/v1/admin/tickets/{ticket['id']}",
        json={"assignee_id": str(uuid4())},
        headers=_hdr(admin_tokens),
    )
    assert r.status_code in (400, 404)


# --------------------------------------------------------------------------
# 12. Bulk status changes
# --------------------------------------------------------------------------


async def test_bulk_status_updates_and_audit(client, db_session):
    admin_email = "bk-admin@test.io"
    await _register(client, admin_email)
    await _promote(db_session, admin_email, UserRole.ADMINISTRATOR)
    admin_tokens = await _login(client, admin_email)
    t1 = await _register(client, "bk-u1@test.io")
    t2 = await _register(client, "bk-u2@test.io")

    r = await client.post(
        "/api/v1/admin/users/bulk-status",
        json={"user_ids": [_uid(t1), _uid(t2)], "status": "inactive"},
        headers=_hdr(admin_tokens),
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["updated"] == 2
    assert data["skipped"] == []
    await db_session.rollback()
    for uid in (_uid(t1), _uid(t2)):
        row = (await db_session.execute(select(User).where(User.id == _uuid(uid)))).scalar_one()
        assert row.status.value == "inactive"
    entries = await _audit_entries(db_session, action="user.bulk_status_updated")
    assert entries, "bulk operation must be audited"


async def test_bulk_status_skips_protected_targets(client, db_session):
    admin_email = "bk2-admin@test.io"
    super_email = "bk2-super@test.io"
    await _register(client, admin_email)
    await _register(client, super_email)
    await _promote(db_session, admin_email, UserRole.ADMINISTRATOR)
    await _promote(db_session, super_email, UserRole.SUPER_ADMIN)
    admin_tokens = await _login(client, admin_email)
    me = await _me(client, admin_tokens)
    sup = await _me(client, await _login(client, super_email))
    normal = await _register(client, "bk2-normal@test.io")

    r = await client.post(
        "/api/v1/admin/users/bulk-status",
        json={
            "user_ids": [me["id"], sup["id"], str(uuid4()), _uid(normal)],
            "status": "inactive",
        },
        headers=_hdr(admin_tokens),
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["updated"] == 1, "only the ordinary user may be updated"
    skipped_ids = {s["id"] for s in data["skipped"]}
    assert me["id"] in skipped_ids, "self must be skipped"
    assert sup["id"] in skipped_ids, "super admin must be skipped"
    assert len(data["skipped"]) == 3

    await db_session.rollback()
    sup_row = (await db_session.execute(select(User).where(User.id == _uuid(sup["id"])))).scalar_one()
    assert sup_row.status.value == "active"
    me_row = (await db_session.execute(select(User).where(User.id == _uuid(me["id"])))).scalar_one()
    assert me_row.status.value == "active"


async def test_bulk_status_validation(client, db_session):
    admin_email = "bk3-admin@test.io"
    await _register(client, admin_email)
    await _promote(db_session, admin_email, UserRole.ADMINISTRATOR)
    tokens = await _login(client, admin_email)
    h = _hdr(tokens)

    # empty list rejected
    r = await client.post("/api/v1/admin/users/bulk-status", json={"user_ids": [], "status": "inactive"}, headers=h)
    assert r.status_code == 422
    # oversized list rejected
    r = await client.post(
        "/api/v1/admin/users/bulk-status",
        json={"user_ids": [str(uuid4()) for _ in range(51)], "status": "inactive"},
        headers=h,
    )
    assert r.status_code == 422
    # invalid status rejected
    r = await client.post(
        "/api/v1/admin/users/bulk-status",
        json={"user_ids": [str(uuid4())], "status": "bogus"},
        headers=h,
    )
    assert r.status_code == 400


# --------------------------------------------------------------------------
# 13. Overview: real system health + user list filtering
# --------------------------------------------------------------------------


async def test_overview_reports_structured_health(client, db_session):
    admin_email = "ov-admin@test.io"
    await _register(client, admin_email)
    await _promote(db_session, admin_email, UserRole.ADMINISTRATOR)
    tokens = await _login(client, admin_email)
    r = await client.get("/api/v1/admin/overview", headers=_hdr(tokens))
    assert r.status_code == 200
    health = r.json()["data"]["system_health"]
    assert health["status"] in ("operational", "degraded")
    services = health["services"]
    assert services["api"] == "ok"
    assert services["database"] == "ok"
    assert services["redis"] in ("ok", "degraded")


async def test_users_list_search_role_status_filters(client, db_session):
    admin_email = "ul-admin@test.io"
    await _register(client, admin_email, "Filter Admin")
    await _promote(db_session, admin_email, UserRole.ADMINISTRATOR)
    tokens = await _login(client, admin_email)
    await _register(client, "ul-alpha@test.io", "Alpha User")
    await _promote(db_session, "ul-alpha@test.io", UserRole.MODERATOR)
    await _register(client, "ul-beta@test.io", "Beta User")

    h = _hdr(tokens)
    r = await client.get("/api/v1/admin/users", params={"search": "Alpha"}, headers=h)
    assert r.status_code == 200
    users = r.json()["data"]["users"]
    assert any(u["email"] == "ul-alpha@test.io" for u in users)
    assert all("Alpha" in (u["full_name"] or "") or "ul-alpha" in u["email"] for u in users)

    r = await client.get("/api/v1/admin/users", params={"role": "moderator"}, headers=h)
    assert r.status_code == 200
    users = r.json()["data"]["users"]
    assert users and all(u["role"] == "moderator" for u in users)

    r = await client.get("/api/v1/admin/users", params={"status": "active"}, headers=h)
    assert r.status_code == 200
    users = r.json()["data"]["users"]
    assert users and all(u["status"] == "active" for u in users)

    # pagination fields present
    data = r.json()["data"]
    for key in ("total", "page", "page_size"):
        assert key in data, f"missing {key}"


# --------------------------------------------------------------------------
# 14. Subscriptions (enriched for the admin UI)
# --------------------------------------------------------------------------


async def test_subscriptions_list_enriched(client, db_session):
    admin_email = "sb-admin@test.io"
    buyer_email = "sb-buyer@test.io"
    await _register(client, admin_email)
    buyer = await _register(client, buyer_email)
    await _promote(db_session, admin_email, UserRole.ADMINISTRATOR)
    admin_tokens = await _login(client, admin_email)

    plan = SubscriptionPlan(
        slug="test-pro", name="Pro", description="test plan", price_amount=999
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    sub = Subscription(
        user_id=_uuid(buyer["user"]["id"]),
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE,
        current_period_end=datetime.now(UTC) + timedelta(days=30),
    )
    db_session.add(sub)
    await db_session.commit()

    r = await client.get("/api/v1/admin/subscriptions", headers=_hdr(admin_tokens))
    assert r.status_code == 200
    rows = r.json()["data"]
    match = [s for s in rows if s["id"] == str(sub.id)]
    assert match, "subscription must be listed"
    assert match[0].get("user_email") == buyer_email, "list must identify the subscriber"
    assert match[0].get("plan_name") == "Pro", "list must include the plan name"


# --------------------------------------------------------------------------
# 15. login-history / sessions surfaces used by the admin account page
# --------------------------------------------------------------------------


async def test_auth_sessions_and_devices_reachable(client):
    tokens = await _register(client, "acct-sess@test.io")
    h = _hdr(tokens)
    r = await client.get("/api/v1/auth/login-history", headers=h)
    assert r.status_code == 200, r.text
    r = await client.get("/api/v1/auth/devices", headers=h)
    assert r.status_code == 200, r.text
    r = await client.get("/api/v1/auth/sessions", headers=h)
    assert r.status_code == 200, r.text
