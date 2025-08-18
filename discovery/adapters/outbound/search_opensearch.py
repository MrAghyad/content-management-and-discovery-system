# discovery/adapters/outbound/search_opensearch.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from datetime import date, datetime

from opensearchpy import OpenSearch, TransportError
from app.core.config import settings
from discovery.ports.search_port import SearchPort


def _client() -> OpenSearch:
    """Create an OpenSearch client aligned with your indexer settings."""
    return OpenSearch(
        hosts=[settings.os_host],                     # e.g. "http://opensearch:9200"
        http_auth=(settings.os_username, settings.os_password) if settings.os_username else None,
        use_ssl=str(settings.os_host).startswith("https"),
        verify_certs=False,                           # dev-only; enable in prod
    )


def _iso(d: date | datetime | str | None) -> Optional[str]:
    if d is None:
        return None
    if isinstance(d, (date, datetime)):
        return d.isoformat()
    return str(d)


class OpenSearchSearchAdapter(SearchPort):
    """
    OpenSearch implementation of SearchPort.

    Mapping assumptions (from your indexer):
      - title, description  -> type: text
      - categories, language, media_type, status -> type: keyword
      - publication_date, created_at -> type: date
      - id -> keyword (stored in _source)
    """

    def __init__(self, client: Optional[OpenSearch] = None, index: Optional[str] = None):
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
        filt: List[Dict[str, Any]] = []

        # ---- Full-text over analyzed fields ----
        if q:
            must.append({
                "multi_match": {
                    "query": q,
                    "fields": [
                        "title^3",
                        "description^2",
                    ],
                    "type": "best_fields",
                    "operator": "and",
                    "fuzziness": "AUTO"
                }
            })

        # ---- Facets on keyword fields (exact match) ----
        mt = filters.get("media_type")
        if mt:
            filt.append({"term": {"media_type": mt}})

        cat = filters.get("category")
        if cat:
            # categories is keyword[] in your mapping
            filt.append({"term": {"categories": cat}})

        lang = filters.get("language")
        if lang:
            filt.append({"term": {"language": lang}})

        # Dates use range on date fields
        df = _iso(filters.get("date_from"))
        if df:
            filt.append({"range": {"publication_date": {"gte": df}}})
        dt = _iso(filters.get("date_to"))
        if dt:
            filt.append({"range": {"publication_date": {"lte": dt}}})

        # Only published by default (matches your ContentStatus + indexer mapping)
        status = filters.get("status")
        if status:
            filt.append({"term": {"status": status}})

        # Build bool query
        if must or filt:
            query: Dict[str, Any] = {"bool": {}}
            if must:
                query["bool"]["must"] = must
            if filt:
                query["bool"]["filter"] = filt
        else:
            query = {"match_all": {}}

        body: Dict[str, Any] = {
            "query": query,
            "sort": [
                {"publication_date": {"order": "desc"}},
                {"created_at": {"order": "desc"}},
            ],
            "track_total_hits": True,
        }

        try:
            # ignore 404 so a missing index returns empty results instead of raising
            res = self.client.search(index=self.index, body=body, ignore=[404])
        except TransportError as e:
            # Be defensive: on connection/mapping errors return empty result
            # (You might want to log this)
            return 0, []

        if not res or "hits" not in res:
            return 0, []

        total_raw = res["hits"]["total"]
        total = total_raw["value"] if isinstance(total_raw, dict) else int(total_raw or 0)
        docs = [hit["_source"] for hit in res["hits"]["hits"] if "_source" in hit ]
        return total, docs
