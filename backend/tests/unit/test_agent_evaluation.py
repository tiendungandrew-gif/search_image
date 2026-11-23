import pytest

from app.evaluation.agent import evaluate_labeled_cases, summarize_agent_cases


def test_fixture_metric_denominators_and_scope_do_not_become_real_accuracy():
    rows = [
        {
            "case_id": "unit",
            "result": {
                "search_mode": "agent",
                "steps": [{"tool": "entity_lookup"}],
                "resolved_entities": [],
                "evidence": [],
                "results": [],
                "status": "insufficient_evidence",
            },
        }
    ]
    labels = {
        "fixture": True,
        "cases": {
            "unit": {
                "search_mode": "agent",
                "tools": ["entity_lookup"],
                "entity_ids": [],
                "relationship_ids": [],
                "image_ids": [],
                "status": "insufficient_evidence",
            }
        },
    }
    scored = evaluate_labeled_cases(rows, labels)
    assert scored["classification"] == "synthetic_fixture"
    assert scored["metrics"]["workflow_success"] == 1
    assert scored["real_world_retrieval_accuracy"] is None
    labels["fixture"] = False
    with pytest.raises(ValueError, match="VERIFIED_AGENT_LABELS_REQUIRED"):
        evaluate_labeled_cases(rows, labels)


def test_fixture_coverage_is_required_and_zero_denominator_stays_unknown():
    result = evaluate_labeled_cases([], {"fixture": True, "cases": {}})
    assert all(v is None for v in result["metrics"].values())
    with pytest.raises(ValueError, match="COVERAGE"):
        evaluate_labeled_cases([], {"fixture": True, "cases": {"missing": {}}})


def test_source_attestation_does_not_become_human_relevance_labels():
    labels = {
        "source_verified": True,
        "source_manifest_sha256": "a" * 64,
        "source_urls": ["https://www.nps.gov/wamo/index.htm"],
        "cases": {},
    }
    result = evaluate_labeled_cases([], labels)
    assert result["classification"] == "source_verified_workflow"
    assert result["real_world_retrieval_accuracy"] is None
    labels["source_manifest_sha256"] = "not-a-source-digest"
    with pytest.raises(ValueError, match="VERIFIED_AGENT_LABELS_REQUIRED"):
        evaluate_labeled_cases([], labels)


def test_recovered_planner_and_transport_timeouts_remain_in_metrics():
    def row(duration, last):
        return {
            "status": "completed",
            "client_ms": duration,
            "result": {
                "rag": {"generated": True},
                "tool_calls": 2,
                "steps": [],
                "latency": {
                    "planning_ms": 2,
                    "tools_ms": duration - 2,
                    "provider_ttft_ms": 100,
                    "request_ttlast_ms": last,
                },
            },
        }

    rows = [
        row(2000, 1800),
        row(4500, 4300),
        {
            "status": "http_failed",
            "client_ms": 5000,
            "transport_timeout": True,
        },
    ]
    rows[0]["result"]["planner_trace"] = [
        {"status": "timeout", "duration_ms": 1},
        {"status": "completed", "duration_ms": 1},
    ]
    value = summarize_agent_cases(rows, "A4")
    assert value["http_failures"] == 1 and value["timeouts"] == 2
    assert value["planner_timeout_attempts"] == 1 and value["planner_failed_attempts"] == 1
    assert value["client_latency"]["count"] == 3
    assert value["generation_target_3s"] == {
        "observed_generated": 2,
        "within_target": 1,
        "exceeded_target": 1,
        "missing_timing": 0,
    }
