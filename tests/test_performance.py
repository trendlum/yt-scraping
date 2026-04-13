from __future__ import annotations

from datetime import datetime, timedelta, timezone

from yt_insights.analytics.performance import build_performance_records
from yt_insights.models import VideoMetricSnapshot


def _snapshot(
    video_id: str,
    hours_after_publish: int,
    views: int,
    *,
    channel_handle: str = "@channel",
) -> VideoMetricSnapshot:
    published_at = datetime(2026, 4, 1, tzinfo=timezone.utc)
    return VideoMetricSnapshot(
        video_id=video_id,
        channel_handle=channel_handle,
        snapshot_at=published_at + timedelta(hours=hours_after_publish),
        published_at=published_at,
        view_count=views,
        like_count=None,
        comment_count=None,
    )


def test_build_performance_records_computes_anchor_views_and_ratios() -> None:
    snapshots = [
        _snapshot("v1", 24, 100),
        _snapshot("v1", 72, 240),
        _snapshot("v1", 168, 600),
        _snapshot("v1", 360, 1000),
        _snapshot("v2", 24, 50),
        _snapshot("v2", 72, 120),
        _snapshot("v2", 168, 200),
        _snapshot("v2", 360, 300),
    ]

    records = build_performance_records(
        snapshots,
        calculated_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
        baseline_window_days=30,
    )

    assert len(records) == 2
    record_by_id = {record.video_id: record for record in records}
    leader = record_by_id["v1"]

    assert leader.views_d1 == 100
    assert leader.views_d7 == 600
    assert leader.baseline_sample_size_d1 == 2
    assert leader.ratio_d1 == round(100 / 75, 4)
    assert leader.packaging_score == leader.ratio_d1
    assert leader.performance_label in {"solid", "normal", "explosive"}
