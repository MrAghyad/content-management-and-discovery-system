from fastapi import APIRouter, Depends, HTTPException, status, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database.db import get_session
from app.core.auth import require_admin, get_current_user
from users.entities.user import UserCreate, UserOut
from users.entities.role import AssignRoleIn
from users.repositories.role_repository import RoleRepository
from users.repositories.user_repository import UserRepository
from users.services.user_service import UserService

router = APIRouter(prefix="/v1/users", tags=["users"])

def get_user_service(db: AsyncSession = Depends(get_session)) -> UserService:
    return UserService(UserRepository(db=db), RoleRepository(db=db))

# staff can create users
@router.post(
    "",
    summary="Create a new user (admin only)",
    description=(
        "Creates a new user and returns the created record.\n\n"
        "### Notes\n"
        "- **Admin** permissions are required (enforced by `require_admin`).\n"
        "- The returned `roles` field is an array of role names.\n"
    ),
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
    responses={
        201: {
            "description": "User successfully created.",
            "content": {
                "application/json": {
                    "examples": {
                        "created": {
                            "summary": "Created user",
                            "value": {
                                "id": "5d2a8c1f-6c53-4b1a-9f9a-c5f1f3e3c0d1",
                                "email": "editor@example.com",
                                "is_active": True,
                                "roles": ["editor"],
                                "created_at": "2025-08-14T20:30:15Z",
                            },
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
                        "missing": {"summary": "No token", "value": {"detail": "Not authenticated"}},
                        "invalid": {"summary": "Bad token", "value": {"detail": "Could not validate credentials"}},
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
            "description": "Authenticated but not authorized (admin required).",
            "content": {
                "application/json": {"examples": {"forbidden": {"summary": "Not admin", "value": {"detail": "forbidden"}}}}
            },
        },
        409: {
            "description": "Email already exists.",
            "content": {"application/json": {"examples": {"conflict": {"value": {"detail": "email_exists"}}}}},
        },
    },
)
async def create_user(payload: UserCreate, svc: UserService = Depends(get_user_service)):
    """
    **Admin-only** user creation.

    **Request body**
    - `email` – unique email
    - `password` – plain text password to be hashed server-side
    - `is_active` – whether the user is active

    **Errors**
    - `401` Not authenticated
    - `403` Not authorized
    - `409` Email already exists
    - `422` Validation error
    """
    user = await svc.create(payload)
    return UserOut(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        roles=[r.name.value for r in user.roles],
        created_at=user.created_at,
    )

@router.get(
    "/me",
    summary="Get my profile",
    description=(
        "Returns the authenticated user's profile.\n\n"
        "### Notes\n"
        "- Requires a valid `Authorization: Bearer <token>` header.\n"
    ),
    response_model=UserOut,
    responses={
        200: {
            "description": "Current user profile.",
            "content": {
                "application/json": {
                    "examples": {
                        "me": {
                            "summary": "Profile example",
                            "value": {
                                "id": "5d2a8c1f-6c53-4b1a-9f9a-c5f1f3e3c0d1",
                                "email": "editor@example.com",
                                "is_active": True,
                                "roles": ["editor"],
                                "created_at": "2025-08-14T20:30:15Z",
                            },
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
                        "missing": {"summary": "No token", "value": {"detail": "Not authenticated"}},
                        "invalid": {"summary": "Bad token", "value": {"detail": "Could not validate credentials"}},
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
    },
)
async def me(user=Depends(get_current_user)):
    """
    Returns the **current authenticated** user's profile.
    """
    return UserOut(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        roles=[r.name.value for r in user.roles],
        created_at=user.created_at,
    )


@router.put(
    "/{user_id}/roles",
    summary="Set user roles (admin only)",
    description=(
        "Replaces the user's roles with the provided list.\n\n"
        "### Notes\n"
        "- **Admin** permissions required.\n"
        "- Supply an array of role assignments; roles not listed will be removed.\n"
        "- Idempotent: sending the same set multiple times results in the same state.\n"
    ),
    response_model=UserOut,
    dependencies=[Depends(require_admin)],
    responses={
        200: {
            "description": "Roles updated; the full user object is returned.",
            "content": {
                "application/json": {
                    "examples": {
                        "updated": {
                            "summary": "User roles updated",
                            "value": {
                                "id": "5d2a8c1f-6c53-4b1a-9f9a-c5f1f3e3c0d1",
                                "email": "editor@example.com",
                                "is_active": True,
                                "roles": ["admin", "editor"],
                                "created_at": "2025-08-14T20:30:15Z",
                            },
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
                        "missing": {"summary": "No token", "value": {"detail": "Not authenticated"}},
                        "invalid": {"summary": "Bad token", "value": {"detail": "Could not validate credentials"}},
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
            "description": "Authenticated but not authorized (admin required).",
            "content": {
                "application/json": {
                    "examples": {"forbidden": {"summary": "Not admin", "value": {"detail": "forbidden"}}}
                }
            },
        },
        404: {
            "description": "User not found.",
            "content": {"application/json": {"examples": {"not_found": {"value": {"detail": "user_not_found"}}}}},
        },
        422: {"description": "Validation error."},
    },
)
async def set_user_roles(
    user_id: str = Path(..., description="User UUID"),
    payload: list[AssignRoleIn] = Body(default=[], description="List of roles to set (full replacement)"),
    svc: UserService = Depends(get_user_service),
):
    """
    **Admin-only**: Replace the target user's roles with the provided list.

    **Request body** (array of objects)
    - `role` – role name (e.g., `admin`, `editor`, `viewer`)

    **Behavior**
    - Roles not included in the payload are removed.
    - Duplicate roles in the payload are ignored.
    """
    user = await svc.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")
    roles = [p.role for p in payload]
    user = await svc.assign_roles(user, roles)
    return UserOut(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        roles=[r.name.value for r in user.roles],
        created_at=user.created_at,
    )