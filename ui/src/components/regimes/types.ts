// Types for regime model API responses.
// Mirrors JSONB shapes from ix/db/models/regime_snapshot.py

// ── List models ─────────────────────────────────────────────────────

export type RegimeCategory = 'axis' | 'phase' | 'composite';

export interface RegimeModel {
  key: string;
  display_name: string;
  description: string;
  states: string[];
  dimensions: string[];
  has_strategy: boolean;
  category?: RegimeCategory;
  color_map: Record<string, string>;
  dimension_colors: Record<string, string>;
  state_descriptions?: Record<string, string>;
  default_params: Record<string, unknown>;
}

/** Compose endpoint response — same shape as a normal regime snapshot
 * but bundled together (current + timeseries + assets + meta + model). */
export interface ComposeResponse {
  model: RegimeModel;
  current_state: CurrentState;
  timeseries: TimeseriesData;
  asset_analytics: AssetAnalytics | null;
  meta: MetaData;
  strategy: StrategyData | null;
}

export interface ModelsResponse {
  models: RegimeModel[];
}

// ── Current state ───────────────────────────────────────────────────

export interface DimensionData {
  z: number;
  p: number;
  direction: string;
  score: number;
  total: number;
  components: { name: string; z: number }[];
  /** Trailing 24-month z-score history for sparkline rendering. */
  history?: number[];
  /** 3-month z acceleration (z[-1] - z[-3]) for cycle direction. */
  acceleration?: number | null;
}

export interface MarketSignal {
  name: string;
  value: string;
  aligned: boolean | null;
}

export interface MarketConfirmation {
  verdict: string;
  score: number;
  total: number;
  signals: MarketSignal[];
}

/** Historical context for the current joint state — populated by the
 * compose endpoint to power the Regime Profile panel. */
export interface RegimeStats {
  occurrences: number;          // # of distinct historical episodes
  months_in_state: number;      // total months ever in this state
  total_months: number;         // total months of composite history
  frequency_pct: number;        // months_in_state / total_months × 100
  avg_run_months: number;       // avg episode length when this state appears
  current_run_months: number;   // current consecutive run
  best_asset: AssetSnippet | null;
  worst_asset: AssetSnippet | null;
  top_separation: {
    ticker: string;
    cohens_d: number | null;
    p_value: number | null;
    best_state: string | null;
    worst_state: string | null;
  } | null;
}

export interface AssetSnippet {
  ticker: string;
  ann_ret: number | null;
  sharpe: number | null;
  win_rate: number | null;
  max_dd?: number | null;
}

/** Per-input-regime current state aligned to the joint composite's date.
 * Populated by the compose endpoint so AxisDock can show consistent
 * values for regimes that are part of the active composition. */
export interface InputRegimeState {
  dominant: string;
  dominant_probability: number;
  months_in_regime: number;
  date: string;
  conviction: number;
  z_history?: number[];
  z_acceleration?: number | null;
}

/** Single PM-actionable read produced by compose.py. Wraps the verdict,
 * the assets to tilt toward/away from, the four DC gates, and the watch
 * list of input axes likely to flip per the 12M Markov. */
export interface DecisionCard {
  verdict: 'RISK-ON' | 'RISK-OFF' | 'MIXED' | 'NEUTRAL';
  primary_ticker: string | null;
  tilt_long: string[];
  tilt_short: string[];
  gates: {
    dc1_separation: boolean;
    dc2_persistence: boolean;
    dc3_conviction: boolean;
    dc4_sample_size: boolean;
  };
  watch: { axis: string; from: string; to: string }[];
}

export interface CurrentState {
  date: string | null;
  dominant: string;
  dominant_probability: number;
  confirmed: string;
  conviction: number;
  months_in_regime: number;
  transitioning?: boolean;
  tactical_regime?: string;
  strategic_regime?: string;
  probabilities: Record<string, number>;
  forward_probabilities?: Record<string, number>;
  /** Multi-horizon Markov projections keyed by month count.
   * Backend serializes integer keys as strings ("1", "3", "6", "12"). */
  forward_horizons?: Record<string, Record<string, number>>;
  decision_card?: DecisionCard | null;
  input_states?: Record<string, InputRegimeState>;
  acceleration?: { growth: number | null; inflation: number | null };
  momentum_3m?: { growth: number | null; inflation: number | null; implied_regime: string | null };
  dimensions: Record<string, DimensionData>;
  current_allocation?: {
    macro_regime: string;
    liquidity_regime: string;
    weights: Record<string, number>;
  };
  blended_allocation?: Record<string, number>;
  liquidity_scaling?: { status: string; scale_factor_pct: number };
  nowcast?: { claims_4wma_z: number | null; model_growth_z: number | null };
  market_confirmation?: MarketConfirmation;
  recent_probabilities?: { dates: string[]; [regime: string]: number[] | string[] };
  regime_stats?: RegimeStats;
  error?: string;
}

export interface CurrentStateResponse {
  regime_type: string;
  computed_at: string;
  parameters: Record<string, unknown>;
  current_state: CurrentState;
}

// ── Timeseries ──────────────────────────────────────────────────────

export interface CorrelationMatrix {
  names: string[];
  matrix: number[][];
}

export interface TransitionRow {
  date: string;
  regime: string;
  probability: string;
}

export interface TimeseriesData {
  dates: string[];
  composites: Record<string, (number | null)[]>;
  probabilities: Record<string, (number | null)[]>;
  smoothed_probabilities: Record<string, (number | null)[]>;
  dominant: string[];
  confirmed: string[];
  conviction: (number | null)[];
  indicators: Record<string, (number | null)[]>;
  correlations?: Record<string, CorrelationMatrix>;
  transitions_recent?: TransitionRow[];
  transition_matrix?: Record<string, Record<string, number>>;
  durations?: Record<string, { avg_months: number; episodes: number }>;
}

export interface TimeseriesResponse {
  regime_type: string;
  computed_at: string;
  timeseries: TimeseriesData;
}

// ── Strategy ────────────────────────────────────────────────────────

export interface StrategyStats {
  cagr: number;
  ann_vol: number;
  sharpe: number;
  max_dd: number;
  months: number;
}

export interface StrategyModel {
  label: string;
  description: string;
  dates: string[];
  equity: number[];
  drawdown: number[];
  stats: StrategyStats;
}

export interface YearlyReturn {
  year: number;
  wf_best: number;
  diversified: number;
  spy: number;
  wf_alpha: number;
  div_alpha: number;
}

export interface StrategyData {
  start_date: string | null;
  end_date: string | null;
  months: number;
  wf_lookback: number;
  num_assets: number;
  lag_months: number;
  models: Record<string, StrategyModel>;
  regime_history: { dates: string[]; regimes: string[] };
  yearly_returns: YearlyReturn[];
  allocation_templates: Record<string, Record<string, number>>;
  assets: string[];
}

export interface StrategyResponse {
  regime_type: string;
  computed_at: string;
  strategy: StrategyData;
}

// ── Asset analytics ─────────────────────────────────────────────────

export interface AssetStat {
  ticker: string;
  ann_ret: number | null;
  ann_vol: number | null;
  sharpe: number | null;
  win_rate: number | null;
  max_dd: number | null;
  worst_mo: number | null;
  best_mo: number | null;
  months: number;
}

export interface RegimeAssetStats {
  months: number;
  assets: AssetStat[];
}

export interface LiquiditySplitBucket {
  label: string;
  description: string;
  months: number;
  assets: { ticker: string; ann_ret: number | null; sharpe: number | null; months: number }[];
}

export interface LiquiditySplit {
  supportive: LiquiditySplitBucket;
  stressed: LiquiditySplitBucket;
}

export interface RegimeSeparation {
  cohens_d: number | null;       // standardized mean diff: (best - worst) / pooled_std
  p_value: number | null;        // Welch t-test p-value for best vs worst
  best_state: string | null;
  worst_state: string | null;
  eta_sq: number | null;         // ANOVA η² across all states (reference)
  n: number;
}

export interface AssetAnalytics {
  per_regime_stats: Record<string, RegimeAssetStats>;
  regime_counts: Record<string, { months: number; pct: number }>;
  expected_returns: Record<string, number>;
  small_sample_regimes: string[];
  regime_separation?: Record<string, RegimeSeparation>;
  liquidity_splits: Record<string, LiquiditySplit>;
  tickers: string[];
}

export interface AssetAnalyticsResponse {
  regime_type: string;
  computed_at: string;
  asset_analytics: AssetAnalytics;
}

// ── Meta ────────────────────────────────────────────────────────────

export interface IndicatorDoc {
  name: string;
  code: string;
  lag: number;
  type: string;
  rationale: string;
}

export interface DimensionDoc {
  description: string;
  indicators: IndicatorDoc[];
}

export interface MetaData {
  model_name: string;
  description: string;
  states: string[];
  dimensions: string[];
  color_map: Record<string, string>;
  dimension_colors: Record<string, string>;
  methodology: Record<string, string>;
  indicator_docs?: Record<string, DimensionDoc>;
  regime_definitions?: Record<string, { growth?: string; inflation?: string; description: string }>;
}

export interface MetaResponse {
  regime_type: string;
  computed_at: string;
  meta: MetaData;
}

// ── Tab type ────────────────────────────────────────────────────────

export type RegimeTab =
  | 'current'
  | 'history'
  | 'indicators'
  | 'assets'
  | 'playbook'
  | 'strategy'
  | 'model';
