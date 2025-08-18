from typing import Optional
from uuid import UUID

from sqlalchemy import select, delete

from content.domain.models.media import ContentMedia, MediaType, MediaSource, MediaProvider
from content.domain.entities.media import ContentMediaCreate, ContentMediaUpdate
from shared.abstracts.abstract_repository import AbstractRepository


class ContentMediaRepository(AbstractRepository):
    async def get_by_parent_id(self, id: UUID) -> Optional[ContentMedia]:
        res = await self.db.execute(select(ContentMedia).where(ContentMedia.content_id == id))
        return res.scalars().first()

    async def create(self, content_id: UUID, payload: ContentMediaCreate) -> ContentMedia:
        obj = ContentMedia(
            content_id=content_id,
            media_type=MediaType(payload.media_type),
            source=MediaSource(payload.source),
            media_provider=MediaProvider(payload.media_provider or "team"),
            media_file=payload.media_file,
            external_url=str(payload.external_url) if payload.external_url else None,
        )
        self.db.add(obj)
        await self.db.commit()
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, content_id: UUID, payload: ContentMediaUpdate) -> Optional[ContentMedia]:
        obj = await self.get_by_parent_id(content_id)
        if not obj:
            return None
        data = payload.model_dump(exclude_unset=True)
        if "media_type" in data and data["media_type"] is not None:
            obj.media_type = MediaType(data["media_type"])
        if "source" in data and data["source"] is not None:
            obj.source = MediaSource(data["source"])
        if "media_provider" in data and data["media_provider"] is not None:
            obj.media_provider = MediaProvider(data["actual_source"])
        if "media_file" in data:
            obj.media_file = data["media_file"]
        if "external_url" in data:
            obj.external_url = str(data["external_url"]) if data["external_url"] else None

        await self.db.commit()
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, content_id: UUID) -> bool:
        res = await self.db.execute(delete(ContentMedia).where(ContentMedia.content_id == content_id))
        await self.db.commit()
        return res.rowcount > 0


    async def list(self, **filters):
        pass

    async def insert(self, obj):
        pass

    async def get(self, entity_id):
        pass