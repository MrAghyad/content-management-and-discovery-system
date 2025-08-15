from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Iterable, List

from shared.abstracts.abstract_repository import AbstractRepository
from users.models.role import Role, RoleName

class RoleRepository(AbstractRepository):
    async def get_by_name(self, name: RoleName) -> Optional[Role]:
        res = await self.db.execute(select(Role).where(Role.name == name))
        return res.scalar_one_or_none()

    async def list_all(self) -> List[Role]:
        res = await self.db.execute(select(Role).order_by(Role.name))
        return list(res.scalars())

    async def ensure(self, names: Iterable[RoleName]) -> list[Role]:
        roles: list[Role] = []
        for n in names:
            role = await self.get_by_name(n)
            if not role:
                role = Role(name=n)
                self.db.add(role)
                await self.db.flush()
            roles.append(role)
        return roles


    async def insert(self, obj):
        pass

    async def update(self, entity_id, obj):
        pass

    async def get_by_parent_id(self, id):
        pass

    async def delete(self, entity_id) -> bool:
        pass

    async def get(self, entity_id):
        pass

    async def list(self, **filters):
        pass
