"""Verify the running bilingual search through a scoped demo User session."""

import hashlib
import json
import re
from pathlib import Path
from time import perf_counter

import httpx

ROOT = Path(__file__).resolve().parents[2]


def main():
    origin = "http://localhost:5173"
    with httpx.Client(base_url=origin, headers={"Origin": origin}, timeout=30) as client:
        login = client.post("/api/v1/auth/quick-login", json={"role": "user"})
        login.raise_for_status()
        client.headers["X-CSRF-Token"] = client.cookies["lens_csrf"]
        try:
            allowed = {item["key"] for item in login.json()["user"]["datasets"]}
            assert allowed
            assert client.get("/api/v1/admin/users").status_code == 403
            rows = []
            for query in (
                "một tách cà phê",
                "a cup of coffee",
                "một con mèo màu nâu",
                "a brown cat",
                "tên lửa phóng lên bầu trời",
                "a rocket launching into the sky",
                "con meo",
                "con  meo",
                "meo",
                "con mèo",
                "a cat",
                "một tách cà phê",
            ):
                start = perf_counter()
                response = client.post("/api/v1/search", json={"text": query, "top_k": 3})
                response.raise_for_status()
                value = response.json()
                assert value["results"]
                assert value["effective_settings"]["text_encoder_manifest_sha256"]
                assert all(r["metadata"]["source_dataset"] in allowed for r in value["results"])
                if query in {"con meo", "con  meo", "meo", "con mèo", "a cat"}:
                    first = value["results"][0]
                    caption = first["metadata"].get("caption") or ""
                    if not re.search(r"\bcats?\b", caption, re.I):
                        media = client.get(first["image_url"])
                        media.raise_for_status()
                        assert (
                            hashlib.sha256(media.content).digest()
                            == hashlib.sha256(
                                (ROOT / "datasets/sample/chelsea.png").read_bytes()
                            ).digest()
                        ), (query, first["metadata"])
                    if query in {"con meo", "con  meo", "meo"}:
                        assert any(w["code"] == "QUERY_ACCENTS_RESTORED" for w in value["warnings"])
                if not rows:
                    media = client.get(value["results"][0]["image_url"])
                    media.raise_for_status()
                    assert media.headers["cache-control"] == "private, no-store"
                rows.append(
                    {
                        "query": query,
                        "http_status": response.status_code,
                        "wall_ms": (perf_counter() - start) * 1000,
                        "processing_ms": value["latency_ms"],
                        "stages": value["latency"]["stages"],
                        "index_id": value["index_id"],
                        "image_manifest_sha256": value["manifest_sha256"],
                        "text_manifest_sha256": value["effective_settings"][
                            "text_encoder_manifest_sha256"
                        ],
                        "image_ids": [r["image_id"] for r in value["results"]],
                        "top1_metadata": value["results"][0]["metadata"],
                        "warnings": value["warnings"],
                    }
                )
            assert rows[-1]["stages"]["text_cache_hits"] == 1
            empty = client.post(
                "/api/v1/search",
                json={
                    "text": "một con mèo",
                    "filters": {"source_dataset": "does-not-exist"},
                },
            )
            empty.raise_for_status()
            assert empty.json()["results"] == []
            output = ROOT / "docs/verification/bilingual/api.json"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(
                    {
                        "scope": "API smoke: User ACL, private media, cache and image index",
                        "queries": rows,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n"
            )
            print(
                json.dumps(
                    {"queries_passed": len(rows), "user_acl": "passed", "report": str(output)}
                )
            )
        finally:
            client.post("/api/v1/auth/logout").raise_for_status()


if __name__ == "__main__":
    main()
