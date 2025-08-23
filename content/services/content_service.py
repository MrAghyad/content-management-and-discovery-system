from typing import Sequence, Optional, List
from uuid import UUID

from content.domain.entities.content import ContentCreate, ContentUpdate
from content.ports.outbound.cache_port import CachePort
from shared.abstracts.abstract_repository import AbstractRepository
from shared.entities.content import ContentOut
from shared.entities.media import ContentMediaOut
from app.core.config import settings
from content.tasks.indexing import index_content, delete_content_index

def _ck_content(cid: UUID) -> str: return f"disc:content:{cid}"
def _ck_media(cid: UUID) -> str:   return f"disc:media:{cid}"

class ContentService:
    """
    Write-through caching for single-content documents only.
    - On create/update: refresh item caches for content and media.
    - On delete: evict item caches for content and media only.
    No list cache (keeps invalidation trivial and correctness high).
    """

    def __init__(
        self,
        repo: AbstractRepository,                 # ContentRepository
        categories_repo: AbstractRepository,      # CategoryRepository
        media_repo: AbstractRepository,           # ContentMediaRepository
        cache_port: CachePort,                    # RedisCacheAdapter (or FakeCache in tests)
    ):
        self.repo = repo
        self.categories_repo = categories_repo
        self.media_repo = media_repo
        self.cache = cache_port

    # ---------- Mutations (update cache + index async) ----------

    async def create(self, payload: ContentCreate):
        obj = await self.repo.insert(payload)

        # categories -> ensure and link via association table (no lazy loads)
        await self._replace_categories(obj, payload.categories or [])

        # hydrate media and build DTO
        media = await self.media_repo.get_by_parent_id(obj.id)
        await self.repo.commit(obj)
        dto = _to_detail_dto(obj, media)

        # write-through: set item caches (store plain dicts; adapter handles serialization)
        await self.cache.set(_ck_content(obj.id), dto.model_dump(mode="json"), ttl=settings.cache_ttl_seconds)
        if media:
            await self.cache.set(
                _ck_media(obj.id),
                ContentMediaOut.model_validate(media).model_dump(mode="json"),
                ttl=settings.cache_ttl_seconds,
            )

        # async index only the single doc
        index_content.apply_async((str(obj.id),), countdown=2)
        return dto

    async def update(self, content_id: UUID, payload: ContentUpdate):
        obj = await self.repo.update(content_id, payload)
        if not obj:
            return None

        # categories replacement if explicitly provided
        if payload.categories is not None:
            await self._replace_categories(obj, payload.categories)

        media = await self.media_repo.get_by_parent_id(content_id)
        dto = _to_detail_dto(obj, media)

        # write-through: update item caches
        await self.cache.set(_ck_content(content_id), dto.model_dump(mode="json"), ttl=settings.cache_ttl_seconds)
        if media:
            await self.cache.set(
                _ck_media(content_id),
                ContentMediaOut.model_validate(media).model_dump(mode="json"),
                ttl=settings.cache_ttl_seconds,
            )
        else:
            # if media absent, evict its key only
            await self.cache.delete_keys(_ck_media(content_id))

        # async index this one doc
        index_content.delay(str(content_id))
        return dto

    async def delete(self, content_id: UUID) -> bool:
        ok = await self.repo.delete(content_id)
        if ok:
            # remove only this content’s item caches
            await self.cache.delete_keys(_ck_content(content_id), _ck_media(content_id))
            # async index delete
            delete_content_index.delay(str(content_id))
        return ok

    # ---------- Queries (read-through, item only) ----------

    async def get(self, content_id: UUID) -> Optional[ContentOut]:
        key = _ck_content(content_id)
        cached = await self.cache.get(key)
        if cached:
            # cached is already a dict from the adapter; no json.loads
            return ContentOut.model_validate(cached)

        obj = await self.repo.get(content_id)
        if not obj:
            return None

        media = await self.media_repo.get_by_parent_id(content_id)
        dto = _to_detail_dto(obj, media)

        await self.cache.set(key, dto.model_dump(mode="json"), ttl=settings.cache_ttl_seconds)
        if media:
            await self.cache.set(
                _ck_media(content_id),
                ContentMediaOut.model_validate(media).model_dump(mode="json"),
                ttl=settings.cache_ttl_seconds,
            )
        return dto

    async def list(
        self,
        q: str | None,
        media_type: str | None,
        category: str | None,
        language: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> Sequence[ContentOut]:
        """
        No list cache by design. This keeps correctness and avoids broad invalidations.
        If later needed, move to tag-based caching (e.g., per-category tag) or per-query TTL cache.
        """
        rows = await self.repo.list(
            **{
                "q": q,
                "media_type": media_type,
                "category": category,
                "language": language,
                "status": status,
                "limit": limit,
                "offset": offset,
            }
        )
        result: list[ContentOut] = []
        for row in rows:
            # row.media may be eager-loaded; fallback to repo if not
            media = row.media or await self.media_repo.get_by_parent_id(row.id)
            result.append(_to_detail_dto(row, media))
        return result

    # ---------- Internal helpers ----------

    async def _replace_categories(self, obj, category_names: List[str]) -> None:
        """
        Ensure category rows exist and replace links via join table.
        """
        cats = await self.categories_repo.ensure_by_names(category_names)
        cat_ids = [c.id for c in cats]
        if hasattr(self.repo, "replace_categories"):
            await self.repo.replace_categories(obj.id, cat_ids)  # type: ignore[attr-defined]
            await self.repo.commit(obj)
        else:
            raise RuntimeError("ContentRepository.replace_categories is required")


# --- local helper ---
def _to_detail_dto(obj, media) -> ContentOut:
    return ContentOut(
        id=obj.id,
        title=obj.title,
        description=obj.description,
        language=obj.language,
        duration=obj.duration,
        publication_date=obj.publication_date,
        categories=[c.name for c in (obj.categories or [])],
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        status=obj.status,
        media=(ContentMediaOut.model_validate(media) if media else None),
    )
