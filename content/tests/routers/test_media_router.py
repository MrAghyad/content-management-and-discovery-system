import pytest
from uuid import UUID
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.auth import require_staff, optional_current_user

from content.domain.models.content import Content, ContentStatus
from content.domain.models.media import ContentMedia, MediaType, MediaSource, MediaProvider


# ---------------------------
# Helpers
# ---------------------------


def _ck_content(cid: UUID) -> str: return f"disc:content:{cid}"
def _ck_media(cid: UUID) -> str:   return f"disc:media:{cid}"

# ---------------------------
# Auth overrides
# ---------------------------

@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[require_staff] = lambda: None
    app.dependency_overrides[optional_current_user] = lambda: None
    yield
    app.dependency_overrides.pop(require_staff, None)
    app.dependency_overrides.pop(optional_current_user, None)


# ==============================================================================
# Create
# ==============================================================================

@pytest.mark.asyncio
async def test_should_persist_media_in_db_on_create(client: AsyncClient, db_session: AsyncSession):
    # GIVEN
    c = Content(title="Parent", status=ContentStatus.published)
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    payload = {
        "media_type": "video",
        "source": "external",
        "media_provider": "youtube",
        "external_url": "https://youtube.com/watch?v=xyz",
    }

    # WHEN
    r = await client.post(f"/v1/contents/{c.id}/media", json=payload)
    assert r.status_code == 201
    body = r.json()

    # THEN
    # Response assertions
    assert body["media_type"] == payload["media_type"]
    assert body["source"] == payload["source"]
    assert body["media_provider"] == payload["media_provider"]
    assert body["external_url"] == payload["external_url"]

    # Database assertions
    q = await db_session.execute(select(ContentMedia).where(ContentMedia.content_id == c.id))
    m = q.scalars().first()
    assert m is not None
    assert m.media_type == MediaType.video
    assert m.source == MediaSource.external
    assert m.media_provider == MediaProvider.youtube
    assert m.external_url == "https://youtube.com/watch?v=xyz"


@pytest.mark.asyncio
async def test_should_cache_media_when_created(client: AsyncClient, db_session: AsyncSession, fake_cache):
    # GIVEN
    c = Content(title="Cache Media", status=ContentStatus.published)
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    payload = {
        "media_type": "audio",
        "source": "external",
        "media_provider": "youtube",
        "external_url": "https://youtube.com/track/123",
    }

    # WHEN
    r = await client.post(f"/v1/contents/{c.id}/media", json=payload)
    assert r.status_code == 201
    cached = await fake_cache.get(_ck_media(c.id))

    # THEN
    assert cached is not None
    assert cached["media_type"] == "audio"
    assert cached["media_provider"] == "youtube"
    assert cached["external_url"] == "https://youtube.com/track/123"


# ==============================================================================
# Get
# ==============================================================================

@pytest.mark.asyncio
async def test_should_return_full_payload_when_getting_media(client: AsyncClient, db_session: AsyncSession):
    # GIVEN
    c = Content(title="With Media", status=ContentStatus.published)
    m = ContentMedia(
        content=c,
        media_type=MediaType.video,
        source=MediaSource.external,
        media_provider=MediaProvider.youtube,
        external_url="https://youtube.com/watch?v=abc",
    )
    db_session.add_all([c, m])
    await db_session.commit()
    await db_session.refresh(c)

    # WHEN
    r = await client.get(f"/v1/contents/{c.id}/media")

    # THEN
    assert r.status_code == 200
    body = r.json()
    assert body["media_type"] == "video"
    assert body["source"] == "external"
    assert body["media_provider"] == "youtube"
    assert body["external_url"] == "https://youtube.com/watch?v=abc"


@pytest.mark.asyncio
async def test_should_return_404_when_getting_missing_media(client: AsyncClient, db_session: AsyncSession):
    # GIVEN
    c = Content(title="No Media", status=ContentStatus.published)
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    # WHEN
    r = await client.get(f"/v1/contents/{c.id}/media")

    # THEN
    assert r.status_code == 404
    assert r.json()["detail"] == "not found"


# ==============================================================================
# Update
# ==============================================================================

@pytest.mark.asyncio
async def test_should_update_media_in_db_and_cache(client: AsyncClient, db_session: AsyncSession, fake_cache):
    # GIVEN
    c = Content(title="Upd", status=ContentStatus.published)
    m = ContentMedia(
        content=c,
        media_type=MediaType.audio,
        source=MediaSource.external,
        media_provider=MediaProvider.youtube,
        external_url="https://youtube.com/track/old",
    )
    db_session.add_all([c, m])
    await db_session.commit()
    await db_session.refresh(c)

    patch = {"external_url": "https://youtube.com/track/new"}  # -> update only the url

    # WHEN
    r = await client.patch(f"/v1/contents/{c.id}/media", json=patch)
    assert r.status_code == 200
    body = r.json()

    # THEN
    # Response reflects patch
    assert body["external_url"] == patch["external_url"]
    assert body["media_provider"] == "youtube"  # unchanged
    assert body["media_type"] == "audio"

    # DB reflects patch
    q = await db_session.execute(select(ContentMedia).where(ContentMedia.content_id == c.id))
    m2 = q.scalars().first()
    assert m2.external_url == "https://youtube.com/track/new"

    # Cache refreshed
    cached = await fake_cache.get(_ck_media(c.id))
    assert cached is not None
    assert cached["external_url"] == "https://youtube.com/track/new"


@pytest.mark.asyncio
async def test_should_return_404_when_updating_nonexistent_media(client: AsyncClient, db_session: AsyncSession):
    # GIVEN
    c = Content(title="No Media Upd", status=ContentStatus.published)
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    # WHEN
    r = await client.patch(f"/v1/contents/{c.id}/media", json={"external_url": "http://x"})

    # THEN
    assert r.status_code == 404
    assert r.json()["detail"] == "not found"


# ==============================================================================
# Delete
# ==============================================================================

@pytest.mark.asyncio
async def test_should_delete_media_from_db_and_cache(client: AsyncClient, db_session: AsyncSession, fake_cache):
    # GIVEN
    c = Content(title="Del", status=ContentStatus.published)
    m = ContentMedia(
        content=c,
        media_type=MediaType.video,
        source=MediaSource.external,
        media_provider=MediaProvider.youtube,
        external_url="https://youtube.com/watch?v=to_delete",
    )
    db_session.add_all([c, m])
    await db_session.commit()
    await db_session.refresh(c)

    # Warm cache
    await client.get(f"/v1/contents/{c.id}/media")

    # WHEN
    r = await client.delete(f"/v1/contents/{c.id}/media")

    # THEN
    assert r.status_code == 200
    assert r.json() == {"ok": True}

    q = await db_session.execute(select(ContentMedia).where(ContentMedia.content_id == c.id))
    assert q.scalars().first() is None  # DB row removed
    assert await fake_cache.get(_ck_media(c.id)) is None  # cache evicted


@pytest.mark.asyncio
async def test_should_return_404_when_deleting_nonexistent_media(client: AsyncClient, db_session: AsyncSession):
    # GIVEN
    c = Content(title="No Media Del", status=ContentStatus.published)
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    # WHEN
    r = await client.delete(f"/v1/contents/{c.id}/media")

    # THEN
    assert r.status_code == 404
    assert r.json()["detail"] == "not found"
