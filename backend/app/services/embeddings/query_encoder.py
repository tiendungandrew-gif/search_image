"""Multilingual text paired with the existing fingerprinted CLIP image index."""

import json
from pathlib import Path
from time import perf_counter

from app.schemas.search import normalize_text
from app.services.embeddings.accent_restorer import AccentRestorer
from app.services.embeddings.clip_encoder import ClipEncoder, fingerprint
from app.services.embeddings.multilingual_encoder import MultilingualTextEncoder


class ClipQueryEncoder:
    def __init__(self, settings):
        started = perf_counter()
        if (
            settings.embedding_model_id != "openai/clip-vit-base-patch32"
            or settings.embedding_model_revision != "3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268"
        ):
            raise ValueError("MULTILINGUAL_IMAGE_SPACE_MISMATCH")
        self.base = ClipEncoder(settings)
        root = Path(settings.embedding_cache_dir)
        self.accent_restorer = AccentRestorer(
            root / "multilingual-text/vi-accent", json.loads((root / "vocab.json").read_text())
        )
        self.text_encoder = MultilingualTextEncoder(
            Path(settings.embedding_cache_dir) / "multilingual-text", self.base.device
        )
        self.dimension = self.base.dimension
        self.manifest_sha256 = self.base.manifest_sha256
        self.text_manifest = {
            **self.text_encoder.manifest,
            "accent_restoration": self.accent_restorer.manifest,
        }
        self.text_manifest_sha256 = fingerprint(self.text_manifest)
        self.initialization_ms = (perf_counter() - started) * 1000
        self.device = self.base.device

    def encode_text(self, texts):
        vectors = self.text_encoder.encode_text(self.normalize_texts(texts))
        self.last_metrics = self.text_encoder.last_metrics.copy()
        return vectors

    def normalize_texts(self, texts):
        return [self.accent_restorer.restore(normalize_text(text)) for text in texts]

    def encode_images(self, images):
        return self.base.encode_images(images)
