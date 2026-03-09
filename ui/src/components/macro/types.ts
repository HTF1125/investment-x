export interface Target { name: string; ticker: string; region: string; }

export interface Indicator { name: string; z: number; signal: string; desc: string; }

export interface RegimeStat {
  regime: string; mean_fwd_ret: number; median_fwd_ret: number;
  std: number; sharpe: number; pct_positive: number; n: number;
}

export interface LiqPhaseStat {
  phase: string; mean_fwd_ret: number; median_fwd_ret: number;
  std: number; sharpe: number; pct_positive: number; n: number;
}

export interface TacticalStat {
  bucket: string; mean_fwd_ret: number; median_fwd_ret: number;
  std: number; sharpe: number; pct_positive: number; n: number;
}

export interface Snapshot {
  current: {
    regime: string; confidence: number; growth: number; inflation: number;
    liquidity: number; tactical: number; allocation: number; liq_phase: string;
    regime_probs: Record<string, number>;
    trend_bullish?: boolean | null; sma_40w?: number | null;
    binary_allocation?: number | null;
  };
  projections: Record<string, Record<string, number>>;
  indicator_counts: Record<string, number>;
  indicators: Record<string, Indicator[]>;
  transition_matrix: { labels: string[]; values: number[][]; };
  regime_stats: RegimeStat[];
  liq_phase_stats?: LiqPhaseStat[];
  tactical_stats?: TacticalStat[];
  empirical_regime_returns?: Record<string, number>;
}

export interface TimeseriesData {
  dates: string[]; target_px: number[]; growth: number[]; inflation: number[];
  liquidity: number[]; tactical: number[]; allocation: number[];
  liq_phase: string[]; regime_probs: Record<string, number[]>;
  trend?: number[]; sma_40w?: number[]; binary_allocation?: number[];
}

export interface BacktestStat {
  label: string; ann_return: number; ann_vol: number; sharpe: number;
  max_dd: number; info_ratio: number; tracking_err: number; ann_turnover: number;
}

export interface ComponentBT {
  equity: number[]; weight: number[];
  stats: { ann_return?: number; ann_vol?: number; sharpe?: number; max_dd?: number; info_ratio?: number; ann_turnover?: number; };
}

export interface BacktestData {
  dates: string[]; strategy_equity: number[]; benchmark_equity: number[];
  full_equity: number[]; strategy_weight: number[]; stats: BacktestStat[];
  regime_only?: ComponentBT; liquidity_only?: ComponentBT; tactical_only?: ComponentBT;
  binary_strategy?: ComponentBT;
}

export type Tab = 'overview' | 'regime' | 'liquidity' | 'tactical';
