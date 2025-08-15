from typing import Protocol, Optional, Tuple, List, Dict, Any

class SearchPort(Protocol):
    """
    Outbound port for search/browse.
    Returns: (total_count, list_of_content_ids_as_str)
    """
    def search(
        self,
        q: Optional[str],
        filters: Dict[str, Any],
        limit: int,
        offset: int,
    ) -> Tuple[int, List[str]]: ...
