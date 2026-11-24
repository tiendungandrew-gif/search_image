"""Read-only acceptance of local quick role sign-in; no credentials required."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from browser_environment import browser_environment  # noqa: E402


def main():
    env = browser_environment(ROOT)
    command = [
        "npm",
        "exec",
        "--",
        "playwright",
        "test",
        "--config",
        "tests/e2e/config/quick-login.config.ts",
    ]
    result = subprocess.run(
        command, cwd=ROOT / "frontend", env=env, text=True, capture_output=True, timeout=210
    )
    folder = ROOT / "docs/verification/quick_login"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "browser.txt").write_text(result.stdout + result.stderr)
    report = ROOT / "frontend/test-results/quick-login.json"
    if report.is_file():
        (folder / "browser.json").write_text(report.read_text())
    print(result.stdout + result.stderr)
    print(json.dumps({"exit_code": result.returncode}))
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
