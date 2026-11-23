import re
from time import perf_counter

from app.schemas.constraints import ConstraintGroup
from app.services.query.language import detect_language
from app.services.query.query_decomposer import decompose
from app.services.query.query_models import QueryAnalysis

RELATIONAL = re.compile(
    r"\b(?:city\s+where|city\s+in\s+which|where.+is\s+located|"
    r"thành phố\s+(?:nơi|mà)|nơi.+tọa lạc|nơi.+nằm)\b",
    re.I,
)


def analyze_query(
    text: str | None, has_image: bool, parse: bool = True, explicit=None, timings=None
) -> QueryAnalysis:
    original = text or ""
    language = detect_language(original)
    result = QueryAnalysis(
        original_query=original,
        query_type="TEXT_IMAGE"
        if text and has_image
        else "IMAGE_SIMILARITY"
        if has_image
        else "SINGLE_INTENT",
        language=language,
        retrieval_strategy="paired_fusion" if text and has_image else "single_vector",
    )
    if text and RELATIONAL.search(text):
        result.query_type = "UNSUPPORTED_RELATIONAL_QUERY"
        result.requires_agent = True
        result.retrieval_strategy = "unsupported"
        return result
    if (parse and text) or explicit is not None:
        started = perf_counter()
        result.constraints, limitation = (
            (explicit, None) if explicit is not None else decompose(text)
        )
        if timings is not None:
            timings["query_decomposition_ms"] = (perf_counter() - started) * 1000
        if limitation:
            result.uncertain = True
            result.limitations.append(limitation)
        if isinstance(result.constraints, ConstraintGroup):
            result.logical_operator = result.constraints.op.upper()
            if not has_image:
                result.query_type = "MULTI_INTENT"
            result.retrieval_strategy = "paired_fusion" if has_image else "multi_query"
        if re.search(r"\b(?:near|gần|wearing|đội|but|nhưng|trong|đang)\b", original, re.I):
            result.limitations.append("phrase_relationships_not_visually_verified")
    return result
