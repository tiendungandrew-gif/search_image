"""Tải subset COCO val2017 có caption; không sửa database hoặc active index."""

import argparse
import hashlib
import io
import json
import random
import re
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from PIL import Image

BASE = "https://s3.amazonaws.com/images.cocodataset.org/"
ARCHIVE = BASE + "annotations/annotations_trainval2017.zip"
MEMBER = "annotations/captions_val2017.json"
TERMS = "https://cocodataset.org/#termsofuse"
SOURCE = "coco2017-val-subset-v1"
ALLOWED_LICENSE_IDS = {4, 5, 7, 8}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_once(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError("EXISTING_FILE_MISMATCH: " + str(path))
        return
    with path.open("xb") as handle:
        handle.write(data)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


class RemoteZip(io.RawIOBase):
    """Read only requested ZIP ranges, pinned to one ETag; never extract paths."""

    def __init__(self, client):
        self.client = client
        head = client.head(ARCHIVE)
        head.raise_for_status()
        self.size = int(head.headers["content-length"])
        self.etag = head.headers["etag"]
        self.position = 0
        if not 1 <= self.size <= 300 * 1024**2:
            raise ValueError("ANNOTATION_ARCHIVE_SIZE")

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        position = (
            offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        )
        if not 0 <= position <= self.size:
            raise ValueError("INVALID_ZIP_SEEK")
        self.position = position
        return position

    def read(self, size=-1):
        size = min(self.size - self.position, size if size >= 0 else self.size)
        if not size:
            return b""
        if size > 16 * 1024**2:
            raise ValueError("ANNOTATION_RANGE_LIMIT")
        start, end = self.position, self.position + size - 1
        with self.client.stream(
            "GET", ARCHIVE, headers={"Range": f"bytes={start}-{end}", "If-Match": self.etag}
        ) as response:
            if response.status_code != 206 or response.headers.get("content-range") != (
                f"bytes {start}-{end}/{self.size}"
            ):
                raise ValueError("ANNOTATION_RANGE_NOT_SUPPORTED")
            data = bytearray()
            for chunk in response.iter_bytes():
                data.extend(chunk)
                if len(data) > size:
                    raise ValueError("ANNOTATION_RANGE_LIMIT")
        if len(data) != size:
            raise ValueError("ANNOTATION_RANGE_INCOMPLETE")
        self.position += size
        return bytes(data)


def annotations(client, cache):
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / "captions_val2017.json"
    receipt_path = cache / "captions_val2017.receipt.json"
    if path.exists() and receipt_path.exists():
        raw = path.read_bytes()
        receipt = json.loads(receipt_path.read_text())
        if sha(raw) != receipt["sha256"]:
            raise ValueError("ANNOTATION_CACHE_CHECKSUM_MISMATCH")
    else:
        remote = RemoteZip(client)
        with zipfile.ZipFile(remote) as bundle:
            info = bundle.getinfo(MEMBER)
            if info.file_size > 16 * 1024**2 or info.compress_size > 8 * 1024**2:
                raise ValueError("ANNOTATION_MEMBER_SIZE")
            raw = bundle.read(info)
        receipt = {
            "archive_url": ARCHIVE,
            "archive_etag": remote.etag,
            "archive_bytes": remote.size,
            "member": MEMBER,
            "sha256": sha(raw),
            "checksum_policy": "observed over verified TLS and ZIP CRC; not publisher-signed",
            "annotation_license": "CC-BY-4.0",
            "terms": TERMS,
        }
        write_once(path, raw)
        write_once(receipt_path, encoded(receipt))
    return json.loads(raw), receipt


def select_subset(data, count, seed):
    captions = {}
    for item in sorted(data["annotations"], key=lambda row: row["id"]):
        if isinstance(item.get("caption"), str) and item["caption"].strip():
            captions.setdefault(item["image_id"], []).append(item)
    licenses = {item["id"]: item for item in data["licenses"]}
    eligible = sorted(
        (
            item
            for item in data["images"]
            if item["id"] in captions and item["license"] in ALLOWED_LICENSE_IDS
        ),
        key=lambda row: row["id"],
    )
    if not 1 <= count <= min(1000, len(eligible)):
        raise ValueError("INVALID_SUBSET_COUNT")
    selected = sorted(random.Random(seed).sample(eligible, count), key=lambda row: row["id"])
    return selected, captions, licenses


def validate_jpeg(raw, expected):
    if not raw or len(raw) > 20 * 1024**2:
        raise ValueError("IMAGE_SIZE_LIMIT")
    with Image.open(io.BytesIO(raw)) as image:
        if image.format != "JPEG" or image.size != (expected["width"], expected["height"]):
            raise ValueError("IMAGE_FORMAT_OR_DIMENSIONS_MISMATCH")
        if image.width * image.height > 25_000_000 or max(image.size) > 10_000:
            raise ValueError("IMAGE_PIXEL_LIMIT")
        image.verify()


def download_image(client, root, image):
    name = image["file_name"]
    if not re.fullmatch(r"\d{12}\.jpg", name) or int(name[:-4]) != image["id"]:
        raise ValueError("INVALID_IMAGE_NAME")
    path = root / "images" / name
    url = BASE + "val2017/" + name
    if path.exists():
        raw = path.read_bytes()
    else:
        for attempt in range(3):
            try:
                with client.stream("GET", url) as response:
                    response.raise_for_status()
                    raw = bytearray()
                    for chunk in response.iter_bytes():
                        raw.extend(chunk)
                        if len(raw) > 20 * 1024**2:
                            raise ValueError("IMAGE_SIZE_LIMIT")
                raw = bytes(raw)
                validate_jpeg(raw, image)
                write_once(path, raw)
                break
            except httpx.HTTPError:
                if attempt == 2:
                    raise
                time.sleep(0.2 * (attempt + 1))
    validate_jpeg(raw, image)
    return {"filename": "images/" + name, "sha256": sha(raw), "bytes": len(raw), "url": url}


def download(output, cache, count=500, seed=42, workers=4, transport=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "images").mkdir(exist_ok=True)
    with httpx.Client(
        timeout=30,
        follow_redirects=False,
        transport=transport,
        headers={"User-Agent": "MultimodalImageSearch/phase08", "Accept-Encoding": "identity"},
        limits=httpx.Limits(max_connections=workers),
    ) as client:
        data, receipt = annotations(client, Path(cache))
        selected, captions, licenses = select_subset(data, count, seed)
        plan = {
            "source_dataset": SOURCE,
            "count": count,
            "seed": seed,
            "annotation_sha256": receipt["sha256"],
            "license_ids": sorted(ALLOWED_LICENSE_IDS),
            "image_ids": [item["id"] for item in selected],
        }
        write_once(output / "selection.json", encoded(plan))
        records = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for record in pool.map(lambda image: download_image(client, output, image), selected):
                records.append(record)
                if len(records) % 50 == 0:
                    print(
                        f"Downloaded/verified {len(records)}/{count}", file=sys.stderr, flush=True
                    )
    metadata, provenance = [], []
    for image, record in zip(selected, records, strict=True):
        caption = captions[image["id"]][0]
        license = licenses[image["license"]]
        metadata.append(
            {
                "filename": record["filename"],
                "source_dataset": SOURCE,
                "source_uri": record["url"],
                "license": license["url"],
                "rights_ref": image.get("flickr_url") or TERMS,
                "title": f"COCO val2017 {image['id']:012d}",
                "caption": caption["caption"].strip(),
                "caption_source": f"coco2017:captions_val2017:annotation:{caption['id']}",
                "tags": [],
            }
        )
        provenance.append(
            {
                **record,
                "source_id": f"coco2017:val2017:{image['id']}",
                "image": image,
                "image_license": license,
                "captions": captions[image["id"]],
                "annotation_receipt": receipt,
                "caption_origin": "imported_human_dataset_annotation",
                "locally_human_verified": False,
            }
        )
    raw = (
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in metadata) + "\n"
    ).encode()
    write_once(output / "metadata.jsonl", raw)
    write_once(output / "provenance.json", encoded(provenance))
    manifest = {
        **plan,
        "metadata_sha256": sha(raw),
        "images": records,
        "provenance_sha256": sha(encoded(provenance)),
        "caption_count": len(metadata),
        "total_image_bytes": sum(r["bytes"] for r in records),
        "rights_policy": (
            "keep per-image source/license; attribution in provenance; no redistribution"
        ),
        "local_human_review": "pending; dataset captions are not query relevance judgments",
    }
    write_once(output / "manifest.json", encoded(manifest))
    return {
        "status": "pass",
        "directory": str(output),
        "images": count,
        "manifest_sha256": sha(encoded(manifest)),
        "annotation_sha256": receipt["sha256"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="datasets/coco_phase08_v1")
    parser.add_argument("--cache", default=".cache/coco")
    parser.add_argument("--count", type=int, default=500, choices=range(1, 1001))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 5))
    args = parser.parse_args()
    result = download(args.output, args.cache, args.count, args.seed, args.workers)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
