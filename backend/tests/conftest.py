import secrets
from unittest.mock import AsyncMock

import pytest

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        app_env="test",
        search_enabled=False,
        rag_enabled=False,
        debug=False,
        database_url=f"postgresql+psycopg://fixture:{secrets.token_hex(16)}@127.0.0.1:5432/fixture",
        qdrant_url="http://127.0.0.1:6333",
        minio_endpoint="127.0.0.1:9000",
        minio_access_key=secrets.token_hex(8),
        minio_secret_key=secrets.token_hex(24),
        api_token=secrets.token_hex(24),
        minio_auto_create_bucket=False,
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
