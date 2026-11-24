#!/usr/bin/env python3
"""Nghiệm thu Phase05 thật, giữ index/data; redact secrets trong logs."""

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--skip-browser", action="store_true")
    parser.add_argument("--skip-benchmark", action="store_true")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--advanced", action="store_true", help="Nghiệm thu Phase 06 và E1–E5")
    parser.add_argument("--rag", action="store_true", help="Nghiệm thu Phase 08/Gemini thật")
    parser.add_argument(
        "--agent",
        action="store_true",
        help="Nghiệm thu Phase 09; fixture tri thức chỉ trong DB tách biệt",
    )
    parser.add_argument("--output", help="Thư mục report riêng, giữ các lượt kiểm thử trước")
    parser.add_argument(
        "--evaluation",
        action="store_true",
        help="Functional regression Phase 07; research runs ghi riêng",
    )
    args = parser.parse_args()
    args.rag = args.rag or args.agent
    args.evaluation = args.evaluation or args.rag
    args.advanced = args.advanced or args.evaluation
    OUT = (
        ROOT
        / "docs/verification"
        / (
            "phase09"
            if args.agent
            else "phase08"
            if args.rag
            else "phase07"
            if args.evaluation
            else "phase06"
            if args.advanced
            else "phase05"
        )
    )
    if args.output:
        OUT = Path(args.output)
    OUT.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    if args.rag:
        env["RUN_RAG_E2E"] = "1"
    if args.agent:
        env["RUN_AGENT_E2E"] = "1"
    secrets = []
    for line in (ROOT / ".env").read_text().splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key] = value
        if (
            any(part in key for part in ["TOKEN", "PASSWORD", "SECRET", "ACCESS_KEY", "API_KEY"])
            and len(value) >= 16
        ):
            secrets.append(value)

    def run(label, command, timeout=600):
        print("[RUN] " + label, flush=True)
        r = subprocess.run(
            command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout
        )
        log = r.stdout + "\n" + r.stderr
        for secret in secrets:
            log = log.replace(secret, "[REDACTED]")
        (OUT / (label + ".txt")).write_text(log)
        counts = re.findall(r"(\d+) passed", log)
        if r.returncode:
            failed = re.findall(r"(\d+) failed", log)
            (OUT / (label + ".json")).write_text(
                json.dumps(
                    {
                        "status": "failed",
                        "passed": int(counts[-1]) if counts else None,
                        "failed": int(failed[-1]) if failed else None,
                    },
                    indent=2,
                )
                + "\n"
            )
            print(log[-18000:], flush=True)
            raise RuntimeError(label + " failed " + str(r.returncode))
        value = {"status": "pass", "passed": int(counts[-1]) if counts else None}
        (OUT / (label + ".json")).write_text(json.dumps(value, indent=2) + "\n")
        print("[OK] " + label, flush=True)

    summary = {
        "status": "running",
        "build_requested": not args.skip_build,
        "browser_requested": not args.skip_browser,
        "benchmark_requested": not args.skip_benchmark,
    }
    try:
        run("compose_config", ["docker", "compose", "--profile", "indexing", "config", "--quiet"])
        if not args.skip_build:
            run("build", ["docker", "compose", "build", "backend", "indexing-worker", "frontend"])
        run(
            "startup",
            [
                "docker",
                "compose",
                "up",
                "-d",
                "--wait",
                "--wait-timeout",
                "180",
                "backend",
                "frontend",
            ],
        )
        run(
            "backend_tests",
            [
                "docker",
                "compose",
                "--profile",
                "indexing",
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "-e",
                "RUN_INTEGRATION=1",
                "-e",
                "RUN_INDEXING_E2E=1",
                "-e",
                "RUN_SEARCH_E2E=1",
                "-e",
                "RUN_ADVANCED_E2E=" + ("1" if args.advanced else "0"),
                "-e",
                "RUN_EVALUATION_E2E=" + ("1" if args.evaluation else "0"),
                "-e",
                "RUN_RAG_E2E=" + ("1" if args.rag else "0"),
                "-e",
                "RUN_RAG_CORPUS_E2E=" + env.get("RUN_RAG_CORPUS_E2E", "0"),
                "-e",
                "RUN_AGENT_E2E=" + ("1" if args.agent else "0"),
                "indexing-worker",
                "pytest",
                "backend/tests/unit",
                "backend/tests/integration",
                "-q",
                "-p",
                "no:cacheprovider",
            ],
        )
        run(
            "python_lint",
            ["docker", "compose", "exec", "-T", "backend", "ruff", "check", "backend", "scripts"],
        )
        run(
            "python_format",
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "backend",
                "ruff",
                "format",
                "--check",
                "backend",
                "scripts",
            ],
        )
        run(
            "frontend_checks",
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "frontend",
                "sh",
                "-ec",
                "npm run typecheck && npm run lint && npm test && npm run build",
            ],
        )
        run(
            "http_smoke",
            [str(ROOT / "backend/.venv/bin/python"), "scripts/checks/verify_services.py"],
        )
        if not args.skip_browser:
            run("browser", ["npm", "--prefix", "frontend", "run", "test:e2e"])
        if not args.skip_benchmark:
            configurations = [("text", "text", []), ("image", "image", [])]
            if args.advanced:
                configurations = [
                    ("E1_text", "text", []),
                    ("E1_image", "image", []),
                    ("E2", "multi_intent", ["--retrieval-strategy", "multi_query"]),
                    ("E3_rrf", "multi_intent", []),
                    ("E3_score", "multi_intent", ["--fusion", "weighted_score"]),
                    ("E4", "multi_intent", ["--rerank"]),
                    ("E5_rrf", "multimodal", ["--rerank"]),
                    ("E5_score", "multimodal", ["--rerank", "--fusion", "weighted_score"]),
                ]
            for name, mode, extra in configurations:
                run(
                    "benchmark_" + name,
                    [
                        str(ROOT / "backend/.venv/bin/python"),
                        "evaluation/scripts/benchmark_search.py",
                        "--mode",
                        mode,
                        "--requests",
                        str(args.requests),
                        "--concurrency",
                        "1",
                        "--warmup",
                        "5",
                        "--output",
                        "evaluation/results/"
                        + ("phase06_" + name if args.advanced else mode + "_baseline")
                        + ".json",
                    ]
                    + extra,
                )
        run(
            "index_preserved",
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "indexing-worker",
                "python",
                "-m",
                "app.cli.indexing",
                "verify",
                "--index",
                env["INGESTION_INDEX_ID"],
            ],
        )
        summary["status"] = "pass"
    except Exception as exc:
        summary["status"] = "failed"
        summary["failure_type"] = type(exc).__name__
        print("[FAIL] " + str(exc), flush=True)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
