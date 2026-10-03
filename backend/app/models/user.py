import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.achievement import UserAchievement
    from app.models.analytics import LeaderboardEntry
    from app.models.certificate import Certificate
    from app.models.device import Device
    from app.models.game import (
        GameChallenge,
        ChallengeAttempt,
        ChallengeSubmission,
        GameTeam,
        GameTeamMember,
        Tournament,
        TournamentRegistration,
    )
    from app.models.inventory import InventoryItem
    from app.models.notification import Notification
    from app.models.premium import Subscription
    from app.models.progress import PlayerProgress
    from app.models.session import AuditLog, Session
    from app.models.social import Friend
    from app.models.support import SupportTicket


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
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

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
    totp_secret: Mapped[str | None] = mapped_column(String(32), nullable=True)
    backup_codes: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    provider: Mapped[AuthProvider] = mapped_column(
        SQLEnum(AuthProvider, native_enum=False),
        default=AuthProvider.EMAIL,
        nullable=False,
    )
    provider_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    email_verification_token: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email_verification_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_reset_token: Mapped[str | None] = mapped_column(String(100), nullable=True)
    password_reset_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    preferences: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
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
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    profile: Mapped[Optional["Profile"]] = relationship(
        "Profile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    sessions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
    devices: Mapped[list["Device"]] = relationship(
        "Device", back_populates="user", cascade="all, delete-orphan"
    )
    progress: Mapped[list["PlayerProgress"]] = relationship(
        "PlayerProgress", back_populates="user", cascade="all, delete-orphan"
    )
    achievements: Mapped[list["UserAchievement"]] = relationship(
        "UserAchievement", back_populates="user", cascade="all, delete-orphan"
    )
    certificates: Mapped[list["Certificate"]] = relationship(
        "Certificate", back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )
    support_tickets: Mapped[list["SupportTicket"]] = relationship(
        "SupportTicket", back_populates="user", foreign_keys="SupportTicket.user_id", cascade="all, delete-orphan"
    )
    inventory: Mapped[list["InventoryItem"]] = relationship(
        "InventoryItem", back_populates="user", cascade="all, delete-orphan"
    )
    friends_sent: Mapped[list["Friend"]] = relationship(
        "Friend", back_populates="user", foreign_keys="Friend.user_id", cascade="all, delete-orphan"
    )
    friends_received: Mapped[list["Friend"]] = relationship(
        "Friend", back_populates="friend_user", foreign_keys="Friend.friend_id"
    )
    leaderboard_entries: Mapped[list["LeaderboardEntry"]] = relationship(
        "LeaderboardEntry", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="user", cascade="all, delete-orphan"
    )
    # Game relationships
    challenges: Mapped[list["GameChallenge"]] = relationship(
        "GameChallenge", back_populates="author", cascade="all, delete-orphan"
    )
    challenge_attempts: Mapped[list["ChallengeAttempt"]] = relationship(
        "ChallengeAttempt", back_populates="user", cascade="all, delete-orphan"
    )
    challenge_submissions: Mapped[list["ChallengeSubmission"]] = relationship(
        "ChallengeSubmission", back_populates="user", cascade="all, delete-orphan"
    )
    game_team_memberships: Mapped[list["GameTeamMember"]] = relationship(
        "GameTeamMember", back_populates="user", cascade="all, delete-orphan"
    )
    captained_teams: Mapped[list["GameTeam"]] = relationship(
        "GameTeam", foreign_keys="GameTeam.captain_id", back_populates="captain", cascade="all, delete-orphan"
    )
    tournament_registrations: Mapped[list["TournamentRegistration"]] = relationship(
        "TournamentRegistration", back_populates="user", cascade="all, delete-orphan"
    )
    created_tournaments: Mapped[list["Tournament"]] = relationship(
        "Tournament", foreign_keys="Tournament.created_by", back_populates="creator", cascade="all, delete-orphan"
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

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    banner_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    xp: Mapped[int] = mapped_column(default=0, nullable=False)
    coins: Mapped[int] = mapped_column(default=0, nullable=False)
    level: Mapped[int] = mapped_column(default=1, nullable=False)
    rank: Mapped[str | None] = mapped_column(String(50), nullable=True)

    titles: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    badges: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    equipped_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    equipped_badge: Mapped[str | None] = mapped_column(String(100), nullable=True)

    statistics: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

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

    user: Mapped["User"] = relationship("User", back_populates="profile")


