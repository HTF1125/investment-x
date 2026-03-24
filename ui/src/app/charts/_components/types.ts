export interface TimeseriesMeta {
  id: string;
  code: string;
  name: string | null;
  category: string | null;
  asset_class: string | null;
  source: string | null;
  frequency: string | null;
  start: string | null;
  end: string | null;
  num_data: number | null;
  country: string | null;
}

export type TransformType = 'none' | 'pctchg' | 'yoy' | 'ma' | 'zscore' | 'diff' | 'drawdown' | 'rebase' | 'log';
export type LineStyle = 'solid' | 'dash' | 'dot' | 'dashdot';
export type ChartType = 'line' | 'bar' | 'area' | 'scatter' | 'stackedbar' | 'stackedarea';

export interface SelectedSeries {
  code: string;
  name: string;
  chartType: ChartType;
  yAxis: 'left' | 'right';
  yAxisIndex?: number;
  visible: boolean;
  color?: string;
  transform?: TransformType;
  transformParam?: number;
  lineStyle?: LineStyle;
  lineWidth?: number;
  paneId?: number;
  showMarkers?: boolean;
  markerSize?: number;
  markerShape?: string;
  fillOpacity?: number;
  showDataLabels?: boolean;
}

export interface Pane {
  id: number;
  label: string;
}

export interface Annotation {
  id: string;
  type: 'hline' | 'vline' | 'text';
  x?: string;
  y?: number;
  text?: string;
  color: string;
  paneId: number;
}

export interface WorkspaceSummary {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
}
