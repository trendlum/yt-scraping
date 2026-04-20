import { useMemo } from 'react';
import { Link } from 'react-router';
import { useFilters } from '../../contexts/FilterContext';
import { KPICard } from '../ui/KPICard';
import { StatusChip } from '../ui/StatusChip';
import { ConfidenceBadge } from '../ui/ConfidenceBadge';
import { ScoreBar } from '../ui/ScoreBar';
import { Sparkline } from '../ui/Sparkline';
import { DeltaPill } from '../ui/DeltaPill';

export function Overview() {
  const { filters } = useFilters();
  const topNiches = [
    {
      niche: 'us iran geopolitics',
      growthStatus: 'fast_emerging',
      earlyScore: 0.82,
      confirmedScore: 0.74,
      confidence: 'high' as const,
      distinctChannels: 11,
      totalVideos: 48,
      trend: [0.45, 0.52, 0.61, 0.68, 0.74, 0.82],
    },
    {
      niche: 'bitcoin etf flows',
      growthStatus: 'confirmed',
      earlyScore: 0.76,
      confirmedScore: 0.81,
      confidence: 'high' as const,
      distinctChannels: 14,
      totalVideos: 62,
      trend: [0.68, 0.71, 0.73, 0.76, 0.79, 0.81],
    },
    {
      niche: 'spanish housing market',
      growthStatus: 'fast_emerging',
      earlyScore: 0.71,
      confirmedScore: 0.65,
      confidence: 'medium' as const,
      distinctChannels: 7,
      totalVideos: 31,
      trend: [0.42, 0.48, 0.55, 0.61, 0.65, 0.71],
    },
  ];

  const topChannels = [
    {
      channel: '@MeidasTouch',
      niche: 'politics',
      growthStatus: 'algorithmic_shift',
      growthScore: 0.79,
      packagingScore: 0.72,
      sustainabilityScore: 0.68,
      algorithmicShiftScore: 0.85,
      volatilityScore: 0.22,
      deltaOverall: 0.18,
    },
    {
      channel: '@CoinBureauFinance',
      niche: 'crypto analysis',
      growthStatus: 'improving',
      growthScore: 0.74,
      packagingScore: 0.81,
      sustainabilityScore: 0.76,
      algorithmicShiftScore: 0.45,
      volatilityScore: 0.31,
      deltaOverall: 0.12,
    },
    {
      channel: '@TheGeoNetwork',
      niche: 'geopolitics',
      growthStatus: 'improving',
      growthScore: 0.68,
      packagingScore: 0.65,
      sustainabilityScore: 0.72,
      algorithmicShiftScore: 0.38,
      volatilityScore: 0.19,
      deltaOverall: 0.09,
    },
  ];

  const topTopics = [
    {
      topicCluster: 'trump foreign policy',
      topicType: 'replicable',
      replicabilityScore: 0.86,
      sustainedTractionScore: 0.78,
      fragilityScore: 0.19,
      distinctChannels: 8,
      coveragePct: 72,
      concentration: 'distributed',
    },
    {
      topicCluster: 'middle east escalation',
      topicType: 'replicable',
      replicabilityScore: 0.82,
      sustainedTractionScore: 0.84,
      fragilityScore: 0.15,
      distinctChannels: 12,
      coveragePct: 68,
      concentration: 'distributed',
    },
    {
      topicCluster: 'political news commentary',
      topicType: 'sustained',
      replicabilityScore: 0.75,
      sustainedTractionScore: 0.91,
      fragilityScore: 0.08,
      distinctChannels: 15,
      coveragePct: 81,
      concentration: 'broad',
    },
  ];

  const underpackagedVideos = [
    {
      title: 'Trump PANICS as Iran REJECTS ULTIMATUM',
      channel: '@MeidasTouch',
      niche: 'politics',
      age: 3.4,
      packagingScore: 0.63,
      momentumScore: 0.91,
      type: 'clear_underpackaged',
      confidence: 'high' as const,
    },
    {
      title: 'Why this market move is being ignored',
      channel: '@CoinBureauFinance',
      niche: 'crypto',
      age: 2.1,
      packagingScore: 0.58,
      momentumScore: 0.85,
      type: 'clear_underpackaged',
      confidence: 'high' as const,
    },
    {
      title: 'The hidden risk behind this housing trend',
      channel: '@EconomicsExplained',
      niche: 'economics',
      age: 4.7,
      packagingScore: 0.61,
      momentumScore: 0.78,
      type: 'clear_underpackaged',
      confidence: 'medium' as const,
    },
  ];

  const filteredNiches = useMemo(() => {
    return topNiches.filter(niche => {
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
  }, [filters]);

  const filteredChannels = useMemo(() => {
    return topChannels.filter(channel => {
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
  }, [filters]);

  const filteredTopics = useMemo(() => {
    return topTopics.filter(topic => {
      if (filters.topicCluster && !topic.topicCluster.toLowerCase().includes(filters.topicCluster.toLowerCase())) {
        return false;
      }
      if (filters.topicType && topic.topicType !== filters.topicType) {
        return false;
      }
      return true;
    });
  }, [filters]);

  const overpackagedVideos = [
    {
      title: 'Breaking News: This changes everything',
      channel: '@GenericNews',
      niche: 'news',
      age: 1.8,
      packagingScore: 0.92,
      momentumScore: 0.31,
      type: 'promise_weak',
      confidence: 'medium' as const,
    },
    {
      title: 'The shocking truth about this collapse',
      channel: '@ClickbaitChannel',
      niche: 'finance',
      age: 2.3,
      packagingScore: 0.88,
      momentumScore: 0.27,
      type: 'promise_weak',
      confidence: 'high' as const,
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
      if (filters.sampleConfidence && video.confidence !== filters.sampleConfidence) {
        return false;
      }
      return true;
    });
  }, [filters]);

  const filteredOverpackaged = useMemo(() => {
    return overpackagedVideos.filter(video => {
      if (filters.channelHandle && !video.channel.toLowerCase().includes(filters.channelHandle.toLowerCase())) {
        return false;
      }
      if (filters.niche && !video.niche.toLowerCase().includes(filters.niche.toLowerCase())) {
        return false;
      }
      if (filters.sampleConfidence && video.confidence !== filters.sampleConfidence) {
        return false;
      }
      return true;
    });
  }, [filters]);

  return (
    <div className="p-4 space-y-4">
      <div className="grid grid-cols-6 gap-3">
        <KPICard label="Emerging niches" value={12} delta={3} />
        <KPICard label="Confirmed growing niches" value={7} delta={1} />
        <KPICard label="Improving channels" value={18} delta={5} />
        <KPICard label="Replicable topics" value={24} delta={4} />
        <KPICard label="Underpackaged videos" value={31} delta={9} />
        <KPICard label="Overpackaged videos" value={14} delta={-2} />
      </div>

      <div className="bg-card border border-border rounded-lg p-3">
        <h3 className="mb-3 text-sm text-foreground">Signal Quality Summary</h3>
        <div className="grid grid-cols-4 gap-4 text-xs">
          <div>
            <div className="text-muted-foreground mb-1">High confidence samples</div>
            <div className="text-lg font-medium text-foreground">68%</div>
          </div>
          <div>
            <div className="text-muted-foreground mb-1">Medium confidence samples</div>
            <div className="text-lg font-medium text-foreground">24%</div>
          </div>
          <div>
            <div className="text-muted-foreground mb-1">Low confidence samples</div>
            <div className="text-lg font-medium text-foreground">8%</div>
          </div>
          <div>
            <div className="text-muted-foreground mb-1">Total entities tracked</div>
            <div className="text-lg font-medium text-foreground">247</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-card border border-border rounded-lg p-3">
          <Link to="/niches" className="block mb-3">
            <h3 className="text-sm text-foreground hover:text-primary transition cursor-pointer">Top Niches to Watch</h3>
          </Link>
          <div className="space-y-2">
            {filteredNiches.map((niche, index) => (
              <Link
                key={niche.niche}
                to="/niches"
                state={{ selectedId: String(index + 1) }}
                className="block border border-border rounded p-2.5 hover:border-primary/50 transition cursor-pointer"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <div className="mb-1 text-sm text-foreground">{niche.niche}</div>
                    <div className="flex items-center gap-2">
                      <StatusChip status={niche.growthStatus} variant="positive" />
                      <ConfidenceBadge confidence={niche.confidence} />
                    </div>
                  </div>
                  <Sparkline data={niche.trend} variant="positive" />
                </div>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <div className="text-muted-foreground mb-1">Early score</div>
                    <ScoreBar score={niche.earlyScore} variant="positive" />
                  </div>
                  <div>
                    <div className="text-muted-foreground mb-1">Confirmed score</div>
                    <ScoreBar score={niche.confirmedScore} variant="positive" />
                  </div>
                </div>
                <div className="flex items-center gap-4 mt-2 text-[10px] text-muted-foreground">
                  <span>{niche.distinctChannels} channels</span>
                  <span>{niche.totalVideos} videos</span>
                </div>
              </Link>
            ))}
          </div>
        </div>

        <div className="bg-card border border-border rounded-lg p-3">
          <Link to="/channels" className="block mb-3">
            <h3 className="text-sm text-foreground hover:text-primary transition cursor-pointer">Top Channels to Watch</h3>
          </Link>
          <div className="space-y-2">
            {filteredChannels.map((channel, index) => (
              <Link
                key={channel.channel}
                to="/channels"
                state={{ selectedId: String(index + 1) }}
                className="block border border-border rounded p-2.5 hover:border-primary/50 transition cursor-pointer"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <div className="mb-1 text-sm text-foreground">{channel.channel}</div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">{channel.niche}</span>
                      <StatusChip status={channel.growthStatus} variant="positive" />
                      <DeltaPill value={channel.deltaOverall} />
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <div className="text-muted-foreground mb-1">Growth score</div>
                    <ScoreBar score={channel.growthScore} variant="positive" />
                  </div>
                  <div>
                    <div className="text-muted-foreground mb-1">Packaging</div>
                    <ScoreBar score={channel.packagingScore} variant="positive" />
                  </div>
                  <div>
                    <div className="text-muted-foreground mb-1">Sustainability</div>
                    <ScoreBar score={channel.sustainabilityScore} variant="positive" />
                  </div>
                  <div>
                    <div className="text-muted-foreground mb-1">Volatility</div>
                    <ScoreBar score={channel.volatilityScore} variant="caution" />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-card border border-border rounded-lg p-3">
        <Link to="/topics" className="block mb-3">
          <h3 className="text-sm text-foreground hover:text-primary transition cursor-pointer">Top Topics to Replicate</h3>
        </Link>
        <div className="grid grid-cols-3 gap-2.5">
          {filteredTopics.map((topic, index) => (
            <Link
              key={topic.topicCluster}
              to="/topics"
              state={{ selectedId: String(index + 1) }}
              className="block border border-border rounded p-2.5 hover:border-primary/50 transition cursor-pointer"
            >
              <div className="mb-2">
                <div className="mb-1 text-sm text-foreground">{topic.topicCluster}</div>
                <StatusChip status={topic.topicType} variant="positive" />
              </div>
              <div className="space-y-2 text-xs">
                <div>
                  <div className="text-muted-foreground mb-1">Replicability</div>
                  <ScoreBar score={topic.replicabilityScore} variant="positive" />
                </div>
                <div>
                  <div className="text-muted-foreground mb-1">Sustained traction</div>
                  <ScoreBar score={topic.sustainedTractionScore} variant="positive" />
                </div>
                <div>
                  <div className="text-muted-foreground mb-1">Fragility</div>
                  <ScoreBar score={topic.fragilityScore} variant="caution" />
                </div>
              </div>
              <div className="flex items-center gap-3 mt-2 text-[10px] text-muted-foreground">
                <span>{topic.distinctChannels} channels</span>
                <span>{topic.coveragePct}% coverage</span>
              </div>
            </Link>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-card border border-border rounded-lg p-3">
          <Link to="/videos" state={{ tab: 'underpackaged' }} className="block mb-3">
            <h3 className="text-sm text-foreground hover:text-primary transition cursor-pointer">Underpackaged Opportunities</h3>
          </Link>
          <div className="space-y-2">
            {filteredUnderpackaged.map((video, idx) => (
              <Link
                key={idx}
                to="/videos"
                state={{ tab: 'underpackaged', selectedId: String(idx + 1) }}
                className="block border border-border rounded p-2.5 hover:border-primary/50 transition cursor-pointer"
              >
                <div className="mb-2 text-sm text-foreground">{video.title}</div>
                <div className="flex items-center gap-2 mb-2 text-[10px]">
                  <span className="text-muted-foreground">{video.channel}</span>
                  <span className="text-muted-foreground">·</span>
                  <span className="text-muted-foreground">{video.niche}</span>
                  <span className="text-muted-foreground">·</span>
                  <span className="text-muted-foreground">{video.age.toFixed(1)}d</span>
                  <ConfidenceBadge confidence={video.confidence} />
                </div>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <div className="text-muted-foreground mb-1">Packaging</div>
                    <ScoreBar score={video.packagingScore} variant="caution" />
                  </div>
                  <div>
                    <div className="text-muted-foreground mb-1">Momentum</div>
                    <ScoreBar score={video.momentumScore} variant="positive" />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>

        <div className="bg-card border border-border rounded-lg p-3">
          <Link to="/videos" state={{ tab: 'overpackaged' }} className="block mb-3">
            <h3 className="text-sm text-foreground hover:text-primary transition cursor-pointer">Overpackaged Videos</h3>
          </Link>
          <div className="space-y-2">
            {filteredOverpackaged.map((video, idx) => (
              <Link
                key={idx}
                to="/videos"
                state={{ tab: 'overpackaged', selectedId: String(idx + 5) }}
                className="block border border-border rounded p-2.5 hover:border-primary/50 transition cursor-pointer"
              >
                <div className="mb-2 text-sm text-foreground">{video.title}</div>
                <div className="flex items-center gap-2 mb-2 text-[10px]">
                  <span className="text-muted-foreground">{video.channel}</span>
                  <span className="text-muted-foreground">·</span>
                  <span className="text-muted-foreground">{video.niche}</span>
                  <span className="text-muted-foreground">·</span>
                  <span className="text-muted-foreground">{video.age.toFixed(1)}d</span>
                  <ConfidenceBadge confidence={video.confidence} />
                </div>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <div className="text-muted-foreground mb-1">Packaging</div>
                    <ScoreBar score={video.packagingScore} variant="positive" />
                  </div>
                  <div>
                    <div className="text-muted-foreground mb-1">Momentum</div>
                    <ScoreBar score={video.momentumScore} variant="critical" />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
