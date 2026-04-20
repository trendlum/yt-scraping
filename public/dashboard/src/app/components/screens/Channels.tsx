import { useState, useEffect, useMemo } from 'react';
import { useLocation } from 'react-router';
import { useFilters } from '../../contexts/FilterContext';
import { StatusChip } from '../ui/StatusChip';
import { ScoreBar } from '../ui/ScoreBar';
import { DeltaPill } from '../ui/DeltaPill';

interface Channel {
  id: string;
  channel: string;
  niche: string;
  growthStatus: string;
  growthScore: number;
  packagingScore: number;
  sustainabilityScore: number;
  algorithmicShiftScore: number;
  volatilityScore: number;
  deltaOverall: number;
  recentPeriod: {
    avgViews: number;
    avgEngagement: number;
    videoCount: number;
  };
  previousPeriod: {
    avgViews: number;
    avgEngagement: number;
    videoCount: number;
  };
}

export function Channels() {
  const location = useLocation();
  const { filters } = useFilters();
  const [selectedChannel, setSelectedChannel] = useState<Channel | null>(null);
  const [sortField, setSortField] = useState<keyof Channel>('growthScore');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  const channels: Channel[] = [
    {
      id: '1',
      channel: '@MeidasTouch',
      niche: 'politics',
      growthStatus: 'algorithmic_shift',
      growthScore: 0.79,
      packagingScore: 0.72,
      sustainabilityScore: 0.68,
      algorithmicShiftScore: 0.85,
      volatilityScore: 0.22,
      deltaOverall: 0.18,
      recentPeriod: {
        avgViews: 245000,
        avgEngagement: 0.068,
        videoCount: 28,
      },
      previousPeriod: {
        avgViews: 187000,
        avgEngagement: 0.055,
        videoCount: 24,
      },
    },
    {
      id: '2',
      channel: '@CoinBureauFinance',
      niche: 'crypto analysis',
      growthStatus: 'improving',
      growthScore: 0.74,
      packagingScore: 0.81,
      sustainabilityScore: 0.76,
      algorithmicShiftScore: 0.45,
      volatilityScore: 0.31,
      deltaOverall: 0.12,
      recentPeriod: {
        avgViews: 312000,
        avgEngagement: 0.074,
        videoCount: 18,
      },
      previousPeriod: {
        avgViews: 289000,
        avgEngagement: 0.069,
        videoCount: 16,
      },
    },
    {
      id: '3',
      channel: '@TheGeoNetwork',
      niche: 'geopolitics',
      growthStatus: 'improving',
      growthScore: 0.68,
      packagingScore: 0.65,
      sustainabilityScore: 0.72,
      algorithmicShiftScore: 0.38,
      volatilityScore: 0.19,
      deltaOverall: 0.09,
      recentPeriod: {
        avgViews: 158000,
        avgEngagement: 0.061,
        videoCount: 22,
      },
      previousPeriod: {
        avgViews: 142000,
        avgEngagement: 0.058,
        videoCount: 20,
      },
    },
    {
      id: '4',
      channel: '@TwoMinutePapers',
      niche: 'ai research',
      growthStatus: 'improving',
      growthScore: 0.82,
      packagingScore: 0.88,
      sustainabilityScore: 0.91,
      algorithmicShiftScore: 0.52,
      volatilityScore: 0.12,
      deltaOverall: 0.15,
      recentPeriod: {
        avgViews: 428000,
        avgEngagement: 0.082,
        videoCount: 15,
      },
      previousPeriod: {
        avgViews: 376000,
        avgEngagement: 0.078,
        videoCount: 14,
      },
    },
  ];

  const filteredChannels = useMemo(() => {
    return channels.filter(channel => {
      if (filters.channelHandle && !channel.channel.toLowerCase().includes(filters.channelHandle.toLowerCase())) {
        return false;
      }
      if (filters.niche && !channel.niche.toLowerCase().includes(filters.niche.toLowerCase())) {
        return false;
      }
      if (filters.channelGrowthStatus && channel.growthStatus !== filters.channelGrowthStatus) {
        return false;
      }
      return true;
    });
  }, [channels, filters]);

  const sortedChannels = [...filteredChannels].sort((a, b) => {
    const aVal = a[sortField];
    const bVal = b[sortField];
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return sortDirection === 'desc' ? bVal - aVal : aVal - bVal;
    }
    return 0;
  });

  const totalPages = Math.ceil(sortedChannels.length / itemsPerPage);
  const paginatedChannels = sortedChannels.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const handleSort = (field: keyof Channel) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'desc' ? 'asc' : 'desc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  useEffect(() => {
    if (location.state?.selectedId) {
      const channel = channels.find(c => c.id === location.state.selectedId);
      if (channel) {
        setSelectedChannel(channel);
      }
    }
  }, [location.state]);

  return (
    <div className="h-[calc(100vh-180px)] overflow-auto px-4 pt-4 pb-0">
      <div className={selectedChannel ? '' : 'pb-4'}>
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h2 className="text-sm text-foreground font-medium">Channel Rankings</h2>
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
        </div>

        <div className="bg-card border border-border rounded-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-muted border-b border-border">
              <tr className="text-[10px] text-muted-foreground uppercase tracking-wide">
                <th className="text-left px-3 py-2">Channel</th>
                <th className="text-left px-3 py-2">Niche</th>
                <th className="text-left px-3 py-2">Status</th>
                <th className="text-left px-3 py-2 cursor-pointer hover:text-primary" onClick={() => handleSort('growthScore')}>
                  Growth {sortField === 'growthScore' && (sortDirection === 'desc' ? '↓' : '↑')}
                </th>
                <th className="text-left px-3 py-2 cursor-pointer hover:text-primary" onClick={() => handleSort('packagingScore')}>
                  Packaging {sortField === 'packagingScore' && (sortDirection === 'desc' ? '↓' : '↑')}
                </th>
                <th className="text-left px-3 py-2 cursor-pointer hover:text-primary" onClick={() => handleSort('volatilityScore')}>
                  Volatility {sortField === 'volatilityScore' && (sortDirection === 'desc' ? '↓' : '↑')}
                </th>
                <th className="text-left px-3 py-2">Delta</th>
              </tr>
            </thead>
            <tbody>
              {paginatedChannels.map((channel) => (
                <tr
                  key={channel.id}
                  className={`border-b border-border hover:bg-muted/50 cursor-pointer transition ${selectedChannel?.id === channel.id ? 'bg-primary/5' : ''}`}
                  onClick={() => setSelectedChannel(channel)}
                >
                  <td className="px-3 py-2.5 text-sm text-foreground">{channel.channel}</td>
                  <td className="px-3 py-2.5 text-xs text-muted-foreground">{channel.niche}</td>
                  <td className="px-3 py-2.5">
                    <StatusChip status={channel.growthStatus} variant="positive" />
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="w-28">
                      <ScoreBar score={channel.growthScore} variant="positive" />
                    </div>
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="w-28">
                      <ScoreBar score={channel.packagingScore} variant="positive" />
                    </div>
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="w-28">
                      <ScoreBar score={channel.volatilityScore} variant="caution" />
                    </div>
                  </td>
                  <td className="px-3 py-2.5">
                    <DeltaPill value={channel.deltaOverall} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {selectedChannel && (
          <div className="mt-4 bg-card border border-border rounded-lg p-4">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="mb-2 text-sm text-foreground">{selectedChannel.channel}</h3>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">{selectedChannel.niche}</span>
                  <StatusChip status={selectedChannel.growthStatus} variant="positive" />
                </div>
              </div>
              <button
                onClick={() => setSelectedChannel(null)}
                className="text-muted-foreground hover:text-primary text-sm"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-3 gap-6">
              <div>
                <h4 className="text-xs text-muted-foreground mb-2 uppercase tracking-wide">Growth Metrics</h4>
                <div className="space-y-3">
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Overall growth score</div>
                    <ScoreBar score={selectedChannel.growthScore} variant="positive" />
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Packaging improvement</div>
                    <ScoreBar score={selectedChannel.packagingScore} variant="positive" />
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Sustainability</div>
                    <ScoreBar score={selectedChannel.sustainabilityScore} variant="positive" />
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Algorithmic shift</div>
                    <ScoreBar score={selectedChannel.algorithmicShiftScore} variant="positive" />
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Volatility</div>
                    <ScoreBar score={selectedChannel.volatilityScore} variant="caution" />
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-xs text-muted-foreground mb-2 uppercase tracking-wide">Recent vs Previous Window</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-xs text-muted-foreground mb-2">Recent Period</div>
                    <div className="space-y-2 text-sm">
                      <div>
                        <div className="text-muted-foreground">Avg views</div>
                        <div>{selectedChannel.recentPeriod.avgViews.toLocaleString()}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Engagement</div>
                        <div>{(selectedChannel.recentPeriod.avgEngagement * 100).toFixed(1)}%</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Videos</div>
                        <div>{selectedChannel.recentPeriod.videoCount}</div>
                      </div>
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-2">Previous Period</div>
                    <div className="space-y-2 text-sm">
                      <div>
                        <div className="text-muted-foreground">Avg views</div>
                        <div>{selectedChannel.previousPeriod.avgViews.toLocaleString()}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Engagement</div>
                        <div>{(selectedChannel.previousPeriod.avgEngagement * 100).toFixed(1)}%</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Videos</div>
                        <div>{selectedChannel.previousPeriod.videoCount}</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-xs text-muted-foreground mb-2 uppercase tracking-wide">Period Comparison</h4>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Views change</span>
                    <DeltaPill
                      value={Math.round(
                        ((selectedChannel.recentPeriod.avgViews - selectedChannel.previousPeriod.avgViews) /
                          selectedChannel.previousPeriod.avgViews) *
                          100
                      )}
                    />
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Engagement change</span>
                    <DeltaPill
                      value={Math.round(
                        ((selectedChannel.recentPeriod.avgEngagement - selectedChannel.previousPeriod.avgEngagement) /
                          selectedChannel.previousPeriod.avgEngagement) *
                          100
                      )}
                    />
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Output change</span>
                    <DeltaPill
                      value={selectedChannel.recentPeriod.videoCount - selectedChannel.previousPeriod.videoCount}
                    />
                  </div>
                </div>
              </div>
            </div>

            {selectedChannel.algorithmicShiftScore > 0.7 && (
              <div className="mt-4 p-3 bg-positive/10 border border-positive/30 rounded text-xs text-positive-foreground">
                ✓ Strong algorithmic shift detected. This channel may have found a new winning format.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
