"""Fault injection trên stack thật; khôi phục đúng các RAG fields đã đổi."""

import argparse
import json
import subprocess
import time
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
FIELDS = ["RAG_ENABLED", "RAG_MODEL_PROVIDER", "RAG_MODEL_ENDPOINT", "RAG_TIMEOUT_SECONDS"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="docs/verification/phase08/fallback_cases.json")
    args = parser.parse_args()
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    path = ROOT / ".env"
    original = dotenv_values(path)
    records = []

    def configure(changes):
        lines = []
        seen = set()
        for line in path.read_text().splitlines():
            key = line.split("=", 1)[0]
            if key in changes:
                if changes[key] is not None:
                    lines.append(key + "=" + changes[key])
                seen.add(key)
            else:
                lines.append(line)
        lines.extend(k + "=" + v for k, v in changes.items() if k not in seen and v is not None)
        path.write_text("\n".join(lines) + "\n")
        path.chmod(0o600)
        subprocess.run(
            [
                "docker",
                "compose",
                "up",
                "-d",
                "--no-deps",
                "--force-recreate",
                "--wait",
                "--wait-timeout",
                "180",
                "backend",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        with httpx.Client(
            headers={"Authorization": "Bearer " + original["API_TOKEN"]}, timeout=5
        ) as client:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if (
                    client.get("http://127.0.0.1:8000/api/v1/health?check=search").status_code
                    == 200
                ):
                    return
                time.sleep(0.5)
        raise RuntimeError("search_not_ready_after_recreate")

    try:
        for name, changes, code in [
            ("rag_disabled", {"RAG_ENABLED": "false"}, "RAG_DISABLED"),
            (
                "provider_connection_failure",
                {
                    "RAG_ENABLED": "true",
                    "RAG_MODEL_PROVIDER": "openai_compatible",
                    "RAG_MODEL_ENDPOINT": "http://127.0.0.1:9",
                },
                "LLM_CONNECTION_FAILED",
            ),
            (
                "real_provider_timeout",
                {k: original.get(k) for k in FIELDS}
                | {"RAG_ENABLED": "true", "RAG_TIMEOUT_SECONDS": "0.1"},
                "LLM_TIMEOUT",
            ),
        ]:
            configure(changes)
            with httpx.Client(
                base_url="http://127.0.0.1:8000",
                headers={"Authorization": "Bearer " + original["API_TOKEN"]},
                timeout=12,
            ) as client:
                search = client.post(
                    "/api/v1/search", json={"query": "a cup of coffee", "top_k": 1, "mode": "text"}
                )
                search.raise_for_status()
                response = client.post(
                    "/api/v1/rag/explain",
                    json={
                        "image_ids": [r["image_id"] for r in search.json()["results"]],
                        "question": "What format and dimensions are in the metadata?",
                        "language": "en",
                    },
                )
                response.raise_for_status()
                result = response.json()
                assert result["results"] and result["rag"]["error_code"] == code, (
                    name,
                    result["rag"]["error_code"],
                )
                assert not result["rag"]["generated"] and not result["rag"]["citations"]
                records.append(
                    {
                        "scenario": name,
                        "status": "pass",
                        "response": result,
                        "search_http_status": search.status_code,
                    }
                )
                print("[OK] " + name, flush=True)
    finally:
        configure({k: original.get(k) for k in FIELDS})
        output.write_text(
            json.dumps(
                {"cases": records, "original_config_restored": True}, indent=2, ensure_ascii=False
            )
            + "\n"
        )


if __name__ == "__main__":
    main()
