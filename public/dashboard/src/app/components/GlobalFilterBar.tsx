import { useFilters } from '../contexts/FilterContext';

export function GlobalFilterBar() {
  const { filters, setFilters, resetFilters } = useFilters();

  return (
    <div className="sticky top-[49px] z-40 border-b border-border bg-card/95 backdrop-blur">
      <div className="px-6 py-2.5">
        <div className="flex flex-wrap items-center gap-2">
          <select
            className="bg-input border border-border rounded px-2.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
            value={filters.analysisWindow}
            onChange={(e) => setFilters({ ...filters, analysisWindow: e.target.value })}
          >
            <option value="30">30 days</option>
            <option value="60">60 days</option>
            <option value="90">90 days</option>
          </select>

          <input
            type="date"
            className="bg-input border border-border rounded px-2.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
            value={filters.analysisDate}
            onChange={(e) => setFilters({ ...filters, analysisDate: e.target.value })}
          />

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
            <option value="fast_emerging">Fast emerging</option>
            <option value="early_rising">Early rising</option>
            <option value="watchlist">Watchlist</option>
            <option value="weak_early_signal">Weak early signal</option>
            <option value="confirmed_growing">Confirmed growing</option>
            <option value="confirmed_emerging">Confirmed emerging</option>
            <option value="confirmed_stable">Confirmed stable</option>
            <option value="confirmed_volatile">Confirmed volatile</option>
            <option value="confirmed_declining">Confirmed declining</option>
          </select>

          <select
            className="bg-input border border-border rounded px-2.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
            value={filters.channelGrowthStatus}
            onChange={(e) => setFilters({ ...filters, channelGrowthStatus: e.target.value })}
          >
            <option value="">Channel status</option>
            <option value="algorithmic_shift">Algorithmic shift</option>
            <option value="improving_packaging">Improving packaging</option>
            <option value="improving_sustainability">Improving sustainability</option>
            <option value="stable_improving">Stable improving</option>
            <option value="stable_flat">Stable flat</option>
            <option value="volatile">Volatile</option>
            <option value="structural_decline">Structural decline</option>
          </select>

          <select
            className="bg-input border border-border rounded px-2.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
            value={filters.topicType}
            onChange={(e) => setFilters({ ...filters, topicType: e.target.value })}
          >
            <option value="">Topic type</option>
            <option value="replicable">Replicable</option>
            <option value="sustained_traction">Sustained traction</option>
            <option value="algorithmic">Algorithmic</option>
            <option value="slow_burner">Slow burner</option>
            <option value="fragile">Fragile</option>
            <option value="deceptive_packaging">Deceptive packaging</option>
          </select>

          <select
            className="bg-input border border-border rounded px-2.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
            value={filters.performanceLabel}
            onChange={(e) => setFilters({ ...filters, performanceLabel: e.target.value })}
          >
            <option value="">Performance label</option>
            <option value="explosive">Explosive</option>
            <option value="strong">Strong</option>
            <option value="solid">Solid</option>
            <option value="underperforming">Underperforming</option>
            <option value="weak">Weak</option>
            <option value="declining">Declining</option>
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
