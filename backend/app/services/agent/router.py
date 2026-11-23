"""Conservative VI/EN routing; patterns are intentionally finite, not general NLU."""

import re
from dataclasses import dataclass

from app.schemas.agent import AgentRequest
from app.services.query.query_classifier import RELATIONAL, analyze_query

PATTERNS = [
    r"(?:landmarks|monuments).+?city\s+(?:where|containing|in which)\s+(.+?)"
    r"(?:\s+is\s+located|\s+is\s+situated|\s+is\s+found|$)",
    r"(?:địa danh|danh lam|di tích).+?thành phố\s+(?:nơi|mà|có)\s+(.+?)"
    r"(?:\s+(?:tọa lạc|nằm|thuộc)|$)",
]


@dataclass(frozen=True)
class Route:
    strategy: str
    anchor: str | None = None
    uncertain: bool = False


def route_query(request: AgentRequest, enabled: bool = True) -> Route:
    text = request.query
    if request.mode == "explain":
        return Route("rag_explanation")
    if request.mode == "metadata":
        return Route("metadata")
    if request.image_id is not None or request.mode == "multimodal":
        return Route("multimodal")
    if request.mode == "text":
        return Route("semantic", uncertain=bool(RELATIONAL.search(text)))
    if request.mode == "multi_intent":
        return Route("multi_intent", uncertain=bool(RELATIONAL.search(text)))
    for pattern in PATTERNS:
        match = re.search(pattern, text, re.I)
        if match:
            anchor = match[1].strip(" .?!\"'")
            return (
                Route(
                    "agentic_multi_hop",
                    anchor,
                    uncertain=bool(re.search(r"\bfamous\b|\bred\b|nổi tiếng|màu đỏ", text, re.I)),
                )
                if anchor
                else Route("unsupported_relation", uncertain=True)
            )
    if RELATIONAL.search(text) or re.search(r"\bcity containing\b|thành phố có", text, re.I):
        return Route("unsupported_relation", uncertain=True)
    analysis = analyze_query(text, False, parse=enabled)
    if request.mode == "multi_intent" or (enabled and analysis.query_type == "MULTI_INTENT"):
        return Route("multi_intent", uncertain=analysis.uncertain)
    return Route("semantic", uncertain=analysis.uncertain)
