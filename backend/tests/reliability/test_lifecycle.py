from unittest.mock import AsyncMock

import pytest

from app.main import create_app


async def test_generator_construction_failure_still_closes_database_services(
    settings, fake_services, monkeypatch
):
    class BrokenGenerator:
        def __init__(self, _settings):
            raise RuntimeError("provider_construction_failed")

    monkeypatch.setattr("app.services.rag.generator.Generator", BrokenGenerator)
    app = create_app(settings, services_factory=lambda _: fake_services)
    with pytest.raises(RuntimeError):
        async with app.router.lifespan_context(app):
            pass
    fake_services.close.assert_awaited_once()


async def test_shutdown_failure_does_not_skip_remaining_resource_cleanup(
    settings, fake_services, monkeypatch
):
    class BrokenGenerator:
        close = AsyncMock(side_effect=RuntimeError("provider_close_failed"))

        def __init__(self, _settings):
            pass

    monkeypatch.setattr("app.services.rag.generator.Generator", BrokenGenerator)
    app = create_app(settings, services_factory=lambda _: fake_services)
    with pytest.raises(RuntimeError):
        async with app.router.lifespan_context(app):
            pass
    fake_services.close.assert_awaited_once()
