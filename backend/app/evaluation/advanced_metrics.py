"""Đo constraint verification có abstention; chỉ caller có human labels được aggregate."""


def constraint_metrics(
    ranking, evidence, judgments, overall_satisfied, k=10, *, overall_judgments=None
):
    if any(
        truth is not None and type(truth) is not bool
        for labels in judgments.values()
        for truth in labels.values()
    ):
        raise ValueError("Invalid human constraint label")
    if overall_judgments and any(
        truth is not None and type(truth) is not bool for truth in overall_judgments.values()
    ):
        raise ValueError("Invalid overall human label")
    selected = ranking[:k]
    verified = correct = known = 0
    for identity in selected:
        for clause, status in evidence.get(identity, {}).items():
            truth = judgments.get(identity, {}).get(clause)
            if truth is None:
                continue
            if type(truth) is not bool:
                raise ValueError("Invalid human constraint label")
            known += 1
            if status not in {"satisfied", "violated", "unknown"}:
                raise ValueError("Invalid evidence status")
            if status == "unknown":
                continue
            verified += 1
            correct += (status == "satisfied") == truth
    satisfied = set(overall_satisfied)
    known_overall = [
        identity
        for identity in selected
        if overall_judgments is None or overall_judgments.get(identity) is not None
    ]
    known_pairs = [
        truth
        for identity in selected
        for truth in judgments.get(identity, {}).values()
        if truth is not None
    ]
    labeled_clauses = {
        clause
        for labels in judgments.values()
        for clause, truth in labels.items()
        if truth is not None
    }
    covered_clauses = {
        clause
        for identity in selected
        for clause, truth in judgments.get(identity, {}).items()
        if truth is True
    }
    return {
        "constraint_accuracy_verified": correct / verified if verified else None,
        "constraint_verification_coverage": verified / known if known else None,
        "constraint_annotated_pairs": known,
        "constraint_verified_pairs": verified,
        "multi_intent_success@10": (
            1 if set(selected) & satisfied else None if len(known_overall) < len(selected) else 0
        )
        if satisfied
        else None,
        "constraint_satisfaction@10": len(set(known_overall) & satisfied) / len(known_overall)
        if known_overall
        else None,
        "overall_judgment_coverage_at_k": len(known_overall) / len(selected) if selected else None,
        "human_constraint_satisfaction_at_k": sum(known_pairs) / len(known_pairs)
        if known_pairs
        else None,
        "constraint_coverage_at_k": len(covered_clauses) / len(labeled_clauses)
        if labeled_clauses
        else None,
    }
