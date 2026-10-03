import enum
from datetime import UTC, datetime
from uuid import uuid4
from typing import List

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class GameStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class GameMode(str, enum.Enum):
    OFFENSIVE = "offensive"
    DEFENSIVE = "defensive"
    SOC = "soc"


class GameSession(Base):
    """Persisted game session for the Enterprise Network Simulator."""

    __tablename__ = "game_sessions"
    __table_args__ = (
        Index("ix_game_sessions_user_id", "user_id"),
        Index("ix_game_sessions_status", "status"),
        Index("ix_game_sessions_game_mode", "game_mode"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    scenario_seed: Mapped[str] = mapped_column(String(120), nullable=False)
    company_profile: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    topology: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    nodes: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    links: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    alerts: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    business_events: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    objectives: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    player_actions_log: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    defense_state: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    world_events: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    xp_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coins_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    energy_remaining: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    current_tick: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    status: Mapped[str] = mapped_column(String(40), default=GameStatus.ACTIVE.value, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(40), default="beginner", nullable=False)
    game_mode: Mapped[str] = mapped_column(String(40), default=GameMode.OFFENSIVE.value, nullable=False)
    industry: Mapped[str] = mapped_column(String(80), default="enterprise", nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class GameHighScore(Base):
    """Per-user high scores keyed by game mode."""

    __tablename__ = "game_high_scores"
    __table_args__ = (
        Index("ix_game_high_scores_user_id", "user_id"),
        Index("ix_game_high_scores_game_mode", "game_mode"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    game_mode: Mapped[str] = mapped_column(String(40), default=GameMode.OFFENSIVE.value, nullable=False)
    industry: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class GameIndustryTemplate(Base):
    """Seed rows describing available industry templates for the enterprise generator."""

    __tablename__ = "game_industry_templates"
    __table_args__ = (
        Index("ix_game_industry_templates_slug", "slug", unique=True),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    device_mix: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    departments: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    alert_profile: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    icon: Mapped[str | None] = mapped_column(String(60), nullable=True)
    min_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    extra_data: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class ChallengeDifficulty(str, enum.Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"
    EXPERT = "Expert"


class ChallengeStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class GameChallenge(Base):
    """Native CyberVerse challenge model."""

    __tablename__ = "game_challenges"
    __table_args__ = (
        Index("ix_game_challenges_slug", "slug", unique=True),
        Index("ix_game_challenges_category", "category"),
        Index("ix_game_challenges_difficulty", "difficulty"),
        Index("ix_game_challenges_published", "is_published"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    difficulty: Mapped[str] = mapped_column(SQLEnum(ChallengeDifficulty), nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    time_limit: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    status: Mapped[str] = mapped_column(SQLEnum(ChallengeStatus), default=ChallengeStatus.DRAFT.value, nullable=False)
    is_published: Mapped[bool] = mapped_column(default=False, nullable=False)
    flag_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    hints: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    environment_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    author_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    author: Mapped["User"] = relationship("User", back_populates="challenges")
    attempts: Mapped[List["ChallengeAttempt"]] = relationship("ChallengeAttempt", back_populates="challenge", cascade="all, delete-orphan")
    submissions: Mapped[List["ChallengeSubmission"]] = relationship("ChallengeSubmission", back_populates="challenge", cascade="all, delete-orphan")


class AttemptStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class ChallengeAttempt(Base):
    """User attempt at a challenge."""

    __tablename__ = "challenge_attempts"
    __table_args__ = (
        Index("ix_challenge_attempts_user_id", "user_id"),
        Index("ix_challenge_attempts_challenge_id", "challenge_id"),
        Index("ix_challenge_attempts_status", "status"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    challenge_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("game_challenges.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    team_id: Mapped[PGUUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("game_teams.id", ondelete="SET NULL"), nullable=True)

    status: Mapped[str] = mapped_column(SQLEnum(AttemptStatus), default=AttemptStatus.ACTIVE.value, nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    xp_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    execution_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    challenge: Mapped["GameChallenge"] = relationship("GameChallenge", back_populates="attempts")
    user: Mapped["User"] = relationship("User", back_populates="challenge_attempts")
    team: Mapped["GameTeam"] = relationship("GameTeam", back_populates="challenge_attempts")
    submissions: Mapped[List["ChallengeSubmission"]] = relationship("ChallengeSubmission", back_populates="attempt", cascade="all, delete-orphan")


class ChallengeSubmission(Base):
    """Flag submission for a challenge."""

    __tablename__ = "challenge_submissions"
    __table_args__ = (
        Index("ix_challenge_submissions_user_id", "user_id"),
        Index("ix_challenge_submissions_challenge_id", "challenge_id"),
        Index("ix_challenge_submissions_attempt_id", "attempt_id"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    attempt_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("challenge_attempts.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    challenge_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("game_challenges.id", ondelete="CASCADE"), nullable=False)

    submitted_flag: Mapped[str] = mapped_column(String(256), nullable=False)
    correct: Mapped[bool] = mapped_column(default=False, nullable=False)

    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    attempt: Mapped["ChallengeAttempt"] = relationship("ChallengeAttempt", back_populates="submissions")
    user: Mapped["User"] = relationship("User", back_populates="challenge_submissions")
    challenge: Mapped["GameChallenge"] = relationship("GameChallenge", back_populates="submissions")


class TournamentStatus(str, enum.Enum):
    UPCOMING = "upcoming"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Tournament(Base):
    """CyberVerse tournament model."""

    __tablename__ = "tournaments"
    __table_args__ = (
        Index("ix_tournaments_status", "status"),
        Index("ix_tournaments_start_at", "start_at"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_players: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    max_teams: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    rules: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(SQLEnum(TournamentStatus), default=TournamentStatus.UPCOMING.value, nullable=False)

    season_id: Mapped[PGUUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tournaments.id", ondelete="SET NULL"), nullable=True)
    created_by: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    registered_players: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    registered_teams: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by], back_populates="created_tournaments")
    season: Mapped["Tournament"] = relationship("Tournament", remote_side=[id], back_populates="sub_tournaments")
    sub_tournaments: Mapped[List["Tournament"]] = relationship("Tournament", back_populates="season")
    registrations: Mapped[List["TournamentRegistration"]] = relationship("TournamentRegistration", back_populates="tournament", cascade="all, delete-orphan")


class TournamentRegistration(Base):
    """Tournament registration."""

    __tablename__ = "tournament_registrations"
    __table_args__ = (
        Index("ix_tournament_registrations_tournament_id", "tournament_id"),
        Index("ix_tournament_registrations_user_id", "user_id"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tournament_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    team_id: Mapped[PGUUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("game_teams.id", ondelete="SET NULL"), nullable=True)

    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    tournament: Mapped["Tournament"] = relationship("Tournament", back_populates="registrations")
    user: Mapped["User"] = relationship("User", back_populates="tournament_registrations")
    team: Mapped["GameTeam"] = relationship("GameTeam", back_populates="tournament_registrations")


class GameTeamRole(str, enum.Enum):
    CAPTAIN = "captain"
    MEMBER = "member"


class GameTeam(Base):
    """CyberVerse game team model (for competitive play)."""

    __tablename__ = "game_teams"
    __table_args__ = (
        Index("ix_game_teams_tag", "tag", unique=True),
        Index("ix_game_teams_captain_id", "captain_id"),
        Index("ix_game_teams_xp", "xp"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    tag: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    max_members: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    is_private: Mapped[bool] = mapped_column(default=False, nullable=False)

    captain_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    member_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    captain: Mapped["User"] = relationship("User", foreign_keys=[captain_id], back_populates="captained_teams")
    members: Mapped[List["GameTeamMember"]] = relationship("GameTeamMember", back_populates="team", cascade="all, delete-orphan")
    challenge_attempts: Mapped[List["ChallengeAttempt"]] = relationship("ChallengeAttempt", back_populates="team")
    tournament_registrations: Mapped[List["TournamentRegistration"]] = relationship("TournamentRegistration", back_populates="team")


class GameTeamMember(Base):
    """Game team membership."""

    __tablename__ = "game_team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_game_team_member_unique"),
        Index("ix_game_team_members_team_id", "team_id"),
        Index("ix_game_team_members_user_id", "user_id"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    team_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("game_teams.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(SQLEnum(GameTeamRole), default=GameTeamRole.MEMBER.value, nullable=False)

    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    team: Mapped["GameTeam"] = relationship("GameTeam", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="game_team_memberships")
