import pytest
from datetime import date
from uuid import UUID
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.auth import require_staff, optional_current_user

from content.domain.models.content import Content, ContentStatus
from content.domain.models.category import Category, content_categories


# ---------------------------
# Helpers
# ---------------------------


def _ck_content(cid: UUID) -> str: return f"disc:content:{cid}"
def _ck_media(cid: UUID) -> str:   return f"disc:media:{cid}"

# ---------------------------
# Auth overrides (focus tests on behavior)
# ---------------------------

@pytest.fixture(autouse=True)
def override_auth():
    # Given: we bypass auth for tests to isolate router/service behavior
    app.dependency_overrides[require_staff] = lambda: None
    app.dependency_overrides[optional_current_user] = lambda: None
    yield
    app.dependency_overrides.pop(require_staff, None)
    app.dependency_overrides.pop(optional_current_user, None)


# ==============================================================================
# Create
# ==============================================================================

@pytest.mark.asyncio
async def test_should_persist_in_db_when_content_is_created(client: AsyncClient, db_session: AsyncSession):
    # GIVEN
    payload = {
        "title": "Episode 1: Origins",           # -> request body fields to create a content row
        "description": "How it all started.",    # -> full details we will assert back
        "categories": ["documentary", "history"],
        "language": "ar",
        "duration": 1800,
        "publication_date": "2025-08-01",
        "status": "published",
    }

    # WHEN
    r = await client.post("/v1/contents", json=payload)   # -> call POST /v1/contents
    assert r.status_code == 201                           # -> API should create and return 201
    body = r.json()
    cid = UUID(body["id"])                                # -> capture created id to verify DB state

    # THEN
    # Response assertions (full field-by-field)
    assert body["title"] == payload["title"]              # -> title persisted
    assert body["description"] == payload["description"]  # -> description persisted
    assert set(body["categories"]) == set(payload["categories"])  # -> categories reflected in DTO
    assert body["language"] == payload["language"]        # -> language persisted
    assert body["duration"] == payload["duration"]        # -> duration persisted
    assert body["publication_date"] == payload["publication_date"]  # -> date persisted as ISO string
    assert body["status"] == payload["status"]            # -> status persisted

    # Database assertions (source of truth)
    q = await db_session.execute(select(Content).where(Content.id == cid))  # -> read freshly created row
    c = q.scalars().first()
    assert c is not None                                   # -> row exists
    assert c.title == payload["title"]                     # -> DB value matches request
    assert c.description == payload["description"]
    assert c.language == payload["language"]
    assert c.duration == payload["duration"]
    assert str(c.publication_date) == payload["publication_date"]
    assert c.status == ContentStatus.published


@pytest.mark.asyncio
async def test_should_write_item_cache_when_content_is_created(client: AsyncClient, fake_cache):
    # GIVEN
    payload = {"title": "Cache Me", "status": "published", "categories": []}  # -> minimal valid payload

    # WHEN
    r = await client.post("/v1/contents", json=payload)  # -> create content
    assert r.status_code == 201
    cid = UUID(r.json()["id"])                           # -> id for cache key

    # THEN
    cached = await fake_cache.get(_ck_content(cid))      # -> item-level cache is set
    assert cached is not None
    assert cached["id"] == str(cid)                      # -> DTO id matches created id
    assert cached["title"] == "Cache Me"                 # -> full value match in cache
    assert cached["status"] == "published"
    assert cached.get("categories", []) == []


@pytest.mark.asyncio
async def test_should_enqueue_index_task_when_content_is_created(client: AsyncClient, celery_delay_spy):
    # GIVEN
    payload = {"title": "Indexed One", "status": "published", "categories": []}  # -> a new content to index

    # WHEN
    r = await client.post("/v1/contents", json=payload)  # -> triggers async index task
    assert r.status_code == 201
    cid = UUID(r.json()["id"])

    # THEN
    assert any(str(cid) in call for call in celery_delay_spy.calls)  # -> task enqueued with correct id


# ==============================================================================
# Get (by id)
# ==============================================================================

@pytest.mark.asyncio
async def test_should_return_full_payload_when_getting_existing_content(client: AsyncClient, db_session: AsyncSession):
    # GIVEN
    c = Content(                                            # -> seed one content row in DB
        title="From DB",
        description="dbdesc",
        language="en",
        duration=99,
        publication_date=date(2025, 8, 1),
        status=ContentStatus.published,
    )
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    # WHEN
    r = await client.get(f"/v1/contents/{c.id}")            # -> fetch by id

    # THEN
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == str(c.id)                          # -> response reflects DB
    assert body["title"] == c.title
    assert body["description"] == c.description
    assert body["language"] == c.language
    assert body["duration"] == c.duration
    assert body["publication_date"] == str(c.publication_date)
    assert body["status"] == "published"


@pytest.mark.asyncio
async def test_should_serve_from_cache_when_db_row_deleted(client: AsyncClient, db_session: AsyncSession, fake_cache):
    # GIVEN
    c = Content(title="Warm Me", status=ContentStatus.published)  # -> create a content to warm cache
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    r1 = await client.get(f"/v1/contents/{c.id}")                 # -> warms item cache
    assert r1.status_code == 200
    await db_session.delete(c)                                    # -> simulate DB row removed
    await db_session.commit()

    # WHEN
    r2 = await client.get(f"/v1/contents/{c.id}")                 # -> should hit cache

    # THEN
    assert r2.status_code == 200
    body = r2.json()
    assert body["id"] == str(c.id)                                # -> value served from cache
    assert body["title"] == "Warm Me"


# ==============================================================================
# List
# ==============================================================================

@pytest.mark.asyncio
async def test_should_list_multiple_contents_from_db(client: AsyncClient, db_session: AsyncSession):
    # GIVEN
    db_session.add_all([                                         # -> two published rows
        Content(title="A", status=ContentStatus.published),
        Content(title="B", status=ContentStatus.published),
    ])
    await db_session.commit()

    # WHEN
    r = await client.get("/v1/contents?status=published")        # -> list published

    # THEN
    assert r.status_code == 200
    arr = r.json()
    titles = [row["title"] for row in arr]                       # -> full list contains both
    assert "A" in titles and "B" in titles


@pytest.mark.asyncio
async def test_should_ignore_cache_when_listing(client: AsyncClient, db_session: AsyncSession, fake_cache):
    # GIVEN
    c = Content(title="List Me", status=ContentStatus.published)  # -> create a row
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    await client.get(f"/v1/contents/{c.id}")                      # -> warm single-item cache (list ignores it)

    # WHEN
    r = await client.get("/v1/contents?status=published")         # -> list endpoint

    # THEN
    assert r.status_code == 200
    arr = r.json()
    assert any(row["title"] == "List Me" for row in arr)          # -> present via DB scan, not cache


# ==============================================================================
# Delete
# ==============================================================================

@pytest.mark.asyncio
async def test_should_remove_from_db_when_content_is_deleted(client: AsyncClient, db_session: AsyncSession):
    # GIVEN
    c = Content(title="To Delete", status=ContentStatus.published)  # -> a row to delete
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    # WHEN
    r = await client.delete(f"/v1/contents/{c.id}")                 # -> delete endpoint

    # THEN
    assert r.status_code == 200
    q = await db_session.execute(select(Content).where(Content.id == c.id))  # -> DB no longer has it
    assert q.scalars().first() is None


@pytest.mark.asyncio
async def test_should_evict_cache_when_content_is_deleted(client: AsyncClient, db_session: AsyncSession, fake_cache):
    # GIVEN
    c = Content(title="Evict Cache", status=ContentStatus.published)  # -> create + warm cache
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    await client.get(f"/v1/contents/{c.id}")                           # -> warm cache to create key

    # WHEN
    r = await client.delete(f"/v1/contents/{c.id}")                    # -> delete

    # THEN
    assert r.status_code == 200
    assert await fake_cache.get(_ck_content(c.id)) is None             # -> item cache key removed


# ==============================================================================
# Categories on create
# ==============================================================================

@pytest.mark.asyncio
async def test_should_persist_categories_when_content_created(client: AsyncClient, db_session: AsyncSession):
    # GIVEN
    payload = {"title": "With Cats", "status": "published", "categories": ["one", "two"]}  # -> two categories

    # WHEN
    r = await client.post("/v1/contents", json=payload)                # -> create content with cats
    assert r.status_code == 201
    cid = UUID(r.json()["id"])

    # THEN
    q = await db_session.execute(                                      # -> verify join table links
        select(Category.name)
        .select_from(content_categories.join(Category, content_categories.c.category_id == Category.id))
        .where(content_categories.c.content_id == cid)
    )
    names = [name for (name,) in q.all()]
    assert set(names) == {"one", "two"}                                # -> both links exist


@pytest.mark.asyncio
async def test_should_cache_categories_when_content_created(client: AsyncClient, fake_cache):
    # GIVEN
    payload = {"title": "Cache Categories", "status": "published", "categories": ["a", "b"]}

    # WHEN
    r = await client.post("/v1/contents", json=payload)                # -> creates and populates item cache
    assert r.status_code == 201
    cid = UUID(r.json()["id"])
    cached = await fake_cache.get(_ck_content(cid))

    # THEN
    assert cached is not None
    assert cached["title"] == "Cache Categories"                       # -> cache has full DTO
    assert set(cached.get("categories", [])) == {"a", "b"}


# ==============================================================================
# Categories on update
# ==============================================================================

@pytest.mark.asyncio
async def test_should_update_category_links_in_db(client: AsyncClient, db_session: AsyncSession):
    # GIVEN
    c = Content(title="Update Cats", status=ContentStatus.published)   # -> start with no category links
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    # WHEN
    _ = await client.patch(f"/v1/contents/{c.id}", json={"categories": ["x", "y"]})  # -> replace links

    # THEN
    q = await db_session.execute(                                      # -> verify join table replacement
        select(Category.name)
        .select_from(content_categories.join(Category, content_categories.c.category_id == Category.id))
        .where(content_categories.c.content_id == c.id)
    )
    names = [name for (name,) in q.all()]
    assert set(names) == {"x", "y"}                                    # -> exactly x,y present


@pytest.mark.asyncio
async def test_should_update_cached_categories_on_update(client: AsyncClient, db_session: AsyncSession, fake_cache):
    # GIVEN
    c = Content(title="Cache Cat Upd", status=ContentStatus.published) # -> create + warm cache
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    await client.get(f"/v1/contents/{c.id}")                           # -> warm item cache

    # WHEN
    _ = await client.patch(f"/v1/contents/{c.id}", json={"categories": ["x", "y"]})  # -> patch categories
    cached = await fake_cache.get(_ck_content(c.id))                    # -> cache should be refreshed

    # THEN
    assert cached is not None
    assert set(cached.get("categories", [])) == {"x", "y"}              # -> cache reflects updated cats
