from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from bot.db.engine import get_session_dependency


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session_dependency():
        yield session
