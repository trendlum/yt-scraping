import { useState, useEffect, useMemo } from 'react';
import { useLocation } from 'react-router';
import { useFilters } from '../../contexts/FilterContext';
import { StatusChip } from '../ui/StatusChip';
import { ConfidenceBadge } from '../ui/ConfidenceBadge';
import { ScoreBar } from '../ui/ScoreBar';

interface Video {
  id: string;
  title: string;
  channel: string;
  niche: string;
  age: number;
  packagingScore: number;
  momentumScore: number;
  ratioD1: number;
  ratioD3: number;
  ratioD7: number;
  ratioD15: number;
  performanceLabel: string;
  opportunityType: string;
  confidence: 'high' | 'medium' | 'low';
  views: number;
  accelerationEarly: number;
  consistencyPeriods: number;
}

export function Videos() {
  const location = useLocation();
  const { filters } = useFilters();
  const [activeTab, setActiveTab] = useState<'underpackaged' | 'overpackaged'>('underpackaged');
  const [selectedVideo, setSelectedVideo] = useState<Video | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  useEffect(() => {
    if (location.state?.tab) {
      setActiveTab(location.state.tab as 'underpackaged' | 'overpackaged');
    }
    if (location.state?.selectedId) {
      const allVideos = [...underpackagedVideos, ...overpackagedVideos];
      const video = allVideos.find(v => v.id === location.state.selectedId);
      if (video) {
        setSelectedVideo(video);
      }
    }
  }, [location.state]);

  const underpackagedVideos: Video[] = [
    {
      id: '1',
      title: 'Trump PANICS as Iran REJECTS ULTIMATUM',
      channel: '@MeidasTouch',
      niche: 'politics',
      age: 3.4,
      packagingScore: 0.63,
      momentumScore: 0.91,
      ratioD1: 1.42,
      ratioD3: 1.68,
      ratioD7: 1.88,
      ratioD15: 2.10,
      performanceLabel: 'explosive',
      opportunityType: 'clear_underpackaged',
      confidence: 'high',
      views: 284000,
      accelerationEarly: 0.27,
      consistencyPeriods: 3,
    },
    {
      id: '2',
      title: 'Why this market move is being ignored',
      channel: '@CoinBureauFinance',
      niche: 'crypto',
      age: 2.1,
      packagingScore: 0.58,
      momentumScore: 0.85,
      ratioD1: 1.38,
      ratioD3: 1.54,
      ratioD7: 1.72,
      ratioD15: 1.91,
      performanceLabel: 'strong',
      opportunityType: 'clear_underpackaged',
      confidence: 'high',
      views: 196000,
      accelerationEarly: 0.31,
      consistencyPeriods: 4,
    },
    {
      id: '3',
      title: 'The hidden risk behind this housing trend',
      channel: '@EconomicsExplained',
      niche: 'economics',
      age: 4.7,
      packagingScore: 0.61,
      momentumScore: 0.78,
      ratioD1: 1.28,
      ratioD3: 1.45,
      ratioD7: 1.61,
      ratioD15: 1.79,
      performanceLabel: 'solid',
      opportunityType: 'clear_underpackaged',
      confidence: 'medium',
      views: 142000,
      accelerationEarly: 0.22,
      consistencyPeriods: 3,
    },
    {
      id: '4',
      title: 'What AI research just achieved is terrifying',
      channel: '@TwoMinutePapers',
      niche: 'ai research',
      age: 1.8,
      packagingScore: 0.55,
      momentumScore: 0.94,
      ratioD1: 1.52,
      ratioD3: 1.84,
      ratioD7: 2.12,
      ratioD15: 2.38,
      performanceLabel: 'explosive',
      opportunityType: 'clear_underpackaged',
      confidence: 'high',
      views: 421000,
      accelerationEarly: 0.35,
      consistencyPeriods: 4,
    },
  ];

  const overpackagedVideos: Video[] = [
    {
      id: '5',
      title: 'Breaking News: This changes everything',
      channel: '@GenericNews',
      niche: 'news',
      age: 1.8,
      packagingScore: 0.92,
      momentumScore: 0.31,
      ratioD1: 0.82,
      ratioD3: 0.71,
      ratioD7: 0.64,
      ratioD15: 0.58,
      performanceLabel: 'declining',
      opportunityType: 'promise_weak',
      confidence: 'medium',
      views: 48000,
      accelerationEarly: -0.18,
      consistencyPeriods: 0,
    },
    {
      id: '6',
      title: 'The shocking truth about this collapse',
      channel: '@ClickbaitChannel',
      niche: 'finance',
      age: 2.3,
      packagingScore: 0.88,
      momentumScore: 0.27,
      ratioD1: 0.76,
      ratioD3: 0.68,
      ratioD7: 0.59,
      ratioD15: 0.51,
      performanceLabel: 'weak',
      opportunityType: 'promise_weak',
      confidence: 'high',
      views: 32000,
      accelerationEarly: -0.22,
      consistencyPeriods: 0,
    },
    {
      id: '7',
      title: 'What happens next will surprise you',
      channel: '@VagueContent',
      niche: 'general',
      age: 3.1,
      packagingScore: 0.85,
      momentumScore: 0.34,
      ratioD1: 0.88,
      ratioD3: 0.79,
      ratioD7: 0.71,
      ratioD15: 0.64,
      performanceLabel: 'underperforming',
      opportunityType: 'promise_weak',
      confidence: 'medium',
      views: 51000,
      accelerationEarly: -0.15,
      consistencyPeriods: 0,
    },
  ];

  const filteredUnderpackaged = useMemo(() => {
    return underpackagedVideos.filter(video => {
      if (filters.channelHandle && !video.channel.toLowerCase().includes(filters.channelHandle.toLowerCase())) {
        return false;
      }
      if (filters.niche && !video.niche.toLowerCase().includes(filters.niche.toLowerCase())) {
        return false;
      }
      if (filters.performanceLabel && video.performanceLabel !== filters.performanceLabel) {
        return false;
      }
      if (filters.sampleConfidence && video.confidence !== filters.sampleConfidence) {
        return false;
      }
      return true;
    });
  }, [underpackagedVideos, filters]);

  const filteredOverpackaged = useMemo(() => {
    return overpackagedVideos.filter(video => {
      if (filters.channelHandle && !video.channel.toLowerCase().includes(filters.channelHandle.toLowerCase())) {
        return false;
      }
      if (filters.niche && !video.niche.toLowerCase().includes(filters.niche.toLowerCase())) {
        return false;
      }
      if (filters.performanceLabel && video.performanceLabel !== filters.performanceLabel) {
        return false;
      }
      if (filters.sampleConfidence && video.confidence !== filters.sampleConfidence) {
        return false;
      }
      return true;
    });
  }, [overpackagedVideos, filters]);

  const currentVideos = activeTab === 'underpackaged' ? filteredUnderpackaged : filteredOverpackaged;
  const totalPages = Math.ceil(currentVideos.length / itemsPerPage);
  const paginatedVideos = currentVideos.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  return (
    <div className="h-[calc(100vh-180px)] overflow-auto px-4 pt-4 pb-0">
      <div className={selectedVideo ? '' : 'pb-4'}>
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  setActiveTab('underpackaged');
                  setCurrentPage(1);
                }}
                className={`px-3 py-1.5 rounded text-xs transition ${
                  activeTab === 'underpackaged'
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:text-primary hover:bg-muted'
                }`}
              >
                Underpackaged
              </button>
              <button
                onClick={() => {
                  setActiveTab('overpackaged');
                  setCurrentPage(1);
                }}
                className={`px-3 py-1.5 rounded text-xs transition ${
                  activeTab === 'overpackaged'
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:text-primary hover:bg-muted'
                }`}
              >
                Overpackaged
              </button>
            </div>
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
                <th className="text-left px-3 py-2">Title</th>
                <th className="text-left px-3 py-2">Channel</th>
                <th className="text-left px-3 py-2">Niche</th>
                <th className="text-left px-3 py-2">Age</th>
                <th className="text-left px-3 py-2">Packaging</th>
                <th className="text-left px-3 py-2">Momentum</th>
                <th className="text-left px-3 py-2">Performance</th>
                <th className="text-left px-3 py-2">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {paginatedVideos.map((video) => (
                <tr
                  key={video.id}
                  className={`border-b border-border hover:bg-muted/50 cursor-pointer transition ${selectedVideo?.id === video.id ? 'bg-primary/5' : ''}`}
                  onClick={() => setSelectedVideo(video)}
                >
                  <td className="px-3 py-2.5 max-w-md">
                    <div className="truncate text-sm text-foreground">{video.title}</div>
                  </td>
                  <td className="px-3 py-2.5 text-xs text-muted-foreground">{video.channel}</td>
                  <td className="px-3 py-2.5 text-xs text-muted-foreground">{video.niche}</td>
                  <td className="px-3 py-2.5 text-xs text-muted-foreground">{video.age.toFixed(1)}d</td>
                  <td className="px-3 py-2.5">
                    <div className="w-16">
                      <ScoreBar score={video.packagingScore} variant={activeTab === 'underpackaged' ? 'caution' : 'positive'} />
                    </div>
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="w-16">
                      <ScoreBar score={video.momentumScore} variant={activeTab === 'underpackaged' ? 'positive' : 'critical'} />
                    </div>
                  </td>
                  <td className="px-3 py-2.5">
                    <StatusChip status={video.performanceLabel} variant={activeTab === 'underpackaged' ? 'positive' : 'caution'} />
                  </td>
                  <td className="px-3 py-2.5">
                    <ConfidenceBadge confidence={video.confidence} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {selectedVideo && (
          <div className="mt-4 bg-card border border-border rounded-lg p-4">
            <div className="flex items-start justify-between mb-4">
              <h3 className="text-sm text-foreground">Video Details</h3>
              <button
                onClick={() => setSelectedVideo(null)}
                className="text-muted-foreground hover:text-primary text-sm"
              >
                ✕
              </button>
            </div>

            <div className="mb-4">
              <h3 className="mb-2 text-sm text-foreground">{selectedVideo.title}</h3>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span>{selectedVideo.channel}</span>
                <span>·</span>
                <span>{selectedVideo.niche}</span>
              </div>
            </div>

            <div className="grid grid-cols-4 gap-6">

              <div>
                <h4 className="text-xs text-muted-foreground mb-2 uppercase tracking-wide">Opportunity Classification</h4>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Type</span>
                    <StatusChip status={selectedVideo.opportunityType} variant={activeTab === 'underpackaged' ? 'positive' : 'caution'} />
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Performance</span>
                    <StatusChip status={selectedVideo.performanceLabel} variant={activeTab === 'underpackaged' ? 'positive' : 'caution'} />
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Confidence</span>
                    <ConfidenceBadge confidence={selectedVideo.confidence} />
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-xs text-muted-foreground mb-2 uppercase tracking-wide">Core Metrics</h4>
                <div className="space-y-3">
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Packaging score</div>
                    <ScoreBar score={selectedVideo.packagingScore} variant={activeTab === 'underpackaged' ? 'caution' : 'positive'} />
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Momentum score</div>
                    <ScoreBar score={selectedVideo.momentumScore} variant={activeTab === 'underpackaged' ? 'positive' : 'critical'} />
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-xs text-muted-foreground mb-2 uppercase tracking-wide">Performance Ratios</h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <div className="text-muted-foreground mb-1">Day 1 ratio</div>
                    <div className={selectedVideo.ratioD1 > 1 ? 'text-positive' : 'text-critical'}>{selectedVideo.ratioD1.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground mb-1">Day 3 ratio</div>
                    <div className={selectedVideo.ratioD3 > 1 ? 'text-positive' : 'text-critical'}>{selectedVideo.ratioD3.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground mb-1">Day 7 ratio</div>
                    <div className={selectedVideo.ratioD7 > 1 ? 'text-positive' : 'text-critical'}>{selectedVideo.ratioD7.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground mb-1">Day 15 ratio</div>
                    <div className={selectedVideo.ratioD15 > 1 ? 'text-positive' : 'text-critical'}>{selectedVideo.ratioD15.toFixed(2)}</div>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-xs text-muted-foreground mb-2 uppercase tracking-wide">Additional Details</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Total views</span>
                    <span>{selectedVideo.views.toLocaleString()}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Video age</span>
                    <span>{selectedVideo.age.toFixed(1)} days</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Early acceleration</span>
                    <span className={selectedVideo.accelerationEarly > 0 ? 'text-positive' : 'text-critical'}>
                      {selectedVideo.accelerationEarly > 0 ? '+' : ''}{selectedVideo.accelerationEarly.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Consistency periods</span>
                    <span>{selectedVideo.consistencyPeriods}</span>
                  </div>
                </div>
              </div>
            </div>

            {activeTab === 'underpackaged' && selectedVideo.momentumScore > 0.85 && (
              <div className="mt-4 p-3 bg-positive/10 border border-positive/30 rounded text-xs text-positive-foreground">
                ✓ Strong underpackaging signal. High momentum with weak packaging suggests significant opportunity for replication with better presentation.
              </div>
            )}

            {activeTab === 'overpackaged' && selectedVideo.packagingScore > 0.85 && selectedVideo.momentumScore < 0.35 && (
              <div className="mt-4 p-3 bg-caution/10 border border-caution/30 rounded text-xs text-caution-foreground">
                ⚠️ Promise-delivery mismatch. High packaging score but weak momentum suggests the content didn't deliver on the packaging promise.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
