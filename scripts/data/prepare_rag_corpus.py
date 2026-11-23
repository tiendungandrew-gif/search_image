#!/usr/bin/env python3
"""Index subset COCO ở collection mới, kiểm chứng rồi mới activate khi có --activate."""

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="datasets/coco_phase08_v1")
    parser.add_argument("--baseline", default="evaluation/datasets/manifests/phase07_v1.json")
    parser.add_argument("--version", default="clip_coco_phase08_v1")
    parser.add_argument("--output", required=True)
    parser.add_argument("--activate", action="store_true")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    dataset = Path(args.dataset).resolve()
    if not dataset.is_relative_to(ROOT / "datasets"):
        raise ValueError("DATASET_PATH_NOT_ALLOWED")
    # Verify the frozen download before introducing any database state.
    import hashlib

    manifest = json.loads((dataset / "manifest.json").read_text())
    for item in manifest["images"]:
        path = (dataset / item["filename"]).resolve()
        if (
            not path.is_relative_to(dataset)
            or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]
        ):
            raise ValueError("DATASET_CHECKSUM_MISMATCH")
    if (
        hashlib.sha256((dataset / "metadata.jsonl").read_bytes()).hexdigest()
        != manifest["metadata_sha256"]
    ):
        raise ValueError("DATASET_METADATA_MISMATCH")
    baseline = json.loads(Path(args.baseline).read_text())
    secrets = [
        line.split("=", 1)[1]
        for line in (ROOT / ".env").read_text().splitlines()
        if "=" in line
        and any(k in line.split("=", 1)[0] for k in ["KEY", "TOKEN", "PASSWORD", "SECRET"])
        and len(line.split("=", 1)[1]) >= 12
    ]

    def save(name, value):
        (output / (name + ".json")).write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        )

    def run(name, *command):
        print("[RUN] " + name, flush=True)
        result = subprocess.run(
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
                *command,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=900,
        )
        log = result.stdout + "\n" + result.stderr
        for secret in secrets:
            log = log.replace(secret, "[REDACTED]")
        (output / (name + ".txt")).write_text(log)
        if result.returncode:
            raise RuntimeError(name + " failed; see redacted log")
        value = json.loads(result.stdout)
        save(name, value)
        print("[OK] " + name, flush=True)
        return value

    summary = {
        "status": "running",
        "activation_requested": args.activate,
        "baseline_index_id": baseline["active"]["index_id"],
        "download_manifest_sha256": hashlib.sha256(
            (dataset / "manifest.json").read_bytes()
        ).hexdigest(),
    }
    try:
        before = run(
            "baseline_before", "app.cli.indexing", "verify", "--index", summary["baseline_index_id"]
        )
        target = run("register", "app.cli.indexing", "register", "--version", args.version)
        summary["target_index_id"] = target["index_id"]
        imported = run(
            "ingest",
            "app.cli.indexing",
            "dataset",
            "--input",
            "/datasets/" + dataset.relative_to(ROOT / "datasets").as_posix(),
            "--index",
            target["index_id"],
            "--name",
            manifest["source_dataset"],
            "--license",
            "per-file",
            "--rights-ref",
            manifest.get("rights_ref", "https://cocodataset.org/#termsofuse"),
        )
        if imported["failed"] or imported["accepted"] != manifest["count"]:
            raise RuntimeError("CORPUS_INGEST_INCOMPLETE")
        run(
            "copy_baseline",
            "app.cli.indexing",
            "reindex",
            "--index",
            target["index_id"],
            "--images",
            *before["image_ids"],
            "--key",
            "phase08-baseline-" + target["index_id"],
        )
        run("worker", "app.cli.indexing", "worker", "--index", target["index_id"], "--once")
        ready = run(
            "verify", "app.cli.indexing", "verify", "--index", target["index_id"], "--mark-ready"
        )
        if ready["verified_images"] != manifest["count"] + before["verified_images"]:
            raise RuntimeError("CORPUS_COUNT_MISMATCH")
        after = run(
            "baseline_after", "app.cli.indexing", "verify", "--index", summary["baseline_index_id"]
        )
        if before["image_ids"] != after["image_ids"]:
            raise RuntimeError("BASELINE_CHANGED")
        if args.activate:
            run("activation", "app.cli.search", "--activate", target["index_id"])
            print("Reload API after activation to load the matching index runtime.", flush=True)
        summary.update(
            status="pass",
            verified_images=ready["verified_images"],
            baseline_preserved=True,
            activated=args.activate,
        )
    except Exception as error:
        summary.update(status="failed", error_type=type(error).__name__)
        raise
    finally:
        save("summary", summary)


if __name__ == "__main__":
    main()
