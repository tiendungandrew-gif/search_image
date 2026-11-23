"""Local real-weight EN/VI smoke and cache checks; no server or database writes."""

import json
import sys
import unicodedata
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import Settings  # noqa: E402
from app.core.exceptions import AppError  # noqa: E402
from app.services.embeddings.query_encoder import ClipQueryEncoder  # noqa: E402


def main():
    model_settings = {
        key: field.default
        for key, field in Settings.model_fields.items()
        if key.startswith("embedding_")
    }
    model_settings["embedding_cache_dir"] = str(ROOT / ".cache/clip")
    encoder = ClipQueryEncoder(SimpleNamespace(**model_settings))
    text = encoder.text_encoder
    unaccented = {
        "con meo": "con mèo",
        "con  meo": "con mèo",
        "meo": "mèo",
        "mot con meo mau nau": "một con mèo màu nâu",
        "con cho": "con chó",
        "2 con meo": "2 con mèo",
        "con ngua": "con ngựa",
        "bai bien": "bãi biển",
        "hoa hong": "hoa hồng",
        "ngoi nha": "ngôi nhà",
        "xe hoi": "xe hơi",
    }
    for source, expected in unaccented.items():
        assert encoder.normalize_texts([source]) == [expected], source
        np.testing.assert_array_equal(
            encoder.encode_text([source]), encoder.encode_text([expected])
        )
    for english in ["cat", "a cat", "dog", "horse", "red car", "a cup of coffee", "con artist"]:
        assert encoder.normalize_texts([english]) == [english]
    paths = sorted(
        p for p in (ROOT / "datasets/sample").iterdir() if p.suffix.lower() in {".png", ".jpg"}
    )
    images = []
    for path in paths:
        with Image.open(path) as image:
            images.append(image.convert("RGB"))
    try:
        image_vectors = encoder.encode_images(images)
    finally:
        for image in images:
            image.close()
    pairs = [
        ("a cup of coffee", "một tách cà phê", "coffee.png"),
        ("a brown cat", "một con mèo màu nâu", "chelsea.png"),
        ("a rocket launching into the sky", "tên lửa phóng lên bầu trời", "rocket.jpg"),
        (
            "stars and galaxies in deep space",
            "các ngôi sao và thiên hà trong vũ trụ",
            "hubble_deep_field.jpg",
        ),
        ("a horse", "một con ngựa", "horse.png"),
    ]
    rows = []
    import torch
    from transformers import CLIPTokenizerFast

    tokenizer = CLIPTokenizerFast.from_pretrained(ROOT / ".cache/clip", local_files_only=True)
    for english, vietnamese, expected in pairs:
        timings = []
        vectors = []
        for query in (english, vietnamese):
            start = perf_counter()
            vectors.append(encoder.encode_text([query])[0])
            timings.append((perf_counter() - start) * 1000)
        values = tokenizer([english], return_tensors="pt").to(encoder.device)
        with torch.inference_mode():
            native = encoder.base.model.get_text_features(**values).cpu().numpy()[0]
        native /= np.linalg.norm(native)
        ranked = [paths[int(np.argmax(image_vectors @ vector))].name for vector in vectors]
        assert ranked == [expected, expected], (english, ranked)
        rows.append(
            {
                "en": english,
                "vi": vietnamese,
                "expected": expected,
                "top1_en_vi": ranked,
                "native_english_top1": paths[int(np.argmax(image_vectors @ native))].name,
                "en_vi_cosine": float(vectors[0] @ vectors[1]),
                "uncached_ms_en_vi": timings,
            }
        )
    # Same query in a padded batch must match independent encoding.
    text.cache.clear()
    together = encoder.encode_text([pairs[0][0], pairs[2][1]])
    text.cache.clear()
    independent = np.stack([encoder.encode_text([q])[0] for q in (pairs[0][0], pairs[2][1])])
    np.testing.assert_allclose(together, independent, atol=1e-6)
    start = perf_counter()
    cached = encoder.encode_text([pairs[2][1]])
    cached_ms = (perf_counter() - start) * 1000
    assert encoder.last_metrics["text_cache_hits"] == 1
    cached[:] = 0
    assert np.linalg.norm(encoder.encode_text([pairs[2][1]])[0]) > 0.99
    nfc = encoder.encode_text([pairs[2][1]])
    nfd = encoder.encode_text([unicodedata.normalize("NFD", pairs[2][1])])
    np.testing.assert_array_equal(nfc, nfd)
    text.cache_capacity = 2
    batch = encoder.encode_text(["cat", "coffee", "horse", "rocket"])
    assert batch.shape == (4, 512) and len(text.cache) == 2
    try:
        encoder.encode_text(["coffee " * 150])
    except AppError as error:
        assert error.code == "TEXT_TOKEN_LIMIT"
    else:
        raise AssertionError("Long queries must not be silently truncated")
    report = {
        "scope": "5 curated pairs over 10 local sample images; smoke, not a quality benchmark",
        "image_manifest_sha256": encoder.manifest_sha256,
        "text_manifest": encoder.text_manifest,
        "text_manifest_sha256": encoder.text_manifest_sha256,
        "unaccented_pairs": unaccented,
        "pairs": rows,
        "cached_text_ms": cached_ms,
        "padding_cache_eviction_copy_unicode_token_limit": "passed",
    }
    output = ROOT / "docs/verification/bilingual/model.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps({"pairs_passed": len(rows), "cached_text_ms": cached_ms, "report": str(output)})
    )


if __name__ == "__main__":
    main()
