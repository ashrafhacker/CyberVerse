from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.schemas.base import APIResponse
from app.services.leaderboard_service import LeaderboardService

router = APIRouter()


@router.get("/", response_model=APIResponse[dict], summary="Get leaderboard rankings")
async def get_leaderboard(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    type: str = Query("weekly", pattern="^(weekly|monthly|all_time)$"),
):
    board = await LeaderboardService.get_or_create_weekly(db)
    entries, total = await LeaderboardService.get_rankings(db, board, limit=limit, offset=offset)
    my_rank = await LeaderboardService.get_user_rank(db, board, user.id)

    return APIResponse[dict](
        data={
            "board_id": str(board.id),
            "name": board.name,
            "type": type,
            "period_start": board.period_start.isoformat() if board.period_start else None,
            "period_end": board.period_end.isoformat() if board.period_end else None,
            "total_players": total,
            "my_rank": my_rank,
            "entries": entries,
        }
    )


@router.get("/top", response_model=APIResponse[list], summary="Get top players")
async def get_top_players(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=50),
):
    board = await LeaderboardService.get_or_create_weekly(db)
    entries, _ = await LeaderboardService.get_rankings(db, board, limit=limit)
    return APIResponse[list](data=entries)