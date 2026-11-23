import unicodedata
from types import SimpleNamespace

import pytest

from app.services.query import language
from app.services.query.query_classifier import analyze_query


@pytest.mark.parametrize("text", ["phở gà", "PHỞ GÀ", unicodedata.normalize("NFD", "hồ bơi")])
def test_vietnamese_unicode_forms(text):
    assert language.detect_language(text) == "vi"


@pytest.mark.parametrize("text", ["pho ga", "bun bo", "con meo"])
def test_ambiguous_ascii_is_not_assumed_english(monkeypatch, text):
    monkeypatch.setattr(language, "language_identifier", lambda: SimpleNamespace(
        classify=lambda _: ("en", 0.65)
    ))
    assert analyze_query(text, False, parse=False).language == "und"


@pytest.mark.parametrize("detected", ["en", "vi"])
def test_confident_language_evidence(monkeypatch, detected):
    monkeypatch.setattr(language, "language_identifier", lambda: SimpleNamespace(
        classify=lambda _: (detected, 0.99)
    ))
    assert language.detect_language("example words") == detected


def test_language_without_optional_ml_or_text(monkeypatch):
    monkeypatch.setattr(language, "language_identifier", lambda: None)
    for text in ["", "123", "red car"]:
        assert language.detect_language(text) == "und"


@pytest.mark.parametrize(("query", "expected"), [
    ("tìm ảnh phở gà", "phở gà"),
    ("tim anh pho ga", "pho ga"),
    ("Tìm kiếm hình ảnh hồ bơi", "hồ bơi"),
    ("tìm cho tôi ảnh con mèo", "con mèo"),
    ("show me pictures of a red car", "a red car"),
    ("find photos of cats and dogs", "cats and dogs"),
    ("ảnh viện áo cưới", "ảnh viện áo cưới"),
    ("anh trai và em gái", "anh trai và em gái"),
    ("city:Hanoi AND tag:cat", "city:Hanoi AND tag:cat"),
    ("phố cổ Hà Nội", "phố cổ Hà Nội"),
])
def test_search_subject_removes_only_explicit_request(query, expected):
    assert language.search_subject(query) == expected
