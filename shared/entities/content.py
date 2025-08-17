from datetime import datetime
from typing import Optional
from uuid import UUID

from content.domain.entities.content import ContentBase
from shared.entities.media import ContentMediaOut


class ContentOut(ContentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    media: Optional[ContentMediaOut] = None

    class Config:
        from_attributes = True