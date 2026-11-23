"""Run isolated real-service fixtures from host; no DB ports are published for this test."""

import argparse
import json
import os
import subprocess
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--llm", action="store_true", help="Also call configured real planning provider"
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    values = {k: v for k, v in dotenv_values(ROOT / ".env").items() if v is not None}
    env = {**os.environ, **values}

    def address(service):
        identity = subprocess.check_output(
            ["docker", "compose", "ps", "-q", service], cwd=ROOT, text=True
        ).strip()
        if not identity:
            raise RuntimeError("SERVICE_NOT_RUNNING")
        inspected = json.loads(subprocess.check_output(["docker", "inspect", identity], cwd=ROOT))
        networks = inspected[0]["NetworkSettings"]["Networks"]
        return next(v["IPAddress"] for k, v in networks.items() if k.endswith("_data"))

    env.update(
        DATABASE_URL=make_url(values["DATABASE_URL"])
        .set(host=address("postgres"), port=5432)
        .render_as_string(hide_password=False),
        QDRANT_URL="http://" + address("qdrant") + ":6333",
        MINIO_ENDPOINT=address("minio") + ":9000",
        DEBUG="false",
        EMBEDDING_CACHE_DIR=str(ROOT / ".cache/clip"),
        DATASET_ROOT=str(ROOT / "datasets"),
        RUN_AGENT_E2E="1",
        RUN_AGENT_LLM_FIXTURE="1" if args.llm else "0",
        AGENT_TEST_BASE_URL="http://127.0.0.1:8000",
        AGENT_FIXTURE_REPORT=str((output / "fixture.json").resolve()),
    )
    result = subprocess.run(
        [
            str(ROOT / "backend/.venv/bin/python"),
            "-m",
            "pytest",
            "backend/tests/integration/test_real_agent.py",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    log = result.stdout + "\n" + result.stderr
    for key, value in env.items():
        if (
            any(k in key for k in ["KEY", "TOKEN", "SECRET", "PASSWORD", "DATABASE_URL"])
            and len(value) >= 12
        ):
            log = log.replace(value, "[REDACTED]")
    (output / "tests.txt").write_text(log)
    (output / "summary.json").write_text(
        json.dumps(
            {
                "status": "pass" if result.returncode == 0 else "failed",
                "llm_requested": args.llm,
                "classification": "fictional knowledge on actual PostgreSQL/Qdrant/MinIO/CLIP",
            },
            indent=2,
        )
        + "\n"
    )
    print(log[-18000:])
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
