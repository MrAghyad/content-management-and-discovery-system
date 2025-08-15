from typing import Iterable, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from content.domain.models.category import Category
from uuid import uuid4

from shared.abstracts.abstract_repository import AbstractRepository


class CategoryRepository(AbstractRepository):
    async def get_by_names(self, names: Iterable[str]) -> List[Category]:
        namelist = [n.strip() for n in names if n and n.strip()]
        if not namelist:
            return []
        res = await self.db.execute(select(Category).where(Category.name.in_(namelist)))
        return list(res.scalars().all())

    async def ensure_by_names(self, names: Iterable[str]) -> List[Category]:
        wanted = [n.strip() for n in names if n and n.strip()]
        if not wanted:
            return []
        existing = await self.get_by_names(wanted)
        existing_names = {c.name for c in existing}
        missing = [n for n in wanted if n not in existing_names]
        for name in missing:
            self.db.add(Category(id=uuid4(), name=name))
        if missing:
            await self.db.flush()
            # re-select to get managed instances
            return await self.get_by_names(wanted)
        return existing

    async def get_by_parent_id(self, id):
        pass

    async def list(self, **filters):
        pass

    async def insert(self, obj):
        pass

    async def update(self, entity_id, obj):
        pass

    async def delete(self, entity_id) -> bool:
        pass

    async def get(self, entity_id):
        pass