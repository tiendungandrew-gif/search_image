from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from sqlalchemy.dialects.postgresql import dialect

from app.core.access import Principal, current_principal
from app.services.search.discovery import discover_images, discovery_statement


def test_random_sample_filters_permissions_hidden_deleted_and_limits_results():
    scope = current_principal.set(Principal(uuid4(), "reader", "user", (), ("shared",)))
    try:
        sql = str(discovery_statement(12, uuid4()).compile(
            dialect=dialect(), compile_kwargs={"literal_binds": True}
        ))
        assert "source_dataset IN ('shared')" in sql
        assert "image_moderation.hidden IS true" in sql
        assert "images.status = 'available'" in sql
        assert "images.deleted_at IS NULL" in sql
        assert "ORDER BY md5(" in sql and "LIMIT 12" in sql
    finally:
        current_principal.reset(scope)


def test_guest_with_no_public_libraries_has_no_candidates():
    scope = current_principal.set(Principal(None, "guest", "guest"))
    try:
        sql = str(discovery_statement(12, uuid4()).compile(dialect=dialect()))
        assert "false" in sql
    finally:
        current_principal.reset(scope)


async def test_gallery_serializes_real_metadata_and_media_links():
    image_id = uuid4()
    image = SimpleNamespace(id=image_id, width=600, height=400, media_type="image/jpeg")
    meta = SimpleNamespace(title="Đà Nẵng", caption="Bãi biển", source_dataset="shared",
                           city="Đà Nẵng", license="CC0")
    session = AsyncMock()
    session.execute.return_value = MagicMock()
    session.execute.return_value.all.return_value = [(image, meta)]
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=False)
    services = SimpleNamespace(database=SimpleNamespace(sessions=lambda: context))
    result = await discover_images(services, 12)
    assert result["total_results"] == 1
    assert result["has_more"] is False and result["next_cursor"] is None
    assert result["seed"]
    item = result["results"][0]
    assert item.image_id == image_id and item.metadata.title == "Đà Nẵng"
    assert item.thumbnail_url == f"/api/v1/images/{image_id}/content?variant=thumbnail"
    assert item.image_url.endswith("?variant=original")


def test_cursor_keeps_seeded_order_and_does_not_use_offsets():
    seed, image_id = uuid4(), uuid4()
    cursor = "a" * 32 + ":" + str(image_id)
    sql = str(discovery_statement(25, seed, cursor).compile(
        dialect=dialect(), compile_kwargs={"literal_binds": True}
    ))
    assert str(seed) in sql and str(image_id) in sql
    assert ") > (" in sql and "LIMIT 25" in sql
    assert "OFFSET" not in sql


async def test_lookahead_produces_cursor_without_returning_extra_image():
    image = SimpleNamespace(id=uuid4(), width=600, height=400, media_type="image/jpeg")
    other = SimpleNamespace(id=uuid4(), width=600, height=400, media_type="image/jpeg")
    meta = SimpleNamespace(title="Beach", caption=None, source_dataset="shared",
                           city=None, license="CC0")
    session = AsyncMock()
    session.execute.return_value = MagicMock()
    session.execute.return_value.all.return_value = [(image, meta), (other, meta)]
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=False)
    services = SimpleNamespace(database=SimpleNamespace(sessions=lambda: context))
    seed = uuid4()
    result = await discover_images(services, 1, seed)
    assert result["has_more"] is True and len(result["results"]) == 1
    assert result["next_cursor"].endswith(":" + str(image.id))
    assert result["seed"] == str(seed)
