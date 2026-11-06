"""Real HTTP + stored images + Gemini. Opt-in; never replaced with provider doubles."""

import json
import os

import httpx
import pytest

from app.core.config import Settings
from app.evaluation.rag import audit_citations

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_RAG_E2E") != "1",
        reason="Requires running API, indexed images and real LLM key",
    ),
]


async def test_real_metadata_generation_and_visual_insufficiency():
    cfg = Settings()
    async with httpx.AsyncClient(
        base_url=os.getenv("RAG_TEST_BASE_URL", "http://backend:8000"),
        headers={"Authorization": "Bearer " + cfg.api_token.get_secret_value()},
        timeout=12,
    ) as c:
        response = await c.post(
            "/api/v1/rag/explain",
            json={
                "query": "a cup of coffee",
                "top_k": 1,
                "question": "What are the image format and dimensions in the metadata?",
                "language": "en",
            },
        )
        assert response.status_code == 200
        result = response.json()
        assert result["results"] and result["rag"]["generated"], {
            "error_code": result["rag"]["error_code"],
            "latency": result["latency"],
        }
        assert result["rag"]["citations"] and audit_citations(result)["exact_quote_support"] == 1
        assert result["latency"]["provider_ttft_ms"] > 0
        assert result["latency"]["provider_ttlast_ms"] >= result["latency"]["provider_ttft_ms"]
        identities = [r["image_id"] for r in result["results"]]
        missing = await c.post(
            "/api/v1/rag/explain",
            json={
                "image_ids": identities,
                "question": "Does this image contain a red motorcycle?",
                "language": "en",
            },
        )
        assert missing.status_code == 200 and missing.json()["results"]
        assert missing.json()["rag"]["grounding_status"] == "insufficient_evidence"
        assert not missing.json()["rag"]["generated"]


async def test_real_provider_stream_and_validated_final_event():
    cfg = Settings()
    async with httpx.AsyncClient(
        base_url=os.getenv("RAG_TEST_BASE_URL", "http://backend:8000"),
        headers={"Authorization": "Bearer " + cfg.api_token.get_secret_value()},
        timeout=12,
    ) as c:
        response = await c.post(
            "/api/v1/rag/explain/stream",
            json={
                "query": "a cup of coffee",
                "question": "Metadata ghi định dạng và kích thước như thế nào?",
                "language": "vi",
                "top_k": 1,
            },
        )
        assert response.status_code == 200
        events = []
        for block in response.text.split("\n\n"):
            lines = block.splitlines()
            if len(lines) == 2:
                events.append(
                    (lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: ")))
                )
        assert events[0][0] == "retrieval_started"
        assert any(e == "token" and v["verified"] is False for e, v in events)
        assert events[-1][0] == "generation_completed"
        assert events[-1][1]["rag"]["generated"]
        assert audit_citations(events[-1][1])["citation_id_validity"] == 1
