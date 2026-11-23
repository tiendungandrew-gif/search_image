"""Bounded downloader contracts with tiny synthetic HTTP fixtures; no real COCO claims."""

import io
import json
import zipfile

import httpx
import pytest
from PIL import Image

from app.cli.download_coco import ARCHIVE, MEMBER, RemoteZip, download, select_subset
from app.schemas.ingestion import ImageMetadataInput


def fixture_data():
    images = [
        {
            "id": i,
            "file_name": f"{i:012d}.jpg",
            "width": 8,
            "height": 8,
            "license": 4 if i < 5 else 1,
            "flickr_url": f"https://www.flickr.com/photos/fixture/{i}",
        }
        for i in range(1, 7)
    ]
    return {
        "images": images,
        "licenses": [
            {"id": 4, "url": "https://creativecommons.org/licenses/by/2.0/", "name": "fixture"}
        ],
        "annotations": [
            {"id": i, "image_id": i, "caption": "Unit fixture caption."} for i in range(1, 7)
        ],
    }


def test_subset_is_reproducible_and_keeps_only_declared_license_ids():
    data = fixture_data()
    selected, _, _ = select_subset(data, 3, 42)
    assert selected == select_subset(data, 3, 42)[0]
    assert len(selected) == 3 and all(image["license"] == 4 for image in selected)
    with pytest.raises(ValueError):
        select_subset(data, 5, 42)


def test_range_download_provenance_resume_and_corruption_rejection(tmp_path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(MEMBER, json.dumps(fixture_data()))
    raw = buffer.getvalue()
    jpeg = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(jpeg, "JPEG")
    seen = []

    def respond(request):
        seen.append(request)
        if str(request.url) == ARCHIVE:
            if request.method == "HEAD":
                return httpx.Response(
                    200, headers={"content-length": str(len(raw)), "etag": '"unit-etag"'}
                )
            start, end = map(int, request.headers["range"].removeprefix("bytes=").split("-"))
            assert request.headers["if-match"] == '"unit-etag"'
            return httpx.Response(
                206,
                content=raw[start : end + 1],
                headers={"content-range": f"bytes {start}-{end}/{len(raw)}"},
            )
        return httpx.Response(200, content=jpeg.getvalue())

    transport = httpx.MockTransport(respond)
    output, cache = tmp_path / "dataset", tmp_path / "cache"
    result = download(output, cache, 2, 42, 1, transport)
    assert result["images"] == 2
    rows = [json.loads(line) for line in (output / "metadata.jsonl").read_text().splitlines()]
    assert len(rows) == 2
    metadata = ImageMetadataInput.model_validate(
        {k: v for k, v in rows[0].items() if k != "filename"}
    )
    assert metadata.caption_source.startswith("coco2017:captions_val2017:annotation:")
    provenance = json.loads((output / "provenance.json").read_text())
    assert all(item["locally_human_verified"] is False for item in provenance)
    before = len(seen)
    assert download(output, cache, 2, 42, 1, transport) == result
    assert len(seen) == before  # Resume verifies cache; no network request needed.
    (cache / "captions_val2017.json").write_text("{}")
    with pytest.raises(ValueError, match="CHECKSUM"):
        download(output, cache, 2, 42, 1, transport)


def test_range_reader_rejects_server_ignoring_range():
    def respond(request):
        return httpx.Response(
            200, content=b"invalid", headers={"content-length": "7", "etag": "fixture"}
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        remote = RemoteZip(client)
        with pytest.raises(ValueError, match="RANGE_NOT_SUPPORTED"):
            remote.read(2)


def test_optional_caption_source_keeps_legacy_idempotency_fingerprint():
    values = {"source_dataset": "fixture", "license": "fixture", "rights_ref": "fixture"}
    legacy = ImageMetadataInput(**values)
    assert "caption_source" not in legacy.fingerprint_data()
    attributed = ImageMetadataInput(
        **values, caption="A fixture.", caption_source="dataset_annotation"
    )
    assert attributed.fingerprint_data()["caption_source"] == "dataset_annotation"
