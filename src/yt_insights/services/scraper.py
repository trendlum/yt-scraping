from __future__ import annotations

import logging
from datetime import datetime, timedelta

from ..analytics.performance import build_performance_records
from ..analytics.transcript_features import TranscriptFeatureExtractor, enrich_transcript_features
from ..analytics.thumbnail_features import ThumbnailFeatureExtractor, enrich_thumbnail_features
from ..analytics.title_features import extract_title_features
from ..clients.supabase import SupabaseClient
from ..clients.youtube import YouTubeClient
from ..constants import DEFAULT_BASELINE_WINDOW_DAYS, DEFAULT_MONITOR_DAYS, DEFAULT_TIMEOUT
from ..exceptions import YouTubeAPIError
from ..models import ChannelScrapeResult, utc_now
from ..repositories.supabase import SupabaseRepository


LOGGER = logging.getLogger(__name__)


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


def run_batch_scrape(
    youtube_client: YouTubeClient,
    repository: SupabaseRepository,
    *,
    limit: int | None,
    monitor_days: int = DEFAULT_MONITOR_DAYS,
    baseline_window_days: int = DEFAULT_BASELINE_WINDOW_DAYS,
    executed_at: datetime | None = None,
    transcript_extractor: TranscriptFeatureExtractor | None = None,
    thumbnail_extractor: ThumbnailFeatureExtractor | None = None,
) -> list[dict]:
    run_started_at = executed_at or utc_now()
    monitor_cutoff = run_started_at - timedelta(days=monitor_days)
    analytics_cutoff = run_started_at - timedelta(days=baseline_window_days)
    channel_handles = repository.get_active_channel_handles()

    results: list[ChannelScrapeResult] = []
    current_rows: list[dict] = []
    snapshot_rows: list[dict] = []
    feature_rows: list[dict] = []
    errors: list[str] = []
    thumbnail_extractor = thumbnail_extractor or ThumbnailFeatureExtractor(
        timeout=getattr(youtube_client, "timeout", DEFAULT_TIMEOUT)
    )
    transcript_extractor = transcript_extractor or TranscriptFeatureExtractor(
        timeout=getattr(youtube_client, "timeout", DEFAULT_TIMEOUT),
        session=getattr(youtube_client, "session", None),
    )

    for handle in channel_handles:
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
            feature_record = extract_title_features(
                video,
                handle,
                extracted_at=run_started_at,
            )
            feature_record = enrich_transcript_features(feature_record, transcript_extractor)
            feature_record = enrich_thumbnail_features(feature_record, thumbnail_extractor)
            feature_rows.append(feature_record.to_row())

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
    )
