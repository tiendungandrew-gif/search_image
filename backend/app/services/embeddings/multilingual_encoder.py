"""Distilled multilingual text encoder aligned to OpenAI CLIP ViT-B/32 images."""

import hashlib
import json
from collections import OrderedDict
from pathlib import Path
from time import perf_counter

import numpy as np

from app.cli.download_multilingual import FILES, MODEL_ID, REVISION
from app.core.exceptions import AppError
from app.schemas.search import normalize_text
from app.services.embeddings.clip_encoder import fingerprint, normalized_vectors


def verified_receipt(root: Path):
    receipt = json.loads((root / "download.json").read_text())
    if receipt.get("model_id") != MODEL_ID or receipt.get("revision") != REVISION:
        raise ValueError("TEXT_MODEL_CACHE_MISMATCH")
    if set(receipt.get("files", {})) != set(FILES):
        raise ValueError("TEXT_MODEL_CACHE_INCOMPLETE")
    for name in FILES:
        with (root / name).open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != receipt["files"][name]:
            raise ValueError("TEXT_MODEL_CACHE_CORRUPT")
    return receipt


class MultilingualTextEncoder:
    def __init__(self, root: Path, device: str):
        import torch
        from safetensors.torch import load_file
        from transformers import AutoModel, AutoTokenizer

        receipt = verified_receipt(root)
        pooling = json.loads((root / "1_Pooling/config.json").read_text())
        dense = json.loads((root / "2_Dense/config.json").read_text())
        sentence = json.loads((root / "sentence_bert_config.json").read_text())
        if (
            pooling
            != {
                "word_embedding_dimension": 768,
                "pooling_mode_cls_token": False,
                "pooling_mode_mean_tokens": True,
                "pooling_mode_max_tokens": False,
                "pooling_mode_mean_sqrt_len_tokens": False,
            }
            or dense
            != {
                "in_features": 768,
                "out_features": 512,
                "bias": False,
                "activation_function": "torch.nn.modules.linear.Identity",
            }
            or sentence != {"max_seq_length": 128, "do_lower_case": False}
        ):
            raise ValueError("TEXT_MODEL_ARCHITECTURE_MISMATCH")
        self.device = device
        self.max_tokens = 128
        self.model = (
            AutoModel.from_pretrained(
                root, local_files_only=True, use_safetensors=True, attn_implementation="eager"
            )
            .to(device)
            .eval()
        )
        self.tokenizer = AutoTokenizer.from_pretrained(root, local_files_only=True)
        self.projection = torch.nn.Linear(768, 512, bias=False)
        weights = load_file(str(root / "2_Dense/model.safetensors"))
        if set(weights) != {"linear.weight"}:
            raise ValueError("TEXT_MODEL_PROJECTION_MISMATCH")
        self.projection.load_state_dict({"weight": weights["linear.weight"]})
        self.projection = self.projection.to(device).eval()
        self.manifest = {
            **receipt,
            "image_space": "openai/clip-vit-base-patch32",
            "pooling": "attention-mask-mean",
            "dimension": 512,
            "normalization": "l2",
            "max_tokens": self.max_tokens,
            "encoder_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        }
        self.manifest_sha256 = fingerprint(self.manifest)
        # Cache vectors only: retrieval and permissions are checked for each request.
        self.cache = OrderedDict()
        self.cache_capacity = 256

    def encode_text(self, texts: list[str]) -> np.ndarray:
        import torch

        started = perf_counter()
        if not texts:
            raise AppError(422, "INVALID_INPUT", "Cần ít nhất một truy vấn")
        texts = [normalize_text(text) for text in texts]
        missing = list(dict.fromkeys(text for text in texts if text not in self.cache))
        fresh = {}
        prepared = perf_counter()
        inferred = prepared
        if missing:
            values = self.tokenizer(missing, return_tensors="pt", padding=True, truncation=False)
            if values["input_ids"].shape[1] > self.max_tokens:
                raise AppError(
                    422,
                    "TEXT_TOKEN_LIMIT",
                    "Mô tả quá dài; hãy rút gọn để nằm trong giới hạn 128 token.",
                )
            values = {key: value.to(self.device) for key, value in values.items()}
            if self.device == "cuda":
                torch.cuda.synchronize()
            prepared = perf_counter()
            with torch.inference_mode():
                tokens = self.model(**values).last_hidden_state
                mask = values["attention_mask"].unsqueeze(-1).to(tokens.dtype)
                pooled = (tokens * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
                features = self.projection(pooled)
            if self.device == "cuda":
                torch.cuda.synchronize()
            inferred = perf_counter()
            vectors = normalized_vectors(features.float().cpu().numpy(), 512)
            fresh = dict(zip(missing, vectors, strict=True))
        result = np.stack([fresh[text] if text in fresh else self.cache[text] for text in texts])
        for text in texts:
            if text in fresh:
                self.cache[text] = fresh[text].copy()
            self.cache.move_to_end(text)
        while len(self.cache) > self.cache_capacity:
            self.cache.popitem(last=False)
        self.last_metrics = {
            "text_preprocessing_ms": (prepared - started) * 1000,
            "text_forward_ms": (inferred - prepared) * 1000,
            "text_cache_hits": len(texts) - sum(text in fresh for text in texts),
        }
        return result
