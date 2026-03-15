'use client';

import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { Loader2, AlertTriangle, Clock, TrendingUp, TrendingDown, ChevronUp, ChevronDown } from 'lucide-react';

// ── Types ───────────────────────────────────────────────────────────────────

interface RRGMetric {
  momentum: number | null;
  strength: number | null;
  quadrant: string | null;
}

interface ScorecardAsset {
  name: string;
  level: number | null;
  returns: Record<string, number | null>;
  dynamic: RRGMetric;
  tactical: RRGMetric;
}

interface ScorecardCategory {
  name: string;
  benchmark: string;
  assets: ScorecardAsset[];
}

interface ScorecardsResponse {
  categories: ScorecardCategory[];
}

const RETURN_COLS = ['1D', '1W', '1M', '3M', '6M', '1Y', '3Y', 'MTD', 'YTD'] as const;

// ── Heatmap ─────────────────────────────────────────────────────────────────

const COL_SCALE: Record<string, number> = {
  '1D': 2.5, '1W': 4, '1M': 7, '3M': 12, '6M': 20,
  '1Y': 35, '3Y': 50, 'MTD': 7, 'YTD': 20,
};

function heatBg(v: number | null, col: string): string {
  if (!v) return 'transparent';
  const t = Math.min(Math.abs(v) / (COL_SCALE[col] ?? 10), 1);
  const a = 0.06 + Math.sqrt(t) * 0.25;
  return v > 0 ? `rgba(34,197,94,${a})` : `rgba(239,68,68,${a})`;
}

function valCls(v: number | null): string {
  if (v === null || v === undefined) return 'text-muted-foreground/40';
  if (v > 0) return 'text-green-500';
  if (v < 0) return 'text-red-500';
  return 'text-muted-foreground/40';
}

function fmtLevel(v: number | null): string {
  if (v === null) return '\u2014';
  if (v >= 10000) return v.toLocaleString(undefined, { maximumFractionDigits: 0 });
  if (v >= 100) return v.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  if (v >= 10) return v.toFixed(2);
  return v.toFixed(4);
}

function fmtRet(v: number | null): string {
  if (v === null || v === undefined) return '\u2014';
  const s = v > 0 ? '+' : '';
  return `${s}${v.toFixed(1)}`;
}

// ── Phase badge ─────────────────────────────────────────────────────────────

const Q: Record<string, { dot: string; tx: string; short: string }> = {
  Leading:   { dot: 'bg-green-500',  tx: 'text-green-500',  short: 'LEAD' },
  Improving: { dot: 'bg-blue-500',   tx: 'text-blue-500',   short: 'IMPR' },
  Weakening: { dot: 'bg-amber-500',  tx: 'text-amber-500',  short: 'WEAK' },
  Lagging:   { dot: 'bg-red-500',    tx: 'text-red-500',    short: 'LAGG' },
};

function Phase({ rrg, label }: { rrg: RRGMetric; label: string }) {
  if (!rrg.quadrant) return <span className="text-muted-foreground/40 text-[8px]">&mdash;</span>;
  const s = Q[rrg.quadrant] ?? { dot: 'bg-muted', tx: 'text-muted-foreground/40', short: '?' };
  return (
    <span
      className={`inline-flex items-center gap-1 ${s.tx} text-[8px] font-bold uppercase tracking-wider leading-none`}
      title={`${label}: ${rrg.quadrant}\nMom ${rrg.momentum?.toFixed(2) ?? '\u2014'} / Str ${rrg.strength?.toFixed(2) ?? '\u2014'}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
      {s.short}
    </span>
  );
}

// ── Shared header cell class ────────────────────────────────────────────────

const TH = 'text-right px-1 py-[5px] text-[9px] font-semibold uppercase tracking-[0.06em] text-muted-foreground/50 whitespace-nowrap';

// ── Sort columns ────────────────────────────────────────────────────────────

type SortCol = 'name' | 'level' | typeof RETURN_COLS[number] | 'dynamic' | 'tactical';
type SortDir = 'asc' | 'desc';

const QUADRANT_ORDER: Record<string, number> = { Leading: 4, Improving: 3, Weakening: 2, Lagging: 1 };

function getSortVal(a: ScorecardAsset, col: SortCol): number | string {
  if (col === 'name') return a.name;
  if (col === 'level') return a.level ?? -Infinity;
  if (col === 'dynamic') return QUADRANT_ORDER[a.dynamic.quadrant ?? ''] ?? 0;
  if (col === 'tactical') return QUADRANT_ORDER[a.tactical.quadrant ?? ''] ?? 0;
  return a.returns[col] ?? -Infinity;
}

// ── Market Pulse ────────────────────────────────────────────────────────────

function MarketPulse({ categories, updatedAt }: { categories: ScorecardCategory[]; updatedAt: number }) {
  const stats = useMemo(() => {
    const all = categories.flatMap(c => c.assets);
    let gainers = 0, losers = 0, sum1D = 0, count1D = 0;
    let bestAsset = '', bestVal = -Infinity, worstAsset = '', worstVal = Infinity;
    const quadrants: Record<string, number> = {};

    for (const a of all) {
      const d = a.returns['1D'];
      if (d != null) {
        if (d > 0) gainers++;
        if (d < 0) losers++;
        sum1D += d;
        count1D++;
        if (d > bestVal) { bestVal = d; bestAsset = a.name; }
        if (d < worstVal) { worstVal = d; worstAsset = a.name; }
      }
      const q = a.dynamic.quadrant;
      if (q) quadrants[q] = (quadrants[q] ?? 0) + 1;
    }

    return { gainers, losers, avg1D: count1D ? sum1D / count1D : 0, bestAsset, bestVal, worstAsset, worstVal, quadrants };
  }, [categories]);

  const ts = new Date(updatedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-1 px-3 py-2 border-b border-border/15 bg-card/50">
      <span className="stat-label">Market Pulse</span>
      <span className="font-mono text-[12px] tabular-nums">
        <span className="text-green-500">{stats.gainers}</span>
        <span className="text-muted-foreground/40 mx-0.5">/</span>
        <span className="text-red-500">{stats.losers}</span>
      </span>
      <span className="font-mono text-[12px] tabular-nums">
        <span className="stat-label mr-1">Avg</span>
        <span className={stats.avg1D >= 0 ? 'text-green-500' : 'text-red-500'}>
          {stats.avg1D > 0 ? '+' : ''}{stats.avg1D.toFixed(2)}%
        </span>
      </span>
      <span className="font-mono text-[12px] tabular-nums inline-flex items-center gap-1">
        <TrendingUp className="w-3 h-3 text-green-500" />
        <span className="text-foreground/80">{stats.bestAsset}</span>
        <span className="text-green-500">+{stats.bestVal.toFixed(1)}</span>
      </span>
      <span className="font-mono text-[12px] tabular-nums inline-flex items-center gap-1">
        <TrendingDown className="w-3 h-3 text-red-500" />
        <span className="text-foreground/80">{stats.worstAsset}</span>
        <span className="text-red-500">{stats.worstVal.toFixed(1)}</span>
      </span>
      {Object.entries(stats.quadrants).map(([q, n]) => {
        const s = Q[q];
        return s ? (
          <span key={q} className={`font-mono text-[12px] tabular-nums ${s.tx}`}>
            {s.short} {n}
          </span>
        ) : null;
      })}
      <span className="ml-auto inline-flex items-center gap-1 text-muted-foreground/40 font-mono text-[10px]">
        <Clock className="w-3 h-3" />
        {ts}
      </span>
    </div>
  );
}

// ── Category table ──────────────────────────────────────────────────────────

function CategoryTable({ cat }: { cat: ScorecardCategory }) {
  const [open, setOpen] = useState(true);
  const [sortCol, setSortCol] = useState<SortCol>('name');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  const handleSort = (col: SortCol) => {
    if (sortCol === col) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortCol(col);
      setSortDir(col === 'name' ? 'asc' : 'desc');
    }
  };

  const sortedAssets = useMemo(() => {
    const arr = [...cat.assets];
    arr.sort((a, b) => {
      const va = getSortVal(a, sortCol);
      const vb = getSortVal(b, sortCol);
      if (typeof va === 'string' && typeof vb === 'string') {
        return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
      }
      const na = va as number, nb = vb as number;
      return sortDir === 'asc' ? na - nb : nb - na;
    });
    return arr;
  }, [cat.assets, sortCol, sortDir]);

  const catStats = useMemo(() => {
    let gainers = 0, losers = 0, sum = 0, count = 0;
    for (const a of cat.assets) {
      const d = a.returns['1D'];
      if (d != null) {
        if (d > 0) gainers++;
        if (d < 0) losers++;
        sum += d;
        count++;
      }
    }
    return { gainers, losers, avg: count ? sum / count : 0 };
  }, [cat.assets]);

  const SortIcon = ({ col }: { col: SortCol }) => {
    if (sortCol !== col) return null;
    return sortDir === 'asc'
      ? <ChevronUp className="inline w-2 h-2 ml-0.5" />
      : <ChevronDown className="inline w-2 h-2 ml-0.5" />;
  };

  return (
    <div>
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2 px-0.5 py-1 group"
      >
        <span className="text-[10px] font-bold uppercase tracking-[0.08em] text-foreground/90 group-hover:text-foreground transition-colors">
          {cat.name}
        </span>
        <span className="text-[8px] font-mono text-muted-foreground/40">
          {cat.assets.length} &middot; vs {cat.benchmark}
        </span>
        <span className="inline-flex items-center gap-1.5 text-[9px] font-mono">
          <span className="text-green-500">{catStats.gainers}&#8593;</span>
          <span className="text-red-500">{catStats.losers}&#8595;</span>
          <span className={catStats.avg >= 0 ? 'text-green-500/70' : 'text-red-500/70'}>
            avg {catStats.avg > 0 ? '+' : ''}{catStats.avg.toFixed(1)}%
          </span>
        </span>
        <div className="flex-1 h-px bg-border/20" />
        <span className="text-[8px] text-muted-foreground/40 font-mono">
          {open ? '\u25be' : '\u25b8'}
        </span>
      </button>

      {open && (
        <div className="overflow-x-auto rounded-[3px] border border-border/25 bg-card">
          <table className="w-full border-collapse">
            <thead className="sticky top-0 z-20">
              <tr className="bg-card border-b border-border/15">
                <th
                  className="text-left px-2 py-[5px] text-[9px] font-semibold uppercase tracking-[0.06em] text-muted-foreground/50 sticky left-0 bg-card z-10 min-w-[80px] cursor-pointer select-none"
                  onClick={() => handleSort('name')}
                >
                  Name<SortIcon col="name" />
                </th>
                <th
                  className={`${TH} min-w-[56px] cursor-pointer select-none`}
                  onClick={() => handleSort('level')}
                >
                  Last<SortIcon col="level" />
                </th>
                <th
                  className={`${TH} min-w-[44px] border-l border-border/15 cursor-pointer select-none`}
                  onClick={() => handleSort('1D')}
                >
                  &Delta;<SortIcon col="1D" />
                </th>
                {RETURN_COLS.slice(1).map(p => (
                  <th
                    key={p}
                    className={`${TH} min-w-[38px] cursor-pointer select-none`}
                    onClick={() => handleSort(p)}
                  >
                    {p}<SortIcon col={p} />
                  </th>
                ))}
                <th
                  className="text-center px-1 py-[5px] text-[9px] font-semibold uppercase tracking-[0.06em] text-muted-foreground/50 border-l border-border/15 min-w-[36px] cursor-pointer select-none hidden sm:table-cell"
                  onClick={() => handleSort('dynamic')}
                >
                  D<SortIcon col="dynamic" />
                </th>
                <th
                  className="text-center px-1 py-[5px] text-[9px] font-semibold uppercase tracking-[0.06em] text-muted-foreground/50 min-w-[36px] cursor-pointer select-none hidden sm:table-cell"
                  onClick={() => handleSort('tactical')}
                >
                  T<SortIcon col="tactical" />
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedAssets.map((a, i) => {
                const d1 = a.returns['1D'];
                return (
                  <tr
                    key={a.name}
                    className={`border-t border-border/10 hover:bg-foreground/[0.03] transition-colors ${
                      i % 2 === 0 ? '' : 'bg-foreground/[0.015]'
                    }`}
                  >
                    {/* Name */}
                    <td className="px-2 py-[4px] text-[11px] font-medium text-foreground/90 whitespace-nowrap sticky left-0 bg-card z-10">
                      {i % 2 !== 0 && (
                        <span className="absolute inset-0 bg-foreground/[0.015] pointer-events-none" />
                      )}
                      <span className="relative">{a.name}</span>
                    </td>

                    {/* Level */}
                    <td className="text-right px-1 py-[4px] font-mono text-[11px] tabular-nums text-foreground/80">
                      {fmtLevel(a.level)}
                    </td>

                    {/* 1D change with arrow */}
                    <td
                      className="text-right px-1 py-[4px] border-l border-border/15"
                      style={{ backgroundColor: heatBg(d1, '1D'), minWidth: '44px' }}
                    >
                      <span className={`font-mono text-[11px] tabular-nums font-semibold ${valCls(d1)}`}>
                        {d1 != null ? (
                          <>
                            <span className="text-[9px]">{d1 > 0 ? '\u25b2' : d1 < 0 ? '\u25bc' : ''}</span>
                            {Math.abs(d1).toFixed(1)}
                          </>
                        ) : '\u2014'}
                      </span>
                    </td>

                    {/* Remaining return columns */}
                    {RETURN_COLS.slice(1).map(col => {
                      const v = a.returns[col];
                      return (
                        <td
                          key={col}
                          className="text-right px-1 py-[4px]"
                          style={{ backgroundColor: heatBg(v, col) }}
                        >
                          <span className={`font-mono text-[11px] tabular-nums ${valCls(v)}`}>
                            {fmtRet(v)}
                          </span>
                        </td>
                      );
                    })}

                    {/* RRG */}
                    <td className="text-center px-0.5 py-[4px] border-l border-border/15 hidden sm:table-cell">
                      <Phase rrg={a.dynamic} label="Dynamic" />
                    </td>
                    <td className="text-center px-0.5 py-[4px] hidden sm:table-cell">
                      <Phase rrg={a.tactical} label="Tactical" />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Main ────────────────────────────────────────────────────────────────────

export default function Scorecards() {
  const { data, isLoading, isError, dataUpdatedAt } = useQuery({
    queryKey: ['scorecards'],
    queryFn: () => apiFetchJson<ScorecardsResponse>('/api/v1/scorecards'),
    staleTime: 1000 * 60 * 5,
    refetchOnWindowFocus: false,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground/40" />
      </div>
    );
  }

  if (isError || !data?.categories) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-2">
        <AlertTriangle className="w-4 h-4 text-muted-foreground/40" />
        <span className="text-xs text-muted-foreground/40">Failed to load scorecards</span>
      </div>
    );
  }

  return (
    <div className="p-2 sm:p-3 lg:p-4 space-y-3">
      <MarketPulse categories={data.categories} updatedAt={dataUpdatedAt} />
      {data.categories.map(cat => (
        <CategoryTable key={cat.name} cat={cat} />
      ))}
    </div>
  );
}
