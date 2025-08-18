import json
from typing import Optional
from uuid import UUID

from content.domain.entities.media import ContentMediaCreate, ContentMediaUpdate
from content.ports.outbound.cache_port import CachePort
from shared.abstracts.abstract_repository import AbstractRepository
from shared.entities.media import ContentMediaOut
from app.core.config import settings
from app.core.cache import cache
from content.tasks.indexing import index_content

def _ck_content(cid: UUID) -> str: return f"disc:content:{cid}"
def _ck_media(cid: UUID) -> str:   return f"disc:media:{cid}"
LIST_PREFIX = "disc:content:list:"

class ContentMediaService:
    def __init__(self, repo :AbstractRepository, cache_port: CachePort):
        self.repo = repo
        self.cache_port = cache_port

    # ---------- Queries (read-through) ----------

    async def get_by_content_id(self, content_id: UUID) -> Optional[ContentMediaOut]:
        key = _ck_media(content_id)
        cached = await cache.get(key)
        if cached:
            return ContentMediaOut.model_validate(cached)
        media = await self.repo.get_by_parent_id(content_id)
        if not media:
            return None
        dto = ContentMediaOut.model_validate(media)
        await cache.set(key, dto.model_dump(mode="json"), ttl=settings.cache_ttl_seconds)
        return dto

    # ---------- Mutations (update cache + index async) ----------

    async def create(self, content_id: UUID, payload: ContentMediaCreate):
        media = await self.repo.create(content_id, payload)

        # refresh media + content caches
        await cache.set(_ck_media(content_id), ContentMediaOut.model_validate(media).model_dump(mode="json"),
                        ttl=settings.cache_ttl_seconds)

        # async reindex the content doc
        index_content.delay(str(content_id))
        return media

    async def update(self, content_id: UUID, payload: ContentMediaUpdate):
        media = await self.repo.update(content_id, payload)
        if not media:
            return None

        await cache.set(_ck_media(content_id), ContentMediaOut.model_validate(media).model_dump(mode="json"),
                        ttl=settings.cache_ttl_seconds)

        index_content.delay(str(content_id))
        return media

    async def delete(self, content_id: UUID) -> bool:
        ok = await self.repo.delete(content_id)
        if ok:
            # remove media key; refresh content key to reflect missing media
            await self.cache_port.delete_keys(_ck_media(content_id))

            index_content.delay(str(content_id))  # reindex without media
        return ok
