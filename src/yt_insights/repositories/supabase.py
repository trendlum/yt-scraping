from __future__ import annotations

from datetime import datetime
from typing import Any

from ..clients.supabase import SupabaseClient
from ..constants import SCRAPER_STATE_NAME
from ..models import VideoMetricSnapshot, parse_datetime, serialize_datetime


def _format_in_filter(values: list[str]) -> str:
    quoted = ",".join(f'"{value}"' for value in values)
    return f"in.({quoted})"


class SupabaseRepository:
    def __init__(self, client: SupabaseClient) -> None:
        self.client = client

    def get_active_channel_configs(self) -> list[dict[str, Any]]:
        payload = self.client.request(
            "GET",
            "yt_channels",
            params={
                "select": "channel_handle,thumbnail_analysis",
                "is_active": "eq.true",
                "order": "id.asc",
            },
        )
        return [
            {
                "channel_handle": row["channel_handle"],
                "thumbnail_analysis": bool(row.get("thumbnail_analysis")),
            }
            for row in payload or []
            if row.get("channel_handle")
        ]

    def get_active_channel_handles(self) -> list[str]:
        return [row["channel_handle"] for row in self.get_active_channel_configs()]

    def get_last_scraper_run(self, scraper_name: str = SCRAPER_STATE_NAME) -> datetime | None:
        payload = self.client.request(
            "GET",
            "yt_scraper_state",
            params={
                "select": "scraper_name,last_run_at",
                "scraper_name": f"eq.{scraper_name}",
                "limit": 1,
            },
        )
        if not payload:
            return None
        return parse_datetime(payload[0].get("last_run_at"))

    def get_recent_video_ids(
        self,
        channel_handle: str,
        *,
        published_after: datetime,
        limit: int = 200,
    ) -> list[str]:
        payload = self.client.request(
            "GET",
            "yt_videos",
            params={
                "select": "video_id",
                "channel_handle": f"eq.{channel_handle}",
                "published_at": f"gte.{serialize_datetime(published_after)}",
                "order": "published_at.desc",
                "limit": limit,
            },
        )
        return [row["video_id"] for row in payload or [] if row.get("video_id")]

    def get_snapshots_for_channels(
        self,
        channel_handles: list[str],
        *,
        published_after: datetime,
        limit: int = 5000,
    ) -> list[VideoMetricSnapshot]:
        if not channel_handles:
            return []

        payload = self.client.request(
            "GET",
            "yt_video_metric_snapshots",
            params={
                "select": (
                    "video_id,channel_handle,snapshot_at,published_at,"
                    "view_count,like_count,comment_count"
                ),
                "channel_handle": _format_in_filter(channel_handles),
                "published_at": f"gte.{serialize_datetime(published_after)}",
                "order": "snapshot_at.asc",
                "limit": limit,
            },
        )
        return [VideoMetricSnapshot.from_row(row) for row in payload or []]

    def _upsert_rows(
        self,
        table_name: str,
        rows: list[dict[str, Any]],
        *,
        on_conflict: str,
    ) -> None:
        if not rows:
            return

        self.client.request(
            "POST",
            table_name,
            params={"on_conflict": on_conflict},
            json_body=rows,
            extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )

    def upsert_current_videos(self, rows: list[dict[str, Any]]) -> None:
        self._upsert_rows("yt_videos", rows, on_conflict="video_id")

    def insert_snapshots(self, rows: list[dict[str, Any]]) -> None:
        self._upsert_rows("yt_video_metric_snapshots", rows, on_conflict="video_id,snapshot_at")

    def upsert_performance_rows(self, rows: list[dict[str, Any]]) -> None:
        self._upsert_rows("yt_video_performance", rows, on_conflict="video_id")

    def upsert_feature_rows(self, rows: list[dict[str, Any]]) -> None:
        self._upsert_rows("yt_video_features", rows, on_conflict="video_id")

    def update_scraper_state(
        self,
        executed_at: datetime,
        scraper_name: str = SCRAPER_STATE_NAME,
    ) -> None:
        self.client.request(
            "POST",
            "yt_scraper_state",
            params={"on_conflict": "scraper_name"},
            json_body=[
                {
                    "scraper_name": scraper_name,
                    "last_run_at": serialize_datetime(executed_at),
                }
            ],
            extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )
