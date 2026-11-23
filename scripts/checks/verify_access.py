"""Read-only HTTP acceptance for account-mode development or deployment."""

import argparse
import http.cookiejar
import json
import urllib.error
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:5173")
    parser.add_argument("--login-file", default=".cache/auth/admin-login.json")
    parser.add_argument("--expected-images", type=int, required=True)
    parser.add_argument("--output", default="docs/verification/access_control/main-http.json")
    args = parser.parse_args()
    credentials = json.loads(Path(args.login_file).read_text())
    jar = http.cookiejar.CookieJar()
    client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def request(path, data=None, headers=None):
        raw = None if data is None else json.dumps(data).encode()
        with client.open(
            urllib.request.Request(
                args.base_url + "/api/v1" + path, data=raw, headers=headers or {}
            ),
            timeout=30,
        ) as response:
            return response.status, json.loads(response.read())

    status, initial = request("/auth/me")
    assert status == 200 and initial["user"] is None and initial["legacy_enabled"] is False
    headers = {"Origin": args.base_url, "Content-Type": "application/json"}
    _, account = request(
        "/auth/login",
        {"username": credentials["username"], "password": credentials["password"]},
        headers,
    )
    assert account["user"]["role"] == "admin"
    headers["X-CSRF-Token"] = next(
        c.value for c in jar if c.name in {"lens_csrf", "__Host-lens_csrf"}
    )
    _, workspace = request("/system/workspace")
    assert workspace["dataset"]["images"] == args.expected_images
    _, datasets = request("/admin/datasets")
    result = {
        "account_role": "admin",
        "legacy_enabled": False,
        "dataset": workspace["dataset"],
        "libraries": [{"key": d["key"], "images": d["images"]} for d in datasets["datasets"]],
    }
    if workspace["capabilities"]["text_search"]:
        _, search = request(
            "/search", {"mode": "text", "text": "a photograph", "top_k": 3}, headers
        )
        assert search["total_results"] > 0
        first = search["results"][0]
        with client.open(args.base_url + first["thumbnail_url"], timeout=20) as image:
            assert image.status == 200 and image.headers["Cache-Control"] == "private, no-store"
        result["retrieved"] = search["total_results"]
        result["private_image"] = True
    request("/auth/logout", {}, headers)
    assert request("/auth/me")[1]["user"] is None
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"status": "passed", **result}, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps({"status": "passed", "images": args.expected_images, "artifact": str(output)}))


if __name__ == "__main__":
    main()
