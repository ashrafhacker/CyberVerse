import enum
from datetime import datetime, timezone
from typing import Optional, List, Dict
from uuid import uuid4

from sqlalchemy import (
    String,
    Text,
    Integer,
    DateTime,
    Boolean,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FriendStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    BLOCKED = "blocked"


class Friend(Base):
    __tablename__ = "friends"
    __table_args__ = (
        UniqueConstraint("user_id", "friend_id", name="uq_friend_pair"),
        Index("ix_friends_user_id", "user_id"),
        Index("ix_friends_friend_id", "friend_id"),
        Index("ix_friends_status", "status"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    friend_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    status: Mapped[FriendStatus] = mapped_column(
        SQLEnum(FriendStatus, native_enum=False),
        default=FriendStatus.PENDING,
        nullable=False,
    )
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    metadata: Mapped[Dict] = mapped_column(JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="friends_sent", foreign_keys=[user_id])  # noqa: F821
    friend_user: Mapped["User"] = relationship("User", back_populates="friends_received", foreign_keys=[friend_id])  # noqa: F821


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (
        Index("ix_teams_slug", "slug", unique=True),
        Index("ix_teams_owner_id", "owner_id"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tagline: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    banner_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    privacy: Mapped[str] = mapped_column(String(20), default="private", nullable=False)  # public, private, closed
    max_members: Mapped[int] = mapped_column(Integer, default=50, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    metadata: Mapped[Dict] = mapped_column(JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    members: Mapped[List["TeamMember"]] = relationship(
        "TeamMember", back_populates="team", cascade="all, delete-orphan"
    )


class TeamMember(Base):
    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_member_unique"),
        Index("ix_team_members_team_id", "team_id"),
        Index("ix_team_members_user_id", "user_id"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    team_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(String(50), default="member", nullable=False)  # owner, admin, member
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    metadata: Mapped[Dict] = mapped_column(JSONB, default=dict, nullable=False)

    team: Mapped["Team"] = relationship("Team", back_populates="members")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_sender_id", "sender_id"),
        Index("ix_chat_messages_recipient_id", "recipient_id"),
        Index("ix_chat_messages_team_id", "team_id"),
        Index("ix_chat_messages_created_at", "created_at"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    sender_id: Mapped[Optional[PGUUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    recipient_id: Mapped[Optional[PGUUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    team_id: Mapped[Optional[PGUUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=True,
    )

    message_type: Mapped[str] = mapped_column(String(50), default="text", nullable=False)  # text, image, system, mission
    content: Mapped[str] = mapped_column(Text, nullable=False)

    attachment_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    metadata: Mapped[Dict] = mapped_column(JSONB, default=dict, nullable=False)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    edited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )