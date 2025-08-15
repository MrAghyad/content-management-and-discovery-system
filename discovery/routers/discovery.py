from typing import Optional, List
from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from shared.entities.content import ContentOut
from app.core.auth import optional_current_user
from discovery.services.discovery_service import DiscoveryService
from shared.wiring import get_search_service, get_cms_read_port

router = APIRouter(
    prefix="/v1/discovery",
    tags=["discovery"],
    responses={
        422: {"description": "Request validation error (Pydantic)."},
    },
)


def get_discovery_service(
    search=Depends(get_search_service),
    cms_read=Depends(get_cms_read_port),
) -> DiscoveryService:
    return DiscoveryService(search=search, cms_read=cms_read)


# ==============================
# Search / Browse
# ==============================
@router.get(
    "/search",
    summary="Search/browse contents",
    description=(
        "Full‑text search over the OpenSearch index with optional filters; "
        "results are **hydrated from the CMS** (with cache) before returning.\n\n"
        "**Auth:** Optional — unauthenticated users can browse.\n\n"
        "### Filters\n"
        "- `q`: free‑text query\n"
        "- `media_type`: `audio` or `video`\n"
        "- `category`, `language`\n"
        "- `date_from`, `date_to` (publication date range)\n"
        "- Pagination via `limit` and `offset`\n"
    ),
    response_model=List[ContentOut],
    responses={
        200: {
            "description": "List of matching content items.",
            "content": {
                "application/json": {
                    "examples": {
                        "search_example": {
                            "summary": "Search results",
                            "value": [
                                {
                                    "id": "7e6f5a20-5a62-4e25-9b02-8a8af5f1a901",
                                    "title": "City Stories — Ep. 12",
                                    "description": "A deep dive into urban design.",
                                    "category": "documentary",
                                    "language": "en",
                                    "duration": 1460,
                                    "publication_date": "2025-08-01",
                                    "created_at": "2025-08-14T22:00:00Z",
                                    "updated_at": "2025-08-14T22:05:00Z",
                                    "media": {
                                        "id": "2e2e6f0f-2b83-4f1d-8c18-3f6e5b6f7fcd",
                                        "content_id": "7e6f5a20-5a62-4e25-9b02-8a8af5f1a901",
                                        "media_type": "video",
                                        "source": "external",
                                        "media_provider": "youtube",
                                        "media_file": None,
                                        "external_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                                        "created_at": "2025-08-14T22:00:00Z",
                                        "updated_at": "2025-08-14T22:05:00Z"
                                    }
                                }
                            ],
                        }
                    }
                }
            },
        }
    },
    openapi_extra={
        "x-codeSamples": [
            {
                "lang": "curl",
                "label": "cURL",
                "source": (
                    "curl 'https://api.example.com/v1/discovery/search?q=city&media_type=video"
                    "&date_from=2025-08-01&limit=10&offset=0'"
                ),
            },
            {
                "lang": "javascript",
                "label": "JavaScript (fetch)",
                "source": (
                    "fetch('https://api.example.com/v1/discovery/search?q=city&language=en&limit=5')\n"
                    "  .then(r => r.json())\n"
                    "  .then(console.log);"
                ),
            },
        ]
    },
)
async def browse(
    q: Optional[str] = Query(None, description="Full‑text query."),
    media_type: Optional[str] = Query(None, pattern="^(audio|video)$", description="Filter by media type."),
    category: Optional[str] = Query(None, description="Filter by category (exact match)."),
    language: Optional[str] = Query(None, description="Filter by language code (e.g., `ar`, `en`)."),
    date_from: Optional[date] = Query(None, description="Filter: publication date from (inclusive)."),
    date_to: Optional[date] = Query(None, description="Filter: publication date to (inclusive)."),
    limit: int = Query(20, ge=1, le=100, description="Page size (1–100)."),
    offset: int = Query(0, ge=0, description="Offset for pagination."),
    _user=Depends(optional_current_user),  # optional auth
    svc: DiscoveryService = Depends(get_discovery_service),
):
    """
    Browse/search content using OpenSearch, then hydrate from CMS (cached). Public endpoint (optional auth).
    """
    return await svc.browse(q, media_type, category, language, date_from, date_to, limit, offset)


# ==============================
# Get by ID
# ==============================
@router.get(
    "/contents/{content_id}",
    summary="Get content by ID (discovery)",
    description=(
        "Fetch a single content item by UUID via Discovery. "
        "Data is hydrated from CMS and may be served from cache.\n\n"
        "**Auth:** Optional."
    ),
    response_model=ContentOut,
    responses={
        200: {
            "description": "Content found.",
            "content": {
                "application/json": {
                    "examples": {
                        "content_example": {
                            "summary": "Content example",
                            "value": {
                                "id": "7e6f5a20-5a62-4e25-9b02-8a8af5f1a901",
                                "title": "City Stories — Ep. 12",
                                "description": "A deep dive into urban design.",
                                "categories": ["documentary"],
                                "language": "en",
                                "duration": 1460,
                                "publication_date": "2025-08-01",
                                "created_at": "2025-08-14T22:00:00Z",
                                "updated_at": "2025-08-14T22:05:00Z",
                                "media": {
                                    "id": "2e2e6f0f-2b83-4f1d-8c18-3f6e5b6f7fcd",
                                    "content_id": "7e6f5a20-5a62-4e25-9b02-8a8af5f1a901",
                                    "media_type": "video",
                                    "source": "external",
                                    "media_provider": "youtube",
                                    "media_file": None,
                                    "external_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                                    "created_at": "2025-08-14T22:00:00Z",
                                    "updated_at": "2025-08-14T22:05:00Z"
                                }
                            }
                        }
                    }
                }
            },
        },
        404: {
            "description": "Content not found.",
            "content": {"application/json": {"examples": {"not_found": {"value": {"detail": "not found"}}}}},
        },
    },
)
async def get_content(
    content_id: UUID = Path(..., description="Content UUID"),
    _user=Depends(optional_current_user),  # optional auth
    svc: DiscoveryService = Depends(get_discovery_service),
):
    """
    Fetch a single content item, hydrated from CMS (cached). Public endpoint (optional auth).
    """
    d = await svc.content_detail(content_id)
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return d
