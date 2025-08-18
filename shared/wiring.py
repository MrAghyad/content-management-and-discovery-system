from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.db import get_session
from app.core.config import settings
from content.adapters.outbound.cache_redis import RedisCacheAdapter
from content.domain.repositories import ContentRepository, ContentMediaRepository
from content.domain.repositories.category_repository import CategoryRepository
from content.ports.outbound.cache_port import CachePort

# Discovery search port + adapter
from discovery.ports.search_port import SearchPort
from discovery.adapters.outbound.search_opensearch import OpenSearchSearchAdapter

# CMS read port + adapters
from content.ports.read_port import CMSReadPort
from content.adapters.read_inprocess import CMSInProcessAdapter
from content.adapters.read_cache import CMSReadCache

# CMS services
from content.services.content_service import ContentService
from content.services.media_service import ContentMediaService

# Discovery service
from discovery.services.discovery_service import DiscoveryService


def get_search_service() -> SearchPort:
    return OpenSearchSearchAdapter()

def get_cache() -> CachePort:
    return RedisCacheAdapter()

async def get_cms_read_port(
    db: AsyncSession = Depends(get_session),
    cache: CachePort = Depends(get_cache),
) -> CMSReadPort:
    """
    Build the in-process adapter with injected services that share ONE DB session.
    Optionally wrap with cache.
    """
    content_svc = ContentService(ContentRepository(db), CategoryRepository(db), ContentMediaRepository(db), cache_port=cache)
    media_svc = ContentMediaService(ContentMediaRepository(db), cache_port=cache)
    base = CMSInProcessAdapter(content_service=content_svc, media_service=media_svc)

    # Wrap with cache decorator (optional, recommended)
    return CMSReadCache(base)


def get_discovery_service(
    search: SearchPort = Depends(get_search_service),
    cms_read: CMSReadPort = Depends(get_cms_read_port),
) -> DiscoveryService:
    return DiscoveryService(search=search, cms_read=cms_read)
