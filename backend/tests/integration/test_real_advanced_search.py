"""Actual CLIP/PG/Qdrant/MinIO; labels chất lượng chưa có, không tự tạo qrels."""

import asyncio
import hashlib
import json
import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.config import Settings
from app.db.models import Image, IndexingJob
from app.main import create_app
from app.services.search.multi_intent import AdvancedRetriever
from app.services.search.reranker import LightweightReranker

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_ADVANCED_E2E") != "1", reason="Cần active CLIP/index và RUN_ADVANCED_E2E=1"
    ),
]


async def test_real_multimodal_multi_intent_constraints_and_baseline(monkeypatch):
    settings = Settings(search_enabled=True)
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        runtime = app.state.search_runtime
        assert runtime.available
        data = await asyncio.to_thread(
            Path(settings.dataset_root, "sample", "coffee.png").read_bytes
        )
        async with runtime.services.database.sessions() as session:
            identity = await session.scalar(
                select(Image.id).where(Image.sha256 == hashlib.sha256(data).hexdigest())
            )
            before = (
                await session.scalar(select(func.count()).select_from(Image)),
                await session.scalar(select(func.count()).select_from(IndexingJob)),
            )
        headers = {"Authorization": "Bearer " + settings.api_token.get_secret_value()}
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", headers=headers
        ) as client:
            baseline = await client.post(
                "/api/v1/search", json={"mode": "text", "text": "a cup of coffee", "top_k": 10}
            )
            assert (
                baseline.status_code == 200
                and baseline.json()["effective_settings"]["channels"] == 1
            )
            assert baseline.json()["effective_settings"]["rerank_applied"] is False
            for query in [
                "coffee and a brown cat",
                "coffee or a brown cat",
                "cà phê và mèo màu nâu",
                "cà phê hoặc mèo màu nâu",
                "(coffee and a cat) or a rocket",
            ]:
                reply = await client.post(
                    "/api/v1/search",
                    json={
                        "query": query,
                        "search_mode": "multi_intent",
                        "rerank": True,
                        "top_k": 5,
                    },
                )
                assert reply.status_code == 200, reply.json()
                value = reply.json()
                assert value["results"] and value["effective_settings"]["rerank_applied"]
                assert 2 <= value["effective_settings"]["channels"] <= 4
                assert all(
                    a["status"] == "unknown"
                    for row in value["results"]
                    for a in row["constraint_assessments"]
                )
                assert all(
                    a["semantic_score"] is not None
                    for row in value["results"]
                    for a in row["constraint_assessments"]
                )
                assert all(row["score_type"] == "reranker" for row in value["results"])
                assert [r["score"] for r in value["results"]] == sorted(
                    [r["score"] for r in value["results"]], reverse=True
                )
            for method in ["rrf", "weighted_score"]:
                reply = await client.post(
                    "/api/v1/search/multimodal",
                    files={"image": ("arbitrary-name.webp", data, "image/webp")},
                    data={
                        "query": "a cup of coffee",
                        "search_mode": "multimodal",
                        "top_k": "5",
                        "fusion_strategy": method,
                        "text_weight": "0.4",
                        "image_weight": "0.6",
                        "rerank": "true",
                    },
                )
                assert reply.status_code == 200, reply.json()
                value = reply.json()
                assert (
                    value["search_mode"] == "multimodal"
                    and value["effective_settings"]["fusion_version"] == method + "-v1"
                )
                assert value["effective_settings"]["channels"] == 2
                # Fusion is a union: with >50 images, an image can occur in only one branch.
                for row in value["results"]:
                    parts = row["contributing_branches"]
                    assert parts and {c["branch"] for c in parts} <= {"whole", "image"}
                    for part in parts:
                        weight = 0.6 if part["branch"] == "image" else 0.4
                        assert part["weight"] == pytest.approx(weight)
                        assert 1 <= part["rank"] <= 50
                        expected = weight * (
                            (part["cosine"] + 1) / 2
                            if method == "weighted_score"
                            else 1 / (60 + part["rank"])
                        )
                        assert part["contribution"] == pytest.approx(expected)
                fixture = await client.post(
                    "/api/v1/search/multimodal",
                    files={"image": ("fixture.png", data, "image/png")},
                    data={
                        "options": json.dumps(
                            {
                                "text": "a cup of coffee",
                                "mode": "multimodal",
                                "top_k": 5,
                                "filters": {"source_dataset": "scikit-image-v0.25.2"},
                                "fusion": {
                                    "method": method,
                                    "text_weight": 0.4,
                                    "image_weight": 0.6,
                                },
                                "rerank": {"enabled": True},
                            }
                        )
                    },
                )
                assert fixture.status_code == 200, fixture.json()
                assert fixture.json()["results"]
                assert all(
                    {c["branch"] for c in row["contributing_branches"]} == {"whole", "image"}
                    for row in fixture.json()["results"]
                )
                content = await client.get(value["results"][0]["image_url"])
                assert content.status_code == 200 and len(content.content) > 0
            strict = await client.post(
                "/api/v1/search",
                json={"text": "cat and coffee", "mode": "multi_intent", "require_verified": True},
            )
            assert (
                strict.status_code == 409
                and strict.json()["error"]["code"] == "VERIFIER_UNAVAILABLE"
            )
            explicit = {
                "op": "or",
                "clauses": [
                    {"id": "yes", "kind": "metadata", "filter": {"min_width": 1}},
                    {"id": "no", "kind": "metadata", "filter": {"min_width": 100000}},
                ],
            }
            metadata = await client.post(
                "/api/v1/search",
                json={"text": "coffee", "constraints": explicit, "require_verified": True},
            )
            assert metadata.status_code == 200 and metadata.json()["results"]
            explicit["op"] = "and"
            empty = await client.post(
                "/api/v1/search", json={"text": "coffee", "constraints": explicit}
            )
            assert empty.status_code == 200 and empty.json()["results"] == []
            unknown = await client.post(
                "/api/v1/search",
                json={
                    "text": "coffee",
                    "constraints": {"id": "x", "kind": "metadata", "filter": {"city": "Hanoi"}},
                    "require_verified": True,
                },
            )
            assert unknown.status_code == 200 and unknown.json()["results"] == []
            relational = await client.post(
                "/api/v1/search",
                json={"text": "Find landmarks in the city where Hoan Kiem Lake is located"},
            )
            assert (
                relational.status_code == 409
                and relational.json()["error"]["code"] == "UNSUPPORTED_RELATIONAL_QUERY"
            )
            uncertain = await client.post("/api/v1/search", json={"text": "black and white cat"})
            assert (
                uncertain.status_code == 200
                and uncertain.json()["effective_settings"]["channels"] == 1
            )
            assert uncertain.json()["query_analysis"]["uncertain"]
            with monkeypatch.context() as patch:
                patch.setattr(settings, "multi_intent_enabled", False)
                basic_fallback = await client.post(
                    "/api/v1/search", json={"text": "coffee and cat"}
                )
                assert (
                    basic_fallback.status_code == 200
                    and basic_fallback.json()["effective_settings"]["channels"] == 1
                )
                disabled = await client.post(
                    "/api/v1/search", json={"text": "coffee and cat", "mode": "multi_intent"}
                )
                assert disabled.status_code == 409
            absent = await client.post("/api/v1/search/multimodal", json={})
            assert absent.status_code == 422
            malformed = await client.post(
                "/api/v1/search/multimodal",
                json={"text": "coffee", "fusion_strategy": "unsupported"},
            )
            assert malformed.status_code == 422
            text_only = await client.post(
                "/api/v1/search/multimodal", files={"query": (None, "coffee")}
            )
            assert text_only.status_code == 200 and text_only.json()["search_mode"] == "text"
            with monkeypatch.context() as patch:

                def broken(*args):
                    raise RuntimeError("isolated rerank failure fixture")

                patch.setattr(LightweightReranker, "rank", broken)
                fallback = await client.post(
                    "/api/v1/search",
                    json={
                        "text": "coffee and cat",
                        "rerank": {"enabled": True, "on_failure": "skip"},
                    },
                )
                assert fallback.status_code == 200 and fallback.json()["results"]
                assert fallback.json()["effective_settings"]["rerank_applied"] is False
                assert any(w["code"] == "RERANK_SKIPPED" for w in fallback.json()["warnings"])
                error = await client.post(
                    "/api/v1/search", json={"text": "coffee and cat", "rerank": True}
                )
                assert error.status_code == 503 and error.json()["error"]["code"] == "RERANK_FAILED"
                simple = await client.post(
                    "/api/v1/search", json={"text": "coffee", "mode": "text"}
                )
                assert simple.status_code == 200
            with monkeypatch.context() as patch:
                original = AdvancedRetriever.stored_scores

                async def slow(self, *args):
                    await asyncio.sleep(0.1)
                    return await original(self, *args)

                patch.setattr(AdvancedRetriever, "stored_scores", slow)
                timed = await client.post(
                    "/api/v1/search",
                    json={
                        "text": "coffee and cat",
                        "rerank": {"enabled": True, "timeout_ms": 1, "on_failure": "skip"},
                    },
                )
                assert timed.status_code == 200 and any(
                    w["code"] == "RERANK_SKIPPED" for w in timed.json()["warnings"]
                )
            async with runtime.services.database.sessions() as session:
                after = (
                    await session.scalar(select(func.count()).select_from(Image)),
                    await session.scalar(select(func.count()).select_from(IndexingJob)),
                )
            assert before == after
            assert identity is not None
