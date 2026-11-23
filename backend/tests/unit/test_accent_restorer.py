from collections import OrderedDict
from types import SimpleNamespace

import pytest

from app.services.embeddings.accent_restorer import AccentRestorer


def restorer():
    instance = AccentRestorer.__new__(AccentRestorer)
    instance.cache = OrderedDict()
    instance.language = SimpleNamespace(classify=lambda text: ("en", 0.999))
    instance.english_vocab = {}
    return instance


@pytest.mark.parametrize(
    "query",
    [
        "con mèo",
        "mèo trên bàn",
        "city:hanoi",
        "COCO 123",
        "tag:cat AND dog",
        "name@example.com",
        "a" * 257,
    ],
)
def test_accent_restoration_preserves_accents_identifiers_and_operators(query):
    assert restorer().restore(query) == query


@pytest.mark.parametrize("query", ["a cat", "cat", "a red car", "cat sleeping on a bed"])
def test_accent_restoration_preserves_confident_english(query):
    assert restorer().restore(query) == query


def test_normalization_cache_is_bounded_and_keeps_recent_queries():
    instance = restorer()
    for i in range(300):
        instance.restore(f"image {i}")
    assert len(instance.cache) == 256
    assert "image 0" not in instance.cache
    assert instance.restore("image 299") == "image 299"
