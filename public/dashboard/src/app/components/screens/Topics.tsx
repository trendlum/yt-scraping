import { useState, useEffect, useMemo } from 'react';
import { useLocation } from 'react-router';
import { useFilters } from '../../contexts/FilterContext';
import { StatusChip } from '../ui/StatusChip';
import { ScoreBar } from '../ui/ScoreBar';

interface Topic {
  id: string;
  topicCluster: string;
  topicType: string;
  replicabilityScore: number;
  sustainedTractionScore: number;
  fragilityScore: number;
  distinctChannels: number;
  coveragePct: number;
  concentration: string;
  totalVideos: number;
  avgPerformance: number;
  topChannels: string[];
  recentExamples: string[];
}

export function Topics() {
  const location = useLocation();
  const { filters } = useFilters();
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);
  const [sortField, setSortField] = useState<keyof Topic>('replicabilityScore');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  const topics: Topic[] = [
    {
      id: '1',
      topicCluster: 'trump foreign policy',
      topicType: 'replicable',
      replicabilityScore: 0.86,
      sustainedTractionScore: 0.78,
      fragilityScore: 0.19,
      distinctChannels: 8,
      coveragePct: 72,
      concentration: 'distributed',
      totalVideos: 42,
      avgPerformance: 0.81,
      topChannels: ['@MeidasTouch', '@BrianTylerCohen', '@TheGeoNetwork'],
      recentExamples: [
        'Trump PANICS as Iran REJECTS ULTIMATUM',
        'The real reason Trump changed his foreign policy',
        'What Trump latest move means for global politics',
      ],
    },
    {
      id: '2',
      topicCluster: 'middle east escalation',
      topicType: 'replicable',
      replicabilityScore: 0.82,
      sustainedTractionScore: 0.84,
      fragilityScore: 0.15,
      distinctChannels: 12,
      coveragePct: 68,
      concentration: 'distributed',
      totalVideos: 51,
      avgPerformance: 0.79,
      topChannels: ['@TheGeoNetwork', '@CaspianReport', '@RealLifeLore'],
      recentExamples: [
        'Why the Middle East is on the brink of war',
        'The escalation nobody is talking about',
        'What happens next in the Middle East crisis',
      ],
    },
    {
      id: '3',
      topicCluster: 'political news commentary',
      topicType: 'sustained',
      replicabilityScore: 0.75,
      sustainedTractionScore: 0.91,
      fragilityScore: 0.08,
      distinctChannels: 15,
      coveragePct: 81,
      concentration: 'broad',
      totalVideos: 89,
      avgPerformance: 0.73,
      topChannels: ['@MeidasTouch', '@BrianTylerCohen', '@PoliticsNews'],
      recentExamples: [
        'Breaking: Major political shift announced',
        'The truth behind today headlines',
        'What the media is not telling you',
      ],
    },
    {
      id: '4',
      topicCluster: 'bitcoin etf analysis',
      topicType: 'replicable',
      replicabilityScore: 0.88,
      sustainedTractionScore: 0.76,
      fragilityScore: 0.22,
      distinctChannels: 9,
      coveragePct: 65,
      concentration: 'concentrated',
      totalVideos: 38,
      avgPerformance: 0.84,
      topChannels: ['@CoinBureauFinance', '@CryptosRUs', '@AltcoinDaily'],
      recentExamples: [
        'Bitcoin ETF flows reveal major institutional move',
        'Why ETF inflows are accelerating',
        'The ETF data nobody is watching',
      ],
    },
    {
      id: '5',
      topicCluster: 'ai agent frameworks',
      topicType: 'emerging',
      replicabilityScore: 0.79,
      sustainedTractionScore: 0.68,
      fragilityScore: 0.31,
      distinctChannels: 7,
      coveragePct: 58,
      concentration: 'concentrated',
      totalVideos: 29,
      avgPerformance: 0.77,
      topChannels: ['@TwoMinutePapers', '@YannicKilcher', '@AIExplained'],
      recentExamples: [
        'Building autonomous AI agents with LangChain',
        'The AI agent revolution is here',
        'How to create your own AI coding assistant',
      ],
    },
  ];

  const filteredTopics = useMemo(() => {
    return topics.filter(topic => {
      if (filters.topicCluster && !topic.topicCluster.toLowerCase().includes(filters.topicCluster.toLowerCase())) {
        return false;
      }
      if (filters.topicType && topic.topicType !== filters.topicType) {
        return false;
      }
      if (filters.niche) {
        const matchesNiche = topic.topChannels.some(channel =>
          channel.toLowerCase().includes(filters.niche.toLowerCase())
        );
        if (!matchesNiche) return false;
      }
      return true;
    });
  }, [topics, filters]);

  const sortedTopics = [...filteredTopics].sort((a, b) => {
    const aVal = a[sortField];
    const bVal = b[sortField];
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return sortDirection === 'desc' ? bVal - aVal : aVal - bVal;
    }
    return 0;
  });

  const totalPages = Math.ceil(sortedTopics.length / itemsPerPage);
  const paginatedTopics = sortedTopics.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const handleSort = (field: keyof Topic) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'desc' ? 'asc' : 'desc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  useEffect(() => {
    if (location.state?.selectedId) {
      const topic = topics.find(t => t.id === location.state.selectedId);
      if (topic) {
        setSelectedTopic(topic);
      }
    }
  }, [location.state]);

  return (
    <div className="h-[calc(100vh-180px)] overflow-auto px-4 pt-4 pb-0">
      <div className={selectedTopic ? '' : 'pb-4'}>
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h2 className="text-sm text-foreground font-medium">Topic Rankings</h2>
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
                <th className="text-left px-3 py-2">Topic Cluster</th>
                <th className="text-left px-3 py-2">Type</th>
                <th className="text-left px-3 py-2 cursor-pointer hover:text-primary" onClick={() => handleSort('replicabilityScore')}>
                  Replicability {sortField === 'replicabilityScore' && (sortDirection === 'desc' ? '↓' : '↑')}
                </th>
                <th className="text-left px-3 py-2 cursor-pointer hover:text-primary" onClick={() => handleSort('sustainedTractionScore')}>
                  Traction {sortField === 'sustainedTractionScore' && (sortDirection === 'desc' ? '↓' : '↑')}
                </th>
                <th className="text-left px-3 py-2 cursor-pointer hover:text-primary" onClick={() => handleSort('fragilityScore')}>
                  Fragility {sortField === 'fragilityScore' && (sortDirection === 'desc' ? '↓' : '↑')}
                </th>
                <th className="text-left px-3 py-2">Coverage</th>
                <th className="text-left px-3 py-2">Channels</th>
              </tr>
            </thead>
            <tbody>
              {paginatedTopics.map((topic) => (
                <tr
                  key={topic.id}
                  className={`border-b border-border hover:bg-muted/50 cursor-pointer transition ${selectedTopic?.id === topic.id ? 'bg-primary/5' : ''}`}
                  onClick={() => setSelectedTopic(topic)}
                >
                  <td className="px-3 py-2.5 text-sm text-foreground">{topic.topicCluster}</td>
                  <td className="px-3 py-2.5">
                    <StatusChip status={topic.topicType} variant="positive" />
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="w-24">
                      <ScoreBar score={topic.replicabilityScore} variant="positive" />
                    </div>
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="w-24">
                      <ScoreBar score={topic.sustainedTractionScore} variant="positive" />
                    </div>
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="w-24">
                      <ScoreBar score={topic.fragilityScore} variant="caution" />
                    </div>
                  </td>
                  <td className="px-3 py-2.5 text-xs text-muted-foreground">{topic.coveragePct}%</td>
                  <td className="px-3 py-2.5 text-xs text-muted-foreground">{topic.distinctChannels}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {selectedTopic && (
          <div className="mt-4 bg-card border border-border rounded-lg p-4">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="mb-2 text-sm text-foreground">{selectedTopic.topicCluster}</h3>
                <StatusChip status={selectedTopic.topicType} variant="positive" />
              </div>
              <button
                onClick={() => setSelectedTopic(null)}
                className="text-muted-foreground hover:text-primary text-sm"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-4 gap-6">
              <div>
                <h4 className="text-xs text-muted-foreground mb-2 uppercase tracking-wide">Opportunity Metrics</h4>
                <div className="space-y-3">
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Replicability score</div>
                    <ScoreBar score={selectedTopic.replicabilityScore} variant="positive" />
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Sustained traction score</div>
                    <ScoreBar score={selectedTopic.sustainedTractionScore} variant="positive" />
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Fragility score</div>
                    <ScoreBar score={selectedTopic.fragilityScore} variant="caution" />
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Average performance</div>
                    <ScoreBar score={selectedTopic.avgPerformance} variant="positive" />
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-xs text-muted-foreground mb-2 uppercase tracking-wide">Distribution Analysis</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="text-muted-foreground mb-1">Coverage</div>
                    <div>{selectedTopic.coveragePct}%</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground mb-1">Concentration</div>
                    <div>{selectedTopic.concentration}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground mb-1">Distinct channels</div>
                    <div>{selectedTopic.distinctChannels}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground mb-1">Total videos</div>
                    <div>{selectedTopic.totalVideos}</div>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-xs text-muted-foreground mb-2 uppercase tracking-wide">Top Channels</h4>
                <div className="space-y-2">
                  {selectedTopic.topChannels.map((channel) => (
                    <div key={channel} className="text-sm bg-muted/30 rounded px-3 py-2">
                      {channel}
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="text-xs text-muted-foreground mb-2 uppercase tracking-wide">Recent Examples</h4>
                <div className="space-y-2">
                  {selectedTopic.recentExamples.map((example, idx) => (
                    <div key={idx} className="text-sm bg-muted/30 rounded px-3 py-2">
                      {example}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {selectedTopic.fragilityScore > 0.25 && (
              <div className="mt-4 p-3 bg-caution/10 border border-caution/30 rounded text-xs text-caution-foreground">
                ⚠️ High fragility detected. This topic may be time-sensitive or event-driven.
              </div>
            )}

            {selectedTopic.replicabilityScore > 0.8 && selectedTopic.sustainedTractionScore > 0.75 && (
              <div className="mt-4 p-3 bg-positive/10 border border-positive/30 rounded text-xs text-positive-foreground">
                ✓ Strong replication opportunity. High scores in both replicability and sustained traction.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
