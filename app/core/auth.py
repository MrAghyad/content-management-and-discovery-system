# app/core/auth.py
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database.db import get_session
from app.core.security import decode_token
from users.repositories.user_repository import UserRepository
from users.models.role import RoleName

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_session),
):
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if not user_id:
            raise ValueError("missing sub")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")

    repo = UserRepository(db)
    user = await repo.get(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="inactive_user")
    return user

def require_role(*roles: str):
    allowed = {r.lower() for r in roles}
    async def dep(user = Depends(get_current_user)):
        user_roles = {r.name.value for r in user.roles}
        if allowed and not (user_roles & allowed):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return user
    return dep

# Helpers
require_admin  = require_role(RoleName.admin.value)
require_editor = require_role(RoleName.editor.value)
require_staff  = require_role(RoleName.admin.value, RoleName.editor.value)
require_viewer = require_role(RoleName.admin.value, RoleName.editor.value, RoleName.viewer.value)

# ---------- Optional auth (public OR authenticated) ----------
def _extract_bearer_token(request: Request) -> str | None:
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth_header:
        return None
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None

async def optional_current_user(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """
    Returns the current user if a valid Bearer token is provided.
    Returns None if no/invalid token is provided (does NOT raise).
    """
    token = _extract_bearer_token(request)
    if not token:
        return None
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
    except Exception:
        # Treat bad/missing token as anonymous (no raise)
        return None

    repo = UserRepository(db)
    user = await repo.get(user_id)
    if not user or not user.is_active:
        return None
    return user
