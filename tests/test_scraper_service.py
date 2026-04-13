from __future__ import annotations

from datetime import datetime, timezone

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


class FakeRepository:
    def __init__(self) -> None:
        self.current_rows: list[dict] = []
        self.snapshot_rows: list[dict] = []
        self.feature_rows: list[dict] = []
        self.performance_rows: list[dict] = []
        self.updated_at = None

    def get_active_channel_handles(self) -> list[str]:
        return ["@channel"]

    def get_recent_video_ids(self, channel_handle: str, *, published_after, limit: int = 200) -> list[str]:
        return ["stored-video"]

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
        executed_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
    )

    assert len(result) == 1
    assert len(repo.current_rows) == 2
    assert len(repo.snapshot_rows) == 2
    assert len(repo.feature_rows) == 2
    assert all(row["thumbnail_feature_status"] == "no_thumbnail" for row in repo.feature_rows)
    assert repo.updated_at == datetime(2026, 4, 13, tzinfo=timezone.utc)
