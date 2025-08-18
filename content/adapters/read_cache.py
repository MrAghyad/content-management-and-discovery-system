import json
from typing import Optional
from uuid import UUID
from content.ports.read_port import CMSReadPort
from shared.entities.content import ContentOut
from shared.entities.media import ContentMediaOut
from app.core.cache import cache
from app.core.config import settings

class CMSReadCache(CMSReadPort):
    def __init__(self, inner: CMSReadPort) -> None:
        self.inner = inner
        self.ttl = settings.cache_ttl_seconds

    async def get_content(self, content_id: UUID) -> Optional[ContentOut]:
        key = f"disc:content:{content_id}"
        if raw := await cache.get(key):
            return ContentOut.model_validate(json.loads(raw))
        obj = await self.inner.get_content(content_id)
        if obj:
            await cache.set(key, obj.model_dump_json(), self.ttl)
        return obj

    async def get_media(self, content_id: UUID) -> Optional[ContentMediaOut]:
        key = f"disc:media:{content_id}"
        if raw := await cache.get(key):
            return ContentMediaOut.model_validate(json.loads(raw))
        obj = await self.inner.get_media(content_id)
        if obj:
            await cache.set(key, obj.model_dump_json(), self.ttl)
        return obj
