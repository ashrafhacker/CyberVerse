"""
media.py — Authenticated media file serving endpoint.

Serves video (MP4) and PDF files stored in the assets/courses directory.
All files require a valid JWT token. Free-preview lessons are accessible
to any authenticated user; all others require course enrollment.

Asset layout:
    assets/courses/
        ceh-v12/pdfs/                CEH v12 Module01-20.pdf
        ceh-v12-specialization/
            ethical-hacking-fundamentals/  …/*.mp4
            system-and-network-security/   …/*.mp4
            advanced-cybersecurity/        …/*.mp4
        hands-on-hacking/
            burp-suite/    …/*.mp4
            http-debugger/ …/*.mp4
"""

from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User

router = APIRouter()

# Root directory of all course assets — two levels above this file:
#   backend/app/api/v1/endpoints/media.py  →  project root  →  assets/courses
_PROJECT_ROOT = Path(__file__).resolve().parents[6]
ASSETS_ROOT = _PROJECT_ROOT / "assets" / "courses"

ALLOWED_EXTENSIONS = {".mp4", ".pdf"}


def _resolve_asset(relative_path: str) -> Path:
    """
    Safely resolve a relative asset path inside ASSETS_ROOT.
    Raises 400 if the path tries to escape the assets directory.
    """
    try:
        resolved = (ASSETS_ROOT / relative_path).resolve()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")

    if not resolved.is_relative_to(ASSETS_ROOT):
        raise HTTPException(status_code=403, detail="Path traversal not allowed")

    if resolved.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not allowed")

    if not resolved.exists():
        raise HTTPException(status_code=404, detail="Asset not found")

    return resolved


@router.get(
    "/stream",
    summary="Stream a course video or PDF",
    responses={
        200: {"description": "File streamed successfully"},
        403: {"description": "Not enrolled or not authenticated"},
        404: {"description": "Asset not found"},
    },
)
async def stream_asset(
    path: str = Query(..., description="Relative path inside assets/courses/"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """
    Stream a course asset file.

    - Authenticated users can access free-preview lessons.
    - Full access requires course enrollment (or premium / admin role).
    """
    resolved = _resolve_asset(path)

    # Admins / developers / super_admin bypass enrollment check
    bypass_roles = {"administrator", "developer", "super_admin", "instructor"}
    if current_user.role not in bypass_roles:
        # TODO: check enrollment in DB — for now allow all authenticated users
        # while the enrollment model is being built out.
        pass

    media_type_map = {
        ".mp4": "video/mp4",
        ".pdf": "application/pdf",
    }
    media_type = media_type_map.get(resolved.suffix.lower(), "application/octet-stream")

    return FileResponse(
        path=str(resolved),
        media_type=media_type,
        filename=resolved.name,
        headers={
            # Allow range requests so browsers can seek in videos
            "Accept-Ranges": "bytes",
            "Cache-Control": "private, max-age=3600",
        },
    )


@router.get(
    "/manifest",
    summary="List all available course assets",
)
async def list_assets(
    course: str | None = Query(None, description="Filter by course slug"),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Return a structured manifest of all available course assets.
    Optionally filter by course slug (e.g. 'ceh-v12', 'hands-on-hacking').
    """
    results: list[dict] = []

    search_root = ASSETS_ROOT
    if course:
        search_root = ASSETS_ROOT / course
        if not search_root.exists():
            raise HTTPException(status_code=404, detail=f"Course '{course}' not found")

    for f in sorted(search_root.rglob("*")):
        if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS:
            relative = f.relative_to(ASSETS_ROOT).as_posix()
            parts = relative.split("/")
            results.append(
                {
                    "path": relative,
                    "filename": f.name,
                    "course": parts[0] if parts else "",
                    "module": parts[1] if len(parts) > 2 else "",
                    "type": "video" if f.suffix.lower() == ".mp4" else "pdf",
                    "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                }
            )

    return {
        "total": len(results),
        "assets": results,
    }
