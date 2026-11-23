"""HTTP acceptance qua reverse proxy thật, có nhãn rỗng/fixture; không ghi dữ liệu."""

import argparse
import hashlib
import json
import ssl
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deployment.common import Deployment  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--expected-images", type=int, required=True)
    parser.add_argument("--tls", action="store_true")
    parser.add_argument("--login-file", default=".cache/auth/deployment-admin-login.json")
    parser.add_argument("--output", default="docs/verification/phase12")
    args = parser.parse_args()
    d = Deployment(args.env_file, args.output + "/runs", args.tls)
    port = d.cfg.get("DEPLOY_HTTPS_PORT", "8443") if args.tls else d.cfg["DEPLOY_HTTP_PORT"]
    base = d.cfg.get("DEPLOY_CHECK_URL", f"{'https' if args.tls else 'http'}://127.0.0.1:{port}")
    context = ssl.create_default_context(cafile=d.cfg.get("DEPLOY_TLS_CA_FILE") or None)
    evidence = {
        "classification": "REAL_DEPLOYMENT_SYNTHETIC_DATA"
        if args.expected_images
        else "REAL_DEPLOYMENT_EMPTY_DATASET",
        "project": d.project,
        "expected_images": args.expected_images,
        "tls": args.tls,
        "checks": [],
    }
    headers = {"Authorization": "Bearer " + d.cfg["API_TOKEN"]}
    with httpx.Client(base_url=base, timeout=20, verify=context) as c:
        mode = c.get("/api/v1/auth/me")
        if mode.status_code == 200 and not mode.json().get("legacy_enabled"):
            credentials = json.loads((Path(args.login_file)).read_text())
            origin = json.loads(d.cfg["CORS_ORIGINS"])[0]
            signed_in = c.post(
                "/api/v1/auth/login",
                json={"username": credentials["username"], "password": credentials["password"]},
                headers={"Origin": origin},
            )
            assert signed_in.status_code == 200
            csrf_name = (
                "__Host-lens_csrf" if d.cfg.get("AUTH_COOKIE_SECURE") == "true" else "lens_csrf"
            )
            headers = {"Origin": origin, "X-CSRF-Token": c.cookies[csrf_name]}
        for path in ["/", "/evaluation"]:
            response = c.get(path)
            assert response.status_code == 200 and '<div id="root">' in response.text
            assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
            assert "@vite/client" not in response.text
            evidence["checks"].append(
                {"path": path, "status": response.status_code, "static_spa": True}
            )
        assert httpx.get(base + "/api/v1/system/workspace", verify=context).status_code == 401
        assert c.post("/api/v1/images", headers=headers, content=b"{}").status_code == 403
        assert c.post("/api/v1/index/jobs", headers=headers, json={}).status_code == 403
        workspace = c.get("/api/v1/system/workspace", headers=headers)
        assert workspace.status_code == 200
        body = workspace.json()
        assert body["dataset"]["images"] == args.expected_images
        evidence["workspace"] = body
        evaluation = c.get("/api/v1/system/evaluation", headers=headers).json()
        assert evaluation["state"] in {"empty", "not_available"} and evaluation["experiments"] == []
        search = c.post(
            "/api/v1/search", headers=headers, json={"text": "colored shapes", "top_k": 3}
        )
        if args.expected_images:
            assert search.status_code == 200 and len(search.json()["results"]) == 3
            results = search.json()["results"]
            assert len({row["image_id"] for row in results}) == 3
            hashes = set()
            for file in Path(d.cfg["DEPLOY_DATASET_PATH"]).rglob("*"):
                if file.suffix.lower() in {".jpg", ".png", ".webp"}:
                    hashes.add(hashlib.sha256(file.read_bytes()).hexdigest())
            for row in results:
                path = row["image_url"]
                assert path.startswith("/api/v1/images/")
                assert httpx.get(base + path, verify=context).status_code == 401
                original = c.get(path, headers=headers)
                assert (
                    original.status_code == 200
                    and original.headers["cache-control"] == "private, no-store"
                )
                assert hashlib.sha256(original.content).hexdigest() in hashes
                assert c.get(row["thumbnail_url"], headers=headers).status_code == 200
            image = next(Path(d.cfg["DEPLOY_DATASET_PATH"]).rglob("*.png"))
            combined = c.post(
                "/api/v1/search/multimodal",
                headers=headers,
                files={"image": ("fixture.png", image.read_bytes(), "image/png")},
                data={"options": '{"mode":"multimodal","text":"colored shapes","top_k":3}'},
            )
            assert combined.status_code == 200 and combined.json()["search_mode"] == "multimodal"
            evidence["retrieved_ids"] = [row["image_id"] for row in results]
        else:
            assert body["dataset"]["state"] == "empty_dataset"
            assert search.status_code in {409, 503}
            assert search.json()["error"]["code"] in {
                "FEATURE_DISABLED",
                "NOT_READY",
                "INDEX_NOT_READY",
            }
        if not body["rag"]["enabled"]:
            rag = c.post(
                "/api/v1/rag/explain",
                headers=headers,
                json={"query": "shapes", "top_k": 1, "question": "What are the image dimensions?"},
            )
            if args.expected_images:
                assert rag.status_code == 200
                assert rag.json()["rag"]["generated"] is False
                assert rag.json()["rag"]["error_code"] in {"RAG_DISABLED", "INSUFFICIENT_EVIDENCE"}
            else:
                assert rag.status_code == 503 and rag.json()["error"]["code"] == "NOT_READY"
            evidence["rag"] = "disabled_verified; live LLM NOT_CONFIGURED"
        agent = c.post(
            "/api/v1/search/agent/stream",
            headers=headers,
            json={
                "query": "Find landmarks in the city where Unknown Phase12 Place is located",
                "top_k": 2,
            },
        )
        if body["agent"]["enabled"]:
            assert agent.status_code == 200 and any(
                event in agent.text for event in ["event: agent_partial", "event: agent_completed"]
            )
            completed = next(
                frame
                for frame in agent.text.split("\n\n")
                if frame.startswith(("event: agent_partial", "event: agent_completed"))
            )
            payload = json.loads(
                next(line[5:] for line in completed.splitlines() if line.startswith("data:"))
            )
            assert payload["status"] == "insufficient_evidence" and not payload["results"]
            evidence["agent"] = {"proxy_sse": True, "status": payload["status"]}
        else:
            assert agent.status_code == 409
            evidence["agent"] = "disabled_verified"
    evidence["inventory"] = d.application("app.cli.operations", "inventory")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S_%f")
    target = Path(args.output) / f"http_{stamp}.json"
    with target.open("x") as handle:
        json.dump(evidence, handle, ensure_ascii=False, indent=2)
    print(json.dumps({"status": "passed", "artifact": str(target)}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("Deployment verification failed; no check was marked passed.", file=sys.stderr)
        raise
