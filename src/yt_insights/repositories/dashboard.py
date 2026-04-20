from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable

from ..clients.supabase import SupabaseClient


def _in_filter(values: Iterable[str]) -> str:
    quoted = ",".join(f'"{value}"' for value in values)
    return f"in.({quoted})"


def _ilike(value: str) -> str:
    return f"ilike.*{value}*"


def _contains(value: str, needle: str) -> bool:
    return needle.lower() in str(value or "").lower()


@dataclass(frozen=True)
class DashboardFilters:
    analysis_window: int | None = None
    niche: str | None = None
    channel_handle: str | None = None
    topic_cluster: str | None = None
    niche_growth_status: str | None = None
    channel_growth_status: str | None = None
    topic_type: str | None = None
    performance_label: str | None = None
    video_type: str | None = None
    sample_confidence: str | None = None


class DashboardRepository:
    def __init__(self, client: SupabaseClient) -> None:
        self.client = client

    @staticmethod
    def _distinct_strings(rows: list[dict[str, Any]], key: str) -> list[str]:
        seen: set[str] = set()
        values: list[str] = []
        for row in rows:
            value = row.get(key)
            if not value:
                continue
            text = str(value)
            if text in seen:
                continue
            seen.add(text)
            values.append(text)
        return values

    def _query(
        self,
        table: str,
        *,
        select: str = "*",
        filters: DashboardFilters | None = None,
        extra_params: list[tuple[str, Any]] | None = None,
        order: str | None = None,
        limit: int | None = None,
        include_window_days: bool = True,
    ) -> list[dict[str, Any]]:
        params: list[tuple[str, Any]] = [("select", select)]
        if filters is not None:
            if include_window_days and filters.analysis_window is not None:
                params.append(("window_days", f"eq.{filters.analysis_window}"))

        if extra_params:
            params.extend(extra_params)
        if order:
            params.append(("order", order))
        if limit is not None:
            params.append(("limit", limit))

        payload = self.client.request("GET", table, params=params)
        return [row for row in payload or [] if isinstance(row, dict)]

    @staticmethod
    def _dedupe_latest(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        seen: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for row in rows:
            value = row.get(key)
            if not value:
                continue
            value = str(value)
            if value in seen:
                continue
            seen.add(value)
            deduped.append(row)
        return deduped

    @staticmethod
    def _top_topics(rows: Iterable[dict[str, Any]], *, limit: int = 5) -> list[dict[str, Any]]:
        counter: Counter[str] = Counter()
        for row in rows:
            clusters = row.get("topic_clusters") or []
            if isinstance(clusters, list):
                counter.update(str(cluster) for cluster in clusters if cluster)
        return [{"label": label, "count": count} for label, count in counter.most_common(limit)]

    @staticmethod
    def _top_channels(rows: Iterable[dict[str, Any]], *, limit: int = 5) -> list[dict[str, Any]]:
        counter: Counter[str] = Counter()
        for row in rows:
            channel = row.get("channel_handle")
            if channel:
                counter.update([str(channel)])
        return [{"channel_handle": channel, "count": count} for channel, count in counter.most_common(limit)]

    def get_meta(self) -> dict[str, Any]:
        niche_status_rows = self._query(
            "vw_niche_rankings",
            select="niche_growth_status_early,niche_growth_status_confirmed",
            limit=500,
            include_window_days=False,
        )
        niche_status_options = self._distinct_strings(niche_status_rows, "niche_growth_status_early")
        niche_status_options.extend(
            value
            for value in self._distinct_strings(niche_status_rows, "niche_growth_status_confirmed")
            if value not in niche_status_options
        )

        channel_status_options = self._distinct_strings(
            self._query(
                "vw_channel_rankings",
                select="channel_growth_status",
                limit=500,
                include_window_days=False,
            ),
            "channel_growth_status",
        )
        topic_type_options = self._distinct_strings(
            self._query(
                "vw_topic_rankings",
                select="topic_type",
                limit=500,
                include_window_days=False,
            ),
            "topic_type",
        )
        performance_label_options = self._distinct_strings(
            self._query(
                "vw_video_detail",
                select="performance_label",
                limit=1000,
                include_window_days=False,
            ),
            "performance_label",
        )

        return {
            "default_window_days": 30,
            "available_window_days": [30, 60, 90],
            "niche_growth_status_options": niche_status_options,
            "channel_growth_status_options": channel_status_options,
            "topic_type_options": topic_type_options,
            "performance_label_options": performance_label_options,
        }

    def list_niches(self, filters: DashboardFilters) -> list[dict[str, Any]]:
        extra_params: list[tuple[str, Any]] = []
        if filters.sample_confidence:
            extra_params.append(("sample_confidence_level", f"eq.{filters.sample_confidence}"))

        rows = self._query(
            "vw_niche_rankings",
            filters=filters,
            extra_params=extra_params,
            select=(
                "niche,analysis_date,window_days,video_count_total,video_count_last_7d,"
                "distinct_channels_count,median_ratio_d1,median_ratio_d3,median_ratio_d7,median_ratio_d15,"
                "niche_early_signal_score,niche_early_acceleration_score,niche_growth_forecast_score,"
                "niche_growth_status_early,niche_growth_score_confirmed,niche_consistency_score_confirmed,"
                "niche_acceleration_score_confirmed,niche_outlier_dependency_score,niche_growth_status_confirmed,"
                "pct_explosive,pct_solid,pct_dead,low_sample_flag,sample_confidence_level,notes"
            ),
            order="niche_growth_score_confirmed.desc.nullslast",
            limit=250,
        )
        if filters.niche:
            rows = [row for row in rows if _contains(row.get("niche"), filters.niche)]
        if filters.niche_growth_status:
            rows = [
                row
                for row in rows
                if row.get("niche_growth_status_early") == filters.niche_growth_status
                or row.get("niche_growth_status_confirmed") == filters.niche_growth_status
            ]
        return rows

    def get_niche_detail(self, filters: DashboardFilters, niche: str) -> dict[str, Any] | None:
        rows = self._query(
            "vw_niche_detail",
            filters=DashboardFilters(
                analysis_window=filters.analysis_window,
                niche=niche,
            ),
            extra_params=[("niche", f"eq.{niche}")],
            limit=1,
        )
        if not rows:
            return None

        related_channels = self._query(
            "vw_channel_rankings",
            filters=DashboardFilters(
                analysis_window=filters.analysis_window,
                niche=niche,
            ),
            extra_params=[("channel_niche", f"eq.{niche}")],
            select=(
                "channel_handle,channel_niche,analysis_date,window_days,channel_growth_status,"
                "channel_growth_score,delta_overall_score,channel_packaging_improvement_score,"
                "channel_sustainability_improvement_score,channel_algorithmic_shift_score,"
                "channel_volatility_score,sample_confidence_level,video_count_recent,video_count_previous"
            ),
            order="channel_growth_score.desc.nullslast",
            limit=5,
        )
        niche_channel_handles = [str(row.get("channel_handle")) for row in related_channels if row.get("channel_handle")]
        video_rows = self._query(
            "vw_video_detail",
            extra_params=[("channel_handle", _in_filter(niche_channel_handles))] if niche_channel_handles else [],
            select="video_id,channel_handle,channel_niche,title,overall_score,topic_clusters",
            order="overall_score.desc.nullslast",
            limit=200,
            include_window_days=False,
        )
        return {
            "row": rows[0],
            "recent_channels": self._dedupe_latest(related_channels, "channel_handle")[:5],
            "top_topics": self._top_topics(video_rows, limit=5),
        }

    def list_channels(self, filters: DashboardFilters) -> list[dict[str, Any]]:
        extra_params: list[tuple[str, Any]] = []
        if filters.channel_growth_status:
            extra_params.append(("channel_growth_status", f"eq.{filters.channel_growth_status}"))
        if filters.sample_confidence:
            extra_params.append(("sample_confidence_level", f"eq.{filters.sample_confidence}"))

        rows = self._query(
            "vw_channel_rankings",
            filters=filters,
            extra_params=extra_params,
            select=(
                "channel_handle,analysis_date,window_days,channel_niche,video_count_recent,"
                "video_count_previous,median_packaging_score_recent,median_packaging_score_previous,"
                "delta_packaging_score,median_momentum_score_recent,median_momentum_score_previous,"
                "delta_momentum_score,median_overall_score_recent,median_overall_score_previous,"
                "delta_overall_score,channel_packaging_improvement_score,channel_sustainability_improvement_score,"
                "channel_algorithmic_shift_score,channel_volatility_score,channel_growth_score,channel_growth_status,"
                "sample_confidence_level,low_sample_flag"
            ),
            order="channel_growth_score.desc.nullslast",
            limit=250,
        )
        if filters.channel_handle:
            rows = [row for row in rows if _contains(row.get("channel_handle"), filters.channel_handle)]
        if filters.niche:
            rows = [row for row in rows if _contains(row.get("channel_niche"), filters.niche)]
        return rows

    def get_channel_detail(self, filters: DashboardFilters, channel_handle: str) -> dict[str, Any] | None:
        rows = self._query(
            "vw_channel_detail",
            filters=DashboardFilters(
                analysis_window=filters.analysis_window,
                channel_handle=channel_handle,
            ),
            extra_params=[("channel_handle", f"eq.{channel_handle}")],
            limit=1,
        )
        if not rows:
            return None

        related_videos = self._query(
            "vw_video_detail",
            extra_params=[("channel_handle", f"eq.{channel_handle}")],
            select="video_id,title,channel_handle,channel_niche,overall_score,topic_clusters,published_at,performance_label",
            order="overall_score.desc.nullslast",
            limit=50,
            include_window_days=False,
        )
        return {
            "row": rows[0],
            "top_topics": self._top_topics(related_videos, limit=5),
            "recent_videos": related_videos[:5],
        }

    def list_topics(self, filters: DashboardFilters) -> list[dict[str, Any]]:
        extra_params: list[tuple[str, Any]] = []
        if filters.topic_type:
            extra_params.append(("topic_type", f"eq.{filters.topic_type}"))
        if filters.sample_confidence:
            extra_params.append(("sample_confidence_level", f"eq.{filters.sample_confidence}"))

        rows = self._query(
            "vw_topic_rankings",
            filters=filters,
            extra_params=extra_params,
            select=(
                "topic_cluster,analysis_date,window_days,video_count,distinct_channels_count,"
                "pct_videos_with_topic,topic_start_strength_score,topic_sustained_traction_score,"
                "topic_fragility_score,topic_replicability_score,topic_type,sample_confidence_level,"
                "pct_dead,pct_underperforming,top1_ratio_d7_vs_median,top3_ratio_d7_avg_vs_median"
            ),
            order="topic_replicability_score.desc.nullslast",
            limit=250,
        )
        if filters.topic_cluster:
            rows = [row for row in rows if _contains(row.get("topic_cluster"), filters.topic_cluster)]
        return rows

    def get_topic_detail(self, filters: DashboardFilters, topic_cluster: str) -> dict[str, Any] | None:
        rows = self._query(
            "vw_topic_detail",
            filters=DashboardFilters(
                analysis_window=filters.analysis_window,
                topic_cluster=topic_cluster,
            ),
            extra_params=[("topic_cluster", f"eq.{topic_cluster}")],
            limit=1,
        )
        if not rows:
            return None

        topic_links = self._query(
            "yt_video_topics",
            select="video_id,topic_cluster",
            extra_params=[("topic_cluster", f"eq.{topic_cluster}")],
            limit=500,
            include_window_days=False,
        )
        video_ids = [str(row.get("video_id")) for row in topic_links if row.get("video_id")]
        videos: list[dict[str, Any]] = []
        if video_ids:
            videos = self._query(
                "vw_video_detail",
                extra_params=[("video_id", _in_filter(video_ids))],
                select="video_id,title,channel_handle,channel_niche,overall_score,topic_clusters,published_at,performance_label",
                order="overall_score.desc.nullslast",
                limit=100,
                include_window_days=False,
            )

        return {
            "row": rows[0],
            "top_channels": self._top_channels(videos, limit=5),
            "recent_examples": videos[:5],
        }

    def list_videos(self, filters: DashboardFilters, *, video_type: str) -> list[dict[str, Any]]:
        extra_params: list[tuple[str, Any]] = []
        if filters.performance_label:
            extra_params.append(("performance_label", f"eq.{filters.performance_label}"))
        confidence_field = "underpackaged_confidence" if video_type == "underpackaged" else "overpackaged_confidence"
        if filters.sample_confidence:
            extra_params.append((confidence_field, f"eq.{filters.sample_confidence}"))

        table = (
            "vw_underpackaged_video_opportunities"
            if video_type == "underpackaged"
            else "vw_overpackaged_video_opportunities"
        )
        score_field = "underpackaged_score" if video_type == "underpackaged" else "overpackaged_score"
        if video_type == "underpackaged":
            select = (
                "video_id,analysis_date,channel_handle,channel_niche,title,video_url,thumbnail_url,published_at,"
                "age_days,packaging_score,momentum_score,ratio_d1,ratio_d3,ratio_d7,ratio_d15,"
                "growth_d1_3,growth_d3_7,growth_d7_15,acceleration_early,acceleration_late,"
                "consistency_periods_above_baseline,performance_label,underpackaged_type,"
                "underpackaged_score,underpackaged_confidence"
            )
        else:
            select = (
                "video_id,analysis_date,channel_handle,channel_niche,title,video_url,thumbnail_url,published_at,"
                "age_days,packaging_score,momentum_score,ratio_d1,ratio_d3,ratio_d7,ratio_d15,"
                "growth_d1_3,growth_d3_7,growth_d7_15,acceleration_early,acceleration_late,"
                "consistency_periods_above_baseline,performance_label,overpackaged_type,"
                "overpackaged_score,overpackaged_confidence"
            )

        rows = self._query(
            table,
            filters=filters,
            extra_params=extra_params,
            select=select,
            order=f"{score_field}.desc.nullslast",
            limit=250,
            include_window_days=False,
        )
        if filters.channel_handle:
            rows = [row for row in rows if _contains(row.get("channel_handle"), filters.channel_handle)]
        if filters.niche:
            rows = [row for row in rows if _contains(row.get("channel_niche"), filters.niche)]
        return rows

    def get_video_detail(self, filters: DashboardFilters, video_id: str) -> dict[str, Any] | None:
        rows = self._query(
            "vw_video_detail",
            extra_params=[("video_id", f"eq.{video_id}")],
            limit=1,
            include_window_days=False,
        )
        if not rows:
            return None
        return {"row": rows[0]}

    def get_overview(self, filters: DashboardFilters) -> dict[str, Any]:
        niches = self.list_niches(filters)
        channels = self.list_channels(filters)
        topics = self.list_topics(filters)
        underpackaged = self.list_videos(filters, video_type="underpackaged")
        overpackaged = self.list_videos(filters, video_type="overpackaged")
        tracked_rows_count = len(niches) + len(channels) + len(topics) + len(underpackaged) + len(overpackaged)
        high_confidence_count = sum(
            1
            for row in niches + channels + topics + underpackaged + overpackaged
            if row.get("sample_confidence_level") == "high"
            or row.get("underpackaged_confidence") == "high"
            or row.get("overpackaged_confidence") == "high"
        )
        high_confidence_share = round((high_confidence_count / tracked_rows_count) * 100) if tracked_rows_count else 0

        return {
            "summary": {
                "analysis_date": None,
                "analysis_window": filters.analysis_window,
                "niches_count": len(niches),
                "channels_count": len(channels),
                "topics_count": len(topics),
                "underpackaged_count": len(underpackaged),
                "overpackaged_count": len(overpackaged),
                "tracked_rows_count": tracked_rows_count,
                "high_confidence_count": high_confidence_count,
                "high_confidence_share": high_confidence_share,
            },
            "niches": niches[:5],
            "channels": channels[:5],
            "topics": topics[:5],
            "underpackaged": underpackaged[:5],
            "overpackaged": overpackaged[:5],
        }
