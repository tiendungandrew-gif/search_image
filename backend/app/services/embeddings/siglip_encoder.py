"""Research-only paired SigLIP2 checkpoint; independent immutable manifest/index."""

import hashlib
import json
from pathlib import Path
from time import perf_counter

from app.services.embeddings.clip_encoder import fingerprint, normalized_vectors


class SiglipEncoder:
    def __init__(self, cache, threads=4):
        import torch
        import transformers
        from PIL import Image
        from transformers import AutoModel, AutoProcessor

        started = perf_counter()
        root = Path(cache)
        receipt = json.loads((root / "download.json").read_text())
        if (
            receipt["model_id"] != "google/siglip2-base-patch16-224"
            or receipt["revision"] != "75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2"
        ):
            raise ValueError("UNEXPECTED_RESEARCH_MODEL")
        for name, sha in receipt["files"].items():
            if hashlib.sha256((root / name).read_bytes()).hexdigest() != sha:
                raise ValueError("MODEL_CACHE_CORRUPT")
        torch.set_num_threads(threads)
        torch.manual_seed(0)
        torch.use_deterministic_algorithms(True)
        self.device = "cpu"
        self.model = (
            AutoModel.from_pretrained(
                root, local_files_only=True, use_safetensors=True, attn_implementation="eager"
            )
            .float()
            .eval()
        )
        self.processor = AutoProcessor.from_pretrained(root, local_files_only=True)
        self.tokenizer = self.processor.tokenizer
        with torch.inference_mode(), Image.new("RGB", (224, 224)) as image:
            image_value = self.model.get_image_features(
                **self.processor(images=[image], return_tensors="pt")
            )
            text_value = self.model.get_text_features(
                **self.processor(
                    text=["a photograph"],
                    padding="max_length",
                    max_length=64,
                    truncation=False,
                    return_tensors="pt",
                )
            )
        if image_value.ndim != 2 or image_value.shape != text_value.shape:
            raise ValueError("PAIRED_DIMENSION_MISMATCH")
        self.dimension = image_value.shape[-1]
        self.manifest = {
            "model_id": receipt["model_id"],
            "revision": receipt["revision"],
            "processor_revision": receipt["revision"],
            "files": receipt["files"],
            "dimension": self.dimension,
            "normalization": "l2",
            "precision": "float32",
            "distance": "cosine",
            "processor": self.processor.image_processor.to_dict(),
            "text_max_positions": 64,
            "text_padding": "max_length",
            "truncation": False,
            "device": "cpu",
            "attention": "eager",
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "encoder_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "decoder_code_sha256": hashlib.sha256(
                Path(__file__).parents[1].joinpath("ingestion/decoder.py").read_bytes()
            ).hexdigest(),
            "license_ref": "https://huggingface.co/google/siglip2-base-patch16-224",
        }
        self.manifest_sha256 = fingerprint(self.manifest)
        self.initialization_ms = (perf_counter() - started) * 1000
        self.last_metrics = {}

    def encode_text(self, texts):
        import torch

        from app.schemas.search import normalize_text

        texts = [normalize_text(text) for text in texts]
        tokens = self.tokenizer(
            texts, padding="max_length", max_length=64, truncation=False, return_tensors="pt"
        )
        if tokens["input_ids"].shape[1] > 64:
            raise ValueError("SIGLIP_TEXT_TOKEN_LIMIT")
        with torch.inference_mode():
            features = self.model.get_text_features(**tokens)
        return normalized_vectors(features.float().cpu().numpy(), self.dimension)

    def encode_images(self, images):
        import torch

        started = perf_counter()
        inputs = self.processor(images=images, return_tensors="pt")
        with torch.inference_mode():
            features = self.model.get_image_features(**inputs)
        vectors = normalized_vectors(features.float().cpu().numpy(), self.dimension)
        self.last_metrics = {"processor_inference_ms": (perf_counter() - started) * 1000}
        return vectors
