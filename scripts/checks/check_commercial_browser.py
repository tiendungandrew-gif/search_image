"""Commercial UI acceptance with real scoped photos, layouts, search and keyboard."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from browser_environment import browser_environment  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project")
    args = parser.parse_args()
    env = browser_environment(ROOT)
    cmd = [
        "npm",
        "exec",
        "--",
        "playwright",
        "test",
        "--config",
        "tests/e2e/config/commercial.config.ts",
    ]
    if args.project:
        cmd += ["--project", args.project]
    result = subprocess.run(
        cmd, cwd=ROOT / "frontend", env=env, capture_output=True, text=True, timeout=380
    )
    folder = ROOT / "docs/verification/commercial_ui"
    folder.mkdir(parents=True, exist_ok=True)
    name = "browser-" + (args.project or "all")
    (folder / (name + ".txt")).write_text(result.stdout + result.stderr)
    report = ROOT / "frontend/test-results/commercial.json"
    if report.exists():
        (folder / (name + ".json")).write_text(report.read_text())
    print(result.stdout + result.stderr)
    print(json.dumps({"exit_code": result.returncode}))
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
