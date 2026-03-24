'use client';

import React, { useState, useMemo, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch, apiFetchJson } from '@/lib/api';
import { Loader2, AlertTriangle, Clock, TrendingUp, TrendingDown, ChevronUp, ChevronDown, ChevronLeft, ChevronRight, RefreshCw, Radio, Volume2, VolumeX } from 'lucide-react';

import { useCountUp } from '@/hooks/useCountUp';
import {
  type RRGMetric, type ScorecardAsset, type ScorecardCategory, type ScorecardsResponse,
  type SortCol, type SortDir,
  RETURN_COLS, MOBILE_HIDDEN_COLS, COL_SCALE, Q, QUADRANT_ORDER, TH,
  heatBg, valCls, fmtLevel, fmtRet, getSortVal,
} from './heatmap-utils';

// ── Phase badge ─────────────────────────────────────────────────────────────

const Phase = React.memo(function Phase({ rrg, label }: { rrg: RRGMetric; label: string }) {
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
});

// ── Sort icon (module-level for stable identity) ───────────────────────────

function SortIcon({ col, sortCol, sortDir }: { col: SortCol; sortCol: SortCol; sortDir: SortDir }) {
  if (sortCol !== col) return null;
  return sortDir === 'asc'
    ? <ChevronUp className="inline w-2.5 h-2.5 ml-0.5 -mt-px" />
    : <ChevronDown className="inline w-2.5 h-2.5 ml-0.5 -mt-px" />;
}

// ── Skeleton loader ─────────────────────────────────────────────────────────

function SkeletonRow({ cols }: { cols: number }) {
  return (
    <tr className="border-t border-border/10">
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-1.5 py-[5px]">
          <div className="h-2.5 bg-foreground/[0.04] rounded animate-pulse" style={{ width: i === 0 ? '60%' : '70%' }} />
        </td>
      ))}
    </tr>
  );
}

function ScorecardSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map(n => (
        <div key={n} className="dashboard-section" style={{ animationDelay: `${n * 80}ms` }}>
          <div className="px-3 py-2 border-b border-border/15">
            <div className="h-3 w-28 bg-foreground/[0.05] rounded animate-pulse" />
          </div>
          <table className="w-full">
            <tbody>
              {Array.from({ length: 4 }).map((_, i) => <SkeletonRow key={i} cols={8} />)}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

// ── Market Pulse ────────────────────────────────────────────────────────────

function MarketPulseHeader({
  categories,
  updatedAt,
  refreshing,
  onRefresh,
  open,
  onToggle,
}: {
  categories: ScorecardCategory[];
  updatedAt: number;
  refreshing: boolean;
  onRefresh: () => void;
  open: boolean;
  onToggle: () => void;
}) {
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

  const animGainers = useCountUp(stats.gainers);
  const animLosers = useCountUp(stats.losers);
  const animAvg = useCountUp(stats.avg1D);
  const animBest = useCountUp(stats.bestVal === -Infinity ? 0 : stats.bestVal);
  const animWorst = useCountUp(stats.worstVal === Infinity ? 0 : stats.worstVal);

  return (
    <div
      className={`animate-fade-in stagger-2 section-header${open ? ' open' : ''}`}
      onClick={onToggle}
    >
      <ChevronDown className={`w-3 h-3 text-muted-foreground/40 flex-shrink-0 transition-transform duration-200${open ? '' : ' -rotate-90'}`} />
      <span className="section-title">Market Pulse</span>

      {/* Gainers / Losers */}
      <span className="font-mono text-[11px] tabular-nums">
        <span className="text-success font-semibold">{Math.round(animGainers)}</span>
        <span className="text-muted-foreground/30 mx-0.5">/</span>
        <span className="text-destructive font-semibold">{Math.round(animLosers)}</span>
      </span>

      {/* Avg */}
      <span className="font-mono text-[11px] tabular-nums">
        <span className="stat-label mr-1">Avg 1D</span>
        <span className={`font-semibold ${stats.avg1D >= 0 ? 'text-success' : 'text-destructive'}`}>
          {animAvg > 0 ? '+' : ''}{animAvg.toFixed(2)}%
        </span>
      </span>

      {/* Divider */}
      <span className="hidden sm:block w-px h-3 bg-border/30" />

      {/* Best */}
      <span className="hidden sm:inline-flex font-mono text-[11px] tabular-nums items-center gap-1">
        <TrendingUp className="w-3 h-3 text-success/80" />
        <span className="text-foreground/60">{stats.bestAsset}</span>
        <span className="text-success font-semibold">+{animBest.toFixed(1)}</span>
      </span>

      {/* Worst */}
      <span className="hidden sm:inline-flex font-mono text-[11px] tabular-nums items-center gap-1">
        <TrendingDown className="w-3 h-3 text-destructive/80" />
        <span className="text-foreground/60">{stats.worstAsset}</span>
        <span className="text-destructive font-semibold">{animWorst.toFixed(1)}</span>
      </span>

      {/* Divider */}
      <span className="hidden lg:block w-px h-3 bg-border/30" />

      {/* RRG Quadrant counts */}
      <span className="hidden lg:inline-flex items-center gap-2">
        {Object.entries(stats.quadrants).map(([q, n]) => {
          const s = Q[q];
          return s ? (
            <span key={q} className={`font-mono text-[10px] tabular-nums font-semibold ${s.tx}`}>
              {s.short}&thinsp;{n}
            </span>
          ) : null;
        })}
      </span>

      {/* Right: timestamp + refresh */}
      <span className="ml-auto inline-flex items-center gap-2">
        <span className="inline-flex items-center gap-1 text-muted-foreground/35 font-mono text-[10px]">
          <Clock className="w-2.5 h-2.5" />
          {ts}
        </span>
        <button
          onClick={(e) => { e.stopPropagation(); onRefresh(); }}
          disabled={refreshing}
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-[calc(var(--radius)-2px)] text-[9px] font-mono uppercase tracking-wider text-muted-foreground/40 hover:text-foreground hover:bg-primary/[0.06] hover:border-primary/20 border border-transparent transition-all disabled:opacity-30"
          title="Clear cache and refresh all data"
        >
          <RefreshCw className={`w-2.5 h-2.5 ${refreshing ? 'animate-spin' : ''}`} />
        </button>
      </span>
    </div>
  );
}

// ── Memoised asset row ──────────────────────────────────────────────────────

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
    <tr
      className={`border-t border-border/[0.07] hover:bg-primary/[0.035] transition-colors duration-100 ${
        odd ? 'bg-foreground/[0.014]' : ''
      }`}
    >
      <td className="px-2 py-[3px] text-[10px] font-medium text-foreground/85 whitespace-nowrap sticky left-0 z-10" style={{ backgroundColor: 'rgb(var(--card))' }}>
        {odd && (
          <span className="absolute inset-0 bg-foreground/[0.014] pointer-events-none" />
        )}
        <span className="relative">{a.name}</span>
      </td>
      <td className="text-right px-1.5 py-[3px] font-mono text-[10px] tabular-nums text-foreground/65">
        {fmtLevel(a.level)}
      </td>
      <td
        className="text-right px-1.5 py-[3px] border-l border-border/10"
        style={{ backgroundColor: d1Bg, minWidth: '42px' }}
      >
        <span className={`font-mono text-[10px] tabular-nums font-semibold ${d1Cls}`}>
          {d1 != null ? (
            <>
              <span className="text-[8px]">{d1 > 0 ? '\u25b2' : d1 < 0 ? '\u25bc' : ''}</span>
              {Math.abs(d1).toFixed(1)}
            </>
          ) : '\u2014'}
        </span>
      </td>
      {heatCells.map(({ col, bg, cls, text }) => (
        <td
          key={col}
          className={`text-right px-1.5 py-[3px]${MOBILE_HIDDEN_COLS.has(col) ? ' hidden sm:table-cell' : ''}`}
          style={{ backgroundColor: bg }}
        >
          <span className={`font-mono text-[10px] tabular-nums ${cls}`}>
            {text}
          </span>
        </td>
      ))}
      <td className="text-center px-0.5 py-[3px] border-l border-border/10 hidden sm:table-cell">
        <Phase rrg={a.dynamic} label="Dynamic" />
      </td>
      <td className="text-center px-0.5 py-[3px] hidden sm:table-cell">
        <Phase rrg={a.tactical} label="Tactical" />
      </td>
    </tr>
  );
});

// ── Category table ──────────────────────────────────────────────────────────

const CategorySection = React.memo(function CategorySection({ cat }: { cat: ScorecardCategory }) {
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

  return (
    <div>
      {/* Sub-section divider header */}
      <div className="subsection-header border-t border-border/[0.08] bg-foreground/[0.015]">
        <span className="subsection-title">{cat.name}</span>
        <div className="flex-1 h-px bg-border/20" />
        <span className="hidden sm:inline-flex items-center gap-2 font-mono text-[9px]">
          {cat.as_of && (
            <span className="text-muted-foreground/30 border border-border/20 rounded px-1 py-px text-[8px]">
              {cat.as_of}
            </span>
          )}
          <span className="text-success font-semibold">{catStats.gainers}<span className="text-[7px] ml-px">&#8593;</span></span>
          <span className="text-destructive font-semibold">{catStats.losers}<span className="text-[7px] ml-px">&#8595;</span></span>
          <span className={`font-semibold ${catStats.avg >= 0 ? 'text-success' : 'text-destructive'}`}>
            {catStats.avg > 0 ? '+' : ''}{catStats.avg.toFixed(1)}%
          </span>
          <span className="text-muted-foreground/30 text-[8px]">vs {cat.benchmark}</span>
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead className="sticky top-0 z-20">
            <tr className="bg-foreground/[0.025]">
              <th
                className="text-left px-2 py-1 text-[9px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/60 sticky left-0 bg-card z-10 min-w-[70px] cursor-pointer select-none"
                onClick={() => handleSort('name')}
                style={{ backgroundColor: 'rgb(var(--card))' }}
              >
                Asset<SortIcon sortCol={sortCol} sortDir={sortDir} col="name" />
              </th>
              <th
                className={`${TH} min-w-[52px] cursor-pointer select-none py-1`}
                onClick={() => handleSort('level')}
              >
                Last<SortIcon sortCol={sortCol} sortDir={sortDir} col="level" />
              </th>
              <th
                className={`${TH} min-w-[42px] border-l border-border/15 cursor-pointer select-none py-1`}
                onClick={() => handleSort('1D')}
              >
                1D<SortIcon sortCol={sortCol} sortDir={sortDir} col="1D" />
              </th>
              {RETURN_COLS.slice(1).map(p => (
                <th
                  key={p}
                  className={`${TH} min-w-[36px] cursor-pointer select-none py-1${MOBILE_HIDDEN_COLS.has(p) ? ' hidden sm:table-cell' : ''}`}
                  onClick={() => handleSort(p)}
                >
                  {p}<SortIcon sortCol={sortCol} sortDir={sortDir} col={p} />
                </th>
              ))}
              <th
                className="text-center px-1 py-1 text-[9px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/60 border-l border-border/15 min-w-[34px] cursor-pointer select-none hidden sm:table-cell"
                onClick={() => handleSort('dynamic')}
                title="Dynamic RRG quadrant"
              >
                DYN<SortIcon sortCol={sortCol} sortDir={sortDir} col="dynamic" />
              </th>
              <th
                className="text-center px-1 py-1 text-[9px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/60 min-w-[34px] cursor-pointer select-none hidden sm:table-cell"
                onClick={() => handleSort('tactical')}
                title="Tactical RRG quadrant"
              >
                TAC<SortIcon sortCol={sortCol} sortDir={sortDir} col="tactical" />
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedAssets.map((a, i) => (
              <AssetRow key={a.name} asset={a} odd={i % 2 !== 0} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
});

// ── Intel Pulse Header ──────────────────────────────────────────────────────

interface IntelDateInfo {
  selectedDate: string | null;
  hasPrev: boolean;
  hasNext: boolean;
  onPrev: () => void;
  onNext: () => void;
  isPlaying: boolean;
  onToggleTTS: () => void;
}

function formatCompactDate(dateStr: string): string {
  try {
    const [y, m, d] = dateStr.split('-').map(Number);
    const date = new Date(y, m - 1, d);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return dateStr;
  }
}

function IntelPulseHeader({ open, onToggle, dateInfo }: { open: boolean; onToggle: () => void; dateInfo: IntelDateInfo | null }) {
  return (
    <div
      className={`animate-fade-in stagger-1 section-header${open ? ' open' : ''}`}
      onClick={onToggle}
    >
      <ChevronDown className={`w-3 h-3 text-muted-foreground/40 flex-shrink-0 transition-transform duration-200${open ? '' : ' -rotate-90'}`} />
      <Radio className="w-3 h-3 text-primary/70 flex-shrink-0" />
      <span className="section-title">Intel</span>

      {/* Date display */}
      {dateInfo?.selectedDate && (
        <span className="font-mono text-[10px] text-muted-foreground/50 tabular-nums">
          {formatCompactDate(dateInfo.selectedDate)}
        </span>
      )}

      {/* Right: nav + TTS */}
      <span className="ml-auto inline-flex items-center gap-1">
        {dateInfo && (
          <>
            <button
              onClick={(e) => { e.stopPropagation(); dateInfo.onPrev(); }}
              disabled={!dateInfo.hasPrev}
              className="flex items-center justify-center w-5 h-5 rounded text-muted-foreground hover:text-primary transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              aria-label="Previous report"
            >
              <ChevronLeft className="w-3 h-3" />
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); dateInfo.onNext(); }}
              disabled={!dateInfo.hasNext}
              className="flex items-center justify-center w-5 h-5 rounded text-muted-foreground hover:text-primary transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              aria-label="Next report"
            >
              <ChevronRight className="w-3 h-3" />
            </button>
            <span className="w-px h-3 bg-border/25 mx-0.5" />
            <button
              onClick={(e) => { e.stopPropagation(); dateInfo.onToggleTTS(); }}
              className={`flex items-center justify-center w-5 h-5 rounded transition-colors ${
                dateInfo.isPlaying
                  ? 'text-primary bg-primary/10'
                  : 'text-muted-foreground/50 hover:text-foreground'
              }`}
              aria-label={dateInfo.isPlaying ? 'Stop reading' : 'Read aloud'}
            >
              {dateInfo.isPlaying ? <VolumeX className="w-3 h-3" /> : <Volume2 className="w-3 h-3" />}
            </button>
          </>
        )}
      </span>
    </div>
  );
}

// ── Main ────────────────────────────────────────────────────────────────────

export default function Scorecards({ intelSlot }: { intelSlot?: React.ReactNode } = {}) {
  const queryClient = useQueryClient();
  const [refreshing, setRefreshing] = useState(false);
  const [intelOpen, setIntelOpen] = useState(true);
  const [pulseOpen, setPulseOpen] = useState(true);
  const [intelDateInfo, setIntelDateInfo] = useState<IntelDateInfo | null>(null);

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
      const freshData = await apiFetchJson<ScorecardsResponse>('/api/v1/scorecards/refresh', { method: 'POST' });
      queryClient.setQueryData(['scorecards'], freshData);
    } catch {
      await queryClient.refetchQueries({ queryKey: ['scorecards'] });
    } finally {
      setRefreshing(false);
    }
  }, [refreshing, queryClient]);

  return (
    <div className="p-2 sm:p-3 lg:p-4 space-y-3 overflow-y-auto">
      {/* ── Section 1: Intel Briefing (renders independently) ──────────── */}
      {intelSlot && (
        <div className="dashboard-section overflow-hidden flex flex-col">
          <IntelPulseHeader
            open={intelOpen}
            onToggle={() => setIntelOpen(o => !o)}
            dateInfo={intelDateInfo}
          />
          {intelOpen && (
            <div className="h-[240px] sm:h-[328px] animate-fade-in stagger-2 overflow-hidden flex flex-col">
              {React.cloneElement(intelSlot as React.ReactElement, {
                hideHeader: true,
                onDateInfo: setIntelDateInfo,
              })}
            </div>
          )}
        </div>
      )}

      {/* ── Section 2: Market Pulse (temporarily disabled) ────────────── */}
      {/*
      <div className="dashboard-section">
        <MarketPulseHeader
          categories={data.categories}
          updatedAt={dataUpdatedAt}
          refreshing={refreshing}
          onRefresh={handleRefresh}
          open={pulseOpen}
          onToggle={() => setPulseOpen(o => !o)}
        />

        {pulseOpen && data.categories.map((cat, i) => (
          <div key={cat.name} className={`animate-fade-in stagger-${Math.min(i + 1, 10)}`}>
            <CategorySection cat={cat} />
          </div>
        ))}
      </div>
      */}
    </div>
  );
}
