from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_roles
from app.core.database import get_db
from app.models.library import LibraryResource, ResourceType
from app.models.user import User, UserRole
from app.schemas.base import APIResponse, PaginatedResponse
from app.schemas.library import ResourceCreate

router = APIRouter()

MANAGER_ROLES = {UserRole.MODERATOR, UserRole.ADMINISTRATOR, UserRole.DEVELOPER, UserRole.SUPER_ADMIN}


def _serialize(r: LibraryResource) -> dict:
    return {
        "id": str(r.id),
        "title": r.title,
        "description": r.description,
        "category": r.category,
        "resource_type": r.resource_type.value if hasattr(r.resource_type, "value") else r.resource_type,
        "difficulty": r.difficulty.value if hasattr(r.difficulty, "value") else r.difficulty,
        "provider": r.provider,
        "url": r.url,
        "file_path": r.file_path,
        "duration_minutes": r.duration_minutes,
        "tags": r.tags,
        "is_free": r.is_free,
        "is_published": r.is_published,
        "view_count": r.view_count,
    }


@router.get("/", response_model=APIResponse[PaginatedResponse], summary="Browse the learning library")
async def list_resources(
    _: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    search: str = Query(None),
    category: str = Query(None),
    resource_type: str = Query(None),
    difficulty: str = Query(None),
):
    filters = [LibraryResource.is_published.is_(True)]
    if search:
        filters.append(
            or_(
                LibraryResource.title.ilike(f"%{search}%"),
                LibraryResource.description.ilike(f"%{search}%"),
                func.array_to_string(LibraryResource.tags, ",").ilike(f"%{search}%"),
            )
        )
    if category:
        filters.append(LibraryResource.category == category)
    if resource_type:
        filters.append(LibraryResource.resource_type == resource_type)
    if difficulty:
        filters.append(LibraryResource.difficulty == difficulty)

    total = await db.scalar(select(func.count()).select_from(LibraryResource).where(*filters))
    result = await db.execute(
        select(LibraryResource)
        .where(*filters)
        .order_by(LibraryResource.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_serialize(r) for r in result.scalars().all()]
    data = PaginatedResponse.create(items, total or 0, page, page_size)
    return APIResponse[PaginatedResponse](data=data)


@router.get("/filters", response_model=APIResponse[dict], summary="Available library filter values")
async def list_filters(db: AsyncSession = Depends(get_db)):
    categories = set(await db.scalars(select(LibraryResource.category).distinct()))
    return APIResponse[dict](
        data={
            "categories": sorted(c for c in categories if c),
            "resource_types": [t.value for t in ResourceType],
            "difficulties": ["beginner", "intermediate", "advanced", "expert"],
        }
    )


@router.get("/{resource_id}", response_model=APIResponse[dict], summary="Get a library resource")
async def get_resource(
    resource_id: UUID,
    _: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(LibraryResource).where(LibraryResource.id == resource_id))
    resource = result.scalar_one_or_none()
    if not resource or not resource.is_published:
        raise HTTPException(status_code=404, detail="Resource not found")

    resource.view_count += 1
    await db.commit()
    return APIResponse[dict](data=_serialize(resource))


@router.post("/", response_model=APIResponse[dict], status_code=201, summary="Add a library resource")
async def create_resource(
    payload: ResourceCreate,
    _: User = Depends(require_roles(MANAGER_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    if not payload.url and not payload.file_path:
        raise HTTPException(status_code=422, detail="Provide either url or file_path")

    resource = LibraryResource(**payload.model_dump())
    db.add(resource)
    await db.commit()
    await db.refresh(resource)
    return APIResponse[dict](data=_serialize(resource))
