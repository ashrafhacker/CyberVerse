from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ToolCategoryOut(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str
    display_order: int


class ToolCreate(BaseModel):
    category_slug: str
    slug: str = Field(min_length=2, max_length=160)
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=10)
    license_name: str = Field(min_length=2, max_length=120)
    open_source: bool = False
    free_tier: bool = True
    supported_os: list[str] = Field(default_factory=list)
    difficulty: str = Field(default="beginner", max_length=40)
    official_url: str | None = None
    docs_url: str | None = None
    tutorial_url: str | None = None
    lab_reference: str | None = None
    tags: list[str] = Field(default_factory=list)
    extra_metadata: dict[str, Any] = Field(default_factory=dict)
    is_published: bool = False
    verified_at: datetime | None = None


class ToolOut(BaseModel):
    id: UUID
    category_slug: str
    slug: str
    name: str
    description: str
    license_name: str
    open_source: bool
    free_tier: bool
    supported_os: list[str]
    difficulty: str
    official_url: str | None = None
    docs_url: str | None = None
    tutorial_url: str | None = None
    lab_reference: str | None = None
    tags: list[str]
    is_published: bool
    view_count: int
    verified_at: datetime | None = None
