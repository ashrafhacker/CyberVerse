import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class AchievementCategory(str, enum.Enum):
    LEARNING = "learning"
    MISSION = "mission"
    SOCIAL = "social"
    PROGRESSION = "progression"
    CHALLENGE = "challenge"
    SPECIAL = "special"


class Achievement(Base):
    __tablename__ = "achievements"
    __table_args__ = (
        Index("ix_achievements_slug", "slug", unique=True),
        Index("ix_achievements_category", "category"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[AchievementCategory] = mapped_column(
        SQLEnum(AchievementCategory, native_enum=False),
        default=AchievementCategory.LEARNING,
        nullable=False,
    )

    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rarity: Mapped[str] = mapped_column(String(50), default="common", nullable=False)  # common, rare, epic, legendary

    xp_reward: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coins_reward: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    criteria_type: Mapped[str] = mapped_column(String(50), nullable=False)
    criteria_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    criteria_meta_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_seasonal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    meta_data: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    user_achievements: Mapped[list["UserAchievement"]] = relationship(
        "UserAchievement", back_populates="achievement", cascade="all, delete-orphan"
    )


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    __table_args__ = (
        UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement_unique"),
        Index("ix_user_achievements_user_id", "user_id"),
        Index("ix_user_achievements_achievement_id", "achievement_id"),
        Index("ix_user_achievements_unlocked_at", "unlocked_at"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    achievement_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("achievements.id", ondelete="CASCADE"),
        nullable=False,
    )

    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unlocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    unlocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    meta_data: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="achievements")  # noqa: F821
    achievement: Mapped["Achievement"] = relationship("Achievement", back_populates="user_achievements")


class DailyChallenge(Base):
    __tablename__ = "daily_challenges"
    __table_args__ = (
        Index("ix_daily_challenges_challenge_date", "challenge_date"),
        Index("ix_daily_challenges_is_active", "is_active"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    challenge_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    task_type: Mapped[str] = mapped_column(String(50), nullable=False)  # lesson, quiz, mission, lab, social
    task_requirement: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    task_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    xp_reward: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    coins_reward: Mapped[int] = mapped_column(Integer, default=20, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    meta_data: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class WeeklyChallenge(Base):
    __tablename__ = "weekly_challenges"
    __table_args__ = (
        Index("ix_weekly_challenges_start_date", "start_date"),
        Index("ix_weekly_challenges_is_active", "is_active"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    objectives: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)

    xp_reward: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    coins_reward: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    meta_data: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
