from __future__ import annotations

from datetime import datetime, timezone

from yt_insights.analytics.transcript_features import TranscriptFeatures
from yt_insights.services.transcript_backfill import refresh_recent_transcripts


class FakeTranscriptExtractor:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def extract_from_video_id(self, video_id: str) -> TranscriptFeatures:
        self.calls.append(video_id)
        return TranscriptFeatures(
            status="complete",
            language="en",
            is_auto_generated=False,
            transcript_text=f"Transcript for {video_id}",
        )


class FakeRepository:
    def __init__(self) -> None:
        self.upserted_rows: list[dict] = []

    def get_active_channel_handles(self) -> list[str]:
        return ["@channel"]

    def get_recent_video_ids(self, channel_handle: str, *, published_after, limit: int = 200) -> list[str]:
        return ["new-video", "skipped-video", "complete-video"]

    def get_feature_rows(self, video_ids: list[str], *, limit: int = 5000) -> dict[str, dict]:
        base_row = {
            "channel_handle": "@channel",
            "extracted_at": "2026-04-19T00:00:00+00:00",
            "extractor_version": "video_features_v4",
            "title_fingerprint": "title",
            "thumbnail_fingerprint": "thumb",
            "source_title": "Title",
            "source_thumbnail_url": None,
            "title_length_chars": 5,
            "title_word_count": 1,
            "uppercase_word_count": 0,
            "digit_count": 0,
            "has_number": False,
            "has_question": False,
            "has_exclamation": False,
            "has_year": False,
            "has_vs": False,
            "has_brackets": False,
            "has_colon": False,
            "trigger_word_count": 0,
            "title_pattern": "statement",
            "thumbnail_feature_status": "no_thumbnail",
            "thumbnail_ocr_status": "no_thumbnail",
            "has_face": None,
            "face_count": None,
            "has_thumbnail_text": None,
            "estimated_thumbnail_text_tokens": None,
            "thumbnail_text": None,
            "thumbnail_text_confidence": None,
            "dominant_emotion": None,
            "dominant_colors": None,
            "composition_type": None,
            "contains_chart": None,
            "contains_map": None,
            "visual_style": None,
        }
        rows = {
            "new-video": {**base_row, "video_id": "new-video", "transcript_status": "skipped"},
            "skipped-video": {**base_row, "video_id": "skipped-video", "transcript_status": "request_blocked"},
            "complete-video": {**base_row, "video_id": "complete-video", "transcript_status": "complete"},
        }
        return {video_id: rows[video_id] for video_id in video_ids if video_id in rows}

    def upsert_feature_rows(self, rows: list[dict]) -> None:
        self.upserted_rows = rows


def test_refresh_recent_transcripts_retries_recent_skipped_and_blocked_rows() -> None:
    repo = FakeRepository()
    extractor = FakeTranscriptExtractor()

    result = refresh_recent_transcripts(
        repo,
        limit=10,
        monitor_days=30,
        feature_workers=1,
        executed_at=datetime(2026, 4, 19, tzinfo=timezone.utc),
        transcript_extractor=extractor,
    )

    assert extractor.calls == ["new-video", "skipped-video"]
    assert len(result) == 2
    assert {row["video_id"] for row in result} == {"new-video", "skipped-video"}
    assert all(row["transcript_status"] == "complete" for row in result)
    assert all(row["transcript_text"].startswith("Transcript for ") for row in result)
    assert all(row["updated_at"] == "2026-04-19T00:00:00+00:00" for row in result)
    assert {row["video_id"] for row in repo.upserted_rows} == {"new-video", "skipped-video"}
