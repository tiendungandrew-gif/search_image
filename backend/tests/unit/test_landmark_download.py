import hashlib
import io
import json
from pathlib import Path

import httpx
import pytest
from PIL import Image

from app.cli.download_landmarks import download, source_url


def test_public_source_allowlist_rejects_untrusted_targets():
    for url in [
        "http://www.nps.gov/a",
        "https://evil.test/a",
        "https://www.nps.gov:8443/a",
        "https://user:pass@www.nps.gov/a",
    ]:
        with pytest.raises(ValueError, match="PUBLIC_SOURCE_NOT_ALLOWED"):
            source_url(url)


def test_download_preserves_author_credit_and_exact_bytes(tmp_path):
    catalog = json.loads(Path("evaluation/agent/datasets/nps_v1.json").read_text())
    catalog["images"] = catalog["images"][:1]
    row = catalog["images"][0]
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog))
    image = io.BytesIO()
    Image.new("RGB", (16, 12)).save(image, format="JPEG")
    raw = image.getvalue()

    def reply(request):
        if request.url.path.endswith("index.htm"):
            asset = row["download_url"].split("/")[-1].split("?")[0]
            return httpx.Response(200, text=asset + " NPS Photo")
        return httpx.Response(200, content=raw, headers={"Content-Type": "image/jpeg"})

    result = download(path, tmp_path / "download", transport=httpx.MockTransport(reply))
    assert result["images"] == 1
    manifest = json.loads((tmp_path / "download/manifest.json").read_text())
    receipt = manifest["images"][0]
    assert receipt["sha256"] == hashlib.sha256(raw).hexdigest()
    assert receipt["credit"] == "NPS Photo" and receipt["width"] == 16
    assert manifest["fixture"] is False
    assert (tmp_path / "download" / receipt["filename"]).read_bytes() == raw


def test_missing_source_credit_blocks_download(tmp_path):
    catalog = json.loads(Path("evaluation/agent/datasets/nps_v1.json").read_text())
    catalog["images"] = catalog["images"][:1]
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog))
    with pytest.raises(ValueError, match="SOURCE_IMAGE_OR_CREDIT_CHANGED"):
        download(
            path,
            tmp_path / "download",
            transport=httpx.MockTransport(lambda r: httpx.Response(200, text="no credit")),
        )
