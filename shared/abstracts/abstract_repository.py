from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession


class AbstractRepository(ABC):
    """
    Minimal, framework-agnostic repository contract.

    Concrete implementations should implement these operations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    @abstractmethod
    async def insert(self, obj): ...

    @abstractmethod
    async def update(self, entity_id, obj): ...

    @abstractmethod
    async def get_by_parent_id(self, id): ...

    @abstractmethod
    async def delete(self, entity_id) -> bool: ...

    @abstractmethod
    async def get(self, entity_id): ...

    @abstractmethod
    async def list(self, **filters): ...

    async def commit(self, obj):
        await self.db.commit()
        await self.db.flush()
        await self.db.refresh(obj)