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
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

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
    env = os.getenv("ENVIRONMENT", "").lower()

    if database_url:
        # Fail closed for shared/production-like databases
        url_lower = database_url.lower()
        dangerous_indicators = [
            "production",
            "prod",
            "staging",
            "stage",
            "live",
            "shared",
            "master",
            "main",
        ]
        # Allow CI to use postgres - preserve CI behavior
        # Only block if it looks like production AND not explicitly in testing with CI-like setup
        if env == "testing":
            # Allow postgres in testing (CI)
            if database_url.startswith("postgresql://"):
                database_url = database_url.replace(
                    "postgresql://", "postgresql+asyncpg://", 1
                )
            return create_async_engine(database_url)
        else:
            # Non-testing env - be extra careful
            if any(ind in url_lower for ind in dangerous_indicators):
                raise RuntimeError(
                    "Test database fixture cannot use production/shared database URL in non-testing environment"
                )
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



# Key prefixes this application writes to Redis (rate limiting, CTF submit
# throttle, AI response cache). Test cleanup is deliberately scoped to these
# prefixes so a shared or long-lived Redis database is never wiped.
_TEST_REDIS_PREFIXES = ("ratelimit:*", "ctf:submit:*", "ai:*")


@pytest_asyncio.fixture(autouse=True)
async def clear_redis():
    """Delete only app-created test keys before and after each test.

    Requires explicit test-only Redis configuration to prevent accidental deletion
    of shared Redis data. Fail closed if isolation cannot be established.
    """
    import redis.asyncio as aioredis

    settings = get_settings()
    redis_url = settings.REDIS_URL
    env = os.getenv("ENVIRONMENT", "").lower()

    # Require explicit test-only configuration
    redis_lower = str(redis_url).lower()
    is_test_isolated = False

    # Check for test-specific database index (common pattern: /15 for tests)
    if redis_lower.endswith("/15") or "/test" in redis_lower:
        is_test_isolated = True
    # Also allow if using localhost in testing context
    if env == "testing" and "localhost" in redis_lower:
        is_test_isolated = True

    if not is_test_isolated:
        raise RuntimeError(
            "Redis cleanup blocked: REDIS_URL must point to an isolated test Redis "
            "(e.g., redis://localhost:6379/15) in testing environment"
        )

    async def _wipe() -> None:
        client = aioredis.from_url(redis_url)
        try:
            for prefix in _TEST_REDIS_PREFIXES:
                async for key in client.scan_iter(match=prefix):
                    await client.delete(key)
        finally:
            await client.aclose()

    try:
        await _wipe()
    except Exception:
        # Redis unavailable: raise to fail closed as isolation cannot be verified
        raise RuntimeError("Redis unavailable - cannot establish test isolation")

    yield
    try:
        await _wipe()
    except Exception:
        raise RuntimeError("Redis unavailable during teardown - cannot verify cleanup")


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
