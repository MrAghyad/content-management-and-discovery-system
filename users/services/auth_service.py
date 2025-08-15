from shared.abstracts.abstract_repository import AbstractRepository
from app.core.security import verify_password, create_access_token

class AuthService:
    def __init__(self, repo: AbstractRepository):
        self.repo = repo

    async def login(self, email: str, password: str) -> str:
        user = await self.repo.get_by_email(email)
        if not user or not user.is_active or not verify_password(password, user.password_hash):
            raise ValueError("invalid_credentials")
        roles = [r.name.value for r in user.roles]
        return create_access_token(str(user.id), roles)
