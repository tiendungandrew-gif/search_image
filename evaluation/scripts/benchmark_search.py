#!/usr/bin/env python3
"""HTTP benchmark, join full ASGI samples qua request ID, không ghi tokens hoặc query text."""

import argparse
import asyncio
import json
import os
import platform
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import httpx
from app.evaluation.metrics import latency_summary

QUERIES = [
    "a cup of coffee",
    "a brown cat",
    "stars and galaxies in deep space",
    "a rocket launching into the sky",
]


async def benchmark(args):
    token = os.environ["API_TOKEN"]
    headers = {"Authorization": "Bearer " + token}
    image = (
        await asyncio.to_thread(Path(args.image).read_bytes)
        if args.mode in {"image", "multimodal"}
        else None
    )
    advanced_queries = [
        ("en", "AND", "a cup of coffee and a brown cat"),
        ("en", "OR", "a cup of coffee or a brown cat"),
        ("vi", "AND", "cà phê và mèo màu nâu"),
        ("vi", "OR", "cà phê hoặc mèo màu nâu"),
    ]
    samples = []
    sequence = iter(range(args.requests))
    first_response = None
    async with httpx.AsyncClient(base_url=args.base_url, timeout=10) as client:
        health = await client.get("/api/v1/health?check=search", headers=headers)
        health.raise_for_status()

        async def request(number, warm=False):
            nonlocal first_response
            identifier = str(uuid4())
            sent = perf_counter()
            try:
                language, logical, query = (
                    advanced_queries[number % len(advanced_queries)]
                    if args.mode in {"multi_intent", "multimodal"}
                    else ("en", None, QUERIES[number % len(QUERIES)])
                )
                options = {"mode": args.mode, "top_k": 10, "exclude_self": False}
                if args.mode != "image":
                    options["text"] = query
                if args.mode in {"multi_intent", "multimodal"}:
                    options.update(
                        {
                            "fusion": {
                                "method": args.fusion,
                                "text_weight": 0.5,
                                "image_weight": 0.5,
                            },
                            "rerank": {"enabled": args.rerank, "on_failure": "error"},
                            "retrieval_strategy": args.retrieval_strategy,
                        }
                    )
                if image is not None:
                    response = await client.post(
                        "/api/v1/search/multimodal",
                        headers=headers | {"X-Request-ID": identifier},
                        files={"image": ("reference.png", image, "image/png")},
                        data={"options": json.dumps(options)},
                    )
                else:
                    response = await client.post(
                        "/api/v1/search",
                        headers=headers | {"X-Request-ID": identifier},
                        json=options,
                    )
                elapsed = (perf_counter() - sent) * 1000
                row = {
                    "request_id": identifier,
                    "status": response.status_code,
                    "client_ms": elapsed,
                    "success": response.status_code == 200,
                    "modality": args.mode,
                    "language": language,
                    "logical_operator": logical,
                }
                if response.status_code == 200:
                    value = response.json()
                    row["processing_ms"] = value["latency"]["processing_ms"]
                    row["result_count"] = len(value["results"])
                    row["result_ids"] = [v["image_id"] for v in value["results"]]
                    row["route"] = value.get("effective_settings", {}).get("route")
                    row["channels"] = value["effective_settings"]["channels"]
                    row["rerank_applied"] = value["effective_settings"].get("rerank_applied", False)
                    row["fusion_version"] = value["effective_settings"]["fusion_version"]
                    if first_response is None:
                        first_response = {
                            k: value[k] for k in ["model_id", "index_id", "manifest_sha256"]
                        }
                else:
                    row["error_code"] = response.json().get("error", {}).get("code", "HTTP_ERROR")
            except Exception as exc:
                row = {
                    "request_id": identifier,
                    "success": False,
                    "client_ms": (perf_counter() - sent) * 1000,
                    "error_code": type(exc).__name__,
                    "modality": args.mode,
                }
            if not warm:
                samples.append(row)

        for i in range(args.warmup):
            await request(i, True)
        started = perf_counter()

        async def worker():
            for i in sequence:
                await request(i)

        await asyncio.gather(*(worker() for _ in range(args.concurrency)))
        seconds = perf_counter() - started
        response = await client.get("/api/v1/system/search-metrics?limit=10000", headers=headers)
        response.raise_for_status()
        server = {sample["request_id"]: sample for sample in response.json()["samples"]}
    for sample in samples:
        span = server.get(sample["request_id"])
        if span:
            sample["server_response_ms"] = span["server_response_ms"]
            sample["serialization_send_ms"] = span["serialization_send_ms"]
            sample["stages"] = span.get("stages", {})
    successful = [s for s in samples if s["success"]]
    server_values = [s["server_response_ms"] for s in successful if "server_response_ms" in s]
    report = {
        "status": "measured",
        "modality": args.mode,
        "experiment": {
            "fusion": args.fusion,
            "rerank": args.rerank,
            "retrieval_strategy": args.retrieval_strategy,
        },
        "requests": args.requests,
        "concurrency": args.concurrency,
        "warmup": args.warmup,
        "cache_state": f"model preloaded; pools warmup={args.warmup}; no query-result cache",
        "environment": {
            "client_platform": platform.platform(),
            "client_python": platform.python_version(),
            "server_environment_artifact": "docs/verification/phase04/environment.json",
        },
        "model": first_response,
        "duration_seconds": seconds,
        "successful": len(successful),
        "failed": len(samples) - len(successful),
        "error_rate": (len(samples) - len(successful)) / len(samples),
        "requests_per_second": len(samples) / seconds,
        "successful_per_second": len(successful) / seconds,
        "client_success_latency": latency_summary([s["client_ms"] for s in successful]),
        "server_success_latency": latency_summary(server_values),
        "server_sample_count": len(server_values),
        "percentile_method": (
            "nearest rank ceil(p*n); successful samples; errors retained separately"
        ),
        "p90_300ms_observed": bool(
            server_values
            and latency_summary(server_values)["p90_ms"] <= 300
            and len(server_values) == args.requests
        ),
        "p95_500ms_observed": bool(
            server_values
            and latency_summary(server_values)["p95_ms"] <= 500
            and len(server_values) == args.requests
        ),
        "samples": samples,
        "subgroups": {
            f"{language}_{logical}": latency_summary(
                [
                    s["server_response_ms"]
                    for s in successful
                    if s.get("language") == language
                    and s.get("logical_operator") == logical
                    and "server_response_ms" in s
                ]
            )
            for language in ["en", "vi"]
            for logical in ["AND", "OR"]
        }
        if args.mode in {"multi_intent", "multimodal"}
        else {},
    }
    if args.index_report:
        index = json.loads(await asyncio.to_thread(Path(args.index_report).read_text))
        if first_response and index["index_id"] != first_response["index_id"]:
            raise ValueError("Index report mismatch")
        report["dataset"] = {
            k: index[k] for k in ["verified_images", "exact_vector_count", "index_id", "collection"]
        }
    target = Path(args.output)
    await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread(target.write_text, json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {k: v for k, v in report.items() if k not in ["samples", "environment"]}, indent=2
        )
    )
    return 0 if len(successful) == args.requests and len(server_values) == args.requests else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--mode", choices=["text", "image", "multi_intent", "multimodal"], required=True
    )
    parser.add_argument("--fusion", choices=["rrf", "weighted_score"], default="rrf")
    parser.add_argument("--rerank", action="store_true")
    parser.add_argument(
        "--retrieval-strategy", choices=["whole_query", "multi_query", "fused"], default="fused"
    )
    parser.add_argument("--image", default="datasets/sample/coffee.png")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--output", required=True)
    parser.add_argument("--index-report", default="docs/verification/phase04/index.json")
    args = parser.parse_args()
    if (
        not 1 <= args.requests <= 10000
        or not 1 <= args.concurrency <= 64
        or not 0 <= args.warmup <= 100
    ):
        parser.error("Invalid request/concurrency/warmup bounds")
    return asyncio.run(benchmark(args))


if __name__ == "__main__":
    raise SystemExit(main())
