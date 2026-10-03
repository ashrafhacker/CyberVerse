from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_roles
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.base import APIResponse
from app.schemas.ctf import ChallengeCreate, ChallengeOut, FlagSubmit, SubmissionOut
from app.services.ctf_service import Challenge, CTFError, CTFService, hash_flag

router = APIRouter()

MANAGER_ROLES = {UserRole.MODERATOR, UserRole.ADMINISTRATOR, UserRole.DEVELOPER, UserRole.SUPER_ADMIN}


@router.get("/challenges", response_model=APIResponse[list[ChallengeOut]], summary="List active CTF challenges")
async def list_challenges(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    category: str = Query(None),
    difficulty: str = Query(None),
):
    items = await CTFService.list_challenges(db, user, category, difficulty)
    return APIResponse[list[ChallengeOut]](
        data=[ChallengeOut.model_validate(item) for item in items]
    )


@router.post("/challenges", response_model=APIResponse[ChallengeOut], status_code=201, summary="Create a CTF challenge (curator/admin)")
async def create_challenge(
    payload: ChallengeCreate,
    _: User = Depends(require_roles(MANAGER_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    challenge = Challenge(
        slug=payload.slug,
        title=payload.title,
        story=payload.story,
        category=payload.category,
        difficulty=payload.difficulty,
        points=payload.points,
        hint=payload.hint,
        flag_sha256=hash_flag(payload.flag),
        flag_hint_prefix=payload.flag_hint_prefix,
        tags=payload.tags,
        is_active=payload.is_active,
    )
    db.add(challenge)
    await db.commit()
    await db.refresh(challenge)
    return APIResponse[ChallengeOut](
        data=ChallengeOut.model_validate(
            {
                "id": str(challenge.id),
                "slug": challenge.slug,
                "title": challenge.title,
                "story": challenge.story,
                "category": challenge.category,
                "difficulty": challenge.difficulty,
                "points": challenge.points,
                "hint": challenge.hint,
                "flag_hint_prefix": challenge.flag_hint_prefix,
                "tags": challenge.tags,
                "solved": False,
            }
        )
    )


@router.post("/challenges/{slug}/submit", response_model=APIResponse[SubmissionOut], summary="Submit a flag for a challenge")
async def submit_flag(
    slug: str,
    payload: FlagSubmit,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    try:
        challenge = await CTFService.get_challenge(db, slug)
    except CTFError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if not await CTFService.check_submission_rate(user):
        raise HTTPException(status_code=429, detail="Too many submissions. Try again shortly.")

    result = await CTFService.submit_flag(db, user, challenge, payload.flag)
    return APIResponse[SubmissionOut](data=SubmissionOut.model_validate(result))


@router.get("/leaderboard", response_model=APIResponse[list[dict]], summary="CTF leaderboard")
async def get_leaderboard(_: CurrentUser, db: AsyncSession = Depends(get_db)):
    return APIResponse[list[dict]](data=await CTFService.leaderboard(db))
