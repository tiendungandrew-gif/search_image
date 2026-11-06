#!/usr/bin/env python3
"""Nghiệm thu Docker thật: health, tests, persistence và phục hồi dependency outage."""

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
SERVICES = {"backend", "frontend", "postgres", "qdrant", "minio"}

MARKERS = r"""
import asyncio, io, sys
from uuid import UUID
from sqlalchemy import text
from app.core.config import Settings
from app.services.health import Services
action, identifier = sys.argv[1], UUID(sys.argv[2]).hex
schema = 'foundation_acceptance_' + identifier
key = 'verification/' + identifier + '.txt'
async def main():
    services = Services(Settings())
    try:
        if action == 'create':
            async with services.database.engine.begin() as conn:
                await conn.execute(text('CREATE SCHEMA ' + schema))
                await conn.execute(text('CREATE TABLE ' + schema + '.marker (value text NOT NULL)'))
                await conn.execute(text('INSERT INTO ' + schema + '.marker VALUES (:value)'),
                                   {'value': identifier})
            await services.minio.run(lambda: services.minio.client.put_object(
                services.minio.bucket, key, io.BytesIO(identifier.encode()), len(identifier),
                content_type='text/plain'))
        elif action == 'verify':
            async with services.database.engine.connect() as conn:
                value = (await conn.execute(text('SELECT value FROM ' + schema + '.marker')))
                assert value.scalar_one() == identifier
            def read_object():
                response = services.minio.client.get_object(services.minio.bucket, key)
                try:
                    assert response.read().decode() == identifier
                finally:
                    response.close(); response.release_conn()
            await services.minio.run(read_object)
        elif action == 'clean':
            async with services.database.engine.begin() as conn:
                await conn.execute(text('DROP TABLE IF EXISTS ' + schema + '.marker'))
                await conn.execute(text('DROP SCHEMA IF EXISTS ' + schema))
            await services.minio.run(lambda: services.minio.client.remove_object(
                services.minio.bucket, key))
        else:
            raise ValueError('unknown marker action')
    finally:
        await services.close()
asyncio.run(main())
"""


def run(*args: str, label: str, capture: bool = False, timeout: int = 1800) -> str:
    print(f"[RUN] {label}", flush=True)
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=capture, timeout=timeout)
    if result.returncode:
        # Không in inspect/config/env hoặc response chứa thông tin cấu hình.
        raise RuntimeError(f"{label} thất bại (exit {result.returncode})")
    return result.stdout if capture else ""


def compose(*args: str, label: str, capture: bool = False) -> str:
    return run("docker", "compose", *args, label=label, capture=capture)


def states() -> list[dict]:
    raw = compose(
        "ps", "--all", "--format", "json", label="Đọc trạng thái containers", capture=True
    )
    if raw.lstrip().startswith("["):
        rows = json.loads(raw)
    else:
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if not SERVICES.issubset({row["Service"] for row in rows}):
        raise RuntimeError("Không đủ năm foundation services của project")
    rows = [row for row in rows if row["Service"] in SERVICES]
    if any(row.get("State") != "running" or row.get("Health") != "healthy" for row in rows):
        raise RuntimeError("Có container chưa running/healthy")
    return [{key: row.get(key) for key in ("Service", "State", "Health")} for row in rows]


def volume_names() -> dict[str, str]:
    output = {}
    for service, destination in (
        ("postgres", "/var/lib/postgresql/data"),
        ("qdrant", "/qdrant/storage"),
        ("minio", "/data"),
    ):
        container = compose("ps", "-q", service, label=f"ID {service}", capture=True).strip()
        mounts = json.loads(
            run(
                "docker",
                "inspect",
                "--format",
                "{{json .Mounts}}",
                container,
                label=f"Volume mount {service}",
                capture=True,
            )
        )
        match = next(m for m in mounts if m["Destination"] == destination)
        if match["Type"] != "volume" or not match.get("Name"):
            raise RuntimeError(f"{service} không dùng named persistent volume")
        output[service] = match["Name"]
    return output


def request(path: str, token: str = "") -> tuple[int, dict]:
    headers = {"Authorization": "Bearer " + token} if token else {}
    req = urllib.request.Request("http://127.0.0.1:8000/api/v1" + path, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code, json.load(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--output", default="docs/verification/docker.json")
    args = parser.parse_args()
    result: dict = {"status": "running", "build_requested": not args.skip_build, "checks": {}}
    output = ROOT / args.output
    identifier = str(uuid4())
    marker_started = False
    checks = result["checks"]
    try:
        token = next(
            line.split("=", 1)[1]
            for line in (ROOT / ".env").read_text().splitlines()
            if line.startswith("API_TOKEN=")
        )
        compose("config", "--quiet", label="Compose config")
        up = ["up", "-d", "--wait", "--wait-timeout", "180"]
        if not args.skip_build:
            up.append("--build")
        compose(*up, label="Build/start năm services")
        result["services"] = states()
        run(sys.executable, "scripts/verify_services.py", label="HTTP/OpenAPI/UI/proxy smoke")
        checks["http_smoke"] = "pass"
        for label, service, command in [
            ("backend unit", "backend", ["pytest", "backend/tests/unit", "-p", "no:cacheprovider"]),
            ("Python lint", "backend", ["ruff", "check", "backend", "scripts"]),
            ("Python format", "backend", ["ruff", "format", "--check", "backend", "scripts"]),
            ("TypeScript", "frontend", ["npm", "run", "typecheck"]),
            ("ESLint", "frontend", ["npm", "run", "lint"]),
            ("frontend unit", "frontend", ["npm", "test"]),
            ("frontend build", "frontend", ["npm", "run", "build"]),
        ]:
            compose("exec", "-T", service, *command, label=label)
            checks[label] = "pass"
        compose(
            "exec",
            "-T",
            "-e",
            "RUN_INTEGRATION=1",
            "backend",
            "pytest",
            "backend/tests/integration",
            "-p",
            "no:cacheprovider",
            label="Real integration/migrations",
        )
        checks["integration"] = "pass"
        before = volume_names()
        marker_started = True
        compose(
            "exec",
            "-T",
            "backend",
            "python",
            "-c",
            MARKERS,
            "create",
            identifier,
            label="Tạo PG/object persistence markers riêng",
        )
        marker_path = "/qdrant/storage/.foundation_acceptance_" + identifier
        compose(
            "exec",
            "-T",
            "qdrant",
            "/bin/bash",
            "-ec",
            'printf %s "$1" > "$2"',
            "marker",
            identifier,
            marker_path,
            label="Qdrant volume marker, không tạo vectors",
        )
        compose(
            "up",
            "-d",
            "--force-recreate",
            "--wait",
            "--wait-timeout",
            "180",
            label="Recreate containers, giữ volumes",
        )
        if volume_names() != before:
            raise RuntimeError("Tên persistent volumes thay đổi sau recreation")
        compose(
            "exec",
            "-T",
            "backend",
            "python",
            "-c",
            MARKERS,
            "verify",
            identifier,
            label="Verify database/object markers còn nguyên",
        )
        compose(
            "exec",
            "-T",
            "qdrant",
            "/bin/bash",
            "-ec",
            '[[ "$(cat "$2")" == "$1" ]]',
            "marker",
            identifier,
            marker_path,
            label="Verify Qdrant file marker",
        )
        checks["volume_persistence"] = "pass"
        for service, key in (("postgres", "postgresql"), ("qdrant", "qdrant"), ("minio", "minio")):
            try:
                compose("stop", service, label=f"Outage test {service}")
                if request("/health/live")[0] != 200:
                    raise RuntimeError("Liveness phụ thuộc data service")
                status, body = request("/health/ready", token)
                if status != 503 or body["dependencies"][key] not in {"unhealthy", "timeout"}:
                    raise RuntimeError(f"Readiness không phản ánh {service} outage")
            finally:
                compose(
                    "up",
                    "-d",
                    "--wait",
                    "--wait-timeout",
                    "180",
                    service,
                    label=f"Restore {service}",
                )
            run(sys.executable, "scripts/verify_services.py", label=f"HTTP sau restore {service}")
            checks[f"outage_{service}"] = "pass"
        result["services"] = states()
        result["volumes"] = before
        result["status"] = "pass"
    except Exception as exc:
        result["status"] = "failed"
        result["failure_type"] = type(exc).__name__
        print("[FAIL] Nghiệm thu chưa hoàn tất; xem bước thất bại ở trên.", flush=True)
    finally:
        if marker_started:
            try:
                compose(
                    "exec",
                    "-T",
                    "backend",
                    "python",
                    "-c",
                    MARKERS,
                    "clean",
                    identifier,
                    label="Dọn đúng PG/object markers của lượt test",
                )
                compose(
                    "exec",
                    "-T",
                    "qdrant",
                    "/bin/bash",
                    "-ec",
                    'rm -f -- "$1"',
                    "marker",
                    "/qdrant/storage/.foundation_acceptance_" + identifier,
                    label="Dọn đúng Qdrant marker của lượt test",
                )
                checks["marker_cleanup"] = "pass"
            except Exception:
                result["status"] = "failed"
                checks["marker_cleanup"] = "failed"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Kết quả: {result['status']}; report: {output.relative_to(ROOT)}", flush=True)
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
