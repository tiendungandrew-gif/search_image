"""Tải explicit CLIP checkpoint pinned; chuyển weights_only state dict sang safetensors."""

import argparse
import hashlib
import json
from pathlib import Path

from huggingface_hub import snapshot_download


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    model = "openai/clip-vit-base-patch32"
    revision = "3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268"
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=True)
    files = [
        "config.json",
        "preprocessor_config.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "vocab.json",
        "merges.txt",
        "pytorch_model.bin",
        "README.md",
    ]
    snapshot_download(model, revision=revision, allow_patterns=files, local_dir=root, max_workers=2)
    import torch
    from safetensors.torch import save_file

    state = torch.load(root / "pytorch_model.bin", map_location="cpu", weights_only=True)
    save_file(
        {key: value.contiguous() for key, value in state.items()},
        str(root / "model.safetensors"),
        metadata={"format": "pt"},
    )
    hashes = {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in [*files, "model.safetensors"]
    }
    # Public pretrained weights, readable bởi non-root worker UID trong container.
    for name in hashes:
        (root / name).chmod(0o644)
    (root / "download.json").write_text(
        json.dumps({"model_id": model, "revision": revision, "files": hashes}, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "model_id": model,
                "revision": revision,
                "file_count": len(hashes),
                "output": str(root),
            }
        )
    )


if __name__ == "__main__":
    main()
