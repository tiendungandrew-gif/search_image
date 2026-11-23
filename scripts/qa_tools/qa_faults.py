"""Real SIGKILL/recovery scenarios, restricted to the generated QA Compose project."""

import json
import os
import shlex
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qa import ROOT, configuration  # noqa: E402


def main():
    cfg = configuration()
    compose = [
        "docker",
        "compose",
        "--env-file",
        ".env.qa",
        "-f",
        "compose.qa.yaml",
        "-p",
        cfg["QA_PROJECT_NAME"],
    ]
    evidence = {
        "classification": "REAL_SERVICE_TERMINATION_ON_ISOLATED_QA",
        "production_data_modified": False,
        "scenarios": [],
    }

    def docker(*arguments):
        command = compose + list(arguments)
        if os.getenv("QA_USE_SG") == "1":
            command = ["sg", "docker", "-c", shlex.join(command)]
        subprocess.run(
            command,
            cwd=ROOT,
            check=True,
            timeout=45,
            capture_output=True,
        )

    with httpx.Client(
        base_url="http://127.0.0.1:8011",
        headers={"Authorization": "Bearer " + cfg["API_TOKEN"]},
        timeout=10,
    ) as client:
        assert client.get("/api/v1/system/info").json()["environment"] == "test"
        initial = client.get("/api/v1/system/workspace").json()
        indexed = initial["dataset"]["state"] == "ready"

        def recovered():
            until = time.monotonic() + 45
            while time.monotonic() < until:
                try:
                    if client.get("/api/v1/health/ready").status_code == 200:
                        if not indexed:
                            return
                        reply = client.post(
                            "/api/v1/search", json={"text": "colored shapes", "top_k": 2}
                        )
                        if reply.status_code == 200 and reply.json()["results"]:
                            return
                except httpx.HTTPError:
                    pass
                time.sleep(0.25)
            raise AssertionError("QA service did not recover within 45 seconds")

        for service, dependency in [
            ("qa-postgres", "postgresql"),
            ("qa-qdrant", "qdrant"),
            ("qa-minio", "minio"),
        ]:
            row = {"service": service, "fault": "SIGKILL"}
            try:
                docker("kill", "-s", "SIGKILL", service)
                assert client.get("/api/v1/health/live").status_code == 200
                started = time.perf_counter()
                ready = client.get("/api/v1/health/ready")
                row.update(
                    readiness_status=ready.status_code,
                    readiness_ms=(time.perf_counter() - started) * 1000,
                )
                assert ready.status_code == 503 and ready.json()["dependencies"][dependency] in {
                    "unhealthy",
                    "timeout",
                }
                snapshot = client.get("/api/v1/system/workspace")
                assert snapshot.status_code in {200, 503, 504}
                if snapshot.status_code == 200:
                    assert snapshot.json()["dataset"]["state"] == "unavailable"
                if indexed:
                    started = time.perf_counter()
                    search = client.post(
                        "/api/v1/search", json={"text": "colored shapes", "top_k": 2}
                    )
                    row.update(
                        search_status=search.status_code,
                        search_ms=(time.perf_counter() - started) * 1000,
                    )
                    assert search.status_code in {503, 504}
                    assert search.json()["error"]["code"] in {
                        "DEPENDENCY_UNAVAILABLE",
                        "DEADLINE_EXCEEDED",
                        "COLLECTION_UNAVAILABLE",
                    }
            finally:
                recovery_start = time.perf_counter()
                docker("start", service)
                recovered()
                row["recovery_ms"] = (time.perf_counter() - recovery_start) * 1000
            row["status"] = "passed"
            evidence["scenarios"].append(row)
        try:
            docker("kill", "-s", "SIGKILL", "qa-api")
            with httpx.Client(timeout=5) as browser_client:
                assert browser_client.get("http://127.0.0.1:5175/").status_code == 200
                proxy = browser_client.get("http://127.0.0.1:5175/api/v1/health")
                assert proxy.status_code >= 500
        finally:
            docker("start", "qa-api")
            recovered()
        evidence["scenarios"].append(
            {
                "service": "qa-api",
                "fault": "SIGKILL",
                "frontend_shell_available": True,
                "status": "passed",
            }
        )
        final = client.get("/api/v1/system/workspace").json()
        assert final["dataset"]["images"] == initial["dataset"]["images"]
        assert final["dataset"]["index_id"] == initial["dataset"]["index_id"]
        evidence["initial_dataset"] = initial["dataset"]
        evidence["final_dataset"] = final["dataset"]
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S_%f")
    target = ROOT / "docs/verification/phase11" / f"faults_{stamp}.json"
    with target.open("x") as handle:
        handle.write(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
