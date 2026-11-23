"""Triển khai Compose production-like; không publish images hoặc tác động stack development."""

import argparse
import json
import ssl
import sys
import time
import urllib.request
from pathlib import Path

from deployment.common import ROOT, Deployment, initialize


def source_version():
    sys.path.insert(0, str(ROOT / "backend"))
    from app.evaluation.tracking import source_snapshot

    return source_snapshot()["sha256"]


def check(deployment):
    cfg = deployment.cfg
    scheme = "https" if deployment.tls else "http"
    port = cfg.get("DEPLOY_HTTPS_PORT", "8443") if deployment.tls else cfg["DEPLOY_HTTP_PORT"]
    context = ssl.create_default_context(cafile=cfg.get("DEPLOY_TLS_CA_FILE") or None)
    base = cfg.get("DEPLOY_CHECK_URL", f"{scheme}://127.0.0.1:{port}")
    results = {}
    paths = ["/healthz", "/api/v1/health/live", "/api/v1/health/ready"]
    account_request = urllib.request.Request(base + "/api/v1/auth/me")
    try:
        with urllib.request.urlopen(account_request, timeout=15, context=context) as response:
            account_mode = not json.loads(response.read()).get("legacy_enabled", False)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        account_mode = False  # Compatibility with frozen pre-account releases.
    if not account_mode:
        paths.append("/api/v1/system/workspace")
    if cfg["SEARCH_ENABLED"] == "true":
        paths.append("/api/v1/health?check=search")
    for path in paths:
        request = urllib.request.Request(
            base + path, headers={"Authorization": "Bearer " + cfg["API_TOKEN"]}
        )
        with urllib.request.urlopen(request, timeout=15, context=context) as response:
            body = response.read()
            results[path] = body.decode() if path == "/healthz" else json.loads(body)
    if account_mode:
        results["/api/v1/auth/me"] = {"user": None, "legacy_enabled": False}
        results["private_inventory"] = deployment.application("app.cli.operations", "inventory")
    deployment.compose("exec", "-T", "worker", "python", "-m", "app.cli.worker", "--health")
    return results


def startup(deployment):
    deployment.compose("config", "--quiet")
    deployment.compose(
        "up",
        "-d",
        "--no-build",
        "--wait",
        "--wait-timeout",
        "180",
        "postgres",
        "qdrant",
        "minio",
        "backend",
        "worker",
        "frontend",
        timeout=240,
    )
    result = check(deployment)
    print(json.dumps({"status": "ready", "verification": result}, ensure_ascii=False, indent=2))


def build(deployment, release):
    revision = source_version()
    release = release or deployment.cfg["DEPLOY_RELEASE"]
    from deployment.common import validate

    validate(deployment.cfg | {"DEPLOY_RELEASE": release})
    deployment.env["DEPLOY_RELEASE"] = release
    for component in ["backend", "frontend"]:
        image = f"semantic-image-search/{component}:{release}"
        existing = deployment.run(["docker", "image", "inspect", image], quiet=True, check=False)
        if existing.returncode == 0:
            labels = json.loads(existing.stdout)[0]["Config"].get("Labels", {})
            if labels.get("org.opencontainers.image.revision") != revision:
                raise ValueError("RELEASE_TAG_ALREADY_EXISTS_FOR_DIFFERENT_SOURCE_USE_NEW_RELEASE")
    existing_manifest = ROOT / ".cache/deployment/releases" / (release + ".json")
    if existing_manifest.is_file():
        frozen = json.loads(existing_manifest.read_text())
        for component, expected in frozen["images"].items():
            inspected = deployment.run(
                ["docker", "image", "inspect", f"semantic-image-search/{component}:{release}"],
                quiet=True,
            )
            if json.loads(inspected.stdout)[0]["Id"] != expected:
                raise ValueError("IMMUTABLE_RELEASE_IMAGE_ID_MISMATCH")
        print(json.dumps({"status": "reused_immutable_release", **frozen}))
        return
    deployment.env["DEPLOY_SOURCE_VERSION"] = revision
    deployment.compose("config", "--quiet")
    deployment.compose("build", "backend", "frontend", "minio", timeout=1200)
    manifest = {
        "release": release,
        "source_sha256": revision,
        "images": {},
    }
    for component in ["backend", "frontend"]:
        image = f"semantic-image-search/{component}:{release}"
        value = deployment.run(["docker", "image", "inspect", image], quiet=True)
        manifest["images"][component] = json.loads(value.stdout)[0]["Id"]
    folder = ROOT / ".cache/deployment/releases"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (release + ".json")
    if path.exists() and json.loads(path.read_text()) != manifest:
        raise ValueError("RELEASE_MANIFEST_ALREADY_EXISTS")
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


def import_dataset(deployment, args):
    path = Path(args.input).resolve()
    root = Path(deployment.cfg["DEPLOY_DATASET_PATH"]).resolve()
    if not path.is_relative_to(root):
        raise ValueError("DATASET_PATH_OUTSIDE_CONFIGURED_ROOT")
    mode = "dataset" if path.is_dir() else "image"
    container_path = "/datasets/" + path.relative_to(root).as_posix()
    common = [
        "--input",
        container_path,
        "--name",
        args.name,
        "--version",
        args.version,
        "--license",
        args.license,
        "--rights-ref",
        args.rights_ref,
    ]
    if args.dry_run:
        result = deployment.application("app.cli.indexing", mode, *common, "--dry-run")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if not args.index_version:
        raise ValueError("INDEX_VERSION_REQUIRED_FOR_APPLY")
    deployment.update(EMBEDDING_BATCH_SIZE=str(args.batch_size))
    registered = deployment.application(
        "app.cli.indexing", "register", "--version", args.index_version, timeout=180
    )
    identity = registered["index_id"]
    inherited = deployment.application("app.cli.operations", "carry-forward", "--index", identity)
    deployment.compose("up", "-d", "--no-deps", "--no-build", "--wait", "worker")
    accepted = deployment.application(
        "app.cli.indexing", mode, *common, "--index", identity, timeout=600
    )
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        result = deployment.application("app.cli.operations", "index-status", "--index", identity)
        counts = result["counts"]
        if counts.get("failed", 0):
            raise RuntimeError("IMPORT_HAS_FAILED_ITEMS_INSPECT_JOBS")
        if counts and not any(
            counts.get(status, 0)
            for status in ["awaiting_input", "queued", "processing", "retry_wait"]
        ):
            break
        time.sleep(2)
    else:
        raise TimeoutError("IMPORT_WORKER_DEADLINE")
    verified = deployment.application(
        "app.cli.indexing", "verify", "--index", identity, "--mark-ready", timeout=600
    )
    activated = deployment.application("app.cli.search", "--activate", identity, timeout=180)
    deployment.update(SEARCH_ENABLED="true", INGESTION_INDEX_ID=identity)
    deployment.compose(
        "up",
        "-d",
        "--no-deps",
        "--no-build",
        "--wait",
        "--wait-timeout",
        "180",
        "backend",
        "worker",
        timeout=240,
    )
    print(
        json.dumps(
            {
                "inherited": inherited,
                "accepted": accepted,
                "verified": verified,
                "activated": activated,
            },
            indent=2,
        )
    )
    print(json.dumps(check(deployment), ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env.deploy")
    parser.add_argument("--evidence-dir")
    parser.add_argument("--tls", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--project", default="image-search-prod")
    init.add_argument("--port", type=int, default=8080)
    init.add_argument("--release", default="phase12-local")
    init.add_argument("--without-ml", action="store_true")
    init.add_argument("--model-path", default=".cache/clip")
    init.add_argument("--dataset-path", default="datasets")
    build_command = sub.add_parser("build")
    build_command.add_argument("--release")
    for name in [
        "validate",
        "up",
        "down",
        "restart",
        "status",
        "check",
        "model-prepare",
        "model-verify",
    ]:
        sub.add_parser(name)
    logs = sub.add_parser("logs")
    logs.add_argument("--tail", type=int, default=100)
    logs.add_argument(
        "--service",
        choices=["backend", "worker", "frontend", "bootstrap", "postgres", "qdrant", "minio"],
    )
    features = sub.add_parser("features")
    features.add_argument("--search", choices=["true", "false"])
    features.add_argument("--agent", choices=["true", "false"])
    features.add_argument("--rag", choices=["true", "false"])
    ingest = sub.add_parser("import")
    ingest.add_argument("--input", required=True)
    ingest.add_argument("--name", required=True)
    ingest.add_argument("--version", required=True)
    ingest.add_argument("--index-version")
    ingest.add_argument("--batch-size", type=int, choices=range(1, 33), default=4)
    ingest.add_argument("--license", required=True)
    ingest.add_argument("--rights-ref", required=True)
    ingest.add_argument("--dry-run", action="store_true")
    ingest.add_argument("--timeout", type=int, default=600)
    knowledge = sub.add_parser("knowledge")
    knowledge.add_argument("--input", required=True)
    knowledge.add_argument("--apply", action="store_true")
    backup = sub.add_parser("backup")
    backup.add_argument("--output", default="backups")
    restore = sub.add_parser("restore")
    restore.add_argument("--backup", required=True)
    verify_restore = sub.add_parser("verify-restore")
    verify_restore.add_argument("--backup", required=True)
    for name in ["update", "rollback"]:
        release = sub.add_parser(name)
        release.add_argument("--release", required=True)
    args = parser.parse_args()
    if args.command == "init":
        initialize(
            Path(args.env_file),
            args.project,
            args.port,
            Path(args.model_path),
            Path(args.dataset_path),
            release=args.release,
            install_ml=not args.without_ml,
        )
        print("Deployment environment initialized (0600); serving .env unchanged.")
        return
    deployment = Deployment(args.env_file, args.evidence_dir, args.tls)
    if args.command not in {"validate", "status", "check", "logs", "verify-restore"}:
        deployment.acquire_lock()
    if args.command == "build":
        build(deployment, args.release)
    elif args.command == "validate":
        deployment.compose("config", "--quiet")
    elif args.command == "up":
        startup(deployment)
    elif args.command == "down":
        deployment.compose("down", timeout=180)
    elif args.command == "restart":
        deployment.compose("restart", "backend", "worker", "frontend", timeout=120)
        for _ in range(45):
            try:
                print(json.dumps(check(deployment), ensure_ascii=False))
                break
            except Exception:
                time.sleep(1)
        else:
            raise RuntimeError("RESTART_NOT_READY")
    elif args.command == "check":
        print(json.dumps(check(deployment), ensure_ascii=False, indent=2))
    elif args.command == "status":
        rows = deployment.compose("ps", "--format", "json", quiet=True).stdout.splitlines()
        containers = [json.loads(row) for row in rows if row.strip()]
        print(
            json.dumps(
                {
                    "containers": [
                        {
                            key: row.get(key)
                            for key in ["Service", "State", "Health", "Image", "Ports"]
                        }
                        for row in containers
                    ],
                    "inventory": deployment.application("app.cli.operations", "inventory"),
                },
                indent=2,
            )
        )
    elif args.command == "logs":
        services = [args.service] if args.service else []
        deployment.compose("logs", "--no-color", "--tail", str(args.tail), *services)
    elif args.command == "model-prepare":
        import os

        deployment.compose(
            "--profile",
            "tools",
            "run",
            "--rm",
            "--no-deps",
            "-T",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "model-preparer",
            timeout=900,
        )
    elif args.command == "model-verify":
        print(json.dumps(deployment.application("app.cli.operations", "model-verify", timeout=180)))
    elif args.command == "features":
        deployment.update(
            **{
                key.upper() + "_ENABLED": value
                for key in ["search", "agent", "rag"]
                if (value := getattr(args, key)) is not None
            }
        )
        deployment.compose("up", "-d", "--no-deps", "--no-build", "--wait", "backend", timeout=240)
        print(json.dumps(check(deployment), ensure_ascii=False))
    elif args.command == "import":
        import_dataset(deployment, args)
    elif args.command == "knowledge":
        path = Path(args.input).resolve()
        root = Path(deployment.cfg["DEPLOY_DATASET_PATH"]).resolve()
        if not path.is_relative_to(root):
            raise ValueError("KNOWLEDGE_PATH_OUTSIDE_DATASET_ROOT")
        command = ["app.cli.knowledge", "--input", "/datasets/" + path.relative_to(root).as_posix()]
        if args.apply:
            command.append("--apply")
        print(json.dumps(deployment.application(*command), ensure_ascii=False))
    else:
        from deployment.backup import backup_deployment, restore_deployment, switch_release

        if args.command == "backup":
            backup_deployment(deployment, Path(args.output))
        elif args.command == "restore":
            restore_deployment(deployment, Path(args.backup))
        elif args.command == "verify-restore":
            from deployment.backup import validate_backup, verify_restored

            verify_restored(deployment, validate_backup(Path(args.backup)))
        else:
            switch_release(deployment, args.release, rollback=args.command == "rollback")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error_type": type(error).__name__,
                    "error_code": str(error)
                    if str(error).replace("_", "").isalnum() and str(error).isupper()
                    else "OPERATION_FAILED",
                    "action": "Check private deployment operation logs",
                }
            )
        )
        raise SystemExit(1) from None
