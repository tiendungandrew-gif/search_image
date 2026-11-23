#!/usr/bin/env python3
"""Research matrix trên source đã đóng băng; immutable experiment IDs, không in secrets."""

import argparse
import json
import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--optimization", action="store_true")
    parser.add_argument("--matrix", action="store_true")
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()
    env = os.environ.copy()
    for line in (ROOT / ".env").read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env[key] = value
    secrets = [
        value
        for key, value in env.items()
        if any(x in key for x in ["TOKEN", "PASSWORD", "SECRET", "ACCESS_KEY", "API_KEY"])
        and len(value) >= 16
    ]
    records = []

    original_width = int(env.get("SEARCH_OBJECT_CHECK_CONCURRENCY", "1"))

    def run(command):
        result = subprocess.run(
            command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=1800
        )
        if result.returncode:
            log = result.stdout + "\n" + result.stderr
            for value in secrets:
                log = log.replace(value, "[REDACTED]")
            print(log[-10000:], flush=True)
            raise RuntimeError("research_command_failed")
        return result.stdout

    def configure(width):
        path = ROOT / ".env"
        lines = [
            line
            for line in path.read_text().splitlines()
            if not line.startswith("SEARCH_OBJECT_CHECK_CONCURRENCY=")
        ]
        path.write_text("\n".join(lines) + f"\nSEARCH_OBJECT_CHECK_CONCURRENCY={width}\n")
        path.chmod(0o600)
        run(
            [
                "docker",
                "compose",
                "up",
                "-d",
                "--no-deps",
                "--force-recreate",
                "--wait",
                "--wait-timeout",
                "180",
                "backend",
            ]
        )
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            try:
                response = httpx.get(
                    "http://127.0.0.1:8000/api/v1/health?check=search",
                    headers={"Authorization": "Bearer " + env["API_TOKEN"]},
                    timeout=5,
                )
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.5)
        raise RuntimeError("search_not_ready_after_restart")

    def benchmark(name):
        print("[RUN] " + name, flush=True)
        output = run(
            [
                str(ROOT / "backend/.venv/bin/python"),
                "-m",
                "app.cli.evaluation",
                "benchmark",
                "--config",
                f"evaluation/experiments/phase07/{name}.json",
            ]
        )
        record = json.loads(output.strip().splitlines()[-1])
        records.append(record)
        print("[OK] " + record["experiment_id"], flush=True)

    suite_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "_" + uuid4().hex[:8]
    status = "running"
    try:
        if args.optimization:
            for width, rep in [(1, 1), (2, 1), (2, 2), (1, 2)]:
                configure(width)
                benchmark(f"opt_head{width}_rep{rep}")
            configure(original_width)
        if args.matrix:
            names = args.only or [
                "fast_default",
                "image",
                "A0",
                "A1",
                "A2",
                "A3",
                "A4",
                "A5_text",
                "A5_rrf",
                "A5_score",
                "load1",
                "load5",
                "load10",
                "load20",
                "load_mixed",
            ]
            for name in names:
                if name not in {
                    p.stem for p in (ROOT / "evaluation/experiments/phase07").glob("*.json")
                }:
                    raise ValueError("unknown_config_name")
                benchmark(name)
        status = "complete"
    finally:
        if args.optimization and status != "complete":
            configure(original_width)
        directory = ROOT / "docs/verification/phase07/suites"
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / (suite_id + ".json")).open("x") as handle:
            json.dump(
                {
                    "status": status,
                    "optimization": args.optimization,
                    "matrix": args.matrix,
                    "experiments": records,
                },
                handle,
                indent=2,
            )
    print(json.dumps({"status": status, "suite": suite_id, "experiments": len(records)}))


if __name__ == "__main__":
    main()
