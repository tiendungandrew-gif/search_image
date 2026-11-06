"""Deterministic rank/score fusion; không coi normalized cosine là probability."""

from dataclasses import dataclass, field

from app.services.search.ranking import rank_unique
from app.services.search.vector_retriever import Candidate


@dataclass
class FusedCandidate(Candidate):
    contributions: list[dict] = field(default_factory=list)
    score_components: dict = field(default_factory=dict)
    assessments: list[dict] = field(default_factory=list)


def cosine_unit(score: float) -> float:
    return max(0.0, min(1.0, (score + 1.0) / 2.0))


def fuse(
    branches: dict[str, list[Candidate]], weights: dict[str, float], method: str, k: int, limit: int
):
    total = sum(weights.values())
    if total <= 0 or any(w < 0 for w in weights.values()):
        raise ValueError("invalid_fusion_weights")
    candidates = {}
    for name, batch in branches.items():
        weight = weights[name] / total
        if weight == 0:
            continue
        for rank, item in enumerate(rank_unique(batch), 1):
            if item.image_id not in candidates:
                candidates[item.image_id] = FusedCandidate(item.image_id, 0, item.payload)
            row = candidates[item.image_id]
            value = weight * (
                cosine_unit(item.score) if method == "weighted_score" else 1 / (k + rank)
            )
            row.score += value
            row.contributions.append(
                {
                    "branch": name,
                    "rank": rank,
                    "cosine": item.score,
                    "weight": weight,
                    "contribution": value,
                }
            )
    # Absent branch contributes 0; không renormalize theo từng document/empty branch.
    return rank_unique(list(candidates.values()))[:limit]
