import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router";
import { useFilters } from "../../contexts/FilterContext";
import {
  buildDashboardQuery,
  formatPercent,
  titleCase,
  TopicDetailResponse,
  TopicRow,
} from "../../lib/dashboard";
import { useDashboardQuery } from "../../lib/useDashboardQuery";
import { ConfidenceBadge } from "../ui/ConfidenceBadge";
import { ScoreBar } from "../ui/ScoreBar";
import { Sparkline } from "../ui/Sparkline";
import { StatusChip } from "../ui/StatusChip";
import { Skeleton } from "../ui/skeleton";

type SortField =
  | "topic_replicability_score"
  | "topic_sustained_traction_score"
  | "topic_fragility_score"
  | "video_count"
  | "distinct_channels_count";

function scoreValue(value: number | null | undefined) {
  return value ?? 0;
}

function scoreVariant(value: number | null | undefined): "positive" | "caution" | "critical" {
  if (value === null || value === undefined) {
    return "critical";
  }
  if (value >= 0.8) {
    return "positive";
  }
  if (value >= 0.6) {
    return "caution";
  }
  return "critical";
}

export function Topics() {
  const location = useLocation();
  const { filters, setFilters } = useFilters();
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [sortField, setSortField] = useState<SortField>("topic_replicability_score");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  const query = useMemo(() => buildDashboardQuery(filters, { limit: 250 }), [filters]);
  const { data, loading, error } = useDashboardQuery<{ items: TopicRow[] }>("/api/dashboard/topics", query);
  const items = data?.items ?? [];

  useEffect(() => {
    const initial = (location.state as { selectedId?: string } | null | undefined)?.selectedId;
    if (initial && items.some((row) => row.topic_cluster === initial)) {
      setSelectedTopic(initial);
      return;
    }
    if (!selectedTopic && items.length > 0) {
      setSelectedTopic(items[0].topic_cluster);
    }
  }, [items, location.state, selectedTopic]);

  useEffect(() => {
    if (selectedTopic && !items.some((row) => row.topic_cluster === selectedTopic)) {
      setSelectedTopic(items[0]?.topic_cluster ?? null);
    }
  }, [items, selectedTopic]);

  const selectedRow = useMemo(
    () => items.find((row) => row.topic_cluster === selectedTopic) ?? null,
    [items, selectedTopic],
  );

  const detailQuery = useMemo(
    () => buildDashboardQuery(filters, { topic_cluster: selectedRow?.topic_cluster ?? selectedTopic ?? "" }),
    [filters, selectedRow?.topic_cluster, selectedTopic],
  );
  const { data: detailData, loading: detailLoading } = useDashboardQuery<TopicDetailResponse>(
    "/api/dashboard/topic-detail",
    detailQuery,
  );

  const sortedItems = useMemo(() => {
    return [...items].sort((left, right) => {
      const leftValue = scoreValue(left[sortField]);
      const rightValue = scoreValue(right[sortField]);
      return sortDirection === "desc" ? rightValue - leftValue : leftValue - rightValue;
    });
  }, [items, sortDirection, sortField]);

  const onSort = (field: SortField) => {
    if (field === sortField) {
      setSortDirection((current) => (current === "desc" ? "asc" : "desc"));
      return;
    }
    setSortField(field);
    setSortDirection("desc");
  };

  const handleSelect = (row: TopicRow) => {
    setSelectedTopic(row.topic_cluster);
    setFilters({
      ...filters,
      topicCluster: row.topic_cluster,
      topicType: row.topic_type || filters.topicType,
    });
  };

  return (
    <div className="h-[calc(100vh-180px)] overflow-auto px-4 pt-4 pb-6">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.45fr)_minmax(0,0.9fr)]">
        <section className="rounded-xl border border-border bg-card">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div>
              <h2 className="text-sm text-foreground">Topic rankings</h2>
              <p className="text-xs text-muted-foreground">Ranked by replicability, sustained traction, and fragility.</p>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <button
                type="button"
                onClick={() => onSort("topic_replicability_score")}
                className={sortField === "topic_replicability_score" ? "text-primary" : "text-muted-foreground"}
              >
                Replicability
              </button>
              <button
                type="button"
                onClick={() => onSort("topic_sustained_traction_score")}
                className={sortField === "topic_sustained_traction_score" ? "text-primary" : "text-muted-foreground"}
              >
                Traction
              </button>
            </div>
          </div>

          {loading ? (
            <div className="space-y-3 p-4">
              {Array.from({ length: 5 }).map((_, index) => (
                <Skeleton key={index} className="h-16 w-full" />
              ))}
            </div>
          ) : error ? (
            <div className="p-4 text-sm text-critical">{error}</div>
          ) : sortedItems.length === 0 ? (
            <div className="p-4 text-sm text-muted-foreground">No topics match the current filters.</div>
          ) : (
            <div className="overflow-hidden">
              <table className="w-full">
                <thead className="border-b border-border bg-muted/40 text-[10px] uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2 text-left">Topic</th>
                    <th className="px-4 py-2 text-left">Type</th>
                    <th className="px-4 py-2 text-left">Replicability</th>
                    <th className="px-4 py-2 text-left">Traction</th>
                    <th className="px-4 py-2 text-left">Fragility</th>
                    <th className="px-4 py-2 text-left">Coverage</th>
                    <th className="px-4 py-2 text-left">Channels</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedItems.map((row) => (
                    <tr
                      key={row.topic_cluster}
                      onClick={() => handleSelect(row)}
                      className={`cursor-pointer border-b border-border transition hover:bg-muted/30 ${
                        selectedTopic === row.topic_cluster ? "bg-primary/5" : ""
                      }`}
                    >
                      <td className="px-4 py-3">
                        <div className="text-sm text-foreground">{row.topic_cluster}</div>
                        <div className="mt-1 text-[10px] uppercase tracking-wide text-muted-foreground">
                          {titleCase(filters.analysisWindow ? `${filters.analysisWindow} day window` : "Latest")}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <StatusChip status={row.topic_type} variant={scoreVariant(row.topic_replicability_score)} />
                      </td>
                      <td className="px-4 py-3">
                        <div className="w-28">
                          <ScoreBar score={scoreValue(row.topic_replicability_score)} variant="positive" />
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="w-28">
                          <ScoreBar score={scoreValue(row.topic_sustained_traction_score)} variant="positive" />
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="w-28">
                          <ScoreBar score={scoreValue(row.topic_fragility_score)} variant="caution" />
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">
                        {formatPercent(row.pct_videos_with_topic)}
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">{row.distinct_channels_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <aside className="rounded-xl border border-border bg-card p-4">
          <div className="mb-4">
            <h3 className="text-sm text-foreground">Topic detail</h3>
            <p className="text-xs text-muted-foreground">Replicability, traction, fragility, and channel dispersion.</p>
          </div>

          {!selectedRow ? (
            <div className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
              Select a topic cluster to inspect the supporting channels and example videos.
            </div>
          ) : detailLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
            </div>
          ) : (
            <div className="space-y-4">
              <div className="rounded-lg border border-border bg-background/40 p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-base text-foreground">{selectedRow.topic_cluster}</div>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <StatusChip status={selectedRow.topic_type} variant={scoreVariant(selectedRow.topic_replicability_score)} />
                      <ConfidenceBadge confidence={selectedRow.sample_confidence_level} />
                    </div>
                  </div>
                  <Sparkline
                    data={[
                      selectedRow.topic_start_strength_score ?? 0,
                      selectedRow.topic_sustained_traction_score ?? 0,
                      selectedRow.topic_replicability_score ?? 0,
                    ]}
                  />
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div>
                    <div className="mb-1 text-xs text-muted-foreground">Replicability</div>
                    <ScoreBar score={selectedRow.topic_replicability_score ?? 0} variant="positive" />
                  </div>
                  <div>
                    <div className="mb-1 text-xs text-muted-foreground">Sustained traction</div>
                    <ScoreBar score={selectedRow.topic_sustained_traction_score ?? 0} variant="positive" />
                  </div>
                  <div>
                    <div className="mb-1 text-xs text-muted-foreground">Start strength</div>
                    <ScoreBar score={selectedRow.topic_start_strength_score ?? 0} variant="positive" />
                  </div>
                  <div>
                    <div className="mb-1 text-xs text-muted-foreground">Fragility</div>
                    <ScoreBar score={selectedRow.topic_fragility_score ?? 0} variant="caution" />
                  </div>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-lg border border-border bg-background/40 p-3">
                  <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Videos</div>
                  <div className="mt-1 text-lg text-foreground">{selectedRow.video_count}</div>
                </div>
                <div className="rounded-lg border border-border bg-background/40 p-3">
                  <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Channels</div>
                  <div className="mt-1 text-lg text-foreground">{selectedRow.distinct_channels_count}</div>
                </div>
              </div>

              <div className="rounded-lg border border-border bg-background/40 p-3 text-sm text-muted-foreground">
                Coverage {formatPercent(selectedRow.pct_videos_with_topic)} and {selectedRow.distinct_channels_count} distinct channels.
              </div>

              {selectedRow.topic_fragility_score !== null && selectedRow.topic_fragility_score > 0.25 ? (
                <div className="rounded-lg border border-caution/30 bg-caution/10 p-3 text-xs text-caution-foreground">
                  High fragility detected. This topic may be time-sensitive or event-driven.
                </div>
              ) : null}

              {selectedRow.topic_replicability_score !== null && selectedRow.topic_replicability_score > 0.8 ? (
                <div className="rounded-lg border border-positive/30 bg-positive/10 p-3 text-xs text-positive-foreground">
                  Strong replication opportunity. High replicability with sustained traction.
                </div>
              ) : null}

              <div className="rounded-lg border border-border bg-background/40 p-3">
                <div className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Top channels</div>
                <div className="space-y-2">
                  {(detailData?.top_channels ?? []).length === 0 ? (
                    <div className="text-sm text-muted-foreground">No channel dispersion data available for this topic.</div>
                  ) : (
                    (detailData?.top_channels ?? []).map((item) => (
                      <div key={item.channel_handle} className="flex items-center justify-between rounded-md border border-border px-3 py-2">
                        <span className="text-sm text-foreground">{item.channel_handle}</span>
                        <span className="text-xs text-muted-foreground">{item.count}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="rounded-lg border border-border bg-background/40 p-3">
                <div className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Recent examples</div>
                <div className="space-y-2">
                  {(detailData?.recent_examples ?? []).length === 0 ? (
                    <div className="text-sm text-muted-foreground">No example videos resolved for this topic cluster.</div>
                  ) : (
                    (detailData?.recent_examples ?? []).map((video) => (
                      <div key={video.video_id} className="rounded-md border border-border px-3 py-2">
                        <div className="text-sm text-foreground">{video.title}</div>
                        <div className="mt-1 text-[10px] uppercase tracking-wide text-muted-foreground">
                          {video.channel_handle} · {video.channel_niche || "Uncategorized"}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
