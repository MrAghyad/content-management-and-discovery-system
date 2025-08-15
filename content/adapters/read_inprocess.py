from typing import Optional
from uuid import UUID

from content.ports.read_port import CMSReadPort
from content.services.content_service import ContentService
from content.services.media_service import ContentMediaService
from shared.entities.content import ContentOut
from shared.entities.media import ContentMediaOut

class CMSInProcessAdapter(CMSReadPort):
    def __init__(self, content_service: ContentService, media_service: ContentMediaService) -> None:
        self._content = content_service
        self._media = media_service

    async def get_content(self, content_id: UUID) -> Optional[ContentOut]:
        obj = await self._content.get(content_id)
        if not obj:
            return None
        media = await self._media.get_by_content_id(content_id)
        return ContentOut(
            id=obj.id,
            title=obj.title,
            description=obj.description,
            category=obj.category,
            language=obj.language,
            duration=obj.duration,
            publication_date=obj.publication_date,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
            media=(ContentMediaOut.model_validate(media) if media else None),
        )

    async def get_media(self, content_id: UUID) -> Optional[ContentMediaOut]:
        media = await self._media.get_by_content_id(content_id)
        return ContentMediaOut.model_validate(media) if media else None
