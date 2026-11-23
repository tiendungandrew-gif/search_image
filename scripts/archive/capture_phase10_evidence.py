"""Private local acceptance snapshots. Output contains no credentials or image bytes."""

import json
from pathlib import Path

import httpx
from dotenv import dotenv_values

root = Path(__file__).resolve().parents[2]
token = dotenv_values(root / ".env").get("API_TOKEN")
assert token, "Missing local API_TOKEN"
headers = {"Authorization": f"Bearer {token}"}
evidence = {"verification": "VERIFIED_WITH_REAL_DATA", "requests": {}}
with httpx.Client(base_url="http://127.0.0.1:8000/api/v1", timeout=10) as client:
    for endpoint in ["health/live", "health/ready", "system/workspace", "system/evaluation"]:
        response = client.get(endpoint, headers=headers)
        assert response.status_code == 200, endpoint
        evidence["requests"][endpoint] = {"status": response.status_code, "body": response.json()}
    snapshot = evidence["requests"]["system/workspace"]["body"]["dataset"]
    assert snapshot["images"] == snapshot["indexed_images"] == snapshot["vectors"] == 513
    assert snapshot["generation"] == 3
    assert snapshot["index_id"] == "b4597021-4b91-491d-99ae-0617a6ca389c"
    search = client.post(
        "search", headers=headers, json={"mode": "text", "text": "a cup of coffee", "top_k": 3}
    )
    assert search.status_code == 200
    image = search.json()["results"][0]
    detail = client.get(f"images/{image['image_id']}", headers=headers)
    assert detail.status_code == 200 and detail.json()["image_id"] == image["image_id"]
    content = client.get(image["thumbnail_url"].removeprefix("/api/v1/"), headers=headers)
    assert content.status_code == 200
    evidence["image_roundtrip"] = {
        "image_id": image["image_id"],
        "detail": detail.json(),
        "content_status": content.status_code,
        "media_type": content.headers["content-type"],
        "byte_size": len(content.content),
    }
    evidence["unauthorized"] = {}
    for endpoint in [
        "system/workspace",
        "system/evaluation",
        f"images/{image['image_id']}",
        image["thumbnail_url"],
    ]:
        response = client.get(endpoint.removeprefix("/api/v1/"))
        assert response.status_code == 401
        evidence["unauthorized"][endpoint] = response.status_code
with httpx.Client(base_url="http://127.0.0.1:8001/api/v1", timeout=10) as client:
    empty = client.get("system/workspace", headers=headers)
    assert empty.status_code == 200 and empty.json()["dataset"]["state"] == "empty_dataset"
    assert empty.json()["dataset"]["images"] == 0
    evaluation = client.get("system/evaluation", headers=headers)
    assert evaluation.status_code == 200 and evaluation.json()["state"] == "empty"
    evidence["real_empty"] = {"workspace": empty.json(), "evaluation": evaluation.json()}
target = root / "docs/verification/phase10/api_evidence.json"
target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
print("Verified live dataset 513, active generation 3, private media and isolated empty backend.")
