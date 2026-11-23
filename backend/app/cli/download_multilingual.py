"""Prepare pinned multilingual CLIP text weights; runtime never downloads models."""

import argparse
import hashlib
import json
from pathlib import Path

MODEL_ID = "sentence-transformers/clip-ViT-B-32-multilingual-v1"
REVISION = "58edf8cada9e398793dca955574a48cbb7f18be2"
FILES = (
    "config.json",
    "config_sentence_transformers.json",
    "model.safetensors",
    "modules.json",
    "sentence_bert_config.json",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.txt",
    "1_Pooling/config.json",
    "2_Dense/config.json",
    "2_Dense/model.safetensors",
)


def download(output: Path):
    from huggingface_hub import snapshot_download

    output.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        MODEL_ID, revision=REVISION, allow_patterns=list(FILES), local_dir=output, max_workers=2
    )
    hashes = {}
    for name in FILES:
        path = output / name
        with path.open("rb") as stream:
            hashes[name] = hashlib.file_digest(stream, "sha256").hexdigest()
        path.chmod(0o644)
    receipt = {"model_id": MODEL_ID, "revision": REVISION, "files": hashes}
    (output / "download.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"model_id": MODEL_ID, "revision": REVISION, "output": str(output)}))
    from app.cli.download_accents import download as download_accents

    download_accents(output / "vi-accent")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    download(parser.parse_args().output)


if __name__ == "__main__":
    main()
