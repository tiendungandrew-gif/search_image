"""Real CLIP on synthetic images; no semantic relevance/faithfulness claim."""

import os
from types import SimpleNamespace
from uuid import uuid4

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient
from qa_tools.seed_qa import seed

from app.core.exceptions import AppError
from app.main import create_app
from app.schemas.rag import RagRequest
from app.services.rag.llm_provider import ProviderChunk
from app.services.rag.rag_service import RagService
from app.services.search.registry import SearchRegistry
from tests.fixtures.synthetic import image_bytes

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_QA_AI") != "1", reason="Requires optional cached real CLIP profile"
    ),
]


async def test_real_clip_empty_to_indexed_search_agent_and_rag_fixture(qa_resources):
    cfg = qa_resources.settings
    result = await seed(qa_resources.services)
    assert result["images_before"] == 0 and result["dimension"] == 512
    cfg.search_enabled = True
    cfg.agent_enabled = True
    cfg.agent_allow_fixture_knowledge = True
    headers = {"Authorization": "Bearer " + cfg.api_token.get_secret_value()}
    app = create_app(cfg)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app), base_url="http://qa", headers=headers) as client,
    ):
        status = (await client.get("/api/v1/system/workspace")).json()
        assert status["dataset"]["state"] == "ready" and status["dataset"]["vectors"] == 6
        for mode, query in [
            ("text", "colored shapes"),
            ("multi_intent", "colored shapes and a rectangle"),
            ("multi_intent", "a rectangle or a circle"),
        ]:
            response = await client.post(
                "/api/v1/search",
                json={
                    "mode": mode,
                    "text": query,
                    "top_k": 3,
                    "rerank": {"enabled": True, "on_failure": "error"},
                },
            )
            assert response.status_code == 200
            body = response.json()
            assert len(body["results"]) == 3
            assert len({image["image_id"] for image in body["results"]}) == 3
            assert all(np.isfinite(image["score"]) for image in body["results"])
            if mode == "multi_intent":
                assert any(
                    a["status"] == "unknown"
                    for image in body["results"]
                    for a in image["constraint_assessments"]
                )
        for method in ["rrf", "weighted_rrf", "weighted_score"]:
            response = await client.post(
                "/api/v1/search/multimodal",
                files={"image": ("fixture.png", image_bytes(), "image/png")},
                data={
                    "options": '{"mode":"multimodal","text":"colored shapes","top_k":3,'
                    '"fusion":{"method":"' + method + '","text_weight":0.4,"image_weight":0.6}}'
                },
            )
            assert response.status_code == 200 and response.json()["search_mode"] == "multimodal"
        exact = await client.post(
            "/api/v1/search/multimodal",
            files={"image": ("fixture.png", image_bytes(), "image/png")},
            data={"options": '{"mode":"image","top_k":1,"exclude_self":false}'},
        )
        assert (
            exact.status_code == 200
            and exact.json()["results"][0]["image_id"] == result["image_ids"][0]
        )
        assert exact.json()["results"][0]["score"] > 0.99
        # SQL-like text is a value, never an executable filter expression.
        empty = await client.post(
            "/api/v1/search",
            json={"text": "shapes", "filters": {"city": "Paris'); DROP TABLE images; --"}},
        )
        assert empty.status_code == 200 and empty.json()["results"] == []
        agent = await client.post(
            "/api/v1/search/agent",
            json={
                "query": "Find landmarks in the city where Fixture Lake Alpha is located",
                "top_k": 3,
            },
        )
        assert agent.status_code == 200
        assert agent.json()["status"] == "completed" and agent.json()["tool_calls"] == 4
        assert [image["image_id"] for image in agent.json()["results"]] == [result["image_ids"][0]]

        # No real LLM is required: validate context/citations with an explicit provider double.
        class FixtureProvider:
            async def stream(self, messages, **kwargs):
                import json

                message = messages[-1]["content"]
                data = json.loads(message[message.index('{"QUESTION_DATA":') :])
                yield ProviderChunk(
                    json.dumps(
                        {"fact_ids": [fact["fact_id"] for fact in data["EVIDENCE_DATA"]][:2]}
                    ),
                    returned_model="fixture-selector",
                )

        generator = app.state.rag_generator
        generator.provider, generator.error_code = FixtureProvider(), None
        try:
            explained = await RagService(app.state.search_runtime, generator).execute(
                RagRequest(
                    image_ids=result["image_ids"][:2],
                    expected_index_id=result["index_id"],
                    question="What is the metadata format?",
                ),
                str(uuid4()),
            )
            assert explained.rag.generated and explained.rag.citations
            assert all(str(c.image_id) in result["image_ids"] for c in explained.rag.citations)
        finally:
            generator.provider = None
        mismatch = SearchRegistry(
            qa_resources.services, SimpleNamespace(dimension=512, manifest_sha256="0" * 64)
        )
        with pytest.raises(AppError) as error:
            await mismatch.load(result["index_id"])
        assert error.value.code == "MODEL_INDEX_MISMATCH"
