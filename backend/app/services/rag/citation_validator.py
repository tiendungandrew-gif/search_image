from pathlib import Path

from app.schemas.rag import Citation, ModelSelection
from app.services.rag.llm_provider import ProviderError


def validate_selection(text, context):
    try:
        selection = ModelSelection.model_validate_json(text)
    except ValueError:
        raise ProviderError("LLM_INVALID_STRUCTURE") from None
    if len(selection.fact_ids) != len(set(selection.fact_ids)):
        raise ProviderError("LLM_DUPLICATE_CITATION")
    if any(identity not in context.facts for identity in selection.fact_ids):
        raise ProviderError("LLM_UNSUPPORTED_CITATION")
    return [Citation(**context.facts[key].model_dump()) for key in selection.fact_ids]


def render_answer(citations, language):
    if not citations:
        return (
            (Path(__file__).parent / "prompts/insufficient_evidence.txt").read_text().strip()
            if language == "vi"
            else "The retrieved images and metadata do not provide enough evidence to confirm this."
        )
    prefix = "Theo metadata" if language == "vi" else "According to the stored metadata"
    return "\n".join(
        f"{prefix} [{c.image_id}], {c.evidence_field}: “{c.quote}”." for c in citations
    )
