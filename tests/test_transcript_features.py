from __future__ import annotations

from unittest.mock import patch

from yt_insights.analytics.transcript_features import TranscriptFeatureExtractor, TranscriptFeatures
from yt_insights.transcript_cli import TranscriptResult, TranscriptSegment, TranscriptNotAvailableError, VideoUnavailableError


def test_transcript_extractor_maps_fetched_transcript_to_complete_features() -> None:
    extractor = TranscriptFeatureExtractor()

    with patch("yt_insights.analytics.transcript_features.create_youtube_transcript_api") as mocked_api, patch(
        "yt_insights.analytics.transcript_features.fetch_transcript"
    ) as mocked_fetch:
        mocked_api.return_value = object()
        mocked_fetch.return_value = TranscriptResult(
            video_id="video-1",
            language_code="en",
            language="English",
            is_generated=True,
            full_text="Hello world",
            segments=[TranscriptSegment(start=0.0, duration=1.0, text="Hello world")],
        )

        features = extractor.extract_from_video_id("video-1")

    assert features.status == "complete"
    assert features.language == "en"
    assert features.is_auto_generated is True
    assert features.transcript_text == "Hello world"


def test_transcript_extractor_returns_no_captions_when_no_transcript_exists() -> None:
    extractor = TranscriptFeatureExtractor()

    with patch("yt_insights.analytics.transcript_features.create_youtube_transcript_api") as mocked_api, patch(
        "yt_insights.analytics.transcript_features.fetch_transcript",
        side_effect=TranscriptNotAvailableError(),
    ):
        mocked_api.return_value = object()
        features = extractor.extract_from_video_id("video-2")

    assert features.status == "no_captions"
    assert features.transcript_text is None


def test_transcript_extractor_returns_video_unavailable_status() -> None:
    extractor = TranscriptFeatureExtractor()

    with patch("yt_insights.analytics.transcript_features.create_youtube_transcript_api") as mocked_api, patch(
        "yt_insights.analytics.transcript_features.fetch_transcript",
        side_effect=VideoUnavailableError(),
    ):
        mocked_api.return_value = object()
        features = extractor.extract_from_video_id("video-3")

    assert features.status == "video_unavailable"
    assert features.transcript_text is None
