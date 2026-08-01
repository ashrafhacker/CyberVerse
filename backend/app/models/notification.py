import enum
from datetime import datetime, timezone
from typing import Optional, Dict
from uuid import uuid4

from sqlalchemy import (
    String,
    Text,
    DateTime,
    Boolean,
    Enum as SQLEnum,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class NotificationType(str, enum.Enum):
    SYSTEM = "system"
    ACHIEVEMENT = "achievement"
    MISSION = "mission"
    COURSE = "course"
    FRIEND = "friend"
    MESSAGE = "message"
    INSTRUCTOR = "instructor"
    PREMIUM = "premium"
    SECURITY = "security"
    MAINTENANCE = "maintenance"
    EVENT = "event"


class NotificationChannel(str, enum.Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_id", "user_id"),
        Index("ix_notifications_type", "notification_type"),
        Index("ix_notifications_read_at", "read_at"),
        Index("ix_notifications_created_at", "created_at"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    notification_type: Mapped[NotificationType] = mapped_column(
        SQLEnum(NotificationType, native_enum=False),
        default=NotificationType.SYSTEM,
        nullable=False,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        SQLEnum(NotificationChannel, native_enum=False),
        default=NotificationChannel.IN_APP,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    icon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    data: Mapped[Dict] = mapped_column(JSONB, default=dict, nullable=False)
    metadata: Mapped[Dict] = mapped_column(JSONB, default=dict, nullable=False)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dismissed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="notifications")  # noqa: F821


class Announcement(Base):
    __tablename__ = "announcements"
    __table_args__ = (
        Index("ix_announcements_published_at", "published_at"),
        Index("ix_announcements_is_active", "is_active"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    author_id: Mapped[Optional[PGUUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    announcement_type: Mapped[str] = mapped_column(String(50), default="general", nullable=False)
    target_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_draft: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    publish_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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