"""Run bounded, isolated quality profiles; never load the serving .env."""

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from browser_environment import browser_environment
from qa_tools.init_qa_env import initialize

ROOT = Path(__file__).resolve().parents[1]


def configuration():
    path = initialize(ROOT)
    values = dict(
        line.split("=", 1)
        for line in path.read_text().splitlines()
        if line and not line.startswith("#")
    )
    if (
        not re.fullmatch(r"phase11-qa-[0-9a-f]{12}", values.get("QA_PROJECT_NAME", ""))
        or values.get("APP_ENV") != "test"
        or "@qa-postgres:5432/image_search_qa" not in values.get("DATABASE_URL", "")
        or values.get("QDRANT_URL") != "http://qa-qdrant:6333"
        or values.get("MINIO_ENDPOINT") != "qa-minio:9000"
    ):
        raise SystemExit("Refusing an unrecognized/non-isolated QA environment")
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "profile",
        choices=[
            "init",
            "up",
            "fast",
            "frontend",
            "services",
            "seed",
            "ai",
            "browser",
            "mock-browser",
            "faults",
            "status",
            "down",
        ],
    )
    parser.add_argument(
        "--with-model",
        action="store_true",
        help="Use locally cached real CLIP; never download weights automatically",
    )
    args = parser.parse_args()
    cfg = configuration()
    env = os.environ.copy()
    for key in [*cfg, "COMPOSE_PROJECT_NAME", "COMPOSE_FILE", "GEMINI_API_KEY", "RAG_API_KEY"]:
        env.pop(key, None)
    env["PATH"] = str(ROOT / ".tools/node/bin") + os.pathsep + env["PATH"]
    if args.with_model:
        env["QA_INSTALL_ML"] = "true"
    compose = [
        "docker",
        "compose",
        "--env-file",
        ".env.qa",
        "-f",
        "compose.qa.yaml",
        "-p",
        cfg["QA_PROJECT_NAME"],
    ]
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S_%f")
    artifact = ROOT / "docs/verification/phase11/runs" / f"{stamp}_{args.profile}"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    commands = []

    def run(command, timeout=300, *, docker=False):
        if docker and os.getenv("QA_USE_SG") == "1":
            command = ["sg", "docker", "-c", shlex.join(command)]
        started = datetime.now(UTC).isoformat()
        try:
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                check=False,
            )
            code, output = result.returncode, result.stdout
        except subprocess.TimeoutExpired as error:
            code, output = 124, error.stdout or ""
            if isinstance(output, bytes):
                output = output.decode(errors="replace")
            output += "\nQA_RUNNER_DEADLINE_EXCEEDED\n"
        for key, value in cfg.items():
            if len(value) >= 12 and any(
                part in key for part in ["TOKEN", "KEY", "PASSWORD", "SECRET"]
            ):
                output = output.replace(value, "[REDACTED_QA_SECRET]")
        with artifact.with_suffix(".log").open("a") as handle:
            handle.write(output)
        print(output, end="", flush=True)
        commands.append({"command": command, "started_utc": started, "exit_code": code})
        artifact.with_suffix(".json").write_text(
            json.dumps(
                {
                    "profile": args.profile,
                    "classification": "isolated_qa",
                    "project": cfg["QA_PROJECT_NAME"],
                    "commands": commands,
                    "status": "passed"
                    if all(row["exit_code"] == 0 for row in commands)
                    else "failed",
                },
                indent=2,
            )
            + "\n"
        )
        if code:
            raise SystemExit(code)

    def test_command(paths, flags=()):
        return compose + [
            "--profile",
            "tools",
            "run",
            "--rm",
            "--no-deps",
            "-T",
            *flags,
            "qa-tests",
            "timeout",
            "240",
            "pytest",
            *paths,
            "-q",
            "-p",
            "no:cacheprovider",
        ]

    if args.profile == "init":
        print("QA credentials initialized separately; no serving configuration loaded.")
    elif args.profile == "up":
        run(compose + ["config", "--quiet"], docker=True)
        run(
            compose
            + ["up", "-d", "--build", "--wait", "--wait-timeout", "180", "qa-api", "qa-frontend"],
            900,
            docker=True,
        )
    elif args.profile == "fast":
        run(
            test_command(
                ["backend/tests/unit", "backend/tests/security", "backend/tests/reliability"]
            ),
            docker=True,
        )
    elif args.profile == "frontend":
        for check in ["typecheck", "lint", "test", "build"]:
            run(["npm", "--prefix", "frontend", "run", check], 180)
    elif args.profile == "services":
        run(
            test_command(
                [
                    "backend/tests/integration/test_real_services.py",
                    "backend/tests/integration/test_qa_services.py",
                    "backend/tests/integration/test_qa_worker_process.py",
                    "backend/tests/integration/test_access_control.py",
                    "backend/tests/integration/test_quick_login.py",
                    "backend/tests/integration/test_registration.py",
                    "backend/tests/integration/test_shared_datasets.py",
                    "backend/tests/integration/test_guest_search.py",
                ],
                ["-e", "RUN_INTEGRATION=1"],
            ),
            docker=True,
        )
    elif args.profile == "seed":
        run(
            compose
            + [
                "--profile",
                "tools",
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "qa-tests",
                "python",
                "scripts/qa_tools/seed_qa.py",
            ],
            docker=True,
        )
        env.update(QA_SEARCH_ENABLED="true", QA_AGENT_ENABLED="true")
        run(
            compose + ["up", "-d", "--no-deps", "--wait", "--wait-timeout", "180", "qa-api"],
            docker=True,
        )
    elif args.profile == "ai":
        run(
            test_command(["backend/tests/integration/test_qa_ai.py"], ["-e", "RUN_QA_AI=1"]),
            docker=True,
        )
    elif args.profile in {"browser", "mock-browser"}:
        env = browser_environment(ROOT, env)
        env["QA_API_TOKEN"] = cfg["API_TOKEN"]
        env["PLAYWRIGHT_BROWSERS_PATH"] = str(ROOT / ".cache/playwright")
        config = (
            "tests/e2e/config/qa.config.ts"
            if args.profile == "browser"
            else "tests/e2e/config/mock.config.ts"
        )
        command = [
            "npm",
            "--prefix",
            "frontend",
            "exec",
            "--",
            "playwright",
            "test",
            "--config",
            f"frontend/{config}",
        ]
        if env.get("QA_BROWSER_PROJECT"):
            command.append("--project=" + env["QA_BROWSER_PROJECT"])
        run(command, 300)
    elif args.profile == "faults":
        run([sys.executable, "scripts/qa_tools/qa_faults.py"], 300)
    elif args.profile == "status":
        run(compose + ["ps"], docker=True)
    elif args.profile == "down":
        run(compose + ["down", "--volumes", "--timeout", "30"], docker=True)


if __name__ == "__main__":
    main()
