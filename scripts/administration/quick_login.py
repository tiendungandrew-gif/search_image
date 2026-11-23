#!/usr/bin/env python3
"""Enable/disable one-click role login in the local development stack."""

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from deployment.common import read_env  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["enable", "disable"])
    args = parser.parse_args()
    path = ROOT / ".env"
    cfg = read_env(path)
    if cfg.get("APP_ENV", "development") != "development":
        parser.error("This helper only operates on the main development .env")
    command = ["docker", "compose", "--env-file", str(path)]
    env = os.environ.copy()
    for key in set(cfg) | {"COMPOSE_FILE", "COMPOSE_PROJECT_NAME"}:
        env.pop(key, None)

    def run(*arguments, timeout=90):
        argv = command + list(arguments)
        if os.getenv("ACCOUNTS_USE_SG") == "1":
            argv = ["sg", "docker", "-c", shlex.join(argv)]
        result = subprocess.run(
            argv, cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode:
            raise RuntimeError(
                "Quick login setup failed; check migration and bootstrap Admin first."
            )
        return result.stdout

    # Provisioning collision checks happen before enabling access. Disable revokes old sessions.
    result = json.loads(
        run("exec", "-T", "backend", "python", "-m", "app.cli.quick_login", args.action)
    )
    flag = "AUTH_QUICK_LOGIN_ENABLED"
    lines = path.read_text().splitlines()
    lines = [line for line in lines if not line.startswith(flag + "=")]
    lines.append(flag + "=" + ("true" if args.action == "enable" else "false"))
    temporary = path.with_name(".env.quick-login.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as handle:
        handle.write("\n".join(lines) + "\n")
    temporary.replace(path)
    run(
        "up",
        "-d",
        "--no-build",
        "--no-deps",
        "--force-recreate",
        "--wait",
        "--wait-timeout",
        "180",
        "backend",
        timeout=240,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "url": "http://localhost:5173",
                "roles": [a["role"] for a in result["accounts"]],
            }
        )
    )


if __name__ == "__main__":
    main()
