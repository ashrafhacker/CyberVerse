"""Shared fixtures for CyberVerse backend tests.

Isolation rules (fail closed):
- Schema create_all()/drop_all() only ever run against a temporary SQLite file
  or a database explicitly declared via TEST_DATABASE_URL and validated as a
  test target. ENVIRONMENT=testing alone is never proof of isolation, and a
  plain DATABASE_URL (application config, possibly loaded from .env) is never
  used for schema operations.
- The schema fixture refuses a test database that already contains tables, so
  cleanup only ever removes tables the fixture itself created.
- Redis key cleanup only runs against a target explicitly declared via
  TEST_REDIS_URL (validated), and only deletes the known test key prefixes.
  FLUSHDB/FLUSHALL are never used. When isolation cannot be verified, cleanup
  is skipped for loopback targets and refused for anything else.
"""

import os
import tempfile
import warnings
from pathlib import Path
from urllib.parse import urlparse

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
from sqlalchemy import inspect  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

# Names that indicate a live/shared/production-ish target. A URL carrying any
# of these is never accepted for schema operations or destructive cleanup.
_UNSAFE_TARGET_MARKERS = (
    "production",
    "prod",
    "staging",
    "stage",
    "live",
    "shared",
    "master",
    "main",
    "backup",
    "dump",
)
_TEST_DB_SCHEMES = {"postgresql", "postgres", "postgresql+asyncpg", "sqlite", "sqlite+aiosqlite"}
_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1", ""}

# SQLite files this module created; only these may ever be deleted.
_created_sqlite_files: set[str] = set()
_cleanup_skip_warned = False


def _flagged_markers(url: str) -> list[str]:
    lowered = str(url).lower()
    return [marker for marker in _UNSAFE_TARGET_MARKERS if marker in lowered]


def _validate_test_database_url(url: str) -> str:
    """Validate an explicit TEST_DATABASE_URL before any schema work.

    Requires a supported scheme, no production/shared markers, and a target
    that identifies itself as a test database (loopback host or test-named
    database). Fails closed on anything unverified.
    """
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in _TEST_DB_SCHEMES:
        raise RuntimeError(
            f"TEST_DATABASE_URL must be a postgres or sqlite URL, got scheme {scheme!r}"
        )
    flagged = _flagged_markers(url)
    if flagged:
        raise RuntimeError(
            "TEST_DATABASE_URL looks like a production/shared target "
            f"(matched {', '.join(flagged)}); refusing schema operations"
        )
    if scheme in {"postgresql", "postgres"}:
        url = url.replace(f"{scheme}://", "postgresql+asyncpg://", 1)
    elif scheme == "sqlite":
        url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)

    if scheme.startswith("sqlite"):
        raw_path = parsed.path or ""
        if "test" not in Path(raw_path).name.lower() and tempfile.gettempdir() not in raw_path:
            raise RuntimeError(
                "sqlite TEST_DATABASE_URL must live in the system temp directory "
                "or have 'test' in its filename"
            )
        return url

    host = (parsed.hostname or "").lower()
    database_name = Path(parsed.path).name.lower()
    if host not in _LOOPBACK_HOSTS and "test" not in database_name:
        raise RuntimeError(
            "TEST_DATABASE_URL must target a loopback host or a database whose "
            "name marks it as a test database"
        )
    return url


def _resolve_database_url() -> str | None:
    """Return the database URL schema operations may use, or None for temp SQLite.

    Only an explicit TEST_DATABASE_URL counts. Application DATABASE_URL (which
    may come from .env and point at a real database) is never accepted, no
    matter what ENVIRONMENT says.
    """
    explicit = os.getenv("TEST_DATABASE_URL")
    if explicit:
        return _validate_test_database_url(explicit.strip())
    if os.getenv("DATABASE_URL"):
        raise RuntimeError(
            "DATABASE_URL is set but no isolated test database is configured. "
            "Set TEST_DATABASE_URL to a dedicated test database (or unset "
            "DATABASE_URL to fall back to a temporary SQLite file); refusing "
            "to run create_all()/drop_all() against an unverified target"
        )
    return None


def _make_engine():
    database_url = _resolve_database_url()
    if database_url is None:
        fd, temp_path = tempfile.mkstemp(prefix="cyberverse_test_", suffix=".db")
        os.close(fd)
        _created_sqlite_files.add(temp_path)
        return create_async_engine(f"sqlite+aiosqlite:///{temp_path}", poolclass=None)
    if database_url.startswith("sqlite"):
        return create_async_engine(database_url, poolclass=None)
    return create_async_engine(database_url)


def _existing_tables(sync_conn) -> list[str]:
    return inspect(sync_conn).get_table_names()


def _discard_created_file(database_file: str | None) -> None:
    if not database_file or database_file not in _created_sqlite_files:
        return
    _created_sqlite_files.discard(database_file)
    try:
        os.unlink(database_file)
    except OSError:
        pass


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = _make_engine()
    database_file = engine.url.database if engine.url.drivername.startswith("sqlite") else None
    try:
        async with engine.begin() as conn:
            existing = await conn.run_sync(_existing_tables)
            if existing:
                raise RuntimeError(
                    "Refusing to run create_all(): the test database is not empty "
                    f"(found {', '.join(sorted(existing)[:5])}). Isolation cannot "
                    "be established - point TEST_DATABASE_URL at a throwaway database"
                )
            await conn.run_sync(Base.metadata.create_all)
    except BaseException:
        await engine.dispose()
        _discard_created_file(database_file)
        raise
    yield engine
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    finally:
        await engine.dispose()
        _discard_created_file(database_file)


@pytest_asyncio.fixture
async def db_session(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


# Key prefixes this application writes to Redis (rate limiting, CTF submit
# throttle, AI response cache). Cleanup is deliberately scoped to these
# prefixes so a shared or long-lived Redis database is never wiped, and
# FLUSHDB/FLUSHALL are never used.
_TEST_REDIS_PREFIXES = ("ratelimit:*", "ctf:submit:*", "ai:*")


def _validate_redis_target(url: str) -> str:
    """Validate an explicitly declared TEST_REDIS_URL target."""
    parsed = urlparse(str(url))
    if (parsed.scheme or "").lower() not in {"redis", "rediss"}:
        raise RuntimeError(f"TEST_REDIS_URL must be a redis:// URL, got scheme {parsed.scheme!r}")
    flagged = _flagged_markers(url)
    if flagged:
        raise RuntimeError(
            "TEST_REDIS_URL looks like a production/shared target "
            f"(matched {', '.join(flagged)}); refusing key cleanup"
        )
    host = (parsed.hostname or "").lower()
    if host not in _LOOPBACK_HOSTS and "test" not in host:
        raise RuntimeError(
            "TEST_REDIS_URL must target a loopback host or a host whose name "
            "marks it as a test target"
        )
    return str(url)


def _resolve_redis_cleanup(redis_url: str | None = None) -> str | None:
    """Return the Redis URL test key cleanup may run against, or None to skip.

    Cleanup only runs against an explicitly declared, validated TEST_REDIS_URL.
    An unverified loopback target skips destructive cleanup (tests can run
    without it); anything that might be shared or production fails closed.
    """
    explicit = os.getenv("TEST_REDIS_URL")
    if explicit:
        return _validate_redis_target(explicit.strip())
    url = str(redis_url if redis_url is not None else get_settings().REDIS_URL)
    parsed = urlparse(url)
    flagged = _flagged_markers(url)
    if (parsed.scheme or "").lower() not in {"redis", "rediss"} or flagged:
        raise RuntimeError(
            "Redis cleanup blocked: REDIS_URL does not look like an isolated "
            "test instance. Set TEST_REDIS_URL to a dedicated test Redis (or "
            "unset REDIS_URL); refusing to touch it"
        )
    if (parsed.hostname or "").lower() not in _LOOPBACK_HOSTS:
        raise RuntimeError(
            "Redis cleanup blocked: REDIS_URL points at a non-loopback host "
            "and no TEST_REDIS_URL declares an isolated test target"
        )
    global _cleanup_skip_warned
    if not _cleanup_skip_warned:
        warnings.warn(
            "No TEST_REDIS_URL configured: skipping destructive Redis cleanup, so "
            "test key prefixes may linger. Set TEST_REDIS_URL to enable cleanup.",
            RuntimeWarning,
            stacklevel=2,
        )
        _cleanup_skip_warned = True
    return None


@pytest_asyncio.fixture(autouse=True)
async def clear_redis():
    """Delete only app-created test keys before and after each test.

    Runs only when an isolated test Redis target is explicitly configured;
    never flushes a database, never touches keys outside the test prefixes.
    """
    redis_url = _resolve_redis_cleanup()
    if redis_url is None:
        yield
        return

    import redis.asyncio as aioredis

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
    except Exception as exc:
        raise RuntimeError(
            "Test Redis configured via TEST_REDIS_URL is unreachable; " "cannot verify isolation"
        ) from exc
    yield
    try:
        await _wipe()
    except Exception as exc:
        raise RuntimeError("Redis cleanup failed during teardown") from exc


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
