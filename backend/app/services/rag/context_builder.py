import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from app.schemas.rag import Fact

PROMPTS = Path(__file__).parent / "prompts"


def select_language(request):
    if request.language != "auto":
        return request.language
    text = " ".join(
        filter(
            None, [request.question, request.query, request.search.text if request.search else None]
        )
    )
    return (
        "vi"
        if re.search(r"[\u00c0-\u01b0\u1ea0-\u1ef9]|\b(anh|tim|giai thich)\b", text, re.I)
        else "en"
    )


def technical_question(question):
    plain = "".join(
        c for c in unicodedata.normalize("NFD", question.lower()) if not unicodedata.combining(c)
    ).replace("đ", "d")
    return bool(
        re.search(
            r"\b(metadata|kich thuoc|dinh dang|nguon|giay phep|width|height|"
            r"dimensions|format|source|license)\b",
            plain,
        )
    )


def technical_fields(question):
    plain = "".join(
        c for c in unicodedata.normalize("NFD", question.lower()) if not unicodedata.combining(c)
    ).replace("đ", "d")
    fields = set()
    for pattern, names in [
        (r"width|height|dimensions|kich thuoc", {"width", "height"}),
        (r"format|dinh dang", {"media_type"}),
        (r"source|nguon", {"source_dataset"}),
        (r"license|giay phep", {"license"}),
    ]:
        if re.search(pattern, plain):
            fields.update(names)
    return fields or {"width", "height", "media_type", "source_dataset", "license", "city"}


@dataclass
class Context:
    messages: list[dict]
    facts: dict[str, Fact]
    summary: dict
    prompt_sha256: str


def build_context(evidence, question, language, settings, request):
    technical = technical_question(question)
    limit = min(
        request.max_context_tokens or settings.rag_max_context_tokens,
        settings.rag_max_context_tokens,
    )
    item_limit = min(
        request.max_evidence_items or settings.rag_max_evidence_items,
        settings.rag_max_evidence_items,
    )
    ordered = sorted(
        evidence,
        key=lambda e: (
            e.incomplete if request.context_policy == "descriptive_first" else False,
            e.retrieval_rank,
        ),
    )
    facts = {}
    included = []
    for record in ordered:
        if str(record.image_id) in included:
            continue
        if len(included) >= item_limit:
            break
        values = {}
        if record.caption:
            values["caption"] = record.caption
        if record.tags:
            values["tags"] = ", ".join(record.tags)
        if record.metadata.get("description"):
            values["description"] = record.metadata["description"]
        if technical:
            values.update(
                {k: str(v) for k, v in record.metadata.items() if k in technical_fields(question)}
            )
        # Technical IDs, titles and scores alone are not descriptions of image content.
        batch = {}
        for field, value in values.items():
            fact = Fact(
                fact_id=f"E{record.retrieval_rank}.{field}",
                image_id=record.image_id,
                evidence_field=field,
                quote=value,
                provenance=record.provenance.get(field, record.provenance["metadata"]),
            )
            batch[fact.fact_id] = fact
        if not batch:
            continue
        proposed = list(facts.values()) + list(batch.values())
        encoded = json.dumps([f.model_dump(mode="json") for f in proposed], ensure_ascii=False)
        if len(encoded.encode()) > limit:
            continue
        facts.update(batch)
        included.append(str(record.image_id))
    templates = {
        name: (PROMPTS / name).read_text()
        for name in [
            "system_prompt.txt",
            "answer_generation.txt",
            "evidence_explanation.txt",
            "insufficient_evidence.txt",
        ]
    }
    sha = hashlib.sha256(json.dumps(templates, sort_keys=True).encode()).hexdigest()
    messages = [
        {"role": "system", "content": templates["system_prompt.txt"]},
        {
            "role": "user",
            "content": templates["answer_generation.txt"]
            + "\n"
            + templates["evidence_explanation.txt"]
            + "\n"
            + json.dumps(
                {
                    "QUESTION_DATA": question,
                    "LANGUAGE": language,
                    "EVIDENCE_DATA": [f.model_dump(mode="json") for f in facts.values()],
                },
                ensure_ascii=False,
            ),
        },
    ]
    upper = sum(len(m["content"].encode()) for m in messages) + 128
    if upper + settings.rag_max_output_tokens > settings.rag_max_input_tokens:
        facts = {}
    return Context(
        messages,
        facts,
        {
            "included_image_ids": included if facts else [],
            "available_images": len(evidence),
            "fact_count": len(facts),
            "context_budget_upper_bound_tokens": limit,
            "input_token_upper_bound": upper,
            "token_count_policy": "UTF-8 byte upper bound + 128 message overhead; not exact tokens",
            "policy": request.context_policy,
            "technical_question": technical,
        },
        sha,
    )
