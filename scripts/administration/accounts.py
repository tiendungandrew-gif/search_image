#!/usr/bin/env python3
"""Private account bootstrap/recovery. Password travels on stdin, never argv or logs."""

import argparse
import json
import os
import secrets
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from deployment.common import read_env  # noqa: E402
from environment_paths import resolve_env_file  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["bootstrap", "reset"])
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--display-name", default="Quản trị viên")
    parser.add_argument("--output", default=".cache/auth/admin-login.json")
    args = parser.parse_args()
    path = resolve_env_file(Path(args.env_file))
    cfg = read_env(path)
    if "DEPLOY_PROJECT_NAME" in cfg:
        compose, project, service = "compose.prod.yaml", cfg["DEPLOY_PROJECT_NAME"], "backend"
        url = f"http://127.0.0.1:{cfg['DEPLOY_HTTP_PORT']}"
    elif "QA_PROJECT_NAME" in cfg:
        compose, project, service = "compose.qa.yaml", cfg["QA_PROJECT_NAME"], "qa-api"
        url = f"http://127.0.0.1:{cfg.get('QA_FRONTEND_PORT', '5175')}"
    elif path == ROOT / ".env":
        compose, project, service = "compose.yaml", "ai-image-search", "backend"
        url = "http://localhost:5173"
    else:
        raise ValueError("Unrecognized account environment")
    output = (ROOT / args.output).resolve()
    if not output.is_relative_to(ROOT / ".cache/auth"):
        raise ValueError("Credential output must be inside .cache/auth")
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    output.parent.chmod(0o700)
    # Reserve the path before changing an account; never overwrite an existing password file.
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    password = secrets.token_urlsafe(24)
    cmd = [
        "docker",
        "compose",
        "--env-file",
        str(path),
        "-f",
        str(ROOT / compose),
        "-p",
        project,
        "exec",
        "-T",
        service,
        "python",
        "-m",
        "app.cli.accounts",
        args.action,
        "--username",
        args.username,
        "--display-name",
        args.display_name,
    ]
    if os.getenv("ACCOUNTS_USE_SG") == "1":
        cmd = ["sg", "docker", "-c", shlex.join(cmd)]
    try:
        env = os.environ.copy()
        env.update(cfg, DEPLOY_ENV_FILE=str(path), QA_ENV_FILE=str(path))
        result = subprocess.run(
            cmd,
            input=password + "\n",
            text=True,
            capture_output=True,
            timeout=60,
            cwd=ROOT,
            env=env,
        )
        if result.returncode:
            raise RuntimeError(
                "Account command failed; credential file kept for recovery. "
                "Check application availability."
            )
        info = json.loads(result.stdout)
        if info.get("status") == "already_configured":
            os.close(descriptor)
            output.unlink()
            print("An admin already exists. No password changed. Use explicit reset for recovery.")
            return
        with os.fdopen(descriptor, "w") as handle:
            json.dump(
                {
                    "url": url,
                    "username": args.username.lower(),
                    "password": password,
                    "project": project,
                },
                handle,
                ensure_ascii=False,
                indent=2,
            )
            handle.write("\n")
        print("Account ready. Private login file: " + str(output))
    except BaseException:
        # Keep generated credentials if a successful operation had an interrupted response.
        try:
            with os.fdopen(descriptor, "w") as handle:
                json.dump(
                    {
                        "username": args.username.lower(),
                        "password": password,
                        "status": "operation_uncertain",
                    },
                    handle,
                )
        except OSError:
            pass
        raise


if __name__ == "__main__":
    main()
