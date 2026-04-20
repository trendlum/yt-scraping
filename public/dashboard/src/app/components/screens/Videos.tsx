import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router";
import { useFilters } from "../../contexts/FilterContext";
import {
  buildDashboardQuery,
  ConfidenceLevel,
  formatAgeDays,
  formatPercent,
  formatScore,
  titleCase,
  VideoDetailResponse,
  VideoRow,
} from "../../lib/dashboard";
import { useDashboardQuery } from "../../lib/useDashboardQuery";
import { ConfidenceBadge } from "../ui/ConfidenceBadge";
import { ScoreBar } from "../ui/ScoreBar";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "../ui/sheet";
import { StatusChip } from "../ui/StatusChip";
import { Spinner } from "../ui/spinner";
import { Tabs, TabsList, TabsTrigger } from "../ui/tabs";

type SortField = "primary_score" | "momentum_score" | "age_days" | "ratio_d7";

function getPrimaryScore(row: VideoRow, tab: "underpackaged" | "overpackaged") {
  return tab === "underpackaged" ? row.underpackaged_score ?? 0 : row.overpackaged_score ?? 0;
}

function getConfidence(row: VideoRow, tab: "underpackaged" | "overpackaged"): ConfidenceLevel {
  const confidence = tab === "underpackaged" ? row.underpackaged_confidence : row.overpackaged_confidence;
  return confidence ?? "medium";
}

function getType(row: VideoRow, tab: "underpackaged" | "overpackaged") {
  return tab === "underpackaged" ? row.underpackaged_type || "unknown" : row.overpackaged_type || "unknown";
}

export function Videos() {
  const location = useLocation();
  const { filters, setFilters } = useFilters();
  const [activeTab, setActiveTab] = useState<"underpackaged" | "overpackaged">(
    (filters.videoType as "underpackaged" | "overpackaged") || "underpackaged",
  );
  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [sortField, setSortField] = useState<SortField>("primary_score");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  useEffect(() => {
    const initialTab = (location.state as { tab?: "underpackaged" | "overpackaged" } | null | undefined)?.tab;
    if (initialTab) {
      setActiveTab(initialTab);
      return;
    }
    if (filters.videoType === "underpackaged" || filters.videoType === "overpackaged") {
      setActiveTab(filters.videoType);
    }
  }, [filters.videoType, location.state]);

  const listQuery = useMemo(() => buildDashboardQuery(filters, { limit: 250, video_type: activeTab }), [filters, activeTab]);
  const { data, loading, error } = useDashboardQuery<{ items: VideoRow[] }>(
    activeTab === "underpackaged"
      ? "/api/dashboard/videos"
      : "/api/dashboard/videos",
    listQuery,
  );
  const items = data?.items ?? [];

  const selectedRow = useMemo(
    () => items.find((row) => row.video_id === selectedVideoId) ?? null,
    [items, selectedVideoId],
  );

  const detailQuery = useMemo(
    () => buildDashboardQuery(filters, { video_id: selectedVideoId ?? "" }),
    [filters, selectedVideoId],
  );
  const { data: detailData, loading: detailLoading } = useDashboardQuery<VideoDetailResponse>(
    selectedVideoId ? "/api/dashboard/video-detail" : "/api/dashboard/video-detail",
    detailQuery,
  );

  useEffect(() => {
    if (selectedVideoId && !items.some((row) => row.video_id === selectedVideoId)) {
      setSelectedVideoId(items[0]?.video_id ?? null);
    }
  }, [items, selectedVideoId]);

  const sortedItems = useMemo(() => {
    return [...items].sort((left, right) => {
      const leftValue =
        sortField === "primary_score"
          ? getPrimaryScore(left, activeTab)
          : sortField === "momentum_score"
            ? left.momentum_score ?? 0
            : sortField === "age_days"
              ? left.age_days ?? 0
              : left.ratio_d7 ?? 0;
      const rightValue =
        sortField === "primary_score"
          ? getPrimaryScore(right, activeTab)
          : sortField === "momentum_score"
            ? right.momentum_score ?? 0
            : sortField === "age_days"
              ? right.age_days ?? 0
              : right.ratio_d7 ?? 0;
      return sortDirection === "desc" ? rightValue - leftValue : leftValue - rightValue;
    });
  }, [activeTab, items, sortDirection, sortField]);

  const onSort = (field: SortField) => {
    if (field === sortField) {
      setSortDirection((current) => (current === "desc" ? "asc" : "desc"));
      return;
    }
    setSortField(field);
    setSortDirection("desc");
  };

  const handleSelect = (row: VideoRow) => {
    setSelectedVideoId(row.video_id);
    setSheetOpen(true);
    setFilters({
      ...filters,
      channelHandle: row.channel_handle,
      niche: row.channel_niche || filters.niche,
      videoType: activeTab,
    });
  };

  const openTab = (tab: "underpackaged" | "overpackaged") => {
    setActiveTab(tab);
    setSortField("primary_score");
    setSortDirection("desc");
    setFilters({ ...filters, videoType: tab });
  };

  return (
    <div className="h-[calc(100vh-180px)] overflow-auto px-4 pt-4 pb-6">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Tabs value={activeTab} onValueChange={(value) => openTab(value as "underpackaged" | "overpackaged")}>
            <TabsList>
              <TabsTrigger value="underpackaged">Underpackaged</TabsTrigger>
              <TabsTrigger value="overpackaged">Overpackaged</TabsTrigger>
            </TabsList>
          </Tabs>

          <div className="flex items-center gap-2 text-xs">
            <button
              type="button"
              onClick={() => onSort("primary_score")}
              className={sortField === "primary_score" ? "text-primary" : "text-muted-foreground"}
            >
              Primary
            </button>
            <button
              type="button"
              onClick={() => onSort("momentum_score")}
              className={sortField === "momentum_score" ? "text-primary" : "text-muted-foreground"}
            >
              Momentum
            </button>
            <button
              type="button"
              onClick={() => onSort("age_days")}
              className={sortField === "age_days" ? "text-primary" : "text-muted-foreground"}
            >
              Age
            </button>
          </div>
        </div>

        <section className="rounded-xl border border-border bg-card">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div>
              <h2 className="text-sm text-foreground">
                {activeTab === "underpackaged" ? "Underpackaged opportunities" : "Overpackaged videos"}
              </h2>
              <p className="text-xs text-muted-foreground">
                Rows are sorted by opportunity score and filtered by the global dashboard state.
              </p>
            </div>
          </div>

          {loading ? (
            <div className="flex min-h-[18rem] items-center justify-center p-4">
              <Spinner />
            </div>
          ) : error ? (
            <div className="p-4 text-sm text-critical">{error}</div>
          ) : sortedItems.length === 0 ? (
            <div className="p-4 text-sm text-muted-foreground">No videos match the current filters.</div>
          ) : (
            <div className="overflow-hidden">
              <table className="w-full">
                <thead className="border-b border-border bg-muted/40 text-[10px] uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2 text-left">Title</th>
                    <th className="px-4 py-2 text-left">Channel</th>
                    <th className="px-4 py-2 text-left">Niche</th>
                    <th className="px-4 py-2 text-left">Age</th>
                    <th className="px-4 py-2 text-left">Packaging</th>
                    <th className="px-4 py-2 text-left">Momentum</th>
                    <th className="px-4 py-2 text-left">D1 / D3 / D7 / D15</th>
                    <th className="px-4 py-2 text-left">Opportunity</th>
                    <th className="px-4 py-2 text-left">Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedItems.map((row) => (
                    <tr
                      key={row.video_id}
                      onClick={() => handleSelect(row)}
                      className="cursor-pointer border-b border-border transition hover:bg-muted/30"
                    >
                      <td className="px-4 py-3">
                        <div className="max-w-[320px] truncate text-sm text-foreground">{row.title}</div>
                        <div className="mt-1 text-[10px] uppercase tracking-wide text-muted-foreground">
                          {titleCase(filters.analysisWindow ? `${filters.analysisWindow} day window` : "Latest")}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">{row.channel_handle}</td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">{row.channel_niche || "Uncategorized"}</td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">{formatAgeDays(row.age_days)}</td>
                      <td className="px-4 py-3">
                        <div className="w-24">
                          <ScoreBar score={row.packaging_score ?? 0} variant={activeTab === "underpackaged" ? "caution" : "positive"} />
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="w-24">
                          <ScoreBar score={row.momentum_score ?? 0} variant={activeTab === "underpackaged" ? "positive" : "critical"} />
                        </div>
                      </td>
                      <td className="px-4 py-3 text-[11px] text-muted-foreground">
                        {formatScore(row.ratio_d1)} / {formatScore(row.ratio_d3)} / {formatScore(row.ratio_d7)} / {formatScore(row.ratio_d15)}
                      </td>
                      <td className="px-4 py-3">
                        <StatusChip status={getType(row, activeTab)} variant={activeTab === "underpackaged" ? "positive" : "caution"} />
                      </td>
                      <td className="px-4 py-3">
                        <ConfidenceBadge confidence={getConfidence(row, activeTab)} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent side="right" className="w-full overflow-y-auto border-border bg-card sm:max-w-xl">
          <SheetHeader>
            <SheetTitle>Video detail</SheetTitle>
            <SheetDescription>Packaging, momentum, ratios, and the latest performance snapshot.</SheetDescription>
          </SheetHeader>

          {!selectedRow ? (
            <div className="px-4 pb-4 text-sm text-muted-foreground">Select a video to inspect its full detail panel.</div>
          ) : detailLoading ? (
            <div className="flex min-h-[16rem] items-center justify-center px-4 pb-4">
              <Spinner />
            </div>
          ) : (
            <div className="space-y-4 px-4 pb-6">
              <div className="rounded-lg border border-border bg-background/40 p-3">
                <div className="text-base text-foreground">{selectedRow.title}</div>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <span>{selectedRow.channel_handle}</span>
                  <span>{selectedRow.channel_niche || "Uncategorized"}</span>
                  <span>{formatAgeDays(selectedRow.age_days)}</span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <StatusChip status={getType(selectedRow, activeTab)} variant={activeTab === "underpackaged" ? "positive" : "caution"} />
                  <StatusChip status={selectedRow.performance_label || "unclassified"} variant={activeTab === "underpackaged" ? "positive" : "caution"} />
                  <ConfidenceBadge confidence={getConfidence(selectedRow, activeTab)} />
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-lg border border-border bg-background/40 p-3">
                  <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Packaging score</div>
                  <div className="mt-1 text-lg text-foreground">{formatScore(selectedRow.packaging_score)}</div>
                  <ScoreBar score={selectedRow.packaging_score ?? 0} variant={activeTab === "underpackaged" ? "caution" : "positive"} />
                </div>
                <div className="rounded-lg border border-border bg-background/40 p-3">
                  <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Momentum score</div>
                  <div className="mt-1 text-lg text-foreground">{formatScore(selectedRow.momentum_score)}</div>
                  <ScoreBar score={selectedRow.momentum_score ?? 0} variant={activeTab === "underpackaged" ? "positive" : "critical"} />
                </div>
              </div>

              <div className="rounded-lg border border-border bg-background/40 p-3">
                <div className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Ratios</div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <div className="text-xs text-muted-foreground">D1</div>
                    <div className="text-sm text-foreground">{formatScore(selectedRow.ratio_d1)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">D3</div>
                    <div className="text-sm text-foreground">{formatScore(selectedRow.ratio_d3)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">D7</div>
                    <div className="text-sm text-foreground">{formatScore(selectedRow.ratio_d7)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">D15</div>
                    <div className="text-sm text-foreground">{formatScore(selectedRow.ratio_d15)}</div>
                  </div>
                </div>
              </div>

              <div className="rounded-lg border border-border bg-background/40 p-3">
                <div className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Performance snapshot</div>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Performance label</span>
                    <span className="text-foreground">{selectedRow.performance_label || "unclassified"}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Current published date</span>
                    <span className="text-foreground">{selectedRow.published_at ? selectedRow.published_at.slice(0, 10) : "—"}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Title clusters</span>
                    <span className="text-foreground">{detailData?.row?.topic_clusters?.length ?? 0}</span>
                  </div>
                </div>
              </div>

              {activeTab === "underpackaged" && (selectedRow.momentum_score ?? 0) > 0.85 ? (
                <div className="rounded-lg border border-positive/30 bg-positive/10 p-3 text-xs text-positive-foreground">
                  Strong underpackaging signal. High momentum with weak packaging suggests a clean replication target.
                </div>
              ) : null}

              {activeTab === "overpackaged" && (selectedRow.packaging_score ?? 0) > 0.85 && (selectedRow.momentum_score ?? 0) < 0.35 ? (
                <div className="rounded-lg border border-caution/30 bg-caution/10 p-3 text-xs text-caution-foreground">
                  Promise-delivery mismatch. High packaging with weak momentum suggests the content did not deliver.
                </div>
              ) : null}

              <div className="rounded-lg border border-border bg-background/40 p-3">
                <div className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Supporting data</div>
                <div className="space-y-2">
                  {detailData?.row ? (
                    <div className="text-sm text-muted-foreground">
                      {detailData.row.view_count ? `${detailData.row.view_count.toLocaleString()} views` : "No view count available"} ·{" "}
                      {detailData.row.like_count ? `${detailData.row.like_count.toLocaleString()} likes` : "No likes data"} ·{" "}
                      {detailData.row.comment_count ? `${detailData.row.comment_count.toLocaleString()} comments` : "No comments data"}
                    </div>
                  ) : (
                    <div className="text-sm text-muted-foreground">No detail payload returned yet.</div>
                  )}
                </div>
              </div>

              <div className="rounded-lg border border-border bg-background/40 p-3">
                <div className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Topic clusters</div>
                <div className="flex flex-wrap gap-2">
                  {(detailData?.row?.topic_clusters ?? []).length === 0 ? (
                    <div className="text-sm text-muted-foreground">No topics were attached to this video.</div>
                  ) : (
                    (detailData?.row?.topic_clusters ?? []).map((topic) => (
                      <StatusChip key={topic} status={topic} variant="neutral" />
                    ))
                  )}
                </div>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
