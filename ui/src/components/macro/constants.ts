import type { Tab } from './types';

export const REGIME_COLORS: Record<string, string> = {
  Goldilocks: '#3fb950', Reflation: '#d29922', Stagflation: '#f85149', Deflation: '#bc8cff',
};

export const PHASE_COLORS: Record<string, string> = {
  Spring: '#3fb950', Summer: '#d29922', Fall: '#f85149', Winter: '#bc8cff',
};

export const TACTICAL_COLORS: Record<string, string> = {
  'Very Bearish': '#f85149', 'Bearish': '#f8514988', 'Neutral': '#a1a1aa',
  'Bullish': '#3fb95088', 'Very Bullish': '#3fb950',
};

export const REGIME_ORDER = ['Goldilocks', 'Reflation', 'Stagflation', 'Deflation'];

export const TABS: { key: Tab; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'regime', label: 'Regime' },
  { key: 'liquidity', label: 'Liquidity' },
  { key: 'tactical', label: 'Tactical' },
];

export const PLOTLY_CONFIG = { responsive: true, displaylogo: false, modeBarButtonsToRemove: ['lasso2d' as const, 'select2d' as const] };

export const CHART_M = { l: 52, r: 16, t: 28, b: 40 };
export const CHART_M_HBAR = { l: 140, r: 16, t: 28, b: 40 };

// ─── Axis defaults ──────────────────────────────────────────────────────────
// Ensure all axes are visible with tick labels, lines, and gridlines.

export const XAXIS_DATE = { type: 'date' as const, showticklabels: true, showline: true, linewidth: 1, showgrid: false };
export const YAXIS_BASE = { showticklabels: true, showline: true, linewidth: 1, showgrid: true };
