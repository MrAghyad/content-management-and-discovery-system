from __future__ import annotations

import asyncio
from uuid import UUID

from celery import shared_task
from app.core.database.db import _get_session_factory
from content.domain.repositories.content_repository import ContentRepository
from content.domain.repositories.media_repository import ContentMediaRepository
from content.index.transformers import to_search_doc
from content.adapters.outbound.indexer_opensearch import OpenSearchIndexer



@shared_task(name="content.index_content")
def index_content(content_id: str) -> None:
    async def _run() -> None:
        cid = UUID(content_id)

        # create session bound to THIS loop
        Session = _get_session_factory()
        async with Session() as db:
            content = await ContentRepository(db).get(cid)
            media = await ContentMediaRepository(db).get_by_parent_id(cid)
            if content:
                # OpenSearchIndexer is sync in our code; call directly.
                # If you later switch to an async client, make upsert async and `await` it here.
                OpenSearchIndexer().upsert(to_search_doc(content, media))

    asyncio.run(_run())

@shared_task(name="content.delete_content_index")
def delete_content_index(content_id: str) -> None:
    async def _run() -> None:
        cid = UUID(content_id)
        # No DB needed, but keep pattern consistent if you add validation later
        OpenSearchIndexer().delete(str(cid))

    asyncio.run(_run())
