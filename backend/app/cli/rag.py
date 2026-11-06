"""CLI nghiệm thu/benchmark RAG, không truyền key LLM qua arguments."""

import argparse
import json
import os
from pathlib import Path

from app.evaluation.rag import run_experiments, validate_review
from app.evaluation.tracking import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--results", default="evaluation/results/phase08")
    parser.add_argument("--requests", type=int, default=20, choices=range(4, 101))
    parser.add_argument("--review")
    parser.add_argument("--experiment")
    args = parser.parse_args()
    if args.review:
        if not args.experiment:
            parser.error("--review requires --experiment result.json")
        result = json.loads(Path(args.experiment).read_text())
        labels = json.loads(Path(args.review).read_text())
        if labels.get("result_sha256") != digest(result):
            parser.error("Review không khớp frozen experiment output")
        print(json.dumps(validate_review(labels, result["cases"])))
        return
    print(
        json.dumps(
            run_experiments(
                args.base_url, os.environ.get("API_TOKEN", ""), args.results, args.requests
            )
        )
    )


if __name__ == "__main__":
    main()
