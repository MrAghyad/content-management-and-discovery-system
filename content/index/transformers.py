from content.domain.models.content import Content
from content.domain.models.media import ContentMedia

def to_search_doc(content: Content, media: ContentMedia | None) -> dict:
    return {
        "id": str(content.id),
        "title": content.title,
        "description": content.description,
        "categories": [c.name for c in (content.categories or [])],
        "language": content.language,
        "media_type": (media.media_type.value if media else None),
        "status": content.status.value,
        "publication_date": content.publication_date.isoformat() if content.publication_date else None,
        "created_at": content.created_at.isoformat(),
        "updated_at": content.updated_at.isoformat(),
    }
