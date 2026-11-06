#!/usr/bin/env python3
"""E1–E5 với exhaustive human judgments; không tạo relevance từ model."""

import argparse
import json
import os
from pathlib import Path

import httpx
from app.evaluation.advanced_metrics import constraint_metrics
from app.evaluation.metrics import retrieval_metrics


def validate_labels(labels):
    if (
        labels.get("human_verified") is not True
        or labels.get("exhaustive_judgments") is not True
        or not labels.get("queries")
    ):
        raise ValueError("Chưa có exhaustive human-verified advanced qrels")
    universe = set(labels["corpus_image_ids"])
    if not universe:
        raise ValueError("Empty corpus")
    for query in labels["queries"]:
        if set(query["grades"]) != universe or set(query["constraint_judgments"]) != universe:
            raise ValueError("Need exhaustive corpus judgments")
        if any(type(grade) is not int or not 0 <= grade <= 3 for grade in query["grades"].values()):
            raise ValueError("Invalid relevance grades")
        if any(
            value is not None and type(value) is not bool
            for clauses in query["constraint_judgments"].values()
            for value in clauses.values()
        ):
            raise ValueError("Invalid human per-constraint label")
        if not set(query["overall_satisfied_image_ids"]).issubset(universe):
            raise ValueError("Unknown image in overall satisfaction labels")
    return universe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--experiments", default="evaluation/experiments/phase06.json")
    args = parser.parse_args()
    labels = json.loads(Path(args.labels).read_text())
    try:
        universe = validate_labels(labels)
    except ValueError as exc:
        parser.error(str(exc))
    experiments = json.loads(Path(args.experiments).read_text())
    results = []
    with httpx.Client(
        base_url=args.base_url,
        headers={"Authorization": "Bearer " + os.environ["API_TOKEN"]},
        timeout=10,
    ) as client:
        details = {}
        for identity in universe:
            response = client.get("/api/v1/images/" + identity)
            response.raise_for_status()
            details[identity] = response.json()
            if details[identity]["status"] != "available":
                raise ValueError("Unavailable corpus image")
        for query in labels["queries"]:
            for name, config in experiments.items():
                request = {**query["request"], **config, "top_k": 10}
                if config["mode"] != "multimodal":
                    request.pop("image_id", None)
                elif not request.get("image_id"):
                    continue
                if "fusion_strategy" in config:
                    request.pop("fusion", None)
                if name == "E1":
                    for key in ["constraints", "require_verified"]:
                        request.pop(key, None)
                endpoint = (
                    "/api/v1/search/multimodal"
                    if config["mode"] == "multimodal"
                    else "/api/v1/search"
                )
                response = client.post(endpoint, json=request)
                response.raise_for_status()
                value = response.json()
                if any(
                    not any(
                        item["index_id"] == value["index_id"] and item["status"] == "ready"
                        for item in detail["indexing"]
                    )
                    for detail in details.values()
                ):
                    raise ValueError("Corpus entry not indexed in active space")
                ids = [row["image_id"] for row in value["results"]]
                if not set(ids).issubset(universe):
                    raise ValueError("Corpus manifest mismatch")
                evidence = {
                    row["image_id"]: {
                        a["clause_id"]: a["status"] for a in row["constraint_assessments"]
                    }
                    for row in value["results"]
                }
                results.append(
                    {
                        "query_id": query["query_id"],
                        "language": query["language"],
                        "groups": query["groups"],
                        "experiment": name,
                        "index_id": value["index_id"],
                        "result_ids": ids,
                        "metrics": {
                            **retrieval_metrics(ids, query["grades"]),
                            **constraint_metrics(
                                ids,
                                evidence,
                                query["constraint_judgments"],
                                query["overall_satisfied_image_ids"],
                            ),
                        },
                    }
                )

    def aggregate(rows):
        if not rows:
            return {}
        output = {}
        for key in rows[0]["metrics"]:
            values = [row["metrics"][key] for row in rows if row["metrics"][key] is not None]
            output[key] = sum(values) / len(values) if values else None
        return output

    aggregates = {
        experiment: aggregate([row for row in results if row["experiment"] == experiment])
        for experiment in experiments
    }
    languages = {
        language: {
            experiment: aggregate(
                [
                    row
                    for row in results
                    if row["experiment"] == experiment and row["language"] == language
                ]
            )
            for experiment in experiments
        }
        for language in ["en", "vi"]
    }
    Path(args.output).write_text(
        json.dumps(
            {
                "status": "measured",
                "human_verified": True,
                "results": results,
                "macro_by_experiment": aggregates,
                "macro_by_language": languages,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
