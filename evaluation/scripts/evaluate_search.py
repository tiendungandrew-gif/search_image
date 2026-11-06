#!/usr/bin/env python3
"""Chỉ đánh giá labels do người dùng xác nhận; không tự bịa relevance."""

import argparse
import json
import os
from pathlib import Path

import httpx
from app.evaluation.metrics import retrieval_metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    labels = json.loads(Path(args.labels).read_text())
    if (
        labels.get("human_verified") is not True
        or labels.get("exhaustive_judgments") is not True
        or not labels.get("queries")
    ):
        parser.error("Chưa có human-verified qrels; không đo retrieval quality")
    universe = set(labels["corpus_image_ids"])
    rows = []
    details = {}
    with httpx.Client(
        base_url=args.base_url,
        headers={"Authorization": "Bearer " + os.environ["API_TOKEN"]},
        timeout=10,
    ) as client:
        for identity in universe:
            detail = client.get("/api/v1/images/" + identity)
            detail.raise_for_status()
            details[identity] = detail.json()
            if detail.json()["status"] != "available":
                raise ValueError("Corpus image unavailable")
        for query in labels["queries"]:
            grades = query.get("grades") or {
                key: int(key in query["relevant_image_ids"]) for key in universe
            }
            if set(grades) != universe:
                raise ValueError("Need exhaustive corpus judgments")
            if not set(grades).issubset(universe) or any(
                type(g) is not int or not 0 <= g <= 3 for g in grades.values()
            ):
                raise ValueError("Invalid judgments/universe")
            response = client.post("/api/v1/search", json={"text": query["query"], "top_k": 10})
            response.raise_for_status()
            active = response.json()["index_id"]
            if any(
                not any(
                    row["index_id"] == active and row["status"] == "ready"
                    for row in detail["indexing"]
                )
                for detail in details.values()
            ):
                raise ValueError("Unindexed corpus entry")
            ids = [r["image_id"] for r in response.json()["results"]]
            if not set(ids).issubset(universe):
                raise ValueError("Corpus manifest mismatch")
            rows.append(
                {
                    "query_id": query["query_id"],
                    "metrics": retrieval_metrics(ids, grades),
                    "result_ids": ids,
                }
            )
    means = {
        key: sum(row["metrics"][key] for row in rows if row["metrics"][key] is not None)
        / sum(row["metrics"][key] is not None for row in rows)
        if any(row["metrics"][key] is not None for row in rows)
        else None
        for key in rows[0]["metrics"]
    }
    output = {
        "status": "measured",
        "human_verified": True,
        "queries": rows,
        "macro_metrics": means,
        "excluded_no_answer_queries": sum(row["metrics"]["recall@10"] is None for row in rows),
    }
    Path(args.output).write_text(json.dumps(output, indent=2) + "\n")


if __name__ == "__main__":
    main()
