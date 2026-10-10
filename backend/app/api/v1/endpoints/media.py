"""Authenticated course media serving with Cloudflare R2 and local fallback.

R2 object keys mirror paths under assets/courses/, e.g.
  ceh-v12/pdfs/module01.pdf
  hands-on-hacking/burp-suite/lesson01.mp4

Private objects are never made public: this endpoint checks course access first,
then redirects to a short-lived, signed R2 GET URL. If an object has not yet been
migrated, the existing local file is served as a compatibility fallback.
"""
from pathlib import Path, PurePosixPath

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_user, get_db
from app.core.config import get_settings
from app.core.r2_storage import get_r2_bucket, get_r2_client, is_missing_object_error
from app.models.user import User

router = APIRouter()
_PROJECT_ROOT = Path(__file__).resolve().parents[6]
ASSETS_ROOT = _PROJECT_ROOT / "assets" / "courses"
ALLOWED_EXTENSIONS = {".mp4", ".pdf"}
_ASSET_COURSE_SLUGS = {
    "ceh-v12": "ceh-v12-official-modules",
    "ceh-v12-specialization": "ceh-v12-system-and-network-security",
    "hands-on-hacking/burp-suite": "burp-suite-live-practical",
    "hands-on-hacking/http-debugger": "http-debugger-pro",
}


def _normalize_asset_path(relative_path: str) -> str:
    """Normalize a URL path and reject traversal, absolute paths, and bad extensions."""
    if not relative_path or "\\" in relative_path or "\x00" in relative_path:
        raise HTTPException(status_code=400, detail="Invalid asset path")
    path = PurePosixPath(relative_path)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise HTTPException(status_code=400, detail="Path traversal not allowed")
    key = path.as_posix()
    if Path(key).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not allowed")
    return key


def _local_path(key: str) -> Path | None:
    root = ASSETS_ROOT.resolve()
    candidate = (root / key).resolve()
    if not candidate.is_relative_to(root):
        raise HTTPException(status_code=403, detail="Path traversal not allowed")
    return candidate if candidate.is_file() else None


async def _authorize_course_asset(key: str, current_user: User | None, db: AsyncSession) -> None:
    bypass_roles = {"administrator", "developer", "super_admin", "instructor"}
    if current_user is not None and current_user.role in bypass_roles:
        return
    parts = key.split("/")
    asset_root = "/".join(parts[:2])
    course_slug = _ASSET_COURSE_SLUGS.get(asset_root) or _ASSET_COURSE_SLUGS.get(parts[0])
    # Assets without a configured course mapping retain the existing preview behavior.
    if not course_slug:
        if current_user is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        return
    from app.models.course import Course
    from app.models.progress import Enrollment

    course_result = await db.execute(select(Course.id).where(Course.slug == course_slug))
    course_id = course_result.scalar_one_or_none()
    if course_id is None:
        # Fail closed: mapped course assets must never bypass authorization
        # just because the course has not been seeded in the database.
        raise HTTPException(status_code=404, detail="Course not found")
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required for this course")
    enrolled = await db.execute(select(Enrollment.id).where(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id == course_id,
    ))
    if enrolled.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="Enroll in this course to access its materials")


def _presign_get(key: str) -> str:
    client = get_r2_client()
    bucket = get_r2_bucket()
    if client is None or not bucket:
        raise RuntimeError("Cloudflare R2 is not configured")
    settings = get_settings()
    suffix = Path(key).suffix.lower()
    content_type = "video/mp4" if suffix == ".mp4" else "application/pdf"
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key, "ResponseContentType": content_type, "ResponseContentDisposition": "inline"},
        ExpiresIn=settings.SIGNED_URL_EXPIRE_SECONDS,
    )


@router.get("/stream", summary="Stream an authorized course video or PDF")
async def stream_asset(
    path: str = Query(..., description="Relative object path inside assets/courses/"),
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    key = _normalize_asset_path(path)
    await _authorize_course_asset(key, current_user, db)

    client, bucket = get_r2_client(), get_r2_bucket()
    if client is not None and bucket:
        try:
            await run_in_threadpool(client.head_object, Bucket=bucket, Key=key)
            url = await run_in_threadpool(_presign_get, key)
            return RedirectResponse(url, status_code=307, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
        except Exception as exc:
            if not is_missing_object_error(exc):
                # Do not silently fall back on auth, credential, or network errors.
                if isinstance(exc, (ClientError, BotoCoreError)):
                    raise HTTPException(status_code=502, detail="Private media storage is temporarily unavailable") from exc
                raise

    local_file = _local_path(key)
    if local_file is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    media_type = "video/mp4" if local_file.suffix.lower() == ".mp4" else "application/pdf"
    return FileResponse(
        path=str(local_file), media_type=media_type, filename=None,
        headers={
            "Accept-Ranges": "bytes", "Cache-Control": "private, max-age=300",
            "Content-Disposition": "inline", "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
            "Content-Security-Policy": "default-src 'self' blob: data: 'unsafe-inline'; img-src 'self' data: blob:; frame-ancestors 'self'",
        },
    )


@router.get("/manifest", summary="List available course media paths")
async def list_assets(
    course: str | None = Query(None, description="Optional folder prefix to filter"),
    current_user: User | None = Depends(get_optional_user),
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    raw_prefix = course or ""
    if (
        "\\" in raw_prefix
        or "\x00" in raw_prefix
        or PurePosixPath(raw_prefix).is_absolute()
        or any(part in {".", ".."} for part in PurePosixPath(raw_prefix).parts)
    ):
        raise HTTPException(status_code=400, detail="Invalid course path")
    prefix = raw_prefix.strip("/")
    assets: dict[str, dict] = {}

    # Include local assets until the migration to R2 is complete.
    search_root = (ASSETS_ROOT / prefix).resolve() if prefix else ASSETS_ROOT.resolve()
    root = ASSETS_ROOT.resolve()
    if search_root.is_relative_to(root) and search_root.exists():
        for file in search_root.rglob("*"):
            if file.is_file() and file.suffix.lower() in ALLOWED_EXTENSIONS:
                key = file.relative_to(root).as_posix()
                parts = key.split("/")
                assets[key] = {"path": key, "filename": file.name, "course": parts[0], "module": parts[1] if len(parts) > 2 else "", "type": "video" if file.suffix.lower() == ".mp4" else "pdf", "size_mb": round(file.stat().st_size / (1024 * 1024), 2), "storage": "local"}

    client, bucket = get_r2_client(), get_r2_bucket()
    if client is not None and bucket:
        def _list_r2():
            paginator = client.get_paginator("list_objects_v2")
            found = {}
            for page in paginator.paginate(Bucket=bucket, Prefix=(prefix + "/") if prefix else ""):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if Path(key).suffix.lower() not in ALLOWED_EXTENSIONS:
                        continue
                    parts = key.split("/")
                    found[key] = {"path": key, "filename": parts[-1], "course": parts[0], "module": parts[1] if len(parts) > 2 else "", "type": "video" if Path(key).suffix.lower() == ".mp4" else "pdf", "size_mb": round(obj.get("Size", 0) / (1024 * 1024), 2), "storage": "r2"}
            return found
        try:
            assets.update(await run_in_threadpool(_list_r2))
        except (ClientError, BotoCoreError) as exc:
            raise HTTPException(status_code=502, detail="Private media storage is temporarily unavailable") from exc

    ordered = [assets[k] for k in sorted(assets)]
    return {"total": len(ordered), "assets": ordered}
