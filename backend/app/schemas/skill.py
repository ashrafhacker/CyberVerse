from uuid import UUID

from pydantic import BaseModel


class SkillBranchOut(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str
    icon: str
    max_level: int
    prerequisites: list
    display_order: int


class UserSkillOut(BaseModel):
    branch_id: UUID
    slug: str
    name: str
    level: int
    max_level: int
    xp_in_branch: int
    activities: int


class SkillProgressOut(BaseModel):
    total_xp: int
    level: int
    rank: str
    next_rank: str | None = None
    next_rank_level: int | None = None
    branches: list[UserSkillOut]
