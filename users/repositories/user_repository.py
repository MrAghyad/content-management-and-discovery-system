from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from shared.abstracts.abstract_repository import AbstractRepository
from users.models.user import User
from users.models.role import Role

class UserRepository(AbstractRepository):
    async def get(self, user_id: UUID) -> Optional[User]:
        stmt = (
            select(User)
            .options(selectinload(User.roles))
            .where(User.id == user_id)
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = (
            select(User)
            .options(selectinload(User.roles))
            .where(User.email == email)
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def create(self, email: str, password_hash: str, roles: List[Role]) -> User:
        user = User(email=email, password_hash=password_hash)
        user.roles = roles
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def set_roles(self, user: User, roles: List[Role]) -> User:
        user.roles = roles
        await self.db.commit()
        await self.db.refresh(user)
        return user


    async def insert(self, obj):
        pass

    async def update(self, entity_id, obj):
        pass

    async def get_by_parent_id(self, id):
        pass

    async def delete(self, entity_id) -> bool:
        pass

    async def list(self, **filters):
        pass