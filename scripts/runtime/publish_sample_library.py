"""Opt the existing, hash-verified login/sample photos into guest search on local dev."""

import hashlib
import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]


def main():
    expected = {
        hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (ROOT / "datasets/sample").iterdir()
        if path.suffix.lower() in {".png", ".jpg"}
    }
    assert len(expected) == 10
    origin = "http://localhost:5173"
    with httpx.Client(base_url=origin, headers={"Origin": origin}, timeout=30) as client:
        login = client.post("/api/v1/auth/quick-login", json={"role": "admin"})
        login.raise_for_status()
        client.headers["X-CSRF-Token"] = client.cookies["lens_csrf"]
        try:
            response = client.get("/api/v1/admin/datasets")
            response.raise_for_status()
            libraries = response.json()["datasets"]
            sample = next(d for d in libraries if d["key"] == "scikit-image-v0.25.2")
            assert sample["is_active"] and sample["images"] == len(expected)
            response = client.get(
                "/api/v1/admin/images", params={"dataset_id": sample["id"], "limit": 100}
            )
            response.raise_for_status()
            images = response.json()
            assert images["total"] == len(expected)
            actual = set()
            for image in images["images"]:
                assert image["status"] == "available" and not image["hidden"]
                data = client.get(f"/api/v1/images/{image['id']}/content?variant=original")
                data.raise_for_status()
                actual.add(hashlib.sha256(data.content).hexdigest())
            assert actual == expected, "Refusing to publish a library containing unknown photos"
            if not sample["is_public"]:
                response = client.patch(
                    f"/api/v1/admin/datasets/{sample['id']}",
                    json={"name": sample["name"], "is_public": True},
                )
                response.raise_for_status()
            after = client.get("/api/v1/admin/datasets").json()["datasets"]
            assert {d["id"]: d["is_public"] for d in libraries if d["id"] != sample["id"]} == {
                d["id"]: d["is_public"] for d in after if d["id"] != sample["id"]
            }
            folder = ROOT / "docs/verification/guest_search"
            folder.mkdir(parents=True, exist_ok=True)
            report = {
                "published_library": sample["key"],
                "images_verified": len(actual),
                "other_libraries_unchanged": True,
                "public_libraries": [d["key"] for d in after if d["is_public"]],
            }
            (folder / "public-sample.json").write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps(report))
        finally:
            client.post("/api/v1/auth/logout").raise_for_status()


if __name__ == "__main__":
    main()
