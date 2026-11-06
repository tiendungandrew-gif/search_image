from app.schemas.constraints import leaves
from app.services.query.constraint_parser import AmbiguousQuery, parse_constraints


def decompose(text: str):
    """Trả AST hoặc fallback marker; không sửa original query dùng để retrieval."""
    try:
        tree = parse_constraints(text)
        return tree, None
    except AmbiguousQuery as exc:
        return None, str(exc)


def retrieval_clauses(tree, limit: int):
    # Negative clauses chỉ dùng assessment/ranking, không tạo positive retrieval branch.
    return [leaf for leaf in leaves(tree) if leaf.kind == "semantic" and not leaf.negated][:limit]
