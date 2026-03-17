'use client';

import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { Loader2, AlertTriangle, ChevronUp, ChevronDown } from 'lucide-react';
import { useCountUp } from '@/hooks/useCountUp';

// ── Types ───────────────────────────────────────────────────────────────────

interface CategorySignal {
  eq_weight: number | null;
  label: string;
  date: string;
  regime?: string;
}

interface RegimeIndex {
  index_name: string;
  computed_at: string;
  eq_weight: number | null;
  label: string;
  regime: string;
  growth_pctile: number | null;
  inflation_pctile: number | null;
  category_signals: Record<string, CategorySignal>;
}

interface RegimeSummaryResponse {
  indices: RegimeIndex[];
}

// ── Regime colors ───────────────────────────────────────────────────────────

const REGIME_COLORS: Record<string, string> = {
  Goldilocks: '#3fb950',
  Reflation: '#d29922',
  Stagflation: '#f85149',
  Deflation: '#bc8cff',
};

const SIGNAL_CLS: Record<string, string> = {
  'Risk-On': 'text-green-500',
  'Risk-Off': 'text-red-500',
  Neutral: 'text-muted-foreground/50',
};

// ── Heatmap helper ──────────────────────────────────────────────────────────

function eqWeightBg(v: number | null): string {
  if (v == null) return 'transparent';
  const t = Math.abs(v - 0.5) * 2;
  const a = 0.06 + Math.sqrt(t) * 0.2;
  return v >= 0.5 ? `rgba(34,197,94,${a})` : `rgba(239,68,68,${a})`;
}

function fmtPct(v: number | null): string {
  if (v == null) return '\u2014';
  return `${(v * 100).toFixed(0)}%`;
}

function fmtEq(v: number | null): string {
  if (v == null) return '\u2014';
  return (v * 100).toFixed(0);
}

// ── Sort ────────────────────────────────────────────────────────────────────

type SortCol = 'name' | 'eq_weight' | 'label' | 'regime' | 'growth' | 'inflation' | 'G' | 'I' | 'L' | 'T';
type SortDir = 'asc' | 'desc';

const SIGNAL_ORDER: Record<string, number> = { 'Risk-On': 3, Neutral: 2, 'Risk-Off': 1 };
const REGIME_ORDER: Record<string, number> = { Goldilocks: 4, Reflation: 3, Stagflation: 2, Deflation: 1 };

function getCatEq(idx: RegimeIndex, key: string): number {
  return idx.category_signals?.[key]?.eq_weight ?? -Infinity;
}

function getSortVal(idx: RegimeIndex, col: SortCol): number | string {
  switch (col) {
    case 'name': return idx.index_name;
    case 'eq_weight': return idx.eq_weight ?? -Infinity;
    case 'label': return SIGNAL_ORDER[idx.label] ?? 0;
    case 'regime': return REGIME_ORDER[idx.regime] ?? 0;
    case 'growth': return idx.growth_pctile ?? -Infinity;
    case 'inflation': return idx.inflation_pctile ?? -Infinity;
    case 'G': return getCatEq(idx, 'Growth');
    case 'I': return getCatEq(idx, 'Inflation');
    case 'L': return getCatEq(idx, 'Liquidity');
    case 'T': return getCatEq(idx, 'Tactical');
  }
}

// ── Shared header cell class ────────────────────────────────────────────────

const TH = 'text-right px-1 py-[5px] text-[9px] font-semibold uppercase tracking-[0.06em] text-muted-foreground/50 whitespace-nowrap';

// ── Summary bar ─────────────────────────────────────────────────────────────

function RegimePulse({ indices }: { indices: RegimeIndex[] }) {
  const stats = useMemo(() => {
    let riskOn = 0, neutral = 0, riskOff = 0, sumEq = 0, countEq = 0;
    const regimeCounts: Record<string, number> = {};

    for (const idx of indices) {
      if (idx.label === 'Risk-On') riskOn++;
      else if (idx.label === 'Risk-Off') riskOff++;
      else neutral++;

      if (idx.eq_weight != null) {
        sumEq += idx.eq_weight;
        countEq++;
      }
      regimeCounts[idx.regime] = (regimeCounts[idx.regime] ?? 0) + 1;
    }

    // Find dominant regime
    let dominantRegime = '';
    let maxCount = 0;
    for (const [r, c] of Object.entries(regimeCounts)) {
      if (c > maxCount) { maxCount = c; dominantRegime = r; }
    }

    return {
      riskOn, neutral, riskOff,
      avgEq: countEq ? sumEq / countEq : 0,
      dominantRegime,
    };
  }, [indices]);

  const regimeColor = REGIME_COLORS[stats.dominantRegime] ?? 'rgb(var(--muted-foreground))';

  const animAvgEq = useCountUp(stats.avgEq * 100);

  return (
    <div className="animate-fade-in stagger-1 flex flex-wrap items-center gap-x-6 gap-y-1 px-3 py-2 border-b border-border/15 bg-card/50">
      <span className="stat-label">Macro Regime</span>
      <span className="font-mono text-[12px] tabular-nums">
        <span className="text-green-500">{stats.riskOn}</span>
        <span className="text-muted-foreground/40 mx-0.5">/</span>
        <span className="text-muted-foreground/60">{stats.neutral}</span>
        <span className="text-muted-foreground/40 mx-0.5">/</span>
        <span className="text-red-500">{stats.riskOff}</span>
      </span>
      <span className="font-mono text-[12px] tabular-nums">
        <span className="stat-label mr-1">Avg Eq.Wt</span>
        <span className={stats.avgEq >= 0.5 ? 'text-green-500' : 'text-red-500'}>
          {animAvgEq.toFixed(0)}%
        </span>
      </span>
      <span className="font-mono text-[12px] tabular-nums inline-flex items-center gap-1.5">
        <span
          className="w-2 h-2 rounded-full transition-colors duration-500"
          style={{ backgroundColor: regimeColor }}
        />
        <span style={{ color: regimeColor }} className="font-semibold transition-colors duration-500">
          {stats.dominantRegime}
        </span>
      </span>
    </div>
  );
}

// ── Regime table ────────────────────────────────────────────────────────────

function RegimeTable({ indices }: { indices: RegimeIndex[] }) {
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

  const sorted = useMemo(() => {
    const arr = [...indices];
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
  }, [indices, sortCol, sortDir]);

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
          Regime Strategy Signals
        </span>
        <span className="text-[8px] font-mono text-muted-foreground/35">
          {indices.length} indices
        </span>
        <div className="flex-1 h-px bg-border/20" />
        <span className="text-[8px] text-muted-foreground/25 font-mono">
          {open ? '\u25be' : '\u25b8'}
        </span>
      </button>

      {open && (
        <div className="overflow-x-auto rounded-[3px] border border-border/25 bg-card">
          <table className="w-full border-collapse">
            <thead className="sticky top-0 z-20">
              <tr className="bg-card border-b border-border/15">
                <th
                  className="text-left px-2 py-[5px] text-[9px] font-semibold uppercase tracking-[0.06em] text-muted-foreground/50 sticky left-0 bg-card z-10 min-w-[70px] cursor-pointer select-none"
                  onClick={() => handleSort('name')}
                >
                  Index<SortIcon col="name" />
                </th>
                <th
                  className={`${TH} min-w-[44px] cursor-pointer select-none`}
                  onClick={() => handleSort('eq_weight')}
                >
                  Eq.Wt<SortIcon col="eq_weight" />
                </th>
                <th
                  className={`${TH} min-w-[52px] cursor-pointer select-none`}
                  onClick={() => handleSort('label')}
                >
                  Signal<SortIcon col="label" />
                </th>
                <th
                  className={`${TH} min-w-[68px] border-l border-border/15 cursor-pointer select-none`}
                  onClick={() => handleSort('regime')}
                >
                  Regime<SortIcon col="regime" />
                </th>
                <th
                  className={`${TH} min-w-[40px] cursor-pointer select-none`}
                  onClick={() => handleSort('growth')}
                >
                  Gro%<SortIcon col="growth" />
                </th>
                <th
                  className={`${TH} min-w-[40px] cursor-pointer select-none`}
                  onClick={() => handleSort('inflation')}
                >
                  Inf%<SortIcon col="inflation" />
                </th>
                <th
                  className={`${TH} min-w-[28px] border-l border-border/15 cursor-pointer select-none hidden sm:table-cell`}
                  onClick={() => handleSort('G')}
                  title="Growth category signal"
                >
                  G<SortIcon col="G" />
                </th>
                <th
                  className={`${TH} min-w-[28px] cursor-pointer select-none hidden sm:table-cell`}
                  onClick={() => handleSort('I')}
                  title="Inflation category signal"
                >
                  I<SortIcon col="I" />
                </th>
                <th
                  className={`${TH} min-w-[28px] cursor-pointer select-none hidden sm:table-cell`}
                  onClick={() => handleSort('L')}
                  title="Liquidity category signal"
                >
                  L<SortIcon col="L" />
                </th>
                <th
                  className={`${TH} min-w-[28px] cursor-pointer select-none hidden sm:table-cell`}
                  onClick={() => handleSort('T')}
                  title="Tactical category signal"
                >
                  T<SortIcon col="T" />
                </th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((idx, i) => {
                const regimeColor = REGIME_COLORS[idx.regime] ?? 'rgb(var(--muted-foreground))';
                const signalCls = SIGNAL_CLS[idx.label] ?? 'text-muted-foreground/50';
                const gEq = idx.category_signals?.Growth?.eq_weight ?? null;
                const iEq = idx.category_signals?.Inflation?.eq_weight ?? null;
                const lEq = idx.category_signals?.Liquidity?.eq_weight ?? null;
                const tEq = idx.category_signals?.Tactical?.eq_weight ?? null;

                return (
                  <tr
                    key={idx.index_name}
                    className={`border-t border-border/10 hover:bg-foreground/[0.03] transition-colors ${
                      i % 2 === 0 ? '' : 'bg-foreground/[0.015]'
                    }`}
                  >
                    {/* Name */}
                    <td className="px-2 py-[4px] text-[11px] font-medium text-foreground/90 whitespace-nowrap sticky left-0 bg-card z-10">
                      {i % 2 !== 0 && (
                        <span className="absolute inset-0 bg-foreground/[0.015] pointer-events-none" />
                      )}
                      <span className="relative">{idx.index_name}</span>
                    </td>

                    {/* Eq.Wt */}
                    <td
                      className="text-right px-1 py-[4px]"
                      style={{ backgroundColor: eqWeightBg(idx.eq_weight) }}
                    >
                      <span className="font-mono text-[11px] tabular-nums font-semibold text-foreground/80">
                        {fmtPct(idx.eq_weight)}
                      </span>
                    </td>

                    {/* Signal */}
                    <td className="text-right px-1 py-[4px]">
                      <span className={`font-mono text-[11px] tabular-nums font-semibold transition-colors duration-500 ${signalCls}`}>
                        {idx.label}
                      </span>
                    </td>

                    {/* Regime */}
                    <td className="text-right px-1 py-[4px] border-l border-border/15">
                      <span className="inline-flex items-center justify-end gap-1 font-mono text-[11px] tabular-nums">
                        <span
                          className="w-1.5 h-1.5 rounded-full shrink-0 transition-colors duration-500"
                          style={{ backgroundColor: regimeColor }}
                        />
                        <span className="transition-colors duration-500" style={{ color: regimeColor }}>{idx.regime}</span>
                      </span>
                    </td>

                    {/* Growth percentile */}
                    <td className="text-right px-1 py-[4px]">
                      <span className="font-mono text-[11px] tabular-nums text-foreground/60">
                        {fmtPct(idx.growth_pctile)}
                      </span>
                    </td>

                    {/* Inflation percentile */}
                    <td className="text-right px-1 py-[4px]">
                      <span className="font-mono text-[11px] tabular-nums text-foreground/60">
                        {fmtPct(idx.inflation_pctile)}
                      </span>
                    </td>

                    {/* Category mini-values G/I/L/T */}
                    <td
                      className="text-center px-0.5 py-[4px] border-l border-border/15 hidden sm:table-cell"
                      style={{ backgroundColor: eqWeightBg(gEq) }}
                    >
                      <span className="font-mono text-[10px] tabular-nums text-foreground/60">
                        {fmtEq(gEq)}
                      </span>
                    </td>
                    <td
                      className="text-center px-0.5 py-[4px] hidden sm:table-cell"
                      style={{ backgroundColor: eqWeightBg(iEq) }}
                    >
                      <span className="font-mono text-[10px] tabular-nums text-foreground/60">
                        {fmtEq(iEq)}
                      </span>
                    </td>
                    <td
                      className="text-center px-0.5 py-[4px] hidden sm:table-cell"
                      style={{ backgroundColor: eqWeightBg(lEq) }}
                    >
                      <span className="font-mono text-[10px] tabular-nums text-foreground/60">
                        {fmtEq(lEq)}
                      </span>
                    </td>
                    <td
                      className="text-center px-0.5 py-[4px] hidden sm:table-cell"
                      style={{ backgroundColor: eqWeightBg(tEq) }}
                    >
                      <span className="font-mono text-[10px] tabular-nums text-foreground/60">
                        {fmtEq(tEq)}
                      </span>
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

export default function MacroRegimeSummary() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['macro-regime-summary'],
    queryFn: () => apiFetchJson<RegimeSummaryResponse>('/api/macro/regime-strategy/summary'),
    staleTime: 300_000,
    refetchOnWindowFocus: false,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground/40" />
      </div>
    );
  }

  if (isError || !data?.indices?.length) {
    if (isError) {
      return (
        <div className="flex items-center justify-center gap-2 py-6">
          <AlertTriangle className="w-3.5 h-3.5 text-muted-foreground/30" />
          <span className="text-[11px] text-muted-foreground/30 font-mono">Regime data unavailable</span>
        </div>
      );
    }
    return null;
  }

  return (
    <div className="space-y-3">
      <RegimePulse indices={data.indices} />
      <div className="animate-fade-in stagger-2">
        <RegimeTable indices={data.indices} />
      </div>
    </div>
  );
}
