from __future__ import annotations

from datetime import datetime, timezone

from yt_insights.analytics.transcript_features import TranscriptFeatures
from yt_insights.analytics.thumbnail_features import ThumbnailImageFeatures
from yt_insights.models import VideoMetricSnapshot, VideoRecord
from yt_insights.services.scraper import merge_unique_video_ids, run_batch_scrape


class FakeYouTubeClient:
    def get_channel_by_handle(self, channel_handle: str) -> dict:
        return {
            "id": "channel-id",
            "snippet": {"title": "Channel"},
            "contentDetails": {"relatedPlaylists": {"uploads": "uploads-1"}},
        }

    def get_uploads_playlist_id(self, channel_data: dict) -> str:
        return channel_data["contentDetails"]["relatedPlaylists"]["uploads"]

    def list_upload_video_ids(self, uploads_playlist_id: str, *, limit: int | None, published_after):
        return ["new-video", "stored-video"]

    def get_videos_details(self, video_ids: list[str]) -> list[VideoRecord]:
        published_at = datetime(2026, 4, 10, tzinfo=timezone.utc)
        return [
            VideoRecord(
                video_id=video_id,
                title=f"Title {video_id}",
                channel_title="Channel",
                published_at=published_at,
                thumbnail_url=None,
                view_count=100,
                like_count=10,
                comment_count=1,
                duration="00:05:00",
                duration_iso8601="PT5M",
                video_url=f"https://www.youtube.com/watch?v={video_id}",
            )
            for video_id in video_ids
        ]


class CustomVideoYouTubeClient(FakeYouTubeClient):
    def __init__(self, overrides: dict[str, dict]) -> None:
        self.overrides = overrides

    def get_videos_details(self, video_ids: list[str]) -> list[VideoRecord]:
        videos = super().get_videos_details(video_ids)
        for video in videos:
            override = self.overrides.get(video.video_id)
            if not override:
                continue
            for field_name, value in override.items():
                setattr(video, field_name, value)
        return videos


class FakeRepository:
    def __init__(self) -> None:
        self.current_rows: list[dict] = []
        self.snapshot_rows: list[dict] = []
        self.feature_rows: list[dict] = []
        self.performance_rows: list[dict] = []
        self.updated_at = None
        self.existing_feature_rows: dict[str, dict] = {}

    def get_active_channel_configs(self) -> list[dict]:
        return [{"channel_handle": "@channel", "thumbnail_analysis": True}]

    def get_recent_video_ids(self, channel_handle: str, *, published_after, limit: int = 200) -> list[str]:
        return ["stored-video"]

    def get_feature_rows(self, video_ids: list[str], *, limit: int = 5000) -> dict[str, dict]:
        return {
            video_id: self.existing_feature_rows[video_id]
            for video_id in video_ids
            if video_id in self.existing_feature_rows
        }

    def upsert_current_videos(self, rows: list[dict]) -> None:
        self.current_rows = rows

    def insert_snapshots(self, rows: list[dict]) -> None:
        self.snapshot_rows = rows

    def upsert_feature_rows(self, rows: list[dict]) -> None:
        self.feature_rows = rows

    def get_snapshots_for_channels(self, channel_handles: list[str], *, published_after, limit: int = 5000):
        return [
            VideoMetricSnapshot.from_row(row)
            for row in self.snapshot_rows
            if row.get("published_at") is not None
        ]

    def upsert_performance_rows(self, rows: list[dict]) -> None:
        self.performance_rows = rows

    def update_scraper_state(self, executed_at) -> None:
        self.updated_at = executed_at


class FakeTranscriptExtractor:
    def __init__(self) -> None:
        self.calls = 0

    def extract_from_video_id(self, video_id: str) -> TranscriptFeatures:
        self.calls += 1
        return TranscriptFeatures(
            status="complete",
            language="en",
            is_auto_generated=False,
            transcript_text=f"Transcript for {video_id}",
        )


def test_merge_unique_video_ids_preserves_order() -> None:
    assert merge_unique_video_ids(["a", "b"], ["b", "c"]) == ["a", "b", "c"]


def test_run_batch_scrape_persists_current_rows_snapshots_and_features() -> None:
    repo = FakeRepository()
    result = run_batch_scrape(
        FakeYouTubeClient(),
        repo,
        limit=10,
        monitor_days=30,
        baseline_window_days=30,
        feature_workers=1,
        executed_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
        transcript_extractor=FakeTranscriptExtractor(),
    )

    assert len(result) == 1
    assert len(repo.current_rows) == 2
    assert len(repo.snapshot_rows) == 2
    assert len(repo.feature_rows) == 2
    assert all(row["transcript_status"] == "complete" for row in repo.feature_rows)
    assert all(row["transcript_language"] == "en" for row in repo.feature_rows)
    assert all(row["transcript_text"] is not None for row in repo.feature_rows)
    assert all(row["thumbnail_feature_status"] == "no_thumbnail" for row in repo.feature_rows)
    assert all(row["thumbnail_ocr_status"] == "no_thumbnail" for row in repo.feature_rows)
    assert repo.updated_at == datetime(2026, 4, 13, tzinfo=timezone.utc)


def test_run_batch_scrape_skips_thumbnail_analysis_when_disabled() -> None:
    class DisabledThumbnailRepository(FakeRepository):
        def get_active_channel_configs(self) -> list[dict]:
            return [{"channel_handle": "@channel", "thumbnail_analysis": False}]

    repo = DisabledThumbnailRepository()
    thumbnail_extractor = FakeThumbnailExtractor()
    result = run_batch_scrape(
        FakeYouTubeClient(),
        repo,
        limit=10,
        monitor_days=30,
        baseline_window_days=30,
        feature_workers=1,
        executed_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
        transcript_extractor=FakeTranscriptExtractor(),
        thumbnail_extractor=thumbnail_extractor,
    )

    assert len(result) == 1
    assert thumbnail_extractor.calls == 0
    assert all(row["thumbnail_feature_status"] == "skipped" for row in repo.feature_rows)
    assert all(row["thumbnail_ocr_status"] == "skipped" for row in repo.feature_rows)
    assert all(row["thumbnail_text"] is None for row in repo.feature_rows)


def test_run_batch_scrape_supports_parallel_feature_enrichment() -> None:
    repo = FakeRepository()
    result = run_batch_scrape(
        FakeYouTubeClient(),
        repo,
        limit=10,
        monitor_days=30,
        baseline_window_days=30,
        feature_workers=4,
        executed_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
        transcript_extractor=FakeTranscriptExtractor(),
    )

    assert len(result) == 1
    assert len(repo.feature_rows) == 2
    assert {row["video_id"] for row in repo.feature_rows} == {"new-video", "stored-video"}
    assert all(row["transcript_status"] == "complete" for row in repo.feature_rows)


def test_run_batch_scrape_reuses_existing_features_without_reextracting() -> None:
    repo = FakeRepository()
    repo.existing_feature_rows = {
        "new-video": {
            "video_id": "new-video",
            "channel_handle": "@channel",
            "extracted_at": "2026-04-01T00:00:00+00:00",
            "extractor_version": "v1",
            "title_fingerprint": "0d077777982fd2f8d38e99bca33179e46d6f3685",
            "thumbnail_fingerprint": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
            "source_title": "Title new-video",
            "source_thumbnail_url": None,
            "title_length_chars": 15,
            "title_word_count": 2,
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
            "transcript_status": "complete",
            "transcript_language": "en",
            "transcript_is_auto_generated": False,
            "transcript_text": "Existing transcript",
            "thumbnail_feature_status": "complete",
            "thumbnail_ocr_status": "extracted",
            "has_face": False,
            "face_count": 0,
            "has_thumbnail_text": True,
            "estimated_thumbnail_text_tokens": 2,
            "thumbnail_text": "BIG MOVE",
            "thumbnail_text_confidence": 0.9,
            "dominant_emotion": None,
            "dominant_colors": ["#000000"],
            "composition_type": "balanced",
            "contains_chart": False,
            "contains_map": False,
            "visual_style": "graphic",
            "updated_at": "2026-04-01T00:00:00+00:00",
        }
    }
    transcript_extractor = FakeTranscriptExtractor()
    thumbnail_extractor = CountingThumbnailExtractor()

    run_batch_scrape(
        FakeYouTubeClient(),
        repo,
        limit=10,
        monitor_days=30,
        baseline_window_days=30,
        feature_workers=1,
        executed_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
        transcript_extractor=transcript_extractor,
        thumbnail_extractor=thumbnail_extractor,
    )

    assert transcript_extractor.calls == 1
    assert thumbnail_extractor.calls == 1
    assert len(repo.feature_rows) == 2
    reused_row = next(row for row in repo.feature_rows if row["video_id"] == "new-video")
    assert reused_row["transcript_text"] == "Existing transcript"
    assert reused_row["thumbnail_text"] == "BIG MOVE"


def test_run_batch_scrape_retries_transcript_when_previous_status_was_download_failed() -> None:
    repo = FakeRepository()
    repo.existing_feature_rows = {
        "new-video": {
            "video_id": "new-video",
            "channel_handle": "@channel",
            "extracted_at": "2026-04-01T00:00:00+00:00",
            "extractor_version": "v1",
            "title_fingerprint": "0d077777982fd2f8d38e99bca33179e46d6f3685",
            "thumbnail_fingerprint": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
            "source_title": "Title new-video",
            "source_thumbnail_url": None,
            "title_length_chars": 15,
            "title_word_count": 2,
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
            "transcript_status": "download_failed",
            "transcript_language": None,
            "transcript_is_auto_generated": None,
            "transcript_text": None,
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
            "updated_at": "2026-04-01T00:00:00+00:00",
        }
    }
    transcript_extractor = FakeTranscriptExtractor()
    thumbnail_extractor = CountingThumbnailExtractor()

    run_batch_scrape(
        FakeYouTubeClient(),
        repo,
        limit=10,
        monitor_days=30,
        baseline_window_days=30,
        feature_workers=1,
        executed_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
        transcript_extractor=transcript_extractor,
        thumbnail_extractor=thumbnail_extractor,
    )

    assert transcript_extractor.calls == 2
    retried_row = next(row for row in repo.feature_rows if row["video_id"] == "new-video")
    assert retried_row["transcript_status"] == "complete"
    assert retried_row["transcript_text"] == "Transcript for new-video"


def test_run_batch_scrape_retries_transcript_when_previous_status_was_video_unplayable() -> None:
    repo = FakeRepository()
    repo.existing_feature_rows = {
        "new-video": {
            "video_id": "new-video",
            "channel_handle": "@channel",
            "extracted_at": "2026-04-01T00:00:00+00:00",
            "extractor_version": "v1",
            "title_fingerprint": "0d077777982fd2f8d38e99bca33179e46d6f3685",
            "thumbnail_fingerprint": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
            "source_title": "Title new-video",
            "source_thumbnail_url": None,
            "title_length_chars": 15,
            "title_word_count": 2,
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
            "transcript_status": "video_unplayable",
            "transcript_language": None,
            "transcript_is_auto_generated": None,
            "transcript_text": None,
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
            "updated_at": "2026-04-01T00:00:00+00:00",
        }
    }
    transcript_extractor = FakeTranscriptExtractor()
    thumbnail_extractor = CountingThumbnailExtractor()

    run_batch_scrape(
        FakeYouTubeClient(),
        repo,
        limit=10,
        monitor_days=30,
        baseline_window_days=30,
        feature_workers=1,
        executed_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
        transcript_extractor=transcript_extractor,
        thumbnail_extractor=thumbnail_extractor,
    )

    assert transcript_extractor.calls == 2
    retried_row = next(row for row in repo.feature_rows if row["video_id"] == "new-video")
    assert retried_row["transcript_status"] == "complete"


def test_run_batch_scrape_reuses_transcript_but_refreshes_title_features_when_title_changes() -> None:
    repo = FakeRepository()
    repo.existing_feature_rows = {
        "new-video": {
            "video_id": "new-video",
            "channel_handle": "@channel",
            "extracted_at": "2026-04-01T00:00:00+00:00",
            "extractor_version": "v1",
            "title_fingerprint": "old-title-hash",
            "thumbnail_fingerprint": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
            "source_title": "Old title",
            "source_thumbnail_url": None,
            "title_length_chars": 9,
            "title_word_count": 2,
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
            "transcript_status": "complete",
            "transcript_language": "en",
            "transcript_is_auto_generated": False,
            "transcript_text": "Existing transcript",
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
            "updated_at": "2026-04-01T00:00:00+00:00",
        }
    }
    transcript_extractor = FakeTranscriptExtractor()
    thumbnail_extractor = CountingThumbnailExtractor()

    run_batch_scrape(
        CustomVideoYouTubeClient({"new-video": {"title": "Updated new-video title"}}),
        repo,
        limit=10,
        monitor_days=30,
        baseline_window_days=30,
        feature_workers=1,
        executed_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
        transcript_extractor=transcript_extractor,
        thumbnail_extractor=thumbnail_extractor,
    )

    assert transcript_extractor.calls == 1
    assert thumbnail_extractor.calls == 1
    updated_row = next(row for row in repo.feature_rows if row["video_id"] == "new-video")
    assert updated_row["source_title"] == "Updated new-video title"
    assert updated_row["transcript_text"] == "Existing transcript"


def test_run_batch_scrape_recomputes_thumbnail_only_when_thumbnail_changes() -> None:
    repo = FakeRepository()
    repo.existing_feature_rows = {
        "new-video": {
            "video_id": "new-video",
            "channel_handle": "@channel",
            "extracted_at": "2026-04-01T00:00:00+00:00",
            "extractor_version": "v1",
            "title_fingerprint": "old-title-hash",
            "thumbnail_fingerprint": "old-thumb-hash",
            "source_title": "Title new-video",
            "source_thumbnail_url": "https://example.com/old.jpg",
            "title_length_chars": 15,
            "title_word_count": 2,
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
            "transcript_status": "complete",
            "transcript_language": "en",
            "transcript_is_auto_generated": False,
            "transcript_text": "Existing transcript",
            "thumbnail_feature_status": "complete",
            "thumbnail_ocr_status": "extracted",
            "has_face": False,
            "face_count": 0,
            "has_thumbnail_text": True,
            "estimated_thumbnail_text_tokens": 2,
            "thumbnail_text": "OLD TEXT",
            "thumbnail_text_confidence": 0.7,
            "dominant_emotion": None,
            "dominant_colors": ["#000000"],
            "composition_type": "balanced",
            "contains_chart": False,
            "contains_map": False,
            "visual_style": "graphic",
            "updated_at": "2026-04-01T00:00:00+00:00",
        }
    }
    transcript_extractor = FakeTranscriptExtractor()
    thumbnail_extractor = CountingThumbnailExtractor()

    run_batch_scrape(
        CustomVideoYouTubeClient({"new-video": {"thumbnail_url": "https://example.com/new.jpg"}}),
        repo,
        limit=10,
        monitor_days=30,
        baseline_window_days=30,
        feature_workers=1,
        executed_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
        transcript_extractor=transcript_extractor,
        thumbnail_extractor=thumbnail_extractor,
    )

    assert transcript_extractor.calls == 1
    assert thumbnail_extractor.calls == 2
    updated_row = next(row for row in repo.feature_rows if row["video_id"] == "new-video")
    assert updated_row["source_thumbnail_url"] == "https://example.com/new.jpg"
    assert updated_row["transcript_text"] == "Existing transcript"


def test_run_batch_scrape_retries_thumbnail_when_previous_status_was_download_failed() -> None:
    repo = FakeRepository()
    repo.existing_feature_rows = {
        "new-video": {
            "video_id": "new-video",
            "channel_handle": "@channel",
            "extracted_at": "2026-04-01T00:00:00+00:00",
            "extractor_version": "v1",
            "title_fingerprint": "0d077777982fd2f8d38e99bca33179e46d6f3685",
            "thumbnail_fingerprint": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
            "source_title": "Title new-video",
            "source_thumbnail_url": None,
            "title_length_chars": 15,
            "title_word_count": 2,
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
            "transcript_status": "complete",
            "transcript_language": "en",
            "transcript_is_auto_generated": False,
            "transcript_text": "Existing transcript",
            "thumbnail_feature_status": "download_failed",
            "thumbnail_ocr_status": "download_failed",
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
            "updated_at": "2026-04-01T00:00:00+00:00",
        }
    }
    transcript_extractor = FakeTranscriptExtractor()
    thumbnail_extractor = CountingThumbnailExtractor()

    run_batch_scrape(
        FakeYouTubeClient(),
        repo,
        limit=10,
        monitor_days=30,
        baseline_window_days=30,
        feature_workers=1,
        executed_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
        transcript_extractor=transcript_extractor,
        thumbnail_extractor=thumbnail_extractor,
    )

    assert transcript_extractor.calls == 1
    assert thumbnail_extractor.calls == 2
    retried_row = next(row for row in repo.feature_rows if row["video_id"] == "new-video")
    assert retried_row["thumbnail_feature_status"] == "no_thumbnail"


class FakeThumbnailExtractor:
    def __init__(self) -> None:
        self.calls = 0

    def extract_from_url(self, thumbnail_url):
        self.calls += 1
        raise AssertionError("thumbnail extraction should not be called")


class CountingThumbnailExtractor:
    def __init__(self) -> None:
        self.calls = 0

    def extract_from_url(self, thumbnail_url):
        self.calls += 1
        return ThumbnailImageFeatures(
            status="no_thumbnail",
            ocr_status="no_thumbnail",
            has_face=None,
            face_count=None,
            has_thumbnail_text=None,
            estimated_thumbnail_text_tokens=None,
            thumbnail_text=None,
            thumbnail_text_confidence=None,
            dominant_colors=None,
            composition_type=None,
            contains_chart=None,
            contains_map=None,
            visual_style=None,
        )
