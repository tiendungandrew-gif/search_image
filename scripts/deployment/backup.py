"""Backup quiesced, checksum và restore chỉ vào namespace trống đã xác minh."""

import hashlib
import json
import os
import re
import selectors
import subprocess
import tarfile
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from deployment.common import ROOT

FILES = {"postgres.dump", "qdrant.tgz", "minio.tgz"}
ARCHIVER = "alpine:3.22.2"


def checksum(path):
    result = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            result.update(chunk)
    return result.hexdigest()


def stream(deployment, command, *, source=None, destination=None, timeout=600):
    started = time.monotonic()
    process = subprocess.Popen(
        deployment.docker_command(command),
        cwd=ROOT,
        env=deployment.env,
        stdin=subprocess.PIPE if source else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    incoming = source.open("rb") if source else None
    output = destination.open("xb") if destination else None
    if destination:
        destination.chmod(0o600)
    pending = b""
    diagnostics = bytearray()
    if source:
        os.set_blocking(process.stdin.fileno(), False)
        selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
    try:
        while selector.get_map():
            if time.monotonic() - started > timeout:
                raise TimeoutError("BACKUP_TRANSFER_DEADLINE")
            for key, _ in selector.select(timeout=0.5):
                if key.data == "stdin":
                    if not pending:
                        pending = incoming.read(65536)
                    if not pending:
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                    else:
                        try:
                            count = os.write(key.fd, pending)
                            pending = pending[count:]
                        except BlockingIOError:
                            pass
                else:
                    chunk = os.read(key.fd, 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                    elif output and key.data == "stdout":
                        output.write(chunk)
                    else:
                        diagnostics.extend(chunk)
                        if len(diagnostics) > 131072:
                            del diagnostics[:-131072]
        code = process.wait(timeout=max(1, timeout - (time.monotonic() - started)))
        deployment.record(
            command,
            code,
            deployment.scrub(diagnostics.decode(errors="replace")),
            time.monotonic() - started,
        )
        if code:
            raise RuntimeError("BACKUP_TRANSFER_FAILED")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        selector.close()
        if incoming:
            incoming.close()
        if output:
            output.close()


def owned_volume(deployment, role):
    name = deployment.project + "_" + role + "_data"
    result = deployment.run(["docker", "volume", "inspect", name], quiet=True)
    value = json.loads(result.stdout)[0]
    if value.get("Labels", {}).get("com.docker.compose.project") != deployment.project:
        raise ValueError("VOLUME_OWNERSHIP_MISMATCH")
    return name


def volume_command(deployment, role, restore=False):
    volume = owned_volume(deployment, role)
    command = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--read-only",
        "--user",
        "0:0",
        "--cap-drop",
        "ALL",
        "--cap-add",
        "DAC_OVERRIDE",
        "--security-opt",
        "no-new-privileges:" + deployment.cfg.get("DEPLOY_NO_NEW_PRIVILEGES", "true"),
    ]
    if restore:
        command += ["--cap-add", "CHOWN", "--cap-add", "FOWNER", "-i"]
    command += [
        "--mount",
        f"type=volume,src={volume},dst=/data" + ("" if restore else ",readonly"),
        ARCHIVER,
        "tar",
        "-xzf" if restore else "-czf",
        "-",
        "-C",
        "/data",
    ]
    return command if restore else command + ["."]


def validate_backup(folder):
    if folder.is_symlink():
        raise ValueError("BACKUP_SYMLINK_NOT_ALLOWED")
    manifest = json.loads((folder / "manifest.json").read_text())
    if manifest.get("format") != "image-search-cold-backup-v1" or set(manifest["files"]) != FILES:
        raise ValueError("INVALID_BACKUP_FORMAT")
    for name, expected in manifest["files"].items():
        path = folder / name
        if path.is_symlink() or checksum(path) != expected["sha256"]:
            raise ValueError("BACKUP_CHECKSUM_MISMATCH")
        if name.endswith(".tgz"):
            with tarfile.open(path) as archive:
                for member in archive:
                    relative = Path(member.name)
                    if (
                        relative.is_absolute()
                        or ".." in relative.parts
                        or not (member.isfile() or member.isdir())
                    ):
                        raise ValueError("UNSAFE_BACKUP_ARCHIVE")
    return manifest


def backup_deployment(deployment, output):
    identifier = datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "_" + uuid4().hex[:8]
    output.mkdir(parents=True, exist_ok=True)
    folder = output.resolve() / identifier
    folder.mkdir(mode=0o700)
    stopped = []
    try:
        deployment.compose("stop", "backend", "worker", timeout=120)
        stopped += ["backend", "worker"]
        inventory = deployment.application("app.cli.operations", "inventory", timeout=180)
        stream(
            deployment,
            deployment.command(
                "exec",
                "-T",
                "postgres",
                "pg_dump",
                "-U",
                deployment.cfg["POSTGRES_USER"],
                "-d",
                deployment.cfg["POSTGRES_DB"],
                "--format=custom",
                "--no-owner",
                "--no-privileges",
            ),
            destination=folder / "postgres.dump",
        )
        deployment.compose("stop", "qdrant", "minio", timeout=90)
        stopped += ["qdrant", "minio"]
        deployment.run(["docker", "image", "inspect", ARCHIVER], quiet=True, check=False)
        # Pull occurs explicitly here; never restore with an unknown utility image.
        deployment.run(["docker", "pull", ARCHIVER], timeout=120, quiet=True)
        for role in ["qdrant", "minio"]:
            stream(
                deployment, volume_command(deployment, role), destination=folder / (role + ".tgz")
            )
        manifest = {
            "format": "image-search-cold-backup-v1",
            "id": identifier,
            "source_project": deployment.project,
            "release": deployment.cfg["DEPLOY_RELEASE"],
            "inventory": inventory,
            "configuration": {
                key: deployment.cfg[key]
                for key in ["EMBEDDING_MODEL_ID", "EMBEDDING_MODEL_REVISION", "SEARCH_ENABLED"]
            },
            "minio_bucket": deployment.cfg["MINIO_BUCKET"],
            "storage_versions": {"postgres": "16.15", "qdrant": "1.20.0", "minio": "2025-09-07"},
            "files": {
                name: {"sha256": checksum(folder / name), "bytes": (folder / name).stat().st_size}
                for name in sorted(FILES)
            },
            "application_environment_secrets_included": False,
            "raw_storage_security_metadata_may_be_included": True,
            "encryption": "not_encrypted; private directory; operator must protect off-host copies",
        }
        with (folder / "manifest.json").open("x") as handle:
            json.dump(manifest, handle, indent=2)
        (folder / "manifest.json").chmod(0o600)
        validate_backup(folder)
    finally:
        if stopped:
            deployment.compose(
                "up",
                "-d",
                "--no-build",
                "--wait",
                "--wait-timeout",
                "60",
                "qdrant",
                "minio",
                timeout=90,
            )
            deployment.compose("start", "backend", "worker", timeout=90)
    from deploy import check

    for _ in range(60):
        try:
            check(deployment)
            break
        except Exception:
            time.sleep(1)
    else:
        raise RuntimeError("BACKUP_COMPLETE_BUT_APPLICATION_NOT_RECOVERED")
    print(json.dumps({"backup": str(folder), "status": "verified"}))
    return folder


def restore_deployment(deployment, folder):
    manifest = validate_backup(folder)
    if manifest["source_project"] == deployment.project:
        raise ValueError("RESTORE_IN_PLACE_NOT_ALLOWED_USE_NEW_PROJECT")
    if manifest["storage_versions"] != {
        "postgres": "16.15",
        "qdrant": "1.20.0",
        "minio": "2025-09-07",
    }:
        raise ValueError("BACKUP_STORAGE_VERSION_MISMATCH")
    if manifest["minio_bucket"] != deployment.cfg["MINIO_BUCKET"]:
        raise ValueError("BACKUP_BUCKET_MISMATCH")
    for key in ["EMBEDDING_MODEL_ID", "EMBEDDING_MODEL_REVISION"]:
        if manifest["configuration"][key] != deployment.cfg[key]:
            raise ValueError("BACKUP_MODEL_CONFIGURATION_MISMATCH")
    deployment.compose(
        "up",
        "-d",
        "--no-build",
        "--wait",
        "--wait-timeout",
        "120",
        "postgres",
        "qdrant",
        "minio",
        timeout=180,
    )
    deployment.application("app.cli.operations", "restore-guard")
    deployment.compose("stop", "qdrant", "minio", timeout=90)
    for role in ["qdrant", "minio"]:
        stream(
            deployment,
            volume_command(deployment, role, restore=True),
            source=folder / (role + ".tgz"),
        )
    stream(
        deployment,
        deployment.command(
            "exec",
            "-T",
            "postgres",
            "pg_restore",
            "-U",
            deployment.cfg["POSTGRES_USER"],
            "-d",
            deployment.cfg["POSTGRES_DB"],
            "--exit-on-error",
            "--no-owner",
            "--no-privileges",
        ),
        source=folder / "postgres.dump",
    )
    deployment.update(SEARCH_ENABLED=manifest["configuration"]["SEARCH_ENABLED"])
    from deploy import startup

    startup(deployment)
    verify_restored(deployment, manifest)


def verify_restored(deployment, manifest):
    from deploy import check

    check(deployment)
    actual = deployment.application("app.cli.operations", "inventory")
    before = manifest["inventory"]
    for snapshot in [actual, before]:
        snapshot["collections"].sort(key=lambda item: item["name"])
    for key in ["counts", "collections", "stored_objects", "active"]:
        if actual[key] != before[key]:
            raise RuntimeError("RESTORE_INVENTORY_MISMATCH")
    consistency = deployment.application("app.cli.operations", "verify-all", timeout=600)
    print(
        json.dumps(
            {"status": "restored", "inventory": actual, "consistency": consistency}, indent=2
        )
    )


def switch_release(deployment, release, rollback=False):
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}", release):
        raise ValueError("INVALID_RELEASE")
    path = ROOT / ".cache/deployment/releases" / (release + ".json")
    if not path.is_file():
        raise ValueError("RELEASE_MANIFEST_NOT_FOUND_BUILD_FIRST")
    manifest = json.loads(path.read_text())
    for component, identity in manifest["images"].items():
        result = deployment.run(
            ["docker", "image", "inspect", f"semantic-image-search/{component}:{release}"],
            quiet=True,
        )
        if json.loads(result.stdout)[0]["Id"] != identity:
            raise ValueError("RELEASE_IMAGE_ID_MISMATCH")
    if rollback:
        deployment.env["DEPLOY_RELEASE"] = release
        schema = deployment.compose(
            "run",
            "--rm",
            "--no-deps",
            "-T",
            "backend",
            "python",
            "-c",
            "from alembic.config import Config; from alembic.script import ScriptDirectory; "
            "print(ScriptDirectory.from_config(Config('backend/alembic.ini')).get_current_head())",
            quiet=True,
        ).stdout.strip()
        current = deployment.compose(
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            deployment.cfg["POSTGRES_USER"],
            "-d",
            deployment.cfg["POSTGRES_DB"],
            "-At",
            "-c",
            "SELECT version_num FROM alembic_version",
            quiet=True,
        ).stdout.strip()
        deployment.env["DEPLOY_RELEASE"] = deployment.cfg["DEPLOY_RELEASE"]
        if schema != current:
            raise ValueError("ROLLBACK_SCHEMA_INCOMPATIBLE_RESTORE_TO_NEW_PROJECT")
    backup_deployment(deployment, ROOT / "backups")
    deployment.update(DEPLOY_RELEASE=release)
    from deploy import startup

    startup(deployment)
