import unicodedata
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.filters import Filters


class ConstraintLeaf(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(min_length=1, max_length=64, pattern=r"^[\w-]+$")
    kind: Literal["semantic", "metadata"]
    required: bool = True
    negated: bool = False
    weight: float = Field(default=1.0, gt=0, le=10, allow_inf_nan=False)
    text: str | None = Field(default=None, min_length=1, max_length=2000)
    filter: Filters | None = None

    @model_validator(mode="after")
    def content(self):
        if self.id in {"whole", "image"}:
            raise ValueError("reserved_constraint_id")
        if self.kind == "semantic":
            if not self.text or not self.text.strip() or self.filter is not None:
                raise ValueError("semantic_leaf_requires_text_only")
            if any(unicodedata.category(c) in {"Cc", "Cs"} and not c.isspace() for c in self.text):
                raise ValueError("invalid_control_character")
            self.text = " ".join(unicodedata.normalize("NFC", self.text).split())
        elif (
            self.filter is None
            or self.text is not None
            or not self.filter.model_dump(exclude_defaults=True)
        ):
            raise ValueError("metadata_leaf_requires_nonempty_filter_only")
        return self


class ConstraintGroup(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    op: Literal["and", "or"]
    clauses: list["ConstraintLeaf | ConstraintGroup"] = Field(min_length=2, max_length=8)


ConstraintSpec = ConstraintLeaf | ConstraintGroup


def leaves(tree: ConstraintSpec | None) -> list[ConstraintLeaf]:
    if tree is None:
        return []
    if isinstance(tree, ConstraintLeaf):
        return [tree]
    return [leaf for clause in tree.clauses for leaf in leaves(clause)]


def validate_tree(tree: ConstraintSpec) -> None:
    items = leaves(tree)
    if len(items) > 8 or len({leaf.id for leaf in items}) != len(items):
        raise ValueError("constraint_limit_or_duplicate_id")

    def depth(node):
        return 0 if isinstance(node, ConstraintLeaf) else 1 + max(map(depth, node.clauses))

    if depth(tree) > 2:
        raise ValueError("constraint_depth_exceeded")
