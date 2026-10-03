from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SkillBranch(Base):
    """A branch of the CyberVerse skill tree (spec: Networking, Linux, ...)."""

    __tablename__ = "skill_branches"
    __table_args__ = (Index("ix_skill_branches_slug", "slug", unique=True),)

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    icon: Mapped[str] = mapped_column(String(80), default="layers", nullable=False)
    max_level: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    prerequisites: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class UserSkill(Base):
    """A learner's level within a skill-tree branch."""

    __tablename__ = "user_skills"
    __table_args__ = (
        UniqueConstraint("user_id", "branch_id", name="uq_user_skill_user_branch"),
        Index("ix_user_skills_user_id", "user_id"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    branch_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("skill_branches.id", ondelete="CASCADE"), nullable=False
    )
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    xp_in_branch: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    activities: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    meta_data: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
