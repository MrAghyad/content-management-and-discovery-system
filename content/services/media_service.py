from uuid import UUID
from typing import Optional

from app.core.config import settings
from content.ports.outbound.cache_port import CachePort
from shared.abstracts.abstract_repository import AbstractRepository
from shared.entities.media import ContentMediaOut
from content.tasks.indexing import index_content

def _ck_media(cid: UUID) -> str:   return f"disc:media:{cid}"

class ContentMediaService:
    def __init__(self, repo :AbstractRepository, cache_port: CachePort):
        self.repo = repo
        self.cache_port = cache_port

    # ---------- Queries ----------

    async def get_by_content_id(self, content_id: UUID) -> Optional[ContentMediaOut]:
        key = _ck_media(content_id)
        cached = await self.cache_port.get(key)
        if cached:
            # The cache adapter for tests returns a dict (not a raw JSON string)
            return ContentMediaOut.model_validate(cached)

        media = await self.repo.get_by_parent_id(content_id)
        if not media:
            return None

        dto = ContentMediaOut.model_validate(media)
        await self.cache_port.set(key, dto.model_dump(mode="json"), ttl=settings.cache_ttl_seconds)
        return dto

    # ---------- Mutations ----------

    async def create(self, content_id: UUID, payload) -> ContentMediaOut:
        media = await self.repo.create(content_id, payload)
        # persist + refresh (repo handles session work)
        dto = ContentMediaOut.model_validate(media)

        # write-through
        await self.cache_port.set(_ck_media(content_id), dto.model_dump(mode="json"), ttl=settings.cache_ttl_seconds)
        # async reindex the content doc
        index_content.delay(str(content_id))

        return dto

    async def update(self, content_id: UUID, payload) -> Optional[ContentMediaOut]:
        media = await self.repo.update(content_id, payload)
        if not media:
            return None

        dto = ContentMediaOut.model_validate(media)
        # write-through
        await self.cache_port.set(_ck_media(content_id), dto.model_dump(mode="json"), ttl=settings.cache_ttl_seconds)
        # async reindex the content doc
        index_content.delay(str(content_id))
        return dto

    async def delete(self, content_id: UUID) -> bool:
        ok = await self.repo.delete(content_id)
        if ok:
            # evict only this media key
            await self.cache_port.delete_keys(_ck_media(content_id))
            # async reindex the content doc
            index_content.delay(str(content_id))
        return ok
