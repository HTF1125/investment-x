export interface ScreenerStock {
  rank: number;
  symbol: string;
  price: number;
  vomo_1m: number | null;
  vomo_6m: number | null;
  vomo_1y: number | null;
  vomo_composite: number | null;
  short_trend: boolean;
  long_trend: boolean;
  trend_confirmed: boolean;
  fwd_eps_growth: number | null;
  fund_count: number;
  return_1m: number | null;
  return_6m: number | null;
  return_1y: number | null;
  // Enriched fields
  market_cap: number | null;
  sector: string | null;
  avg_volume_30d: number | null;
  relative_volume: number | null;
  drawdown_52w: number | null;
  rs_percentile: number | null;
  sparkline_3m: number[] | null;
}

export interface FlowEntry {
  fund_name: string;
  symbol: string;
  security_name: string;
  action: string;
  shares: number;
  value_usd: number;
  shares_change_pct: number | null;
  report_date: string | null;
  vomo_composite: number | null;
  // Q-over-Q fields
  prev_shares: number | null;
  prev_value_usd: number | null;
  qoq_shares_change_pct: number | null;
}

export interface ConsensusEntry {
  symbol: string;
  fund_count: number;
  total_value_usd: number;
  fund_names: string[];
  actions: Record<string, number>;
  consensus_label: string;
  sector: string | null;
  market_cap: number | null;
  vomo_composite: number | null;
  price: number | null;
  drawdown_52w: number | null;
  rs_percentile: number | null;
}

export interface SectorConcentration {
  sector: string;
  stock_count: number;
  total_value_usd: number;
  avg_vomo: number | null;
  avg_fund_count: number | null;
  top_symbols: string[];
}

export interface ScreenerResponse {
  stocks: ScreenerStock[];
  total: number;
  computed_at: string;
  universe_size: number;
}

export interface FlowsResponse {
  flows: FlowEntry[];
  total: number;
  computed_at: string;
}

export interface ConsensusResponse {
  consensus: ConsensusEntry[];
  total: number;
  computed_at: string;
}

export interface SectorResponse {
  sectors: SectorConcentration[];
  total: number;
  computed_at: string;
}

export type ScreenerTab = 'rankings' | 'flows' | 'methodology';

export type SortField =
  | 'rank' | 'symbol' | 'price'
  | 'vomo_1m' | 'vomo_6m' | 'vomo_1y' | 'vomo_composite'
  | 'fwd_eps_growth' | 'fund_count'
  | 'return_1m' | 'return_6m' | 'return_1y'
  | 'market_cap' | 'avg_volume_30d' | 'relative_volume'
  | 'drawdown_52w' | 'rs_percentile';
