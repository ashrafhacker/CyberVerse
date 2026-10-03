"""
Quests (daily/weekly) and player inventory.

Wraps the existing DailyChallenge / WeeklyChallenge / InventoryItem models so the
spec's quest system (§27) and educational inventory (§26) are exposed via a clean
API without adding duplicate tables.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.achievement import DailyChallenge, WeeklyChallenge
from app.models.analytics import InventoryItem


class ProgressionError(ValueError):
    pass


def _daily_dict(c: DailyChallenge) -> dict:
    return {
        "id": c.id,
        "challenge_date": c.challenge_date,
        "title": c.title,
        "description": c.description,
        "task_type": c.task_type,
        "task_requirement": c.task_requirement,
        "xp_reward": c.xp_reward,
        "coins_reward": c.coins_reward,
    }


def _weekly_dict(c: WeeklyChallenge) -> dict:
    return {
        "id": c.id,
        "title": c.title,
        "description": c.description,
        "objectives": c.objectives or [],
        "xp_reward": c.xp_reward,
        "coins_reward": c.coins_reward,
        "is_premium": c.is_premium,
        "start_date": c.start_date,
        "end_date": c.end_date,
    }


def _inventory_dict(it: InventoryItem) -> dict:
    return {
        "id": it.id,
        "item_type": it.item_type,
        "item_id": it.item_id,
        "name": it.name,
        "description": it.description,
        "icon": it.icon,
        "rarity": it.rarity,
        "quantity": it.quantity,
        "is_equipped": it.is_equipped,
        "is_consumed": it.is_consumed,
        "acquired_from": it.acquired_from,
        "acquired_at": it.acquired_at,
        "expires_at": it.expires_at,
    }


class ProgressionService:
    @staticmethod
    async def today_daily_challenges(db: AsyncSession) -> list[dict]:
        start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        result = await db.execute(
            select(DailyChallenge)
            .where(DailyChallenge.is_active.is_(True), DailyChallenge.challenge_date >= start, DailyChallenge.challenge_date < end)
            .order_by(DailyChallenge.challenge_date)
        )
        return [_daily_dict(c) for c in result.scalars().all()]

    @staticmethod
    async def current_weekly_challenges(db: AsyncSession) -> list[dict]:
        now = datetime.now(UTC)
        result = await db.execute(
            select(WeeklyChallenge)
            .where(WeeklyChallenge.is_active.is_(True), WeeklyChallenge.start_date <= now, WeeklyChallenge.end_date >= now)
            .order_by(WeeklyChallenge.start_date)
        )
        return [_weekly_dict(c) for c in result.scalars().all()]

    @staticmethod
    async def list_inventory(db: AsyncSession, user_id: UUID, item_type: str | None = None) -> list[dict]:
        query = select(InventoryItem).where(InventoryItem.user_id == user_id)
        if item_type:
            query = query.where(InventoryItem.item_type == item_type)
        result = await db.execute(query.order_by(InventoryItem.acquired_at.desc()))
        return [_inventory_dict(it) for it in result.scalars().all()]

    @staticmethod
    async def equip_item(db: AsyncSession, user_id: UUID, item_id: UUID, equipped: bool) -> dict:
        item = await db.get(InventoryItem, item_id)
        if not item or item.user_id != user_id:
            raise ProgressionError("Item not found")
        item.is_equipped = equipped
        await db.commit()
        await db.refresh(item)
        return _inventory_dict(item)

    @staticmethod
    async def grant_item(
        db: AsyncSession,
        user_id: UUID,
        item_type: str,
        item_id: str,
        name: str,
        description: str,
        icon: str | None = None,
        rarity: str = "common",
        quantity: int = 1,
        acquired_from: str | None = None,
        expires_at: datetime | None = None,
    ) -> dict:
        item = InventoryItem(
            user_id=user_id,
            item_type=item_type,
            item_id=item_id,
            name=name,
            description=description,
            icon=icon,
            rarity=rarity,
            quantity=quantity,
            acquired_from=acquired_from,
            expires_at=expires_at,
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return _inventory_dict(item)
