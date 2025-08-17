from __future__ import annotations

from typing import Iterable, List, Optional, Sequence
from uuid import UUID, uuid4

from sqlalchemy import select, delete, update as sa_update
from sqlalchemy.exc import IntegrityError

from content.domain.models.category import Category
from shared.abstracts.abstract_repository import AbstractRepository


class CategoryRepository(AbstractRepository):
    # ---------- Query helpers ----------

    async def get_by_names(self, names: Iterable[str]) -> List[Category]:
        namelist = [n.strip() for n in names if n and n.strip()]
        if not namelist:
            return []
        res = await self.db.execute(select(Category).where(Category.name.in_(namelist)))
        return list(res.scalars().all())

    async def get_by_ids(self, ids: Iterable[UUID]) -> List[Category]:
        idlist = [cid for cid in ids if cid]
        if not idlist:
            return []
        res = await self.db.execute(select(Category).where(Category.id.in_(idlist)))
        return list(res.scalars().all())

    async def ensure_by_names(self, names: Iterable[str]) -> List[Category]:
        """
        Ensure all given category names exist. Returns the managed Category objects
        (existing or newly created). Uses a simple insert-on-miss strategy and then re-selects.
        """
        wanted = [n.strip() for n in names if n and n.strip()]
        if not wanted:
            return []

        existing = await self.get_by_names(wanted)
        existing_names = {c.name for c in existing}
        missing = [n for n in wanted if n not in existing_names]

        for name in missing:
            self.db.add(Category(id=uuid4(), name=name))

        if missing:
            # Flush once (single round-trip) then re-select to return managed instances
            try:
                await self.db.commit()
                await self.db.flush()
            except IntegrityError:
                # In case of concurrent creation, ignore and just re-read
                await self.db.rollback()

            # IMPORTANT: do not leave the tx rolled back; start a new one contextually if needed.
            # Most of your services call commit later anyway.
            existing = await self.get_by_names(wanted)

        return existing

    # ---------- AbstractRepository CRUD ----------

    async def insert(self, obj: Category) -> Category:
        """
        Insert a Category instance. If you pass a plain name, prefer ensure_by_names().
        """
        if obj.id is None:
            obj.id = uuid4()
        self.db.add(obj)
        await self.db.commit()
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def get(self, entity_id: UUID) -> Optional[Category]:
        res = await self.db.execute(select(Category).where(Category.id == entity_id))
        return res.scalars().first()

    async def update(self, entity_id: UUID, obj: Category) -> Optional[Category]:
        """
        Update the name (or other future fields) of a Category.
        """
        # If you prefer ORM approach, you can load and mutate. The SQL form is fewer round-trips.
        await self.db.execute(
            sa_update(Category)
            .where(Category.id == entity_id)
            .values(name=obj.name)
        )
        # Return the fresh row
        return await self.get(entity_id)

    async def delete(self, entity_id: UUID) -> bool:
        res = await self.db.execute(delete(Category).where(Category.id == entity_id))
        return res.rowcount > 0

    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[Category]:
        stmt = select(Category).order_by(Category.name.asc()).limit(limit).offset(offset)
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def list_all(self) -> Sequence[Category]:
        res = await self.db.execute(select(Category).order_by(Category.name.asc()))
        return res.scalars().all()

    # Not applicable for this aggregate
    async def get_by_parent_id(self, id):
        raise NotImplementedError("Category has no parent relation in this model")
