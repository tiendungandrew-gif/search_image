"""Paired text/image query wrapper; không sửa fingerprint image encoder Prompt04."""

from time import perf_counter

import numpy as np

from app.core.exceptions import AppError
from app.schemas.search import normalize_text
from app.services.embeddings.clip_encoder import ClipEncoder, normalized_vectors


class ClipQueryEncoder:
    def __init__(self, settings):
        from transformers import CLIPTokenizerFast

        started = perf_counter()
        self.base = ClipEncoder(settings)
        self.tokenizer = CLIPTokenizerFast.from_pretrained(
            settings.embedding_cache_dir, local_files_only=True
        )
        self.dimension = self.base.dimension
        self.manifest_sha256 = self.base.manifest_sha256
        self.initialization_ms = (perf_counter() - started) * 1000
        self.device = self.base.device

    def encode_text(self, texts: list[str]) -> np.ndarray:
        import torch

        started = perf_counter()
        if not texts:
            raise AppError(422, "INVALID_INPUT", "Cần ít nhất một truy vấn")
        texts = [normalize_text(text) for text in texts]
        values = self.tokenizer(texts, return_tensors="pt", padding=True, truncation=False)
        if (
            values["input_ids"].shape[1]
            > self.base.model.config.text_config.max_position_embeddings
        ):
            raise AppError(
                422,
                "TEXT_TOKEN_LIMIT",
                "Truy vấn vượt token limit của CLIP; không truncate tự động",
            )
        values = {key: value.to(self.device) for key, value in values.items()}
        if self.device == "cuda":
            torch.cuda.synchronize()
        prepared = perf_counter()
        with torch.inference_mode():
            features = self.base.model.get_text_features(**values)
        if self.device == "cuda":
            torch.cuda.synchronize()
        inferred = perf_counter()
        vector = normalized_vectors(features.float().cpu().numpy(), self.dimension)
        self.last_metrics = {
            "text_preprocessing_ms": (prepared - started) * 1000,
            "text_forward_ms": (inferred - prepared) * 1000,
        }
        return vector

    def encode_images(self, images):
        return self.base.encode_images(images)
