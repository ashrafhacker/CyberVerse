import enum
from datetime import UTC, datetime
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

from app.core.database import Base, FlexibleArray
from app.models.course import DifficultyLevel


class MissionType(str, enum.Enum):
    STORY = "story"
    PRACTICE = "practice"
    CHALLENGE = "challenge"
    DAILY = "daily"
    WEEKLY = "weekly"
    INSTRUCTOR = "instructor"
    COOP = "coop"


class MissionStatus(str, enum.Enum):
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ObjectiveType(str, enum.Enum):
    READ = "read"
    WATCH = "watch"
    QUIZ = "quiz"
    TERMINAL = "terminal"
    SIMULATION = "simulation"
    INVESTIGATE = "investigate"
    CONFIGURE = "configure"
    ANALYZE = "analyze"
    REPORT = "report"
    CUSTOM = "custom"


class Mission(Base):
    __tablename__ = "missions"
    __table_args__ = (
        Index("ix_missions_slug", "slug", unique=True),
        Index("ix_missions_type", "mission_type"),
        Index("ix_missions_status", "status"),
        Index("ix_missions_difficulty", "difficulty"),
        Index("ix_missions_is_premium", "is_premium"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    mission_type: Mapped[MissionType] = mapped_column(
        SQLEnum(MissionType, native_enum=False),
        default=MissionType.PRACTICE,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    short_description: Mapped[str] = mapped_column(String(500), nullable=False)
    background_story: Mapped[str | None] = mapped_column(Text, nullable=True)

    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    banner_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    difficulty: Mapped[DifficultyLevel] = mapped_column(
        SQLEnum(DifficultyLevel, native_enum=False),
        default=DifficultyLevel.BEGINNER,
        nullable=False,
    )
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    prerequisites: Mapped[list[str]] = mapped_column(FlexibleArray(str), default=list, nullable=False)
    learning_objectives: Mapped[list[str]] = mapped_column(FlexibleArray(str), default=list, nullable=False)
    tags: Mapped[list[str]] = mapped_column(FlexibleArray(str), default=list, nullable=False)

    status: Mapped[MissionStatus] = mapped_column(
        SQLEnum(MissionStatus, native_enum=False),
        default=MissionStatus.DRAFT,
        nullable=False,
    )
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_repeatable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_attempts: Mapped[int | None] = mapped_column(Integer, nullable=True)

    xp_reward: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    coins_reward: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    bonus_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bonus_coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    unlock_requirements: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
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
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    objectives: Mapped[list["MissionObjective"]] = relationship(
        "MissionObjective", back_populates="mission", cascade="all, delete-orphan", order_by="MissionObjective.order"
    )
    progress: Mapped[list["MissionProgress"]] = relationship(
        "MissionProgress", back_populates="mission", cascade="all, delete-orphan"
    )
    rewards: Mapped[list["MissionReward"]] = relationship(
        "MissionReward", back_populates="mission", cascade="all, delete-orphan"
    )


class MissionObjective(Base):
    __tablename__ = "mission_objectives"
    __table_args__ = (
        Index("ix_mission_objectives_mission_id", "mission_id"),
        Index("ix_mission_objectives_order", "mission_id", "order"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    mission_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("missions.id", ondelete="CASCADE"),
        nullable=False,
    )

    objective_type: Mapped[ObjectiveType] = mapped_column(
        SQLEnum(ObjectiveType, native_enum=False),
        default=ObjectiveType.CUSTOM,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    hint: Mapped[str | None] = mapped_column(Text, nullable=True)

    content: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    validation: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    xp_reward: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    coins_reward: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    unlock_requirements: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

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

    mission: Mapped["Mission"] = relationship("Mission", back_populates="objectives")
    progress: Mapped[list["ObjectiveProgress"]] = relationship(
        "ObjectiveProgress", back_populates="objective", cascade="all, delete-orphan"
    )


class MissionProgress(Base):
    __tablename__ = "mission_progress"
    __table_args__ = (
        Index("ix_mission_progress_user_id", "user_id"),
        Index("ix_mission_progress_mission_id", "mission_id"),
        Index("ix_mission_progress_status", "status"),
        UniqueConstraint("user_id", "mission_id", name="uq_mission_progress_user_mission"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    mission_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("missions.id", ondelete="CASCADE"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(String(50), default="not_started", nullable=False)
    current_objective_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    xp_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coins_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bonus_xp_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bonus_coins_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    best_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
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

    mission: Mapped["Mission"] = relationship("Mission", back_populates="progress")
    objective_progress: Mapped[list["ObjectiveProgress"]] = relationship(
        "ObjectiveProgress", back_populates="mission_progress", cascade="all, delete-orphan"
    )


class ObjectiveProgress(Base):
    __tablename__ = "objective_progress"
    __table_args__ = (
        Index("ix_objective_progress_mission_progress_id", "mission_progress_id"),
        Index("ix_objective_progress_objective_id", "objective_id"),
        UniqueConstraint("mission_progress_id", "objective_id", name="uq_objective_progress_unique"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    mission_progress_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("mission_progress.id", ondelete="CASCADE"),
        nullable=False,
    )
    objective_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("mission_objectives.id", ondelete="CASCADE"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(String(50), default="not_started", nullable=False)
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    xp_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coins_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    submitted_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    validation_result: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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

    mission_progress: Mapped["MissionProgress"] = relationship("MissionProgress", back_populates="objective_progress")
    objective: Mapped["MissionObjective"] = relationship("MissionObjective", back_populates="progress")


class MissionReward(Base):
    __tablename__ = "mission_rewards"
    __table_args__ = (
        Index("ix_mission_rewards_mission_id", "mission_id"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    mission_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("missions.id", ondelete="CASCADE"),
        nullable=False,
    )

    reward_type: Mapped[str] = mapped_column(String(50), nullable=False)  # item, badge, title, certificate, xp, coins
    reward_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)

    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    probability: Mapped[float] = mapped_column(default=1.0, nullable=False)  # For random rewards

    conditions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    meta_data: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    mission: Mapped["Mission"] = relationship("Mission", back_populates="rewards")
