from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.db import get_session
from app.core.auth import optional_current_user, require_staff
from content.domain.repositories import ContentRepository, ContentMediaRepository
from content.domain.repositories.category_repository import CategoryRepository
from shared.entities.content import ContentOut
from shared.entities.media import ContentMediaOut
from content.domain.entities.content import ContentUpdate
from content.services.content_service import ContentService
from content.services.media_service import ContentMediaService
from content.ports.outbound.indexer_port import IndexerPort
from content.ports.outbound.cache_port import CachePort
from content.adapters.outbound.indexer_opensearch import OpenSearchIndexer
from content.adapters.outbound.cache_redis import RedisCacheAdapter

router = APIRouter(prefix="/v1/contents", tags=["contents"])

def get_indexer() -> IndexerPort:
    return OpenSearchIndexer()

def get_cache() -> CachePort:
    return RedisCacheAdapter()

async def get_services(
    db: AsyncSession = Depends(get_session),
    indexer: IndexerPort = Depends(get_indexer),
    cache: CachePort = Depends(get_cache),
):
    return (ContentService(ContentRepository(db), CategoryRepository(db), ContentMediaRepository(db), indexer=indexer, cache=cache),
            ContentMediaService(ContentMediaRepository(db), indexer=indexer, cache=cache))



@router.post(
    "",
    summary="Create content (staff only)",
    description=(
        "Creates a new content item (podcast episode, documentary, etc.).\n\n"
        "**Auth:** Editors/Admins only (via `require_staff`).\n\n"
        "**Body shape:** validated by the domain entity in the service layer "
        "Required fields include at least `title`; optional fields include "
        "`description`, `categories`, `language`, `duration`, and `publication_date`.\n"
    ),
    response_model=ContentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_staff)],
    responses={
        201: {
            "description": "Content created.",
            "content": {
                "application/json": {
                    "examples": {
                        "created": {
                            "summary": "Created content",
                            "value": {
                                "id": "7e6f5a20-5a62-4e25-9b02-8a8af5f1a901",
                                "title": "Episode 1: Origins",
                                "description": "How it all started.",
                                "categories": ["documentary"],
                                "language": "ar",
                                "duration": 1800,
                                "publication_date": "2025-08-01",
                                "created_at": "2025-08-14T20:12:44Z",
                                "updated_at": "2025-08-14T20:12:44Z",
                                "media": {
                                    "id": "2e2e6f0f-2b83-4f1d-8c18-3f6e5b6f7fcd",
                                    "content_id": "7e6f5a20-5a62-4e25-9b02-8a8af5f1a901",
                                    "media_type": "video",
                                    "source": "external",
                                    "media_provider": "youtube",
                                    "media_file": None,
                                    "external_url": "https://youtube.com/watch?v=abc123",
                                    "created_at": "2025-08-14T20:12:44Z",
                                    "updated_at": "2025-08-14T20:12:44Z",
                                },
                            },
                        }
                    }
                }
            },
        },
        401: {"description": "Not authenticated."},
        403: {"description": "Authenticated but not authorized (staff required)."},
    },
)
async def create_content(
    payload: dict,
    services = Depends(get_services),
):
    # payload validated via Pydantic at service layer entities
    content_svc, media_svc = services
    from content.domain.entities.content import ContentCreate
    obj = await content_svc.create(ContentCreate.model_validate(payload))
    media = await media_svc.get_by_parent_id(obj.id)
    return ContentOut(
        id=obj.id,
        title=obj.title,
        description=obj.description,
        categories=[category.name for category in obj.categories],
        language=obj.language,
        duration=obj.duration,
        publication_date=obj.publication_date,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        media=(ContentMediaOut.model_validate(media) if media else None),
    )

@router.patch(
    "/{content_id}",
    summary="Update content (staff only)",
    description=(
        "Partially updates a content item.\n\n"
        "**Auth:** Editors/Admins only. \n\n"
        "Fields are validated."
    ),
    response_model=ContentOut,
    dependencies=[Depends(require_staff)],
    responses={
        200: {"description": "Content updated; full object returned."},
        401: {"description": "Not authenticated."},
        403: {"description": "Authenticated but not authorized (staff required)."},
        404: {"description": "Content not found."},
    },
)
async def update_content(
    content_id: UUID = Path(..., description="Content UUID"),
    payload: ContentUpdate = Body(..., description="Partial update payload"),
    services = Depends(get_services),
):
    content_svc, media_svc = services
    obj = await content_svc.update(content_id, ContentUpdate.model_validate(payload))
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    media = await media_svc.get_by_parent_id(obj.id)
    return ContentOut(
        id=obj.id,
        title=obj.title,
        description=obj.description,
        categories=[category.name for category in obj.categories],
        language=obj.language,
        duration=obj.duration,
        publication_date=obj.publication_date,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        media=(ContentMediaOut.model_validate(media) if media else None),
    )

@router.delete(
    "/{content_id}",
    summary="Delete content (staff only)",
    description="Deletes a content item by ID. Returns `{ \"ok\": true }` on success.",
    dependencies=[Depends(require_staff)],
    responses={
        200: {
            "description": "Deleted.",
            "content": {"application/json": {"examples": {"ok": {"value": {"ok": True}}}}},
        },
        401: {"description": "Not authenticated."},
        403: {"description": "Authenticated but not authorized (staff required)."},
        404: {"description": "Content not found."},
    },
)
async def delete_content(
    content_id: UUID = Path(..., description="Content UUID"),
    services = Depends(get_services),
):
    content_svc, _ = services
    ok = await content_svc.delete(content_id)
    if not ok:
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True}

@router.get(
    "",
    summary="List/browse contents",
    description=(
        "Returns a paginated list of content items. "
        "Searches by full‑text (`q`) and supports filters. "
        "**Auth:** Optional. If provided, additional personalization/visibility may apply."
    ),
    response_model=List[ContentOut],
    dependencies=[Depends(optional_current_user)],
    responses={
        200: {
            "description": "List of content items (paginated via `limit`/`offset`).",
            "content": {
                "application/json": {
                    "examples": {
                        "list": {
                            "summary": "List example",
                            "value": [
                                {
                                    "id": "7e6f5a20-5a62-4e25-9b02-8a8af5f1a901",
                                    "title": "Episode 1: Origins",
                                    "description": "Incredible teams",
                                    "categories": ["documentary", "football"],
                                    "language": "ar",
                                    "duration": 1800,
                                    "publication_date": "2025-08-01",
                                    "created_at": "2025-08-14T20:12:44Z",
                                    "updated_at": "2025-08-14T20:12:44Z",
                                }
                            ],
                        }
                    }
                }
            },
        },
    },
)
async def list_contents(
    q: Optional[str] = Query(None, description="Free-text search query."),
    media_type: Optional[str] = Query(None, pattern="^(audio|video)$", description="Filter by media type."),
    category: Optional[str] = Query(None, description="Filter by category (exact match)."),
    language: Optional[str] = Query(None, description="Filter by language code (e.g., `ar`, `en`)."),
    status: Optional[str] = Query(None, pattern="^(draft|published)$", description="Filter by content status."),
    limit: int = Query(20, ge=1, le=100, description="Page size (1–100)."),
    offset: int = Query(0, ge=0, description="Offset for pagination."),
    services = Depends(get_services),
):
    content_svc, _ = services
    rows = await content_svc.list(q, media_type, category, language, status, limit, offset)
    out: list[ContentOut] = []
    for r in rows:
        out.append(
            ContentOut(
                id=r.id,
                title=r.title,
                description=r.description,
                categories=[category.name for category in r.categories],
                language=r.language,
                duration=r.duration,
                publication_date=r.publication_date,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
        )
    return out

@router.get(
    "/{content_id}",
    summary="Get content by ID",
    description="Fetches a single content item by UUID. **Auth:** Optional.",
    response_model=ContentOut,
    dependencies=[Depends(optional_current_user)],
    responses={
        200: {
            "description": "Content found.",
            "content": {
                "application/json": {
                    "examples": {
                        "content": {
                            "summary": "Content example",
                            "value": {
                                "id": "7e6f5a20-5a62-4e25-9b02-8a8af5f1a901",
                                "title": "Episode 1: Origins",
                                "description": "How it all started.",
                                "categories": ["documentary", "motivational"],
                                "language": "ar",
                                "duration": 1800,
                                "publication_date": "2025-08-01",
                                "created_at": "2025-08-14T20:12:44Z",
                                "updated_at": "2025-08-14T20:12:44Z",
                                "media": {
                                    "id": "2e2e6f0f-2b83-4f1d-8c18-3f6e5b6f7fcd",
                                    "content_id": "7e6f5a20-5a62-4e25-9b02-8a8af5f1a901",
                                    "media_type": "video",
                                    "source": "external",
                                    "media_provider": "youtube",
                                    "media_file": None,
                                    "external_url": "https://youtube.com/watch?v=abc123",
                                    "created_at": "2025-08-14T20:12:44Z",
                                    "updated_at": "2025-08-14T20:12:44Z",
                                },
                            },
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
    services = Depends(get_services),
):
    content_svc, media_svc = services
    obj = await content_svc.get(content_id)
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    media = await media_svc.get_by_parent_id(obj.id)
    return ContentOut(
        id=obj.id,
        title=obj.title,
        description=obj.description,
        categories=obj.categories,
        language=obj.language,
        duration=obj.duration,
        publication_date=obj.publication_date,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        media=(ContentMediaOut.model_validate(media) if media else None),
    )
