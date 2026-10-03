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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CTFCategory(str, enum.Enum):
    WEB = "web"
    CRYPTO = "crypto"
    FORENSICS = "forensics"
    REVERSING = "reversing"
    OSINT = "osint"
    NETWORKING = "networking"
    LINUX = "linux"
    DEFENSIVE = "defensive"
    GENERAL = "general"


class Challenge(Base):
    __tablename__ = "ctf_challenges"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_ctf_challenges_slug"),
        Index("ix_ctf_challenges_category", "category"),
        Index("ix_ctf_challenges_difficulty", "difficulty"),
        Index("ix_ctf_challenges_active", "is_active"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    story: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[CTFCategory] = mapped_column(
        String(40), default=CTFCategory.GENERAL.value, nullable=False
    )
    difficulty: Mapped[str] = mapped_column(String(40), default="beginner", nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    flag_sha256: Mapped[str] = mapped_column(String(128), nullable=False)
    flag_hint_prefix: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[PGUUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class FlagSubmission(Base):
    __tablename__ = "ctf_submissions"
    __table_args__ = (
        UniqueConstraint("user_id", "challenge_id", name="uq_ctf_submission_user_challenge"),
        Index("ix_ctf_submissions_challenge_id", "challenge_id"),
        Index("ix_ctf_submissions_user_id", "user_id"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    challenge_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ctf_challenges.id", ondelete="CASCADE"), nullable=False
    )
    correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    first_blood: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    solved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
