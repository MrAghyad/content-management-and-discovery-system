from pydantic import BaseModel, Field, constr
from typing import Literal, List
from datetime import date

ContentStatus = Literal["draft", "ready", "published"]

class ContentBase(BaseModel):
    title: constr(min_length=1, max_length=255)
    description: str | None = None
    language: constr(max_length=32) | None = None
    duration: int | None = Field(default=None, ge=0)
    publication_date: date | None = None
    status: ContentStatus = "draft"
    categories: List[str] = []

class ContentCreate(ContentBase):
    pass

class ContentUpdate(ContentBase):
    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Episode 1: Origins (Remastered)",
                "description": "An updated deep dive into the origins of the project.",
                "categories": ["documentary", "projects"],
                "language": "en",
                "duration": 1820,
                "publication_date": "2025-08-10"
            }
        }
    }
