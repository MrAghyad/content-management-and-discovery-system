from datetime import datetime
from typing import Optional
from uuid import UUID

from content.domain.entities.media import ContentMediaBase


class ContentMediaOut(ContentMediaBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True