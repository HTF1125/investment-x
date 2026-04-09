import type { RegimeTab, RegimeModel } from './types';

// ────────────────────────────────────────────────────────────────────
// Hardcoded fallback colors/descriptions.
// These serve as a safety net when the API model response doesn't
// provide a color_map. Prefer `getRegimeColor(state, model)` helper
// below so the model's registered colors take precedence.
// ────────────────────────────────────────────────────────────────────

export const REGIME_COLORS: Record<string, string> = {
  // Macro (Growth × Inflation)
  Goldilocks:  '#48A86E',
  Reflation:   '#E0A848',
  Deflation:   '#6B8EAE',
  Stagflation: '#D65656',
  Mixed:       '#7D8596',
  // Composite Growth × Inflation joint states (institutional mapping)
  'Expansion+Falling':    '#48A86E', // goldilocks-like → muted green
  'Expansion+Rising':     '#E0A848', // reflation-like → amber
  'Contraction+Falling':  '#6B8EAE', // deflation-like → steel blue
  'Contraction+Rising':   '#D65656', // stagflation-like → rust red
  // Liquidity (Easing × Tightening)
  Easing:      '#48A86E',
  Tightening:  '#D65656',
  // Credit Cycle (Level × Trend)
  Expansion:   '#48A86E',
  LateCycle:   '#E0A848',
  Stress:      '#D65656',
  Recovery:    '#6B8EAE',
  // Dollar Cycle (Level × Trend)
  Weakness:    '#48A86E',
  Bottoming:   '#E0A848',
  Strength:    '#D65656',
  Reversal:    '#6B8EAE',
  // Liquidity2 (Level × Trend) — future
  LateEasing:  '#E0A848',
  Loosening:   '#6B8EAE',
  // Yield Curve (Steep × Flat)
  Steep:       '#48A86E',
  Flat:        '#D65656',
  // Real Rates (High × Low)
  High:        '#D65656',
  Low:         '#48A86E',
};

export const DIMENSION_COLORS: Record<string, string> = {
  Growth:    '#48A86E',
  Inflation: '#D65656',
  Liquidity: '#6B8EAE',
  Credit:    '#6B8EAE',
  Dollar:    '#48A86E',
  Level:     '#D65656',
  Trend:     '#E0A848',
  YieldCurve: '#6B8EAE',
  RealRates:  '#E0A848',
};

export const ASSET_COLORS: Record<string, string> = {
  SPY: '#6B8EAE', IWM: '#06b6d4', EFA: '#9AA4B2', EEM: '#fb923c',
  TLT: '#22d3ee', IEF: '#48A86E', TIP: '#65a30d', HYG: '#f87171',
  GLD: '#E0A848', SLV: '#cbd5e1', DBC: '#a16207', DBA: '#84cc16',
  XLE: '#f97316', XLU: '#8b5cf6', LQD: '#f43f5e', BIL: '#64748b',
};

export const REGIME_ORDER = ['Goldilocks', 'Reflation', 'Deflation', 'Stagflation'];

export const REGIME_DESCRIPTIONS: Record<string, string> = {
  // Macro
  Goldilocks:  'Growth ↑ · Inflation ↓ — ideal risk-on',
  Reflation:   'Growth ↑ · Inflation ↑ — cyclical / late-cycle',
  Deflation:   'Growth ↓ · Inflation ↓ — recessionary',
  Stagflation: 'Growth ↓ · Inflation ↑ — worst environment',
  Mixed:       'No regime > 30% confidence — ambiguous backdrop',
  // Liquidity
  Easing:      'Liquidity conditions supportive — spreads tight, curve positive',
  Tightening:  'Liquidity conditions stressed — spreads wide, curve inverted',
  // Credit Cycle
  Expansion:   'Spreads tight & falling — healthy credit cycle continuation',
  LateCycle:   'Spreads tight but rising — top-of-cycle warning',
  Stress:      'Spreads wide & rising — credit stress phase',
  Recovery:    'Spreads wide & falling — peak credit buy signal',
  // Dollar Cycle
  Weakness:    'Dollar weak & falling — sustained EM tailwind',
  Bottoming:   'Dollar weak but rising — EM warning / inflection',
  Strength:    'Dollar strong & rising — EM capital flight risk',
  Reversal:    'Dollar strong & falling — EM rally setup',
  // Liquidity2 (future)
  LateEasing:  'Liquidity easy but stress building — complacency warning',
  Loosening:   'Stressed liquidity turning supportive — peak buy',
  // Yield Curve
  Steep:       'Slope above rolling 5y history — expansionary stance, normal carry',
  Flat:        'Slope below rolling 5y history — late-cycle, restrictive, recession warning',
  // Real Rates
  High:        'Real rates above rolling 8y history — late-tightening. Contrarian setup for gold 12M fwd.',
  Low:         'Real rates below rolling 8y history — mid-easing. Post-rally consolidation for gold.',
};

export const REGIME_TABS: { key: RegimeTab; label: string }[] = [
  { key: 'current',     label: 'Overview' },
  { key: 'history',     label: 'History' },
  { key: 'assets',      label: 'Assets' },
];

/** Methodology is demoted from a top-level tab to an info icon in the
 * page header — most users never need it, but it's still discoverable
 * via a single click for those who do. */
export const METHODOLOGY_TAB: { key: RegimeTab; label: string } = {
  key: 'model',
  label: 'Methodology',
};

/** Quick-pick composition presets surfaced above the AxisDock so users
 * can jump to canonical 2-3 axis joint regimes in one click. Keys are
 * filtered against the live registry at render time so missing regimes
 * silently disappear from their preset (instead of breaking the row). */
export const COMPOSITION_PRESETS: {
  label: string;
  description: string;
  keys: string[];
}[] = [
  {
    label: 'Macro G·I',
    description: 'Growth × Inflation — the classic 4-quadrant macro framework',
    keys: ['growth', 'inflation'],
  },
  {
    label: 'Verdad Credit',
    description: 'Credit Level × Credit Trend — the Verdad credit cycle',
    keys: ['credit_level', 'credit_trend'],
  },
  {
    label: 'Verdad Dollar',
    description: 'Dollar Level × Dollar Trend — the dollar cycle',
    keys: ['dollar_level', 'dollar_trend'],
  },
  {
    label: 'Yield Curve',
    description: 'Inflation × Yield Curve — the inflation/term-premium read',
    keys: ['inflation', 'yield_curve'],
  },
  {
    label: 'Risk Triad',
    description: 'Growth × Inflation × Liquidity — the macro risk triad',
    keys: ['growth', 'inflation', 'liquidity'],
  },
  {
    label: 'Gold Driver',
    description: 'Real Rates × Inflation — the classical gold-pricing framework',
    keys: ['real_rates', 'inflation'],
  },
];

export const PLOTLY_CONFIG = {
  displayModeBar: false,
  responsive: true,
};

// ────────────────────────────────────────────────────────────────────
// Model-aware accessors.
// Always prefer these helpers over direct REGIME_COLORS lookup so
// regime-specific color_maps from the API take precedence.
// ────────────────────────────────────────────────────────────────────

const FALLBACK = '#9AA4B2';

/** Get color for a regime state.
 *
 * Order: frontend REGIME_COLORS (steel-tuned) → API color_map → FALLBACK.
 * Frontend steel palette takes precedence over backend colors so the
 * institutional palette stays consistent across all regime renderings.
 * The API color_map is still honored for custom regime states not in
 * REGIME_COLORS. */
export function getRegimeColor(
  state: string | undefined | null,
  model?: RegimeModel | null,
): string {
  if (!state) return FALLBACK;
  return REGIME_COLORS[state] ?? model?.color_map?.[state] ?? FALLBACK;
}

/** Get color for a dimension. Frontend steel palette takes precedence. */
export function getDimensionColor(
  dim: string | undefined | null,
  model?: RegimeModel | null,
): string {
  if (!dim) return FALLBACK;
  return DIMENSION_COLORS[dim] ?? model?.dimension_colors?.[dim] ?? FALLBACK;
}

/** Get a short descriptive label for a regime state.
 *
 * Prefers model.state_descriptions (which can disambiguate shared state
 * names like "Expansion" between credit and growth regimes), falls back
 * to the shared REGIME_DESCRIPTIONS constants.
 */
export function getRegimeDescription(
  state: string | undefined | null,
  model?: RegimeModel | null,
): string {
  if (!state) return '';
  return model?.state_descriptions?.[state] ?? REGIME_DESCRIPTIONS[state] ?? '';
}

/** Sort state names so the model's declared order comes first. */
export function getRegimeOrder(
  model?: RegimeModel | null,
  fallback: string[] = REGIME_ORDER,
): string[] {
  return model?.states ?? fallback;
}

