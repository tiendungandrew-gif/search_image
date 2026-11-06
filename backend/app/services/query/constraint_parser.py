"""Grammar nhỏ: AND ưu tiên hơn OR; cụm thuộc tính/quan hệ được giữ nguyên."""

import re

from pydantic import ValidationError

from app.core.exceptions import AppError
from app.schemas.constraints import ConstraintGroup, ConstraintLeaf, leaves, validate_tree
from app.schemas.filters import Filters

TOKEN = re.compile(r"(\(|\)|\b(?:and|or|và|hoặc)\b)", re.I)
COLOR_PAIR = re.compile(
    r"(?:black|white|red|blue|đen|trắng|đỏ|xanh)\s+(?:and|và)\s+(?:black|white|red|blue|đen|trắng|đỏ|xanh)\b",
    re.I,
)


class AmbiguousQuery(ValueError):
    pass


def parse_constraints(text: str):
    if COLOR_PAIR.search(text) or '"' in text or "'" in text:
        raise AmbiguousQuery("ambiguous_conjunction_or_quote")
    # Chỉ mở comma-list khi có explicit conjunction; không tách mọi dấu phẩy.
    text = re.sub(r",\s*(?:and|và)\s+", " and ", text, flags=re.I)
    if "," in text and re.search(r"\b(?:and|và)\b", text, re.I):
        text = text.replace(",", " and ")
    text = re.sub(
        r"^(?:find\s+(?:images?\s+)?(?:containing\s+|of\s+|with\s+)?|tìm\s+(?:ảnh\s+)?(?:có\s+)?)",
        "",
        text,
        flags=re.I,
    )
    tokens = [part.strip() for part in TOKEN.split(text) if part.strip()]
    position = 0
    serial = 0

    def leaf(phrase):
        nonlocal serial
        required = not bool(
            re.match(r"^(?:preferably|optionally|ưu tiên|nếu có thể)\b", phrase, re.I)
        )
        phrase = re.sub(r"^(?:preferably|optionally|ưu tiên|nếu có thể)\s+", "", phrase, flags=re.I)
        negated = False
        negative = re.search(r"\b(?:without|không có)\s+", phrase, re.I)
        if negative and negative.start() > 0:
            # Giữ quan hệ cùng cụm gốc, đồng thời ghi exclusion riêng.
            group = ConstraintGroup(
                op="and",
                clauses=[
                    leaf(phrase[: negative.start()].strip()),
                    leaf(phrase[negative.start() :].strip()),
                ],
            )
            if not required:
                for item in leaves(group):
                    item.required = False
            return group
        if negative:
            negated = True
            phrase = phrase[negative.end() :].strip()
        phrase = re.sub(r"^(?:with|có)\s+", "", phrase, flags=re.I).strip(" .")
        if not phrase:
            raise AmbiguousQuery("empty_clause")
        serial += 1
        if serial > 8:
            raise AppError(422, "CONSTRAINT_LIMIT", "Tối đa 8 constraints")
        fields = {"tag": "tags_all", "city": "city", "source": "source_dataset"}
        match = re.fullmatch(r"(tag|city|source):\s*(.+)", phrase, re.I)
        if match:
            key = fields[match[1].lower()]
            value = [match[2]] if key == "tags_all" else match[2]
            try:
                return ConstraintLeaf(
                    id=f"q{serial}",
                    kind="metadata",
                    filter=Filters(**{key: value}),
                    required=required,
                    negated=negated,
                )
            except ValidationError:
                raise AppError(422, "INVALID_INPUT", "Metadata expression vượt giới hạn") from None
        return ConstraintLeaf(
            id=f"q{serial}", kind="semantic", text=phrase, required=required, negated=negated
        )

    def atom(depth):
        nonlocal position
        if position >= len(tokens):
            raise AmbiguousQuery("missing_clause")
        item = tokens[position]
        position += 1
        if item == "(":
            if depth >= 2:
                raise AppError(422, "CONSTRAINT_LIMIT", "Grouping quá sâu")
            node = expression("or", depth + 1)
            if position >= len(tokens) or tokens[position] != ")":
                raise AmbiguousQuery("unbalanced_parentheses")
            position += 1
            return node
        if item.lower() in {"and", "or", "và", "hoặc"} or item == ")":
            raise AmbiguousQuery("unexpected_operator")
        return leaf(item)

    def expression(op, depth):
        nonlocal position
        values = [expression("and", depth) if op == "or" else atom(depth)]
        operators = {"or", "hoặc"} if op == "or" else {"and", "và"}
        while position < len(tokens) and tokens[position].lower() in operators:
            position += 1
            values.append(expression("and", depth) if op == "or" else atom(depth))
        flattened = []
        for item in values:
            flattened.extend(
                item.clauses if isinstance(item, ConstraintGroup) and item.op == op else [item]
            )
        return flattened[0] if len(flattened) == 1 else ConstraintGroup(op=op, clauses=flattened)

    tree = expression("or", 0)
    if position != len(tokens):
        raise AmbiguousQuery("unsupported_grouping")
    try:
        validate_tree(tree)
    except ValueError:
        raise AppError(422, "CONSTRAINT_LIMIT", "AST tối đa 8 leaves và 2 group levels") from None
    return tree
