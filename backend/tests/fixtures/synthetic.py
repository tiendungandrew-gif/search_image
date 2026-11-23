import hashlib
import io

import numpy as np
from PIL import Image, ImageDraw

from app.services.embeddings.clip_encoder import fingerprint, normalized_vectors


def image_bytes(number=0, media="PNG"):
    with Image.new("RGB", (96, 80), (30 + number * 20, 40, 150)) as image:
        draw = ImageDraw.Draw(image)
        draw.rectangle((12, 12, 36 + number, 54), fill=(230, 150, 30))
        draw.line((0, number + 5, 95, 70), fill=(20, 220, 80), width=3)
        output = io.BytesIO()
        image.save(output, format=media)
        return output.getvalue()


class SyntheticEncoder:
    """Fake vector space for mechanics only; never installed in app runtime."""

    dimension = 8
    device = "test-double"
    initialization_ms = 0
    last_metrics = {}
    manifest = {
        "model_id": "qa/synthetic-digest-8",
        "revision": "fixture-v1",
        "processor_revision": "fixture-v1",
        "dimension": 8,
        "normalization": "l2",
        "distance": "cosine",
        "fixture": True,
        "license_ref": "fixture://generated-for-software-testing",
    }
    manifest_sha256 = fingerprint(manifest)

    def encode_images(self, images):
        rows = []
        for image in images:
            raw = hashlib.sha256(image.tobytes()).digest()[:8]
            rows.append(np.frombuffer(raw, dtype=np.uint8).astype(np.float32) + 1)
        return normalized_vectors(rows, self.dimension)
