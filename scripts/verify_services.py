#!/usr/bin/env python3
"""Kiểm tra HTTP và response semantics; không coi process/container running là healthy."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", default="http://127.0.0.1:8000")
    parser.add_argument("--frontend", default="http://127.0.0.1:5173")
    parser.add_argument("--env-file", default=".env")
    args = parser.parse_args()
    token = os.environ.get("API_TOKEN", "")
    env_file = Path(args.env_file)
    if not token and env_file.is_file():
        token = next(
            (
                line.split("=", 1)[1].strip()
                for line in env_file.read_text().splitlines()
                if line.startswith("API_TOKEN=")
            ),
            "",
        )
    failed = False
    for label, url, authorize in [
        ("liveness", args.backend + "/api/v1/health/live", False),
        ("readiness", args.backend + "/api/v1/health/ready", True),
        ("OpenAPI", args.backend + "/openapi.json", False),
        ("API docs", args.backend + "/docs", False),
        ("frontend", args.frontend, False),
        ("frontend API proxy", args.frontend + "/api/v1/health", False),
    ]:
        try:
            headers = {"Authorization": f"Bearer {token}"} if authorize else {}
            if authorize and not token:
                raise ValueError("thiếu API_TOKEN; dùng --env-file")
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=headers), timeout=5
            ) as r:
                data = r.read()
                if label == "liveness" and json.loads(data).get("status") != "alive":
                    raise ValueError("liveness status sai")
                if label == "readiness":
                    body = json.loads(data)
                    if (
                        body.get("status") != "ready"
                        or set(body.get("dependencies", {})) != {"postgresql", "qdrant", "minio"}
                        or any(v != "healthy" for v in body["dependencies"].values())
                    ):
                        raise ValueError("dependency chưa healthy")
                if label == "OpenAPI" and "/api/v1/health/live" not in json.loads(data).get(
                    "paths", {}
                ):
                    raise ValueError("schema thiếu endpoint foundation")
                if label == "frontend" and b'id="root"' not in data:
                    raise ValueError("response không phải React entry page")
                if label == "frontend API proxy" and json.loads(data).get("check") != "live":
                    raise ValueError("proxy chưa nối backend")
            print(f"[OK] {label}")
        except (urllib.error.URLError, ValueError, json.JSONDecodeError, TimeoutError):
            print(f"[LỖI] {label}; kiểm tra URL/config/service logs, không in credentials.")
            failed = True
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
