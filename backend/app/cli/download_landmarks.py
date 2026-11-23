"""Tải catalog NPS cố định đã đối chiếu nguồn; không phải tool của Agent."""

import argparse
import hashlib
import io
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from PIL import Image


def source_url(value):
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "www.nps.gov"
        or parsed.port not in {None, 443}
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise ValueError("PUBLIC_SOURCE_NOT_ALLOWED")
    return value


def download(catalog, output, transport=None):
    data = json.loads(Path(catalog).read_text())
    rows = data["images"]
    if data.get("fixture") is not False or not 1 <= len(rows) <= 20:
        raise ValueError("INVALID_PUBLIC_CATALOG")
    for row in rows:
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,79}", row["slug"]):
            raise ValueError("INVALID_PUBLIC_FILENAME")
        for field in ["source_page", "relation_source", "download_url"]:
            source_url(row[field])
        if not urlsplit(row["download_url"]).path.startswith("/common/uploads/structured_data/"):
            raise ValueError("PUBLIC_IMAGE_PATH_NOT_ALLOWED")
        if not row["credit"].startswith("NPS") or "©" in row["credit"]:
            raise ValueError("PUBLIC_IMAGE_RIGHTS_NOT_VERIFIED")
    target = Path(output)
    target.mkdir(parents=True, exist_ok=False)
    metadata, receipts = [], []
    with httpx.Client(timeout=25, transport=transport, follow_redirects=False) as client:
        for row in rows:
            response = client.get(row["source_page"])
            response.raise_for_status()
            if len(response.content) > 1024 * 1024:
                raise ValueError("SOURCE_PAGE_LIMIT")
            asset = urlsplit(row["download_url"]).path.rsplit("/", 1)[-1]
            if asset not in response.text or row["credit"] not in response.text:
                raise ValueError("SOURCE_IMAGE_OR_CREDIT_CHANGED")
            # No retries on rate limits and no redirect to another source.
            with client.stream("GET", row["download_url"]) as image_response:
                image_response.raise_for_status()
                if not image_response.headers.get("content-type", "").startswith("image/"):
                    raise ValueError("PUBLIC_IMAGE_CONTENT_TYPE")
                raw = bytearray()
                for chunk in image_response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 20 * 1024 * 1024:
                        raise ValueError("PUBLIC_IMAGE_SIZE_LIMIT")
            with Image.open(io.BytesIO(raw)) as image:
                width, height = image.size
                if image.format != "JPEG" or width * height > 25_000_000:
                    raise ValueError("PUBLIC_IMAGE_FORMAT_OR_PIXELS")
                image.verify()
            filename = row["slug"] + ".jpg"
            (target / filename).write_bytes(raw)
            metadata.append(
                {
                    "filename": filename,
                    "title": row["canonical_name"],
                    "caption": row["caption"],
                    "caption_source": row["source_page"],
                    "description": row["credit"] + ". " + row["modifications"],
                    "tags": ["landmark", "washington-dc", "nps"],
                    "source_dataset": data["dataset_id"],
                    "source_uri": row["source_page"],
                    "license": row["license"],
                    "rights_ref": data["rights_ref"],
                }
            )
            receipts.append(
                {
                    **row,
                    "filename": filename,
                    "width": width,
                    "height": height,
                    "byte_size": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "source_page_sha256": hashlib.sha256(response.content).hexdigest(),
                }
            )
    encoded = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in metadata).encode()
    (target / "metadata.jsonl").write_bytes(encoded)
    manifest = {
        "dataset_id": data["dataset_id"],
        "source_dataset": data["dataset_id"],
        "rights_ref": data["rights_ref"],
        "count": len(receipts),
        "fixture": False,
        "downloaded_at": datetime.now(UTC).isoformat(),
        "catalog_sha256": hashlib.sha256(Path(catalog).read_bytes()).hexdigest(),
        "metadata_sha256": hashlib.sha256(encoded).hexdigest(),
        "images": receipts,
    }
    (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return {"status": "downloaded", "images": len(receipts), "output": str(target)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default="evaluation/agent/datasets/nps_v1.json")
    parser.add_argument("--output", default="datasets/landmarks_phase09_v1")
    args = parser.parse_args()
    try:
        print(json.dumps(download(args.catalog, args.output)))
    except (ValueError, httpx.HTTPError, OSError) as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
