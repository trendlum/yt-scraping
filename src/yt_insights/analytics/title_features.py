from __future__ import annotations

import re

from ..constants import VIDEO_FEATURES_EXTRACTOR_VERSION
from ..models import VideoFeatureRecord, VideoRecord, sha1_text, utc_now


_WORD_RE = re.compile(r"[A-Za-z0-9']+")
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_VS_RE = re.compile(r"\bvs\.?\b", re.IGNORECASE)
_QUESTION_PREFIX_RE = re.compile(
    r"^(why|what|when|where|who|how|que|como|por que)\b",
    re.IGNORECASE,
)
_HOW_TO_RE = re.compile(r"^(how to|how i|como)\b", re.IGNORECASE)
_LIST_RE = re.compile(
    r"^(?:top\s+\d+|\d+\s+ways|\d+\s+trucos|\d+\s+ideas|\d+\s+steps)\b",
    re.IGNORECASE,
)

_TRIGGER_WORDS = {
    "secret",
    "mistake",
    "mistakes",
    "warning",
    "warn",
    "shocking",
    "fail",
    "failed",
    "insane",
    "crazy",
    "brutal",
    "simple",
    "easy",
    "hard",
    "avoid",
    "truth",
    "secretos",
    "error",
    "errores",
    "alerta",
    "fracasa",
    "fracasar",
    "facil",
    "evita",
}

_WARNING_WORDS = {
    "warning",
    "avoid",
    "mistake",
    "mistakes",
    "alerta",
    "error",
    "errores",
    "evita",
}
_PREDICTION_WORDS = {"predict", "prediction", "next", "future", "2026", "2027", "prediccion", "futuro"}
_OPINION_WORDS = {"opinion", "review", "thoughts", "honest", "my"}


def classify_title_pattern(title: str) -> str:
    normalized = title.strip()
    lowered = normalized.lower()

    if "?" in normalized or _QUESTION_PREFIX_RE.search(normalized):
        return "question"
    if _HOW_TO_RE.search(normalized):
        return "how_to"
    if _VS_RE.search(normalized):
        return "comparison"
    if _LIST_RE.search(normalized) or lowered.startswith("top "):
        return "list"
    if any(word in lowered for word in _WARNING_WORDS):
        return "warning"
    if any(word in lowered for word in _PREDICTION_WORDS):
        return "prediction"
    if any(word in lowered for word in _OPINION_WORDS):
        return "opinion"
    return "statement"


def extract_title_features(
    video: VideoRecord,
    channel_handle: str,
    *,
    extracted_at=None,
) -> VideoFeatureRecord:
    extracted_at = extracted_at or utc_now()
    title = video.title or ""
    words = _WORD_RE.findall(title)
    uppercase_words = [word for word in words if len(word) > 1 and word.isupper()]
    lowered_words = [word.lower() for word in words]

    trigger_word_count = sum(1 for word in lowered_words if word in _TRIGGER_WORDS)
    return VideoFeatureRecord(
        video_id=video.video_id,
        channel_handle=channel_handle,
        extracted_at=extracted_at,
        extractor_version=VIDEO_FEATURES_EXTRACTOR_VERSION,
        title_fingerprint=sha1_text(title),
        thumbnail_fingerprint=sha1_text(video.thumbnail_url),
        source_title=video.title,
        source_thumbnail_url=video.thumbnail_url,
        title_length_chars=len(title),
        title_word_count=len(words),
        uppercase_word_count=len(uppercase_words),
        digit_count=sum(1 for char in title if char.isdigit()),
        has_number=any(char.isdigit() for char in title),
        has_question="?" in title,
        has_exclamation="!" in title,
        has_year=bool(_YEAR_RE.search(title)),
        has_vs=bool(_VS_RE.search(title)),
        has_brackets=any(char in title for char in "[]()"),
        has_colon=":" in title,
        trigger_word_count=trigger_word_count,
        title_pattern=classify_title_pattern(title),
    )
