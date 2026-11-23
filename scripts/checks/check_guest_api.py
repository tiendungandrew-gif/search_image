"""Serving guest smoke: public cat relevance, direct private media denial and login gates."""

import hashlib
import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]


def main():
    origin = "http://localhost:5173"
    with httpx.Client(base_url=origin, headers={"Origin": origin}, timeout=30) as admin:
        response = admin.post("/api/v1/auth/quick-login", json={"role": "admin"})
        response.raise_for_status()
        admin.headers["X-CSRF-Token"] = admin.cookies["lens_csrf"]
        try:
            libraries = admin.get("/api/v1/admin/datasets").json()["datasets"]
            private = next(d for d in libraries if not d["is_public"] and d["images"])
            image = admin.get(
                "/api/v1/admin/images", params={"dataset_id": private["id"], "limit": 1}
            ).json()["images"][0]
        finally:
            admin.post("/api/v1/auth/logout").raise_for_status()
    expected = hashlib.sha256((ROOT / "datasets/sample/chelsea.png").read_bytes()).digest()
    with httpx.Client(base_url=origin, headers={"Origin": origin}, timeout=30) as guest:
        response = guest.get("/api/v1/public/workspace")
        response.raise_for_status()
        workspace = response.json()
        assert workspace["dataset"]["images"] == 10
        assert [d["key"] for d in workspace["public_datasets"]] == ["scikit-image-v0.25.2"]
        assert not workspace["capabilities"]["image_search"]
        queries = []
        for text in ["con meo", "a cat"]:
            response = guest.post("/api/v1/search", json={"text": text, "top_k": 3})
            response.raise_for_status()
            value = response.json()
            assert response.headers["cache-control"] == "private, no-store"
            assert value["results"] and all(
                r["metadata"]["source_dataset"] == "scikit-image-v0.25.2" for r in value["results"]
            )
            first = value["results"][0]
            detail = guest.get(f"/api/v1/images/{first['image_id']}")
            detail.raise_for_status()
            assert detail.headers["cache-control"] == "private, no-store"
            content = guest.get(first["image_url"])
            content.raise_for_status()
            assert hashlib.sha256(content.content).digest() == expected
            assert content.headers["cache-control"] == "private, no-store"
            queries.append(
                {
                    "query": text,
                    "top1_image_id": first["image_id"],
                    "top1_sha_matches_sample_cat": True,
                    "warnings": value["warnings"],
                }
            )
        for suffix in ["", "/content?variant=original", "/content?variant=thumbnail"]:
            assert guest.get(f"/api/v1/images/{image['id']}{suffix}").status_code == 404
        filtered = guest.post(
            "/api/v1/search",
            json={"text": "con meo", "filters": {"source_dataset": private["key"]}},
        )
        filtered.raise_for_status()
        assert filtered.json()["results"] == []
        for path in ["/admin/users", "/system/workspace", "/rag/status", "/search/agent/status"]:
            assert guest.get("/api/v1" + path).status_code == 401
        assert (
            guest.post(
                "/api/v1/search/multimodal", files={"image": ("test.png", b"invalid", "image/png")}
            ).status_code
            == 401
        )
        assert guest.post("/api/v1/search", json={"text": "cat", "top_k": 50}).status_code == 422
        assert (
            guest.post(
                "/api/v1/search", json={"text": "cat"}, headers={"Origin": "https://evil.example"}
            ).status_code
            == 403
        )
        assert not guest.cookies.get("lens_session")
    report = {
        "scope": "Serving API, no anonymous session or user credentials",
        "public_images": 10,
        "queries": queries,
        "private_metadata_original_thumbnail": "404",
        "private_source_filter": "empty",
        "privileged_routes": "401",
        "guest_top_k_limit": "422",
        "cross_origin": "403",
        "quota_and_revocation": "covered separately by isolated integration tests",
    }
    folder = ROOT / "docs/verification/guest_search"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "api.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": "passed", "queries": len(queries), "private_media_denied": True}))


if __name__ == "__main__":
    main()
