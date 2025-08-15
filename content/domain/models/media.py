from __future__ import annotations
from datetime import datetime
from enum import Enum
from uuid import uuid4, UUID

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base

class MediaType(str, Enum):
    audio = "audio"
    video = "video"

class MediaSource(str, Enum):
    upload = "upload"
    external = "external"

class MediaProvider(str, Enum):         # NEW — where external media comes from
    team = "team"
    youtube = "youtube"

class ContentMedia(Base):
    __tablename__ = "content_media"
    __table_args__ = (
        UniqueConstraint("content_id", name="uq_content_media_content"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    content_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("contents.id", ondelete="CASCADE"), nullable=False)

    media_type: Mapped[MediaType] = mapped_column(SAEnum(MediaType, name="media_type"), nullable=False)
    source: Mapped[MediaSource] = mapped_column(SAEnum(MediaSource, name="media_source"), nullable=False)
    media_provider: Mapped[MediaProvider] = mapped_column(  # NEW
        SAEnum(MediaProvider, name="media_provider"),
        nullable=False,
        default=MediaProvider.team,
    )

    media_file: Mapped[str | None] = mapped_column(String(512), nullable=True)
    external_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    content: Mapped["Content"] = relationship(back_populates="media")
