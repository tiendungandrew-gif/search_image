"""Conservative language labels; ambiguous fragments must not default to English."""

import re
import unicodedata
from functools import lru_cache


@lru_cache(maxsize=1)
def language_identifier():
    try:
        from py3langid.langid import MODEL_FILE, LanguageIdentifier
    except ImportError:
        return None
    identifier = LanguageIdentifier.from_model_file(MODEL_FILE, norm_probs=True)
    identifier.set_languages(["en", "vi"])
    return identifier


def detect_language(text: str) -> str:
    text = unicodedata.normalize("NFC", text).strip()
    if re.search(r"[ăâđêôơưà-ỹ]", text.lower()):
        return "vi"
    if not re.search(r"[a-zA-Z]", text):
        return "und"
    identifier = language_identifier()
    if identifier is None:
        return "und"
    language, confidence = identifier.classify(text)
    return language if confidence >= 0.90 else "und"


_REQUEST_PREFIX = re.compile(
    r"^(?:(?:tìm|tim|tìm kiếm|tim kiem)(?:\s+cho\s+(?:tôi|toi|mình|minh))?"
    r"\s+(?:hình ảnh|hinh anh|hình|hinh|ảnh|anh)|"
    r"(?:show me|find|search for)\s+(?:pictures|photos|images)\s+of)\s+",
    re.IGNORECASE,
)


def search_subject(text: str) -> str:
    """Remove only explicit image-search requests, preserving the subject and syntax."""
    normalized = unicodedata.normalize("NFC", text).strip()
    subject = _REQUEST_PREFIX.sub("", normalized, count=1).strip()
    return subject or normalized
