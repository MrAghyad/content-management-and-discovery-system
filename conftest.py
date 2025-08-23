# conftest.py
import asyncio
import json
import os
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.core.database.db import get_session as real_get_session, get_session
from app.core.database.base import Base  # your declarative base (adjust import path if needed)
from content.ports.outbound.cache_port import CachePort


# ---- Fakes ------------------------------------------------------------------

import json
from typing import Any, Dict, Optional
class _FakeCache(CachePort):
    def __init__(self) -> None:
        self.store: Dict[str, Any] = {}

    async def get(self, key: str) -> Optional[Any]:
        val = self.store.get(key)
        # tolerate accidental JSON-string values
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return val
        return val

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        # store the dict/list directly; do NOT json.dumps here
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)

    async def delete_prefix(self, prefix: str) -> None:
        for k in list(self.store.keys()):
            if k.startswith(prefix):
                self.store.pop(k, None)

    async def delete_keys(self, *keys: str) -> None:
        for k in keys:
            self.store.pop(k, None)

    # handy helpers used by tests
    def keys(self):
        return list(self.store.keys())


class FakeIndexer:
    def __init__(self) -> None:
        self.upserts: list[dict] = []
        self.deletes: list[str] = []

    def ensure_index(self) -> None:
        pass

    def upsert(self, doc: dict) -> None:
        self.upserts.append(doc)

    def delete(self, content_id) -> None:
        self.deletes.append(str(content_id))


import json
import types
import content.services.content_service as cs

class CeleryDelaySpy:
    def __init__(self):
        self.calls: list[str] = []

    def record_delay(self, *args, **kwargs):
        self.calls.append(f"delay args={args} kwargs={kwargs}")

    def record_apply_async(self, args=None, kwargs=None, **opts):
        self.calls.append(f"apply_async args={args} kwargs={kwargs} opts={opts}")

class _TaskStub:
    def __init__(self, spy: CeleryDelaySpy):
        self._spy = spy
    # mimic Celery task API parts we use
    def delay(self, *args, **kwargs):
        self._spy.record_delay(*args, **kwargs)
        return None
    def apply_async(self, args=None, kwargs=None, **opts):
        self._spy.record_apply_async(args=args, kwargs=kwargs or {}, **opts)
        return None

@pytest.fixture(autouse=True)
def celery_delay_spy(monkeypatch):
    """
    Patch the *import site* used by the service:
    content.services.content_service.index_content (and delete_content_index).
    """
    spy = CeleryDelaySpy()

    # Replace the task objects with stubs on the service module itself.
    monkeypatch.setattr(cs, "index_content", _TaskStub(spy), raising=True)

    # If your service calls delete_content_index.delay(...) on delete:
    if hasattr(cs, "delete_content_index"):
        monkeypatch.setattr(cs, "delete_content_index", _TaskStub(spy), raising=True)

    return spy


# ---- Async engine + session --------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def SessionMaker(async_engine):
    return async_sessionmaker(bind=async_engine, expire_on_commit=False, class_=AsyncSession)

@pytest_asyncio.fixture(autouse=True, scope="function")
async def override_get_session(SessionMaker):
    async def _dep():
        async with SessionMaker() as s:
            yield s
    app.dependency_overrides[get_session] = _dep
    yield
    app.dependency_overrides.pop(get_session, None)

@pytest_asyncio.fixture
async def db_session(SessionMaker):
    async with SessionMaker() as s:
        yield s


@pytest_asyncio.fixture(scope="function")
async def fake_cache(monkeypatch) -> _FakeCache:
    fc = _FakeCache()
    # Patch the exact imported symbol the service uses
    import content.services.content_service as cs
    import content.services.media_service as ms
    monkeypatch.setattr(cs, "cache", fc, raising=False)
    monkeypatch.setattr(ms, "cache", fc, raising=False)

    # Also patch the module where cache is defined (belt-and-suspenders)
    import app.core.cache as core_cache
    monkeypatch.setattr(core_cache, "cache", fc, raising=False)

    return fc


@pytest_asyncio.fixture(scope="function")
async def fake_indexer(monkeypatch) -> FakeIndexer:
    fi = FakeIndexer()
    # Make OpenSearchIndexer return our fake
    import content.adapters.outbound.indexer_opensearch as io
    monkeypatch.setattr(io, "OpenSearchIndexer", lambda *a, **k: fi, raising=False)
    return fi

@pytest_asyncio.fixture(scope="function")
async def override_get_services(override_get_session, fake_cache, fake_indexer, db_session: AsyncSession):
    """
    Override the router's get_services so handlers use:
      - the same AsyncSession,
      - Fake cache for cache_port,
      - Fake indexer via monkeypatch above,
      - Real repositories bound to the same session.
    """
    from content.routers import contents as contents_router
    from content.routers import media as media_rounter
    from content.domain.repositories import ContentRepository, ContentMediaRepository
    from content.domain.repositories.category_repository import CategoryRepository
    from content.services.content_service import ContentService
    from content.services.media_service import ContentMediaService

    async def _get_services_override():
        return ContentService(
                repo=ContentRepository(db_session),
                categories_repo=CategoryRepository(db_session),
                media_repo=ContentMediaRepository(db_session),
                cache_port=fake_cache,  # delete_keys/delete_prefix go here
            )
    async def _get_media_services_override():
        return ContentMediaService(
                repo=ContentMediaRepository(db_session),
                cache_port=fake_cache,  # delete_keys/delete_prefix go here
            )


    app.dependency_overrides[contents_router.get_services] = _get_services_override
    app.dependency_overrides[media_rounter.get_service] = _get_media_services_override
    try:
        yield
    finally:
        app.dependency_overrides.pop(contents_router.get_services, None)
        app.dependency_overrides.pop(media_rounter.get_service, None)


# ---- HTTP client -------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def client(override_get_services) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://testserver") as c:
        yield c
