from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, UniqueConstraint, Table, Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from uuid import UUID, uuid4

from app.core.database.base import Base

content_categories = Table(
    "content_categories",
    Base.metadata,
    Column("content_id", PGUUID(as_uuid=True), ForeignKey("contents.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", PGUUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)

class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("name", name="uq_categories_name"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), default=uuid4, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    # reverse relationship (optional; not strictly needed on Category side)
    contents = relationship("Content", secondary=content_categories, back_populates="categories")
