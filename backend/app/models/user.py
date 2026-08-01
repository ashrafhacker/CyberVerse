import enum
from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    String,
    Text,
    DateTime,
    Boolean,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    GUEST = "guest"
    STUDENT = "student"
    PREMIUM_STUDENT = "premium_student"
    INSTRUCTOR = "instructor"
    MODERATOR = "moderator"
    ADMINISTRATOR = "administrator"
    DEVELOPER = "developer"
    SUPER_ADMIN = "super_admin"


class UserStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BANNED = "banned"


class AuthProvider(str, enum.Enum):
    EMAIL = "email"
    GOOGLE = "google"
    GITHUB = "github"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_status", "status"),
        Index("ix_users_role", "role"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, native_enum=False),
        default=UserRole.STUDENT,
        nullable=False,
    )
    status: Mapped[UserStatus] = mapped_column(
        SQLEnum(UserStatus, native_enum=False),
        default=UserStatus.PENDING,
        nullable=False,
    )

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_2fa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    totp_secret: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    backup_codes: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)

    provider: Mapped[AuthProvider] = mapped_column(
        SQLEnum(AuthProvider, native_enum=False),
        default=AuthProvider.EMAIL,
        nullable=False,
    )
    provider_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    email_verification_token: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email_verification_expires: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    password_reset_token: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    password_reset_expires: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    preferences: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

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
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    profile: Mapped[Optional["Profile"]] = relationship(
        "Profile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    sessions: Mapped[List["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
    devices: Mapped[List["Device"]] = relationship(
        "Device", back_populates="user", cascade="all, delete-orphan"
    )
    progress: Mapped[List["PlayerProgress"]] = relationship(
        "PlayerProgress", back_populates="user", cascade="all, delete-orphan"
    )
    achievements: Mapped[List["UserAchievement"]] = relationship(
        "UserAchievement", back_populates="user", cascade="all, delete-orphan"
    )
    certificates: Mapped[List["Certificate"]] = relationship(
        "Certificate", back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )
    subscriptions: Mapped[List["Subscription"]] = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )
    support_tickets: Mapped[List["SupportTicket"]] = relationship(
        "SupportTicket", back_populates="user", cascade="all, delete-orphan"
    )
    inventory: Mapped[List["InventoryItem"]] = relationship(
        "InventoryItem", back_populates="user", cascade="all, delete-orphan"
    )
    friends_sent: Mapped[List["Friend"]] = relationship(
        "Friend", back_populates="user", foreign_keys="Friend.user_id", cascade="all, delete-orphan"
    )
    friends_received: Mapped[List["Friend"]] = relationship(
        "Friend", back_populates="friend_user", foreign_keys="Friend.friend_id"
    )
    leaderboard_entries: Mapped[List["LeaderboardEntry"]] = relationship(
        "LeaderboardEntry", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="user", cascade="all, delete-orphan"
    )


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (
        Index("ix_profiles_username", "username", unique=True),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    banner_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    xp: Mapped[int] = mapped_column(default=0, nullable=False)
    coins: Mapped[int] = mapped_column(default=0, nullable=False)
    level: Mapped[int] = mapped_column(default=1, nullable=False)
    rank: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    titles: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    badges: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    equipped_title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    equipped_badge: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    statistics: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

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

    user: Mapped["User"] = relationship("User", back_populates="profile")


