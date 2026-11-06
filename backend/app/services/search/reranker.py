"""Lightweight baseline và protocol để thay vision-language reranker khi có evidence."""

from typing import Protocol

from app.schemas.constraints import ConstraintGroup, leaves
from app.services.search.evidence import SATISFIED, UNKNOWN, VIOLATED
from app.services.search.fusion import cosine_unit
from app.services.search.ranking import rank_unique


class Reranker(Protocol):
    def rank(self, candidates, scores, tree): ...


def semantic_relevance(tree, signals):
    def value(leaf):
        score = cosine_unit(signals[leaf.id])
        return 1 - score if leaf.negated else score

    def visit(node):
        if not isinstance(node, ConstraintGroup):
            return (value(node), node.weight) if node.kind == "semantic" and node.required else None
        values = [item for child in node.clauses if (item := visit(child)) is not None]
        if not values:
            return None
        mean = sum(v * w for v, w in values) / sum(w for _, w in values)
        score = (
            max(v for v, _ in values) if node.op == "or" else (min(v for v, _ in values) + mean) / 2
        )
        return score, 1.0

    required = visit(tree) if tree is not None else None
    optional = [
        (value(leaf), leaf.weight)
        for leaf in leaves(tree)
        if leaf.kind == "semantic" and not leaf.required
    ]
    preference = sum(v * w for v, w in optional) / sum(w for _, w in optional) if optional else None
    return required[0] if required else None, preference


class LightweightReranker:
    def __init__(self, settings):
        self.settings = settings

    def rank(self, candidates, scores, tree):
        cfg = self.settings
        weights = [
            cfg.rerank_whole_weight,
            cfg.rerank_constraint_weight,
            cfg.rerank_metadata_weight,
        ]
        total = sum(weights)
        for candidate in candidates:
            signals = scores[candidate.image_id]
            whole = cosine_unit(signals["whole"])
            required, preference = semantic_relevance(tree, signals)
            constraint = whole if required is None else required
            if preference is not None:
                constraint = (
                    1 - cfg.rerank_optional_weight
                ) * constraint + cfg.rerank_optional_weight * preference
            metadata = [a for a in candidate.assessments if a["evidence_kind"] == "metadata"]
            verified = (
                sum(a["status"] == SATISFIED for a in metadata) / len(metadata) if metadata else 0
            )
            unknown = sum(a["required"] and a["status"] == UNKNOWN for a in candidate.assessments)
            mismatch = sum(a["required"] and a["status"] == VIOLATED for a in candidate.assessments)
            # Các thành phần [0,1], penalties có cap; đây là ordering score chưa calibrated.
            score = (weights[0] * whole + weights[1] * constraint + weights[2] * verified) / total
            penalty = min(
                1.0, cfg.rerank_unknown_penalty * unknown + cfg.rerank_required_penalty * mismatch
            )
            candidate.score_components = {
                "whole_query": whole,
                "constraint_mean": constraint,
                "verified_metadata": verified,
                "required_penalty": penalty,
                "fusion_score": candidate.score,
            }
            candidate.score = max(0.0, score - penalty)
        return rank_unique(candidates)
