import type { ScreenerTab, SortField } from './types';

export const TABS: { key: ScreenerTab; label: string }[] = [
  { key: 'rankings', label: 'Rankings' },
  { key: 'flows', label: '13F Flows' },
  { key: 'methodology', label: 'Methodology' },
];

export interface ColumnDef {
  key: SortField;
  label: string;
  width: string;
  hidden?: boolean;
}

export const SORTABLE_COLUMNS: ColumnDef[] = [
  { key: 'rank', label: '#', width: 'w-10' },
  { key: 'symbol', label: 'Symbol', width: 'w-20' },
  { key: 'price', label: 'Price', width: 'w-20' },
  { key: 'vomo_composite', label: 'Composite', width: 'w-24' },
  { key: 'fund_count', label: 'Funds', width: 'w-16' },
  { key: 'rs_percentile', label: 'RS%', width: 'w-16' },
  { key: 'drawdown_52w', label: 'DD 52w', width: 'w-18' },
  { key: 'fwd_eps_growth', label: 'Fwd EPS', width: 'w-20' },
  { key: 'return_6m', label: 'Ret 6M', width: 'w-18' },
  // Hidden by default
  { key: 'vomo_1m', label: 'VOMO 1M', width: 'w-20', hidden: true },
  { key: 'vomo_6m', label: 'VOMO 6M', width: 'w-20', hidden: true },
  { key: 'vomo_1y', label: 'VOMO 1Y', width: 'w-20', hidden: true },
  { key: 'return_1m', label: 'Ret 1M', width: 'w-18', hidden: true },
  { key: 'return_1y', label: 'Ret 1Y', width: 'w-18', hidden: true },
  { key: 'market_cap', label: 'Mkt Cap', width: 'w-22', hidden: true },
  { key: 'avg_volume_30d', label: 'Avg Vol', width: 'w-20', hidden: true },
  { key: 'relative_volume', label: 'Rel Vol', width: 'w-18', hidden: true },
];

/** Default visible column keys */
export const DEFAULT_VISIBLE: Set<SortField> = new Set(
  SORTABLE_COLUMNS.filter(c => !c.hidden).map(c => c.key)
);

export const ACTION_COLORS: Record<string, string> = {
  NEW: 'text-success',
  INCREASED: 'text-success/80',
  DECREASED: 'text-destructive/80',
  SOLD: 'text-destructive',
  UNCHANGED: 'text-muted-foreground/50',
  UNKNOWN: 'text-muted-foreground/50',
};

export const CONSENSUS_COLORS: Record<string, string> = {
  Accumulating: 'text-success',
  Reducing: 'text-destructive',
  Mixed: 'text-warning',
  Unchanged: 'text-muted-foreground/50',
};

/** Green-to-red VOMO heatmap color */
export function vomoColor(value: number | null): string {
  if (value === null) return 'text-muted-foreground/40';
  if (value >= 4) return 'text-success';
  if (value >= 2) return 'text-success/80';
  if (value >= 1) return 'text-success/60';
  if (value >= 0) return 'text-muted-foreground';
  if (value >= -2) return 'text-destructive/60';
  return 'text-destructive';
}

/** VOMO cell background tint (low opacity) */
export function vomoBackground(value: number | null): string {
  if (value === null) return '';
  if (value >= 4) return 'bg-success/[0.08]';
  if (value >= 2) return 'bg-success/[0.06]';
  if (value >= 1) return 'bg-success/[0.04]';
  if (value >= 0) return '';
  if (value >= -2) return 'bg-destructive/[0.04]';
  return 'bg-destructive/[0.06]';
}

/** Trend dot color class */
export function trendColor(short: boolean, long: boolean): string {
  if (short && long) return 'bg-success';
  if (short || long) return 'bg-warning';
  return 'bg-destructive';
}

/** Format number with sign */
export function fmtNum(v: number | null, decimals = 1): string {
  if (v === null || v === undefined) return '-';
  return v >= 0 ? `+${v.toFixed(decimals)}` : v.toFixed(decimals);
}

/** Format percentage */
export function fmtPct(v: number | null): string {
  if (v === null || v === undefined) return '-';
  return `${(v * 100).toFixed(1)}%`;
}

/** Format large USD values (in thousands as reported) */
export function fmtUsd(v: number): string {
  const val = v * 1000; // Convert from thousands
  if (val >= 1e9) return `$${(val / 1e9).toFixed(1)}B`;
  if (val >= 1e6) return `$${(val / 1e6).toFixed(1)}M`;
  if (val >= 1e3) return `$${(val / 1e3).toFixed(0)}K`;
  return `$${val.toFixed(0)}`;
}

/** Format market cap (raw value, not in thousands) */
export function fmtMarketCap(v: number | null): string {
  if (v === null || v === undefined) return '-';
  if (v >= 1e12) return `$${(v / 1e12).toFixed(1)}T`;
  if (v >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(0)}M`;
  return `$${v.toFixed(0)}`;
}

/** Format share count */
export function fmtShares(v: number): string {
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(0)}K`;
  return v.toLocaleString();
}

/** Format volume (avg daily) */
export function fmtVolume(v: number | null): string {
  if (v === null || v === undefined) return '-';
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(0)}K`;
  return v.toLocaleString();
}
