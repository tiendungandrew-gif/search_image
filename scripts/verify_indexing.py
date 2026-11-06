#!/usr/bin/env python3
"""Nghiệm thu Prompt 04 bằng Docker, CLIP và sample dataset thật; không fake vectors."""

import argparse
import json
import re
import subprocess
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/verification/phase04"


def command(label, args, structured=False, extra=None):
    print("[RUN] " + label, flush=True)
    completed = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=1800)
    if completed.returncode:
        print(completed.stdout[-16000:])
        print(completed.stderr[-8000:])
        raise RuntimeError(label + " failed, exit " + str(completed.returncode))
    if structured:
        value = json.loads(completed.stdout)
    else:
        value = {"status": "pass", "return_code": 0}
        counts = re.findall(r"(\d+) passed", completed.stdout)
        if counts:
            value["passed"] = int(counts[-1])
    if extra:
        value.update(extra)
    (OUT / (label + ".json")).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    print("[OK] " + label, flush=True)
    return value


def cli(label, *args):
    return command(
        label,
        [
            "docker",
            "compose",
            "--profile",
            "indexing",
            "run",
            "--rm",
            "--no-deps",
            "-T",
            "indexing-worker",
            "python",
            "-m",
            "app.cli.indexing",
            *args,
        ],
        structured=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    result = {"status": "running", "build_requested": not args.skip_build, "checks": {}}
    restore_worker = False
    try:
        settings = dict(
            line.split("=", 1)
            for line in (ROOT / ".env").read_text().splitlines()
            if "=" in line and not line.startswith("#")
        )
        index = str(UUID(settings["INGESTION_INDEX_ID"]))
        result["index_id"] = index
        command(
            "compose_config", ["docker", "compose", "--profile", "indexing", "config", "--quiet"]
        )
        if not args.skip_build:
            command("build", ["docker", "compose", "build", "backend", "indexing-worker"])
        command(
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
        running = subprocess.check_output(
            [
                "docker",
                "compose",
                "--profile",
                "indexing",
                "ps",
                "--status",
                "running",
                "--services",
            ],
            cwd=ROOT,
            text=True,
        ).splitlines()
        restore_worker = "indexing-worker" in running
        result["worker_was_running"] = restore_worker
        if restore_worker:
            command(
                "worker_pause",
                ["docker", "compose", "--profile", "indexing", "stop", "indexing-worker"],
            )
        tests = command(
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
                "indexing-worker",
                "pytest",
                "backend/tests/unit",
                "backend/tests/integration",
                "-q",
                "-p",
                "no:cacheprovider",
            ],
        )
        result["checks"]["backend_tests"] = tests
        command(
            "python_lint",
            ["docker", "compose", "exec", "-T", "backend", "ruff", "check", "backend", "scripts"],
        )
        command(
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
        command(
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
        command("http_smoke", ["python3", "scripts/verify_services.py"])
        dataset = cli(
            "dataset",
            "dataset",
            "--input",
            "/datasets/sample",
            "--index",
            index,
            "--name",
            "scikit-image-v0.25.2",
            "--license",
            "per-file",
            "--rights-ref",
            "datasets/sample_manifest.json",
        )
        if dataset["failed"] or dataset["validated"] != 10:
            raise RuntimeError("Sample ingestion did not validate 10 files")
        accepted = cli(
            "batch_submission",
            "source",
            "--source",
            dataset["source_id"],
            "--index",
            index,
            "--key",
            "verify-" + uuid4().hex,
        )
        metrics = cli("worker", "worker", "--index", index, "--once")
        job = cli("job", "job", "--job", accepted["job_id"])
        if job["status"] != "succeeded" or job["counts"]["succeeded"] != 10:
            raise RuntimeError("Batch not completed")
        verified = cli("index", "verify", "--index", index, "--mark-ready")
        if verified["status"] != "pass" or verified["exact_vector_count"] != 10:
            raise RuntimeError("Cross-storage verification failed")
        repeated = cli(
            "repeat",
            "dataset",
            "--input",
            "/datasets/sample",
            "--index",
            index,
            "--name",
            "scikit-image-v0.25.2",
            "--license",
            "per-file",
            "--rights-ref",
            "datasets/sample_manifest.json",
        )
        if repeated["duplicates"] != 10 or repeated["failed"]:
            raise RuntimeError("Repeat not idempotent")
        after = cli("index_after_repeat", "verify", "--index", index)
        if after["image_ids"] != verified["image_ids"] or after["exact_vector_count"] != 10:
            raise RuntimeError("Repeat changed identities/count")
        orphans = cli("orphans", "orphans")
        if orphans["orphan_object_keys"] or orphans["scan_truncated"]:
            raise RuntimeError("Orphan originals need review")
        if sum(batch["batch_size"] for batch in metrics["batches"]) != 10:
            raise RuntimeError("Missing real inference measurements")
        result["checks"].update(
            {
                "real_clip_batch": "pass",
                "cross_storage_ids_bytes_vectors": "pass",
                "idempotent_repeat": "pass",
                "original_orphans": "pass",
            }
        )
        result["status"] = "pass"
    except Exception as exc:
        result["status"] = "failed"
        result["failure_type"] = type(exc).__name__
        print("[FAIL] " + str(exc), flush=True)
    finally:
        if restore_worker:
            try:
                command(
                    "worker_restore",
                    ["docker", "compose", "--profile", "indexing", "up", "-d", "indexing-worker"],
                )
            except Exception:
                result["status"] = "failed"
                result["worker_restore"] = "failed"
    (OUT / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
