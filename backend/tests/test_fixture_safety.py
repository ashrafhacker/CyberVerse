"""Safety tests for the database and Redis test fixtures.

These guard the fail-closed rules in conftest: schema operations only ever
run against a temporary SQLite file or an explicitly declared test database,
and destructive Redis cleanup only runs against an explicitly declared,
validated test target.
"""

import inspect
import re

import pytest

from tests.conftest import (
    _resolve_database_url,
    _resolve_redis_cleanup,
    _validate_test_database_url,
)

# ---------------------------------------------------------------------------
# Database target validation
# ---------------------------------------------------------------------------


def _clear_test_env(monkeypatch):
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)


def test_defaults_to_temp_sqlite(monkeypatch):
    _clear_test_env(monkeypatch)
    assert _resolve_database_url() is None


def test_plain_database_url_is_never_used(monkeypatch):
    """Application DATABASE_URL alone must fail closed, even when
    ENVIRONMENT=testing claims this is a test run."""
    _clear_test_env(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/cyberverse")
    with pytest.raises(RuntimeError, match="TEST_DATABASE_URL"):
        _resolve_database_url()


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://user:pass@prod-db.example.com:5432/app",
        "postgresql://user:pass@db.example.com:5432/production",
        "postgresql://user:pass@db.example.com:5432/app_staging",
        "postgresql://user:pass@db.example.com:5432/shared_data",
        "sqlite:////var/data/prod.db",
    ],
)
def test_unsafe_test_database_urls_are_rejected(url):
    with pytest.raises(RuntimeError):
        _validate_test_database_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://cyberverse:cyberverse@localhost:5432/cyberverse",
        "postgresql+asyncpg://cyberverse:cyberverse@127.0.0.1:5432/cyberverse_test",
        "postgresql://user:pass@db.example.com:5432/app_test",
        "sqlite+aiosqlite:////tmp/cyberverse_test_xyz.db",
    ],
)
def test_valid_test_database_urls_are_accepted(url):
    assert _validate_test_database_url(url)


def test_remote_unnamed_test_database_is_rejected():
    """Explicit config alone is not enough: the target must identify itself
    as a test target (loopback or test-named database)."""
    with pytest.raises(RuntimeError, match="loopback"):
        _validate_test_database_url("postgresql://user:pass@db.example.com:5432/cyberverse")


def test_non_postgres_scheme_is_rejected():
    with pytest.raises(RuntimeError, match="scheme"):
        _validate_test_database_url("mysql://user:pass@localhost:3306/cyberverse_test")


def test_test_database_url_is_used_when_set(monkeypatch):
    _clear_test_env(monkeypatch)
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql://user:pass@localhost:5432/cyberverse")
    assert _resolve_database_url() == "postgresql+asyncpg://user:pass@localhost:5432/cyberverse"


# ---------------------------------------------------------------------------
# Redis target validation
# ---------------------------------------------------------------------------


def test_unverified_loopback_redis_skips_cleanup(monkeypatch):
    """No TEST_REDIS_URL: loopback target is unproven, so destructive cleanup
    is skipped rather than run against an instance we cannot verify."""
    import tests.conftest as conftest_module

    monkeypatch.delenv("TEST_REDIS_URL", raising=False)
    monkeypatch.setattr(conftest_module, "_cleanup_skip_warned", False)
    with pytest.warns(RuntimeWarning, match="TEST_REDIS_URL"):
        assert _resolve_redis_cleanup("redis://localhost:6379/15") is None


@pytest.mark.parametrize(
    "url",
    [
        "redis://prod-redis.example.com:6379/0",
        "redis://shared-redis.example.com:6379/0",
        "rediss://cache.example.com:6380/0",
    ],
)
def test_unverified_remote_redis_fails_closed(monkeypatch, url):
    monkeypatch.delenv("TEST_REDIS_URL", raising=False)
    with pytest.raises(RuntimeError, match="Redis cleanup blocked"):
        _resolve_redis_cleanup(url)


def test_explicit_test_redis_is_accepted(monkeypatch):
    monkeypatch.setenv("TEST_REDIS_URL", "redis://localhost:6379/15")
    assert _resolve_redis_cleanup("redis://other.example.com:6379/0") == "redis://localhost:6379/15"


def test_explicit_but_unsafe_test_redis_is_rejected(monkeypatch):
    monkeypatch.setenv("TEST_REDIS_URL", "redis://production-redis:6379/0")
    with pytest.raises(RuntimeError, match="production"):
        _resolve_redis_cleanup("redis://localhost:6379/15")


def test_remote_named_test_redis_is_rejected(monkeypatch):
    monkeypatch.setenv("TEST_REDIS_URL", "redis://cache.example.com:6379/0")
    with pytest.raises(RuntimeError, match="loopback"):
        _resolve_redis_cleanup("redis://localhost:6379/15")


def test_cleanup_never_flushes_databases():
    """The fixture may only delete known test key prefixes, never FLUSH*."""
    from tests import conftest as conftest_module

    source = inspect.getsource(conftest_module)
    assert re.search(r"flush(db|all)\s*\(", source, re.IGNORECASE) is None
    assert conftest_module._TEST_REDIS_PREFIXES
