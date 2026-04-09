import type { AnnotationConfig, DrawnShape } from '@/lib/buildChartFigure';

export interface PackSummary {
  id: string;
  name: string;
  description: string | null;
  chart_count: number;
  is_published: boolean;
  creator_name?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SelectedSeries {
  code: string;
  name: string;
  chartType: string;
  yAxis: string;
  yAxisIndex?: number;
  visible: boolean;
  color?: string;
  transform?: string;
  transformParam?: number;
  lineStyle?: string;
  lineWidth?: number;
  paneId?: number;
  showMarkers?: boolean;
  markerSize?: number;
  markerShape?: string;
  fillOpacity?: number;
  showDataLabels?: boolean;
}

export interface ChartConfig {
  title?: string;
  description?: string;
  code?: string;
  /** Pre-rendered Plotly figure (inline). */
  figure?: any;
  /** ISO timestamp of when the figure was cached. */
  figureCachedAt?: string;
  /** Reference to a Charts table record — figure loaded lazily. */
  chart_id?: string;
  series: SelectedSeries[];
  panes?: { id: number; label: string }[];
  annotations?: AnnotationConfig[];
  logAxes?: (number | string)[];
  invertedAxes?: string[];
  pctAxes?: string[];
  activeRange?: string;
  startDate?: string;
  endDate?: string;
  yAxisBases?: Record<string, number>;
  yAxisRanges?: Record<string, { min?: number; max?: number }>;
  showRecessions?: boolean;
  hoverMode?: string;
  showLegend?: boolean;
  legendPosition?: string;
  showGridlines?: boolean;
  gridlineStyle?: string;
  axisTitles?: Record<string, string>;
  titleFontSize?: number;
  showZeroline?: boolean;
  bargap?: number;
  drawnShapes?: DrawnShape[];
  deleted?: boolean;
  [key: string]: any;
}

export interface PackDetail {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  charts: ChartConfig[];
  is_published: boolean;
  creator_name?: string | null;
  created_at: string;
  updated_at: string;
}

// ── Helpers ──

export function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return shortDate(iso);
}

// ── Flash toast type ──

export interface FlashMessage {
  type: 'success' | 'error';
  text: string;
}
