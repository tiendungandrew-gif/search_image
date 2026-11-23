"""CLI nghiên cứu Phase07: snapshots, labels, quality, benchmark, model, reports."""

import argparse
import asyncio
import json
import os
from pathlib import Path

from app.evaluation.contracts import BenchmarkConfig
from app.evaluation.dataset import (
    annotation_pack,
    prepare_queries,
    query_digest,
    read_queries,
    validate_dataset,
    validate_labels,
)
from app.evaluation.tracking import Experiment, digest


def write_new(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--results", default="evaluation/results/phase07")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--index-report", default="docs/verification/phase04/index.json")
    prepare.add_argument("--cache", default=".cache/evaluation/images")
    prepare.add_argument("--output", default="evaluation/datasets/manifests/phase07_v1.json")
    prepare.add_argument("--queries", default="evaluation/queries/phase07_v1.jsonl")
    prepare.add_argument("--dataset-id", default="phase07_current_index")
    for name in [
        "validate-dataset",
        "annotation-pack",
        "validate-labels",
        "evaluate",
        "benchmark",
        "model-comparison",
        "profile",
    ]:
        sub = commands.add_parser(name)
        sub.add_argument("--snapshot", default="evaluation/datasets/manifests/phase07_v1.json")
        sub.add_argument("--queries", default="evaluation/queries/phase07_v1.jsonl")
        if name in {"validate-labels", "evaluate", "model-comparison"}:
            sub.add_argument("--labels")
        if name == "annotation-pack":
            sub.add_argument("--output", default=".cache/evaluation/annotation.html")
        if name == "evaluate":
            sub.add_argument("--configuration", default="{}")
            sub.add_argument("--config", help="Cùng BenchmarkConfig với latency/ablation")
            sub.add_argument("--split", choices=["dev", "test"])
        if name == "benchmark":
            sub.add_argument("--config", required=True)
        if name == "model-comparison":
            sub.add_argument("--siglip-cache", default="/models/siglip2")
            sub.add_argument("--model", choices=["clip", "siglip2"], required=True)
    report = commands.add_parser("report")
    report.add_argument("--output", default="evaluation/reports/phase07")
    analysis = commands.add_parser("analyze-optimization")
    analysis.add_argument("--suite")
    args = parser.parse_args()
    token = os.environ.get("API_TOKEN", "")
    if args.command == "analyze-optimization":
        from app.evaluation.analysis import analyze_optimization

        print(json.dumps(analyze_optimization(args.results, args.suite)))
        return
    if args.command == "prepare":
        snapshot = validate_dataset(
            args.base_url, token, args.index_report, args.cache, args.dataset_id
        )
        cases = prepare_queries(snapshot)
        write_new(args.output, snapshot)
        target = Path(args.queries)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x") as handle:
            for case in cases:
                handle.write(case.model_dump_json() + "\n")
        print(
            json.dumps(
                {
                    "status": "prepared",
                    "snapshot": args.output,
                    "queries": len(cases),
                    "query_set_sha256": query_digest(cases),
                    "images": len(snapshot["images"]),
                }
            )
        )
        return
    if args.command == "report":
        from app.evaluation.reporting import generate_report

        print(json.dumps(generate_report(args.results, args.output)))
        return
    snapshot = json.loads(Path(args.snapshot).read_text())
    cases = read_queries(args.queries)
    if args.command == "annotation-pack":
        print(
            json.dumps(
                annotation_pack(snapshot, cases, "evaluation/annotation/review.html", args.output)
            )
        )
        return
    labels = json.loads(Path(args.labels).read_text()) if getattr(args, "labels", None) else None
    if args.command == "validate-labels":
        if labels is None:
            parser.error("--labels required; no human labels inferred")
        print(json.dumps(validate_labels(labels, snapshot, cases)))
        return
    config = (
        json.loads(Path(args.config).read_text())
        if args.command == "benchmark" or args.command == "evaluate" and args.config
        else json.loads(args.configuration)
        if args.command == "evaluate"
        else {"model": getattr(args, "model", None)}
    )
    server_environment = snapshot.get("server_environment")
    if args.command in {"benchmark", "evaluate", "validate-dataset"}:
        import httpx

        try:
            response = httpx.get(
                args.base_url + "/api/v1/system/search-runtime",
                headers={"Authorization": "Bearer " + token},
                timeout=5,
            )
            if response.status_code == 200:
                server_environment = response.json()
        except httpx.HTTPError:
            pass
    experiment = Experiment(
        args.results,
        args.command,
        config,
        {
            "dataset_sha256": snapshot["sha256"],
            "dataset_images": len(snapshot["images"]),
            "query_set_sha256": query_digest(cases),
            "label_sha256": digest(labels) if labels else None,
            "active": snapshot["active"],
            "server_environment": server_environment,
        },
    )
    try:
        if args.command == "benchmark":
            from app.evaluation.benchmark import run_benchmark

            result = asyncio.run(
                run_benchmark(
                    BenchmarkConfig.model_validate(config), cases, snapshot, args.base_url, token
                )
            )
        elif args.command == "evaluate":
            from app.evaluation.quality import evaluate

            result = evaluate(
                cases,
                snapshot,
                labels,
                args.base_url,
                token,
                {} if args.config else config,
                args.split,
                BenchmarkConfig.model_validate(config) if args.config else None,
            )
        elif args.command == "profile":
            from app.evaluation.profiling import profile_services

            result = asyncio.run(profile_services(snapshot))
        elif args.command == "validate-dataset":
            # Verify each frozen image hash against live private content and ready receipt.
            import hashlib

            import httpx

            with httpx.Client(
                base_url=args.base_url, headers={"Authorization": "Bearer " + token}, timeout=10
            ) as client:
                for image in snapshot["images"]:
                    response = client.get(
                        f"/api/v1/images/{image['image_id']}/content?variant=original"
                    )
                    response.raise_for_status()
                    if hashlib.sha256(response.content).hexdigest() != image["sha256"]:
                        raise ValueError("live_corpus_digest_drift")
            result = {
                "status": "valid",
                "images": len(snapshot["images"]),
                "snapshot_sha256": snapshot["sha256"],
            }
        else:
            from app.evaluation.models import compare_model

            result = asyncio.run(
                compare_model(args.model, args.siglip_cache, snapshot, cases, labels)
            )
        experiment.complete(result)
        print(
            json.dumps(
                {
                    "experiment_id": experiment.identifier,
                    "directory": str(experiment.directory),
                    "status": result["status"],
                }
            )
        )
    except Exception as exc:
        experiment.complete(
            {
                "status": "failed",
                "error_type": type(exc).__name__,
                "error_code": getattr(exc, "code", None),
            }
        )
        raise


if __name__ == "__main__":
    main()
