from uuid import UUID

import pytest

from app.services.search.text_matching import (
    accented_words,
    fold_text,
    hybrid_rank,
    matches_name,
    requires_food_phrase,
)
from app.services.search.vector_retriever import Candidate


@pytest.mark.parametrize("query", ["pho 10 ly quoc su", "PHỞ 10 LÝ QUỐC SƯ", "phở 10 lý quốc sư"])
def test_proper_name_matches_accents_and_original_number(query):
    assert matches_name(query, ["Phở 10 Lý Quốc Sư Hà Nội"])
    assert not matches_name(query, ["Phở 100 Lý Quốc Sư Hà Nội"])
    assert not matches_name(query, ["Tượng đài Lý Quốc Sư"])


def test_fold_decomposed_vietnamese_and_punctuation():
    assert fold_text("Đà Nẵng — Phở 10") == "da nang pho 10"
    assert fold_text("Pho\u031b\u0309 10 Ly\u0301 Quo\u0302\u0301c Su\u031b") == "pho 10 ly quoc su"


def test_short_generic_fragments_do_not_override_visual_search():
    assert not matches_name("khach san", ["Khách sạn Metropole Hà Nội"])
    assert not matches_name("pho", ["Phở 10 Lý Quốc Sư"])
    assert matches_name("pho ly quoc su", ["Phở 10 Lý Quốc Sư Hà Nội"])


def test_explicit_accents_do_not_confuse_distinct_vietnamese_words():
    assert accented_words("Phở phố phổ PHỞ") == ["phở", "phố", "phổ"]
    assert accented_words("pho pho pho") == []
    assert not matches_name("phố 10 lý quốc sư", ["Phở 10 Lý Quốc Sư Hà Nội"])
    assert not matches_name("phở cổ hội an", ["Phố cổ Hội An"])
    assert matches_name("pho co hoi an", ["Phố cổ Hội An"])


def test_hybrid_adds_missing_text_candidates_and_deduplicates():
    a, b, c = (UUID(int=n) for n in [1, 2, 3])
    text = [Candidate(a, 0.5, {}), Candidate(b, 0.4, {})]
    visual = [Candidate(b, 0.9, {}), Candidate(c, 0.8, {})]
    output = hybrid_rank(text, visual)
    assert [item.image_id for item in output] == [b, a, c]
    assert output[0].score_components == {"text_rank": 0.4, "visual_cosine": 0.9}
    assert len(hybrid_rank(text, visual, limit=1)) == 1


@pytest.mark.parametrize("query", ["phở gà", "pho ga", "PHỞ GÀ", "phở ga"])
def test_compound_phrase_keeps_adjacent_words_and_explicit_accents(query):
    from app.services.search.text_matching import matches_phrase

    assert matches_phrase(query, ["Tô phở gà nóng với rau thơm"])
    assert not matches_phrase(query, ["Bát phở bò với trứng gà"])
    assert not matches_phrase(query, ["Đàn gà đứng trên sân"])
    assert not matches_phrase(query, ["Tô phở", "Gà luộc trên bàn"])


def test_phrase_matching_preserves_accents_and_does_not_match_word_fragments():
    from app.services.search.text_matching import matches_phrase

    assert not matches_phrase("phở gà", ["Phố gà và một quán phở bò"])
    assert not matches_phrase("pho ga", ["Phở gan và rau thơm"])
    assert matches_phrase("hồ bơi vô cực", ["Hồ bơi vô cực nhìn ra biển"])
    assert matches_phrase("bún bò", ["Bún bò Huế cay thơm"])
    assert not matches_phrase("phở và gà", ["Phở và gà luộc trên bàn"])


def test_phrase_policy_excludes_single_terms_filters_and_explicit_conjunctions():
    from app.services.search.text_matching import short_phrase

    assert short_phrase("phở gà")
    assert short_phrase("ho boi vo cuc")
    for query in ["phở", "phở hoặc gà", "phở và gà", "pho va ga", "city: Ha Noi"]:
        assert not short_phrase(query)


@pytest.mark.parametrize("query", [
    "bun ga", "BÚN GÀ", "bún ga?", "bún gà", "phở gà", "pho ga",
    "bun bo hue", "cơm gà", "cháo gà", "miến gà",
])
def test_dish_concepts_require_phrase_evidence_even_without_matches(query):
    assert requires_food_phrase(query)


@pytest.mark.parametrize("query", [
    "con gà", "ga", "phố gà", "phở và gà", "pho or ga", "city:hanoi",
    "hồ bơi", "red chicken", "bún không có gà", "còm gà",
])
def test_food_policy_does_not_reinterpret_animals_accents_or_explicit_logic(query):
    assert not requires_food_phrase(query)
