from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.db import get_session
from app.core.config import settings

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


async def get_cms_read_port(
    db: AsyncSession = Depends(get_session),
) -> CMSReadPort:
    """
    Build the in-process adapter with injected services that share ONE DB session.
    Optionally wrap with cache.
    """
    content_svc = ContentService(db)
    media_svc = ContentMediaService(db)
    base = CMSInProcessAdapter(content_service=content_svc, media_service=media_svc)

    # Wrap with cache decorator (optional, recommended)
    return CMSReadCache(base)


def get_discovery_service(
    search: SearchPort = Depends(get_search_service),
    cms_read: CMSReadPort = Depends(get_cms_read_port),
) -> DiscoveryService:
    return DiscoveryService(search=search, cms_read=cms_read)
