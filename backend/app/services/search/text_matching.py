"""Literal catalog names and bounded rank fusion, independent of accent guessing."""

import unicodedata
from dataclasses import dataclass
from uuid import UUID

from app.services.search.fusion import FusedCandidate


def fold_text(value):
    decomposed = unicodedata.normalize("NFD", value.lower().replace("đ", "d"))
    unaccented = "".join(c for c in decomposed if not "\u0300" <= c <= "\u036f")
    return " ".join("".join(c if c.isalnum() else " " for c in unaccented).split())


def accented_words(value):
    normalized = unicodedata.normalize("NFC", value.lower())
    words = "".join(c if c.isalnum() else " " for c in normalized).split()
    return list(dict.fromkeys(word for word in words if fold_text(word) != word))


@dataclass
class TextHit:
    image_id: UUID
    score: float
    title: str | None
    name_match: bool
    phrase_match: bool = False


def short_phrase(value):
    """A short concept, not a conjunction, filter expression or quoted query."""
    words = fold_text(value).split()
    return (
        2 <= len(words) <= 5
        and not any(mark in value for mark in [":", '"', "'", "(", ")"])
        and not set(words).intersection({"and", "or", "va", "hoac", "khong", "without"})
    )


def requires_food_phrase(value):
    """Recognize bounded dish + ingredient concepts, never an isolated animal.

    Abstain rather than pad these searches with visually similar animal photos.
    Explicit accents must agree with the dish word (phố is not phở).
    This is a precision policy for common Vietnamese dishes, not visual verification.
    """
    if not short_phrase(value):
        return False
    normalized = unicodedata.normalize("NFC", value.lower())
    words = "".join(c if c.isalnum() else " " for c in normalized).split()
    dishes = {"bun": "bún", "pho": "phở", "mien": "miến", "com": "cơm", "chao": "cháo"}
    ingredients = {"ga": "gà", "bo": "bò", "heo": "heo", "lon": "lợn", "ca": "cá"}

    def agrees(word, vocabulary):
        folded = fold_text(word)
        return folded in vocabulary and word in {folded, vocabulary[folded]}

    return agrees(words[0], dishes) and any(agrees(word, ingredients) for word in words[1:])


def matches_phrase(query, descriptions):
    """Require adjacent words in a single descriptive field; preserve explicit accents."""
    if not short_phrase(query):
        return False

    def tokens(value):
        value = unicodedata.normalize("NFC", value.lower())
        return "".join(c if c.isalnum() else " " for c in value).split()

    original = tokens(query)
    expected = [fold_text(word) for word in original]
    for description in descriptions:
        if not isinstance(description, str):
            continue
        words = tokens(description)
        folded = [fold_text(word) for word in words]
        for start in range(len(words) - len(expected) + 1):
            if folded[start : start + len(expected)] != expected:
                continue
            if all(
                fold_text(word) == word or words[start + offset] == word
                for offset, word in enumerate(original)
            ):
                return True
    return False


def matches_name(query, names):
    folded = fold_text(query)
    # Very short generic fragments still use visual/description retrieval.
    if len(folded.split()) < 3:
        return False
    for name in names:
        if not isinstance(name, str) or not name:
            continue
        normalized = unicodedata.normalize("NFC", name.lower())
        exact = set("".join(c if c.isalnum() else " " for c in normalized).split())
        if not set(accented_words(query)).issubset(exact):
            continue
        words = iter(fold_text(name).split())
        if all(any(word == token for word in words) for token in folded.split()):
            return True
    return False


def hybrid_rank(text_candidates, visual_candidates, limit=1000):
    combined = {}
    for branch, candidates, weight in [
        ("metadata", text_candidates, 0.6),
        ("visual", visual_candidates, 0.4),
    ]:
        for rank, candidate in enumerate(candidates, 1):
            item = combined.setdefault(
                candidate.image_id, FusedCandidate(candidate.image_id, 0, candidate.payload)
            )
            contribution = weight / (60 + rank)
            item.score += contribution
            item.score_components["text_rank" if branch == "metadata" else "visual_cosine"] = (
                candidate.score
            )
            item.contributions.append(
                {"branch": branch, "rank": rank, "weight": weight, "contribution": contribution}
            )
    return sorted(combined.values(), key=lambda c: (-c.score, str(c.image_id)))[:limit]
