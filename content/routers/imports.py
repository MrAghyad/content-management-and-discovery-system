from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.db import get_session
from app.core.auth import require_staff
from content.domain.entities.imports import ImportUrlIn
from content.services.external_media_providers.import_media_service import ImportService
from content.ports.outbound.cache_port import CachePort
from content.adapters.outbound.cache_redis import RedisCacheAdapter
from content.services.external_media_providers.provider_registry import ProviderRegistry
from content.adapters.outbound.external_media_providers.youtube_provider import YouTubeProvider
from shared.entities.content import ContentOut

router = APIRouter(
    prefix="/v1/import",
    tags=["import"],
    # Admin/Editor only for the whole router
    dependencies=[Depends(require_staff)],
    responses={
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
            "description": "Authenticated but not authorized (staff required).",
            "content": {"application/json": {"examples": {"forbidden": {"value": {"detail": "forbidden"}}}}},
        },
        422: {"description": "Request validation error (Pydantic)."},
    },
)

def get_cache() -> CachePort:
    return RedisCacheAdapter()

async def get_import_service(
    db: AsyncSession = Depends(get_session),
    cache: CachePort = Depends(get_cache),
) -> ImportService:
    # Extensible provider registry (add SoundCloud/Vimeo later)
    registry = ProviderRegistry(providers=[YouTubeProvider()])
    return ImportService(db=db, cache_port=cache, registry=registry)


@router.post(
    "/by-url",
    summary="Import content by external URL (YouTube, etc.)",
    description=(
        "Fetches metadata (and media reference) from a supported external provider and "
        "creates/updates the local content entry accordingly.\n\n"
        "**Currently supported:** YouTube.\n"
        "Future providers (e.g., SoundCloud, Vimeo) can be plugged in via the Provider Registry."
    ),
    response_model=ContentOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Imported successfully. Returns the created/updated content.",
            "content": {
                "application/json": {
                    "examples": {
                        "youtube_success": {
                            "summary": "Imported from YouTube",
                            "value": {
                                "id": "7e6f5a20-5a62-4e25-9b02-8a8af5f1a901",
                                "title": "Inside the City — Ep. 12",
                                "description": "A deep dive into urban design.",
                                "category": "documentary",
                                "language": "en",
                                "duration": 1460,
                                "publication_date": "2025-08-01",
                                "created_at": "2025-08-14T22:00:00Z",
                                "updated_at": "2025-08-14T22:00:00Z",
                                "media": {
                                    "id": "2e2e6f0f-2b83-4f1d-8c18-3f6e5b6f7fcd",
                                    "content_id": "7e6f5a20-5a62-4e25-9b02-8a8af5f1a901",
                                    "media_type": "video",
                                    "source": "external",
                                    "media_provider": "youtube",
                                    "media_file": None,
                                    "external_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                                    "created_at": "2025-08-14T22:00:00Z",
                                    "updated_at": "2025-08-14T22:00:00Z"
                                }
                            }
                        }
                    }
                }
            },
        },
        400: {
            "description": "Unsupported URL or provider fetch failed.",
            "content": {
                "application/json": {
                    "examples": {
                        "unsupported": {
                            "summary": "URL not supported",
                            "value": {"detail": "Unsupported URL or provider fetch failed"},
                        }
                    }
                }
            },
        },
    },
)
async def import_by_url(
    body: ImportUrlIn = Body(
        ...,
        description="Wrapper containing the external media URL to import.",
        examples={
            "youtube": {
                "summary": "YouTube URL",
                "value": {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
            }
        },
    ),
    svc: ImportService = Depends(get_import_service),
):
    """
    Imports content metadata/media reference from a supported provider.

    **Request body**
    - `url` – Full URL of the item on the external provider (e.g., YouTube video URL).

    **Errors**
    - `400` – Unsupported URL or provider failed to fetch data.
    - `401` – Not authenticated.
    - `403` – Not authorized (staff required).
    - `422` – Validation error.
    """
    dto = await svc.import_by_url(str(body.url))
    if not dto:
        raise HTTPException(status_code=400, detail="Unsupported URL or provider fetch failed")
    return dto
