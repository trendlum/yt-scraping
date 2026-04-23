from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .constants import THUMBNAIL_PRIORITY


_DURATION_PATTERN = re.compile(
    r"P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?"
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat()


def to_int_or_none(value: str | int | None) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def pick_thumbnail_url(thumbnails: dict[str, Any] | None) -> str | None:
    if not thumbnails:
        return None

    for key in THUMBNAIL_PRIORITY:
        candidate = thumbnails.get(key)
        if isinstance(candidate, dict) and candidate.get("url"):
            return str(candidate["url"])

    return None


def parse_duration_to_hms(duration: str | None) -> str | None:
    if not duration:
        return None

    match = _DURATION_PATTERN.fullmatch(duration)
    if not match:
        return None

    days = int(match.group("days") or 0)
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    total_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds

    total_hours, remainder = divmod(total_seconds, 3600)
    total_minutes, remaining_seconds = divmod(remainder, 60)
    return f"{total_hours:02d}:{total_minutes:02d}:{remaining_seconds:02d}"


def compute_video_age_hours(
    published_at: datetime | None,
    observed_at: datetime,
) -> float | None:
    if published_at is None:
        return None
    delta = observed_at - published_at
    return round(delta.total_seconds() / 3600, 2)


def sha1_text(value: str | None) -> str:
    return hashlib.sha1((value or "").encode("utf-8")).hexdigest()


@dataclass(slots=True)
class VideoRecord:
    video_id: str
    title: str | None
    channel_title: str | None
    published_at: datetime | None
    thumbnail_url: str | None
    view_count: int | None
    like_count: int | None
    comment_count: int | None
    duration: str | None
    duration_iso8601: str | None
    video_url: str

    @classmethod
    def from_api_item(cls, item: dict[str, Any]) -> "VideoRecord | None":
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})
        content_details = item.get("contentDetails", {})
        video_id = item.get("id")
        if not video_id:
            return None

        duration_iso = content_details.get("duration")
        return cls(
            video_id=str(video_id),
            title=snippet.get("title"),
            channel_title=snippet.get("channelTitle"),
            published_at=parse_datetime(snippet.get("publishedAt")),
            thumbnail_url=pick_thumbnail_url(snippet.get("thumbnails")),
            view_count=to_int_or_none(statistics.get("viewCount")),
            like_count=to_int_or_none(statistics.get("likeCount")),
            comment_count=to_int_or_none(statistics.get("commentCount")),
            duration=parse_duration_to_hms(duration_iso),
            duration_iso8601=duration_iso,
            video_url=f"https://www.youtube.com/watch?v={video_id}",
        )

    @classmethod
    def from_public_dict(cls, data: dict[str, Any]) -> "VideoRecord":
        return cls(
            video_id=str(data["video_id"]),
            title=data.get("title"),
            channel_title=data.get("channel_title"),
            published_at=parse_datetime(data.get("published_at")),
            thumbnail_url=data.get("thumbnail_url"),
            view_count=to_int_or_none(data.get("view_count")),
            like_count=to_int_or_none(data.get("like_count")),
            comment_count=to_int_or_none(data.get("comment_count")),
            duration=data.get("duration"),
            duration_iso8601=data.get("duration_iso8601"),
            video_url=data.get("video_url") or f"https://www.youtube.com/watch?v={data['video_id']}",
        )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "video_id": self.video_id,
            "title": self.title,
            "channel_title": self.channel_title,
            "published_at": serialize_datetime(self.published_at),
            "thumbnail_url": self.thumbnail_url,
            "view_count": self.view_count,
            "like_count": self.like_count,
            "comment_count": self.comment_count,
            "duration": self.duration,
            "duration_iso8601": self.duration_iso8601,
            "video_url": self.video_url,
        }

    def to_current_row(self, channel_handle: str, fetched_at: datetime) -> dict[str, Any]:
        return {
            "video_id": self.video_id,
            "channel_handle": channel_handle,
            "title": self.title,
            "published_at": serialize_datetime(self.published_at),
            "thumbnail_url": self.thumbnail_url,
            "view_count": self.view_count,
            "like_count": self.like_count,
            "comment_count": self.comment_count,
            "duration": self.duration,
            "duration_iso8601": self.duration_iso8601,
            "video_url": self.video_url,
            "fetched_at": serialize_datetime(fetched_at),
            "updated_at": serialize_datetime(fetched_at),
        }

    def to_snapshot_row(self, channel_handle: str, snapshot_at: datetime) -> dict[str, Any]:
        return {
            "video_id": self.video_id,
            "channel_handle": channel_handle,
            "snapshot_at": serialize_datetime(snapshot_at),
            "published_at": serialize_datetime(self.published_at),
            "video_age_hours": compute_video_age_hours(self.published_at, snapshot_at),
            "title": self.title,
            "thumbnail_url": self.thumbnail_url,
            "view_count": self.view_count,
            "like_count": self.like_count,
            "comment_count": self.comment_count,
        }


@dataclass(slots=True)
class ChannelScrapeResult:
    channel_handle: str
    channel_id: str | None
    channel_name: str | None
    uploads_playlist_id: str
    videos: list[VideoRecord]

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "channel_handle": self.channel_handle,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "uploads_playlist_id": self.uploads_playlist_id,
            "videos": [video.to_public_dict() for video in self.videos],
        }


@dataclass(slots=True)
class VideoMetricSnapshot:
    video_id: str
    channel_handle: str
    snapshot_at: datetime
    published_at: datetime | None
    view_count: int | None
    like_count: int | None
    comment_count: int | None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "VideoMetricSnapshot":
        snapshot_at = parse_datetime(row.get("snapshot_at"))
        if snapshot_at is None:
            raise ValueError("snapshot_at is required in snapshot rows")
        return cls(
            video_id=str(row["video_id"]),
            channel_handle=str(row["channel_handle"]),
            snapshot_at=snapshot_at,
            published_at=parse_datetime(row.get("published_at")),
            view_count=to_int_or_none(row.get("view_count")),
            like_count=to_int_or_none(row.get("like_count")),
            comment_count=to_int_or_none(row.get("comment_count")),
        )

    @property
    def age_hours(self) -> float | None:
        return compute_video_age_hours(self.published_at, self.snapshot_at)


@dataclass(slots=True)
class VideoPerformanceRecord:
    video_id: str
    channel_handle: str
    calculated_at: datetime
    current_snapshot_at: datetime
    published_at: datetime | None
    baseline_window_days: int
    performance_model_version: str
    age_days: float | None
    current_view_count: int | None
    views_d1: int | None
    views_d3: int | None
    views_d7: int | None
    views_d15: int | None
    baseline_median_d1: float | None
    baseline_median_d3: float | None
    baseline_median_d7: float | None
    baseline_median_d15: float | None
    baseline_sample_size_d1: int
    baseline_sample_size_d3: int
    baseline_sample_size_d7: int
    baseline_sample_size_d15: int
    ratio_d1: float | None
    ratio_d3: float | None
    ratio_d7: float | None
    ratio_d15: float | None
    flow_d1: float | None
    flow_d1_3: float | None
    flow_d3_7: float | None
    flow_d7_15: float | None
    growth_d1_3: float | None
    growth_d3_7: float | None
    growth_d7_15: float | None
    acceleration_early: float | None
    acceleration_late: float | None
    consistency_periods_above_baseline: int
    packaging_score: float | None
    momentum_score: float | None
    overall_score: float | None
    performance_label: str

    def to_row(self) -> dict[str, Any]:
        return {
            "video_id": self.video_id,
            "channel_handle": self.channel_handle,
            "calculated_at": serialize_datetime(self.calculated_at),
            "current_snapshot_at": serialize_datetime(self.current_snapshot_at),
            "published_at": serialize_datetime(self.published_at),
            "baseline_window_days": self.baseline_window_days,
            "performance_model_version": self.performance_model_version,
            "age_days": self.age_days,
            "current_view_count": self.current_view_count,
            "views_d1": self.views_d1,
            "views_d3": self.views_d3,
            "views_d7": self.views_d7,
            "views_d15": self.views_d15,
            "baseline_median_d1": self.baseline_median_d1,
            "baseline_median_d3": self.baseline_median_d3,
            "baseline_median_d7": self.baseline_median_d7,
            "baseline_median_d15": self.baseline_median_d15,
            "baseline_sample_size_d1": self.baseline_sample_size_d1,
            "baseline_sample_size_d3": self.baseline_sample_size_d3,
            "baseline_sample_size_d7": self.baseline_sample_size_d7,
            "baseline_sample_size_d15": self.baseline_sample_size_d15,
            "ratio_d1": self.ratio_d1,
            "ratio_d3": self.ratio_d3,
            "ratio_d7": self.ratio_d7,
            "ratio_d15": self.ratio_d15,
            "flow_d1": self.flow_d1,
            "flow_d1_3": self.flow_d1_3,
            "flow_d3_7": self.flow_d3_7,
            "flow_d7_15": self.flow_d7_15,
            "growth_d1_3": self.growth_d1_3,
            "growth_d3_7": self.growth_d3_7,
            "growth_d7_15": self.growth_d7_15,
            "acceleration_early": self.acceleration_early,
            "acceleration_late": self.acceleration_late,
            "consistency_periods_above_baseline": self.consistency_periods_above_baseline,
            "packaging_score": self.packaging_score,
            "momentum_score": self.momentum_score,
            "overall_score": self.overall_score,
            "performance_label": self.performance_label,
            "updated_at": serialize_datetime(self.calculated_at),
        }


@dataclass(slots=True)
class VideoFeatureRecord:
    video_id: str
    channel_handle: str
    extracted_at: datetime
    extractor_version: str
    title_fingerprint: str
    thumbnail_fingerprint: str
    source_title: str | None
    source_thumbnail_url: str | None
    title_length_chars: int
    title_word_count: int
    uppercase_word_count: int
    digit_count: int
    has_number: bool
    has_question: bool
    has_exclamation: bool
    has_year: bool
    has_vs: bool
    has_brackets: bool
    has_colon: bool
    trigger_word_count: int
    title_pattern: str
    thumbnail_feature_status: str = "pending"
    thumbnail_ocr_status: str = "pending"
    has_face: bool | None = None
    face_count: int | None = None
    has_thumbnail_text: bool | None = None
    estimated_thumbnail_text_tokens: int | None = None
    thumbnail_text: str | None = None
    thumbnail_text_confidence: float | None = None
    dominant_emotion: str | None = None
    dominant_colors: list[str] | None = None
    composition_type: str | None = None
    contains_chart: bool | None = None
    contains_map: bool | None = None
    visual_style: str | None = None
    format_type: str | None = None
    promise_type: str | None = None
    topic_cluster_status: str = "pending"
    topic_cluster_model: str | None = None
    topic_cluster_input_fingerprint: str | None = None
    topic_cluster_extracted_at: datetime | None = None
    topic_cluster_error: str | None = None
    topic_clusters: list[str] | None = None

    def to_row(self) -> dict[str, Any]:
        return {
            "video_id": self.video_id,
            "channel_handle": self.channel_handle,
            "extracted_at": serialize_datetime(self.extracted_at),
            "extractor_version": self.extractor_version,
            "title_fingerprint": self.title_fingerprint,
            "thumbnail_fingerprint": self.thumbnail_fingerprint,
            "source_title": self.source_title,
            "source_thumbnail_url": self.source_thumbnail_url,
            "title_length_chars": self.title_length_chars,
            "title_word_count": self.title_word_count,
            "uppercase_word_count": self.uppercase_word_count,
            "digit_count": self.digit_count,
            "has_number": self.has_number,
            "has_question": self.has_question,
            "has_exclamation": self.has_exclamation,
            "has_year": self.has_year,
            "has_vs": self.has_vs,
            "has_brackets": self.has_brackets,
            "has_colon": self.has_colon,
            "trigger_word_count": self.trigger_word_count,
            "title_pattern": self.title_pattern,
            "thumbnail_feature_status": self.thumbnail_feature_status,
            "thumbnail_ocr_status": self.thumbnail_ocr_status,
            "has_face": self.has_face,
            "face_count": self.face_count,
            "has_thumbnail_text": self.has_thumbnail_text,
            "estimated_thumbnail_text_tokens": self.estimated_thumbnail_text_tokens,
            "thumbnail_text": self.thumbnail_text,
            "thumbnail_text_confidence": self.thumbnail_text_confidence,
            "dominant_emotion": self.dominant_emotion,
            "dominant_colors": self.dominant_colors,
            "composition_type": self.composition_type,
            "contains_chart": self.contains_chart,
            "contains_map": self.contains_map,
            "visual_style": self.visual_style,
            "format_type": self.format_type,
            "promise_type": self.promise_type,
            "topic_cluster_status": self.topic_cluster_status,
            "topic_cluster_model": self.topic_cluster_model,
            "topic_cluster_input_fingerprint": self.topic_cluster_input_fingerprint,
            "topic_cluster_extracted_at": serialize_datetime(self.topic_cluster_extracted_at),
            "topic_cluster_error": self.topic_cluster_error,
            "topic_clusters": self.topic_clusters,
            "updated_at": serialize_datetime(self.extracted_at),
        }
