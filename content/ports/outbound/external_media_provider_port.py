from typing import Protocol, Optional
from content.domain.entities import ExternalMediaItem

class ExternalMediaProviderPort(Protocol):
    """Generic read-only provider interface (URL-driven)."""

    def can_handle(self, url: str) -> bool: ...
    def fetch_by_url(self, url: str) -> Optional[ExternalMediaItem]: ...
