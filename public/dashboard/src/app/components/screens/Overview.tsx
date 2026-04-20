import { useMemo } from "react";
import { useNavigate } from "react-router";
import { useFilters } from "../../contexts/FilterContext";
import {
  buildDashboardQuery,
  ConfidenceLevel,
  OverviewResponse,
  formatAgeDays,
  formatPercent,
} from "../../lib/dashboard";
import { useDashboardQuery } from "../../lib/useDashboardQuery";
import { ConfidenceBadge } from "../ui/ConfidenceBadge";
import { DeltaPill } from "../ui/DeltaPill";
import { KPICard } from "../ui/KPICard";
import { ScoreBar } from "../ui/ScoreBar";
import { Sparkline } from "../ui/Sparkline";
import { StatusChip } from "../ui/StatusChip";
import { Skeleton } from "../ui/skeleton";

function confidenceCount(items: Array<{ sample_confidence_level?: ConfidenceLevel; underpackaged_confidence?: ConfidenceLevel; overpackaged_confidence?: ConfidenceLevel }>) {
  return items.filter(
    (item) =>
      item.sample_confidence_level === "high" ||
      item.underpackaged_confidence === "high" ||
      item.overpackaged_confidence === "high",
  ).length;
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

export function Overview() {
  const navigate = useNavigate();
  const { filters, setFilters } = useFilters();

  const query = useMemo(() => buildDashboardQuery(filters, { limit: 250 }), [filters]);
  const { data, loading, error } = useDashboardQuery<OverviewResponse>("/api/dashboard/overview", query);

  const summary = data?.summary;
  const confidenceRows = [
    ...((data?.niches ?? []) as Array<{ sample_confidence_level?: ConfidenceLevel }>),
    ...((data?.channels ?? []) as Array<{ sample_confidence_level?: ConfidenceLevel }>),
    ...((data?.topics ?? []) as Array<{ sample_confidence_level?: ConfidenceLevel }>),
    ...((data?.underpackaged ?? []) as Array<{ underpackaged_confidence?: ConfidenceLevel }>),
    ...((data?.overpackaged ?? []) as Array<{ overpackaged_confidence?: ConfidenceLevel }>),
  ];
  const highConfidenceCount = confidenceCount(confidenceRows);
  const totalTracked = confidenceRows.length;
  const highConfidenceShare = totalTracked > 0 ? Math.round((highConfidenceCount / totalTracked) * 100) : 0;

  const applyFilterAndNavigate = (path: string, nextFilters: Partial<typeof filters>) => {
    setFilters({ ...filters, ...nextFilters });
    navigate(path);
  };

  const topNiches = data?.niches ?? [];
  const topChannels = data?.channels ?? [];
  const topTopics = data?.topics ?? [];
  const underpackaged = data?.underpackaged ?? [];
  const overpackaged = data?.overpackaged ?? [];

  return (
    <div className="space-y-4 p-4">
      <div className="grid gap-3 lg:grid-cols-6">
        <KPICard label="Emerging niches" value={summary?.niches_count ?? 0} />
        <KPICard label="Improving channels" value={summary?.channels_count ?? 0} />
        <KPICard label="Replicable topics" value={summary?.topics_count ?? 0} />
        <KPICard label="Underpackaged videos" value={summary?.underpackaged_count ?? 0} />
        <KPICard label="Overpackaged videos" value={summary?.overpackaged_count ?? 0} />
        <KPICard label="High confidence" value={highConfidenceShare} delta={highConfidenceCount} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <section className="rounded-xl border border-border bg-card p-4">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h2 className="text-sm text-foreground">Signal quality</h2>
              <p className="text-xs text-muted-foreground">Confidence distribution across the current result set.</p>
            </div>
            <StatusChip status={`window ${filters.analysisWindow}d`} variant="neutral" />
          </div>

          <div className="grid gap-3 sm:grid-cols-4">
            <div className="rounded-lg border border-border bg-background/40 p-3">
              <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Analysis date</div>
              <div className="mt-1 text-lg text-foreground">{filters.analysisDate || "Latest"}</div>
            </div>
            <div className="rounded-lg border border-border bg-background/40 p-3">
              <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Window</div>
              <div className="mt-1 text-lg text-foreground">{filters.analysisWindow} days</div>
            </div>
            <div className="rounded-lg border border-border bg-background/40 p-3">
              <div className="text-[10px] uppercase tracking-wide text-muted-foreground">High confidence</div>
              <div className="mt-1 text-lg text-foreground">{highConfidenceShare}%</div>
            </div>
            <div className="rounded-lg border border-border bg-background/40 p-3">
              <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Tracked rows</div>
              <div className="mt-1 text-lg text-foreground">{totalTracked}</div>
            </div>
          </div>
        </section>

        <section className="rounded-xl border border-border bg-card p-4">
          <h2 className="text-sm text-foreground">Active filters</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {filters.niche ? <StatusChip status={filters.niche} variant="neutral" /> : null}
            {filters.channelHandle ? <StatusChip status={filters.channelHandle} variant="neutral" /> : null}
            {filters.topicCluster ? <StatusChip status={filters.topicCluster} variant="neutral" /> : null}
            {filters.nicheGrowthStatus ? <StatusChip status={filters.nicheGrowthStatus} variant="neutral" /> : null}
            {filters.channelGrowthStatus ? <StatusChip status={filters.channelGrowthStatus} variant="neutral" /> : null}
            {filters.topicType ? <StatusChip status={filters.topicType} variant="neutral" /> : null}
            {filters.performanceLabel ? <StatusChip status={filters.performanceLabel} variant="neutral" /> : null}
            {filters.sampleConfidence ? <StatusChip status={filters.sampleConfidence} variant="neutral" /> : null}
          </div>
        </section>
      </div>

      {loading ? (
        <div className="grid gap-4 xl:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="rounded-xl border border-border bg-card p-4">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="mt-4 h-28 w-full" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="rounded-xl border border-critical/30 bg-critical/10 p-4 text-sm text-critical">
          {error}
        </div>
      ) : (
        <>
          <div className="grid gap-4 xl:grid-cols-2">
            <section className="rounded-xl border border-border bg-card p-4">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <h3 className="text-sm text-foreground">Top niches to watch</h3>
                  <p className="text-xs text-muted-foreground">Ranked by confirmed growth and early signal.</p>
                </div>
                <button
                  type="button"
                  onClick={() => navigate("/niches")}
                  className="text-xs text-primary"
                >
                  View all
                </button>
              </div>
              <div className="space-y-3">
                {topNiches.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
                    No niche data for the current filters.
                  </div>
                ) : (
                  topNiches.map((row) => (
                    <button
                      key={row.niche}
                      type="button"
                      onClick={() => applyFilterAndNavigate("/niches", { niche: row.niche })}
                      className="w-full rounded-lg border border-border bg-background/40 p-3 text-left transition hover:border-primary/40"
                    >
                      <div className="mb-2 flex items-start justify-between gap-3">
                        <div>
                          <div className="text-sm text-foreground">{row.niche}</div>
                          <div className="mt-1 flex flex-wrap items-center gap-2">
                            <StatusChip status={row.niche_growth_status_confirmed} variant={scoreVariant(row.niche_growth_score_confirmed)} />
                            <ConfidenceBadge confidence={row.sample_confidence_level} />
                          </div>
                        </div>
                        <Sparkline
                          data={[
                            row.niche_early_signal_score ?? 0,
                            row.niche_growth_forecast_score ?? 0,
                            row.niche_growth_score_confirmed ?? 0,
                          ]}
                          variant="positive"
                        />
                      </div>
                      <div className="grid gap-3 text-xs sm:grid-cols-2">
                        <div>
                          <div className="mb-1 text-muted-foreground">Early signal</div>
                          <ScoreBar score={row.niche_early_signal_score ?? 0} variant="positive" />
                        </div>
                        <div>
                          <div className="mb-1 text-muted-foreground">Confirmed growth</div>
                          <ScoreBar score={row.niche_growth_score_confirmed ?? 0} variant="positive" />
                        </div>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-3 text-[10px] uppercase tracking-wide text-muted-foreground">
                        <span>{row.distinct_channels_count} channels</span>
                        <span>{row.video_count_total} videos</span>
                        <span>{formatPercent(row.pct_explosive)} explosive</span>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </section>

            <section className="rounded-xl border border-border bg-card p-4">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <h3 className="text-sm text-foreground">Top channels to watch</h3>
                  <p className="text-xs text-muted-foreground">Channels with positive growth and improvement signals.</p>
                </div>
                <button
                  type="button"
                  onClick={() => navigate("/channels")}
                  className="text-xs text-primary"
                >
                  View all
                </button>
              </div>
              <div className="space-y-3">
                {topChannels.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
                    No channel data for the current filters.
                  </div>
                ) : (
                  topChannels.map((row) => (
                    <button
                      key={row.channel_handle}
                      type="button"
                      onClick={() =>
                        applyFilterAndNavigate("/channels", {
                          channelHandle: row.channel_handle,
                          niche: row.channel_niche || filters.niche,
                        })
                      }
                      className="w-full rounded-lg border border-border bg-background/40 p-3 text-left transition hover:border-primary/40"
                    >
                      <div className="mb-2 flex items-start justify-between gap-3">
                        <div>
                          <div className="text-sm text-foreground">{row.channel_handle}</div>
                          <div className="mt-1 flex flex-wrap items-center gap-2">
                            <span className="text-xs text-muted-foreground">{row.channel_niche || "Uncategorized"}</span>
                            <StatusChip status={row.channel_growth_status} variant="positive" />
                            <DeltaPill value={Math.round((row.delta_overall_score ?? 0) * 100)} />
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <ConfidenceBadge confidence={row.sample_confidence_level} />
                          <Sparkline
                            data={[
                              row.median_packaging_score_previous ?? 0,
                              row.median_packaging_score_recent ?? 0,
                              row.median_overall_score_recent ?? 0,
                            ]}
                            variant="positive"
                          />
                        </div>
                      </div>
                      <div className="grid gap-3 text-xs sm:grid-cols-3">
                        <div>
                          <div className="mb-1 text-muted-foreground">Growth</div>
                          <ScoreBar score={row.channel_growth_score ?? 0} variant="positive" />
                        </div>
                        <div>
                          <div className="mb-1 text-muted-foreground">Packaging improvement</div>
                          <ScoreBar score={row.channel_packaging_improvement_score ?? 0} variant="positive" />
                        </div>
                        <div>
                          <div className="mb-1 text-muted-foreground">Volatility</div>
                          <ScoreBar score={row.channel_volatility_score ?? 0} variant="caution" />
                        </div>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </section>
          </div>

          <section className="rounded-xl border border-border bg-card p-4">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h3 className="text-sm text-foreground">Top topics to replicate</h3>
                <p className="text-xs text-muted-foreground">Topic clusters with strong replicability and traction.</p>
              </div>
              <button
                type="button"
                onClick={() => navigate("/topics")}
                className="text-xs text-primary"
              >
                View all
              </button>
            </div>
            <div className="grid gap-3 xl:grid-cols-3">
              {topTopics.length === 0 ? (
                <div className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
                  No topic data for the current filters.
                </div>
              ) : (
                topTopics.map((row) => (
                  <button
                    key={row.topic_cluster}
                    type="button"
                    onClick={() => applyFilterAndNavigate("/topics", { topicCluster: row.topic_cluster })}
                    className="rounded-lg border border-border bg-background/40 p-3 text-left transition hover:border-primary/40"
                  >
                    <div className="mb-2 flex items-start justify-between gap-3">
                      <div>
                        <div className="text-sm text-foreground">{row.topic_cluster}</div>
                        <div className="mt-1 flex flex-wrap items-center gap-2">
                          <StatusChip status={row.topic_type} variant="positive" />
                          <ConfidenceBadge confidence={row.sample_confidence_level} />
                        </div>
                      </div>
                      <Sparkline
                        data={[
                          row.topic_start_strength_score ?? 0,
                          row.topic_sustained_traction_score ?? 0,
                          row.topic_replicability_score ?? 0,
                        ]}
                        variant="positive"
                      />
                    </div>
                    <div className="space-y-2 text-xs">
                      <div>
                        <div className="mb-1 text-muted-foreground">Replicability</div>
                        <ScoreBar score={row.topic_replicability_score ?? 0} variant="positive" />
                      </div>
                      <div>
                        <div className="mb-1 text-muted-foreground">Sustained traction</div>
                        <ScoreBar score={row.topic_sustained_traction_score ?? 0} variant="positive" />
                      </div>
                      <div>
                        <div className="mb-1 text-muted-foreground">Fragility</div>
                        <ScoreBar score={row.topic_fragility_score ?? 0} variant="caution" />
                      </div>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-3 text-[10px] uppercase tracking-wide text-muted-foreground">
                      <span>{row.distinct_channels_count} channels</span>
                      <span>{row.video_count} videos</span>
                      <span>{formatPercent(row.pct_videos_with_topic)} coverage</span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </section>

          <div className="grid gap-4 xl:grid-cols-2">
            <section className="rounded-xl border border-border bg-card p-4">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <h3 className="text-sm text-foreground">Underpackaged opportunities</h3>
                  <p className="text-xs text-muted-foreground">Strong momentum with weaker packaging.</p>
                </div>
                <button type="button" onClick={() => navigate("/videos")} className="text-xs text-primary">
                  View all
                </button>
              </div>
              <div className="space-y-3">
                {underpackaged.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
                    No underpackaged videos match the current filters.
                  </div>
                ) : (
                  underpackaged.map((row) => (
                    <button
                      key={row.video_id}
                      type="button"
                      onClick={() =>
                        applyFilterAndNavigate("/videos", {
                          channelHandle: row.channel_handle,
                          niche: row.channel_niche || filters.niche,
                          videoType: "underpackaged",
                        })
                      }
                      className="w-full rounded-lg border border-border bg-background/40 p-3 text-left transition hover:border-primary/40"
                    >
                      <div className="mb-2 flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="truncate text-sm text-foreground">{row.title}</div>
                          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                            <span>{row.channel_handle}</span>
                            <span>{row.channel_niche || "Uncategorized"}</span>
                            <span>{formatAgeDays(row.age_days)}</span>
                          </div>
                        </div>
                        <ConfidenceBadge confidence={row.underpackaged_confidence ?? "medium"} />
                      </div>
                      <div className="grid gap-3 text-xs sm:grid-cols-2">
                        <div>
                          <div className="mb-1 text-muted-foreground">Packaging</div>
                          <ScoreBar score={row.packaging_score ?? 0} variant="caution" />
                        </div>
                        <div>
                          <div className="mb-1 text-muted-foreground">Momentum</div>
                          <ScoreBar score={row.momentum_score ?? 0} variant="positive" />
                        </div>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <StatusChip status={row.underpackaged_type || "unknown"} variant="positive" />
                        <DeltaPill value={Math.round((row.underpackaged_score ?? 0) * 100)} />
                      </div>
                    </button>
                  ))
                )}
              </div>
            </section>

            <section className="rounded-xl border border-border bg-card p-4">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <h3 className="text-sm text-foreground">Overpackaged videos</h3>
                  <p className="text-xs text-muted-foreground">Strong packaging with weak delivery.</p>
                </div>
                <button type="button" onClick={() => navigate("/videos")} className="text-xs text-primary">
                  View all
                </button>
              </div>
              <div className="space-y-3">
                {overpackaged.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
                    No overpackaged videos match the current filters.
                  </div>
                ) : (
                  overpackaged.map((row) => (
                    <button
                      key={row.video_id}
                      type="button"
                      onClick={() =>
                        applyFilterAndNavigate("/videos", {
                          channelHandle: row.channel_handle,
                          niche: row.channel_niche || filters.niche,
                          videoType: "overpackaged",
                        })
                      }
                      className="w-full rounded-lg border border-border bg-background/40 p-3 text-left transition hover:border-primary/40"
                    >
                      <div className="mb-2 flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="truncate text-sm text-foreground">{row.title}</div>
                          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                            <span>{row.channel_handle}</span>
                            <span>{row.channel_niche || "Uncategorized"}</span>
                            <span>{formatAgeDays(row.age_days)}</span>
                          </div>
                        </div>
                        <ConfidenceBadge confidence={row.overpackaged_confidence ?? "medium"} />
                      </div>
                      <div className="grid gap-3 text-xs sm:grid-cols-2">
                        <div>
                          <div className="mb-1 text-muted-foreground">Packaging</div>
                          <ScoreBar score={row.packaging_score ?? 0} variant="positive" />
                        </div>
                        <div>
                          <div className="mb-1 text-muted-foreground">Momentum</div>
                          <ScoreBar score={row.momentum_score ?? 0} variant="critical" />
                        </div>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <StatusChip status={row.overpackaged_type || "unknown"} variant="caution" />
                        <DeltaPill value={Math.round((row.overpackaged_score ?? 0) * 100)} />
                      </div>
                    </button>
                  ))
                )}
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
