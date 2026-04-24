from __future__ import annotations

from datetime import datetime
from typing import Any

from ..clients.supabase import SupabaseClient
from ..constants import SCRAPER_STATE_NAME
from ..exceptions import SupabaseAPIError
from ..models import VideoMetricSnapshot, parse_datetime, serialize_datetime

_IN_FILTER_BATCH_SIZE = 50


def _format_in_filter(values: list[str]) -> str:
    quoted = ",".join(f'"{value}"' for value in values)
    return f"in.({quoted})"


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _chunked(values: list[str], size: int) -> list[list[str]]:
    if size <= 0:
        raise ValueError("chunk size must be positive")
    return [values[index : index + size] for index in range(0, len(values), size)]


class SupabaseRepository:
    def __init__(self, client: SupabaseClient) -> None:
        self.client = client

    def _fetch_rows_in_chunks(
        self,
        table_name: str,
        filter_field: str,
        values: list[str],
        *,
        select: str,
        limit: int = 5000,
        order: str | None = None,
    ) -> list[dict[str, Any]]:
        if not values:
            return []

        rows: list[dict[str, Any]] = []
        for chunk in _chunked(_dedupe_preserve_order(values), _IN_FILTER_BATCH_SIZE):
            params: dict[str, Any] = {
                "select": select,
                filter_field: _format_in_filter(chunk),
                "limit": limit,
            }
            if order is not None:
                params["order"] = order
            payload = self.client.request(
                "GET",
                table_name,
                params=params,
            ) or []
            rows.extend(payload)
        return rows

    def get_active_channel_configs(self) -> list[dict[str, Any]]:
        payload = self.client.request(
            "GET",
            "yt_channels",
            params={
                "select": "channel_handle,thumbnail_analysis,channel_niche",
                "is_active": "eq.true",
                "order": "id.asc",
            },
        )
        return [
            {
                "channel_handle": row["channel_handle"],
                "thumbnail_analysis": bool(row.get("thumbnail_analysis")),
                "channel_niche": row.get("channel_niche"),
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

    def get_current_video_rows(self, video_ids: list[str], *, limit: int = 5000) -> dict[str, dict[str, Any]]:
        payload = self._fetch_rows_in_chunks(
            "yt_videos",
            "video_id",
            video_ids,
            select=(
                "video_id,channel_handle,title,published_at,thumbnail_url,"
                "view_count,like_count,comment_count,duration,duration_iso8601,video_url"
            ),
            limit=limit,
        )
        return {
            str(row["video_id"]): row
            for row in payload
            if row.get("video_id")
        }

    def get_feature_rows(self, video_ids: list[str], *, limit: int = 5000) -> dict[str, dict[str, Any]]:
        payload = self._fetch_rows_in_chunks(
            "yt_video_features",
            "video_id",
            video_ids,
            select="*",
            limit=limit,
        )
        return {
            str(row["video_id"]): row
            for row in payload
            if row.get("video_id")
        }

    def get_channel_niches(self, channel_handles: list[str], *, limit: int = 5000) -> dict[str, str | None]:
        payload = self._fetch_rows_in_chunks(
            "yt_channels",
            "channel_handle",
            channel_handles,
            select="channel_handle,channel_niche",
            limit=limit,
        )
        return {
            str(row["channel_handle"]): row.get("channel_niche")
            for row in payload
            if row.get("channel_handle")
        }

    def list_topic_cluster_candidates(
        self,
        *,
        limit: int = 200,
        after_video_id: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "select": "*",
            "order": "video_id.asc",
            "limit": limit,
        }
        if after_video_id:
            params["video_id"] = f"gt.{after_video_id}"

        feature_rows = self.client.request(
            "GET",
            "yt_video_features",
            params=params,
        ) or []
        if not feature_rows:
            return []

        channel_niches = self.get_channel_niches(
            [str(row["channel_handle"]) for row in feature_rows if row.get("channel_handle")],
            limit=max(limit, len(feature_rows)),
        )
        candidates: list[dict[str, Any]] = []
        for feature_row in feature_rows:
            video_id = str(feature_row.get("video_id") or "")
            channel_handle = str(feature_row.get("channel_handle") or "")
            candidates.append(
                {
                    "video_id": video_id,
                    "channel_handle": channel_handle,
                    "title": feature_row.get("source_title"),
                    "channel_niche": channel_niches.get(channel_handle),
                    "feature_row": feature_row,
                }
            )
        return candidates

    def get_snapshots_for_channels(
        self,
        channel_handles: list[str],
        *,
        published_after: datetime,
        limit: int = 5000,
    ) -> list[VideoMetricSnapshot]:
        payload: list[dict[str, Any]] = []
        for chunk in _chunked(_dedupe_preserve_order(channel_handles), _IN_FILTER_BATCH_SIZE):
            chunk_payload = self.client.request(
                "GET",
                "yt_video_metric_snapshots",
                params={
                    "select": (
                        "video_id,channel_handle,snapshot_at,published_at,"
                        "view_count,like_count,comment_count"
                    ),
                    "channel_handle": _format_in_filter(chunk),
                    "published_at": f"gte.{serialize_datetime(published_after)}",
                    "order": "snapshot_at.asc",
                    "limit": limit,
                },
            ) or []
            payload.extend(chunk_payload)
        return [VideoMetricSnapshot.from_row(row) for row in payload or []]

    def get_latest_snapshot_rows(self, video_ids: list[str], *, limit: int = 5000) -> dict[str, dict[str, Any]]:
        payload = self._fetch_rows_in_chunks(
            "vw_latest_yt_video_metric_snapshots",
            "video_id",
            video_ids,
            select=(
                "video_id,channel_handle,snapshot_at,published_at,title,thumbnail_url,"
                "view_count,like_count,comment_count"
            ),
            limit=limit,
        )
        return {
            str(row["video_id"]): row
            for row in payload
            if row.get("video_id")
        }

    def _upsert_rows(
        self,
        table_name: str,
        rows: list[dict[str, Any]],
        *,
        on_conflict: str,
    ) -> None:
        if not rows:
            return

        try:
            self.client.request(
                "POST",
                table_name,
                params={"on_conflict": on_conflict},
                json_body=rows,
                extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
            )
        except SupabaseAPIError as exc:
            row_count = len(rows)
            sample_ids = [
                str(row.get("video_id"))
                for row in rows[:5]
                if row.get("video_id") is not None
            ]
            detail = f"{row_count} rows"
            if sample_ids:
                detail += f", sample video_ids={sample_ids}"
            raise SupabaseAPIError(
                f"Failed to upsert into {table_name}: {detail}: {exc}"
            ) from exc

    def upsert_current_videos(self, rows: list[dict[str, Any]]) -> None:
        self._upsert_rows("yt_videos", rows, on_conflict="video_id")

    def insert_snapshots(self, rows: list[dict[str, Any]]) -> None:
        self._upsert_rows("yt_video_metric_snapshots", rows, on_conflict="video_id,snapshot_at")

    def upsert_performance_rows(self, rows: list[dict[str, Any]]) -> None:
        self._upsert_rows("yt_video_performance", rows, on_conflict="video_id")

    def upsert_feature_rows(self, rows: list[dict[str, Any]]) -> None:
        self._upsert_rows("yt_video_features", rows, on_conflict="video_id")

    def replace_video_topics(self, topics_by_video_id: dict[str, list[str]]) -> None:
        if not topics_by_video_id:
            return

        for chunk in _chunked(_dedupe_preserve_order(list(topics_by_video_id.keys())), _IN_FILTER_BATCH_SIZE):
            self.client.request(
                "DELETE",
                "yt_video_topics",
                params={"video_id": _format_in_filter(chunk)},
            )
        rows = [
            {"video_id": video_id, "topic_cluster": topic_cluster}
            for video_id, topic_clusters in topics_by_video_id.items()
            for topic_cluster in topic_clusters
        ]
        if rows:
            self._upsert_rows("yt_video_topics", rows, on_conflict="video_id,topic_cluster")

    def get_topic_cluster_debug_inputs(self, video_ids: list[str], *, limit: int = 5000) -> list[dict[str, Any]]:
        videos_payload = self._fetch_rows_in_chunks(
            "yt_videos",
            "video_id",
            video_ids,
            select="video_id,channel_handle,title",
            limit=limit,
        )
        if not videos_payload:
            return []

        feature_rows = self.get_feature_rows(video_ids, limit=limit)
        channel_niches = self.get_channel_niches(
            [str(row["channel_handle"]) for row in videos_payload if row.get("channel_handle")],
            limit=limit,
        )
        videos_by_id = {
            str(row["video_id"]): row
            for row in videos_payload
            if row.get("video_id")
        }

        ordered_rows: list[dict[str, Any]] = []
        for video_id in video_ids:
            video_row = videos_by_id.get(video_id)
            if video_row is None:
                continue
            channel_handle = str(video_row.get("channel_handle") or "")
            feature_row = feature_rows.get(video_id, {})
            ordered_rows.append(
                {
                    "video_id": video_id,
                    "channel_handle": channel_handle,
                    "title": video_row.get("title"),
                    "thumbnail_text": feature_row.get("thumbnail_text"),
                    "channel_niche": channel_niches.get(channel_handle),
                    "existing_format_type": feature_row.get("format_type"),
                    "existing_promise_type": feature_row.get("promise_type"),
                    "existing_topic_cluster_status": feature_row.get("topic_cluster_status"),
                }
            )
        return ordered_rows

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
