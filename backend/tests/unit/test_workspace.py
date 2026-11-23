import json
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.services.workspace import dataset_state, evaluation_summaries


@pytest.mark.parametrize(
    "images,indexed,vectors,index_status,runtime,expected",
    [
        (0, 0, None, "absent", False, "empty_dataset"),
        (12, 0, None, "building", False, "index_building"),
        (12, 0, None, "absent", False, "index_not_ready"),
        (12, 12, 0, "ready", True, "index_not_ready"),
        (12, 12, 12, "ready", False, "index_not_ready"),
        (12, 12, 12, "ready", True, "ready"),
        (None, None, None, None, False, "unavailable"),
    ],
)
def test_dataset_classification(images, indexed, vectors, index_status, runtime, expected):
    assert (
        dataset_state(
            {"postgresql": "healthy", "minio": "healthy", "qdrant": "healthy"},
            images,
            indexed,
            vectors,
            index_status,
            runtime,
        )
        == expected
    )


def test_database_failure_is_never_empty():
    assert dataset_state({"postgresql": "unhealthy"}, 0, 0, 0, None, False) == "unavailable"


async def test_workspace_and_evaluation_require_server_auth(app, auth_headers, monkeypatch):
    snapshot = AsyncMock(
        return_value={
            "dataset": {
                "state": "empty_dataset",
                "images": 0,
                "available_images": 0,
                "indexed_images": 0,
                "vectors": None,
                "index_id": None,
                "index_status": "absent",
                "generation": None,
            },
            "dependencies": {"postgresql": "healthy", "qdrant": "healthy", "minio": "healthy"},
            "capabilities": {
                name: False
                for name in [
                    "text_search",
                    "image_search",
                    "multimodal",
                    "multi_intent",
                    "rerank",
                    "explanations",
                    "agent",
                ]
            },
            "rag": {"enabled": False, "configured": False, "streaming": False},
            "agent": {"enabled": False, "llm_planning": False},
            "limits": {"top_k": 50, "image_bytes": 20971520},
        }
    )
    monkeypatch.setattr("app.services.workspace.workspace_snapshot", snapshot)
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        for path in ["workspace", "evaluation"]:
            assert (await client.get(f"/api/v1/system/{path}")).status_code == 401
        assert snapshot.await_count == 0
        response = await client.get("/api/v1/system/workspace", headers=auth_headers)
        assert response.json()["dataset"]["state"] == "empty_dataset"
        snapshot.assert_awaited_once()


def test_new_system_endpoints_have_typed_openapi_contracts(app):
    schema = app.openapi()
    for name, model in [("workspace", "WorkspaceSnapshot"), ("evaluation", "EvaluationSummary")]:
        response = schema["paths"][f"/api/v1/system/{name}"]["get"]["responses"]["200"]
        assert (
            response["content"]["application/json"]["schema"]["$ref"]
            == f"#/components/schemas/{model}"
        )


def test_evaluation_unconfigured_empty_and_allowlisted_metrics(tmp_path):
    assert evaluation_summaries(tmp_path / "absent")["state"] == "not_available"
    assert evaluation_summaries(tmp_path)["state"] == "empty"
    run = tmp_path / "phase10" / "run1"
    run.mkdir(parents=True)
    (run / "result.json").write_text(
        json.dumps(
            {
                "status": "measured",
                "attempted": 10,
                "successful": 9,
                "failed": 1,
                "client_success_latency": {"p90_ms": 27.3, "p95_ms": 29.2},
                "samples": [{"query": "private"}],
                "api_key": "must-never-leave-server",
            }
        )
    )
    result = evaluation_summaries(tmp_path)
    row = result["experiments"][0]
    assert result["state"] == "available" and row["p90_ms"] == 27.3
    assert row["recall_at_10"] is None
    assert "private" not in json.dumps(result)
    assert "must-never-leave-server" not in json.dumps(result)


def test_evaluation_skips_corrupt_and_symlink_escape(tmp_path):
    outside = tmp_path / "outside.json"
    outside.write_text('{"status":"private"}')
    root = tmp_path / "results"
    run = root / "phase10" / "broken"
    run.mkdir(parents=True)
    (run / "result.json").symlink_to(outside)
    other = root / "phase10" / "corrupt"
    other.mkdir()
    (other / "result.json").write_text("not json")
    assert evaluation_summaries(root) == {"state": "empty", "experiments": [], "skipped": 2}
