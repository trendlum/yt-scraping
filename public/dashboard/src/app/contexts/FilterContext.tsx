import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import type { DashboardFiltersState, MetaResponse } from '../lib/dashboard';

interface FilterContextType {
  filters: DashboardFiltersState;
  setFilters: (filters: DashboardFiltersState) => void;
  resetFilters: () => void;
  meta: MetaResponse | null;
}

function createDefaultFilters(analysisWindow = '30'): DashboardFiltersState {
  return {
    analysisWindow,
    niche: '',
    channelHandle: '',
    topicCluster: '',
    nicheGrowthStatus: '',
    channelGrowthStatus: '',
    topicType: '',
    performanceLabel: '',
    videoType: '',
    sampleConfidence: '',
  };
}

const defaultFilters = createDefaultFilters();

const FilterContext = createContext<FilterContextType | undefined>(undefined);

export function FilterProvider({ children }: { children: ReactNode }) {
  const [filters, setFilters] = useState<DashboardFiltersState>(defaultFilters);
  const [meta, setMeta] = useState<MetaResponse | null>(null);

  const resetFilters = () => {
    setFilters(createDefaultFilters(String(meta?.default_window_days ?? 30)));
  };

  useEffect(() => {
    const controller = new AbortController();

    fetch('/api/dashboard/meta', { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error('Failed to load dashboard metadata');
        }
        return response.json();
      })
      .then((payload: MetaResponse) => {
        if (controller.signal.aborted) {
          return;
        }

        setMeta(payload);

        if (payload?.default_window_days && String(payload.default_window_days) !== defaultFilters.analysisWindow) {
          setFilters((current) =>
            current.analysisWindow === defaultFilters.analysisWindow
              ? { ...current, analysisWindow: String(payload.default_window_days) }
              : current
          );
        }
      })
      .catch(() => {
        // Keep the UI usable if metadata cannot be resolved yet.
      });

    return () => controller.abort();
  }, []);

  return (
    <FilterContext.Provider value={{ filters, setFilters, resetFilters, meta }}>
      {children}
    </FilterContext.Provider>
  );
}

export function useFilters() {
  const context = useContext(FilterContext);
  if (!context) {
    throw new Error('useFilters must be used within FilterProvider');
  }
  return context;
}
