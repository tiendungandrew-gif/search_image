import hashlib
import json
from types import SimpleNamespace

import pytest

from app.cli.download_multilingual import FILES, MODEL_ID, REVISION
from app.services.embeddings.multilingual_encoder import verified_receipt
from app.services.embeddings.query_encoder import ClipQueryEncoder


@pytest.fixture
def model_cache(tmp_path):
    hashes = {}
    for name in FILES:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture: " + name.encode())
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    receipt = {"model_id": MODEL_ID, "revision": REVISION, "files": hashes}
    (tmp_path / "download.json").write_text(json.dumps(receipt))
    return tmp_path, receipt


def test_text_cache_checks_every_required_file(model_cache):
    root, receipt = model_cache
    assert verified_receipt(root) == receipt
    (root / "2_Dense/model.safetensors").write_bytes(b"tampered projection")
    with pytest.raises(ValueError, match="TEXT_MODEL_CACHE_CORRUPT"):
        verified_receipt(root)


@pytest.mark.parametrize(
    "model,revision",
    [
        ("another/512-dimensional-model", "3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268"),
        ("openai/clip-vit-base-patch32", "0" * 40),
    ],
)
def test_multilingual_requires_the_aligned_image_checkpoint(model, revision):
    with pytest.raises(ValueError, match="MULTILINGUAL_IMAGE_SPACE_MISMATCH"):
        ClipQueryEncoder(
            SimpleNamespace(
                embedding_model_id=model,
                embedding_model_revision=revision,
            )
        )


@pytest.mark.parametrize("change", ["revision", "missing", "extra"])
def test_text_cache_rejects_wrong_revision_or_file_set(model_cache, change):
    root, receipt = model_cache
    if change == "revision":
        receipt["revision"] = "0" * 40
    elif change == "missing":
        receipt["files"].pop("tokenizer.json")
    else:
        receipt["files"]["../outside"] = "0" * 64
    (root / "download.json").write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="TEXT_MODEL_CACHE_(MISMATCH|INCOMPLETE)"):
        verified_receipt(root)
