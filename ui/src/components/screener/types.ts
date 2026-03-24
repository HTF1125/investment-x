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

export type ScreenerTab = 'rankings' | 'flows' | 'methodology';

export type SortField =
  | 'rank' | 'symbol' | 'price'
  | 'vomo_1m' | 'vomo_6m' | 'vomo_1y' | 'vomo_composite'
  | 'fwd_eps_growth' | 'fund_count'
  | 'return_1m' | 'return_6m' | 'return_1y';
