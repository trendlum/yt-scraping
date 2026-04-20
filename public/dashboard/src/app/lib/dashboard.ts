export type ConfidenceLevel = "high" | "medium" | "low";

export interface DashboardFiltersState {
  analysisWindow: string;
  niche: string;
  channelHandle: string;
  topicCluster: string;
  nicheGrowthStatus: string;
  channelGrowthStatus: string;
  topicType: string;
  performanceLabel: string;
  videoType: string;
  sampleConfidence: string;
}

export interface NicheRow {
  niche: string;
  analysis_date: string;
  window_days: number;
  video_count_total: number;
  video_count_last_7d: number;
  distinct_channels_count: number;
  median_ratio_d1: number | null;
  median_ratio_d3: number | null;
  median_ratio_d7: number | null;
  median_ratio_d15: number | null;
  niche_early_signal_score: number | null;
  niche_early_acceleration_score: number | null;
  niche_growth_forecast_score: number | null;
  niche_growth_status_early: string;
  niche_growth_score_confirmed: number | null;
  niche_consistency_score_confirmed: number | null;
  niche_acceleration_score_confirmed: number | null;
  niche_outlier_dependency_score: number | null;
  niche_growth_status_confirmed: string;
  pct_explosive: number | null;
  pct_solid: number | null;
  pct_dead: number | null;
  sample_confidence_level: ConfidenceLevel;
  low_sample_flag: boolean;
  notes: string | null;
}

export interface ChannelRow {
  channel_handle: string;
  analysis_date: string;
  window_days: number;
  channel_niche: string | null;
  video_count_recent: number;
  video_count_previous: number;
  median_packaging_score_recent: number | null;
  median_packaging_score_previous: number | null;
  delta_packaging_score: number | null;
  median_momentum_score_recent: number | null;
  median_momentum_score_previous: number | null;
  delta_momentum_score: number | null;
  median_overall_score_recent: number | null;
  median_overall_score_previous: number | null;
  delta_overall_score: number | null;
  channel_packaging_improvement_score: number | null;
  channel_sustainability_improvement_score: number | null;
  channel_algorithmic_shift_score: number | null;
  channel_volatility_score: number | null;
  channel_growth_score: number | null;
  channel_growth_status: string;
  sample_confidence_level: ConfidenceLevel;
  low_sample_flag: boolean;
}

export interface TopicRow {
  topic_cluster: string;
  analysis_date: string;
  window_days: number;
  video_count: number;
  distinct_channels_count: number;
  pct_videos_with_topic: number | null;
  topic_start_strength_score: number | null;
  topic_sustained_traction_score: number | null;
  topic_fragility_score: number | null;
  topic_replicability_score: number | null;
  topic_type: string;
  sample_confidence_level: ConfidenceLevel;
  pct_dead: number | null;
  pct_underperforming: number | null;
  top1_ratio_d7_vs_median: number | null;
  top3_ratio_d7_avg_vs_median: number | null;
}

export interface VideoRow {
  video_id: string;
  analysis_date: string;
  channel_handle: string;
  channel_niche: string | null;
  title: string;
  video_url: string | null;
  thumbnail_url: string | null;
  published_at: string | null;
  age_days: number | null;
  packaging_score: number | null;
  momentum_score: number | null;
  ratio_d1: number | null;
  ratio_d3: number | null;
  ratio_d7: number | null;
  ratio_d15: number | null;
  growth_d1_3: number | null;
  growth_d3_7: number | null;
  growth_d7_15: number | null;
  acceleration_early: number | null;
  acceleration_late: number | null;
  consistency_periods_above_baseline: number | null;
  performance_label: string | null;
  underpackaged_type?: string | null;
  underpackaged_score?: number | null;
  underpackaged_confidence?: ConfidenceLevel | null;
  overpackaged_type?: string | null;
  overpackaged_score?: number | null;
  overpackaged_confidence?: ConfidenceLevel | null;
}

export interface VideoDetailRow extends VideoRow {
  video_url: string;
  thumbnail_url: string | null;
  view_count: number | null;
  like_count: number | null;
  comment_count: number | null;
  calculated_at: string;
  current_snapshot_at: string;
  performance_published_at: string | null;
  current_view_count: number | null;
  views_d1: number | null;
  views_d3: number | null;
  views_d7: number | null;
  views_d15: number | null;
  baseline_median_d1: number | null;
  baseline_median_d3: number | null;
  baseline_median_d7: number | null;
  baseline_median_d15: number | null;
  baseline_sample_size_d1: number | null;
  baseline_sample_size_d3: number | null;
  baseline_sample_size_d7: number | null;
  baseline_sample_size_d15: number | null;
  flow_d1: number | null;
  flow_d1_3: number | null;
  flow_d3_7: number | null;
  flow_d7_15: number | null;
  overall_score: number | null;
  packaging_score: number | null;
  momentum_score: number | null;
  performance_label: string | null;
  title_length_chars: number | null;
  title_word_count: number | null;
  uppercase_word_count: number | null;
  digit_count: number | null;
  has_number: boolean | null;
  has_question: boolean | null;
  has_exclamation: boolean | null;
  has_year: boolean | null;
  has_vs: boolean | null;
  has_brackets: boolean | null;
  has_colon: boolean | null;
  trigger_word_count: number | null;
  title_pattern: string | null;
  thumbnail_feature_status: string | null;
  has_face: boolean | null;
  face_count: number | null;
  has_thumbnail_text: boolean | null;
  estimated_thumbnail_text_tokens: number | null;
  dominant_emotion: string | null;
  dominant_colors: unknown;
  composition_type: string | null;
  contains_chart: boolean | null;
  contains_map: boolean | null;
  visual_style: string | null;
  thumbnail_ocr_status: string | null;
  thumbnail_text: string | null;
  thumbnail_text_confidence: number | null;
  transcript_status: string | null;
  transcript_language: string | null;
  transcript_is_auto_generated: boolean | null;
  format_type: string | null;
  promise_type: string | null;
  topic_clusters: string[];
}

export interface OverviewResponse {
  summary: {
    analysis_date: string | null;
    analysis_window: number | null;
    niches_count: number;
    channels_count: number;
    topics_count: number;
    underpackaged_count: number;
    overpackaged_count: number;
    tracked_rows_count: number;
    high_confidence_count: number;
    high_confidence_share: number;
  };
  niches: NicheRow[];
  channels: ChannelRow[];
  topics: TopicRow[];
  underpackaged: VideoRow[];
  overpackaged: VideoRow[];
}

export interface NicheDetailResponse {
  row: NicheRow | null;
  recent_channels: ChannelRow[];
  top_topics: Array<{ label: string; count: number }>;
}

export interface ChannelDetailResponse {
  row: ChannelRow | null;
  top_topics: Array<{ label: string; count: number }>;
  recent_videos: VideoRow[];
}

export interface TopicDetailResponse {
  row: TopicRow | null;
  top_channels: Array<{ channel_handle: string; count: number }>;
  recent_examples: VideoRow[];
}

export interface VideoDetailResponse {
  row: VideoDetailRow | null;
}

export interface MetaResponse {
  default_window_days: number;
  available_window_days: number[];
  niche_growth_status_options: string[];
  channel_growth_status_options: string[];
  topic_type_options: string[];
  performance_label_options: string[];
}

type QueryValue = string | number | boolean | null | undefined;

const filterParamMap: Record<keyof DashboardFiltersState, string> = {
  analysisWindow: "analysis_window",
  niche: "niche",
  channelHandle: "channel_handle",
  topicCluster: "topic_cluster",
  nicheGrowthStatus: "niche_growth_status",
  channelGrowthStatus: "channel_growth_status",
  topicType: "topic_type",
  performanceLabel: "performance_label",
  videoType: "video_type",
  sampleConfidence: "sample_confidence",
};

export function buildDashboardQuery(
  filters: Partial<DashboardFiltersState> = {},
  extra: Record<string, QueryValue> = {},
) {
  const params = new URLSearchParams();

  for (const [key, value] of Object.entries(filters) as Array<[keyof DashboardFiltersState, QueryValue]>) {
    if (value === undefined || value === null || value === "") {
      continue;
    }
    params.set(filterParamMap[key], String(value));
  }

  for (const [key, value] of Object.entries(extra)) {
    if (value === undefined || value === null || value === "") {
      continue;
    }
    params.set(key, String(value));
  }

  return params.toString();
}

export async function dashboardRequest<T>(
  path: string,
  query = "",
  signal?: AbortSignal,
): Promise<T> {
  const url = query ? `${path}?${query}` : path;
  const response = await fetch(url, { signal });
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const message = payload?.error ?? `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  return payload as T;
}

export function formatScore(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  return value.toFixed(2);
}

export function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  return `${Math.round(value * 100)}%`;
}

export function formatDate(value: string | null | undefined) {
  if (!value) {
    return "Latest";
  }
  return value.slice(0, 10);
}

export function formatAgeDays(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  return `${value.toFixed(1)}d`;
}

export function titleCase(value: string | null | undefined) {
  if (!value) {
    return "—";
  }
  return value.replace(/_/g, " ");
}
