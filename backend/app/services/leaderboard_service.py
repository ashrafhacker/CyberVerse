from datetime import UTC
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import Leaderboard, LeaderboardEntry
from app.models.progress import PlayerProgress
from app.models.user import Profile, User


class LeaderboardService:
    @staticmethod
    async def get_or_create_weekly(db: AsyncSession) -> Leaderboard:
        return await LeaderboardService.get_or_create_board(db, "weekly")

    @staticmethod
    async def get_or_create_board(db: AsyncSession, board_type: str) -> Leaderboard:
        from datetime import datetime, timedelta

        now = datetime.now(UTC)
        if board_type == "all_time":
            start = datetime(2000, 1, 1, tzinfo=UTC)
            end = now + timedelta(days=3650)
            name = "All-Time Leaderboard"
        elif board_type == "monthly":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = (start + timedelta(days=32)).replace(day=1)
            name = f"Monthly Leaderboard {start.strftime('%Y-%m')}"
        else:  # weekly
            board_type = "weekly"
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
            name = f"Weekly Leaderboard {start.strftime('%Y-%m-%d')}"

        result = await db.execute(
            select(Leaderboard).where(
                Leaderboard.leaderboard_type == board_type,
                Leaderboard.period_start == start,
            )
        )
        board = result.scalar_one_or_none()
        if not board:
            board = Leaderboard(
                leaderboard_type=board_type,
                name=name,
                period_start=start,
                period_end=end,
            )
            db.add(board)
            await db.commit()
            await db.refresh(board)
        return board

    @staticmethod
    async def get_rankings(
        db: AsyncSession,
        board: Leaderboard,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list, int]:
        total_result = await db.execute(
            select(func.count(LeaderboardEntry.id)).where(
                LeaderboardEntry.leaderboard_id == board.id
            )
        )
        total = total_result.scalar_one()

        result = await db.execute(
            select(LeaderboardEntry, Profile, User)
            .join(Profile, Profile.user_id == LeaderboardEntry.user_id)
            .join(User, User.id == LeaderboardEntry.user_id)
            .where(LeaderboardEntry.leaderboard_id == board.id)
            .order_by(LeaderboardEntry.score.desc())
            .limit(limit)
            .offset(offset)
        )

        entries = []
        for entry, profile, user in result.all():
            entries.append(
                {
                    "rank": entry.rank,
                    "user_id": str(user.id),
                    "username": profile.username,
                    "full_name": user.full_name,
                    "avatar_url": user.avatar_url,
                    "score": entry.score,
                    "time_spent_seconds": entry.time_spent_seconds,
                }
            )
        return entries, total

    @staticmethod
    async def get_user_rank(db: AsyncSession, board: Leaderboard, user_id: UUID) -> dict | None:
        result = await db.execute(
            select(LeaderboardEntry).where(
                LeaderboardEntry.leaderboard_id == board.id,
                LeaderboardEntry.user_id == user_id,
            )
        )
        entry = result.scalar_one_or_none()
        if not entry:
            return None
        return {
            "rank": entry.rank,
            "score": entry.score,
        }

    @staticmethod
    async def rebuild_board(db: AsyncSession, board: Leaderboard) -> int:
        """Recalculate leaderboard from player progress (for all-time / weekly boards)."""
        # Clear existing entries for this board
        from sqlalchemy import delete
        await db.execute(delete(LeaderboardEntry).where(LeaderboardEntry.leaderboard_id == board.id))

        result = await db.execute(
            select(PlayerProgress.user_id, PlayerProgress.total_xp, PlayerProgress.time_spent_seconds)
            .order_by(desc(PlayerProgress.total_xp))
        )
        rows = result.all()

        entries = []
        for index, (user_id, score, time_spent) in enumerate(rows, start=1):
            entries.append(
                LeaderboardEntry(
                    leaderboard_id=board.id,
                    user_id=user_id,
                    score=score,
                    rank=index,
                    time_spent_seconds=time_spent,
                )
            )

        db.add_all(entries)
        await db.commit()
        return len(entries)
