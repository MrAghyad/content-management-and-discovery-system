from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database.db import get_session
from users.entities.auth import LoginIn, TokenOut
from users.repositories.user_repository import UserRepository
from users.services.auth_service import AuthService

router = APIRouter(
    prefix="/v1/auth",
    tags=["auth"],
)

def get_auth_service(db: AsyncSession = Depends(get_session)) -> AuthService:
    return AuthService(UserRepository(db))

@router.post(
    "/token",
    summary="Issue JWT access token",
    description=(
        "Authenticates a user with email and password and returns a short‑lived JWT access token.\n\n"
        "### Notes\n"
        "- Use this token in the `Authorization: Bearer <token>` header for protected endpoints.\n"
        "- The token reflects the user's active status and current roles at issuance time.\n"
        "- If credentials are invalid or the account is inactive, the server returns **401 Unauthorized**.\n"
    ),
    response_model=TokenOut,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Authentication succeeded; JWT returned.",
            "content": {
                "application/json": {
                    "examples": {
                        "success": {
                            "summary": "Successful login",
                            "value": {"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
                        }
                    }
                }
            },
            "headers": {
                "Cache-Control": {
                    "schema": {"type": "string"},
                    "description": "Clients should not cache tokens.",
                }
            },
        },
        401: {
            "description": "Invalid email or password, or user is inactive.",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_credentials": {
                            "summary": "Bad email/password",
                            "value": {"detail": "invalid_credentials"},
                        },
                        "inactive_user": {
                            "summary": "User is inactive",
                            "value": {"detail": "inactive_user"},
                        },
                    }
                }
            },
            "headers": {
                "WWW-Authenticate": {
                    "schema": {"type": "string"},
                    "description": "Authentication scheme required (e.g., Bearer).",
                }
            },
        },
    },
)
async def issue_token(
    payload: LoginIn,
    svc: AuthService = Depends(get_auth_service),
):
    """
    Authenticate with email & password and receive a JWT.

    **Request body**
    - `email` – user email (string, required)
    - `password` – user password (string, required)

    **Successful response (200)**
    - `access_token` – JWT string to send as `Authorization: Bearer <token>`

    **Errors**
    - `401 invalid_credentials` – Email/password mismatch
    - `401 inactive_user` – User exists but is not active
    - `422` – Validation error (malformed email, missing fields, etc.)
    """
    try:
        token = await svc.login(payload.email, payload.password)
    except ValueError:
        # Keep the exact error contract your clients expect
        # Consider returning 'inactive_user' if your service distinguishes it
        # and raising HTTP 401 accordingly.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenOut(access_token=token)