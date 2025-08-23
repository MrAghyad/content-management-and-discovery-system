from pydantic import BaseModel, HttpUrl
from typing import Literal, Optional
from datetime import date

MediaType = Literal["audio", "video"]
MediaSource = Literal["upload", "external"]
MediaProvider = Literal["team", "youtube"]

class ContentMediaBase(BaseModel):
    media_type: Optional[MediaType] | None = "audio"
    source: Optional[MediaSource] | None = "upload"
    media_file: str | None = None
    external_url: HttpUrl | None = None
    media_provider: Optional[MediaProvider] | None = "team"

class ContentMediaCreate(ContentMediaBase):
    pass

class ContentMediaUpdate(ContentMediaBase):
    pass


class ExternalMediaItem(BaseModel):
    provider: str  | None     = None         # e.g., "youtube"
    provider_id: str  | None  = None         # e.g., YouTube videoId
    url: HttpUrl  | None  = None             # canonical URL
    title: str   | None  = None
    description: Optional[str] = None
    media_type: MediaType  | None    # "video" or "audio"
    duration_seconds: Optional[int] = None
    language: Optional[str] = None
    category: Optional[str] = None
    publication_date: Optional[date] = None
    thumbnail_url: Optional[HttpUrl] = None
