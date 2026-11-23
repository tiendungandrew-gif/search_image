#!/usr/bin/env python3
"""Tải explicit 10 ảnh CC0/public-domain từ scikit-image v0.25.2 và kiểm SHA upstream."""

import ast
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

BASE = "https://raw.githubusercontent.com/scikit-image/scikit-image/v0.25.2/skimage/"
SAMPLES = {
    "camera.png": "CC0-1.0",
    "brick.png": "CC0-1.0",
    "grass.png": "CC0-1.0",
    "gravel.png": "CC0-1.0",
    "coffee.png": "CC0-1.0",
    "chelsea.png": "CC0-1.0",
    "horse.png": "CC0-1.0",
    "rocket.jpg": "public-domain",
    "clock_motion.png": "public-domain",
    "hubble_deep_field.jpg": "public-domain",
}


def main():
    root = Path("datasets/sample")
    root.mkdir(parents=True, exist_ok=True)
    with urlopen(BASE + "data/_registry.py", timeout=30) as response:
        registry_source = response.read().decode()
    tree = ast.parse(registry_source)
    registry = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "registry" for t in node.targets)
    )
    rows = []
    for name, license in SAMPLES.items():
        url = BASE + "data/" + name
        with urlopen(url, timeout=60) as response:
            data = response.read(20 * 1024**2)
        digest = hashlib.sha256(data).hexdigest()
        assert digest == registry["data/" + name], name
        target = root / name
        if target.exists() and target.read_bytes() != data:
            raise RuntimeError("Refuse overwrite changed sample: " + name)
        target.write_bytes(data)
        rows.append(
            {
                "filename": name,
                "source_dataset": "scikit-image-v0.25.2",
                "source_uri": url,
                "license": license,
                "rights_ref": BASE + "data/_fetchers.py",
                "sha256": digest,
            }
        )
    (root / "metadata.jsonl").write_text(
        "".join(json.dumps({k: v for k, v in row.items() if k != "sha256"}) + "\n" for row in rows)
    )
    Path("datasets/sample_manifest.json").write_text(
        json.dumps(
            {
                "source_version": "v0.25.2",
                "rights_notes": BASE + "data/_fetchers.py",
                "images": rows,
            },
            indent=2,
        )
        + "\n"
    )
    print("Verified 10 sample images; no generated captions/tags")


if __name__ == "__main__":
    main()
