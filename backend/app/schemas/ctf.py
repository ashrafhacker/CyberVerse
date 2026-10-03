from uuid import UUID

from pydantic import BaseModel, Field


class ChallengeCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=120)
    title: str = Field(min_length=2, max_length=200)
    story: str = Field(min_length=10)
    category: str = "general"
    difficulty: str = "beginner"
    points: int = Field(default=100, ge=1)
    hint: str | None = None
    flag: str = Field(min_length=1, description="Plaintext flag; stored only as a SHA-256 hash")
    flag_hint_prefix: str | None = Field(default=None, description="Public prefix, e.g. CVX{}")
    tags: list[str] = Field(default_factory=list)
    is_active: bool = False


class ChallengeOut(BaseModel):
    id: UUID
    slug: str
    title: str
    story: str
    category: str
    difficulty: str
    points: int
    hint: str | None = None
    flag_hint_prefix: str | None = None
    tags: list[str]
    solved: bool = False


class FlagSubmit(BaseModel):
    flag: str = Field(min_length=1, max_length=200)


class SubmissionOut(BaseModel):
    correct: bool
    points_earned: int
    attempts: int
    first_blood: bool
    message: str
