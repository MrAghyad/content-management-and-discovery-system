from typing import Sequence, Optional
from uuid import UUID

from content.domain.entities.content import ContentCreate, ContentUpdate
from content.ports.outbound.cache_port import CachePort
from shared.abstracts.abstract_repository import AbstractRepository
from shared.entities.content import ContentOut
from shared.entities.media import ContentMediaOut
from app.core.config import settings
from app.core.cache import cache
from content.tasks.indexing import index_content, delete_content_index


def _ck_content(cid: UUID) -> str: return f"disc:content:{cid}"
def _ck_media(cid: UUID) -> str:   return f"disc:media:{cid}"
LIST_PREFIX = "disc:content:list:"

class ContentService:
    def __init__(self, repo: AbstractRepository, categories_repo: AbstractRepository, media_repo: AbstractRepository, cache_port: CachePort):
        self.repo = repo
        self.categories_repo = categories_repo
        self.media_repo = media_repo
        self.cache_port = cache_port

    # ---------- Mutations (update cache + index async) ----------

    async def create(self, payload: ContentCreate):
        obj = await self.repo.insert(payload)
        await self.append_categories_to_content(payload.categories, obj)
        # hydrate media and build DTO
        media = await self.media_repo.get_by_parent_id(obj.id)
        dto = _to_detail_dto(obj, media)
        # write-through: set item cache
        await cache.set(_ck_content(obj.id), dto.model_dump(mode="json"), ttl=settings.cache_ttl_seconds)
        if media:
            await cache.set(_ck_media(obj.id), ContentMediaOut.model_validate(media).model_dump(mode="json"),
                            ttl=settings.cache_ttl_seconds)
        # invalidate list caches
        await self.cache_port.delete_prefix(LIST_PREFIX)
        # async index
        index_content.delay(str(obj.id))
        return obj

    async def append_categories_to_content(self, categories, content):
        cats = await self.categories_repo.ensure_by_names(categories or [])
        content.categories = cats
        await self.repo.commit(content)

    async def update(self, content_id: UUID, payload: ContentUpdate):
        obj = await self.repo.update(content_id, payload)
        if not obj:
            return None

        if "categories" in payload and payload["categories"] is not None:
            await self.append_categories_to_content(payload.categories, obj)

        media = await self.media_repo.get_by_parent_id(content_id)
        dto = _to_detail_dto(obj, media)
        # write-through: update caches
        await cache.set(_ck_content(content_id), dto.model_dump(mode="json"), ttl=settings.cache_ttl_seconds)
        if media:
            await cache.set(_ck_media(content_id), ContentMediaOut.model_validate(media).model_dump(mode="json"),
                            ttl=settings.cache_ttl_seconds)
        else:
            await self.cache_port.delete_keys(_ck_media(content_id))
        # invalidate list caches
        await self.cache_port.delete_prefix(LIST_PREFIX)
        # async index
        index_content.delay(str(content_id))
        return obj

    async def delete(self, content_id: UUID) -> bool:
        ok = await self.repo.delete(content_id)
        if ok:
            # remove item caches + list caches
            await self.cache_port.delete_keys(_ck_content(content_id), _ck_media(content_id))
            await self.cache_port.delete_prefix(LIST_PREFIX)
            # async index delete
            delete_content_index.delay(str(content_id))
        return ok

    # ---------- Queries (read-through) ----------

    async def get(self, content_id: UUID) -> Optional[ContentOut]:
        key = _ck_content(content_id)
        cached = await cache.get(key)
        if cached:
            return ContentOut.model_validate(cached)

        obj = await self.repo.get(content_id)
        if not obj:
            return None
        media = await self.media_repo.get_by_parent_id(content_id)
        dto = _to_detail_dto(obj, media)
        await cache.set(key, dto.model_dump(mode="json"), ttl=settings.cache_ttl_seconds)
        if media:
            await cache.set(_ck_media(content_id), ContentMediaOut.model_validate(media).model_dump(mode="json"),
                            ttl=settings.cache_ttl_seconds)
        return dto

    async def list(
        self, q: str | None, media_type: str | None, category: str | None,
        language: str | None, status: str | None, limit: int, offset: int,
    ) -> Sequence[ContentOut]:
        list_key = f"{LIST_PREFIX}{q}:{media_type}:{category}:{language}:{status}:{limit}:{offset}"
        cached = await cache.get(list_key)
        if cached:
            return [ContentOut.model_validate(item) for item in cached]

        rows = await self.repo.list(q, media_type, category, language, status, limit, offset)
        result: list[ContentOut] = []
        for row in rows:
            media = row.media or await self.media_repo.get_by_parent_id(row.id)
            result.append(_to_detail_dto(row, media))

        await cache.set(list_key, [dto.model_dump(mode="json") for dto in result],
                        ttl=settings.cache_ttl_seconds)
        return result


# --- local helper ---
def _to_detail_dto(obj, media) -> ContentOut:
    return ContentOut(
        id=obj.id,
        title=obj.title,
        description=obj.description,
        category=obj.category,
        language=obj.language,
        duration=obj.duration,
        publication_date=obj.publication_date,
        categories=[c.name for c in (obj.categories or [])],
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        media=(ContentMediaOut.model_validate(media) if media else None),
    )
