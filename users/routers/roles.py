from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.db import get_session
from app.core.auth import require_admin
from users.entities.role import RoleOut
from users.repositories.role_repository import RoleRepository
from users.services.role_service import RoleService

router = APIRouter(
    prefix="/v1/roles",
    tags=["roles"],
    dependencies=[Depends(require_admin)],  # Admin-only access
    responses={
        200: {
            "description": "List of roles.",
            "content": {
                "application/json": {
                    "examples": {
                        "example": {
                            "summary": "Roles list",
                            "value": [
                                {"id": "8c6a3a45-2e6c-4a1a-8d8b-9c7f2b0d7a21", "name": "admin",  "created_at": "2025-08-10T12:34:56Z"},
                                {"id": "0b1a98e2-754a-4d63-a53c-18d3b5a0d5e1", "name": "editor", "created_at": "2025-08-10T12:35:05Z"},
                                {"id": "b0efc8b8-1df4-41cf-8b20-0a3f7e0f92d3", "name": "viewer", "created_at": "2025-08-10T12:35:12Z"}
                            ],
                        }
                    }
                }
            },
        },
        401: {
            "description": "Missing/invalid credentials.",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_token": {"summary": "No token", "value": {"detail": "Not authenticated"}},
                        "invalid_token": {"summary": "Bad token", "value": {"detail": "Could not validate credentials"}},
                    }
                }
            },
            "headers": {
                "WWW-Authenticate": {
                    "schema": {"type": "string"},
                    "description": "Authentication scheme (e.g., Bearer).",
                }
            },
        },
        403: {
            "description": "Authenticated but not authorized (admin role required).",
            "content": {
                "application/json": {
                    "examples": {
                        "forbidden": {"summary": "Not admin", "value": {"detail": "forbidden"}},
                    }
                }
            },
        },
        422: {"description": "Request validation error."},
    },
)

def get_role_service(db: AsyncSession = Depends(get_session)) -> RoleService:
    return RoleService(RoleRepository(db))


@router.get(
    "",
    summary="List all roles (admin only)",
    description=(
        "Returns the complete list of system roles. "
        "This endpoint is **restricted to admins** via the `require_admin` dependency.\n\n"
        "### Notes\n"
        "- Typical roles include `admin`, `editor`, and `viewer`.\n"
        "- Use this endpoint to populate role pickers in admin UIs.\n"
    ),
    response_model=list[RoleOut],
    status_code=status.HTTP_200_OK,
)
async def list_roles(svc: RoleService = Depends(get_role_service)):
    """
    **Admin-only**: returns all roles.

    **Response (200)**
    - Array of role objects: `id`, `name`, `created_at`
    """
    roles = await svc.list_all()
    return [RoleOut(id=r.id, name=r.name.value, created_at=r.created_at) for r in roles]