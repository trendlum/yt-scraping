from __future__ import annotations

from datetime import datetime, timezone

from yt_insights.analytics.title_features import classify_title_pattern, extract_title_features
from yt_insights.models import VideoRecord


def test_extract_title_features_captures_v1_title_signals() -> None:
    video = VideoRecord(
        video_id="abc123",
        title="Why 90% of Creators FAIL in 2026?",
        channel_title="Channel",
        published_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        thumbnail_url="https://example.com/thumb.jpg",
        view_count=1000,
        like_count=100,
        comment_count=10,
        duration="00:10:00",
        duration_iso8601="PT10M",
        video_url="https://www.youtube.com/watch?v=abc123",
    )

    features = extract_title_features(
        video,
        "@creator",
        extracted_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
    )

    assert features.video_id == "abc123"
    assert features.has_number is True
    assert features.has_question is True
    assert features.has_year is True
    assert features.trigger_word_count >= 1
    assert features.title_pattern == "question"


def test_classify_title_pattern_detects_comparison() -> None:
    assert classify_title_pattern("iPhone vs Android for creators") == "comparison"
