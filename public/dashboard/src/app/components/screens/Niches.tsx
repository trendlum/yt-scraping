import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router";
import { useFilters } from "../../contexts/FilterContext";
import {
  buildDashboardQuery,
  ConfidenceLevel,
  NicheDetailResponse,
  NicheRow,
  formatPercent,
  titleCase,
} from "../../lib/dashboard";
import { useDashboardQuery } from "../../lib/useDashboardQuery";
import { ConfidenceBadge } from "../ui/ConfidenceBadge";
import { ScoreBar } from "../ui/ScoreBar";
import { Sparkline } from "../ui/Sparkline";
import { StatusChip } from "../ui/StatusChip";
import { Skeleton } from "../ui/skeleton";

type SortField = "niche_growth_score_confirmed" | "niche_early_signal_score" | "video_count_total" | "distinct_channels_count";

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

export function Niches() {
  const location = useLocation();
  const { filters, setFilters } = useFilters();
  const [selectedNiche, setSelectedNiche] = useState<string | null>(null);
  const [sortField, setSortField] = useState<SortField>("niche_growth_score_confirmed");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  const query = useMemo(() => buildDashboardQuery(filters, { limit: 250 }), [filters]);
  const { data, loading, error } = useDashboardQuery<{ items: NicheRow[] }>("/api/dashboard/niches", query);

  const items = data?.items ?? [];

  useEffect(() => {
    const initial = (location.state as { selectedId?: string } | null | undefined)?.selectedId;
    if (initial && items.some((row) => row.niche === initial)) {
      setSelectedNiche(initial);
      return;
    }
    if (!selectedNiche && items.length > 0) {
      setSelectedNiche(items[0].niche);
    }
  }, [items, location.state, selectedNiche]);

  useEffect(() => {
    if (selectedNiche && !items.some((row) => row.niche === selectedNiche)) {
      setSelectedNiche(items[0]?.niche ?? null);
    }
  }, [items, selectedNiche]);

  const selectedRow = useMemo(
    () => items.find((row) => row.niche === selectedNiche) ?? null,
    [items, selectedNiche],
  );

  const detailQuery = useMemo(
    () => buildDashboardQuery(filters, { niche: selectedRow?.niche ?? selectedNiche ?? "" }),
    [filters, selectedRow?.niche, selectedNiche],
  );
  const { data: detailData, loading: detailLoading } = useDashboardQuery<NicheDetailResponse>(
    selectedRow?.niche ? "/api/dashboard/niche-detail" : "/api/dashboard/niche-detail",
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

  const handleSelect = (row: NicheRow) => {
    setSelectedNiche(row.niche);
    setFilters({ ...filters, niche: row.niche });
  };

  return (
    <div className="h-[calc(100vh-180px)] overflow-auto px-4 pt-4 pb-6">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.45fr)_minmax(0,0.9fr)]">
        <section className="rounded-xl border border-border bg-card">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div>
              <h2 className="text-sm text-foreground">Niche rankings</h2>
              <p className="text-xs text-muted-foreground">Ranked by confirmed growth, early signal, and sample quality.</p>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <button
                type="button"
                onClick={() => onSort("niche_early_signal_score")}
                className={sortField === "niche_early_signal_score" ? "text-primary" : "text-muted-foreground"}
              >
                Early
              </button>
              <button
                type="button"
                onClick={() => onSort("niche_growth_score_confirmed")}
                className={sortField === "niche_growth_score_confirmed" ? "text-primary" : "text-muted-foreground"}
              >
                Confirmed
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
            <div className="p-4 text-sm text-muted-foreground">No niches match the current filters.</div>
          ) : (
            <div className="overflow-hidden">
              <table className="w-full">
                <thead className="border-b border-border bg-muted/40 text-[10px] uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2 text-left">Niche</th>
                    <th className="px-4 py-2 text-left">Status</th>
                    <th className="px-4 py-2 text-left">Early</th>
                    <th className="px-4 py-2 text-left">Confirmed</th>
                    <th className="px-4 py-2 text-left">Confidence</th>
                    <th className="px-4 py-2 text-left">Channels</th>
                    <th className="px-4 py-2 text-left">Videos</th>
                    <th className="px-4 py-2 text-left">Trend</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedItems.map((row) => (
                    <tr
                      key={row.niche}
                      onClick={() => handleSelect(row)}
                      className={`cursor-pointer border-b border-border transition hover:bg-muted/30 ${
                        selectedNiche === row.niche ? "bg-primary/5" : ""
                      }`}
                    >
                      <td className="px-4 py-3">
                        <div className="text-sm text-foreground">{row.niche}</div>
                        <div className="mt-1 text-[10px] uppercase tracking-wide text-muted-foreground">
                          {titleCase(filters.analysisWindow ? `${filters.analysisWindow} day window` : "Latest")}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <StatusChip status={row.niche_growth_status_confirmed} variant={scoreVariant(row.niche_growth_score_confirmed)} />
                      </td>
                      <td className="px-4 py-3">
                        <div className="w-28">
                          <ScoreBar score={scoreValue(row.niche_early_signal_score)} variant="positive" />
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="w-28">
                          <ScoreBar score={scoreValue(row.niche_growth_score_confirmed)} variant="positive" />
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <ConfidenceBadge confidence={row.sample_confidence_level} />
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">{row.distinct_channels_count}</td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">{row.video_count_total}</td>
                      <td className="px-4 py-3">
                        <Sparkline
                          data={[
                            row.niche_early_signal_score ?? 0,
                            row.niche_growth_forecast_score ?? 0,
                            row.niche_growth_score_confirmed ?? 0,
                          ]}
                        />
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
            <h3 className="text-sm text-foreground">Niche detail</h3>
            <p className="text-xs text-muted-foreground">Early vs confirmed signal, confidence, and supporting entities.</p>
          </div>

          {!selectedRow ? (
            <div className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
              Select a niche to inspect the supporting channels and topics.
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
                    <div className="text-base text-foreground">{selectedRow.niche}</div>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <StatusChip status={selectedRow.niche_growth_status_early} variant={scoreVariant(selectedRow.niche_early_signal_score)} />
                      <StatusChip status={selectedRow.niche_growth_status_confirmed} variant={scoreVariant(selectedRow.niche_growth_score_confirmed)} />
                      <ConfidenceBadge confidence={selectedRow.sample_confidence_level} />
                    </div>
                  </div>
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div>
                    <div className="mb-1 text-xs text-muted-foreground">Early signal</div>
                    <ScoreBar score={selectedRow.niche_early_signal_score ?? 0} variant="positive" />
                  </div>
                  <div>
                    <div className="mb-1 text-xs text-muted-foreground">Confirmed growth</div>
                    <ScoreBar score={selectedRow.niche_growth_score_confirmed ?? 0} variant="positive" />
                  </div>
                  <div>
                    <div className="mb-1 text-xs text-muted-foreground">Acceleration</div>
                    <ScoreBar score={selectedRow.niche_acceleration_score_confirmed ?? 0} variant="positive" />
                  </div>
                  <div>
                    <div className="mb-1 text-xs text-muted-foreground">Outlier dependency</div>
                    <ScoreBar score={selectedRow.niche_outlier_dependency_score ?? 0} variant="caution" />
                  </div>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-lg border border-border bg-background/40 p-3">
                  <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Sample size</div>
                  <div className="mt-1 text-lg text-foreground">{selectedRow.video_count_total}</div>
                </div>
                <div className="rounded-lg border border-border bg-background/40 p-3">
                  <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Distinct channels</div>
                  <div className="mt-1 text-lg text-foreground">{selectedRow.distinct_channels_count}</div>
                </div>
              </div>

              {selectedRow.sample_confidence_level !== "high" ? (
                <div className="rounded-lg border border-caution/30 bg-caution/10 p-3 text-xs text-caution-foreground">
                  Low sample confidence. Treat this niche as directional rather than confirmed.
                </div>
              ) : null}

              {selectedRow.notes ? (
                <div className="rounded-lg border border-border bg-background/40 p-3 text-sm text-muted-foreground">
                  {selectedRow.notes}
                </div>
              ) : null}

              <div className="rounded-lg border border-border bg-background/40 p-3">
                <div className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Recent channels</div>
                <div className="space-y-2">
                  {(detailData?.recent_channels ?? []).length === 0 ? (
                    <div className="text-sm text-muted-foreground">No supporting channels resolved for this niche.</div>
                  ) : (
                    (detailData?.recent_channels ?? []).map((row) => (
                      <div key={row.channel_handle} className="rounded-md border border-border px-3 py-2 text-sm text-foreground">
                        <div>{row.channel_handle}</div>
                        <div className="mt-1 text-[10px] uppercase tracking-wide text-muted-foreground">
                          {row.channel_niche || "Uncategorized"} · {row.channel_growth_status}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="rounded-lg border border-border bg-background/40 p-3">
                <div className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Top topics</div>
                <div className="space-y-2">
                  {(detailData?.top_topics ?? []).length === 0 ? (
                    <div className="text-sm text-muted-foreground">No topic clusters resolved for this niche.</div>
                  ) : (
                    (detailData?.top_topics ?? []).map((topic) => (
                      <div key={topic.label} className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm">
                        <span className="text-foreground">{topic.label}</span>
                        <span className="text-muted-foreground">{topic.count}</span>
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
