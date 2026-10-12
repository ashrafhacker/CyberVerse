"""Regression tests for the authenticated course media endpoint.

Guards the authorization contract of the R2 media storage work:
path-traversal rejection, extension allowlisting, fail-closed behavior when
a mapped course is missing from the database, enrollment enforcement,
role bypass, manifest authentication, and the local-file fallback used
when Cloudflare R2 is not configured.
"""

from uuid import UUID

from sqlalchemy import select

from app.models.course import Course
from app.models.progress import Enrollment
from app.models.user import User, UserRole

# ceh-v12/ maps to ceh-v12-official-modules via _ASSET_COURSE_SLUGS
MAPPED_PDF = "ceh-v12/pdfs/module01.pdf"
MAPPED_COURSE_SLUG = "ceh-v12-official-modules"
# No course mapping: auth-only access (preview behavior)
UNMAPPED_MP4 = "random-course/clip.mp4"


async def _register(client, email: str, username: str) -> tuple[dict, str]:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
            "full_name": "Media Tester",
            "username": username,
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    return headers, data["user"]["id"]


async def _seed_course(db_session, slug: str = MAPPED_COURSE_SLUG) -> Course:
    course = Course(
        slug=slug,
        name="Official CEH v12 Modules",
        description="Test course for media authorization tests.",
        short_description="Media test course.",
    )
    db_session.add(course)
    await db_session.commit()
    return course


async def _enroll(db_session, user_id: str, course: Course) -> None:
    # The register payload serializes ids to strings; PGUUID expects uuid.UUID.
    db_session.add(Enrollment(user_id=UUID(user_id), course_id=course.id))
    await db_session.commit()


# ---------------------------------------------------------------------------
# Path normalization (runs before auth; must reject regardless of caller)
# ---------------------------------------------------------------------------


async def test_stream_rejects_dotdot_traversal(client):
    response = await client.get("/api/v1/media/stream", params={"path": "../secrets.pdf"})
    assert response.status_code == 400


async def test_stream_rejects_nested_traversal(client):
    response = await client.get(
        "/api/v1/media/stream", params={"path": "ceh-v12/pdfs/../../../etc/passwd.pdf"}
    )
    assert response.status_code == 400


async def test_stream_rejects_absolute_path(client):
    response = await client.get("/api/v1/media/stream", params={"path": "/etc/shadow.pdf"})
    assert response.status_code == 400


async def test_stream_rejects_backslash(client):
    response = await client.get("/api/v1/media/stream", params={"path": "..\\evil.pdf"})
    assert response.status_code == 400


async def test_stream_rejects_disallowed_extension(client):
    response = await client.get("/api/v1/media/stream", params={"path": "ceh-v12/pdfs/module.exe"})
    assert response.status_code == 400
    assert "not allowed" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Authorization: unmapped vs mapped course assets
# ---------------------------------------------------------------------------


async def test_stream_unmapped_asset_denied_by_default(client):
    """Unmapped assets have no explicit preview policy: deny everyone."""
    response = await client.get("/api/v1/media/stream", params={"path": UNMAPPED_MP4})
    assert response.status_code == 403


async def test_stream_mapped_asset_fails_closed_when_course_not_seeded(client):
    """Mapped assets must never serve when the course is absent from the DB."""
    response = await client.get("/api/v1/media/stream", params={"path": MAPPED_PDF})
    assert response.status_code == 404
    assert response.json()["detail"] == "Course not found"


async def test_stream_mapped_asset_requires_authentication(client, db_session):
    await _seed_course(db_session)
    response = await client.get("/api/v1/media/stream", params={"path": MAPPED_PDF})
    assert response.status_code == 401


async def test_stream_forbidden_without_enrollment(client, db_session):
    await _seed_course(db_session)
    headers, _ = await _register(client, "noenroll@test.io", "noenroll_test")
    response = await client.get(
        "/api/v1/media/stream", params={"path": MAPPED_PDF}, headers=headers
    )
    assert response.status_code == 403
    assert "Enroll" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Local fallback serving (R2 unconfigured in tests -> local file path)
# ---------------------------------------------------------------------------


async def test_stream_enrolled_user_gets_local_file(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.api.v1.endpoints.media.ASSETS_ROOT", tmp_path)
    asset = tmp_path / "ceh-v12" / "pdfs" / "module01.pdf"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"%PDF-1.4 test asset")

    course = await _seed_course(db_session)
    headers, user_id = await _register(client, "enrolled@test.io", "enrolled_test")
    await _enroll(db_session, user_id, course)

    response = await client.get(
        "/api/v1/media/stream", params={"path": MAPPED_PDF}, headers=headers
    )
    assert response.status_code == 200
    assert response.content == b"%PDF-1.4 test asset"
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-disposition"] == "inline"
    assert response.headers["cache-control"].startswith("private")
    assert response.headers["accept-ranges"] == "bytes"


async def test_stream_enrolled_user_missing_local_file_404(
    client, db_session, tmp_path, monkeypatch
):
    monkeypatch.setattr("app.api.v1.endpoints.media.ASSETS_ROOT", tmp_path)
    (tmp_path / "ceh-v12").mkdir()

    course = await _seed_course(db_session)
    headers, user_id = await _register(client, "missing@test.io", "missing_test")
    await _enroll(db_session, user_id, course)

    response = await client.get(
        "/api/v1/media/stream", params={"path": MAPPED_PDF}, headers=headers
    )
    assert response.status_code == 404


async def test_stream_instructor_role_bypasses_enrollment(
    client, db_session, tmp_path, monkeypatch
):
    monkeypatch.setattr("app.api.v1.endpoints.media.ASSETS_ROOT", tmp_path)
    asset = tmp_path / "ceh-v12" / "pdfs" / "module01.pdf"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"%PDF-1.4 instructor")

    await _seed_course(db_session)
    headers, user_id = await _register(client, "instructor@test.io", "instructor_test")
    result = await db_session.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one()
    user.role = UserRole.INSTRUCTOR
    await db_session.commit()

    response = await client.get(
        "/api/v1/media/stream", params={"path": MAPPED_PDF}, headers=headers
    )
    assert response.status_code == 200
    assert response.content == b"%PDF-1.4 instructor"


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


async def test_manifest_requires_authentication(client):
    response = await client.get("/api/v1/media/manifest")
    assert response.status_code == 401


async def test_manifest_rejects_traversal_prefix(client):
    headers, _ = await _register(client, "manifest400@test.io", "manifest400_test")
    response = await client.get(
        "/api/v1/media/manifest", params={"course": "../.."}, headers=headers
    )
    assert response.status_code == 400


async def test_manifest_lists_local_assets_for_authenticated_user(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.api.v1.endpoints.media.ASSETS_ROOT", tmp_path)
    asset = tmp_path / "ceh-v12" / "pdfs" / "module01.pdf"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"%PDF-1.4 listed")
    (tmp_path / "ceh-v12" / "pdfs" / "ignore.exe").write_bytes(b"MZ")

    headers, _ = await _register(client, "manifest@test.io", "manifest_test")
    response = await client.get("/api/v1/media/manifest", headers=headers)
    assert response.status_code == 200
    payload = response.json()  # media endpoints return raw dicts, no envelope
    assert payload["total"] == len(payload["assets"])
    paths = [a["path"] for a in payload["assets"]]
    assert "ceh-v12/pdfs/module01.pdf" in paths
    assert all(not p.endswith(".exe") for p in paths)
    entry = next(a for a in payload["assets"] if a["path"] == "ceh-v12/pdfs/module01.pdf")
    assert entry["storage"] == "local"
    assert entry["type"] == "pdf"


async def test_stream_unmapped_asset_forbidden_for_enrolled_user(client, db_session):
    course = await _seed_course(db_session)
    headers, user_id = await _register(client, "enrolled_unmapped@test.io", "enrolled_unmapped")
    await _enroll(db_session, user_id, course)
    response = await client.get(
        "/api/v1/media/stream", params={"path": UNMAPPED_MP4}, headers=headers
    )
    assert response.status_code == 403


async def test_stream_unmapped_asset_bypasses_course_gate_for_instructor(client, db_session):
    """Instructors are exempt from the course-enrollment gate.

    They clear `_authorize_course_asset` entirely, so a non-existent asset falls
    through to the file resolver and 404s instead of being denied 403.
    """
    await _seed_course(db_session)
    headers, user_id = await _register(client, "instr_unmapped@test.io", "instr_unmapped")
    from sqlalchemy import select
    from app.models.user import User, UserRole
    from uuid import UUID
    result = await db_session.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one()
    user.role = UserRole.INSTRUCTOR
    await db_session.commit()
    response = await client.get(
        "/api/v1/media/stream", params={"path": UNMAPPED_MP4}, headers=headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Asset not found"


async def test_stream_unmapped_asset_bypasses_course_gate_for_admin(client, db_session):
    """Administrators are exempt from the course-enrollment gate (same as above)."""
    await _seed_course(db_session)
    headers, user_id = await _register(client, "admin_unmapped@test.io", "admin_unmapped")
    from sqlalchemy import select
    from app.models.user import User, UserRole
    from uuid import UUID
    result = await db_session.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one()
    user.role = UserRole.ADMINISTRATOR
    await db_session.commit()
    response = await client.get(
        "/api/v1/media/stream", params={"path": UNMAPPED_MP4}, headers=headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Asset not found"
