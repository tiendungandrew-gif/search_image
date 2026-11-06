"""Real-model/API profiling and identity checks; not semantic ground truth."""

import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import Settings
from app.db.models import Image
from app.main import create_app

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_EVALUATION_E2E") != "1",
        reason="Requires real CLIP/index and RUN_EVALUATION_E2E=1",
    ),
]


async def test_real_profiling_and_identity_receipts():
    cfg = Settings(search_enabled=True)
    app = create_app(cfg)
    async with app.router.lifespan_context(app):
        assert app.state.search_runtime.available
        headers = {"Authorization": "Bearer " + cfg.api_token.get_secret_value()}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            denied = await client.get("/api/v1/system/search-runtime")
            assert denied.status_code == 401
            result = await client.get("/api/v1/system/search-runtime", headers=headers)
            assert result.status_code == 200
            value = result.json()
            assert value["model"]["dimension"] == 512 and value["model_initialization_ms"] > 0
            assert value["process_memory_kib"]["VmRSS"] > 0
            assert not any(
                key in value for key in ["api_token", "database_url", "minio_secret_key"]
            )
            async with app.state.services.database.sessions() as session:
                identity = await session.scalar(
                    select(Image.id).where(Image.status == "available").order_by(Image.id)
                )
            found = await client.post(
                "/api/v1/search",
                headers=headers,
                json={
                    "image_id": str(identity),
                    "mode": "image",
                    "exclude_self": False,
                    "top_k": 1,
                },
            )
            assert found.status_code == 200 and found.json()["results"][0]["image_id"] == str(
                identity
            )
            assert found.json()["results"][0]["score"] > 0.99
