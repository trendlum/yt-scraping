from __future__ import annotations

import os
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any

from ..analytics.performance import build_performance_records
from ..analytics.transcript_features import TranscriptFeatureExtractor, enrich_transcript_features
from ..analytics.thumbnail_features import ThumbnailFeatureExtractor, enrich_thumbnail_features
from ..analytics.title_features import extract_title_features
from ..clients.supabase import SupabaseClient
from ..clients.youtube import YouTubeClient
from ..constants import (
    DEFAULT_BASELINE_WINDOW_DAYS,
    DEFAULT_FEATURE_WORKERS,
    DEFAULT_MONITOR_DAYS,
    DEFAULT_TIMEOUT,
)
from ..exceptions import YouTubeAPIError
from ..models import ChannelScrapeResult, utc_now
from ..repositories.supabase import SupabaseRepository


LOGGER = logging.getLogger(__name__)

_TRANSCRIPT_FIELDS = (
    "transcript_status",
    "transcript_language",
    "transcript_is_auto_generated",
    "transcript_text",
)

_THUMBNAIL_FIELDS = (
    "thumbnail_feature_status",
    "thumbnail_ocr_status",
    "has_face",
    "face_count",
    "has_thumbnail_text",
    "estimated_thumbnail_text_tokens",
    "thumbnail_text",
    "thumbnail_text_confidence",
    "dominant_emotion",
    "dominant_colors",
    "composition_type",
    "contains_chart",
    "contains_map",
    "visual_style",
)


def merge_unique_video_ids(*video_id_groups: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for group in video_id_groups:
        for video_id in group:
            if video_id in seen:
                continue
            seen.add(video_id)
            ordered.append(video_id)
    return ordered


def scrape_channel_result(
    youtube_client: YouTubeClient,
    channel_handle: str,
    *,
    limit: int | None,
    published_after: datetime | None = None,
) -> ChannelScrapeResult:
    return youtube_client.scrape_channel_latest_videos(
        channel_handle,
        limit=limit,
        published_after=published_after,
    )


def scrape_channel_for_monitoring(
    youtube_client: YouTubeClient,
    repository: SupabaseRepository,
    channel_handle: str,
    *,
    limit: int | None,
    monitor_cutoff: datetime,
) -> ChannelScrapeResult:
    channel_data = youtube_client.get_channel_by_handle(channel_handle)
    uploads_playlist_id = youtube_client.get_uploads_playlist_id(channel_data)
    latest_video_ids = youtube_client.list_upload_video_ids(
        uploads_playlist_id,
        limit=limit,
        published_after=monitor_cutoff,
    )
    stored_video_ids = repository.get_recent_video_ids(
        channel_handle,
        published_after=monitor_cutoff,
        limit=max(limit or 0, 200),
    )
    video_ids = merge_unique_video_ids(latest_video_ids, stored_video_ids)
    videos = youtube_client.get_videos_details(video_ids)
    return ChannelScrapeResult(
        channel_handle=channel_handle,
        channel_id=channel_data.get("id"),
        channel_name=channel_data.get("snippet", {}).get("title"),
        uploads_playlist_id=uploads_playlist_id,
        videos=videos,
    )


def _resolve_feature_workers(feature_workers: int | None) -> int:
    if feature_workers is None:
        return DEFAULT_FEATURE_WORKERS
    return max(1, feature_workers)


def _build_feature_row(
    video: Any,
    channel_handle: str,
    run_started_at: datetime,
    should_analyze_thumbnail: bool,
    transcript_extractor: TranscriptFeatureExtractor,
    thumbnail_extractor: ThumbnailFeatureExtractor,
) -> dict:
    feature_record = extract_title_features(
        video,
        channel_handle,
        extracted_at=run_started_at,
    )
    feature_record = enrich_transcript_features(feature_record, transcript_extractor)
    if should_analyze_thumbnail:
        feature_record = enrich_thumbnail_features(feature_record, thumbnail_extractor)
    else:
        feature_record.thumbnail_feature_status = "skipped"
        feature_record.thumbnail_ocr_status = "skipped"
        feature_record.has_thumbnail_text = None
        feature_record.estimated_thumbnail_text_tokens = None
        feature_record.thumbnail_text = None
        feature_record.thumbnail_text_confidence = None
    return feature_record.to_row()


def _parallel_feature_rows(
    videos: list[Any],
    *,
    channel_handle: str,
    run_started_at: datetime,
    should_analyze_thumbnail: bool,
    feature_workers: int,
    transcript_extractor_factory: Any,
    thumbnail_extractor_factory: Any,
    existing_feature_rows: dict[str, dict[str, Any]],
) -> list[dict]:
    if not videos:
        return []

    max_workers = min(feature_workers, len(videos), max(1, (os.cpu_count() or 1) * 4))

    def build_row(video: Any) -> dict:
        feature_record = extract_title_features(
            video,
            channel_handle,
            extracted_at=run_started_at,
        )
        existing_row = existing_feature_rows.get(video.video_id)

        if existing_row is not None:
            for field_name in _TRANSCRIPT_FIELDS:
                setattr(feature_record, field_name, existing_row.get(field_name))

            thumbnail_unchanged = (
                existing_row.get("thumbnail_fingerprint") == feature_record.thumbnail_fingerprint
            )
            if thumbnail_unchanged:
                for field_name in _THUMBNAIL_FIELDS:
                    setattr(feature_record, field_name, existing_row.get(field_name))
                return feature_record.to_row()

        if should_analyze_thumbnail:
            thumbnail_extractor = thumbnail_extractor_factory()
            feature_record = enrich_thumbnail_features(feature_record, thumbnail_extractor)
        else:
            feature_record.thumbnail_feature_status = "skipped"
            feature_record.thumbnail_ocr_status = "skipped"
            feature_record.has_thumbnail_text = None
            feature_record.estimated_thumbnail_text_tokens = None
            feature_record.thumbnail_text = None
            feature_record.thumbnail_text_confidence = None

        if existing_row is None:
            transcript_extractor = transcript_extractor_factory()
            feature_record = enrich_transcript_features(feature_record, transcript_extractor)

        return feature_record.to_row()

    if feature_workers <= 1 or len(videos) == 1:
        return [build_row(video) for video in videos]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(build_row, videos))


def run_batch_scrape(
    youtube_client: YouTubeClient,
    repository: SupabaseRepository,
    *,
    limit: int | None,
    monitor_days: int = DEFAULT_MONITOR_DAYS,
    baseline_window_days: int = DEFAULT_BASELINE_WINDOW_DAYS,
    feature_workers: int | None = DEFAULT_FEATURE_WORKERS,
    executed_at: datetime | None = None,
    transcript_extractor: TranscriptFeatureExtractor | None = None,
    thumbnail_extractor: ThumbnailFeatureExtractor | None = None,
) -> list[dict]:
    run_started_at = executed_at or utc_now()
    monitor_cutoff = run_started_at - timedelta(days=monitor_days)
    analytics_cutoff = run_started_at - timedelta(days=baseline_window_days)
    channel_configs = repository.get_active_channel_configs()

    results: list[ChannelScrapeResult] = []
    current_rows: list[dict] = []
    snapshot_rows: list[dict] = []
    feature_rows: list[dict] = []
    errors: list[str] = []
    feature_workers = _resolve_feature_workers(feature_workers)
    timeout = getattr(youtube_client, "timeout", DEFAULT_TIMEOUT)
    youtube_session = getattr(youtube_client, "session", None)

    if thumbnail_extractor is None:
        def thumbnail_extractor_factory() -> ThumbnailFeatureExtractor:
            return ThumbnailFeatureExtractor(timeout=timeout)
    else:
        def thumbnail_extractor_factory() -> ThumbnailFeatureExtractor:
            return thumbnail_extractor

    if transcript_extractor is None:
        def transcript_extractor_factory() -> TranscriptFeatureExtractor:
            return TranscriptFeatureExtractor(
                timeout=timeout,
                session=youtube_session,
            )
    else:
        def transcript_extractor_factory() -> TranscriptFeatureExtractor:
            return transcript_extractor

    for channel_config in channel_configs:
        handle = channel_config["channel_handle"]
        should_analyze_thumbnail = channel_config["thumbnail_analysis"]
        LOGGER.info("Scraping channel %s", handle)
        try:
            channel_result = scrape_channel_for_monitoring(
                youtube_client,
                repository,
                handle,
                limit=limit,
                monitor_cutoff=monitor_cutoff,
            )
        except YouTubeAPIError as exc:
            LOGGER.exception("Failed to scrape channel %s", handle)
            errors.append(f"{handle}: {exc}")
            continue

        results.append(channel_result)
        for video in channel_result.videos:
            current_rows.append(video.to_current_row(handle, run_started_at))
            snapshot_rows.append(video.to_snapshot_row(handle, run_started_at))

        existing_feature_rows = repository.get_feature_rows(
            [video.video_id for video in channel_result.videos]
        )
        feature_rows.extend(
            _parallel_feature_rows(
                channel_result.videos,
                channel_handle=handle,
                run_started_at=run_started_at,
                should_analyze_thumbnail=should_analyze_thumbnail,
                feature_workers=feature_workers,
                transcript_extractor_factory=transcript_extractor_factory,
                thumbnail_extractor_factory=thumbnail_extractor_factory,
                existing_feature_rows=existing_feature_rows,
            )
        )

    if not results:
        raise YouTubeAPIError(
            "Batch scrape failed for all channels. Errors: " + ("; ".join(errors) or "unknown")
        )

    repository.upsert_current_videos(current_rows)
    repository.insert_snapshots(snapshot_rows)
    repository.upsert_feature_rows(feature_rows)

    processed_handles = [result.channel_handle for result in results]
    snapshots = repository.get_snapshots_for_channels(
        processed_handles,
        published_after=analytics_cutoff,
    )
    performance_rows = [
        record.to_row()
        for record in build_performance_records(
            snapshots,
            calculated_at=run_started_at,
            baseline_window_days=baseline_window_days,
        )
    ]
    repository.upsert_performance_rows(performance_rows)
    repository.update_scraper_state(run_started_at)

    LOGGER.info(
        "Stored %s current rows, %s snapshots, %s feature rows and %s performance rows",
        len(current_rows),
        len(snapshot_rows),
        len(feature_rows),
        len(performance_rows),
    )
    if errors:
        LOGGER.warning("Skipped %s channels with errors", len(errors))

    return [result.to_public_dict() for result in results]


def scrape_channel_latest_videos(
    api_key: str,
    channel_handle: str,
    limit: int | None,
    published_after: datetime | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    youtube_client = YouTubeClient(api_key, timeout=timeout)
    result = scrape_channel_result(
        youtube_client,
        channel_handle,
        limit=limit,
        published_after=published_after,
    )
    return result.to_public_dict()


def scrape_and_store_channels(
    api_key: str,
    supabase_url: str,
    supabase_key: str,
    limit: int | None,
    timeout: int = DEFAULT_TIMEOUT,
    monitor_days: int = DEFAULT_MONITOR_DAYS,
    baseline_window_days: int = DEFAULT_BASELINE_WINDOW_DAYS,
    feature_workers: int | None = DEFAULT_FEATURE_WORKERS,
) -> list[dict]:
    youtube_client = YouTubeClient(api_key, timeout=timeout)
    repository = SupabaseRepository(
        SupabaseClient(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            timeout=timeout,
        )
    )
    return run_batch_scrape(
        youtube_client,
        repository,
        limit=limit,
        monitor_days=monitor_days,
        baseline_window_days=baseline_window_days,
        feature_workers=feature_workers,
    )
