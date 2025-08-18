from pydantic import BaseModel, HttpUrl
from typing import Literal, Optional
from datetime import date

MediaType = Literal["audio", "video"]
MediaSource = Literal["upload", "external"]
MediaProvider = Literal["team", "youtube"]

class ContentMediaBase(BaseModel):
    media_type: Optional[MediaType] = "audio"
    source: Optional[MediaSource] = "upload"
    media_file: str | None = None
    external_url: HttpUrl | None = None
    media_provider: Optional[MediaProvider] = "team"

class ContentMediaCreate(ContentMediaBase):
    pass

class ContentMediaUpdate(ContentMediaBase):
    pass


class ExternalMediaItem(BaseModel):
    provider: str               # e.g., "youtube"
    provider_id: str            # e.g., YouTube videoId
    url: HttpUrl                # canonical URL
    title: str
    description: Optional[str] = None
    media_type: MediaType       # "video" or "audio"
    duration_seconds: Optional[int] = None
    language: Optional[str] = None
    category: Optional[str] = None
    publication_date: Optional[date] = None
    thumbnail_url: Optional[HttpUrl] = None
