"""Shared fixtures for CyberVerse backend tests.

Uses SQLite for fast local testing (no Docker required).
"""

import os
import tempfile

# Required settings must exist BEFORE app modules are imported
os.environ.setdefault("SECRET_KEY", "test-secret-key-0123456789abcdef0123456789abcdef")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-0123456789abcdef0123456789abc")
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")

# Clear settings cache to pick up test env vars
from app.core.config import get_settings
get_settings.cache_clear()

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


def _make_engine():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        return create_async_engine(database_url)

    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()
    return create_async_engine(
        f"sqlite+aiosqlite:///{temp_db.name}", poolclass=None
    )


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = _make_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    database_file = engine.url.database
    is_sqlite = engine.url.drivername == "sqlite+aiosqlite"
    await engine.dispose()
    if is_sqlite and database_file:
        try:
            os.unlink(database_file)
        except OSError:
            pass


@pytest_asyncio.fixture
async def db_session(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
