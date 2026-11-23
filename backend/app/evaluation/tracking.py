import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def hardware_manifest():
    cpu = next(
        (
            line.split(":", 1)[1].strip()
            for line in Path("/proc/cpuinfo").read_text().splitlines()
            if line.startswith("model name")
        ),
        None,
    )
    ram = next(
        (
            int(line.split()[1])
            for line in Path("/proc/meminfo").read_text().splitlines()
            if line.startswith("MemTotal:")
        ),
        None,
    )
    versions = {}
    for name in ["numpy", "torch", "transformers", "httpx", "qdrant-client", "matplotlib"]:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return {
        "cpu": cpu,
        "logical_cpus": os.cpu_count(),
        "total_ram_kib": ram,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "packages": versions,
    }


def source_snapshot(root=None, archive_root=None):
    root = Path.cwd() if root is None else root
    excluded = {
        ".venv",
        "node_modules",
        "__pycache__",
        "dist",
        "test-results",
        "playwright-report",
        ".pytest_cache",
        ".ruff_cache",
    }
    paths = [
        p
        for name in [
            "backend",
            "scripts",
            "frontend",
            "workers",
            "infra",
            ".github",
            "evaluation/scripts",
            "evaluation/experiments",
            "evaluation/annotation",
            "evaluation/agent",
        ]
        for p in (root / name).rglob("*")
        if p.is_file()
        and not excluded.intersection(p.parts)
        and p.suffix not in {".pyc", ".log"}
        and (not p.name.startswith(".env") or p.name == ".env.example")
    ]
    paths.extend(
        root / name
        for name in [
            "compose.yaml",
            "compose.host.yaml",
            "compose.qa.yaml",
            "compose.prod.yaml",
            "compose.tls.yaml",
            ".env.deploy.example",
            "Makefile",
            ".env.example",
            ".gitignore",
            ".dockerignore",
            "ruff.toml",
        ]
        if (root / name).is_file()
    )
    h = hashlib.sha256()
    for p in sorted(set(paths)):
        h.update(p.relative_to(root).as_posix().encode() + b"\0" + p.read_bytes() + b"\0")
    archive = None
    if archive_root is not None:
        destination = Path(archive_root) / "_sources"
        destination.mkdir(parents=True, exist_ok=True)
        archive = destination / (h.hexdigest() + ".tar.gz")
        if not archive.exists():
            with tarfile.open(archive, "x:gz") as bundle:
                for path in sorted(set(paths)):
                    bundle.add(path, arcname=path.relative_to(root).as_posix(), recursive=False)
    return {
        "sha256": h.hexdigest(),
        "files": len(set(paths)),
        "archive": str(archive) if archive is not None else None,
        "scope": (
            "backend/frontend/scripts/workers/infra/evaluation source and locks; "
            "excludes results/caches/private env"
        ),
    }


class Experiment:
    def __init__(self, root, kind, config, provenance=None):
        self.identifier = (
            datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "_" + kind + "_" + uuid4().hex[:10]
        )
        self.directory = Path(root) / self.identifier
        self.directory.mkdir(parents=True, exist_ok=False)
        try:
            git = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
            commit = git.stdout.strip() if git.returncode == 0 else None
            git_status = "available" if commit else "no_commit"
        except FileNotFoundError:
            commit = None
            git_status = "git_not_installed"
        self.write(
            "experiment.json",
            {
                "experiment_id": self.identifier,
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "kind": kind,
                "config": config,
                "git_commit": commit,
                "git_status": git_status,
                "source": source_snapshot(archive_root=root),
                "client_platform": platform.platform(),
                "client_python": platform.python_version(),
                "client_hardware": hardware_manifest(),
                "provenance": provenance or {},
            },
        )

    def write(self, name, value):
        if Path(name).name != name:
            raise ValueError("artifact_name_required")
        encoded = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        with (self.directory / name).open("x") as handle:
            handle.write(encoded)

    def complete(self, value):
        self.write("result.json", value)
        return self.directory
