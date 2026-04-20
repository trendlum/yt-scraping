import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router";
import { useFilters } from "../../contexts/FilterContext";
import {
  buildDashboardQuery,
  ChannelDetailResponse,
  ChannelRow,
  formatScore,
  titleCase,
} from "../../lib/dashboard";
import { useDashboardQuery } from "../../lib/useDashboardQuery";
import { ConfidenceBadge } from "../ui/ConfidenceBadge";
import { DeltaPill } from "../ui/DeltaPill";
import { ScoreBar } from "../ui/ScoreBar";
import { Sparkline } from "../ui/Sparkline";
import { StatusChip } from "../ui/StatusChip";
import { Skeleton } from "../ui/skeleton";

type SortField =
  | "channel_growth_score"
  | "channel_packaging_improvement_score"
  | "channel_sustainability_improvement_score"
  | "channel_volatility_score"
  | "delta_overall_score";

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

export function Channels() {
  const location = useLocation();
  const { filters, setFilters } = useFilters();
  const [selectedChannel, setSelectedChannel] = useState<string | null>(null);
  const [sortField, setSortField] = useState<SortField>("channel_growth_score");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  const query = useMemo(() => buildDashboardQuery(filters, { limit: 250 }), [filters]);
  const { data, loading, error } = useDashboardQuery<{ items: ChannelRow[] }>("/api/dashboard/channels", query);
  const items = data?.items ?? [];

  useEffect(() => {
    const initial = (location.state as { selectedId?: string } | null | undefined)?.selectedId;
    if (initial && items.some((row) => row.channel_handle === initial)) {
      setSelectedChannel(initial);
      return;
    }
    if (!selectedChannel && items.length > 0) {
      setSelectedChannel(items[0].channel_handle);
    }
  }, [items, location.state, selectedChannel]);

  useEffect(() => {
    if (selectedChannel && !items.some((row) => row.channel_handle === selectedChannel)) {
      setSelectedChannel(items[0]?.channel_handle ?? null);
    }
  }, [items, selectedChannel]);

  const selectedRow = useMemo(
    () => items.find((row) => row.channel_handle === selectedChannel) ?? null,
    [items, selectedChannel],
  );

  const detailQuery = useMemo(
    () => buildDashboardQuery(filters, { channel_handle: selectedRow?.channel_handle ?? selectedChannel ?? "" }),
    [filters, selectedRow?.channel_handle, selectedChannel],
  );
  const { data: detailData, loading: detailLoading } = useDashboardQuery<ChannelDetailResponse>(
    "/api/dashboard/channel-detail",
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

  const handleSelect = (row: ChannelRow) => {
    setSelectedChannel(row.channel_handle);
    setFilters({
      ...filters,
      channelHandle: row.channel_handle,
      niche: row.channel_niche || filters.niche,
    });
  };

  return (
    <div className="h-[calc(100vh-180px)] overflow-auto px-4 pt-4 pb-6">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.45fr)_minmax(0,0.9fr)]">
        <section className="rounded-xl border border-border bg-card">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div>
              <h2 className="text-sm text-foreground">Channel rankings</h2>
              <p className="text-xs text-muted-foreground">Comparing recent vs previous windows and growth signals.</p>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <button
                type="button"
                onClick={() => onSort("channel_growth_score")}
                className={sortField === "channel_growth_score" ? "text-primary" : "text-muted-foreground"}
              >
                Growth
              </button>
              <button
                type="button"
                onClick={() => onSort("delta_overall_score")}
                className={sortField === "delta_overall_score" ? "text-primary" : "text-muted-foreground"}
              >
                Delta
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
            <div className="p-4 text-sm text-muted-foreground">No channels match the current filters.</div>
          ) : (
            <div className="overflow-hidden">
              <table className="w-full">
                <thead className="border-b border-border bg-muted/40 text-[10px] uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2 text-left">Channel</th>
                    <th className="px-4 py-2 text-left">Niche</th>
                    <th className="px-4 py-2 text-left">Status</th>
                    <th className="px-4 py-2 text-left">Growth</th>
                    <th className="px-4 py-2 text-left">Packaging</th>
                    <th className="px-4 py-2 text-left">Volatility</th>
                    <th className="px-4 py-2 text-left">Delta</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedItems.map((row) => (
                    <tr
                      key={row.channel_handle}
                      onClick={() => handleSelect(row)}
                      className={`cursor-pointer border-b border-border transition hover:bg-muted/30 ${
                        selectedChannel === row.channel_handle ? "bg-primary/5" : ""
                      }`}
                    >
                      <td className="px-4 py-3">
                        <div className="text-sm text-foreground">{row.channel_handle}</div>
                        <div className="mt-1 text-[10px] uppercase tracking-wide text-muted-foreground">
                          {titleCase(filters.analysisWindow ? `${filters.analysisWindow} day window` : "Latest")}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">{row.channel_niche || "Uncategorized"}</td>
                      <td className="px-4 py-3">
                        <StatusChip status={row.channel_growth_status} variant={scoreVariant(row.channel_growth_score)} />
                      </td>
                      <td className="px-4 py-3">
                        <div className="w-28">
                          <ScoreBar score={scoreValue(row.channel_growth_score)} variant="positive" />
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="w-28">
                          <ScoreBar score={scoreValue(row.channel_packaging_improvement_score)} variant="positive" />
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="w-28">
                          <ScoreBar score={scoreValue(row.channel_volatility_score)} variant="caution" />
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <DeltaPill value={Math.round((row.delta_overall_score ?? 0) * 100)} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <aside className="rounded-xl border border-border bg-card p-4">
          <div className="mb-4">
            <h3 className="text-sm text-foreground">Channel detail</h3>
            <p className="text-xs text-muted-foreground">Recent vs previous window, improvement scores, and volatility.</p>
          </div>

          {!selectedRow ? (
            <div className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
              Select a channel to inspect trend changes and the latest videos.
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
                    <div className="text-base text-foreground">{selectedRow.channel_handle}</div>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <StatusChip status={selectedRow.channel_growth_status} variant={scoreVariant(selectedRow.channel_growth_score)} />
                      <ConfidenceBadge confidence={selectedRow.sample_confidence_level} />
                      <span className="text-xs text-muted-foreground">{selectedRow.channel_niche || "Uncategorized"}</span>
                    </div>
                  </div>
                  <Sparkline
                    data={[
                      selectedRow.channel_packaging_improvement_score ?? 0,
                      selectedRow.channel_sustainability_improvement_score ?? 0,
                      selectedRow.channel_algorithmic_shift_score ?? 0,
                    ]}
                  />
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div>
                    <div className="mb-1 text-xs text-muted-foreground">Growth score</div>
                    <ScoreBar score={selectedRow.channel_growth_score ?? 0} variant="positive" />
                  </div>
                  <div>
                    <div className="mb-1 text-xs text-muted-foreground">Packaging improvement</div>
                    <ScoreBar score={selectedRow.channel_packaging_improvement_score ?? 0} variant="positive" />
                  </div>
                  <div>
                    <div className="mb-1 text-xs text-muted-foreground">Sustainability improvement</div>
                    <ScoreBar score={selectedRow.channel_sustainability_improvement_score ?? 0} variant="positive" />
                  </div>
                  <div>
                    <div className="mb-1 text-xs text-muted-foreground">Volatility</div>
                    <ScoreBar score={selectedRow.channel_volatility_score ?? 0} variant="caution" />
                  </div>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-lg border border-border bg-background/40 p-3">
                  <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Recent videos</div>
                  <div className="mt-1 text-lg text-foreground">{selectedRow.video_count_recent}</div>
                </div>
                <div className="rounded-lg border border-border bg-background/40 p-3">
                  <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Previous videos</div>
                  <div className="mt-1 text-lg text-foreground">{selectedRow.video_count_previous}</div>
                </div>
              </div>

              <div className="rounded-lg border border-border bg-background/40 p-3">
                <div className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Window comparison</div>
                <div className="space-y-2 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Median overall score</span>
                      <span className="text-foreground">
                      {formatScore(selectedRow.median_overall_score_previous)} {"->"} {formatScore(selectedRow.median_overall_score_recent)}
                      </span>
                    </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Delta overall score</span>
                    <DeltaPill value={Math.round((selectedRow.delta_overall_score ?? 0) * 100)} />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Delta momentum</span>
                    <DeltaPill value={Math.round((selectedRow.delta_momentum_score ?? 0) * 100)} />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Delta packaging</span>
                    <DeltaPill value={Math.round((selectedRow.delta_packaging_score ?? 0) * 100)} />
                  </div>
                </div>
              </div>

              {selectedRow.channel_growth_status === "algorithmic_shift" ? (
                <div className="rounded-lg border border-positive/30 bg-positive/10 p-3 text-xs text-positive-foreground">
                  Strong algorithmic shift detected. This channel may have found a new winning format.
                </div>
              ) : null}

              {selectedRow.sample_confidence_level !== "high" ? (
                <div className="rounded-lg border border-caution/30 bg-caution/10 p-3 text-xs text-caution-foreground">
                  Low sample confidence. Use the delta signals as directional evidence only.
                </div>
              ) : null}

              <div className="rounded-lg border border-border bg-background/40 p-3">
                <div className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Recent videos</div>
                <div className="space-y-2">
                  {(detailData?.recent_videos ?? []).length === 0 ? (
                    <div className="text-sm text-muted-foreground">No recent videos resolved for this channel.</div>
                  ) : (
                    (detailData?.recent_videos ?? []).map((video) => (
                      <div key={video.video_id} className="rounded-md border border-border px-3 py-2">
                        <div className="text-sm text-foreground">{video.title}</div>
                        <div className="mt-1 flex items-center gap-2 text-[10px] uppercase tracking-wide text-muted-foreground">
                          <span>{video.performance_label || "unclassified"}</span>
                          <span>{video.channel_niche || "Uncategorized"}</span>
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
