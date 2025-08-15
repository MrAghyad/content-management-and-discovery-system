# app/core/cache.py
from __future__ import annotations

from typing import Any, Optional
import json
import asyncio

# IMPORTANT: use the asyncio namespace
import redis.asyncio as redis

from app.core.config import settings


class Cache:
    def __init__(self) -> None:
        self._redis: Optional[redis.Redis] = None

    async def init(self) -> None:
        # from_url returns an async Redis client object; do NOT await here
        self._redis = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        # Optional sanity check to fail fast if Redis isn’t reachable
        try:
            await self._redis.ping()
        except Exception as e:
            # Re-raise so FastAPI startup fails visibly
            raise RuntimeError(f"Redis not reachable at {settings.redis_url}: {e}") from e

    async def close(self) -> None:
        if self._redis is not None:
            # redis-py v5 has aclose(); v4 uses close()
            close = getattr(self._redis, "aclose", None) or getattr(self._redis, "close", None)
            if asyncio.iscoroutinefunction(close):
                await close()  # type: ignore[arg-type]
            elif callable(close):
                close()        # type: ignore[misc]

    async def get(self, key: str) -> Any | None:
        if self._redis is None:
            return None
        val = await self._redis.get(key)
        if val is None:
            return None
        try:
            return json.loads(val)
        except Exception:
            return val

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        if self._redis is None:
            return False
        payload = json.dumps(value, default=str)
        if ttl and ttl > 0:
            return await self._redis.set(key, payload, ex=ttl)
        return await self._redis.set(key, payload)

    async def delete(self, key: str) -> bool:
        if self._redis is None:
            return False
        return (await self._redis.delete(key)) > 0

    async def delete_prefix(self, prefix: str) -> int:
        """Efficient-ish pattern delete; use with care."""
        if self._redis is None:
            return 0
        total = 0
        # Use scan to avoid blocking Redis
        async for key in self._redis.scan_iter(match=f"{prefix}*"):
            total += await self._redis.delete(key)
        return total


cache = Cache()
