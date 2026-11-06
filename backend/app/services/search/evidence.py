from app.schemas.constraints import ConstraintGroup, leaves

SATISFIED = "satisfied"
VIOLATED = "violated"
UNKNOWN = "unknown"


def metadata_status(filters, image, metadata, tags):
    values = []
    for field in ["source_dataset", "city"]:
        expected = getattr(filters, field)
        if expected is not None:
            actual = getattr(metadata, field, None)
            values.append(None if actual is None else actual == expected)
    if filters.media_types:
        values.append(image.media_type in filters.media_types)
    # Tags không có không phải bằng chứng absence; metadata hiện không đánh dấu exhaustive.
    if filters.tags_any:
        values.append(True if set(tags).intersection(filters.tags_any) else None)
    if filters.tags_all:
        values.append(True if set(filters.tags_all).issubset(tags) else None)
    for field in ["width", "height"]:
        low, high = getattr(filters, "min_" + field), getattr(filters, "max_" + field)
        actual = getattr(image, field)
        if low is not None:
            values.append(actual >= low)
        if high is not None:
            values.append(actual <= high)
    for field, op in [("captured_from", lambda a, b: a >= b), ("captured_to", lambda a, b: a <= b)]:
        expected = getattr(filters, field)
        if expected is not None:
            actual = getattr(metadata, "captured_at", None)
            values.append(None if actual is None else op(actual, expected))
    return VIOLATED if False in values else UNKNOWN if None in values else SATISFIED


def assessments(tree, row, tags, semantic_scores=None):
    output = []
    for leaf in leaves(tree):
        status = (
            metadata_status(leaf.filter, row[0], row[1], tags)
            if leaf.kind == "metadata"
            else UNKNOWN
        )
        if leaf.negated and status != UNKNOWN:
            status = VIOLATED if status == SATISFIED else SATISFIED
        output.append(
            {
                "clause_id": leaf.id,
                "status": status,
                "evidence_ref": f"metadata:{row[0].id}" if status != UNKNOWN else None,
                "evidence_kind": "metadata" if leaf.kind == "metadata" else "semantic_similarity",
                "semantic_score": (semantic_scores or {}).get(leaf.id),
                "required": leaf.required,
                "negated": leaf.negated,
            }
        )
    return output


def evaluate_required(tree, statuses):
    """Projection chỉ required leaves: optional OR branch không thể bypass mandatory leaf."""
    if tree is None:
        return SATISFIED

    def visit(node):
        if not isinstance(node, ConstraintGroup):
            return statuses[node.id] if node.required else None
        values = [value for child in node.clauses if (value := visit(child)) is not None]
        if not values:
            return None
        if node.op == "and":
            return VIOLATED if VIOLATED in values else UNKNOWN if UNKNOWN in values else SATISFIED
        return SATISFIED if SATISFIED in values else UNKNOWN if UNKNOWN in values else VIOLATED

    return visit(tree) or SATISFIED
