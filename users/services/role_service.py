from shared.abstracts.abstract_repository import AbstractRepository
from users.models.role import Role, RoleName

class RoleService:
    def __init__(self, repo: AbstractRepository):
        self.repo = repo

    async def list_all(self) -> list[Role]:
        return await self.repo.list_all()

    async def ensure_defaults(self) -> list[Role]:
        return await self.repo.ensure([RoleName.admin, RoleName.editor, RoleName.viewer])

    async def get_by_name(self, name: str) -> Role | None:
        try:
            enum_name = RoleName(name)
        except ValueError:
            return None
        return await self.repo.get_by_name(enum_name)
