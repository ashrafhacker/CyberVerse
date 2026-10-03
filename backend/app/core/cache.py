"""
Redis caching layer for CyberVerse API.
Provides high-performance caching for frequent queries with automatic invalidation.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, Callable, TypeVar

import redis.asyncio as redis
import structlog
from redis.asyncio import Redis

from app.core.config import settings

logger = structlog.get_logger("cyberverse.cache")

T = TypeVar("T")

_redis_client: Redis | None = None


async def get_redis_client() -> Redis:
    """Get or create the global Redis client with connection pooling."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
            retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT,
            health_check_interval=settings.REDIS_HEALTH_CHECK_INTERVAL,
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    """Close the Redis connection pool."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None


class CacheService:
    """High-level cache service with key namespacing and TTL management."""

    def __init__(self, prefix: str = None):
        self.prefix = prefix or settings.CACHE_PREFIX

    def _make_key(self, key: str) -> str:
        return f"{self.prefix}{key}"

    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value from cache."""
        try:
            client = await get_redis_client()
            value = await client.get(self._make_key(key))
            if value is None:
                return default
            return json.loads(value)
        except Exception as exc:
            logger.warning("cache.get_failed", key=key, error=str(exc))
            return default

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set a value in cache with TTL."""
        try:
            client = await get_redis_client()
            ttl = ttl or settings.CACHE_DEFAULT_TTL_SECONDS
            await client.setex(self._make_key(key), ttl, json.dumps(value, default=str))
            return True
        except Exception as exc:
            logger.warning("cache.set_failed", key=key, error=str(exc))
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        try:
            client = await get_redis_client()
            result = await client.delete(self._make_key(key))
            return result > 0
        except Exception as exc:
            logger.warning("cache.delete_failed", key=key, error=str(exc))
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        try:
            client = await get_redis_client()
            keys = []
            async for key in client.scan_iter(match=self._make_key(pattern)):
                keys.append(key)
            if keys:
                return await client.delete(*keys)
            return 0
        except Exception as exc:
            logger.warning("cache.delete_pattern_failed", pattern=pattern, error=str(exc))
            return 0

    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        try:
            client = await get_redis_client()
            return await client.exists(self._make_key(key)) > 0
        except Exception as exc:
            logger.warning("cache.exists_failed", key=key, error=str(exc))
            return False

    async def increment(self, key: str, amount: int = 1, ttl: int = None) -> int:
        """Atomically increment a counter."""
        try:
            client = await get_redis_client()
            full_key = self._make_key(key)
            value = await client.incrby(full_key, amount)
            if ttl:
                await client.expire(full_key, ttl)
            return value
        except Exception as exc:
            logger.warning("cache.increment_failed", key=key, error=str(exc))
            return 0


def cached(ttl: int = None, key_prefix: str = ""):
    """
    Decorator to cache function results in Redis.
    
    Usage:
        @cached(ttl=300, key_prefix="courses")
        async def get_courses(db, page=1): ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = CacheService(key_prefix)
            cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator


# Pre-configured cache instances for different domains
course_cache = CacheService("course:")
user_cache = CacheService("user:")
progress_cache = CacheService("progress:")
leaderboard_cache = CacheService("leaderboard:")
threat_intel_cache = CacheService("threat_intel:")
ctf_cache = CacheService("ctf:")
lab_cache = CacheService("lab:")
analytics_cache = CacheService("analytics:")