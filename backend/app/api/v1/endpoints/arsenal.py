from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_roles
from app.core.database import get_db
from app.models.tool import Tool
from app.models.user import User, UserRole
from app.schemas.base import APIResponse, PaginatedResponse
from app.schemas.tool import ToolCategoryOut, ToolCreate, ToolOut
from app.services.cyber_arsenal import CyberArsenalError, CyberArsenalService

router = APIRouter()

MANAGER_ROLES = {UserRole.MODERATOR, UserRole.ADMINISTRATOR, UserRole.DEVELOPER, UserRole.SUPER_ADMIN}


def _serialize(t: Tool, category_slug: str | None = None) -> dict:
    return {
        "id": str(t.id),
        "category_slug": category_slug or (t.category.slug if t.category else ""),
        "slug": t.slug,
        "name": t.name,
        "description": t.description,
        "license_name": t.license_name,
        "open_source": t.open_source,
        "free_tier": t.free_tier,
        "supported_os": t.supported_os,
        "difficulty": t.difficulty,
        "official_url": t.official_url,
        "docs_url": t.docs_url,
        "tutorial_url": t.tutorial_url,
        "lab_reference": t.lab_reference,
        "tags": t.tags,
        "is_published": t.is_published,
        "view_count": t.view_count,
        "verified_at": t.verified_at.isoformat() if t.verified_at else None,
    }


@router.get("/categories", response_model=APIResponse[list[ToolCategoryOut]], summary="List tool categories")
async def list_categories(_: CurrentUser, db: AsyncSession = Depends(get_db)):
    categories = await CyberArsenalService.list_categories(db)
    return APIResponse(
        data=[
            ToolCategoryOut.model_validate(
                {"id": c.id, "slug": c.slug, "name": c.name, "description": c.description, "display_order": c.display_order}
            )
            for c in categories
        ]
    )


@router.get("/tools", response_model=APIResponse[PaginatedResponse], summary="Browse the Cyber Arsenal")
async def list_tools(
    _: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    search: str = Query(None),
    category: str = Query(None),
    license_name: str = Query(None),
    os: str = Query(None, description="Operating system slug, e.g. linux/windows/macos"),
    difficulty: str = Query(None),
):
    try:
        items, total = await CyberArsenalService.list_tools(
            db,
            page,
            page_size,
            search,
            category,
            license_name,
            os,
            difficulty,
            published_only=True,
        )
    except CyberArsenalError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    data = PaginatedResponse.create(
        [_serialize(t, t.category.slug if t.category else None) for t in items],
        total,
        page,
        page_size,
    )
    return APIResponse[PaginatedResponse](data=data)


@router.get("/filters", response_model=APIResponse[dict], summary="Arsenal filter values")
async def list_filters(_: CurrentUser, db: AsyncSession = Depends(get_db)):
    return APIResponse[dict](data=await CyberArsenalService.filters(db))


@router.get("/tools/{slug_or_id}", response_model=APIResponse[ToolOut], summary="Get a tool")
async def get_tool(slug_or_id: str, _: CurrentUser, db: AsyncSession = Depends(get_db)):
    try:
        if len(slug_or_id) == 36:
            tool = await CyberArsenalService.get_tool(db, tool_id=UUID(slug_or_id), slug=None)
        else:
            tool = await CyberArsenalService.get_tool(db, tool_id=None, slug=slug_or_id)
    except (CyberArsenalError, ValueError):
        raise HTTPException(status_code=404, detail="Tool not found")

    tool.view_count += 1
    if not tool.verified_at:
        tool.verified_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(tool)
    return APIResponse[ToolOut](data=ToolOut.model_validate(_serialize(tool, tool.category.slug if tool.category else None)))


@router.post("/tools", response_model=APIResponse[ToolOut], status_code=201, summary="Add a tool (curator/admin)")
async def create_tool(
    payload: ToolCreate,
    _: User = Depends(require_roles(MANAGER_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    try:
        tool = await CyberArsenalService.create_tool(db, payload.model_dump())
    except CyberArsenalError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return APIResponse[ToolOut](data=ToolOut.model_validate(_serialize(tool, tool.category.slug if tool.category else None)))
