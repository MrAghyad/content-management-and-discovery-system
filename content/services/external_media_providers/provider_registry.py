from typing import List, Optional
from content.ports.outbound.external_media_provider_port import ExternalMediaProviderPort

class ProviderRegistry:
    def __init__(self, providers: List[ExternalMediaProviderPort]):
        self._providers = providers

    def resolve_by_url(self, url: str) -> Optional[ExternalMediaProviderPort]:
        for p in self._providers:
            if p.can_handle(url):
                return p
        return None
