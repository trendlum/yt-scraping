from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any

from ..analytics.transcript_features import TranscriptFeatureExtractor
from ..clients.supabase import SupabaseClient
from ..constants import DEFAULT_FEATURE_WORKERS, DEFAULT_MONITOR_DAYS, DEFAULT_TIMEOUT
from ..models import serialize_datetime, utc_now
from ..repositories.supabase import SupabaseRepository


_TRANSCRIPT_BACKFILL_STATUSES = {
    None,
    "",
    "pending",
    "skipped",
    "download_failed",
    "request_blocked",
    "ip_blocked",
    "dependency_missing",
    "video_unplayable",
    "no_captions",
}


def _resolve_feature_workers(feature_workers: int | None) -> int:
    if feature_workers is None:
        return DEFAULT_FEATURE_WORKERS
    return max(1, feature_workers)


def refresh_recent_transcripts(
    repository: SupabaseRepository,
    *,
    limit: int | None = None,
    monitor_days: int = DEFAULT_MONITOR_DAYS,
    feature_workers: int | None = DEFAULT_FEATURE_WORKERS,
    executed_at: datetime | None = None,
    transcript_extractor: TranscriptFeatureExtractor | None = None,
) -> list[dict[str, Any]]:
    run_started_at = executed_at or utc_now()
    monitor_cutoff = run_started_at - timedelta(days=monitor_days)
    feature_workers = _resolve_feature_workers(feature_workers)
    timeout = DEFAULT_TIMEOUT

    channel_handles = repository.get_active_channel_handles()
    candidate_ids: list[str] = []
    seen_ids: set[str] = set()
    for channel_handle in channel_handles:
        recent_video_ids = repository.get_recent_video_ids(
            channel_handle,
            published_after=monitor_cutoff,
            limit=max(limit or 0, 200),
        )
        for video_id in recent_video_ids:
            if video_id in seen_ids:
                continue
            seen_ids.add(video_id)
            candidate_ids.append(video_id)

    existing_feature_rows = repository.get_feature_rows(candidate_ids)
    rows_to_refresh = [
        row
        for row in existing_feature_rows.values()
        if row.get("transcript_status") in _TRANSCRIPT_BACKFILL_STATUSES
    ]
    if not rows_to_refresh:
        return []

    shared_extractor = transcript_extractor or TranscriptFeatureExtractor(timeout=timeout)

    def build_row(feature_row: dict[str, Any]) -> dict[str, Any]:
        merged_row = dict(feature_row)
        extracted = shared_extractor.extract_from_video_id(str(feature_row["video_id"]))
        merged_row["transcript_status"] = extracted.status
        merged_row["transcript_language"] = extracted.language
        merged_row["transcript_is_auto_generated"] = extracted.is_auto_generated
        merged_row["transcript_text"] = extracted.transcript_text
        merged_row["updated_at"] = serialize_datetime(run_started_at)
        return merged_row

    if feature_workers <= 1 or len(rows_to_refresh) == 1:
        refreshed_rows = [build_row(row) for row in rows_to_refresh]
    else:
        max_workers = min(feature_workers, len(rows_to_refresh), max(1, (os.cpu_count() or 1) * 4))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            refreshed_rows = list(executor.map(build_row, rows_to_refresh))

    repository.upsert_feature_rows(refreshed_rows)
    return refreshed_rows


def backfill_recent_transcripts(
    supabase_url: str,
    supabase_key: str,
    limit: int | None,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    monitor_days: int = DEFAULT_MONITOR_DAYS,
    feature_workers: int | None = DEFAULT_FEATURE_WORKERS,
) -> list[dict[str, Any]]:
    repository = SupabaseRepository(
        SupabaseClient(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            timeout=timeout,
        )
    )
    return refresh_recent_transcripts(
        repository,
        limit=limit,
        monitor_days=monitor_days,
        feature_workers=feature_workers,
    )
