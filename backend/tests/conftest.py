"""Shared fixtures for CyberVerse backend tests.

Tests require a PostgreSQL database (models use JSONB/PGUUID/ARRAY).
- CI: the Postgres service container is provisioned by the workflow.
- Local: run `docker compose -f docker/docker-compose.dev.yml up -d postgres`
  then `$env:DATABASE_URL="postgresql://cyberverse:cyberverse@localhost:5432/cyberverse"`.

The test suite creates and drops all tables on the configured database at
session start/end. Never point DATABASE_URL at a production database.
"""

import os

# Required settings must exist BEFORE app modules are imported
os.environ.setdefault("SECRET_KEY", "test-secret-key-0123456789abcdef0123456789abcdef")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-0123456789abcdef0123456789abc")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://cyberverse:cyberverse@localhost:5432/cyberverse_test",
)
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker  # noqa: E402

from app.core.database import Base, create_engine, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    engine = create_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


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
