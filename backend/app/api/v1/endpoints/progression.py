from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.schemas.base import APIResponse
from app.services.progression_service import ProgressionError, ProgressionService

router = APIRouter()


@router.get("/quests/daily", response_model=APIResponse[list], summary="Today's daily challenges")
async def today_daily(_: CurrentUser, db: AsyncSession = Depends(get_db)):
    return APIResponse[list](data=await ProgressionService.today_daily_challenges(db))


@router.get("/quests/weekly", response_model=APIResponse[list], summary="Current weekly challenges")
async def current_weekly(_: CurrentUser, db: AsyncSession = Depends(get_db)):
    return APIResponse[list](data=await ProgressionService.current_weekly_challenges(db))


@router.get("/inventory", response_model=APIResponse[list], summary="List player inventory")
async def list_inventory(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    item_type: str = Query(None),
):
    return APIResponse[list](data=await ProgressionService.list_inventory(db, user.id, item_type))


@router.post("/inventory/{item_id}/equip", response_model=APIResponse[dict], summary="Equip/unequip an item")
async def equip_item(item_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db), equipped: bool = True):
    try:
        item = await ProgressionService.equip_item(db, user.id, item_id, equipped)
    except ProgressionError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return APIResponse[dict](data=item)
