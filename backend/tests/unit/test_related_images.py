from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.api.v1.images import related_images
from app.core.exceptions import AppError


def request(role="user", available=True):
    return SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(
            settings=SimpleNamespace(search_enabled=True, search_max_top_k=50, guest_max_top_k=10),
            search_runtime=SimpleNamespace(available=available),
        )),
        state=SimpleNamespace(principal=SimpleNamespace(role=role), request_id=uuid4()),
    )


async def test_related_reuses_scoped_image_search_and_excludes_reference(monkeypatch):
    charge = AsyncMock()
    execute = AsyncMock(return_value="result")
    monkeypatch.setattr("app.api.v1.images.charge_usage", charge)
    monkeypatch.setattr(
        "app.services.search.search_service.SearchService",
        lambda _: SimpleNamespace(execute=execute),
    )
    image_id = uuid4()
    req = request()
    assert await related_images(image_id, req, 24) == "result"
    options = execute.call_args.args[0]
    assert options.image_id == image_id and options.mode == "image"
    assert options.exclude_self and options.top_k == 24
    charge.assert_awaited_once_with(req, "search")


async def test_guest_related_respects_quota_and_guest_limit(monkeypatch):
    charge = AsyncMock()
    execute = AsyncMock(return_value="result")
    monkeypatch.setattr("app.api.v1.images.charge_guest_search", charge)
    monkeypatch.setattr(
        "app.services.search.search_service.SearchService",
        lambda _: SimpleNamespace(execute=execute),
    )
    req = request("guest")
    await related_images(uuid4(), req, 24)
    assert execute.call_args.args[0].top_k == 10
    charge.assert_awaited_once_with(req)


async def test_unavailable_model_returns_retryable_error():
    with pytest.raises(AppError) as issue:
        await related_images(uuid4(), request(available=False), 24)
    assert issue.value.status == 503 and issue.value.retryable


async def test_inaccessible_reference_remains_not_found(monkeypatch):
    execute = AsyncMock(side_effect=AppError(404, "IMAGE_NOT_FOUND", "Not found"))
    monkeypatch.setattr("app.api.v1.images.charge_usage", AsyncMock())
    monkeypatch.setattr(
        "app.services.search.search_service.SearchService",
        lambda _: SimpleNamespace(execute=execute),
    )
    with pytest.raises(AppError) as issue:
        await related_images(uuid4(), request(), 24)
    assert issue.value.status == 404
