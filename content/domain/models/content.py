from __future__ import annotations
from datetime import date, datetime
from enum import Enum
from uuid import uuid4, UUID

from sqlalchemy import Date, DateTime, Enum as SAEnum, String, Text, Integer, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base
from content.domain.models.category import content_categories


class ContentStatus(str, Enum):
    draft = "draft"
    published = "published"

class Content(Base):
    __tablename__ = "contents"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(20), nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)  # seconds
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[ContentStatus] = mapped_column(SAEnum(ContentStatus, name="content_status"), default=ContentStatus.draft, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # one-to-one to media
    media = relationship("ContentMedia", back_populates="content", uselist=False, cascade="all, delete-orphan")
    categories = relationship("Category", lazy="selectin", secondary=content_categories, back_populates="contents")  # NEW