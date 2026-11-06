from typing import Protocol

import numpy as np
from PIL.Image import Image


class ImageEncoder(Protocol):
    dimension: int
    manifest: dict
    manifest_sha256: str
    initialization_ms: float
    device: str
    last_metrics: dict[str, float]

    def encode_images(self, images: list[Image]) -> np.ndarray: ...
