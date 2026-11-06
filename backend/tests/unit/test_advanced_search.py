"""Fixtures logic/scoring có kỳ vọng tính tay; không là human relevance labels."""

from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.core.exceptions import AppError
from app.schemas.constraints import ConstraintGroup, ConstraintLeaf, leaves
from app.schemas.search import Filters, FusionOptions, SearchRequest
from app.services.query.query_classifier import analyze_query
from app.services.search.evidence import assessments, evaluate_required, metadata_status
from app.services.search.fusion import fuse
from app.services.search.reranker import LightweightReranker, semantic_relevance
from app.services.search.vector_retriever import Candidate


@pytest.mark.parametrize(
    "text,language,count",
    [
        (
            "Find images containing a red motorcycle, "
            "a person wearing a helmet, and rainy weather.",
            "en",
            3,
        ),
        ("Tìm ảnh có xe máy màu đỏ và người đội mũ bảo hiểm", "vi", 2),
        ("coffee or cat", "en", 2),
        ("Tìm ảnh có mèo hoặc cà phê", "vi", 2),
        ("cat and coffee and rocket and stars", "en", 4),
    ],
)
def test_supported_languages_and_complete_original(text, language, count):
    result = analyze_query(text, False)
    assert result.query_type == "MULTI_INTENT" and result.language == language
    assert result.original_query == text and len(leaves(result.constraints)) == count


def test_boolean_precedence_and_phrase_preservation():
    tree = analyze_query(
        "(red motorcycle and person wearing red helmet) or blue bicycle", False
    ).constraints
    assert tree.op == "or" and tree.clauses[0].op == "and"
    assert leaves(tree)[1].text == "person wearing red helmet"
    assert analyze_query("a person wearing a red helmet", False).query_type == "SINGLE_INTENT"


@pytest.mark.parametrize(
    "text", ["black and white cat", "cat and", '"cat and coffee"', "cat (coffee"]
)
def test_ambiguous_query_retains_whole_signal(text):
    result = analyze_query(text, False)
    assert result.uncertain and result.original_query == text and result.constraints is None


def test_optional_negative_and_no_agent_fabrication():
    result = analyze_query("red car without people and preferably sunshine", False)
    items = leaves(result.constraints)
    assert [(c.text, c.negated, c.required) for c in items] == [
        ("red car", False, True),
        ("people", True, True),
        ("sunshine", False, False),
    ]
    assert analyze_query(
        "Find landmarks in the city where Hoan Kiem Lake is located", False
    ).requires_agent
    assert analyze_query("Tìm thắng cảnh ở thành phố nơi hồ tọa lạc", False).requires_agent
    assert analyze_query(None, True).query_type == "IMAGE_SIMILARITY"
    assert analyze_query("coffee", True).query_type == "TEXT_IMAGE"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"constraints": {"id": "whole", "kind": "semantic", "text": "cat"}},
        {"constraints": {"id": "image", "kind": "semantic", "text": "cat"}},
        {"fusion_strategy": "unknown"},
        {"text_weight": -1},
        {"text_weight": float("nan")},
        {"fusion": {"method": "rrf", "text_weight": 0.0, "image_weight": 0.0}},
        {"fusion_strategy": "rrf", "fusion": {"method": "rrf"}},
        {"rerank": {"enabled": True, "timeout_ms": 0}},
        {
            "constraints": {
                "op": "and",
                "clauses": [
                    {"id": "x", "kind": "semantic", "text": "a"},
                    {"id": "x", "kind": "semantic", "text": "b"},
                ],
            }
        },
    ],
)
def test_advanced_request_validation(kwargs):
    with pytest.raises(ValidationError):
        SearchRequest(text="coffee", **kwargs)


def test_constraint_count_depth_and_unicode():
    with pytest.raises(AppError):
        analyze_query(" and ".join(["cat"] * 9), False)
    with pytest.raises(ValidationError):
        SearchRequest(
            text="cat",
            constraints={
                "op": "and",
                "clauses": [
                    {"id": "x", "kind": "semantic", "text": "bad\x00text"},
                    {"id": "y", "kind": "semantic", "text": "cat"},
                ],
            },
        )
    result = SearchRequest(query="  ca\u0300   phe\u0302 ", search_mode="multi_intent", rerank=True)
    assert result.text == "cà phê" and result.rerank.enabled
    assert FusionOptions(text_weight=0.2, image_weight=0.8).text_weight == 0.2


def test_metadata_expression_limit_is_input_error():
    with pytest.raises(AppError) as error:
        analyze_query("city:" + "x" * 129, False)
    assert error.value.status == 422 and error.value.code == "INVALID_INPUT"


def test_rrf_formula_duplicate_tie_and_weighted_missing_branch():
    a, b = UUID(int=1), UUID(int=2)
    branches = {
        "text": [Candidate(a, 0.8, {}), Candidate(a, 0.7, {}), Candidate(b, 0.4, {})],
        "image": [Candidate(b, 0.9, {})],
    }
    rows = fuse(branches, {"text": 0.5, "image": 0.5}, "rrf", 60, 100)
    assert [r.image_id for r in rows] == [b, a]
    assert rows[0].score == pytest.approx(0.5 / 62 + 0.5 / 61)
    assert len(rows[0].contributions) == 2
    scores = fuse(branches, {"text": 0.5, "image": 0.5}, "weighted_score", 60, 100)
    assert next(r.score for r in scores if r.image_id == a) == pytest.approx(0.5 * (0.8 + 1) / 2)
    tied = fuse(
        {"x": [Candidate(b, 0.5, {}), Candidate(a, 0.5, {})]}, {"x": 1}, "weighted_score", 60, 1
    )
    assert tied[0].image_id == a
    assert fuse({"x": [], "y": []}, {"x": 1, "y": 0}, "rrf", 60, 100) == []


def test_metadata_unknown_negative_and_optional_gate():
    image = SimpleNamespace(id=UUID(int=1), width=600, height=400, media_type="image/png")
    meta = SimpleNamespace(city=None, source_dataset="sample", captured_at=None)
    assert metadata_status(Filters(city="Hanoi"), image, meta, []) == "unknown"
    assert metadata_status(Filters(tags_all=["cat"]), image, meta, []) == "unknown"
    assert metadata_status(Filters(min_width=700), image, meta, []) == "violated"
    tree = analyze_query("city:Hanoi and preferably tag:cat", False).constraints
    evidence = assessments(tree, (image, meta), [], {})
    assert evaluate_required(tree, {r["clause_id"]: r["status"] for r in evidence}) == "unknown"
    semantic = ConstraintLeaf(id="s", kind="semantic", text="people", negated=True)
    assert assessments(semantic, (image, meta), [], {"s": -0.99})[0]["status"] == "unknown"
    or_tree = ConstraintGroup(
        op="or",
        clauses=[
            ConstraintLeaf(id="required", kind="semantic", text="cat"),
            ConstraintLeaf(id="optional", kind="semantic", text="rain", required=False),
        ],
    )
    assert (
        evaluate_required(or_tree, {"required": "violated", "optional": "satisfied"}) == "violated"
    )


def test_and_or_semantic_ranking_different_from_verified_evidence(settings):
    and_tree = analyze_query("cat and coffee", False).constraints
    or_tree = analyze_query("cat or coffee", False).constraints
    values = {"q1": 0.9, "q2": -0.9}
    assert semantic_relevance(and_tree, values)[0] == pytest.approx(0.275)
    assert semantic_relevance(or_tree, values)[0] == pytest.approx(0.95)
    candidate = fuse({"x": [Candidate(UUID(int=1), 0.8, {})]}, {"x": 1}, "rrf", 60, 10)[0]
    candidate.assessments = [
        {"required": True, "status": "unknown", "evidence_kind": "semantic_similarity"}
    ]
    reranked = LightweightReranker(settings).rank(
        [candidate], {candidate.image_id: {"whole": 0.8, **values}}, and_tree
    )
    assert reranked[0].assessments[0]["status"] == "unknown"
    assert reranked[0].score_components["constraint_mean"] == pytest.approx(0.275)


def test_advanced_metrics_abstention_does_not_become_success():
    from app.evaluation.advanced_metrics import constraint_metrics

    actual = constraint_metrics(
        ["a", "b"],
        {"a": {"c": "satisfied"}, "b": {"c": "unknown"}},
        {"a": {"c": True}, "b": {"c": False}},
        ["a"],
    )
    assert actual["constraint_accuracy_verified"] == 1
    assert actual["constraint_verification_coverage"] == 0.5
    assert actual["multi_intent_success@10"] == 1
    assert actual["constraint_satisfaction@10"] == 0.5
    unknown = constraint_metrics(["a"], {"a": {"c": "unknown"}}, {"a": {"c": True}}, ["a"])
    assert unknown["constraint_accuracy_verified"] is None
