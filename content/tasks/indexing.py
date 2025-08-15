from app.core.celery_app import celery_app
from content.adapters.outbound.indexer_opensearch import OpenSearchIndexer
from content.domain.repositories.content_repository import ContentRepository
from content.domain.repositories.media_repository import ContentMediaRepository
from content.index.transformers import to_search_doc
from app.core.database.db import async_sessionmaker

@celery_app.task(name="index_content")
def index_content(content_id: int):
    """
    Fetch content + media from DB and upsert into OpenSearch.
    Runs in a worker, outside HTTP request context.
    """
    import asyncio

    async def _index():
        indexer = OpenSearchIndexer()
        async with async_sessionmaker() as db:
            content = await ContentRepository(db).get(content_id)
            media = await ContentMediaRepository(db).get_by_parent_id(content_id)
            if content:
                indexer.upsert(to_search_doc(content, media))

    asyncio.run(_index())

@celery_app.task(name="delete_content_index")
def delete_content_index(content_id: int):
    """
    Remove a content document from OpenSearch.
    """
    OpenSearchIndexer().delete(content_id)
