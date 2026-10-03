import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import async_session_maker

async def check():
    async with async_session_maker() as db:
        res = await db.execute(text("SELECT slug FROM courses"))
        print(res.fetchall())

asyncio.run(check())
