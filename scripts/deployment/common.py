"""Cấu hình riêng, lệnh Compose có deadline và logs không chứa secrets."""

import fcntl
import json
import os
import re
import secrets
import shlex
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

from environment_paths import is_protected_environment, resolve_env_file

ROOT = Path(__file__).resolve().parents[2]


def read_env(path):
    values = {}
    for line in resolve_env_file(path).read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise ValueError("INVALID_ENV_KEY")
        if key in values:
            raise ValueError("DUPLICATE_ENV_KEY")
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            value = json.loads(value)
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        if not isinstance(value, str):
            raise ValueError("INVALID_ENV_VALUE")
        values[key] = value
    return values


def write_env(path, values, *, new=False):
    path = Path(path)
    if any("\n" in str(value) or "\r" in str(value) for value in values.values()):
        raise ValueError("INVALID_ENV_NEWLINE")
    encoded = "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"
    if new:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as handle:
            handle.write(encoded)
    else:
        temporary = path.with_name(path.name + ".tmp-" + secrets.token_hex(4))
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as handle:
            handle.write(encoded)
        temporary.replace(path)


def initialize(
    path, project, port, model_path, dataset_path, release="phase12-local", install_ml=True
):
    if is_protected_environment(path):
        raise ValueError("SERVING_OR_QA_ENV_IS_NOT_A_DEPLOYMENT_ENV")
    path = resolve_env_file(path)
    if path.exists():
        raise ValueError("ENV_ALREADY_EXISTS")
    values = read_env(ROOT / ".env.example")
    password = secrets.token_hex(24)
    values.update(
        APP_ENV="production",
        DEBUG="false",
        MINIO_AUTO_CREATE_BUCKET="false",
        POSTGRES_PASSWORD=password,
        DATABASE_URL=f"postgresql+psycopg://image_search:{password}@postgres:5432/image_search",
        QDRANT_API_KEY=secrets.token_hex(24),
        MINIO_ACCESS_KEY="deploy" + secrets.token_hex(10),
        MINIO_SECRET_KEY=secrets.token_hex(24),
        API_TOKEN=secrets.token_hex(24),
        WRITE_API_TOKEN=secrets.token_hex(24),
        CORS_ORIGINS=json.dumps([f"http://127.0.0.1:{port}", f"http://localhost:{port}"]),
        REQUEST_TIMEOUT_SECONDS="5",
        DEPENDENCY_TIMEOUT_SECONDS="3",
        LOG_LEVEL="INFO",
        EMBEDDING_DEVICE="cpu",
        EVALUATION_RESULTS_DIR="/evaluation/results",
        DEPLOY_PROJECT_NAME=project,
        DEPLOY_RELEASE=release,
        DEPLOY_HTTP_PORT=str(port),
        DEPLOY_BIND_ADDRESS="127.0.0.1",
        DEPLOY_MODEL_PATH=str(model_path.resolve()),
        DEPLOY_DATASET_PATH=str(dataset_path.resolve()),
        DEPLOY_INSTALL_ML="true" if install_ml else "false",
        DEPLOY_NO_NEW_PRIVILEGES="true",
    )
    validate(values)
    model_path.mkdir(parents=True, exist_ok=True)
    dataset_path.mkdir(parents=True, exist_ok=True)
    write_env(path, values, new=True)


def validate(cfg):
    if not re.fullmatch(
        r"image-search-[a-z0-9][a-z0-9_-]{2,50}", cfg.get("DEPLOY_PROJECT_NAME", "")
    ):
        raise ValueError("UNRECOGNIZED_DEPLOY_PROJECT")
    if cfg.get("APP_ENV") != "production" or cfg.get("DEBUG") != "false":
        raise ValueError("PRODUCTION_SETTINGS_REQUIRED")
    if cfg.get("MINIO_AUTO_CREATE_BUCKET") != "false":
        raise ValueError("USE_EXPLICIT_BOOTSTRAP")
    for key in ["SEARCH_ENABLED", "RAG_ENABLED", "AGENT_ENABLED"]:
        if cfg.get(key) not in {"true", "false"}:
            raise ValueError("INVALID_FEATURE_FLAG")
    if cfg.get("AGENT_ALLOW_FIXTURE_KNOWLEDGE") != "false":
        raise ValueError("FIXTURE_KNOWLEDGE_NOT_ALLOWED")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}", cfg.get("DEPLOY_RELEASE", "")):
        raise ValueError("INVALID_RELEASE")
    for key in [
        "POSTGRES_PASSWORD",
        "QDRANT_API_KEY",
        "MINIO_SECRET_KEY",
        "API_TOKEN",
        "WRITE_API_TOKEN",
    ]:
        if len(cfg.get(key, "")) < 24:
            raise ValueError("MISSING_DEPLOY_SECRET")
    if cfg.get("API_TOKEN") == cfg.get("WRITE_API_TOKEN"):
        raise ValueError("DISTINCT_READ_WRITE_TOKENS_REQUIRED")
    if not 1024 <= int(cfg.get("DEPLOY_HTTP_PORT", "0")) <= 65535:
        raise ValueError("INVALID_HTTP_PORT")
    if cfg.get("DEPLOY_BIND_ADDRESS") != "127.0.0.1" and not cfg.get("DEPLOY_PUBLIC_HOST"):
        raise ValueError("PUBLIC_BIND_REQUIRES_EXPLICIT_HOST_AND_TLS_CONFIGURATION")
    if cfg.get("QDRANT_URL") != "http://qdrant:6333" or cfg.get("MINIO_ENDPOINT") != "minio:9000":
        raise ValueError("DEPLOY_DATA_ENDPOINTS_MUST_BE_INTERNAL")
    database = urlsplit(cfg.get("DATABASE_URL", ""))
    if (
        database.scheme != "postgresql+psycopg"
        or database.hostname != "postgres"
        or database.port != 5432
        or database.path != "/" + cfg["POSTGRES_DB"]
        or unquote(database.username or "") != cfg["POSTGRES_USER"]
        or unquote(database.password or "") != cfg["POSTGRES_PASSWORD"]
    ):
        raise ValueError("DEPLOY_DATABASE_MUST_MATCH_INTERNAL_POSTGRES")


class Deployment:
    def __init__(self, path, evidence=None, tls=False):
        if is_protected_environment(path):
            raise ValueError("SERVING_OR_QA_ENV_IS_NOT_A_DEPLOYMENT_ENV")
        self.path = resolve_env_file(path)
        self.cfg = read_env(self.path)
        validate(self.cfg)
        if self.path.stat().st_mode & 0o077:
            raise ValueError("DEPLOY_ENV_MUST_HAVE_MODE_0600")
        self.tls = tls
        if self.cfg.get("DEPLOY_BIND_ADDRESS") != "127.0.0.1" and not tls:
            raise ValueError("PUBLIC_BIND_REQUIRES_TLS")
        self.project = self.cfg["DEPLOY_PROJECT_NAME"]
        self.env = os.environ.copy()
        prefixes = (
            "AUTH_",
            "USER_",
            "APP_",
            "API_",
            "WRITE_",
            "RAG_",
            "AGENT_",
            "SEARCH_",
            "EMBEDDING_",
            "DEPLOY_",
            "DATABASE_",
            "POSTGRES_",
            "MINIO_",
            "QDRANT_",
            "VITE_",
            "CORS_",
            "COMPOSE_",
        )
        for key in list(self.env):
            if key.startswith(prefixes) or key in {"GEMINI_API_KEY", "OPENAI_API_KEY", "DEBUG"}:
                self.env.pop(key)
        self.env.update(self.cfg, DEPLOY_ENV_FILE=str(self.path))
        self.evidence = Path(evidence or ROOT / ".cache/deployment/logs")
        self.evidence.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S_%f")
        self.artifact = self.evidence / (stamp + "_" + self.project)
        self.records = []

    def acquire_lock(self):
        folder = ROOT / ".cache/deployment/locks"
        folder.mkdir(parents=True, exist_ok=True)
        self.lock_handle = (folder / (self.project + ".lock")).open("a")
        (folder / (self.project + ".lock")).chmod(0o600)
        try:
            fcntl.flock(self.lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("DEPLOYMENT_OPERATION_ALREADY_RUNNING") from None

    def command(self, *arguments):
        command = [
            "docker",
            "compose",
            "--env-file",
            str(self.path),
            "-f",
            str(ROOT / "compose.prod.yaml"),
        ]
        if self.tls:
            command += ["-f", str(ROOT / "compose.tls.yaml")]
        return command + ["-p", self.project, *arguments]

    def docker_command(self, arguments):
        if os.getenv("DEPLOY_USE_SG") == "1":
            return ["sg", "docker", "-c", shlex.join(arguments)]
        return arguments

    def scrub(self, output):
        for key, value in self.cfg.items():
            if len(value) >= 12 and any(
                term in key for term in ["TOKEN", "KEY", "PASSWORD", "SECRET"]
            ):
                output = output.replace(value, "[REDACTED_DEPLOY_SECRET]")
        return output

    def run(self, arguments, timeout=180, *, quiet=False, check=True, docker=True):
        command = self.docker_command(arguments) if docker else arguments
        started = time.monotonic()
        try:
            result = subprocess.run(
                command, cwd=ROOT, env=self.env, text=True, capture_output=True, timeout=timeout
            )
        except subprocess.TimeoutExpired as error:
            self.record(command, 124, "OPERATION_DEADLINE_EXCEEDED", time.monotonic() - started)
            raise RuntimeError("OPERATION_DEADLINE_EXCEEDED") from error
        safe = self.scrub(result.stdout + result.stderr)
        self.record(command, result.returncode, safe, time.monotonic() - started)
        if not quiet:
            print(safe, end="", flush=True)
        if check and result.returncode:
            raise RuntimeError("COMMAND_FAILED_SEE_OPERATION_LOG")
        return result

    def record(self, command, code, output, elapsed):
        self.records.append({"command": command, "exit_code": code, "elapsed_seconds": elapsed})
        with self.artifact.with_suffix(".log").open("a") as handle:
            handle.write(output + "\n")
        self.artifact.with_suffix(".log").chmod(0o600)
        self.artifact.with_suffix(".json").write_text(
            json.dumps({"project": self.project, "commands": self.records}, indent=2) + "\n"
        )

    def compose(self, *arguments, **kwargs):
        return self.run(self.command(*arguments), **kwargs)

    def application(self, *arguments, **kwargs):
        result = self.compose(
            "run",
            "--rm",
            "--no-deps",
            "-T",
            "backend",
            "python",
            "-m",
            *arguments,
            quiet=True,
            **kwargs,
        )
        return json.loads(result.stdout)

    def update(self, **values):
        candidate = self.cfg | {key: str(value) for key, value in values.items()}
        validate(candidate)
        write_env(self.path, candidate)
        self.cfg = candidate
        self.env.update(candidate)
