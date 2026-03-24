import React from 'react';

// ── Types ───────────────────────────────────────────────────────────────────

export interface RRGMetric {
  momentum: number | null;
  strength: number | null;
  quadrant: string | null;
}

export interface ScorecardAsset {
  name: string;
  level: number | null;
  returns: Record<string, number | null>;
  dynamic: RRGMetric;
  tactical: RRGMetric;
}

export interface ScorecardCategory {
  name: string;
  benchmark: string;
  as_of: string | null;
  assets: ScorecardAsset[];
}

export interface ScorecardsResponse {
  categories: ScorecardCategory[];
}

// ── Constants ───────────────────────────────────────────────────────────────

export const RETURN_COLS = ['1D', '1W', '1M', '3M', '6M', '1Y', '3Y', 'MTD', 'YTD'] as const;
export const MOBILE_HIDDEN_COLS = new Set(['3M', '6M', '1Y', '3Y', 'MTD']);

export const COL_SCALE: Record<string, number> = {
  '1D': 2.5, '1W': 4, '1M': 7, '3M': 12, '6M': 20,
  '1Y': 35, '3Y': 50, 'MTD': 7, 'YTD': 20,
};

export const Q: Record<string, { dot: string; tx: string; short: string }> = {
  Leading:   { dot: 'bg-success',     tx: 'text-success',     short: 'LEAD' },
  Improving: { dot: 'bg-blue-500',    tx: 'text-blue-500',    short: 'IMPR' },
  Weakening: { dot: 'bg-warning',     tx: 'text-warning',     short: 'WEAK' },
  Lagging:   { dot: 'bg-destructive', tx: 'text-destructive', short: 'LAGG' },
};

export const QUADRANT_ORDER: Record<string, number> = { Leading: 4, Improving: 3, Weakening: 2, Lagging: 1 };

export const TH = 'text-right px-1.5 py-[3px] text-[9px] font-semibold uppercase tracking-[0.06em] text-muted-foreground/50 whitespace-nowrap';

// ── Sort types ──────────────────────────────────────────────────────────────

export type SortCol = 'name' | 'level' | typeof RETURN_COLS[number] | 'dynamic' | 'tactical';
export type SortDir = 'asc' | 'desc';

// ── Heatmap utilities ───────────────────────────────────────────────────────

export function heatBg(v: number | null, col: string): string {
  if (!v) return 'transparent';
  const t = Math.min(Math.abs(v) / (COL_SCALE[col] ?? 10), 1);
  const a = 0.07 + Math.sqrt(t) * 0.38;
  return v > 0 ? `rgb(var(--success) / ${a})` : `rgb(var(--destructive) / ${a})`;
}

export function valCls(v: number | null): string {
  if (v === null || v === undefined) return 'text-muted-foreground/40';
  if (v > 0) return 'text-success';
  if (v < 0) return 'text-destructive';
  return 'text-muted-foreground/40';
}

export function fmtLevel(v: number | null): string {
  if (v === null) return '\u2014';
  if (v >= 10000) return v.toLocaleString(undefined, { maximumFractionDigits: 0 });
  if (v >= 100) return v.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  if (v >= 10) return v.toFixed(2);
  return v.toFixed(4);
}

export function fmtRet(v: number | null): string {
  if (v === null || v === undefined) return '\u2014';
  const s = v > 0 ? '+' : '';
  return `${s}${v.toFixed(1)}`;
}

// ── Sort helper ─────────────────────────────────────────────────────────────

export function getSortVal(a: ScorecardAsset, col: SortCol): number | string {
  if (col === 'name') return a.name;
  if (col === 'level') return a.level ?? -Infinity;
  if (col === 'dynamic') return QUADRANT_ORDER[a.dynamic.quadrant ?? ''] ?? 0;
  if (col === 'tactical') return QUADRANT_ORDER[a.tactical.quadrant ?? ''] ?? 0;
  return a.returns[col] ?? -Infinity;
}
