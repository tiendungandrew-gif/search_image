#!/usr/bin/env python3
"""Chạy command local với file env chỉ định; không source/eval shell hoặc in secrets."""

import argparse
import os
import subprocess

from dotenv import dotenv_values
from environment_paths import resolve_env_file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("Cần command sau --")
    env_file = resolve_env_file(args.env_file)
    if not env_file.is_file():
        parser.error("Không tìm thấy env file")
    values = {key: value for key, value in dotenv_values(env_file).items() if value is not None}
    # Chỉ child process dùng env file; không thay đổi shell/host environment của người dùng.
    return subprocess.call(command, env=os.environ | values)


if __name__ == "__main__":
    raise SystemExit(main())
