from typing import Sequence, Optional, List
from uuid import UUID

from sqlalchemy import select, delete, insert
from sqlalchemy.orm import selectinload

from content.domain.models.content import Content, ContentStatus
from content.domain.models.category import Category, content_categories
from content.domain.entities import ContentCreate, ContentUpdate
from shared.abstracts.abstract_repository import AbstractRepository


class ContentRepository(AbstractRepository):

    async def insert(self, payload: ContentCreate) -> Content:
        obj = Content(
            title=payload.title,
            description=payload.description,
            language=payload.language,
            duration=payload.duration,
            publication_date=payload.publication_date,
            status=ContentStatus(payload.status),
        )
        self.db.add(obj)

        await self.db.commit()
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def get(self, content_id: UUID) -> Optional[Content]:
        stmt = (
            select(Content)
            .options(
                selectinload(Content.media),
                selectinload(Content.categories),  # eager-load to avoid lazy IO later
            )
            .where(Content.id == content_id)
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def update(self, content_id: UUID, payload: ContentUpdate) -> Optional[Content]:
        obj = await self.get(content_id)
        if not obj:
            return None
        data = payload.model_dump(exclude_unset=True)

        for field in ["title","description","language","duration","publication_date","status"]:
            if field in data and data[field] is not None:
                if field == "status":
                    setattr(obj, field, ContentStatus(data[field]))
                else:
                    setattr(obj, field, data[field])

        await self.db.commit()
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, content_id: UUID) -> bool:
        # remove join rows first to avoid FK errors if cascade isn't present
        await self.db.execute(
            delete(content_categories).where(content_categories.c.content_id == content_id)
        )
        res = await self.db.execute(
            delete(Content).where(Content.id == content_id)
        )
        # commit so the deletes persist
        await self.db.commit()
        # rowcount can be None on some DBs; coerce safely
        return bool(getattr(res, "rowcount", 0))

    async def list(
        self,
        **filters
    ) -> Sequence[Content]:
        q = filters.get("q", None)
        language = filters.get("language", None)
        status = filters.get("status", None)
        category = filters.get("category", None)
        limit = filters.get("limit", None)
        offset = filters.get("offset", None)

        stmt = select(Content).options(selectinload(Content.media), selectinload(Content.categories))
        if q:
            like = f"%{q}%"
            stmt = stmt.where((Content.title.ilike(like)) | (Content.description.ilike(like)))
        if language:
            stmt = stmt.where(Content.language == language)
        if status:
            stmt = stmt.where(Content.status == ContentStatus(status))
        if category:
            # join through association table to filter by category name
            stmt = (
                stmt.join(content_categories, Content.id == content_categories.c.content_id)
                .join(Category, Category.id == content_categories.c.category_id)
                .where(Category.name == category)
            )

        stmt = stmt.order_by(
            Content.publication_date.desc().nullslast(),
            Content.created_at.desc(),
        ).limit(limit).offset(offset)

        res = await self.db.execute(stmt)
        return res.scalars().unique().all()


    async def list_all(self) -> Sequence[Content]:
        res = await self.db.execute(
            select(Content).options(
                selectinload(Content.media),
                selectinload(Content.categories),
            )
        )
        return res.scalars().all()

    # ----------------------------
    # Category link management (no lazy collection access)
    # ----------------------------

    async def replace_categories(self, content_id: UUID, category_ids: List[UUID]) -> None:
        """
        Replace all category links for a content by manipulating the join table directly.
        This avoids touching Content.categories (which can trigger lazy loads in async).
        """
        # delete existing links
        await self.db.execute(
            delete(content_categories).where(content_categories.c.content_id == content_id)
        )
        await self.db.commit()
        await self.db.flush()

        # insert new links
        if category_ids:
            rows = [{"content_id": content_id, "category_id": cid} for cid in category_ids]
            for row in rows:
                await self.db.execute(insert(content_categories).values(**row))
            await self.db.commit()
            await self.db.flush()

    async def list_category_ids(self, content_id: UUID) -> List[UUID]:
        res = await self.db.execute(
            select(content_categories.c.category_id).where(
                content_categories.c.content_id == content_id
            )
        )
        return [row[0] for row in res.all()]

    async def get_by_parent_id(self, id):
        pass