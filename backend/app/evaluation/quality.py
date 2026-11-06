import hashlib
import json
from collections import defaultdict
from pathlib import Path

import httpx

from app.evaluation.advanced_metrics import constraint_metrics
from app.evaluation.benchmark import request_options
from app.evaluation.dataset import query_digest, validate_labels
from app.evaluation.metrics import retrieval_metrics
from app.evaluation.statistics import paired_bootstrap
from app.evaluation.tracking import digest


def aggregate(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["task"], row["query_type"], row["language"], row["search_mode"])].append(row)
    output = []
    for (task, kind, language, mode), items in grouped.items():
        metrics = {}
        for key in items[0]["metrics"]:
            values = [row["metrics"][key] for row in items if row["metrics"][key] is not None]
            metrics[key] = {
                "mean": sum(values) / len(values) if values else None,
                "evaluated_queries": len(values),
            }
        output.append(
            {
                "task": task,
                "query_type": kind,
                "language": language,
                "search_mode": mode,
                "query_count": len(items),
                "metrics": metrics,
            }
        )
    return output


def evaluate(
    cases, snapshot, labels, base_url, token, configuration=None, split=None, benchmark_config=None
):
    if labels is not None:
        validate_labels(labels, snapshot, cases)
    rows = []
    unavailable = []
    universe = {row["image_id"] for row in snapshot["images"]}
    with httpx.Client(
        base_url=base_url, headers={"Authorization": "Bearer " + token}, timeout=10
    ) as client:
        for case in cases:
            if split and case.split != split:
                continue
            if (
                benchmark_config
                and benchmark_config.query_types
                and case.query_type not in benchmark_config.query_types
            ):
                continue
            if case.task != "exact_identity" and labels is None:
                unavailable.append(case.query_id)
                continue
            request = (
                request_options(case, benchmark_config)
                if benchmark_config
                else {**case.request, **(configuration or {}), "top_k": 10}
            )
            endpoint = (
                "/api/v1/search/multimodal" if case.query_type == "multimodal" else "/api/v1/search"
            )
            if case.query_type in {"image", "multimodal"} and request.get("image_id"):
                source = next(
                    row for row in snapshot["images"] if row["image_id"] == case.request["image_id"]
                )
                raw = Path(source["cache_file"]).read_bytes()
                if hashlib.sha256(raw).hexdigest() != source["sha256"]:
                    raise ValueError("reference_digest_drift")
                uploaded = {key: value for key, value in request.items() if key != "image_id"}
                response = client.post(
                    "/api/v1/search/multimodal",
                    files={"image": ("reference", raw, "application/octet-stream")},
                    data={"options": json.dumps(uploaded)},
                )
            else:
                response = client.post(endpoint, json=request)
            row = {
                "query_id": case.query_id,
                "query_type": case.query_type,
                "language": case.language,
                "task": case.task,
                "group_id": case.group_id,
                "split": case.split,
                "http_status": response.status_code,
            }
            if response.status_code != 200:
                row.update(status="failed", error_code=response.json().get("error", {}).get("code"))
                rows.append(row)
                continue
            value = response.json()
            if any(
                value[key] != snapshot["active"][key]
                for key in ["model_id", "index_id", "manifest_sha256"]
            ):
                raise ValueError("index_snapshot_drift")
            ids = [r["image_id"] for r in value["results"]]
            if not set(ids).issubset(universe):
                raise ValueError("unjudged_corpus_result")
            if case.task == "exact_identity":
                reference = case.request["image_id"]
                grades = {identity: 2 if identity == reference else 0 for identity in universe}
                provenance = (
                    "authoritative exact-byte identity on SHA256-deduplicated corpus; "
                    "fresh uploaded image encoding; not semantic similarity judgments"
                )
                extra = {}
            else:
                judgment = labels["queries"][case.query_id]
                grades = judgment["grades"]
                provenance = "human_verified"
                evidence = {
                    r["image_id"]: {
                        a["clause_id"]: a["status"] for a in r["constraint_assessments"]
                    }
                    for r in value["results"]
                }
                extra = (
                    constraint_metrics(
                        ids,
                        evidence,
                        judgment.get("constraint_judgments", {}),
                        [
                            identity
                            for identity, truth in judgment.get("overall_satisfied", {}).items()
                            if truth is True
                        ],
                        overall_judgments=judgment.get("overall_satisfied", {}),
                    )
                    if case.query_type == "multi_intent"
                    else {}
                )
            row.update(
                status="measured",
                search_mode=value["search_mode"],
                result_ids=ids,
                metrics={
                    **retrieval_metrics(
                        ids,
                        grades,
                        relevant_grade=labels.get("binary_relevance_min_grade", 2)
                        if labels and case.task != "exact_identity"
                        else 2,
                        strict_labels=True,
                    ),
                    **extra,
                },
                label_provenance=provenance,
            )
            rows.append(row)
    successful = [row for row in rows if row["status"] == "measured"]
    return {
        "status": "partial_semantic_labels_unavailable"
        if unavailable
        else "partial_failed_queries"
        if any(row["status"] == "failed" for row in rows)
        else "measured",
        "dataset_sha256": snapshot["sha256"],
        "query_set_sha256": query_digest(cases),
        "label_sha256": digest(labels) if labels else None,
        "queries": rows,
        "unavailable_semantic_query_ids": unavailable,
        "failed_queries": sum(row["status"] == "failed" for row in rows),
        "aggregates": aggregate(successful),
        "semantic_quality_measured": labels is not None,
    }


def compare_quality(before, after, metric="ndcg@10"):
    if any(
        before.get(k) != after.get(k)
        for k in ["dataset_sha256", "query_set_sha256", "label_sha256"]
    ):
        raise ValueError("incompatible_evaluation_manifests")
    first = {
        r["query_id"]: r
        for r in before["queries"]
        if r["status"] == "measured" and r["metrics"].get(metric) is not None
    }
    second = {
        r["query_id"]: r
        for r in after["queries"]
        if r["status"] == "measured" and r["metrics"].get(metric) is not None
    }
    return paired_bootstrap(
        {k: v["metrics"][metric] for k, v in first.items()},
        {k: v["metrics"][metric] for k, v in second.items()},
        {k: v["group_id"] for k, v in first.items()},
    )
