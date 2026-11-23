"""Agent measurements reuse Experiment/statistics; fixture scores are never real-world accuracy."""

import csv
import re
from time import perf_counter, sleep

import httpx

from app.evaluation.rag import audit_citations
from app.evaluation.statistics import describe
from app.evaluation.tracking import Experiment


def evaluate_labeled_cases(rows, labels):
    fixture = labels.get("fixture") is True
    source_verified = (
        labels.get("source_verified") is True
        and re.fullmatch(r"[a-f0-9]{64}", str(labels.get("source_manifest_sha256", ""))) is not None
        and isinstance(labels.get("source_urls"), list)
        and bool(labels["source_urls"])
        and all(
            isinstance(url, str) and url.startswith("https://") for url in labels["source_urls"]
        )
    )
    human_verified = labels.get("human_verified") is True and bool(labels.get("annotator"))
    if not fixture and not source_verified and not human_verified:
        raise ValueError("VERIFIED_AGENT_LABELS_REQUIRED")
    expected = labels.get("cases", {})
    if set(expected) != {r["case_id"] for r in rows}:
        raise ValueError("LABEL_COVERAGE_MISMATCH")
    scores = {
        k: []
        for k in [
            "routing_accuracy",
            "tool_selection_accuracy",
            "entity_resolution_accuracy",
            "relationship_resolution_accuracy",
            "expected_image_identity_match",
            "workflow_success",
        ]
    }
    for row in rows:
        actual = row["result"]
        truth = expected[row["case_id"]]
        scores["routing_accuracy"].append(actual["search_mode"] == truth["search_mode"])
        scores["tool_selection_accuracy"].append(
            [s["tool"] for s in actual["steps"]] == truth["tools"]
        )
        scores["entity_resolution_accuracy"].append(
            {e["entity_id"] for e in actual["resolved_entities"]} == set(truth["entity_ids"])
        )
        scores["relationship_resolution_accuracy"].append(
            {e["evidence_id"] for e in actual["evidence"]} == set(truth["relationship_ids"])
        )
        scores["expected_image_identity_match"].append(
            {i["image_id"] for i in actual["results"]} == set(truth["image_ids"])
        )
        scores["workflow_success"].append(actual["status"] == truth["status"])
    return {
        "classification": "synthetic_fixture"
        if fixture
        else "human_verified_real_cases"
        if human_verified
        else "source_verified_workflow",
        "cases": len(rows),
        "metrics": {k: sum(v) / len(v) if v else None for k, v in scores.items()},
        "real_world_retrieval_accuracy": None
        if not human_verified
        else "requires separate relevance judgments",
    }


def summarize_agent_cases(cases, mode):
    planner_traces = [t for r in cases for t in r.get("result", {}).get("planner_trace", [])]
    generated = [
        r for r in cases if r.get("result", {}).get("rag", {}) and r["result"]["rag"]["generated"]
    ]
    tool_calls = sum(r.get("result", {}).get("tool_calls", 0) for r in cases)
    failed_tools = sum(
        s["status"] in {"failed", "timeout"}
        for r in cases
        for s in r.get("result", {}).get("steps", [])
    )
    timeouts = sum(
        r["status"] == "timeout"
        or r.get("transport_timeout", False)
        or r.get("result", {}).get("error_code") == "AGENT_DEADLINE_EXCEEDED"
        or any(s["status"] == "timeout" for s in r.get("result", {}).get("steps", []))
        or any(s["status"] == "timeout" for s in r.get("result", {}).get("planner_trace", []))
        for r in cases
    )
    return {
        "attempted": len(cases),
        "http_failures": sum(r["status"] == "http_failed" for r in cases),
        "failed_executions": sum(r["status"] == "failed" for r in cases),
        "partial_executions": sum(r["status"] == "partial" for r in cases),
        "validated_plans": sum(r.get("result", {}).get("plan_validated", False) for r in cases),
        "structural_query_success": sum(
            r.get("result", {}).get("query_success", False) for r in cases
        )
        if mode != "A1"
        else None,
        "insufficient_evidence": sum(r["status"] == "insufficient_evidence" for r in cases),
        "timeouts": timeouts,
        "timeout_rate": timeouts / len(cases),
        "planner_attempt_count": len(planner_traces),
        "planner_failed_attempts": sum(
            t["status"] in {"failed", "timeout"} for t in planner_traces
        ),
        "planner_timeout_attempts": sum(t["status"] == "timeout" for t in planner_traces),
        "planning_attempt_latency": describe([t["duration_ms"] for t in planner_traces]),
        "generated": len(generated),
        "explanations_with_citations": sum(
            bool(r["result"]["rag"].get("citations")) for r in generated
        ),
        "client_latency": describe([r["client_ms"] for r in cases]),
        "planning_latency": describe(
            [r["result"]["latency"]["planning_ms"] for r in cases if mode != "A1" and "result" in r]
        ),
        "tools_latency": describe(
            [r["result"]["latency"]["tools_ms"] for r in cases if mode != "A1" and "result" in r]
        ),
        "mean_hops": sum(r.get("result", {}).get("logical_hops", 0) for r in cases) / len(cases),
        "mean_tool_calls": tool_calls / len(cases),
        "tool_failure_rate": failed_tools / tool_calls if tool_calls else None,
        "provider_ttft": describe(
            [
                r["result"]["latency"]["provider_ttft_ms"]
                for r in generated
                if r["result"]["latency"]["provider_ttft_ms"] is not None
            ]
        ),
        "request_ttlast": describe(
            [
                r["result"]["latency"]["request_ttlast_ms"]
                for r in generated
                if r["result"]["latency"]["request_ttlast_ms"] is not None
            ]
        ),
        "generation_target_3s": {
            "observed_generated": len(generated),
            "within_target": sum(
                r["result"]["latency"].get("request_ttlast_ms") is not None
                and r["result"]["latency"]["request_ttlast_ms"] <= 3000
                for r in generated
            ),
            "exceeded_target": sum(
                r["result"]["latency"].get("request_ttlast_ms") is not None
                and r["result"]["latency"]["request_ttlast_ms"] > 3000
                for r in generated
            ),
            "missing_timing": sum(
                r["result"]["latency"].get("request_ttlast_ms") is None for r in generated
            ),
        },
        "real_world_quality": None,
    }


def run_agent_experiments(
    base_url,
    token,
    results,
    requests=16,
    include_llm=False,
    image_query="a dog outdoors",
    relational_query="Find landmarks in the city where Hoan Kiem Lake is located",
    min_interval_seconds=0,
):
    if not 0 <= min_interval_seconds <= 30:
        raise ValueError("INVALID_AGENT_BENCHMARK_INTERVAL")
    modes = ["A1", "A2", "A3", "A4"] if include_llm else ["A1", "A2", "A4"]
    experiment = Experiment(
        results,
        "agent",
        {
            "requests": requests,
            "modes": modes,
            "concurrency": 1,
            "seed": 42,
            "image_query": image_query,
            "relational_query": relational_query,
            "min_interval_seconds": min_interval_seconds,
        },
    )
    rows = []
    with httpx.Client(
        base_url=base_url, headers={"Authorization": "Bearer " + token}, timeout=45
    ) as client:
        status = client.get("/api/v1/search/agent/status")
        status.raise_for_status()
        runtime = client.get("/api/v1/system/search-runtime")
        runtime.raise_for_status()
        last_started = None
        benchmark_started = perf_counter()
        for number in range(requests):
            if last_started is not None:
                sleep(max(0, min_interval_seconds - (perf_counter() - last_started)))
            mode = modes[number % len(modes)]
            body = {"query": image_query, "top_k": 3}
            if mode in {"A2", "A3"}:
                body["query"] = relational_query
                body["planning_mode"] = "llm" if mode == "A3" else "deterministic"
            if mode == "A4":
                body["include_explanation"] = True
            started = perf_counter()
            last_started = started
            row = {"case_id": f"{mode}_{number:03d}", "configuration": mode, "request": body}
            try:
                response = client.post(
                    "/api/v1/search" if mode == "A1" else "/api/v1/search/agent",
                    json={"text": body["query"], "mode": "text", "top_k": 3}
                    if mode == "A1"
                    else body,
                )
                row["http_status"] = response.status_code
                response.raise_for_status()
                value = response.json()
                row.update(
                    status="direct_search" if mode == "A1" else value["status"], result=value
                )
                if value.get("rag"):
                    row["citation_audit"] = audit_citations(value)
            except httpx.HTTPError as error:
                row.update(
                    status="http_failed",
                    error_type=type(error).__name__,
                    transport_timeout=isinstance(error, httpx.TimeoutException),
                )
            row["client_ms"] = (perf_counter() - started) * 1000
            rows.append(row)
    groups = {}
    for mode in modes:
        cases = [r for r in rows if r["configuration"] == mode]
        groups[mode] = summarize_agent_cases(cases, mode)
    value = {
        "status": "measured",
        "attempted": len(rows),
        "duration_seconds_including_pacing": perf_counter() - benchmark_started,
        "successful": sum(r["status"] != "http_failed" for r in rows),
        "failed": sum(r["status"] == "http_failed" for r in rows),
        "cases": rows,
        "agent_groups": groups,
        "runtime": runtime.json(),
        "agent_configuration": status.json(),
        "real_world_ground_truth": "not_available",
        "notes": [
            "A2/A3 outcomes depend on available verified knowledge; "
            "execution is not relevance accuracy.",
            "A1/A4 share an image query; A2/A3 are a different relational task.",
            "Small-N timings are exploratory; provider/network load is uncontrolled.",
        ],
    }
    experiment.complete(value)
    return {
        "experiment_id": experiment.identifier,
        "directory": str(experiment.directory),
        "groups": groups,
    }


def report_agent_runs(runs, target):
    groups = []
    cases = []
    for run in runs:
        for name, group in run["result"].get("agent_groups", {}).items():
            groups.append(
                {
                    "experiment_id": run["experiment"]["experiment_id"],
                    "configuration": name,
                    **group,
                }
            )
        if "agent_groups" in run["result"]:
            cases.extend(
                {"experiment_id": run["experiment"]["experiment_id"], **row}
                for row in run["result"]["cases"]
            )
    if not groups:
        return []
    fields = [
        "experiment_id",
        "configuration",
        "attempted",
        "http_failures",
        "failed_executions",
        "partial_executions",
        "validated_plans",
        "insufficient_evidence",
        "timeouts",
        "timeout_rate",
        "planner_attempt_count",
        "planner_failed_attempts",
        "planner_timeout_attempts",
        "generated",
        "explanations_with_citations",
        "mean_hops",
        "mean_tool_calls",
        "tool_failure_rate",
        "client_p90_ms",
        "client_p95_ms",
        "planning_p90_ms",
        "ttlast_p90_ms",
    ]
    with (target / "agent_summary.csv").open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in groups:
            writer.writerow(
                {
                    **{k: row.get(k) for k in fields},
                    "client_p90_ms": row["client_latency"]["p90_ms"],
                    "client_p95_ms": row["client_latency"]["p95_ms"],
                    "planning_p90_ms": row["planning_latency"]["p90_ms"],
                    "ttlast_p90_ms": row["request_ttlast"]["p90_ms"],
                }
            )
    with (target / "agent_cases.csv").open("x", newline="") as handle:
        fields = [
            "experiment_id",
            "case_id",
            "configuration",
            "status",
            "http_status",
            "client_ms",
            "logical_hops",
            "tool_calls",
            "planner_attempts",
            "error_code",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in cases:
            writer.writerow({k: row.get(k, row.get("result", {}).get(k)) for k in fields})
    import matplotlib.pyplot as plt

    figure, axis = plt.subplots(figsize=(9, 5))
    axis.bar(
        [g["configuration"] + "\n" + g["experiment_id"][-6:] for g in groups],
        [g["client_latency"]["p90_ms"] for g in groups],
    )
    axis.set_ylabel("Client P90 ms, mọi lượt thử")
    axis.set_title("Thời gian Agent thăm dò; các nhóm có task khác nhau")
    figure.tight_layout()
    for extension in ["png", "svg"]:
        figure.savefig(target / ("agent_latency." + extension), dpi=160)
    plt.close(figure)
    lines = [
        "",
        "## Agent: thời gian thực thi và abstention, chưa có real-world quality labels",
        "",
        "| Nhóm / experiment | N / HTTP errors / insufficient | Client P90 ms | "
        "Plan P90 ms | Mean hops / calls |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in groups:
        plan = row["planning_latency"]["p90_ms"]
        lines.append(
            f"| {row['configuration']} / {row['experiment_id']} | "
            f"{row['attempted']} / {row['http_failures']} / "
            f"{row['insufficient_evidence']} | {row['client_latency']['p90_ms']:.2f} | "
            f"{plan if plan is not None else '—'} | "
            f"{row['mean_hops']:.2f} / {row['mean_tool_calls']:.2f} |"
        )
    lines.extend(
        [
            "",
            "A2/A3 dùng quan hệ thật nếu có trong kho; "
            "execution success không là relevance accuracy. "
            "A1/A4 dùng cùng image query, khác task với A2/A3. "
            "Xem agent_cases.csv và raw JSON để giữ mọi failure. "
            "Không có human quality bars khi thiếu nhãn.",
        ]
    )
    return lines
