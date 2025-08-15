import os
import re
import requests
from typing import Optional
from datetime import timedelta, datetime
from content.domain.entities import ExternalMediaItem
from content.ports.outbound.external_media_provider_port import ExternalMediaProviderPort
from app.core.config import settings

_YT_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)(?P<id>[A-Za-z0-9_-]{11})"
)

def _iso8601_duration_to_seconds(iso: str) -> int:
    # Basic ISO8601 PT#H#M#S parser
    hours = minutes = seconds = 0
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if m:
        hours = int(m.group(1) or 0)
        minutes = int(m.group(2) or 0)
        seconds = int(m.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds

class YouTubeProvider(ExternalMediaProviderPort):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.youtube_api_key

    def can_handle(self, url: str) -> bool:
        return bool(_YT_RE.search(url))

    def fetch_by_url(self, url: str) -> Optional[ExternalMediaItem]:
        m = _YT_RE.search(url)
        if not m:
            return None
        vid = m.group("id")
        params = {
            "part": "snippet,contentDetails",
            "id": vid,
            "key": self.api_key,
        }
        r = requests.get("https://www.googleapis.com/youtube/v3/videos", params=params, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        if not data.get("items"):
            return None
        item = data["items"][0]
        snippet = item.get("snippet", {})
        content = item.get("contentDetails", {})
        duration = _iso8601_duration_to_seconds(content.get("duration"))
        published_at = snippet.get("publishedAt")
        pub_date = None
        if published_at:
            try:
                pub_date = datetime.fromisoformat(published_at.replace("Z", "+00:00")).date()
            except Exception:
                pub_date = None

        title = snippet.get("title") or ""
        description = snippet.get("description")
        lang = snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage")
        category = None  # could map categoryId via another API call if needed
        thumb = (snippet.get("thumbnails") or {}).get("high") or (snippet.get("thumbnails") or {}).get("default")
        thumb_url = thumb.get("url") if thumb else None

        canonical_url = f"https://www.youtube.com/watch?v={vid}"
        return ExternalMediaItem(
            provider="youtube",
            provider_id=vid,
            url=canonical_url,
            title=title,
            description=description,
            media_type="video",
            duration_seconds=duration,
            language=lang,
            category=category,
            publication_date=pub_date,
            thumbnail_url=thumb_url,
        )
