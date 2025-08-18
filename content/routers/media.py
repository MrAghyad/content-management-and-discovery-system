from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.db import get_session
from app.core.auth import require_staff, optional_current_user
from content.domain.entities import ContentMediaCreate, ContentMediaUpdate
from content.domain.repositories import ContentMediaRepository
from shared.entities.media import ContentMediaOut
from content.services.media_service import ContentMediaService
from content.ports.outbound.indexer_port import IndexerPort
from content.ports.outbound.cache_port import CachePort
from content.adapters.outbound.indexer_opensearch import OpenSearchIndexer
from content.adapters.outbound.cache_redis import RedisCacheAdapter

router = APIRouter(prefix="/v1/contents/{content_id}/media", tags=["media"])

def get_indexer() -> IndexerPort:
    return OpenSearchIndexer()

def get_cache() -> CachePort:
    return RedisCacheAdapter()

async def get_service(
    db: AsyncSession = Depends(get_session),
    indexer: IndexerPort = Depends(get_indexer),
    cache: CachePort = Depends(get_cache),
):
    return ContentMediaService(ContentMediaRepository(db), cache_port=cache)

@router.get(
    "",
    summary="Get content media by content ID",
    description="Returns the media record (audio/video) for the given content. **Auth:** Optional.",
    response_model=ContentMediaOut,
    dependencies=[Depends(optional_current_user)],
    responses={
        200: {"description": "Media found."},
        404: {"description": "Media not found for this content."},
    },
)
async def get_media(
    content_id: UUID = Path(..., description="Content UUID"),
    media_svc = Depends(get_service),
):
    media = await media_svc.get_by_content_id(content_id)
    if not media:
        raise HTTPException(status_code=404, detail="not found")
    return ContentMediaOut.model_validate(media)

@router.post(
    "",
    summary="Create media for a content item (staff only)",
    description=(
        "Creates a media record (audio/video) for the specified content. "
        "Media can be uploaded or external (e.g., YouTube). **Auth:** Editors/Admins only."
    ),
    response_model=ContentMediaOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_staff)],
    responses={
        201: {"description": "Media created."},
        401: {"description": "Not authenticated."},
        403: {"description": "Authenticated but not authorized (staff required)."},
        409: {"description": "Media already exists for this content (if unique 1:1)."},
    },
)
async def create_media(
    content_id: UUID = Path(..., description="Content UUID"),
    payload: ContentMediaCreate = ...,  # shows proper schema + examples in docs
    media_svc = Depends(get_service),
):
    media = await media_svc.create(content_id, ContentMediaCreate.model_validate(payload))
    return ContentMediaOut.model_validate(media)

@router.patch(
    "",
    summary="Update media for a content item (staff only)",
    description=(
        "Partially updates the media record for the specified content.\n\n**Auth:** Editors/Admins only.\n\n"
        "Only fields provided in the request body are updated."
    ),
    response_model=ContentMediaOut,
    dependencies=[Depends(require_staff)],
    responses={
        200: {"description": "Media updated."},
        401: {"description": "Not authenticated."},
        403: {"description": "Authenticated but not authorized (staff required)."},
        404: {"description": "Media not found for this content."},
    },
)
async def update_media(
    content_id: UUID = Path(..., description="Content UUID"),
    payload: ContentMediaUpdate = ...,  # schema + examples appear in docs
    media_svc = Depends(get_service),
):
    media = await media_svc.update(content_id, ContentMediaUpdate.model_validate(payload))
    if not media:
        raise HTTPException(status_code=404, detail="not found")
    return ContentMediaOut.model_validate(media)

@router.delete(
    "",
    summary="Delete media for a content item (staff only)",
    description="Deletes the media associated with the given content. Returns `{ \"ok\": true }` on success.",
    dependencies=[Depends(require_staff)],
    responses={
        200: {"description": "Deleted.", "content": {"application/json": {"example": {"ok": True}}}},
        401: {"description": "Not authenticated."},
        403: {"description": "Authenticated but not authorized (staff required)."},
        404: {"description": "Media not found for this content."},
    },
)
async def delete_media(
    content_id: UUID = Path(..., description="Content UUID"),
    media_svc = Depends(get_service),
):
    ok = await media_svc.delete(content_id)
    if not ok:
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True}
