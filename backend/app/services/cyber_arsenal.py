"""
Cyber Arsenal — free/open-source security tools directory.

Only legitimate tools are listed (open source, free, or with a genuine free
tier). All external links point to official project/vendor sites. This service
never resolves or fetches external URLs at runtime — links are editorial data
curated at seed time.
"""

from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tool import Tool, ToolCategory


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


class CyberArsenalError(ValueError):
    pass


class CyberArsenalService:
    @staticmethod
    async def ensure_categories(db: AsyncSession, defaults: list[dict]) -> None:
        count = await db.scalar(select(func.count()).select_from(ToolCategory))
        if count and count > 0:
            return
        for data in defaults:
            db.add(ToolCategory(**data))
        await db.commit()

    @staticmethod
    async def get_category(db: AsyncSession, slug: str) -> ToolCategory:
        result = await db.execute(select(ToolCategory).where(ToolCategory.slug == slug))
        category = result.scalar_one_or_none()
        if not category:
            raise CyberArsenalError(f"Unknown category: {slug}")
        return category

    @staticmethod
    async def list_categories(db: AsyncSession) -> list[ToolCategory]:
        result = await db.execute(
            select(ToolCategory).order_by(ToolCategory.display_order, ToolCategory.name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def list_tools(
        db: AsyncSession,
        page: int,
        page_size: int,
        search: str | None,
        category: str | None,
        license_name: str | None,
        os_name: str | None,
        difficulty: str | None,
        published_only: bool = True,
    ) -> tuple[list[Tool], int]:
        filters = []
        if published_only:
            filters.append(Tool.is_published.is_(True))
        if search:
            filters.append(
                or_(
                    Tool.name.ilike(f"%{search}%"),
                    Tool.description.ilike(f"%{search}%"),
                    func.array_to_string(Tool.tags, ",").ilike(f"%{search}%"),
                )
            )
        if category:
            cat = await CyberArsenalService.get_category(db, category)
            filters.append(Tool.category_id == cat.id)
        if license_name:
            filters.append(Tool.license_name.ilike(f"%{license_name}%"))
        if os_name:
            filters.append(Tool.supported_os.any(os_name))
        if difficulty:
            filters.append(Tool.difficulty == difficulty)

        total = await db.scalar(select(func.count()).select_from(Tool).where(*filters))
        result = await db.execute(
            select(Tool)
            .where(*filters)
            .order_by(Tool.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total or 0

    @staticmethod
    async def filters(db: AsyncSession) -> dict:
        categories = await CyberArsenalService.list_categories(db)
        licenses = set(await db.scalars(select(Tool.license_name).distinct()))
        os_names: set[str] = set()
        rows = await db.scalars(select(Tool.supported_os))
        for row in rows:
            os_names.update(row or [])
        return {
            "categories": [{"slug": c.slug, "name": c.name} for c in categories],
            "licenses": sorted(l for l in licenses if l),
            "os": sorted(os for os in os_names if os),
            "difficulties": ["beginner", "intermediate", "advanced", "expert"],
        }

    @staticmethod
    async def get_tool(db: AsyncSession, tool_id: UUID | None, slug: str | None) -> Tool:
        if tool_id:
            result = await db.execute(select(Tool).where(Tool.id == tool_id))
        elif slug:
            result = await db.execute(select(Tool).where(Tool.slug == slug))
        else:
            raise CyberArsenalError("Tool identifier required")
        tool = result.scalar_one_or_none()
        if not tool or not tool.is_published:
            raise CyberArsenalError("Tool not found")
        return tool

    @staticmethod
    async def create_tool(db: AsyncSession, data: dict) -> Tool:
        category = await CyberArsenalService.get_category(db, data.pop("category_slug"))
        if not data.get("slug"):
            data["slug"] = slugify(data.get("name", ""))
        tool = Tool(category_id=category.id, **data)
        db.add(tool)
        await db.commit()
        await db.refresh(tool)
        return tool
