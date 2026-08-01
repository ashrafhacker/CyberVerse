from typing import List, Optional

from pydantic import Field

from app.models.course import DifficultyLevel
from app.models.library import ResourceType
from app.schemas.base import BaseSchema


class ResourceCreate(BaseSchema):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    category: str = Field(min_length=2, max_length=50)
    resource_type: ResourceType = ResourceType.ARTICLE
    difficulty: DifficultyLevel = DifficultyLevel.BEGINNER
    provider: Optional[str] = Field(None, max_length=100)
    url: Optional[str] = Field(None, max_length=500)
    file_path: Optional[str] = Field(None, max_length=500)
    duration_minutes: Optional[int] = Field(None, ge=1, le=100000)
    tags: List[str] = Field(default_factory=list)
    is_free: bool = True
    is_published: bool = False
