import { useFilters } from '../contexts/FilterContext';

export function GlobalFilterBar() {
  const { filters, setFilters, resetFilters, meta } = useFilters();
  const windowOptions = meta?.available_window_days?.length ? meta.available_window_days : [30, 60, 90];
  const nicheStatusOptions =
    meta?.niche_growth_status_options?.length
      ? meta.niche_growth_status_options
      : [
          "fast_emerging",
          "early_rising",
          "watchlist",
          "weak_early_signal",
          "confirmed_growing",
          "confirmed_emerging",
          "confirmed_stable",
          "confirmed_volatile",
          "confirmed_declining",
        ];
  const channelStatusOptions =
    meta?.channel_growth_status_options?.length
      ? meta.channel_growth_status_options
      : [
          "algorithmic_shift",
          "improving_packaging",
          "improving_sustainability",
          "stable_improving",
          "stable_flat",
          "volatile",
          "structural_decline",
        ];
  const topicTypeOptions =
    meta?.topic_type_options?.length
      ? meta.topic_type_options
      : [
          "replicable",
          "sustained_traction",
          "algorithmic",
          "slow_burner",
          "fragile",
          "deceptive_packaging",
        ];
  const performanceLabelOptions =
    meta?.performance_label_options?.length
      ? meta.performance_label_options
      : ["explosive", "strong", "solid", "underperforming", "weak", "declining"];

  return (
    <div className="sticky top-[49px] z-40 border-b border-border bg-card/95 backdrop-blur">
      <div className="px-6 py-2.5">
        <div className="flex flex-wrap items-center gap-2">
          <select
            className="bg-input border border-border rounded px-2.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
            value={filters.analysisWindow}
            onChange={(e) => setFilters({ ...filters, analysisWindow: e.target.value })}
          >
            {windowOptions.map((windowDays) => (
              <option key={windowDays} value={String(windowDays)}>
                {windowDays} days
              </option>
            ))}
          </select>

          <input
            type="text"
            placeholder="Niche"
            className="bg-input border border-border rounded px-2.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-primary w-28 text-foreground placeholder:text-muted-foreground"
            value={filters.niche}
            onChange={(e) => setFilters({ ...filters, niche: e.target.value })}
          />

          <input
            type="text"
            placeholder="Channel handle"
            className="bg-input border border-border rounded px-2.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-primary w-32 text-foreground placeholder:text-muted-foreground"
            value={filters.channelHandle}
            onChange={(e) => setFilters({ ...filters, channelHandle: e.target.value })}
          />

          <input
            type="text"
            placeholder="Topic cluster"
            className="bg-input border border-border rounded px-2.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-primary w-32 text-foreground placeholder:text-muted-foreground"
            value={filters.topicCluster}
            onChange={(e) => setFilters({ ...filters, topicCluster: e.target.value })}
          />

          <select
            className="bg-input border border-border rounded px-2.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
            value={filters.nicheGrowthStatus}
            onChange={(e) => setFilters({ ...filters, nicheGrowthStatus: e.target.value })}
          >
            <option value="">Niche status</option>
            {nicheStatusOptions.map((option) => (
              <option key={option} value={option}>
                {option.replace(/_/g, ' ')}
              </option>
            ))}
          </select>

          <select
            className="bg-input border border-border rounded px-2.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
            value={filters.channelGrowthStatus}
            onChange={(e) => setFilters({ ...filters, channelGrowthStatus: e.target.value })}
          >
            <option value="">Channel status</option>
            {channelStatusOptions.map((option) => (
              <option key={option} value={option}>
                {option.replace(/_/g, ' ')}
              </option>
            ))}
          </select>

          <select
            className="bg-input border border-border rounded px-2.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
            value={filters.topicType}
            onChange={(e) => setFilters({ ...filters, topicType: e.target.value })}
          >
            <option value="">Topic type</option>
            {topicTypeOptions.map((option) => (
              <option key={option} value={option}>
                {option.replace(/_/g, ' ')}
              </option>
            ))}
          </select>

          <select
            className="bg-input border border-border rounded px-2.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
            value={filters.performanceLabel}
            onChange={(e) => setFilters({ ...filters, performanceLabel: e.target.value })}
          >
            <option value="">Performance label</option>
            {performanceLabelOptions.map((option) => (
              <option key={option} value={option}>
                {option.replace(/_/g, ' ')}
              </option>
            ))}
          </select>

          <select
            className="bg-input border border-border rounded px-2.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
            value={filters.videoType}
            onChange={(e) => setFilters({ ...filters, videoType: e.target.value })}
          >
            <option value="">Video type</option>
            <option value="underpackaged">Underpackaged</option>
            <option value="overpackaged">Overpackaged</option>
          </select>

          <select
            className="bg-input border border-border rounded px-2.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
            value={filters.sampleConfidence}
            onChange={(e) => setFilters({ ...filters, sampleConfidence: e.target.value })}
          >
            <option value="">Confidence</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          <input
            type="number"
            min="0"
            step="1"
            placeholder="Min sample"
            className="bg-input border border-border rounded px-2.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-primary w-24 text-foreground placeholder:text-muted-foreground"
            value={filters.minSampleThreshold}
            onChange={(e) => setFilters({ ...filters, minSampleThreshold: e.target.value })}
          />

          <button
            className="ml-auto text-xs text-muted-foreground hover:text-primary transition"
            onClick={resetFilters}
          >
            Reset
          </button>
        </div>
      </div>
    </div>
  );
}
