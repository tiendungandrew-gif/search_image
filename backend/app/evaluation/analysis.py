"""Phân tích ABBA từ raw samples; pooled percentiles, rank parity, uncertainty."""

import json
import statistics
from collections import defaultdict
from pathlib import Path

from app.evaluation.statistics import describe, latency_bootstrap, paired_bootstrap
from app.evaluation.tracking import Experiment


def analyze_optimization(results, suite=None):
    selected = (
        {row["experiment_id"] for row in json.loads(Path(suite).read_text())["experiments"]}
        if suite
        else None
    )
    runs = []
    for path in Path(results).glob("*/result.json"):
        if selected is not None and path.parent.name not in selected:
            continue
        value = json.loads(path.read_text())
        if value.get("config", {}).get("name", "").startswith("opt_head"):
            runs.append((path.parent.name, value))
    if len(runs) != 4:
        raise ValueError("exactly_one_four_run_ABBA_suite_required")
    by_width = defaultdict(list)
    ranks = defaultdict(set)
    timings = {1: defaultdict(list), 2: defaultdict(list)}
    groups = {}
    for _identifier, run in sorted(runs):
        widths = {
            s["effective_settings"]["object_check_concurrency"]
            for s in run["samples"]
            if s["success"]
        }
        if run["failed"] or len(widths) != 1:
            raise ValueError("complete_unambiguous_ABBA_runs_required")
        width = widths.pop()
        by_width[width].extend(run["samples"])
        for sample in run["samples"]:
            key = sample["query_id"]
            ranks[key].add(tuple(sample["result_ids"]))
            timings[width][key].append(sample["server_response_ms"])
            groups[key] = sample["group_id"]
    if set(by_width) != {1, 2} or set(timings[1]) != set(timings[2]):
        raise ValueError("paired_query_sets_required")
    pooled = {}
    for width, samples in by_width.items():
        times = [s["server_response_ms"] for s in samples]
        pooled[str(width)] = {
            "server_latency": describe(times),
            "p90_uncertainty": latency_bootstrap(times),
            "object_window_mean_ms": statistics.fmean(
                s["stages"]["object_head_windows_ms"] for s in samples
            ),
        }
    comparisons = [
        {
            "query_id": key,
            "group_id": groups[key],
            "head1_mean_ms": statistics.fmean(timings[1][key]),
            "head2_mean_ms": statistics.fmean(timings[2][key]),
            "all_ranks_identical": len(ranks[key]) == 1,
        }
        for key in sorted(ranks)
    ]
    experiment = Experiment(
        results, "optimization-analysis", {}, {"input_runs": [r[0] for r in runs]}
    )
    result = {
        "status": "measured",
        "input_runs": [r[0] for r in sorted(runs)],
        "pooled": pooled,
        "query_comparisons": comparisons,
        "all_ranks_identical": all(r["all_ranks_identical"] for r in comparisons),
        "latency_mean_delta_cluster_bootstrap": paired_bootstrap(
            {r["query_id"]: r["head1_mean_ms"] for r in comparisons},
            {r["query_id"]: r["head2_mean_ms"] for r in comparisons},
            groups,
        ),
        "semantic_quality": "unavailable_no_human_labels; rank parity only",
        "decision": (
            "retain_head1_default; no demonstrated end-to-end improvement"
            if pooled["2"]["server_latency"]["mean_ms"] >= pooled["1"]["server_latency"]["mean_ms"]
            or pooled["2"]["server_latency"]["p90_ms"] >= pooled["1"]["server_latency"]["p90_ms"]
            else "head2_has_lower_descriptive_latency; review before changing defaults"
        ),
    }
    experiment.complete(result)
    return {"experiment_id": experiment.identifier, "status": result["status"]}
