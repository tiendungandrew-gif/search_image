"""Kiểm chứng workflow từ nguồn công khai; không tạo nhãn chất lượng của người đánh giá."""

import argparse
import hashlib
import json
from pathlib import Path

import httpx
from app.evaluation.agent import evaluate_labeled_cases
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]


def verify(output, llm=False, rag=False):
    target = Path(output)
    target.mkdir(parents=True, exist_ok=False)
    payload = json.loads((ROOT / "evaluation/agent/datasets/nps_v1_knowledge.json").read_text())
    download = json.loads((ROOT / "datasets/landmarks_phase09_v1/manifest.json").read_text())
    ingestion = json.loads(
        (ROOT / "docs/verification/phase09_completion_20261106/corpus/ingest.json").read_text()
    )
    expected_ids = {r["image_id"] for r in payload["image_entities"]}
    expected_entities = {r["id"] for r in payload["entities"]}
    expected_relations = {r["id"] for r in payload["relationships"]}
    truth = {
        "source_verified": True,
        "source_manifest_sha256": hashlib.sha256(
            json.dumps(download, sort_keys=True).encode()
        ).hexdigest(),
        "source_urls": sorted({r["source_ref"] for r in payload["relationships"]}),
        "cases": {},
    }
    rows = []
    cases = [
        ("english", "Find landmarks in the city where Washington Monument is located"),
        ("vietnamese", "Tìm ảnh địa danh ở thành phố nơi Washington Monument tọa lạc"),
        ("alias", "Find landmarks in the city where Jefferson Memorial is located"),
    ]
    # Expected IDs originate in the source/import receipts, before any Agent execution.
    for name, _ in cases:
        truth["cases"][name] = {
            "search_mode": "agent",
            "status": "completed",
            "image_ids": sorted(expected_ids),
            "entity_ids": sorted(expected_entities),
            "relationship_ids": sorted(expected_relations),
            "tools": [
                "entity_lookup",
                "relationship_lookup",
                "get_related_entities",
                "semantic_image_search",
            ],
        }
    report = {
        "status": "running",
        "classification": "source_verified_real_workflow",
        "human_quality_verified": False,
        "cases": rows,
    }
    values = dotenv_values(ROOT / ".env")
    try:
        with httpx.Client(
            base_url="http://127.0.0.1:8000",
            timeout=35,
            headers={"Authorization": "Bearer " + values["API_TOKEN"]},
        ) as client:
            for record in download["images"]:
                identity = next(
                    r["image_id"]
                    for r in ingestion["results"]
                    if r["filename"] == record["filename"]
                )
                r = client.get(f"/api/v1/images/{identity}/content?variant=original")
                r.raise_for_status()
                assert hashlib.sha256(r.content).hexdigest() == record["sha256"]
            for name, query in cases:
                r = client.post("/api/v1/search/agent", json={"query": query, "top_k": 10})
                r.raise_for_status()
                result = r.json()
                rows.append({"case_id": name, "result": result})
                assert result["status"] == "completed" and result["tool_calls"] == 4
                assert (
                    result["logical_hops"] == 3
                    and result["verification_state"] == "VERIFIED_WITH_REAL_DATA"
                )
                assert {i["image_id"] for i in result["results"]} == expected_ids
            report["workflow_metrics"] = evaluate_labeled_cases(rows, truth)
            for name, body in [
                (
                    "missing",
                    {
                        "query": cases[0][1].replace(
                            "Washington Monument", "Missing Public Landmark Phase09"
                        )
                    },
                ),
                (
                    "hard_filter",
                    {"query": cases[0][1], "filters": {"source_dataset": "not-nps-dataset"}},
                ),
            ]:
                r = client.post("/api/v1/search/agent", json=body)
                r.raise_for_status()
                value = r.json()
                report[name] = value
                assert value["status"] == "insufficient_evidence" and not value["results"]
            if llm:
                r = client.post(
                    "/api/v1/search/agent",
                    json={"query": cases[0][1], "planning_mode": "llm", "top_k": 10},
                )
                r.raise_for_status()
                value = r.json()
                report["real_llm"] = value
                assert value["status"] == "completed" and value["plan_validated"]
                assert value["planner_trace"][-1]["status"] == "completed"
                assert {i["image_id"] for i in value["results"]} == expected_ids
            if rag:
                r = client.post(
                    "/api/v1/search/agent",
                    json={"query": cases[0][1], "include_explanation": True, "top_k": 10},
                )
                r.raise_for_status()
                value = r.json()
                report["real_rag"] = value
                assert value["results"] and value["rag"] and value["rag"]["generated"]
                assert all(c["image_id"] in expected_ids for c in value["rag"]["citations"])
                assert value["rag"]["context"]["format"] == "compact"
            report["status"] = "pass"
    except Exception as error:
        report.update(status="failed", error_type=type(error).__name__)
        raise
    finally:
        (target / "expected_labels.json").write_text(
            json.dumps(truth, ensure_ascii=False, indent=2) + "\n"
        )
        (target / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return {
        "status": report["status"],
        "real_workflow_cases": len(rows),
        "human_quality_verified": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--rag", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.output, args.llm, args.rag)))


if __name__ == "__main__":
    main()
