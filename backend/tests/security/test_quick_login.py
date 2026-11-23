"""Quick sign-in is an explicit local feature, never a production authorization path."""

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.config import Settings
from app.core.quick_login import quick_login_enabled
from app.main import create_app
from app.schemas.access import CreateUser


def test_quick_login_default_off_and_config_rejects_production_or_public(settings):
    assert not settings.auth_quick_login_enabled
    assert not quick_login_enabled(settings)
    local = settings.model_copy(update={"auth_quick_login_enabled": True})
    assert quick_login_enabled(local)
    for changes in [
        {"app_env": "production"},
        {"cors_origins": ["https://search.example.org"], "auth_cookie_secure": True},
    ]:
        with pytest.raises(ValidationError):
            Settings.model_validate(
                {**settings.model_dump(), "auth_quick_login_enabled": True, **changes}
            )
        assert not quick_login_enabled(local.model_copy(update=changes))


async def test_quick_login_route_disabled_and_cannot_select_an_arbitrary_role(settings):
    app = create_app(settings)
    async with AsyncClient(transport=ASGITransport(app), base_url="http://qa") as client:
        assert (
            await client.post("/api/v1/auth/quick-login", json={"role": "admin"})
        ).status_code == 404
        assert (
            await client.post("/api/v1/auth/quick-login", json={"role": "owner"})
        ).status_code == 422
        assert (
            await client.post(
                "/api/v1/auth/quick-login", json={"role": "admin", "username": "admin"}
            )
        ).status_code == 422


def test_public_account_creation_cannot_mark_an_account_as_demo():
    with pytest.raises(ValidationError):
        CreateUser(
            username="demo_admin",
            password="long-enough-password",
            display_name="Demo",
            role="admin",
            is_demo=True,
        )
