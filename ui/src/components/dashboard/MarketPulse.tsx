'use client';

import React, { useState, useMemo, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { Loader2, AlertTriangle, Clock, TrendingUp, TrendingDown, ChevronUp, ChevronDown, RefreshCw } from 'lucide-react';
import { useCountUp } from '@/hooks/useCountUp';
import {
  type RRGMetric, type ScorecardAsset, type ScorecardCategory, type ScorecardsResponse,
  type SortCol, type SortDir,
  RETURN_COLS, MOBILE_HIDDEN_COLS, Q, TH,
  heatBg, valCls, fmtLevel, fmtRet, getSortVal,
} from './heatmap-utils';

// ── Phase badge ──────────────────────────────────────────────────────────────

const Phase = React.memo(function Phase({ rrg, label }: { rrg: RRGMetric; label: string }) {
  if (!rrg.quadrant) return <span className="text-muted-foreground/40 text-[8px]">&mdash;</span>;
  const s = Q[rrg.quadrant] ?? { dot: 'bg-muted', tx: 'text-muted-foreground/40', short: '?' };
  return (
    <span className={`inline-flex items-center gap-1 ${s.tx} text-[8px] font-bold uppercase tracking-wider leading-none`}
      title={`${label}: ${rrg.quadrant}\nMom ${rrg.momentum?.toFixed(2) ?? '\u2014'} / Str ${rrg.strength?.toFixed(2) ?? '\u2014'}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
      {s.short}
    </span>
  );
});

// ── Sort icon ────────────────────────────────────────────────────────────────

function SortIcon({ col, sortCol, sortDir }: { col: SortCol; sortCol: SortCol; sortDir: SortDir }) {
  if (sortCol !== col) return null;
  return sortDir === 'asc' ? <ChevronUp className="inline w-2.5 h-2.5 ml-0.5 -mt-px" /> : <ChevronDown className="inline w-2.5 h-2.5 ml-0.5 -mt-px" />;
}

// ── Memoised asset row ───────────────────────────────────────────────────────

const AssetRow = React.memo(function AssetRow({ asset: a, odd }: { asset: ScorecardAsset; odd: boolean }) {
  const d1 = a.returns['1D'];

  const heatCells = useMemo(() =>
    RETURN_COLS.slice(1).map(col => {
      const v = a.returns[col];
      return { col, bg: heatBg(v, col), cls: valCls(v), text: fmtRet(v) };
    }),
    [a.returns],
  );

  const d1Bg = useMemo(() => heatBg(d1, '1D'), [d1]);
  const d1Cls = useMemo(() => valCls(d1), [d1]);

  return (
    <tr className={`border-t border-border/[0.07] hover:bg-primary/[0.035] transition-colors duration-100 ${odd ? 'bg-foreground/[0.014]' : ''}`}>
      <td className="px-2 py-[3px] text-[10px] font-medium text-foreground/85 whitespace-nowrap sticky left-0 z-10" style={{ backgroundColor: 'rgb(var(--card))' }}>
        {odd && <span className="absolute inset-0 bg-foreground/[0.014] pointer-events-none" />}
        <span className="relative">{a.name}</span>
      </td>
      <td className="text-right px-1.5 py-[3px] font-mono text-[10px] tabular-nums text-foreground/65">{fmtLevel(a.level)}</td>
      <td className="text-right px-1.5 py-[3px] border-l border-border/10" style={{ backgroundColor: d1Bg, minWidth: '42px' }}>
        <span className={`font-mono text-[10px] tabular-nums font-semibold ${d1Cls}`}>
          {d1 != null ? <><span className="text-[8px]">{d1 > 0 ? '\u25b2' : d1 < 0 ? '\u25bc' : ''}</span>{Math.abs(d1).toFixed(1)}</> : '\u2014'}
        </span>
      </td>
      {heatCells.map(({ col, bg, cls, text }) => (
        <td key={col} className={`text-right px-1.5 py-[3px]${MOBILE_HIDDEN_COLS.has(col) ? ' hidden sm:table-cell' : ''}`} style={{ backgroundColor: bg }}>
          <span className={`font-mono text-[10px] tabular-nums ${cls}`}>{text}</span>
        </td>
      ))}
      <td className="text-center px-0.5 py-[3px] border-l border-border/10 hidden sm:table-cell"><Phase rrg={a.dynamic} label="Dynamic" /></td>
      <td className="text-center px-0.5 py-[3px] hidden sm:table-cell"><Phase rrg={a.tactical} label="Tactical" /></td>
    </tr>
  );
});

// ── Category table ───────────────────────────────────────────────────────────

const CategorySection = React.memo(function CategorySection({ cat }: { cat: ScorecardCategory }) {
  const [sortCol, setSortCol] = useState<SortCol>('name');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  const handleSort = (col: SortCol) => {
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortCol(col); setSortDir(col === 'name' ? 'asc' : 'desc'); }
  };

  const sorted = useMemo(() => {
    const arr = [...cat.assets];
    arr.sort((a, b) => {
      const va = getSortVal(a, sortCol), vb = getSortVal(b, sortCol);
      if (typeof va === 'string' && typeof vb === 'string') return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
      return sortDir === 'asc' ? (va as number) - (vb as number) : (vb as number) - (va as number);
    });
    return arr;
  }, [cat.assets, sortCol, sortDir]);

  const stats = useMemo(() => {
    let g = 0, l = 0, sum = 0, n = 0;
    for (const a of cat.assets) { const d = a.returns['1D']; if (d != null) { if (d > 0) g++; if (d < 0) l++; sum += d; n++; } }
    return { g, l, avg: n ? sum / n : 0 };
  }, [cat.assets]);

  return (
    <div>
      <div className="subsection-header border-t border-border/[0.08] bg-foreground/[0.015]">
        <span className="subsection-title">{cat.name}</span>
        <div className="flex-1 h-px bg-border/20" />
        <span className="hidden sm:inline-flex items-center gap-2 font-mono text-[9px]">
          {cat.as_of && <span className="text-muted-foreground/30 border border-border/20 rounded px-1 py-px text-[8px]">{cat.as_of}</span>}
          <span className="text-success font-semibold">{stats.g}<span className="text-[7px] ml-px">&#8593;</span></span>
          <span className="text-destructive font-semibold">{stats.l}<span className="text-[7px] ml-px">&#8595;</span></span>
          <span className={`font-semibold ${stats.avg >= 0 ? 'text-success' : 'text-destructive'}`}>{stats.avg > 0 ? '+' : ''}{stats.avg.toFixed(1)}%</span>
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead className="sticky top-0 z-20">
            <tr className="bg-foreground/[0.025]">
              <th className="text-left px-2 py-1 text-[9px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/60 sticky left-0 bg-card z-10 min-w-[70px] cursor-pointer select-none" onClick={() => handleSort('name')} style={{ backgroundColor: 'rgb(var(--card))' }}>
                Asset<SortIcon sortCol={sortCol} sortDir={sortDir} col="name" />
              </th>
              <th className={`${TH} min-w-[52px] cursor-pointer select-none py-1`} onClick={() => handleSort('level')}>Last<SortIcon sortCol={sortCol} sortDir={sortDir} col="level" /></th>
              <th className={`${TH} min-w-[42px] border-l border-border/15 cursor-pointer select-none py-1`} onClick={() => handleSort('1D')}>1D<SortIcon sortCol={sortCol} sortDir={sortDir} col="1D" /></th>
              {RETURN_COLS.slice(1).map(p => (
                <th key={p} className={`${TH} min-w-[36px] cursor-pointer select-none py-1${MOBILE_HIDDEN_COLS.has(p) ? ' hidden sm:table-cell' : ''}`} onClick={() => handleSort(p)}>
                  {p}<SortIcon sortCol={sortCol} sortDir={sortDir} col={p} />
                </th>
              ))}
              <th className="text-center px-1 py-1 text-[9px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/60 border-l border-border/15 min-w-[34px] cursor-pointer select-none hidden sm:table-cell" onClick={() => handleSort('dynamic')}>DYN<SortIcon sortCol={sortCol} sortDir={sortDir} col="dynamic" /></th>
              <th className="text-center px-1 py-1 text-[9px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/60 min-w-[34px] cursor-pointer select-none hidden sm:table-cell" onClick={() => handleSort('tactical')}>TAC<SortIcon sortCol={sortCol} sortDir={sortDir} col="tactical" /></th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((a, i) => (
              <AssetRow key={a.name} asset={a} odd={i % 2 !== 0} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
});

// ── Header ───────────────────────────────────────────────────────────────────

function PulseHeader({ categories, updatedAt, refreshing, onRefresh, collapsed, onToggleCollapse }: {
  categories: ScorecardCategory[]; updatedAt: number; refreshing: boolean; onRefresh: () => void;
  collapsed?: boolean; onToggleCollapse?: () => void;
}) {
  const stats = useMemo(() => {
    const all = categories.flatMap(c => c.assets);
    let g = 0, l = 0, sum = 0, n = 0, bA = '', bV = -Infinity, wA = '', wV = Infinity;
    for (const a of all) {
      const d = a.returns['1D'];
      if (d != null) { if (d > 0) g++; if (d < 0) l++; sum += d; n++; if (d > bV) { bV = d; bA = a.name; } if (d < wV) { wV = d; wA = a.name; } }
    }
    return { g, l, avg: n ? sum / n : 0, bA, bV, wA, wV };
  }, [categories]);

  const ts = new Date(updatedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const aG = useCountUp(stats.g), aL = useCountUp(stats.l), aAvg = useCountUp(stats.avg);

  return (
    <div className="section-header flex-wrap">
      <span className="section-title">Markets</span>
      {onToggleCollapse && (
        <button onClick={onToggleCollapse} className="w-5 h-5 flex items-center justify-center rounded-full text-muted-foreground/25 hover:text-foreground/50 hover:bg-foreground/[0.06] transition-all" title={collapsed ? 'Expand' : 'Collapse'}>
          <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${collapsed ? '-rotate-90' : ''}`} />
        </button>
      )}
      <span className="font-mono text-[11px] tabular-nums">
        <span className="text-success font-semibold">{Math.round(aG)}</span>
        <span className="text-muted-foreground/30 mx-0.5">/</span>
        <span className="text-destructive font-semibold">{Math.round(aL)}</span>
      </span>
      <span className="font-mono text-[11px] tabular-nums">
        <span className="stat-label mr-1">Avg</span>
        <span className={`font-semibold ${stats.avg >= 0 ? 'text-success' : 'text-destructive'}`}>{aAvg > 0 ? '+' : ''}{aAvg.toFixed(2)}%</span>
      </span>
      <span className="hidden sm:inline-flex font-mono text-[10px] tabular-nums items-center gap-1">
        <TrendingUp className="w-2.5 h-2.5 text-success/80" />
        <span className="text-foreground/60">{stats.bA}</span>
        <span className="text-success font-semibold">+{stats.bV === -Infinity ? 0 : stats.bV.toFixed(1)}</span>
      </span>
      <span className="hidden sm:inline-flex font-mono text-[10px] tabular-nums items-center gap-1">
        <TrendingDown className="w-2.5 h-2.5 text-destructive/80" />
        <span className="text-foreground/60">{stats.wA}</span>
        <span className="text-destructive font-semibold">{stats.wV === Infinity ? 0 : stats.wV.toFixed(1)}</span>
      </span>
      <span className="ml-auto inline-flex items-center gap-2">
        <span className="inline-flex items-center gap-1 text-muted-foreground/35 font-mono text-[10px]"><Clock className="w-2.5 h-2.5" />{ts}</span>
        <button onClick={onRefresh} disabled={refreshing} className="btn-icon" title="Refresh">
          <RefreshCw className={`w-2.5 h-2.5 ${refreshing ? 'animate-spin' : ''}`} />
        </button>
      </span>
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

export default function MarketPulse({ collapsed, onToggleCollapse }: { collapsed?: boolean; onToggleCollapse?: () => void } = {}) {
  const queryClient = useQueryClient();
  const [refreshing, setRefreshing] = useState(false);

  const { data, isLoading, isError, dataUpdatedAt } = useQuery({
    queryKey: ['scorecards'],
    queryFn: () => apiFetchJson<ScorecardsResponse>('/api/v1/scorecards'),
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    refetchOnWindowFocus: false,
  });

  const handleRefresh = useCallback(async () => {
    if (refreshing) return;
    setRefreshing(true);
    try {
      const fresh = await apiFetchJson<ScorecardsResponse>('/api/v1/scorecards/refresh', { method: 'POST' });
      queryClient.setQueryData(['scorecards'], fresh);
    } catch { await queryClient.refetchQueries({ queryKey: ['scorecards'] }); }
    finally { setRefreshing(false); }
  }, [refreshing, queryClient]);

  if (isLoading) {
    return <div className="h-32 flex items-center justify-center"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground/30" /></div>;
  }

  if (isError || !data?.categories) {
    return (
      <div className="flex items-center justify-center py-8 gap-2">
        <AlertTriangle className="w-3.5 h-3.5 text-muted-foreground/30" />
        <span className="text-[11px] text-muted-foreground/30 font-mono">Failed to load market data</span>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col min-h-0 overflow-hidden">
      <PulseHeader categories={data.categories} updatedAt={dataUpdatedAt} refreshing={refreshing} onRefresh={handleRefresh} collapsed={collapsed} onToggleCollapse={onToggleCollapse} />
      {!collapsed && (
        <div className="flex-1 min-h-0 overflow-y-auto">
          {data.categories.map((cat, i) => (
            <div key={cat.name} className={`animate-fade-in stagger-${Math.min(i + 1, 10)}`}>
              <CategorySection cat={cat} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
