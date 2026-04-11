// Formatting helpers for regime UI

export function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  return `${(v * 100).toFixed(digits)}%`;
}

export function fmtPctSigned(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  const sign = v >= 0 ? '+' : '';
  return `${sign}${(v * 100).toFixed(digits)}%`;
}

export function fmtZ(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  const sign = v >= 0 ? '+' : '';
  return `${sign}${v.toFixed(digits)}`;
}

export function fmtNum(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  return v.toFixed(digits);
}

export function safeNum(v: number | null | undefined, fallback = 0): number {
  if (v === null || v === undefined || Number.isNaN(v)) return fallback;
  return v;
}

/** Theme-aware color for an annual return value. Banded:
 *  > +5%  → success, > −5% → warning, otherwise destructive. */
export function retColor(ret: number | null | undefined): string {
  if (ret === null || ret === undefined || Number.isNaN(ret)) {
    return 'rgb(var(--muted-foreground) / 0.4)';
  }
  if (ret > 0.05) return 'rgb(var(--success))';
  if (ret > -0.05) return 'rgb(var(--warning))';
  return 'rgb(var(--destructive))';
}

/** Convert hex color to rgb string. */
export function hexToRgb(hex: string): string {
  const h = hex.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `${r},${g},${b}`;
}

/** Build dominant-regime spans for chart background shading. */
export function buildRegimeSpans(
  dates: string[],
  dominant: string[],
): { x0: string; x1: string; regime: string }[] {
  if (dates.length === 0 || dominant.length === 0) return [];
  const spans: { x0: string; x1: string; regime: string }[] = [];
  let curRegime = dominant[0];
  let segStart = dates[0];
  for (let i = 1; i < dates.length; i++) {
    if (dominant[i] !== curRegime) {
      spans.push({ x0: segStart, x1: dates[i], regime: curRegime });
      curRegime = dominant[i];
      segStart = dates[i];
    }
  }
  spans.push({ x0: segStart, x1: dates[dates.length - 1], regime: curRegime });
  return spans;
}
