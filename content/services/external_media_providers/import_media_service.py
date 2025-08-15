from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from content.domain.repositories.content_repository import ContentRepository
from content.domain.repositories.media_repository import ContentMediaRepository
from content.domain.entities.content import ContentCreate
from content.domain.entities.media import ContentMediaCreate, MediaProvider, MediaSource
from content.domain.models.media import MediaType
from content.ports.outbound.cache_port import CachePort
from content.services.external_media_providers.provider_registry import ProviderRegistry
from content.domain.entities import ExternalMediaItem
from shared.entities.content import ContentOut
from app.core.cache import cache
from app.core.config import settings
from content.tasks.indexing import index_content

def _ck_content(cid: UUID) -> str: return f"disc:content:{cid}"
def _ck_media(cid: UUID) -> str:   return f"disc:media:{cid}"
LIST_PREFIX = "disc:content:list:"

class ImportService:
    """
    Import external items into CMS (write-through cache and async indexing).
    """

    def __init__(
        self,
        db: AsyncSession,
        cache_port: CachePort,
        registry: ProviderRegistry,
    ):
        self.db = db
        self.cache_port = cache_port
        self.registry = registry
        self.contents = ContentRepository(db)
        self.medias = ContentMediaRepository(db)

    async def import_by_url(self, url: str) -> Optional[ContentOut]:
        provider = self.registry.resolve_by_url(url)
        if not provider:
            return None
        item: Optional[ExternalMediaItem] = provider.fetch_by_url(url)
        if not item:
            return None

        # Create Content
        payload = ContentCreate(
            title=item.title,
            description=item.description,
            category=item.category,
            language=item.language,
            duration=item.duration_seconds,
            publication_date=item.publication_date,
            status="draft",  # editors can publish later
        )
        content = await self.contents.create(payload)

        # Create Media (external)
        m_payload = ContentMediaCreate(
            media_type=MediaType.video.value if item.media_type == "video" else "audio",
            source=MediaSource.external.value,
            media_provider=MediaProvider.youtube.value,
            media_file=None,
            external_url=str(item.url),
        )
        await self.medias.create(content.id, m_payload)

        dto = ContentOut(
            id=content.id,
            title=content.title,
            description=content.description,
            language=content.language,
            categories=content.categories,
            duration=content.duration,
            publication_date=content.publication_date,
            created_at=content.created_at,
            updated_at=content.updated_at,
            media_type=m_payload.media_type,
        )

        # Write-through cache and invalidate lists
        await cache.set(_ck_content(content.id), dto.model_dump(mode="json"), ttl=settings.cache_ttl_seconds)
        await cache.set(_ck_media(content.id), dto.media.model_dump(mode="json"), ttl=settings.cache_ttl_seconds)
        await self.cache_port.delete_prefix(LIST_PREFIX)

        # Async index (uses existing Celery task)
        index_content.delay(str(content.id))

        return dto
