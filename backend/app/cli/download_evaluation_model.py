"""Tải model nghiên cứu pinned riêng; không đổi cache/index CLIP đang active."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download

MODEL = "google/siglip2-base-patch16-224"
REVISION = "75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=".cache/siglip2")
    args = parser.parse_args()
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(root).free < 8 * 1024**3:
        raise ValueError("Need 8 GiB free disk")
    names = [
        "config.json",
        "preprocessor_config.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "tokenizer.json",
        "tokenizer.model",
        "model.safetensors",
        "README.md",
    ]
    info = HfApi().model_info(MODEL, revision=REVISION, files_metadata=True)
    size = sum(f.size or 0 for f in info.siblings if f.rfilename in names)
    if size > 2 * 1024**3:
        raise ValueError("Unexpected model download size")
    snapshot_download(MODEL, revision=REVISION, allow_patterns=names, local_dir=root, max_workers=2)
    hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names}
    for name in names:
        (root / name).chmod(0o644)
    value = {
        "model_id": MODEL,
        "revision": REVISION,
        "files": hashes,
        "license": "Apache-2.0",
        "download_bytes": size,
    }
    (root / "download.json").write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps({k: v for k, v in value.items() if k != "files"}, indent=2))


if __name__ == "__main__":
    main()
