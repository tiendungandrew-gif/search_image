"""Real CLIP/Qdrant/PG/MinIO tests trên corpus Phase 04; không qrels/accuracy claim."""

import asyncio
import hashlib
import os
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient
from qdrant_client import models as qm
from sqlalchemy import func, select

from app.core.config import Settings
from app.db.models import Image, IndexingJob
from app.main import create_app

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_SEARCH_E2E") != "1",
        reason="Cần active index/model/cache và RUN_SEARCH_E2E=1",
    ),
]


async def test_real_text_image_search_and_failure_paths():
    settings = Settings(search_enabled=True)
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        runtime = app.state.search_runtime
        assert runtime.available
        services = runtime.services
        vector = await runtime.compute(lambda: runtime.encoder.encode_text(["a cup of coffee"]))
        assert vector.shape == (1, 512) and np.isfinite(vector).all()
        assert np.linalg.norm(vector[0]) == pytest.approx(1, abs=1e-5)
        with pytest.raises(Exception) as error:
            await runtime.compute(lambda: runtime.encoder.encode_text(["coffee " * 150]))
        assert getattr(error.value, "code", None) == "TEXT_TOKEN_LIMIT"
        headers = {"Authorization": "Bearer " + settings.api_token.get_secret_value()}
        async with services.database.sessions() as session:
            before = (
                await session.scalar(select(func.count()).select_from(Image)),
                await session.scalar(select(func.count()).select_from(IndexingJob)),
            )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for query in [
                "a cup of coffee",
                "a brown cat",
                "stars and galaxies in deep space",
                "a rocket launching into the sky",
            ]:
                response = await client.post(
                    "/api/v1/search",
                    headers=headers,
                    json={"query": query, "search_mode": "semantic", "top_k": 3},
                )
                assert response.status_code == 200, response.json()
                value = response.json()
                assert 0 < len(value["results"]) <= 3
                assert len({r["image_id"] for r in value["results"]}) == len(value["results"])
                scores = [r["score"] for r in value["results"]]
                assert scores == sorted(scores, reverse=True)
                for result in value["results"]:
                    content = await client.get(result["image_url"], headers=headers)
                    assert (
                        content.status_code == 200
                        and content.headers["cache-control"] == "private, no-store"
                    )
            data = await asyncio.to_thread(
                Path(settings.dataset_root, "sample", "coffee.png").read_bytes
            )
            async with services.database.sessions() as session:
                identity = await session.scalar(
                    select(Image.id).where(Image.sha256 == hashlib.sha256(data).hexdigest())
                )
            response = await client.post(
                "/api/v1/search/multimodal",
                headers=headers,
                files={"image": ("filename-is-not-a-query.jpg", data, "application/octet-stream")},
                data={"options": '{"mode":"image","top_k":3,"exclude_self":false}'},
            )
            assert response.status_code == 200, response.json()
            assert response.json()["results"][0]["image_id"] == str(identity)
            assert response.json()["results"][0]["score"] > 0.99
            existing = await client.post(
                "/api/v1/search", headers=headers, json={"image_id": str(identity), "top_k": 3}
            )
            assert existing.status_code == 200
            assert str(identity) not in [r["image_id"] for r in existing.json()["results"]]
            empty = await client.post(
                "/api/v1/search",
                headers=headers,
                json={"text": "a cat", "filters": {"source_dataset": "does-not-exist"}},
            )
            assert empty.status_code == 200 and empty.json()["results"] == []
            invalid = await client.post(
                "/api/v1/search/multimodal",
                headers=headers,
                files={"image": ("bad.png", b"corrupt", "image/png")},
            )
            assert invalid.status_code == 422
            fusion = await client.post(
                "/api/v1/search/multimodal",
                headers=headers,
                json={"text": "coffee", "image_id": str(identity), "mode": "multimodal"},
            )
            assert fusion.status_code == 200
            assert fusion.json()["search_mode"] == "multimodal"
            assert fusion.json()["effective_settings"]["channels"] == 2
            old = runtime.registry.index.collection_name
            isolated = "search_fixture_" + uuid4().hex
            try:
                runtime.registry.index.collection_name = "missing_" + uuid4().hex
                missing = await client.post(
                    "/api/v1/search", headers=headers, json={"text": "coffee"}
                )
                assert missing.status_code == 503
                # Isolated incompatible fixture; không thay collection ứng dụng.
                await services.qdrant.client.create_collection(
                    isolated, vectors_config=qm.VectorParams(size=7, distance=qm.Distance.COSINE)
                )
                runtime.registry.index.collection_name = isolated
                mismatch = await client.post(
                    "/api/v1/search", headers=headers, json={"text": "coffee"}
                )
                assert mismatch.status_code == 409
            finally:
                runtime.registry.index.collection_name = old
                if await services.qdrant.client.collection_exists(isolated):
                    await services.qdrant.client.delete_collection(isolated)
            metrics = await client.get("/api/v1/system/search-metrics", headers=headers)
            assert metrics.status_code == 200
            samples = metrics.json()["samples"]
            assert samples and all(s["server_response_ms"] >= 0 for s in samples)
            assert all("text" not in s for s in samples)
        async with services.database.sessions() as session:
            after = (
                await session.scalar(select(func.count()).select_from(Image)),
                await session.scalar(select(func.count()).select_from(IndexingJob)),
            )
        assert before == after  # Query uploads không persist corpus/jobs.
