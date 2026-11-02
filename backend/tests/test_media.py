"""Regression tests for the authenticated course media endpoint.

Guards the authorization contract of the R2 media storage work:
path-traversal rejection, extension allowlisting, fail-closed behavior when
a mapped course is missing from the database, enrollment enforcement,
deny-by-default for unmapped assets (every role), privileged access for
mapped assets only, authorization-aware manifest filtering for local and
R2 listings, manifest authentication, and the local-file fallback used
when Cloudflare R2 is not configured.
"""

from uuid import UUID

import pytest
from sqlalchemy import select

from app.models.course import Course
from app.models.progress import Enrollment
from app.models.user import User, UserRole

# ceh-v12/ maps to ceh-v12-official-modules via _ASSET_COURSE_SLUGS
MAPPED_PDF = "ceh-v12/pdfs/module01.pdf"
MAPPED_COURSE_SLUG = "ceh-v12-official-modules"
# No course mapping: denied for every role (no public preview policy)
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
            # Non-browser client: opt in to body tokens for Bearer auth.
            "include_tokens": True,
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["access_token"]
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


async def _set_role(db_session, user_id: str, role: UserRole) -> None:
    result = await db_session.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one()
    user.role = role
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


async def test_manifest_lists_local_assets_for_enrolled_user(
    client, db_session, tmp_path, monkeypatch
):
    monkeypatch.setattr("app.api.v1.endpoints.media.ASSETS_ROOT", tmp_path)
    asset = tmp_path / "ceh-v12" / "pdfs" / "module01.pdf"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"%PDF-1.4 listed")
    (tmp_path / "ceh-v12" / "pdfs" / "ignore.exe").write_bytes(b"MZ")

    course = await _seed_course(db_session)
    headers, user_id = await _register(client, "manifest@test.io", "manifest_test")
    await _enroll(db_session, user_id, course)

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


async def test_manifest_hides_assets_from_unenrolled_user(
    client, db_session, tmp_path, monkeypatch
):
    """Unenrolled users must not see filenames, paths, or counts of course assets."""
    monkeypatch.setattr("app.api.v1.endpoints.media.ASSETS_ROOT", tmp_path)
    asset = tmp_path / "ceh-v12" / "pdfs" / "module01.pdf"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"%PDF-1.4 hidden")
    (tmp_path / "random-course").mkdir()
    (tmp_path / "random-course" / "clip.mp4").write_bytes(b"\x00mp4")

    await _seed_course(db_session)
    headers, _ = await _register(client, "manifest_hidden@test.io", "manifest_hidden")

    response = await client.get("/api/v1/media/manifest", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 0
    assert payload["assets"] == []
    assert "module01.pdf" not in response.text
    assert "clip.mp4" not in response.text


async def test_manifest_shows_mapped_assets_to_privileged_user(
    client, db_session, tmp_path, monkeypatch
):
    """Privileged roles see mapped assets of real courses without enrollment,
    but unmapped assets stay hidden."""
    monkeypatch.setattr("app.api.v1.endpoints.media.ASSETS_ROOT", tmp_path)
    asset = tmp_path / "ceh-v12" / "pdfs" / "module01.pdf"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"%PDF-1.4 instructor")
    (tmp_path / "random-course").mkdir()
    (tmp_path / "random-course" / "clip.mp4").write_bytes(b"\x00mp4")

    await _seed_course(db_session)
    headers, user_id = await _register(client, "manifest_instr@test.io", "manifest_instr")
    await _set_role(db_session, user_id, UserRole.INSTRUCTOR)

    response = await client.get("/api/v1/media/manifest", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    paths = [a["path"] for a in payload["assets"]]
    assert "ceh-v12/pdfs/module01.pdf" in paths
    assert "random-course/clip.mp4" not in paths
    assert "clip.mp4" not in response.text


async def test_manifest_never_lists_unseeded_course_assets(
    client, db_session, tmp_path, monkeypatch
):
    """Mapped assets whose course record is missing stay hidden for everyone."""
    monkeypatch.setattr("app.api.v1.endpoints.media.ASSETS_ROOT", tmp_path)
    asset = tmp_path / "ceh-v12" / "pdfs" / "module01.pdf"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"%PDF-1.4 unseeded")

    # Course deliberately not seeded.
    headers, user_id = await _register(client, "manifest_nocourse@test.io", "manifest_nocourse")
    await _set_role(db_session, user_id, UserRole.SUPER_ADMIN)

    response = await client.get("/api/v1/media/manifest", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 0
    assert "module01.pdf" not in response.text


async def test_stream_unmapped_asset_forbidden_for_enrolled_user(client, db_session):
    course = await _seed_course(db_session)
    headers, user_id = await _register(client, "enrolled_unmapped@test.io", "enrolled_unmapped")
    await _enroll(db_session, user_id, course)
    response = await client.get(
        "/api/v1/media/stream", params={"path": UNMAPPED_MP4}, headers=headers
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    ("role", "role_name"),
    [
        (UserRole.INSTRUCTOR, "instructor"),
        (UserRole.ADMINISTRATOR, "administrator"),
        (UserRole.DEVELOPER, "developer"),
        (UserRole.SUPER_ADMIN, "super_admin"),
    ],
)
async def test_stream_unmapped_asset_denied_for_privileged_roles(
    client, db_session, tmp_path, monkeypatch, role, role_name
):
    """Unmapped assets are denied with 403 for every role, privileged or not."""
    monkeypatch.setattr("app.api.v1.endpoints.media.ASSETS_ROOT", tmp_path)
    asset = tmp_path / "random-course" / "clip.mp4"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"\x00mp4 exists on disk")

    await _seed_course(db_session)
    headers, user_id = await _register(client, f"{role_name}_unmapped@test.io", f"{role_name}_u")
    await _set_role(db_session, user_id, role)

    response = await client.get(
        "/api/v1/media/stream", params={"path": UNMAPPED_MP4}, headers=headers
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied"


async def test_stream_privileged_role_still_needs_course_record(client, db_session):
    """A privileged role must not bypass the course lookup: missing course = 404."""
    headers, user_id = await _register(client, "admin_nocourse@test.io", "admin_nocourse")
    await _set_role(db_session, user_id, UserRole.ADMINISTRATOR)

    response = await client.get(
        "/api/v1/media/stream", params={"path": MAPPED_PDF}, headers=headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Course not found"


# ---------------------------------------------------------------------------
# Manifest: R2 listings follow the same policy as local listings
# ---------------------------------------------------------------------------


class _FakePaginator:
    def __init__(self, objects):
        self._objects = objects

    def paginate(self, Bucket, Prefix):  # noqa: N803 - boto3 paginator signature
        yield {"Contents": [obj for obj in self._objects if obj["Key"].startswith(Prefix)]}


class _FakeR2Client:
    def __init__(self, objects):
        self._objects = objects

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        return _FakePaginator(self._objects)


def _fake_r2(monkeypatch, objects):
    monkeypatch.setattr("app.api.v1.endpoints.media.get_r2_client", lambda: _FakeR2Client(objects))
    monkeypatch.setattr("app.api.v1.endpoints.media.get_r2_bucket", lambda: "test-bucket")


_R2_OBJECTS = [
    {"Key": "ceh-v12/pdfs/r2module.pdf", "Size": 1024},
    {"Key": "random-course/clip.mp4", "Size": 2048},
    {"Key": "ceh-v12-specialization/notes.pdf", "Size": 512},
]


async def test_manifest_r2_listings_filtered_for_unenrolled_user(
    client, db_session, tmp_path, monkeypatch
):
    monkeypatch.setattr("app.api.v1.endpoints.media.ASSETS_ROOT", tmp_path / "empty")
    _fake_r2(monkeypatch, _R2_OBJECTS)

    await _seed_course(db_session)
    headers, _ = await _register(client, "r2_hidden@test.io", "r2_hidden")

    response = await client.get("/api/v1/media/manifest", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 0
    assert payload["assets"] == []
    for key in ("r2module.pdf", "clip.mp4", "notes.pdf"):
        assert key not in response.text


async def test_manifest_r2_listings_filtered_for_enrolled_user(
    client, db_session, tmp_path, monkeypatch
):
    monkeypatch.setattr("app.api.v1.endpoints.media.ASSETS_ROOT", tmp_path / "empty")
    _fake_r2(monkeypatch, _R2_OBJECTS)

    course = await _seed_course(db_session)
    headers, user_id = await _register(client, "r2_enrolled@test.io", "r2_enrolled")
    await _enroll(db_session, user_id, course)

    response = await client.get("/api/v1/media/manifest", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    paths = [a["path"] for a in payload["assets"]]
    # Enrolled in ceh-v12-official-modules only: unmapped and unseeded-course
    # assets must not leak, even when they live in R2.
    assert paths == ["ceh-v12/pdfs/r2module.pdf"]
    assert payload["assets"][0]["storage"] == "r2"
    assert "clip.mp4" not in response.text
    assert "notes.pdf" not in response.text


async def test_manifest_r2_listings_for_privileged_user(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.api.v1.endpoints.media.ASSETS_ROOT", tmp_path / "empty")
    _fake_r2(monkeypatch, _R2_OBJECTS)

    await _seed_course(db_session)
    headers, user_id = await _register(client, "r2_instr@test.io", "r2_instr")
    await _set_role(db_session, user_id, UserRole.INSTRUCTOR)

    response = await client.get("/api/v1/media/manifest", headers=headers)
    assert response.status_code == 200
    paths = [a["path"] for a in response.json()["assets"]]
    assert paths == ["ceh-v12/pdfs/r2module.pdf"]
    assert "clip.mp4" not in response.text


# ---------------------------------------------------------------------------
# R2 error handling: no local fallback on authorization/network errors
# ---------------------------------------------------------------------------


class _RaisingR2Client:
    def __init__(self, exc):
        self._exc = exc

    def head_object(self, Bucket, Key):  # noqa: N803 - boto3 signature
        raise self._exc


def _fake_r2_raising(monkeypatch, exc):
    monkeypatch.setattr("app.api.v1.endpoints.media.get_r2_client", lambda: _RaisingR2Client(exc))
    monkeypatch.setattr("app.api.v1.endpoints.media.get_r2_bucket", lambda: "test-bucket")


async def _enrolled_with_local_file(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.api.v1.endpoints.media.ASSETS_ROOT", tmp_path)
    asset = tmp_path / "ceh-v12" / "pdfs" / "module01.pdf"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"%PDF-1.4 local copy")
    course = await _seed_course(db_session)
    headers, user_id = await _register(client, "r2err@test.io", "r2err_test")
    await _enroll(db_session, user_id, course)
    return headers


async def test_stream_r2_access_denied_never_falls_back_to_local(
    client, db_session, tmp_path, monkeypatch
):
    from botocore.exceptions import ClientError

    headers = await _enrolled_with_local_file(client, db_session, tmp_path, monkeypatch)
    _fake_r2_raising(
        monkeypatch,
        ClientError(
            {
                "Error": {"Code": "AccessDenied", "Message": "denied"},
                "ResponseMetadata": {"HTTPStatusCode": 403},
            },
            "HeadObject",
        ),
    )

    response = await client.get(
        "/api/v1/media/stream", params={"path": MAPPED_PDF}, headers=headers
    )
    assert response.status_code == 502
    assert b"%PDF-1.4 local copy" not in response.content


async def test_stream_r2_network_error_never_falls_back_to_local(
    client, db_session, tmp_path, monkeypatch
):
    from botocore.exceptions import EndpointConnectionError

    headers = await _enrolled_with_local_file(client, db_session, tmp_path, monkeypatch)
    _fake_r2_raising(
        monkeypatch,
        EndpointConnectionError(endpoint_url="https://r2.example.com"),
    )

    response = await client.get(
        "/api/v1/media/stream", params={"path": MAPPED_PDF}, headers=headers
    )
    assert response.status_code == 502
    assert b"%PDF-1.4 local copy" not in response.content


async def test_stream_r2_missing_object_falls_back_to_local(
    client, db_session, tmp_path, monkeypatch
):
    from botocore.exceptions import ClientError

    headers = await _enrolled_with_local_file(client, db_session, tmp_path, monkeypatch)
    _fake_r2_raising(
        monkeypatch,
        ClientError(
            {
                "Error": {"Code": "NoSuchKey", "Message": "gone"},
                "ResponseMetadata": {"HTTPStatusCode": 404},
            },
            "HeadObject",
        ),
    )

    response = await client.get(
        "/api/v1/media/stream", params={"path": MAPPED_PDF}, headers=headers
    )
    assert response.status_code == 200
    assert response.content == b"%PDF-1.4 local copy"


# ---------------------------------------------------------------------------
# Repository layout
# ---------------------------------------------------------------------------


def test_media_root_resolves_from_repo_layout():
    from pathlib import Path

    import app.api.v1.endpoints.media as media

    expected = Path(__file__).resolve().parents[2] / "assets" / "courses"
    assert media.ASSETS_ROOT == expected
