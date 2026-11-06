from collections.abc import AsyncIterator
from math import ceil

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings


class Database:
    def __init__(self, settings: Settings):
        statement_timeout_ms = int(settings.dependency_timeout_seconds * 1000)
        self.engine = create_async_engine(
            settings.database_url.get_secret_value(),
            pool_pre_ping=True,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout_seconds,
            connect_args={
                "connect_timeout": max(1, ceil(settings.dependency_timeout_seconds)),
                "options": f"-c statement_timeout={statement_timeout_ms}",
            },
            hide_parameters=True,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, autoflush=False)

    async def probe(self) -> None:
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def close(self) -> None:
        await self.engine.dispose()


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.services.database.sessions() as session:
        # Caller dùng async with session.begin(); không implicit commit khi request kết thúc.
        yield session
