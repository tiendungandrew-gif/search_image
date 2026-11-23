"""Download pinned Vietnamese accent-restoration data, never remote Python code."""

import argparse
import hashlib
import json
from pathlib import Path

MODEL_ID = "ai4irl/clavi-accent-restoration"
REVISION = "940c6d81842f88c0ca70b166a3031e0dd54e5dec"
FILES = {
    "config.json": "a9a981238294e1539b2b1b7dbe77f99dd271f9554580ac2bd530329b3597c60c",
    "vocab.json": "6cb82c63ef2f7e8c79c5d684d4390c49283d29ba0cb4dc4e3121cbf8eb5606a4",
    "model.safetensors": "7b12c43f0184054d61397e1dff1e0ede3e0afad80f85218d6b083fe55d2d8c14",
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(root):
    for name, expected in FILES.items():
        if digest(root / name) != expected:
            raise ValueError("ACCENT_MODEL_CACHE_CORRUPT")


def download(root):
    import httpx

    root.mkdir(parents=True, exist_ok=True)
    for name, expected in FILES.items():
        target = root / name
        if target.is_file() and digest(target) == expected:
            continue
        temporary = target.with_suffix(target.suffix + ".partial")
        url = f"https://huggingface.co/{MODEL_ID}/resolve/{REVISION}/vi-VN/{name}"
        try:
            with httpx.stream("GET", url, follow_redirects=True, timeout=60) as response:
                response.raise_for_status()
                with temporary.open("wb") as stream:
                    for chunk in response.iter_bytes(1024 * 1024):
                        stream.write(chunk)
            if digest(temporary) != expected:
                raise ValueError("ACCENT_MODEL_DOWNLOAD_CORRUPT")
            temporary.chmod(0o644)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    receipt = {"model_id": MODEL_ID, "revision": REVISION, "files": FILES}
    (root / "download.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"model_id": MODEL_ID, "revision": REVISION, "output": str(root)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    download(parser.parse_args().output)


if __name__ == "__main__":
    main()
