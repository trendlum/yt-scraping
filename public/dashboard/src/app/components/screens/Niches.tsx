import { useState, useEffect, useMemo } from 'react';
import { useLocation } from 'react-router';
import { useFilters } from '../../contexts/FilterContext';
import { StatusChip } from '../ui/StatusChip';
import { ConfidenceBadge } from '../ui/ConfidenceBadge';
import { ScoreBar } from '../ui/ScoreBar';
import { Sparkline } from '../ui/Sparkline';

interface Niche {
  id: string;
  niche: string;
  growthStatus: string;
  earlyScore: number;
  confirmedScore: number;
  confidence: 'high' | 'medium' | 'low';
  distinctChannels: number;
  totalVideos: number;
  trend: number[];
  sampleSize: number;
  recentChannels: string[];
  topTopics: string[];
}

export function Niches() {
  const location = useLocation();
  const { filters } = useFilters();
  const [selectedNiche, setSelectedNiche] = useState<Niche | null>(null);
  const [sortField, setSortField] = useState<'earlyScore' | 'confirmedScore'>('earlyScore');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  const niches: Niche[] = [
    {
      id: '1',
      niche: 'us iran geopolitics',
      growthStatus: 'fast_emerging',
      earlyScore: 0.82,
      confirmedScore: 0.74,
      confidence: 'high',
      distinctChannels: 11,
      totalVideos: 48,
      trend: [0.45, 0.52, 0.61, 0.68, 0.74, 0.82],
      sampleSize: 48,
      recentChannels: ['@MeidasTouch', '@TheGeoNetwork', '@BrianTylerCohen'],
      topTopics: ['trump foreign policy', 'middle east escalation', 'iran nuclear deal'],
    },
    {
      id: '2',
      niche: 'bitcoin etf flows',
      growthStatus: 'confirmed',
      earlyScore: 0.76,
      confirmedScore: 0.81,
      confidence: 'high',
      distinctChannels: 14,
      totalVideos: 62,
      trend: [0.68, 0.71, 0.73, 0.76, 0.79, 0.81],
      sampleSize: 62,
      recentChannels: ['@CoinBureauFinance', '@CryptosRUs', '@AltcoinDaily'],
      topTopics: ['bitcoin etf inflows', 'institutional adoption', 'etf approval impact'],
    },
    {
      id: '3',
      niche: 'spanish housing market',
      growthStatus: 'fast_emerging',
      earlyScore: 0.71,
      confirmedScore: 0.65,
      confidence: 'medium',
      distinctChannels: 7,
      totalVideos: 31,
      trend: [0.42, 0.48, 0.55, 0.61, 0.65, 0.71],
      sampleSize: 31,
      recentChannels: ['@EconomicsExplained', '@MoneyMacro', '@RealEstate'],
      topTopics: ['spanish property prices', 'barcelona housing crisis', 'european real estate'],
    },
    {
      id: '4',
      niche: 'ai agent frameworks',
      growthStatus: 'fast_emerging',
      earlyScore: 0.88,
      confirmedScore: 0.69,
      confidence: 'medium',
      distinctChannels: 9,
      totalVideos: 37,
      trend: [0.51, 0.58, 0.63, 0.72, 0.81, 0.88],
      sampleSize: 37,
      recentChannels: ['@TwoMinutePapers', '@YannicKilcher', '@AIExplained'],
      topTopics: ['langchain tutorials', 'autonomous agents', 'ai coding assistants'],
    },
    {
      id: '5',
      niche: 'south china sea tensions',
      growthStatus: 'confirmed',
      earlyScore: 0.73,
      confirmedScore: 0.78,
      confidence: 'high',
      distinctChannels: 10,
      totalVideos: 44,
      trend: [0.65, 0.68, 0.71, 0.74, 0.76, 0.78],
      sampleSize: 44,
      recentChannels: ['@TheGeoNetwork', '@CaspianReport', '@PolyMatter'],
      topTopics: ['china taiwan conflict', 'philippines dispute', 'us china military'],
    },
  ];

  const filteredNiches = useMemo(() => {
    return niches.filter(niche => {
      if (filters.niche && !niche.niche.toLowerCase().includes(filters.niche.toLowerCase())) {
        return false;
      }
      if (filters.nicheGrowthStatus && niche.growthStatus !== filters.nicheGrowthStatus) {
        return false;
      }
      if (filters.sampleConfidence && niche.confidence !== filters.sampleConfidence) {
        return false;
      }
      return true;
    });
  }, [niches, filters]);

  const sortedNiches = [...filteredNiches].sort((a, b) => {
    const aVal = a[sortField];
    const bVal = b[sortField];
    return sortDirection === 'desc' ? bVal - aVal : aVal - bVal;
  });

  const totalPages = Math.ceil(sortedNiches.length / itemsPerPage);
  const paginatedNiches = sortedNiches.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const handleSort = (field: 'earlyScore' | 'confirmedScore') => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'desc' ? 'asc' : 'desc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  useEffect(() => {
    if (location.state?.selectedId) {
      const niche = niches.find(n => n.id === location.state.selectedId);
      if (niche) {
        setSelectedNiche(niche);
      }
    }
  }, [location.state]);

  return (
    <div className="h-[calc(100vh-180px)] overflow-auto px-4 pt-4 pb-0">
      <div className={selectedNiche ? '' : 'pb-4'}>
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h2 className="text-sm text-foreground font-medium">Niche Rankings</h2>
            <div className="flex items-center gap-2 text-xs">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="px-2 py-1 text-muted-foreground hover:text-primary disabled:opacity-30 disabled:cursor-not-allowed"
              >
                ←
              </button>
              <span className="text-muted-foreground">
                {currentPage} / {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                disabled={currentPage === totalPages}
                className="px-2 py-1 text-muted-foreground hover:text-primary disabled:opacity-30 disabled:cursor-not-allowed"
              >
                →
              </button>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-muted-foreground">Comparison:</span>
            <button
              className={`px-2.5 py-1 rounded ${sortField === 'earlyScore' ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:text-primary'}`}
              onClick={() => handleSort('earlyScore')}
            >
              Early signal
            </button>
            <button
              className={`px-2.5 py-1 rounded ${sortField === 'confirmedScore' ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:text-primary'}`}
              onClick={() => handleSort('confirmedScore')}
            >
              Confirmed
            </button>
          </div>
        </div>

        <div className="bg-card border border-border rounded-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-muted border-b border-border">
              <tr className="text-[10px] text-muted-foreground uppercase tracking-wide">
                <th className="text-left px-3 py-2">Niche</th>
                <th className="text-left px-3 py-2">Status</th>
                <th className="text-left px-3 py-2 cursor-pointer hover:text-primary" onClick={() => handleSort('earlyScore')}>
                  Early Score {sortField === 'earlyScore' && (sortDirection === 'desc' ? '↓' : '↑')}
                </th>
                <th className="text-left px-3 py-2 cursor-pointer hover:text-primary" onClick={() => handleSort('confirmedScore')}>
                  Confirmed Score {sortField === 'confirmedScore' && (sortDirection === 'desc' ? '↓' : '↑')}
                </th>
                <th className="text-left px-3 py-2">Confidence</th>
                <th className="text-left px-3 py-2">Channels</th>
                <th className="text-left px-3 py-2">Videos</th>
                <th className="text-left px-3 py-2">Trend</th>
              </tr>
            </thead>
            <tbody>
              {paginatedNiches.map((niche) => (
                <tr
                  key={niche.id}
                  className={`border-b border-border hover:bg-muted/50 cursor-pointer transition ${selectedNiche?.id === niche.id ? 'bg-primary/5' : ''}`}
                  onClick={() => setSelectedNiche(niche)}
                >
                  <td className="px-3 py-2.5 text-sm text-foreground">{niche.niche}</td>
                  <td className="px-3 py-2.5">
                    <StatusChip status={niche.growthStatus} variant="positive" />
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="w-28">
                      <ScoreBar score={niche.earlyScore} variant="positive" />
                    </div>
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="w-28">
                      <ScoreBar score={niche.confirmedScore} variant="positive" />
                    </div>
                  </td>
                  <td className="px-3 py-2.5">
                    <ConfidenceBadge confidence={niche.confidence} />
                  </td>
                  <td className="px-3 py-2.5 text-xs text-muted-foreground">{niche.distinctChannels}</td>
                  <td className="px-3 py-2.5 text-xs text-muted-foreground">{niche.totalVideos}</td>
                  <td className="px-3 py-2.5">
                    <Sparkline data={niche.trend} variant="positive" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {selectedNiche && (
          <div className="mt-4 bg-card border border-border rounded-lg p-4">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="mb-2 text-sm text-foreground">{selectedNiche.niche}</h3>
                <div className="flex items-center gap-2">
                  <StatusChip status={selectedNiche.growthStatus} variant="positive" />
                  <ConfidenceBadge confidence={selectedNiche.confidence} />
                </div>
              </div>
              <button
                onClick={() => setSelectedNiche(null)}
                className="text-muted-foreground hover:text-primary text-sm"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-4 gap-6">
              <div>
                <h4 className="text-xs text-muted-foreground mb-2 uppercase tracking-wide">Score Comparison</h4>
                <div className="space-y-3">
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Early signal score</div>
                    <ScoreBar score={selectedNiche.earlyScore} variant="positive" />
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Confirmed growth score</div>
                    <ScoreBar score={selectedNiche.confirmedScore} variant="positive" />
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-xs text-muted-foreground mb-2 uppercase tracking-wide">Trend Analysis</h4>
                <div className="bg-muted/30 rounded p-4 flex items-center justify-center">
                  <Sparkline data={selectedNiche.trend} variant="positive" />
                </div>
                <div className="mt-2 text-xs text-muted-foreground">
                  Growth trajectory over last 30 days
                </div>
              </div>

              <div>
                <h4 className="text-xs text-muted-foreground mb-2 uppercase tracking-wide">Sample Details</h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <div className="text-muted-foreground mb-1">Sample size</div>
                    <div>{selectedNiche.sampleSize} videos</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground mb-1">Distinct channels</div>
                    <div>{selectedNiche.distinctChannels}</div>
                  </div>
                </div>
                {selectedNiche.confidence === 'low' && (
                  <div className="mt-3 p-3 bg-caution/10 border border-caution/30 rounded text-xs text-caution-foreground">
                    ⚠️ Low sample size may affect accuracy
                  </div>
                )}
              </div>

              <div>
                <h4 className="text-xs text-muted-foreground mb-2 uppercase tracking-wide">Active Channels</h4>
                <div className="space-y-2">
                  {selectedNiche.recentChannels.map((channel) => (
                    <div key={channel} className="text-sm bg-muted/30 rounded px-3 py-2">
                      {channel}
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="text-xs text-muted-foreground mb-2 uppercase tracking-wide">Top Topics</h4>
                <div className="space-y-2">
                  {selectedNiche.topTopics.map((topic) => (
                    <div key={topic} className="text-sm bg-muted/30 rounded px-3 py-2">
                      {topic}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
