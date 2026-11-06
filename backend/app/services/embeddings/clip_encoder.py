"""CLIP thật, local cache only; tải weights bằng CLI riêng trước khi chạy worker."""

import hashlib
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from PIL.Image import Image


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def normalized_vectors(values, dimension):
    values = np.asarray(values, dtype=np.float32)
    if values.ndim != 2 or values.shape[1] != dimension or not np.isfinite(values).all():
        raise ValueError("INVALID_VECTOR")
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    if not np.isfinite(norms).all() or (norms <= 1e-12).any():
        raise ValueError("ZERO_VECTOR")
    return values / norms


class ClipEncoder:
    def __init__(self, settings):
        import torch
        import transformers
        from transformers import CLIPImageProcessor, CLIPModel

        start = perf_counter()
        root = Path(settings.embedding_cache_dir)
        receipt = json.loads((root / "download.json").read_text())
        if (
            receipt["model_id"] != settings.embedding_model_id
            or receipt["revision"] != settings.embedding_model_revision
        ):
            raise ValueError("MODEL_CACHE_MISMATCH")
        for name, digest in receipt["files"].items():
            path = root / name
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError("MODEL_CACHE_CORRUPT")
        self.device = (
            "cuda"
            if settings.embedding_device == "auto" and torch.cuda.is_available()
            else settings.embedding_device
        )
        if self.device == "auto":
            self.device = "cpu"
        if self.device == "cuda" and not torch.cuda.is_available():
            raise ValueError("CUDA_UNAVAILABLE")
        torch.set_num_threads(settings.embedding_cpu_threads)
        torch.manual_seed(0)
        torch.use_deterministic_algorithms(True)
        self.model = (
            CLIPModel.from_pretrained(
                root, local_files_only=True, use_safetensors=True, attn_implementation="eager"
            )
            .to(self.device)
            .eval()
        )
        self.processor = CLIPImageProcessor.from_pretrained(root, local_files_only=True)
        self.dimension = int(self.model.config.projection_dim)
        self.manifest = {
            "model_id": settings.embedding_model_id,
            "revision": settings.embedding_model_revision,
            "processor_revision": settings.embedding_model_revision,
            "dimension": self.dimension,
            "precision": "float32",
            "normalization": "l2",
            "distance": "cosine",
            "processor": self.processor.to_dict(),
            "files": receipt["files"],
            "alpha": "white",
            "exif": "transpose",
            "canonical_vector": "float32-le-l2-v1",
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "device": self.device,
            "attention": "eager",
            "encoder_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "decoder_code_sha256": hashlib.sha256(
                Path(__file__).parents[1].joinpath("ingestion/decoder.py").read_bytes()
            ).hexdigest(),
        }
        self.manifest_sha256 = fingerprint(self.manifest)
        self.initialization_ms = (perf_counter() - start) * 1000

    def encode_images(self, images: list[Image]) -> np.ndarray:
        import torch

        started = perf_counter()
        values = None
        features = None
        try:
            values = self.processor(images=images, return_tensors="pt")["pixel_values"].to(
                self.device
            )
            if self.device == "cuda":
                torch.cuda.synchronize()
            prepared_at = perf_counter()
            with torch.inference_mode():
                features = self.model.get_image_features(pixel_values=values)
            if self.device == "cuda":
                torch.cuda.synchronize()
            inferred_at = perf_counter()
            vectors = normalized_vectors(features.float().cpu().numpy(), self.dimension)
            self.last_metrics = {
                "processor_ms": (prepared_at - started) * 1000,
                "inference_ms": (inferred_at - prepared_at) * 1000,
                "normalization_transfer_ms": (perf_counter() - inferred_at) * 1000,
            }
            return vectors
        except torch.cuda.OutOfMemoryError:
            del values, features
            torch.cuda.empty_cache()
            if len(images) == 1:
                raise
            middle = len(images) // 2
            return np.concatenate(
                [self.encode_images(images[:middle]), self.encode_images(images[middle:])]
            )
