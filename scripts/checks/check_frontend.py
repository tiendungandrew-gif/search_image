"""Run browser checks with only the local read token; never print credentials."""

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from browser_environment import browser_environment  # noqa: E402
from dotenv import dotenv_values  # noqa: E402

root = Path(__file__).resolve().parents[2]
env = os.environ.copy()

env = browser_environment(root, env)
env["API_TOKEN"] = dotenv_values(root / ".env").get("API_TOKEN") or ""
result = subprocess.run(
    ["npm", "exec", "playwright", "--", "test", *sys.argv[1:]],
    cwd=root / "frontend",
    env=env,
    check=False,
)
raise SystemExit(result.returncode)
