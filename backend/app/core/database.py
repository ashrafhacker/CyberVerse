from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, TypeVar

from sqlalchemy import JSON, TypeDecorator, String, Integer
from sqlalchemy.dialects.postgresql import ARRAY as PGArray
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings

T = TypeVar("T")


class FlexibleArray(TypeDecorator[list[T]]):
    """
    Array type that works with both PostgreSQL (native ARRAY) and SQLite (JSON).
    Stores as JSON array in SQLite, native ARRAY in PostgreSQL.
    """

    impl = JSON
    cache_ok = True

    def __init__(self, item_type: type = str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.item_type = item_type
        if item_type == str:
            self._sa_item_type = String()
        elif item_type == int:
            self._sa_item_type = Integer()
        else:
            self._sa_item_type = String()

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PGArray(self._sa_item_type))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value: list[T] | None, dialect: Any) -> Any:
        if value is None:
            return []
        if dialect.name == "postgresql":
            return value
        import json
        return json.dumps(value)

    def process_result_value(self, value: Any, dialect: Any) -> list[T]:
        if value is None:
            return []
        if dialect.name == "postgresql":
            return value
        if isinstance(value, str):
            import json
            return json.loads(value)
        return value


class Base(DeclarativeBase):
    pass


def create_engine() -> AsyncEngine:
    kwargs: dict[str, Any] = {}
    if settings.ENVIRONMENT == "testing":
        kwargs["poolclass"] = NullPool
    else:
        kwargs.update({
            "pool_size": settings.DATABASE_POOL_SIZE,
            "max_overflow": settings.DATABASE_MAX_OVERFLOW,
            "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
            "pool_recycle": settings.DATABASE_POOL_RECYCLE,
            "pool_pre_ping": True,
            "connect_args": settings.DATABASE_CONNECT_ARGS,
        })

    return create_async_engine(
        settings.database_url_async,
        echo=settings.DEBUG,
        execution_options={"isolation_level": "READ_COMMITTED"},
        **kwargs
    )


engine = create_engine()

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    await engine.dispose()
