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

export const REGIME_SIGNAL_COLORS: Record<string, string> = {
  'Risk-On': '#3fb950', 'Neutral': '#d29922', 'Risk-Off': '#f85149',
};

export const TABS: { key: Tab; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'methodology', label: 'Methodology' },
  { key: 'strategy', label: 'Backtest' },
  { key: 'factors', label: 'Factors' },
  { key: 'regime', label: 'Regime' },
  { key: 'momentum', label: 'Momentum' },
];

export const STRAT_COLORS: Record<string, string> = {
  Growth: '#3fb950', Inflation: '#f0883e', Liquidity: '#58a6ff',
  Tactical: '#bc8cff', Regime: '#f85149', Blended: '#39d2c0',
};

export const STRAT_ORDER = ['Growth', 'Inflation', 'Liquidity', 'Tactical', 'Regime', 'Blended'];

// ─── Regime background visual system ────────────────────────────────────────
// Three-layer approach: bottom strip + full-height tint + vertical transition lines

const REGIME_STRIP_COLORS: Record<string, { dark: string; light: string }> = {
  Bull:    { dark: 'rgba(63,185,80,0.60)',  light: 'rgba(22,120,50,0.55)' },
  Bear:    { dark: 'rgba(248,81,73,0.60)',  light: 'rgba(210,45,45,0.55)' },
  Neutral: { dark: 'rgba(210,153,34,0.45)', light: 'rgba(148,98,0,0.40)' },
};

// Mid-layer: fades from strip upward — simulates gradient
const REGIME_FADE_COLORS: Record<string, { dark: string; light: string }> = {
  Bull:    { dark: 'rgba(63,185,80,0.04)',  light: 'rgba(22,120,50,0.03)' },
  Bear:    { dark: 'rgba(248,81,73,0.04)',  light: 'rgba(210,45,45,0.03)' },
  Neutral: { dark: 'rgba(210,153,34,0.03)', light: 'rgba(148,98,0,0.02)' },
};

const REGIME_TINT_COLORS: Record<string, { dark: string; light: string }> = {
  Bull:    { dark: 'rgba(63,185,80,0.09)',  light: 'rgba(22,120,50,0.065)' },
  Bear:    { dark: 'rgba(248,81,73,0.09)',  light: 'rgba(210,45,45,0.065)' },
  Neutral: { dark: 'rgba(210,153,34,0.06)', light: 'rgba(148,98,0,0.04)' },
};

const REGIME_LINE_COLORS: Record<string, { dark: string; light: string }> = {
  Bull:    { dark: 'rgba(63,185,80,0.20)',  light: 'rgba(22,120,50,0.15)' },
  Bear:    { dark: 'rgba(248,81,73,0.20)',  light: 'rgba(210,45,45,0.15)' },
  Neutral: { dark: 'rgba(210,153,34,0.18)', light: 'rgba(148,98,0,0.14)' },
};

/** Build regime background shapes — all regimes: tint + fade + strip + transition lines */
export function buildRegimeShapes(
  spans: { x0: string; x1: string; regime: string }[],
  theme: 'light' | 'dark',
): any[] {
  const shapes: any[] = [];
  for (let i = 0; i < spans.length; i++) {
    const s = spans[i];
    const regime = s.regime as keyof typeof REGIME_STRIP_COLORS;
    const strip = REGIME_STRIP_COLORS[regime] ?? REGIME_STRIP_COLORS.Neutral;
    const fade = REGIME_FADE_COLORS[regime] ?? REGIME_FADE_COLORS.Neutral;
    const tint = REGIME_TINT_COLORS[regime] ?? REGIME_TINT_COLORS.Neutral;
    const line = REGIME_LINE_COLORS[regime] ?? REGIME_LINE_COLORS.Neutral;

    // Layer 1: Full-height regime tint
    shapes.push({
      type: 'rect', xref: 'x', yref: 'paper',
      x0: s.x0, x1: s.x1, y0: 0, y1: 1,
      fillcolor: tint[theme], line: { width: 0 }, layer: 'below',
    });

    // Layer 2: Bottom fade — extra intensity in lower 20% for gradient effect
    shapes.push({
      type: 'rect', xref: 'x', yref: 'paper',
      x0: s.x0, x1: s.x1, y0: 0, y1: 0.20,
      fillcolor: fade[theme], line: { width: 0 }, layer: 'below',
    });

    // Layer 3: Bottom strip — solid color anchor
    shapes.push({
      type: 'rect', xref: 'x', yref: 'paper',
      x0: s.x0, x1: s.x1, y0: 0, y1: 0.045,
      fillcolor: strip[theme], line: { width: 0 }, layer: 'below',
    });

    // Vertical transition lines at regime boundaries
    if (i > 0) {
      shapes.push({
        type: 'line', xref: 'x', yref: 'paper',
        x0: s.x0, x1: s.x0, y0: 0, y1: 1,
        line: { color: line[theme], width: 0.75, dash: 'dot' }, layer: 'below',
      });
    }
  }
  return shapes;
}

export const PLOTLY_CONFIG = { responsive: true, displaylogo: false, modeBarButtonsToRemove: ['lasso2d' as const, 'select2d' as const], scrollZoom: false };

export const CHART_M = { l: 52, r: 16, t: 28, b: 40 };
export const CHART_M_HBAR = { l: 140, r: 16, t: 28, b: 40 };

// ─── Axis defaults ──────────────────────────────────────────────────────────
// Ensure all axes are visible with tick labels, lines, and gridlines.

export const XAXIS_DATE = { type: 'date' as const, showticklabels: true, showline: true, linewidth: 1, showgrid: false };
export const YAXIS_BASE = { showticklabels: true, showline: true, linewidth: 1, showgrid: true };
