# content/tests/routers/test_discovery_router.py

import pytest
from datetime import date
from uuid import UUID, uuid4
from httpx import AsyncClient

from app.main import app
from app.core.auth import optional_current_user
from discovery.services.discovery_service import DiscoveryService
from shared.entities.media import ContentMediaOut
from shared.entities.content import ContentOut


# ------------------------------------------------------------------------------
# Helpers: make deterministic DTOs (match response_model=ContentOut)
# ------------------------------------------------------------------------------

def _mk_media(content_id: UUID) -> dict:
    # keep the same signature for convenience, but do not include content_id
    return {
        "id": str(uuid4()),
        "media_type": "video",
        "source": "external",
        "media_provider": "youtube",
        "media_file": None,
        "external_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "created_at": "2025-08-14T22:00:00Z",
        "updated_at": "2025-08-14T22:05:00Z",
    }


def _mk_content(idx: int = 1) -> dict:
    cid = uuid4()
    return {
        "id": str(cid),
        "title": f"City Stories — Ep. {idx}",
        "description": "A deep dive into urban design.",
        "categories": ["documentary"],
        "language": "en",
        "duration": 1460,
        "publication_date": "2025-08-01",
        "created_at": "2025-08-14T22:00:00Z",
        "updated_at": "2025-08-14T22:05:00Z",
        "media": _mk_media(cid),
    }


# ------------------------------------------------------------------------------
# Mock DiscoveryService (captures args so we can assert router forwards correctly)
# ------------------------------------------------------------------------------

class _FakeDiscoveryService(DiscoveryService):  # type: ignore[misc]
    def __init__(self):
        # configure per-test return values
        self._browse_return = []           # list[ContentOut-like dict]
        self._detail_map = {}              # dict[UUID -> ContentOut-like dict]

        # capture last call args (for assertions)
        self.last_browse_args = None       # (q, media_type, category, language, date_from, date_to, limit, offset)
        self.last_detail_id = None

    # The real service has `browse(...)` and `content_detail(id)`; we mirror them.
    async def browse(
        self,
        q,
        media_type,
        category,
        language,
        date_from,
        date_to,
        limit,
        offset,
    ):
        # record exactly what the router passed in (types matter)
        self.last_browse_args = (q, media_type, category, language, date_from, date_to, limit, offset)
        # return what the test configured
        return self._browse_return

    async def content_detail(self, content_id: UUID):
        self.last_detail_id = content_id
        return self._detail_map.get(content_id)


# ------------------------------------------------------------------------------
# Dependency overrides
# ------------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _override_auth():
    # GIVEN: optional auth is bypassed; we only test router behavior
    app.dependency_overrides[optional_current_user] = lambda: None
    yield
    app.dependency_overrides.pop(optional_current_user, None)


@pytest.fixture()
def fake_discovery_service():
    return _FakeDiscoveryService()


@pytest.fixture(autouse=True)
def _override_discovery_dep(fake_discovery_service: _FakeDiscoveryService):
    # Override the DI factory to return our fake service
    from discovery.routers import discovery as discovery_router
    app.dependency_overrides[discovery_router.get_discovery_service] = lambda: fake_discovery_service
    yield
    app.dependency_overrides.pop(discovery_router.get_discovery_service, None)


# ==============================================================================
# /v1/discovery/search
# ==============================================================================

@pytest.mark.asyncio
async def test_should_forward_query_params_and_return_results_when_browse_is_called(
    client: AsyncClient, fake_discovery_service: _FakeDiscoveryService
):
    # GIVEN
    items = [_mk_content(12), _mk_content(13)]
    fake_discovery_service._browse_return = items

    q = "city"
    media_type = "video"
    category = "documentary"
    language = "en"
    date_from = "2025-08-01"
    date_to = "2025-08-31"
    limit = 10
    offset = 5

    # WHEN
    r = await client.get(
        "/v1/discovery/search",
        params=dict(
            q=q,
            media_type=media_type,
            category=category,
            language=language,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        ),
    )

    # THEN
    assert r.status_code == 200

    # Router should have passed **parsed** types to the service
    passed = fake_discovery_service.last_browse_args
    assert passed is not None
    (
        q_passed,
        media_type_passed,
        category_passed,
        language_passed,
        date_from_passed,
        date_to_passed,
        limit_passed,
        offset_passed,
    ) = passed

    assert q_passed == q
    assert media_type_passed == media_type
    assert category_passed == category
    assert language_passed == language
    assert date_from_passed == date.fromisoformat(date_from)   # parsed to date
    assert date_to_passed == date.fromisoformat(date_to)       # parsed to date
    assert limit_passed == limit
    assert offset_passed == offset

    # Full payload assertions (shape and field values)
    body = r.json()
    assert isinstance(body, list) and len(body) == 2
    for i, it in enumerate(items):
        got = body[i]
        assert got["id"] == it["id"]
        assert got["title"] == it["title"]
        assert got["description"] == it["description"]
        assert got["categories"] == it["categories"]
        assert got["language"] == it["language"]
        assert got["duration"] == it["duration"]
        assert got["publication_date"] == it["publication_date"]
        assert got["created_at"] == it["created_at"]
        assert got["updated_at"] == it["updated_at"]
        # media nested
        assert got["media"] == it["media"]


@pytest.mark.asyncio
async def test_should_return_empty_list_when_browse_finds_no_results(
    client: AsyncClient, fake_discovery_service: _FakeDiscoveryService
):
    # GIVEN
    fake_discovery_service._browse_return = []

    # WHEN
    r = await client.get("/v1/discovery/search", params={"q": "nothing", "limit": 3})

    # THEN
    assert r.status_code == 200
    body = r.json()
    assert body == []


@pytest.mark.asyncio
async def test_should_reject_invalid_media_type_with_422(client: AsyncClient):
    # GIVEN (invalid media_type pattern)
    params = {"media_type": "ebook"}

    # WHEN
    r = await client.get("/v1/discovery/search", params=params)

    # THEN
    assert r.status_code == 422  # pattern validation enforced by router


@pytest.mark.asyncio
async def test_should_reject_limit_above_max_with_422(client: AsyncClient):
    # GIVEN (limit > 100)
    params = {"limit": 101}

    # WHEN
    r = await client.get("/v1/discovery/search", params=params)

    # THEN
    assert r.status_code == 422  # limit range validation enforced by router


# ==============================================================================
# /v1/discovery/contents/{id}
# ==============================================================================

@pytest.mark.asyncio
async def test_should_return_content_when_content_detail_exists(
    client: AsyncClient, fake_discovery_service: _FakeDiscoveryService
):
    # GIVEN
    c = _mk_content(42)
    cid = UUID(c["id"])
    fake_discovery_service._detail_map[cid] = c

    # WHEN
    r = await client.get(f"/v1/discovery/contents/{cid}")

    # THEN
    assert r.status_code == 200
    assert fake_discovery_service.last_detail_id == cid

    body = r.json()
    # full field-by-field assertions
    assert body["id"] == c["id"]
    assert body["title"] == c["title"]
    assert body["description"] == c["description"]
    assert body["categories"] == c["categories"]
    assert body["language"] == c["language"]
    assert body["duration"] == c["duration"]
    assert body["publication_date"] == c["publication_date"]
    assert body["created_at"] == c["created_at"]
    assert body["updated_at"] == c["updated_at"]
    assert body["media"] == c["media"]


@pytest.mark.asyncio
async def test_should_return_404_when_content_detail_absent(
    client: AsyncClient, fake_discovery_service: _FakeDiscoveryService
):
    # GIVEN
    cid = uuid4()
    # (do not put it in _detail_map -> simulates missing item)

    # WHEN
    r = await client.get(f"/v1/discovery/contents/{cid}")

    # THEN
    assert r.status_code == 404
    assert r.json() == {"detail": "not found"}
