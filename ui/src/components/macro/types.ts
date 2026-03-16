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

export type Tab = 'strategy' | 'factors' | 'regime' | 'signal' | 'cross-market' | 'robustness' | 'methodology';

// ─── Walk-Forward Strategy Types ────────────────────────────────────────────

export interface StrategyResult {
  ann_return: number; sharpe: number; max_dd: number; vol: number;
  ir: number; te: number; hit_rate: number; avg_eq_wt: number; alpha: number;
  period_start: string; period_end: string;
  cumulative: { dates: string[]; strategy: number[]; benchmark: number[]; index: number[] };
  eq_weight: { dates: string[]; values: number[] };
  drawdown: { dates: string[]; values: number[] };
  rolling_excess: { dates: string[]; values: number[] };
  yearly_alpha: Record<string, number>;
}

export interface RegimeHistoryEntry {
  date: string; regime: string; growth_pctile: number;
  inflation_pctile: number; eq_weight: number;
}

export interface RegimeStrategyBacktest {
  parameters: Record<string, any>;
  cat_counts: Record<string, number>;
  benchmark: { ann_return: number; sharpe: number; max_dd: number; vol: number };
  strategies: Record<string, StrategyResult>;
  regime_history: RegimeHistoryEntry[];
}

export interface FactorCategory {
  n_rebalances: number;
  n_unique_indicators: number;
  frequency: { indicator: string; count: number; pct: number }[];
  latest_selection: { date: string; indicators: { name: string; ic: number }[] };
  ic_heatmap: { dates: string[]; indicators: string[]; values: number[][] };
}

export interface CurrentSignalData {
  category_signals: Record<string, { eq_weight: number; label: string; date: string; regime?: string; growth_pctile?: number; inflation_pctile?: number }>;
  factor_selections: Record<string, { name: string; ic: number }[]>;
}

// ─── Summary (all-indices overview) ──────────────────────────────────────────

export interface SummaryIndex {
  index_name: string;
  computed_at: string;
  eq_weight: number | null;
  label: string;
  regime: string;
  growth_pctile: number | null;
  inflation_pctile: number | null;
  category_signals: Record<string, { eq_weight: number; label: string; date: string }>;
  sharpe: number | null;
  alpha: number | null;
  max_dd: number | null;
  ann_return: number | null;
}
