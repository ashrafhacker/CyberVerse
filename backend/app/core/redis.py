import logging
from typing import Any, Optional

import redis.asyncio as aioredis
from fastapi import Request

from app.core.config import settings


class RedisClient:
    """Async Redis client wrapper with cache helpers."""

    _instance: aioredis.Redis | None = None

    @classmethod
    async def get_client(cls) -> aioredis.Redis:
        if cls._instance is None:
            cls._instance = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
            )
        return cls._instance

    @classmethod
    async def close(cls) -> None:
        if cls._instance is not None:
            await cls._instance.aclose()
            cls._instance = None

    @classmethod
    async def get(cls, key: str) -> str | None:
        client = await cls.get_client()
        return await client.get(key)

    @classmethod
    async def set(cls, key: str, value: str, ttl: int | None = None) -> None:
        client = await cls.get_client()
        if ttl:
            await client.set(key, value, ex=ttl)
        else:
            await client.set(key, value)

    @classmethod
    async def delete(cls, key: str) -> None:
        client = await cls.get_client()
        await client.delete(key)

    @classmethod
    async def increment(cls, key: str, amount: int = 1, ttl: int | None = None) -> int:
        client = await cls.get_client()
        value = await client.incr(key, amount)
        if ttl and value == amount:
            await client.expire(key, ttl)
        return value

    @classmethod
    async def cache_get_json(cls, key: str) -> Any:
        value = await cls.get(key)
        if value:
            import json
            return json.loads(value)
        return None

    @classmethod
    async def cache_set_json(cls, key: str, data: Any, ttl: int | None = None) -> None:
        import json
        await cls.set(key, json.dumps(data, default=str), ttl=ttl)


async def get_redis() -> aioredis.Redis:
    return await RedisClient.get_client()


class RateLimiter:
    """
    Sliding window rate limiter backed by Redis.

    Fails OPEN: if Redis is unavailable the request is allowed through
    (availability over strictness), and the event is logged.
    """

    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
        prefix: str = "ratelimit",
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.prefix = prefix

    def key_for(self, identifier: str, scope: str = "default") -> str:
        return f"{self.prefix}:{scope}:{identifier}"

    async def is_allowed(self, identifier: str, scope: str = "default") -> bool:
        try:
            key = self.key_for(identifier, scope)
            current = await RedisClient.increment(key, 1, ttl=self.window_seconds)
            return current <= self.max_requests
        except Exception:
            logging.getLogger(__name__).warning(
                "rate_limit_redis_unavailable", exc_info=True
            )
            return True

    async def remaining(self, identifier: str, scope: str = "default") -> int:
        key = self.key_for(identifier, scope)
        client = await RedisClient.get_client()
        current = await client.get(key)
        count = int(current or 0)
        return max(0, self.max_requests - count)

    @classmethod
    def from_request(
        cls,
        request: Request,
        max_requests: Optional[int] = None,
        window_seconds: Optional[int] = None,
    ) -> "RateLimiter":
        return cls(
            max_requests=max_requests or settings.RATE_LIMIT_REQUESTS,
            window_seconds=window_seconds or settings.RATE_LIMIT_WINDOW,
        )

    @classmethod
    async def check(
        cls,
        request: Request,
        max_requests: Optional[int] = None,
        window_seconds: Optional[int] = None,
        scope: str = "default",
    ) -> bool:
        limiter = cls.from_request(request, max_requests, window_seconds)
        forwarded = request.headers.get("x-forwarded-for")
        ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
        return await limiter.is_allowed(ip, scope)


async def healthcheck() -> bool:
    try:
        client = await RedisClient.get_client()
        await client.ping()
        return True
    except Exception:
        return False
