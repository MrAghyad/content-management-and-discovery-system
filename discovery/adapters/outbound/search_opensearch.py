from typing import Optional, Dict, Tuple, List, Any

from opensearchpy import OpenSearch
from discovery.ports.search_port import SearchPort
from app.core.config import settings


def _client() -> OpenSearch:
    return OpenSearch(
        hosts=[settings.os_host],
        http_auth=(settings.os_username, settings.os_password) if settings.os_username else None,
        use_ssl=str(settings.os_host).startswith("https"),
        verify_certs=False,  # set True with proper certs in prod
    )


class OpenSearchSearchAdapter(SearchPort):
    """
    OpenSearch implementation of SearchPort.
    Produces a ranked list of content IDs (as strings).
    """

    def __init__(self, client: OpenSearch | None = None, index: Optional[str] = None):
        self.client = client or _client()
        self.index = index or settings.os_index

    def search(
        self,
        q: Optional[str],
        filters: Dict[str, Any],
        limit: int,
        offset: int,
    ) -> Tuple[int, List[str]]:
        must: List[Dict[str, Any]] = []
        if q:
            must.append({
                "multi_match": {
                    "query": q,
                    "fields": ["title^3", "description", "category", "language"],
                    "type": "best_fields"
                }
            })

        # Facets
        if (mt := filters.get("media_type")):
            must.append({"term": {"media_type": mt}})
        if (cat := filters.get("category")):
            must.append({"term": {"categories": cat}})
        if (lang := filters.get("language")):
            must.append({"term": {"language": lang}})
        if (df := filters.get("date_from")):
            must.append({"range": {"publication_date": {"gte": df}}})
        if (dt := filters.get("date_to")):
            must.append({"range": {"publication_date": {"lte": dt}}})

        query = {"match_all": {}} if not must else {"bool": {"must": must, "filter": []}}
        # Show only published content by default
        if query.get("bool") is not None:
            query["bool"]["filter"].append({"term": {"status": "published"}})
        else:
            query = {"bool": {"must": [{"match_all": {}}], "filter": [{"term": {"status": "published"}}]}}

        body = {
            "query": query,
            "_source": ["id"],
            "size": limit,
            "from": offset,
            "sort": [
                {"publication_date": {"order": "desc"}},
                {"created_at": {"order": "desc"}},
            ],
        }

        res = self.client.search(index=self.index, body=body)
        # OS may return total as dict or int depending on version
        total_raw = res["hits"]["total"]
        total = total_raw["value"] if isinstance(total_raw, dict) else int(total_raw)
        ids = [hit["_source"]["id"] for hit in res["hits"]["hits"]]
        return total, ids
