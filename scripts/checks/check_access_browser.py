"""Run real account browser acceptance; credentials are read from a private file."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from browser_environment import browser_environment  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:5175")
    parser.add_argument("--login-file", default=".cache/auth/qa-admin-login.json")
    parser.add_argument("--indexed", action="store_true")
    parser.add_argument("--project")
    args = parser.parse_args()
    if args.base_url not in {"http://127.0.0.1:5175", "http://localhost:5175"}:
        parser.error("Account mutation browser tests require the isolated QA origin on port 5175")
    env = browser_environment(ROOT, os.environ.copy())
    env.update(
        ACCESS_BASE_URL=args.base_url,
        ACCESS_LOGIN_FILE=str((ROOT / args.login_file).resolve()),
        ACCESS_INDEXED="1" if args.indexed else "0",
    )
    command = ["npm", "exec", "--", "playwright", "test", "--config", "playwright.access.config.ts"]
    if args.project:
        command += ["--project", args.project]
    result = subprocess.run(
        command, cwd=ROOT / "frontend", env=env, text=True, capture_output=True, timeout=320
    )
    folder = ROOT / "docs/verification/access_control"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "browser.log").write_text(result.stdout + result.stderr)
    report = ROOT / "frontend/test-results/access-control.json"
    if report.is_file():
        (folder / "browser.json").write_text(report.read_text())
    print(result.stdout + result.stderr)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
