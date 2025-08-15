from typing import Optional
from uuid import UUID
from opensearchpy import OpenSearch, NotFoundError
from app.core.config import settings
from content.ports.outbound.indexer_port import IndexerPort

MAPPING = {
    "settings": {"index": {"number_of_shards": 1, "number_of_replicas": 0, "refresh_interval": "1s"}},
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "title": {"type": "text"},
            "description": {"type": "text"},
            "categories": {"type": "keyword"},
            "language": {"type": "keyword"},
            "media_type": {"type": "keyword"},
            "status": {"type": "keyword"},
            "publication_date": {"type": "date"},
            "created_at": {"type": "date"},
        }
    },
}

def _client() -> OpenSearch:
    return OpenSearch(
        hosts=[settings.os_host],
        http_auth=(settings.os_username, settings.os_password),
        use_ssl=settings.os_host.startswith("https"),
        verify_certs=False,
    )

class OpenSearchIndexer(IndexerPort):
    def __init__(self, client: Optional[OpenSearch] = None, index: Optional[str] = None):
        self.client = client or _client()
        self.index = index or settings.os_index

    def ensure_index(self) -> None:
        if not self.client.indices.exists(self.index):
            self.client.indices.create(index=self.index, body=MAPPING)

    def upsert(self, doc: dict) -> None:
        self.client.index(index=self.index, id=doc["id"], body=doc, refresh=False)

    def delete(self, content_id: UUID) -> None:
        try:
            self.client.delete(index=self.index, id=str(content_id), refresh=False)
        except NotFoundError:
            pass
