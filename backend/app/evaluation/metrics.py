"""Metric formulas; fixtures trong tests không là ground-truth nghiên cứu."""

import math


def retrieval_metrics(ranking, grades, *, relevant_grade=1, strict_labels=False):
    if relevant_grade not in {1, 2, 3} or any(
        type(g) is not int or not 0 <= g <= 3 for g in grades.values()
    ):
        raise ValueError("invalid_relevance_grades")
    if strict_labels and not set(ranking).issubset(grades):
        raise ValueError("unjudged_result")
    relevant = {identity for identity, grade in grades.items() if grade >= relevant_grade}
    if not any(grades.values()):
        return {
            name: None
            for name in [
                *[
                    f"{metric}@{k}"
                    for metric in ["recall", "precision", "hit", "dcg", "idcg", "ndcg"]
                    for k in [1, 5, 10]
                ],
                "mrr@10",
            ]
        }
    seen = set()
    hits = []
    gain = []
    for identity in ranking[:10]:
        fresh = identity not in seen
        seen.add(identity)
        grade = grades.get(identity, 0) if fresh else 0
        hits.append(int(grade >= relevant_grade))
        gain.append(grade)
    ideal = sorted(grades.values(), reverse=True)[:10]
    dcg = sum((2**grade - 1) / math.log2(rank + 2) for rank, grade in enumerate(gain))
    idcg = sum((2**grade - 1) / math.log2(rank + 2) for rank, grade in enumerate(ideal))
    return {
        **{f"recall@{k}": sum(hits[:k]) / len(relevant) if relevant else None for k in [1, 5, 10]},
        **{f"precision@{k}": sum(hits[:k]) / k if relevant else None for k in [1, 5, 10]},
        **{f"hit@{k}": int(any(hits[:k])) if relevant else None for k in [1, 5, 10]},
        **{
            f"dcg@{k}": sum((2**g - 1) / math.log2(r + 2) for r, g in enumerate(gain[:k]))
            for k in [1, 5, 10]
        },
        **{
            f"idcg@{k}": sum((2**g - 1) / math.log2(r + 2) for r, g in enumerate(ideal[:k]))
            for k in [1, 5, 10]
        },
        **{
            f"ndcg@{k}": sum((2**g - 1) / math.log2(r + 2) for r, g in enumerate(gain[:k]))
            / sum((2**g - 1) / math.log2(r + 2) for r, g in enumerate(ideal[:k]))
            for k in [1, 5]
        },
        "mrr@10": next((1 / (rank + 1) for rank, hit in enumerate(hits) if hit), 0)
        if relevant
        else None,
        "ndcg@10": dcg / idcg if idcg else None,
    }


def nearest_rank(values, p):
    if not values:
        return None
    if not 0 < p <= 1:
        raise ValueError("invalid_percentile")
    return sorted(values)[math.ceil(p * len(values)) - 1]


def latency_summary(values):
    return {f"p{int(p * 100)}_ms": nearest_rank(values, p) for p in [0.5, 0.9, 0.95]}
