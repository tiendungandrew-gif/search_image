"""Benchmark Agent dùng framework hiện có; không truyền LLM key qua arguments."""

import argparse
import json
import os

from app.evaluation.agent import run_agent_experiments


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--results", default="evaluation/results/phase09")
    parser.add_argument("--requests", type=int, default=16, choices=range(4, 101))
    parser.add_argument("--include-llm", action="store_true")
    parser.add_argument("--min-interval-seconds", type=float, default=0)
    parser.add_argument("--image-query", default="a dog outdoors")
    parser.add_argument(
        "--relational-query", default="Find landmarks in the city where Hoan Kiem Lake is located"
    )
    args = parser.parse_args()
    print(
        json.dumps(
            run_agent_experiments(
                args.base_url,
                os.environ.get("API_TOKEN", ""),
                args.results,
                args.requests,
                args.include_llm,
                args.image_query,
                args.relational_query,
                args.min_interval_seconds,
            )
        )
    )


if __name__ == "__main__":
    main()
