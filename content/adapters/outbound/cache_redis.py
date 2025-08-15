from __future__ import annotations
from typing import Any

from content.ports.outbound.cache_port import CachePort
from app.core.cache import cache  # <- shared singleton managed in app lifespan


class RedisCacheAdapter(CachePort):
    """
    Thin adapter that delegates to the shared async cache client in app.core.cache.
    Ensures all components use the same Redis connection and lifecycle.
    """

    async def get(self, key: str) -> Any | None:
        return await cache.get(key)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        return await cache.set(key, value, ttl)

    async def delete(self, key: str) -> bool:
        return await cache.delete(key)

    async def delete_prefix(self, prefix: str) -> int:
        return await cache.delete_prefix(prefix)
