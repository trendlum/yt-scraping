from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

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
        self.original_feature_rows: list[dict] = []
        self.performance_rows: list[dict] = []
        self.updated_at = None
        self.existing_current_rows: dict[str, dict] = {}
        self.existing_feature_rows: dict[str, dict] = {}
        self.latest_snapshot_rows: dict[str, dict] = {}
        self.topic_candidates: list[dict] = []
        self.replaced_topics: dict[str, list[str]] = {}

    def get_active_channel_configs(self) -> list[dict]:
        return [{"channel_handle": "@channel", "thumbnail_analysis": True, "channel_niche": "crypto"}]

    def get_recent_video_ids(self, channel_handle: str, *, published_after, limit: int = 200) -> list[str]:
        return ["stored-video"]

    def get_feature_rows(self, video_ids: list[str], *, limit: int = 5000) -> dict[str, dict]:
        return {
            video_id: self.existing_feature_rows[video_id]
            for video_id in video_ids
            if video_id in self.existing_feature_rows
        }

    def get_current_video_rows(self, video_ids: list[str], *, limit: int = 5000) -> dict[str, dict]:
        return {
            video_id: self.existing_current_rows[video_id]
            for video_id in video_ids
            if video_id in self.existing_current_rows
        }

    def get_latest_snapshot_rows(self, video_ids: list[str], *, limit: int = 5000) -> dict[str, dict]:
        return {
            video_id: self.latest_snapshot_rows[video_id]
            for video_id in video_ids
            if video_id in self.latest_snapshot_rows
        }

    def upsert_current_videos(self, rows: list[dict]) -> None:
        self.current_rows = rows

    def insert_snapshots(self, rows: list[dict]) -> None:
        self.snapshot_rows = rows

    def upsert_feature_rows(self, rows: list[dict]) -> None:
        if rows and "title_pattern" in rows[0]:
            self.original_feature_rows = rows
        self.feature_rows = rows

    def list_topic_cluster_candidates(self, *, limit: int = 200, after_video_id: str | None = None) -> list[dict]:
        if not self.topic_candidates:
            return []
        rows = self.topic_candidates
        if after_video_id is not None:
            rows = [row for row in rows if str(row["video_id"]) > after_video_id]
        return rows[:limit]

    def replace_video_topics(self, topics_by_video_id: dict[str, list[str]]) -> None:
        self.replaced_topics.update(topics_by_video_id)

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


def test_merge_unique_video_ids_preserves_order() -> None:
    assert merge_unique_video_ids(["a", "b"], ["b", "c"]) == ["a", "b", "c"]


def test_load_topic_cluster_prompt_uses_packaged_resource_when_repo_path_is_missing(monkeypatch, tmp_path) -> None:
    from yt_insights.services import topic_clustering

    monkeypatch.setattr(topic_clustering, "BOT_PROMPT_PATH", tmp_path / "missing-topic_cluster.txt")

    prompt = topic_clustering.load_topic_cluster_prompt()

    assert prompt.description == "Extract topic clusters, format_type and promise_type from a YouTube video"
    assert prompt.model == "deepseek-chat"
    assert "Return ONLY valid JSON" in prompt.system_prompt
    assert prompt.user_template == "Channel niche: {{channel_niche}}\nTitle: {{title}}\nThumbnail text: {{thumbnail_text}}"


def test_packaged_topic_cluster_prompt_matches_repo_prompt() -> None:
    repo_prompt = (Path("bots") / "topic_cluster.txt").read_text(encoding="utf-8")
    packaged_prompt = (Path("src") / "yt_insights" / "bots" / "topic_cluster.txt").read_text(encoding="utf-8")

    assert packaged_prompt == repo_prompt


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
    )

    assert len(result) == 1
    assert len(repo.current_rows) == 2
    assert len(repo.snapshot_rows) == 2
    assert len(repo.original_feature_rows) == 2
    assert all(row["thumbnail_feature_status"] == "no_thumbnail" for row in repo.original_feature_rows)
    assert all(row["thumbnail_ocr_status"] == "no_thumbnail" for row in repo.original_feature_rows)
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
        thumbnail_extractor=thumbnail_extractor,
    )

    assert len(result) == 1
    assert thumbnail_extractor.calls == 0
    assert all(row["thumbnail_feature_status"] == "skipped" for row in repo.original_feature_rows)
    assert all(row["thumbnail_ocr_status"] == "skipped" for row in repo.original_feature_rows)
    assert all(row["thumbnail_text"] is None for row in repo.original_feature_rows)


def test_run_batch_scrape_reuses_existing_thumbnail_features_when_thumbnail_unchanged() -> None:
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
    thumbnail_extractor = CountingThumbnailExtractor()

    run_batch_scrape(
        FakeYouTubeClient(),
        repo,
        limit=10,
        monitor_days=30,
        baseline_window_days=30,
        feature_workers=1,
        executed_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
        thumbnail_extractor=thumbnail_extractor,
    )

    assert thumbnail_extractor.calls == 1
    assert len(repo.original_feature_rows) == 2
    reused_row = next(row for row in repo.original_feature_rows if row["video_id"] == "new-video")
    assert reused_row["thumbnail_text"] == "BIG MOVE"


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
    thumbnail_extractor = CountingThumbnailExtractor()

    run_batch_scrape(
        FakeYouTubeClient(),
        repo,
        limit=10,
        monitor_days=30,
        baseline_window_days=30,
        feature_workers=1,
        executed_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
        thumbnail_extractor=thumbnail_extractor,
    )

    assert thumbnail_extractor.calls == 2
    retried_row = next(row for row in repo.original_feature_rows if row["video_id"] == "new-video")
    assert retried_row["thumbnail_feature_status"] == "no_thumbnail"


def test_run_batch_scrape_runs_topic_clustering_for_all_candidate_videos() -> None:
    class FakeTopicClusterClient:
        @property
        def prompt(self):
            from yt_insights.services.topic_clustering import load_topic_cluster_prompt

            return load_topic_cluster_prompt()

        @property
        def model(self) -> str:
            return "deepseek-reasoner"

        def classify(self, *, title: str, thumbnail_text: str | None, channel_niche: str):
            from yt_insights.ai_usage import AiUsage
            from yt_insights.services.topic_clustering import TopicClusterResult

            return TopicClusterResult(
                topic_clusters=["bitcoin etf flows"],
                format_type="news_breakdown",
                promise_type="news",
                usage=AiUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15, calls=1),
                model="deepseek-reasoner",
                provider="deepseek",
            )

    repo = FakeRepository()
    executed_at = datetime(2026, 4, 13, tzinfo=timezone.utc)
    run_batch_scrape(
        FakeYouTubeClient(),
        repo,
        limit=10,
        monitor_days=30,
        baseline_window_days=30,
        feature_workers=1,
        executed_at=executed_at,
    )

    run_batch_scrape(
        FakeYouTubeClient(),
        repo,
        limit=10,
        monitor_days=30,
        baseline_window_days=30,
        feature_workers=1,
        executed_at=executed_at,
        topic_cluster_client=FakeTopicClusterClient(),
    )

    assert repo.replaced_topics == {
        "new-video": ["bitcoin etf flows"],
        "stored-video": ["bitcoin etf flows"],
    }
    assert all(row["topic_cluster_status"] == "complete" for row in repo.feature_rows)
    assert all(row["topic_clusters"] == ["bitcoin etf flows"] for row in repo.feature_rows)


def test_run_batch_scrape_skips_videos_that_already_have_topic_cluster_fields() -> None:
    from yt_insights.services.topic_clustering import _topic_cluster_input_fingerprint, load_topic_cluster_prompt

    class FailingTopicClusterClient:
        @property
        def prompt(self):
            return load_topic_cluster_prompt()

        @property
        def model(self) -> str:
            return "deepseek-chat"

        def classify(self, *, title: str, thumbnail_text: str | None, channel_niche: str):
            raise AssertionError("LLM should not be called for already completed rows")

    repo = FakeRepository()
    executed_at = datetime(2026, 4, 13, tzinfo=timezone.utc)
    run_batch_scrape(
        FakeYouTubeClient(),
        repo,
        limit=10,
        monitor_days=30,
        baseline_window_days=30,
        feature_workers=1,
        executed_at=executed_at,
    )

    repo.existing_feature_rows = {}
    prompt = load_topic_cluster_prompt()
    for row in repo.original_feature_rows:
        complete_row = dict(row)
        complete_row.update(
            {
                "topic_cluster_status": "complete",
                "topic_clusters": ["bitcoin etf flows"],
                "format_type": "news_breakdown",
                "promise_type": "news",
                "topic_cluster_input_fingerprint": _topic_cluster_input_fingerprint(
                    prompt_fingerprint=prompt.prompt_fingerprint,
                    title=complete_row.get("source_title"),
                    thumbnail_text=complete_row.get("thumbnail_text"),
                    channel_niche="crypto",
                ),
            }
        )
        repo.existing_feature_rows[complete_row["video_id"]] = complete_row

    run_batch_scrape(
        FakeYouTubeClient(),
        repo,
        limit=10,
        monitor_days=30,
        baseline_window_days=30,
        feature_workers=1,
        executed_at=executed_at,
        topic_cluster_client=FailingTopicClusterClient(),
    )

    assert repo.replaced_topics == {}


def test_run_batch_scrape_skips_unchanged_snapshots_within_24_hours() -> None:
    repo = FakeRepository()
    repo.latest_snapshot_rows = {
        "new-video": {
            "video_id": "new-video",
            "channel_handle": "@channel",
            "snapshot_at": "2026-04-12T18:00:00+00:00",
            "published_at": "2026-04-10T00:00:00+00:00",
            "title": "Title new-video",
            "thumbnail_url": None,
            "view_count": 100,
            "like_count": 10,
            "comment_count": 1,
        },
        "stored-video": {
            "video_id": "stored-video",
            "channel_handle": "@channel",
            "snapshot_at": "2026-04-11T00:00:00+00:00",
            "published_at": "2026-04-10T00:00:00+00:00",
            "title": "Title stored-video",
            "thumbnail_url": None,
            "view_count": 100,
            "like_count": 10,
            "comment_count": 1,
        },
    }

    run_batch_scrape(
        FakeYouTubeClient(),
        repo,
        limit=10,
        monitor_days=30,
        baseline_window_days=30,
        feature_workers=1,
        executed_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
    )

    assert [row["video_id"] for row in repo.snapshot_rows] == ["stored-video"]


def test_run_batch_scrape_skips_unchanged_current_and_feature_upserts() -> None:
    initial_repo = FakeRepository()
    executed_at = datetime(2026, 4, 13, tzinfo=timezone.utc)
    run_batch_scrape(
        FakeYouTubeClient(),
        initial_repo,
        limit=10,
        monitor_days=30,
        baseline_window_days=30,
        feature_workers=1,
        executed_at=executed_at,
    )

    repo = FakeRepository()
    repo.existing_current_rows = {
        row["video_id"]: {
            key: row[key]
            for key in (
                "video_id",
                "channel_handle",
                "title",
                "published_at",
                "thumbnail_url",
                "view_count",
                "like_count",
                "comment_count",
                "duration",
                "duration_iso8601",
                "video_url",
            )
        }
        for row in initial_repo.current_rows
    }
    repo.existing_feature_rows = {
        row["video_id"]: dict(row)
        for row in initial_repo.original_feature_rows
    }

    run_batch_scrape(
        FakeYouTubeClient(),
        repo,
        limit=10,
        monitor_days=30,
        baseline_window_days=30,
        feature_workers=1,
        executed_at=executed_at,
    )

    assert repo.current_rows == []
    assert repo.original_feature_rows == []
