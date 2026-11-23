"""Chạy browser acceptance bằng read token riêng của deployment, không ghi token vào build."""

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from browser_environment import browser_environment  # noqa: E402
from deployment.common import ROOT, Deployment  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--indexed", action="store_true")
    parser.add_argument("--login-file", default=".cache/auth/deployment-admin-login.json")
    parser.add_argument("--project")
    args = parser.parse_args()
    d = Deployment(args.env_file)
    env = browser_environment(ROOT)
    env.update(
        DEPLOY_READ_TOKEN=d.cfg["API_TOKEN"],
        DEPLOY_BASE_URL="http://127.0.0.1:" + d.cfg["DEPLOY_HTTP_PORT"],
        DEPLOY_INDEXED="1" if args.indexed else "0",
    )
    if d.cfg.get("AUTH_LEGACY_TOKENS_ENABLED", "false") != "true":
        env["DEPLOY_LOGIN_FILE"] = str((ROOT / args.login_file).resolve())
    command = ["npm", "exec", "playwright", "--", "test", "--config", "playwright.deploy.config.ts"]
    if args.project:
        command += ["--project", args.project]
    result = subprocess.run(
        command, cwd=ROOT / "frontend", env=env, text=True, capture_output=True, timeout=240
    )
    folder = ROOT / "docs/verification/phase12"
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S_%f")
    name = f"browser_{'indexed' if args.indexed else 'empty'}_{stamp}"
    (folder / (name + ".log")).write_text(d.scrub(result.stdout + result.stderr))
    report = ROOT / "frontend/test-results/deployment.json"
    if report.is_file():
        (folder / (name + ".json")).write_text(d.scrub(report.read_text()))
    print(d.scrub(result.stdout + result.stderr))
    print(json.dumps({"exit_code": result.returncode, "artifact": name}))
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
