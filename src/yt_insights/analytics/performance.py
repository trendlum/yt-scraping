from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from statistics import median

from ..constants import BASELINE_ANCHOR_DAYS, PERFORMANCE_MODEL_VERSION
from ..models import VideoMetricSnapshot, VideoPerformanceRecord


_ANCHOR_TOLERANCE_HOURS = {
    1: 18,
    3: 36,
    7: 84,
    15: 120,
}


def _round(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def _safe_ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _flow(end_value: int | None, start_value: int | None, periods: int) -> float | None:
    if end_value is None or periods <= 0:
        return None
    if start_value is None:
        return float(end_value) / periods
    if end_value < start_value:
        return None
    return float(end_value - start_value) / periods


def _weighted_average(values: list[tuple[float | None, float]]) -> float | None:
    numerator = 0.0
    denominator = 0.0
    for value, weight in values:
        if value is None:
            continue
        numerator += value * weight
        denominator += weight
    if denominator == 0:
        return None
    return numerator / denominator


def _extract_anchor_views(snapshots: list[VideoMetricSnapshot]) -> dict[int, int | None]:
    anchors: dict[int, int | None] = {}
    for target_day in BASELINE_ANCHOR_DAYS:
        target_hours = target_day * 24
        tolerance = _ANCHOR_TOLERANCE_HOURS[target_day]
        candidates = [
            snapshot
            for snapshot in snapshots
            if snapshot.age_hours is not None
            and abs(snapshot.age_hours - target_hours) <= tolerance
            and snapshot.view_count is not None
        ]
        if not candidates:
            anchors[target_day] = None
            continue
        best = min(candidates, key=lambda snapshot: abs(snapshot.age_hours - target_hours))
        anchors[target_day] = best.view_count
    return anchors


def _classify_performance(
    *,
    age_days: float | None,
    ratio_d1: float | None,
    ratio_d3: float | None,
    ratio_d7: float | None,
    ratio_d15: float | None,
    growth_d3_7: float | None,
    consistency: int,
) -> str:
    if ratio_d1 is not None and ratio_d3 is not None and ratio_d1 >= 1.8 and ratio_d3 >= 1.5:
        return "explosive"
    if ratio_d1 is not None and ratio_d7 is not None and ratio_d1 <= 1.1 and ratio_d7 >= 1.8:
        return "algorithmic"
    if ratio_d1 is not None and ratio_d15 is not None and ratio_d1 < 1.0 and ratio_d15 >= 1.4:
        return "slow_burner"
    if age_days is not None and age_days >= 3 and ratio_d3 is not None and ratio_d3 < 0.5:
        return "dead"
    if consistency >= 3:
        return "solid"
    if age_days is not None and age_days >= 7 and ratio_d7 is not None and ratio_d7 < 0.8:
        return "underperforming"
    if growth_d3_7 is not None and growth_d3_7 > 1.0 and ratio_d7 is not None and ratio_d7 >= 1.2:
        return "algorithmic"
    return "normal"


def build_performance_records(
    snapshots: list[VideoMetricSnapshot],
    *,
    calculated_at: datetime,
    baseline_window_days: int,
) -> list[VideoPerformanceRecord]:
    grouped_by_video: dict[str, list[VideoMetricSnapshot]] = defaultdict(list)
    for snapshot in snapshots:
        grouped_by_video[snapshot.video_id].append(snapshot)

    if not grouped_by_video:
        return []

    candidate_cutoff = calculated_at - timedelta(days=baseline_window_days)
    candidate_videos: dict[str, list[VideoMetricSnapshot]] = {}
    video_anchor_views: dict[str, dict[int, int | None]] = {}

    for video_id, items in grouped_by_video.items():
        ordered_items = sorted(items, key=lambda item: item.snapshot_at)
        latest_snapshot = ordered_items[-1]
        if latest_snapshot.published_at is None or latest_snapshot.published_at < candidate_cutoff:
            continue
        candidate_videos[video_id] = ordered_items
        video_anchor_views[video_id] = _extract_anchor_views(ordered_items)

    channel_anchor_values: dict[str, dict[int, list[int]]] = defaultdict(
        lambda: {anchor_day: [] for anchor_day in BASELINE_ANCHOR_DAYS}
    )
    for video_id, ordered_items in candidate_videos.items():
        channel_handle = ordered_items[-1].channel_handle
        anchors = video_anchor_views[video_id]
        for anchor_day, view_count in anchors.items():
            if view_count is not None:
                channel_anchor_values[channel_handle][anchor_day].append(view_count)

    channel_baselines: dict[str, dict[int, float | None]] = defaultdict(dict)
    channel_sample_sizes: dict[str, dict[int, int]] = defaultdict(dict)
    for channel_handle, anchor_values in channel_anchor_values.items():
        for anchor_day, values in anchor_values.items():
            channel_sample_sizes[channel_handle][anchor_day] = len(values)
            channel_baselines[channel_handle][anchor_day] = float(median(values)) if values else None

    performance_records: list[VideoPerformanceRecord] = []
    for video_id, ordered_items in candidate_videos.items():
        latest_snapshot = ordered_items[-1]
        anchors = video_anchor_views[video_id]
        channel_handle = latest_snapshot.channel_handle
        baselines = channel_baselines[channel_handle]
        sample_sizes = channel_sample_sizes[channel_handle]

        views_d1 = anchors[1]
        views_d3 = anchors[3]
        views_d7 = anchors[7]
        views_d15 = anchors[15]

        ratio_d1 = _round(_safe_ratio(views_d1, baselines.get(1)))
        ratio_d3 = _round(_safe_ratio(views_d3, baselines.get(3)))
        ratio_d7 = _round(_safe_ratio(views_d7, baselines.get(7)))
        ratio_d15 = _round(_safe_ratio(views_d15, baselines.get(15)))

        flow_d1 = _round(float(views_d1) if views_d1 is not None else None, 2)
        flow_d1_3 = _round(_flow(views_d3, views_d1, 2), 2)
        flow_d3_7 = _round(_flow(views_d7, views_d3, 4), 2)
        flow_d7_15 = _round(_flow(views_d15, views_d7, 8), 2)

        growth_d1_3 = _round(_safe_ratio(flow_d1_3, flow_d1))
        growth_d3_7 = _round(_safe_ratio(flow_d3_7, flow_d1_3))
        growth_d7_15 = _round(_safe_ratio(flow_d7_15, flow_d3_7))
        acceleration_early = _round(
            None if growth_d1_3 is None or growth_d3_7 is None else growth_d3_7 - growth_d1_3
        )
        acceleration_late = _round(
            None if growth_d3_7 is None or growth_d7_15 is None else growth_d7_15 - growth_d3_7
        )

        ratios = [ratio for ratio in (ratio_d1, ratio_d3, ratio_d7, ratio_d15) if ratio is not None]
        consistency = sum(1 for ratio in ratios if ratio >= 1.0)
        packaging_score = ratio_d1
        momentum_score = _round(
            _weighted_average(
                [
                    (ratio_d3, 0.35),
                    (ratio_d7, 0.4),
                    (ratio_d15, 0.25),
                ]
            )
        )
        overall_score = _weighted_average(
            [
                (packaging_score, 0.35),
                (ratio_d3, 0.2),
                (ratio_d7, 0.25),
                (ratio_d15, 0.2),
            ]
        )
        if overall_score is not None:
            overall_score += consistency * 0.1
            if acceleration_late is not None and acceleration_late > 0 and ratio_d7 is not None and ratio_d7 >= 1:
                overall_score += 0.1
        overall_score = _round(overall_score)

        performance_records.append(
            VideoPerformanceRecord(
                video_id=video_id,
                channel_handle=channel_handle,
                calculated_at=calculated_at,
                current_snapshot_at=latest_snapshot.snapshot_at,
                published_at=latest_snapshot.published_at,
                baseline_window_days=baseline_window_days,
                performance_model_version=PERFORMANCE_MODEL_VERSION,
                age_days=_round(
                    None if latest_snapshot.age_hours is None else latest_snapshot.age_hours / 24,
                    2,
                ),
                current_view_count=latest_snapshot.view_count,
                views_d1=views_d1,
                views_d3=views_d3,
                views_d7=views_d7,
                views_d15=views_d15,
                baseline_median_d1=_round(baselines.get(1), 2),
                baseline_median_d3=_round(baselines.get(3), 2),
                baseline_median_d7=_round(baselines.get(7), 2),
                baseline_median_d15=_round(baselines.get(15), 2),
                baseline_sample_size_d1=sample_sizes.get(1, 0),
                baseline_sample_size_d3=sample_sizes.get(3, 0),
                baseline_sample_size_d7=sample_sizes.get(7, 0),
                baseline_sample_size_d15=sample_sizes.get(15, 0),
                ratio_d1=ratio_d1,
                ratio_d3=ratio_d3,
                ratio_d7=ratio_d7,
                ratio_d15=ratio_d15,
                flow_d1=flow_d1,
                flow_d1_3=flow_d1_3,
                flow_d3_7=flow_d3_7,
                flow_d7_15=flow_d7_15,
                growth_d1_3=growth_d1_3,
                growth_d3_7=growth_d3_7,
                growth_d7_15=growth_d7_15,
                acceleration_early=acceleration_early,
                acceleration_late=acceleration_late,
                consistency_periods_above_baseline=consistency,
                packaging_score=packaging_score,
                momentum_score=momentum_score,
                overall_score=overall_score,
                performance_label=_classify_performance(
                    age_days=None if latest_snapshot.age_hours is None else latest_snapshot.age_hours / 24,
                    ratio_d1=ratio_d1,
                    ratio_d3=ratio_d3,
                    ratio_d7=ratio_d7,
                    ratio_d15=ratio_d15,
                    growth_d3_7=growth_d3_7,
                    consistency=consistency,
                ),
            )
        )

    return performance_records
