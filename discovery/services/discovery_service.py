from typing import Optional, List
from uuid import UUID
from datetime import date

from shared.entities.content import ContentOut
from discovery.ports.search_port import SearchPort
from content.ports.read_port import CMSReadPort  # CMS-owned query port


class DiscoveryService:
    """
    Read-model service that:
      - queries OpenSearch via SearchPort
      - hydrates results via CMSReadPort
    """

    def __init__(self, search: SearchPort, cms_read: CMSReadPort):
        self.search = search
        self.cms_read = cms_read

    async def browse(
        self,
        q: Optional[str],
        media_type: Optional[str],
        category: Optional[str],
        language: Optional[str],
        date_from: Optional[date],
        date_to: Optional[date],
        limit: int,
        offset: int,
    ) -> List[ContentOut]:
        _, docs = self.search.search(
            q,
            {
                "media_type": media_type,
                "category": category,
                "language": language,
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
            },
            limit,
            offset,
        )
        out: List[ContentOut] = []
        # Hydrate from CMS (cached inside CMS adapter)
        for doc in docs:
            detail = ContentOut.model_validate(doc)
            if self.cms_read.get_content(detail.id):
                out.append(detail)
        return out

    async def content_detail(self, content_id: UUID) -> Optional[ContentOut]:
        return await self.cms_read.get_content(content_id)
