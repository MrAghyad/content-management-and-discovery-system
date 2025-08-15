from datetime import datetime
from uuid import UUID

from content.domain.entities.media import ContentMediaBase


class ContentMediaOut(ContentMediaBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True