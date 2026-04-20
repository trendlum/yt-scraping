import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import type { DashboardFiltersState } from '../lib/dashboard';

interface FilterContextType {
  filters: DashboardFiltersState;
  setFilters: (filters: DashboardFiltersState) => void;
  resetFilters: () => void;
}

const defaultFilters: DashboardFiltersState = {
  analysisWindow: '30',
  analysisDate: '',
  niche: '',
  channelHandle: '',
  topicCluster: '',
  nicheGrowthStatus: '',
  channelGrowthStatus: '',
  topicType: '',
  performanceLabel: '',
  videoType: '',
  sampleConfidence: '',
  minSampleThreshold: '',
};

const FilterContext = createContext<FilterContextType | undefined>(undefined);

export function FilterProvider({ children }: { children: ReactNode }) {
  const [filters, setFilters] = useState<DashboardFiltersState>(defaultFilters);

  const resetFilters = () => {
    setFilters(defaultFilters);
  };

  useEffect(() => {
    if (filters.analysisDate) {
      return;
    }

    const controller = new AbortController();

    fetch('/api/dashboard/meta', { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error('Failed to load dashboard metadata');
        }
        return response.json();
      })
      .then((payload) => {
        if (!controller.signal.aborted && payload?.latest_analysis_date) {
          setFilters((current) =>
            current.analysisDate ? current : { ...current, analysisDate: payload.latest_analysis_date }
          );
        }
      })
      .catch(() => {
        // Keep the UI usable if metadata cannot be resolved yet.
      });

    return () => controller.abort();
  }, [filters.analysisDate]);

  return (
    <FilterContext.Provider value={{ filters, setFilters, resetFilters }}>
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
