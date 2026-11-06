import pytest
from pydantic import ValidationError

from app.core.config import Settings


def replace(settings, **overrides):
    return Settings(_env_file=None, **(settings.model_dump() | overrides))


@pytest.mark.parametrize(
    "change",
    [
        {"database_url": "sqlite:///database.db"},
        {"minio_endpoint": "http://minio:9000/path"},
        {"qdrant_url": "http://user:secret@localhost:6333"},
        {"api_token": "short"},
        {"minio_secret_key": "changeme-password"},
        {"cors_origins": ["*"]},
        {"cors_origins": ["http://localhost:5173/path"]},
        {"request_timeout_seconds": 0},
        {"dependency_timeout_seconds": 5},
        {"database_pool_size": 0},
        {"api_prefix": "/v2"},
        {"app_env": "production", "debug": True},
        {"app_env": "production", "minio_auto_create_bucket": True},
    ],
)
def test_invalid_settings_rejected(settings, change):
    with pytest.raises(ValidationError):
        replace(settings, **change)


def test_empty_optional_qdrant_key_and_secret_repr(settings):
    value = replace(settings, qdrant_api_key="")
    assert value.qdrant_api_key is None
    assert value.api_token.get_secret_value() not in repr(value)
    assert value.database_url.get_secret_value() not in repr(value)
