from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from shared.abstracts.abstract_repository import AbstractRepository
from users.repositories.user_repository import UserRepository
from users.repositories.role_repository import RoleRepository
from users.entities.user import UserCreate
from users.models.user import User
from users.models.role import RoleName
from app.core.security import hash_password

class UserService:
    def __init__(self, users_repo: AbstractRepository, role_repo: AbstractRepository):
        self.users = users_repo
        self.roles = role_repo

    async def create(self, payload: UserCreate) -> User:
        role_enums = [RoleName(r) for r in payload.roles]
        role_objs = await self.roles.ensure(role_enums)
        return await self.users.create(payload.email, hash_password(payload.password), role_objs)

    async def assign_roles(self, user: User, roles: List[str]) -> User:
        role_enums = [RoleName(r) for r in roles]
        role_objs = await self.roles.ensure(role_enums)
        return await self.users.set_roles(user, role_objs)

    async def get_by_email(self, email: str) -> Optional[User]:
        return await self.users.get_by_email(email)

    async def get_by_id(self, user_id) -> Optional[User]:
        return await self.users.get(user_id)
