from typing import Protocol, Optional
from uuid import UUID
from shared.entities.content import ContentOut
from shared.entities.media import ContentMediaOut

class ContentCatalogPort(Protocol):
    async def get_content(self, content_id: UUID) -> Optional[ContentOut]: ...
    async def get_media(self, content_id: UUID) -> Optional[ContentMediaOut]: ...
