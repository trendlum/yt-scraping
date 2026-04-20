import { createContext, useContext, useState, ReactNode } from 'react';

interface Filters {
  analysisWindow: string;
  analysisDate: string;
  niche: string;
  channelHandle: string;
  topicCluster: string;
  nicheGrowthStatus: string;
  channelGrowthStatus: string;
  topicType: string;
  performanceLabel: string;
  videoType: string;
  sampleConfidence: string;
  minSampleThreshold: string;
}

interface FilterContextType {
  filters: Filters;
  setFilters: (filters: Filters) => void;
  resetFilters: () => void;
}

const defaultFilters: Filters = {
  analysisWindow: '30',
  analysisDate: '2026-04-20',
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
  const [filters, setFilters] = useState<Filters>(defaultFilters);

  const resetFilters = () => {
    setFilters(defaultFilters);
  };

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
