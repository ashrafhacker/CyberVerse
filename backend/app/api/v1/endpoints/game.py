"""
CyberVerse native game endpoints (challenges, tournaments, teams, arena).

Uses the project's async SQLAlchemy conventions: `get_db` yields an
`AsyncSession`, so every query is `await db.execute(select(...))` and every
mutation is followed by `await db.commit()` / `await db.refresh()`.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.api.deps import CurrentUser, require_roles
from app.core.database import get_db
from app.models.game import (
    ChallengeAttempt,
    ChallengeSubmission,
    GameChallenge,
    GameTeam,
    GameTeamMember,
    Tournament,
    TournamentRegistration,
)
from app.models.user import User, UserRole, UserStatus
from app.schemas.base import APIResponse
from app.schemas.game import (
    ArenaStatsResponse,
    ChallengeAttemptResponse,
    ChallengeSubmissionCreate,
    ChallengeSubmissionResponse,
    GameChallengeCreate,
    GameChallengeListResponse,
    GameChallengeResponse,
    GameChallengeUpdate,
    GameTeamCreate,
    GameTeamListResponse,
    GameTeamMemberResponse,
    GameTeamResponse,
    TournamentCreate,
    TournamentListResponse,
    TournamentRegistrationCreate,
    TournamentRegistrationResponse,
    TournamentResponse,
)

router = APIRouter()

MANAGER_ROLES = {
    UserRole.INSTRUCTOR,
    UserRole.MODERATOR,
    UserRole.ADMINISTRATOR,
    UserRole.DEVELOPER,
    UserRole.SUPER_ADMIN,
}
ADMIN_ROLES = {
    UserRole.MODERATOR,
    UserRole.ADMINISTRATOR,
    UserRole.DEVELOPER,
    UserRole.SUPER_ADMIN,
}

OPEN_ATTEMPT_STATES = ("active", "paused")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _str(value: Any) -> str | None:
    """Coerce a UUID/None column into the string form the API contracts expect."""
    return str(value) if value is not None else None


async def _paginate(db: AsyncSession, stmt: Select, page: int, page_size: int) -> tuple[list[Any], int]:
    """Run a count + paged window over an existing SELECT statement."""
    total = await db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = (await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return list(rows), int(total or 0)


def _challenge_out(challenge: GameChallenge) -> GameChallengeResponse:
    return GameChallengeResponse.model_validate(
        {
            "id": str(challenge.id),
            "title": challenge.title,
            "slug": challenge.slug,
            "description": challenge.description,
            "category": challenge.category,
            "difficulty": str(challenge.difficulty),
            "points": challenge.points,
            "xp": challenge.xp,
            "time_limit": challenge.time_limit,
            "status": str(challenge.status),
            "is_published": challenge.is_published,
            "flag_hash": challenge.flag_hash,
            "hints": list(challenge.hints or []),
            "environment_config": challenge.environment_config or {},
            "author_id": _str(challenge.author_id),
            "created_at": challenge.created_at,
            "updated_at": challenge.updated_at,
        }
    )


def _attempt_out(attempt: ChallengeAttempt) -> ChallengeAttemptResponse:
    return ChallengeAttemptResponse.model_validate(
        {
            "id": str(attempt.id),
            "challenge_id": str(attempt.challenge_id),
            "user_id": str(attempt.user_id),
            "team_id": _str(attempt.team_id),
            "status": str(attempt.status),
            "score": attempt.score,
            "xp_awarded": attempt.xp_awarded,
            "started_at": attempt.started_at,
            "completed_at": attempt.completed_at,
            "execution_metadata": attempt.execution_metadata or {},
        }
    )


def _tournament_out(tournament: Tournament) -> TournamentResponse:
    return TournamentResponse.model_validate(
        {
            "id": str(tournament.id),
            "name": tournament.name,
            "description": tournament.description,
            "start_at": tournament.start_at,
            "end_at": tournament.end_at,
            "max_players": tournament.max_players,
            "max_teams": tournament.max_teams,
            "rules": tournament.rules,
            "status": str(tournament.status),
            "season_id": _str(tournament.season_id),
            "created_by": _str(tournament.created_by),
            "registered_players": tournament.registered_players,
            "registered_teams": tournament.registered_teams,
            "created_at": tournament.created_at,
            "updated_at": tournament.updated_at,
        }
    )


def _registration_out(registration: TournamentRegistration) -> TournamentRegistrationResponse:
    return TournamentRegistrationResponse.model_validate(
        {
            "id": str(registration.id),
            "tournament_id": str(registration.tournament_id),
            "user_id": str(registration.user_id),
            "team_id": _str(registration.team_id),
            "registered_at": registration.registered_at,
        }
    )


def _team_out(team: GameTeam) -> GameTeamResponse:
    return GameTeamResponse.model_validate(
        {
            "id": str(team.id),
            "name": team.name,
            "tag": team.tag,
            "description": team.description or "",
            "avatar": team.avatar,
            "max_members": team.max_members,
            "is_private": team.is_private,
            "captain_id": str(team.captain_id),
            "member_count": team.member_count,
            "xp": team.xp,
            "rank": team.rank,
            "created_at": team.created_at,
            "updated_at": team.updated_at,
        }
    )


def _member_out(member: GameTeamMember) -> GameTeamMemberResponse:
    return GameTeamMemberResponse.model_validate(
        {
            "id": str(member.id),
            "team_id": str(member.team_id),
            "user_id": str(member.user_id),
            "role": str(member.role),
            "joined_at": member.joined_at,
        }
    )


async def _get_challenge(db: AsyncSession, slug: str) -> GameChallenge:
    challenge = (
        await db.execute(select(GameChallenge).where(GameChallenge.slug == slug))
    ).scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return challenge


# ---------------------------------------------------------------------------
# Challenge endpoints
# ---------------------------------------------------------------------------

@router.get("/challenges", response_model=APIResponse[GameChallengeListResponse], summary="List challenges")
async def list_challenges(
    _: CurrentUser,
    db: AsyncSession = Depends(get_db),
    category: str | None = Query(None),
    difficulty: str | None = Query(None),
    published: bool | None = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    stmt = select(GameChallenge)
    if published is not None:
        stmt = stmt.where(GameChallenge.is_published.is_(published))
    if category:
        stmt = stmt.where(GameChallenge.category == category)
    if difficulty:
        stmt = stmt.where(GameChallenge.difficulty == difficulty)
    stmt = stmt.order_by(GameChallenge.created_at.desc())

    challenges, total = await _paginate(db, stmt, page, page_size)
    return APIResponse[GameChallengeListResponse](
        data=GameChallengeListResponse(
            challenges=[_challenge_out(c) for c in challenges],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/challenges/{slug}", response_model=APIResponse[GameChallengeResponse], summary="Get one challenge")
async def get_challenge(
    slug: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    challenge = await _get_challenge(db, slug)
    if not challenge.is_published and challenge.author_id != user.id and user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return APIResponse[GameChallengeResponse](data=_challenge_out(challenge))


@router.post(
    "/challenges",
    response_model=APIResponse[GameChallengeResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a challenge (instructor/admin)",
)
async def create_challenge(
    challenge_in: GameChallengeCreate,
    user: User = Depends(require_roles(MANAGER_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    duplicate = (
        await db.execute(select(GameChallenge.id).where(GameChallenge.slug == challenge_in.slug))
    ).scalar_one_or_none()
    if duplicate:
        raise HTTPException(status_code=409, detail="Challenge slug already exists")

    challenge = GameChallenge(**challenge_in.model_dump(), author_id=user.id)
    db.add(challenge)
    await db.commit()
    await db.refresh(challenge)
    return APIResponse[GameChallengeResponse](data=_challenge_out(challenge))


@router.patch("/challenges/{challenge_id}", response_model=APIResponse[GameChallengeResponse], summary="Update a challenge")
async def update_challenge(
    challenge_id: UUID,
    challenge_in: GameChallengeUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    challenge = (
        await db.execute(select(GameChallenge).where(GameChallenge.id == challenge_id))
    ).scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    if challenge.author_id != user.id and user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized")

    for field, value in challenge_in.model_dump(exclude_unset=True).items():
        setattr(challenge, field, value)
    challenge.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(challenge)
    return APIResponse[GameChallengeResponse](data=_challenge_out(challenge))


@router.delete("/challenges/{challenge_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a challenge")
async def delete_challenge(
    challenge_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    challenge = (
        await db.execute(select(GameChallenge).where(GameChallenge.id == challenge_id))
    ).scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    if challenge.author_id != user.id and user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized")

    await db.delete(challenge)
    await db.commit()
    return None


@router.post("/challenges/{slug}/start", response_model=APIResponse[ChallengeAttemptResponse], summary="Start (or resume) an attempt")
async def start_challenge(
    slug: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    challenge = await _get_challenge(db, slug)
    if not challenge.is_published and user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Challenge not available")

    existing = (
        await db.execute(
            select(ChallengeAttempt).where(
                ChallengeAttempt.challenge_id == challenge.id,
                ChallengeAttempt.user_id == user.id,
                ChallengeAttempt.status.in_(OPEN_ATTEMPT_STATES),
            )
        )
    ).scalar_one_or_none()
    if existing:
        return APIResponse[ChallengeAttemptResponse](data=_attempt_out(existing))

    attempt = ChallengeAttempt(
        challenge_id=challenge.id,
        user_id=user.id,
        status="active",
        started_at=datetime.now(UTC),
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)
    return APIResponse[ChallengeAttemptResponse](data=_attempt_out(attempt))


@router.post(
    "/challenges/{slug}/submit",
    response_model=APIResponse[ChallengeSubmissionResponse],
    summary="Submit a flag for the active attempt",
)
async def submit_flag(
    slug: str,
    submission: ChallengeSubmissionCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    challenge = await _get_challenge(db, slug)

    attempt = (
        await db.execute(
            select(ChallengeAttempt).where(
                ChallengeAttempt.challenge_id == challenge.id,
                ChallengeAttempt.user_id == user.id,
                ChallengeAttempt.status.in_(OPEN_ATTEMPT_STATES),
            )
        )
    ).scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=400, detail="No active attempt for this challenge")

    flag_hash = hashlib.sha256(submission.flag.strip().encode()).hexdigest()
    correct = flag_hash == challenge.flag_hash

    db.add(
        ChallengeSubmission(
            attempt_id=attempt.id,
            user_id=user.id,
            challenge_id=challenge.id,
            submitted_flag=submission.flag,
            correct=correct,
            submitted_at=datetime.now(UTC),
        )
    )

    if correct:
        attempt.status = "completed"
        attempt.completed_at = datetime.now(UTC)
        attempt.score = challenge.points
        attempt.xp_awarded = challenge.xp
        user.xp = (user.xp or 0) + challenge.xp
        user.level = 1 + int(((user.xp or 0) / 1000) ** 0.5)

    await db.commit()

    return APIResponse[ChallengeSubmissionResponse](
        data=ChallengeSubmissionResponse(
            correct=correct,
            message="Correct flag!" if correct else "Incorrect flag. Try again.",
            xp_awarded=challenge.xp if correct else None,
        )
    )


# ---------------------------------------------------------------------------
# Tournament endpoints
# ---------------------------------------------------------------------------

@router.get("/tournaments", response_model=APIResponse[TournamentListResponse], summary="List tournaments")
async def list_tournaments(
    _: CurrentUser,
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    stmt = select(Tournament)
    if status_filter:
        stmt = stmt.where(Tournament.status == status_filter)
    stmt = stmt.order_by(Tournament.start_at.desc())

    tournaments, total = await _paginate(db, stmt, page, page_size)
    return APIResponse[TournamentListResponse](
        data=TournamentListResponse(
            tournaments=[_tournament_out(t) for t in tournaments],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/tournaments/{tournament_id}", response_model=APIResponse[TournamentResponse], summary="Get a tournament")
async def get_tournament(
    tournament_id: UUID,
    _: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    tournament = (
        await db.execute(select(Tournament).where(Tournament.id == tournament_id))
    ).scalar_one_or_none()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return APIResponse[TournamentResponse](data=_tournament_out(tournament))


@router.post(
    "/tournaments",
    response_model=APIResponse[TournamentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a tournament (instructor/admin)",
)
async def create_tournament(
    tournament_in: TournamentCreate,
    user: User = Depends(require_roles(MANAGER_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    payload = tournament_in.model_dump()
    season_id = payload.pop("season_id", None)
    tournament = Tournament(
        **payload,
        season_id=UUID(season_id) if season_id else None,
        created_by=user.id,
    )
    db.add(tournament)
    await db.commit()
    await db.refresh(tournament)
    return APIResponse[TournamentResponse](data=_tournament_out(tournament))


@router.post(
    "/tournaments/{tournament_id}/register",
    response_model=APIResponse[TournamentRegistrationResponse],
    summary="Register for a tournament",
)
async def register_tournament(
    tournament_id: UUID,
    registration: TournamentRegistrationCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    tournament = (
        await db.execute(select(Tournament).where(Tournament.id == tournament_id))
    ).scalar_one_or_none()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    if str(tournament.status) != "upcoming":
        raise HTTPException(status_code=400, detail="Tournament not open for registration")

    existing = (
        await db.execute(
            select(TournamentRegistration).where(
                TournamentRegistration.tournament_id == tournament_id,
                TournamentRegistration.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Already registered")

    team_id = UUID(registration.team_id) if registration.team_id else None
    if team_id is not None:
        team = (await db.execute(select(GameTeam).where(GameTeam.id == team_id))).scalar_one_or_none()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

    row = TournamentRegistration(tournament_id=tournament_id, user_id=user.id, team_id=team_id)
    db.add(row)
    tournament.registered_players = (tournament.registered_players or 0) + 1
    if team_id is not None:
        tournament.registered_teams = (tournament.registered_teams or 0) + 1
    await db.commit()
    await db.refresh(row)
    return APIResponse[TournamentRegistrationResponse](data=_registration_out(row))


# ---------------------------------------------------------------------------
# Team endpoints
# ---------------------------------------------------------------------------

@router.get("/teams", response_model=APIResponse[GameTeamListResponse], summary="List teams")
async def list_teams(
    _: CurrentUser,
    db: AsyncSession = Depends(get_db),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    stmt = select(GameTeam)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(GameTeam.name.ilike(pattern) | GameTeam.tag.ilike(pattern))
    stmt = stmt.order_by(GameTeam.xp.desc())

    teams, total = await _paginate(db, stmt, page, page_size)
    return APIResponse[GameTeamListResponse](
        data=GameTeamListResponse(
            teams=[_team_out(t) for t in teams],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/teams/{team_id}", response_model=APIResponse[GameTeamResponse], summary="Get a team")
async def get_team(
    team_id: UUID,
    _: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    team = (await db.execute(select(GameTeam).where(GameTeam.id == team_id))).scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return APIResponse[GameTeamResponse](data=_team_out(team))


@router.post(
    "/teams",
    response_model=APIResponse[GameTeamResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a team",
)
async def create_team(
    team_in: GameTeamCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    existing = (
        await db.execute(select(GameTeam).where(GameTeam.tag == team_in.tag))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Team tag already taken")

    team = GameTeam(**team_in.model_dump(), captain_id=user.id, member_count=1)
    db.add(team)
    await db.flush()
    db.add(GameTeamMember(team_id=team.id, user_id=user.id, role="captain"))
    await db.commit()
    await db.refresh(team)
    return APIResponse[GameTeamResponse](data=_team_out(team))


@router.post("/teams/{team_id}/join", response_model=APIResponse[GameTeamMemberResponse], summary="Join a team")
async def join_team(
    team_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    team = (await db.execute(select(GameTeam).where(GameTeam.id == team_id))).scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if team.is_private and team.captain_id != user.id:
        raise HTTPException(status_code=403, detail="Team is private")
    if team.member_count >= team.max_members:
        raise HTTPException(status_code=400, detail="Team is full")

    existing = (
        await db.execute(
            select(GameTeamMember).where(
                GameTeamMember.team_id == team_id,
                GameTeamMember.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Already a member")

    member = GameTeamMember(team_id=team_id, user_id=user.id, role="member")
    db.add(member)
    team.member_count = (team.member_count or 0) + 1
    await db.commit()
    await db.refresh(member)
    return APIResponse[GameTeamMemberResponse](data=_member_out(member))


# ---------------------------------------------------------------------------
# Arena stats
# ---------------------------------------------------------------------------

@router.get("/arena/stats", response_model=APIResponse[ArenaStatsResponse], summary="Global arena statistics")
async def get_arena_stats(
    _: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    active_challenges = await db.scalar(
        select(func.count())
        .select_from(GameChallenge)
        .where(GameChallenge.is_published.is_(True), GameChallenge.status == "published")
    )
    total_players = await db.scalar(
        select(func.count()).select_from(User).where(User.status == UserStatus.ACTIVE)
    )
    active_environments = await db.scalar(
        select(func.count()).select_from(ChallengeAttempt).where(ChallengeAttempt.status == "active")
    )
    current_season = (
        await db.execute(
            select(Tournament)
            .where(Tournament.status == "active")
            .order_by(Tournament.start_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    return APIResponse[ArenaStatsResponse](
        data=ArenaStatsResponse(
            active_challenges=int(active_challenges or 0),
            total_players=int(total_players or 0),
            active_environments=int(active_environments or 0),
            current_season=(
                {"name": current_season.name, "ends_at": current_season.end_at} if current_season else None
            ),
        )
    )
