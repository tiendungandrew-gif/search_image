"""Conservative contextual accent restoration before multilingual CLIP encoding.

Architecture/data: ai4irl Clavi, Apache-2.0. Inference is implemented locally;
no downloaded Python is executed. Language ID: py3langid, BSD-3-Clause.
"""

import hashlib
import json
import re
from collections import OrderedDict
from pathlib import Path

from app.cli.download_accents import FILES, MODEL_ID, REVISION, verify
from app.services.query.language import language_identifier


class AccentRestorer:
    def __init__(self, root: Path, english_vocab: dict):
        import torch
        from safetensors.torch import load_file

        verify(root)
        config = json.loads((root / "config.json").read_text())
        vocab = json.loads((root / "vocab.json").read_text())
        if (
            config.get("architecture") != "AccentRestorationBiLSTM"
            or config.get("language") != "vi-VN"
            or config.get("format_version") != 1
            or config.get("vocab_size") != 211
            or config.get("hidden_dim") != 512
            or config.get("embedding_dim") != 192
            or config.get("num_layers") != 3
        ):
            raise ValueError("ACCENT_MODEL_ARCHITECTURE_MISMATCH")
        self.vocab = vocab["vocab"]
        self.char_ids = {ch: i for i, ch in enumerate(self.vocab)}
        self.unknown = self.char_ids[vocab["unk_token"]]
        self.padding = self.char_ids[vocab["pad_token"]]
        self.mask = torch.full((len(self.vocab), len(self.vocab)), -torch.inf)
        families = list(vocab["accent_families"].values())
        for ch, index in self.char_ids.items():
            family = next((group for group in families if ch in group), [ch])
            self.mask[index, [self.char_ids[c] for c in family]] = 0

        class Model(torch.nn.Module):
            def __init__(self, padding):
                super().__init__()
                self.embedding = torch.nn.Embedding(211, 192, padding_idx=padding)
                self.encoder = torch.nn.LSTM(
                    192, 512, num_layers=3, batch_first=True, bidirectional=True
                )
                self.head = torch.nn.Linear(1024, 211)

            def forward(self, ids):
                encoded, _ = self.encoder(self.embedding(ids))
                return self.head(encoded)

        self.model = Model(self.padding)
        self.model.load_state_dict(load_file(str(root / "model.safetensors")), strict=True)
        self.model.eval()
        self.language = language_identifier()
        self.english_vocab = english_vocab
        self.cache = OrderedDict()
        self.manifest = {
            "model_id": MODEL_ID,
            "revision": REVISION,
            "files": FILES,
            "language_id": "py3langid-0.4.0-en-vi",
            "policy": "ascii-short-contextual-conservative-v1",
            "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        }

    def restore(self, text: str) -> str:
        if text in self.cache:
            self.cache.move_to_end(text)
            return self.cache[text]
        result = self._restore(text)
        self.cache[text] = result
        if len(self.cache) > 256:
            self.cache.popitem(last=False)
        return result

    def _restore(self, text: str) -> str:
        # Do not reinterpret already accented text, long descriptions or operators.
        if (
            not text.isascii()
            or len(text) > 256
            or not re.fullmatch(r"[A-Za-z0-9\s.,!?-]+", text)
            or re.search(r"\b[A-Za-z]+[-_]?\d+\b|\b[A-Z]{2,}\s+\d+\b", text)
        ):
            return text
        language, confidence = self.language.classify(text)
        words = re.findall(r"[a-z]+", text.lower())
        common_english = bool(words) and all(
            self.english_vocab.get(word + "</w>", 50000) < 10000 for word in words
        )
        if language == "en" and (confidence >= 0.98 or common_english):
            return text
        import torch

        # Supply the task context missing from very short search fragments.
        prefix = "Tìm hình ảnh: "
        contextual = prefix + text
        ids = [self.char_ids.get(ch, self.unknown) for ch in contextual]
        values = torch.tensor([ids], dtype=torch.long)
        with torch.inference_mode():
            scores = (self.model(values)[0] + self.mask[values[0]])[len(prefix) :]
            probabilities = scores.softmax(dim=-1)
            predicted = scores.argmax(dim=-1).tolist()
        result = "".join(
            self.vocab[predicted[i]] if source != self.unknown else ch
            for i, (ch, source) in enumerate(zip(text, ids[len(prefix) :], strict=True))
        )
        changes = [i for i, (a, b) in enumerate(zip(text, result, strict=True)) if a != b]
        if not changes:
            return text
        # Abstain on uncertain spelling; names and ambiguous short words are common.
        if min(float(probabilities[i, predicted[i]]) for i in changes) < 0.55:
            return text
        restored_language, restored_confidence = self.language.classify(result)
        if restored_language != "vi" or restored_confidence < 0.75:
            return text
        return result
