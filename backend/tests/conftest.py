import os
import secrets
from unittest.mock import AsyncMock

import pytest

from app.core.config import Settings
from app.main import create_app


@pytest.fixture(autouse=True)
def require_isolated_integration_environment(request):
    if request.node.get_closest_marker("integration"):
        if os.getenv("QA_ISOLATED") != "1":
            pytest.fail("Integration tests require scripts/qa.py and an isolated QA environment")
        from sqlalchemy.engine import make_url

        cfg = Settings()
        url = make_url(cfg.database_url.get_secret_value())
        if (
            cfg.app_env != "test"
            or url.host != "qa-postgres"
            or not url.database.startswith("image_search_qa")
        ):
            pytest.fail("Refusing integration tests against a serving or unrecognized database")


@pytest.fixture
def settings():
    defaults = {
        name: field.get_default(call_default_factory=True)
        for name, field in Settings.model_fields.items()
        if not field.is_required()
    }
    defaults.update(
        app_env="test",
        search_enabled=False,
        guest_search_enabled=False,
        rag_enabled=False,
        agent_enabled=False,
        agent_llm_planning_enabled=False,
        debug=False,
        minio_auto_create_bucket=False,
        auth_legacy_tokens_enabled=True,
    )
    return Settings(
        _env_file=None,
        **defaults,
        database_url=f"postgresql+psycopg://fixture:{secrets.token_hex(16)}@127.0.0.1:5432/fixture",
        qdrant_url="http://127.0.0.1:6333",
        minio_endpoint="127.0.0.1:9000",
        minio_access_key=secrets.token_hex(8),
        minio_secret_key=secrets.token_hex(24),
        api_token=secrets.token_hex(24),
    )


@pytest.fixture
def fake_services():
    # Unit double; không phải bằng chứng connectivity với dịch vụ thật.
    class FakeServices:
        initialize = AsyncMock()
        close = AsyncMock()
        readiness = AsyncMock(
            return_value={
                "postgresql": "healthy",
                "qdrant": "healthy",
                "minio": "healthy",
            }
        )

    return FakeServices()


@pytest.fixture
def app(settings, fake_services):
    return create_app(settings, services_factory=lambda _: fake_services)


@pytest.fixture
def auth_headers(settings):
    return {"Authorization": f"Bearer {settings.api_token.get_secret_value()}"}
