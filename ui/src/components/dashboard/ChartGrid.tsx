'use client';

import React, { useState, useEffect, memo } from 'react';
import { useQuery } from '@tanstack/react-query';
import dynamic from 'next/dynamic';
import { apiFetchJson } from '@/lib/api';
import { useTheme } from '@/context/ThemeContext';
import { Loader2, ArrowLeft, Activity, AlertTriangle, BarChart3 } from 'lucide-react';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import type { ApiIndex } from './Technicals';
import VomoSparkline from './VomoSparkline';

import { applyChartTheme, CHART_SEMANTIC } from '@/lib/chartTheme';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false, loading: () => <div /> }) as any;

// ── Types ──

interface VamsSummary {
  indices: ApiIndex[];
  cacri: number;
  cross_asset_vams: Record<string, number>;
  computed_at: string;
}

// ── Helpers ──

function fmtPrice(v: number | null | undefined): string {
  if (v == null) return '—';
  if (v >= 10000) return v.toLocaleString(undefined, { maximumFractionDigits: 0 });
  if (v >= 100) return v.toLocaleString(undefined, { maximumFractionDigits: 1 });
  return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function fmtReturn(v: number | null | undefined): { text: string; cls: string } {
  if (v == null) return { text: '—', cls: 'table-cell-neutral' };
  const pct = v / 100;
  const sign = pct > 0 ? '+' : '';
  const text = `${sign}${(pct * 100).toFixed(1)}%`;
  if (pct > 0.001) return { text, cls: 'table-cell-positive' };
  if (pct < -0.001) return { text, cls: 'table-cell-negative' };
  return { text, cls: 'table-cell-neutral' };
}

function regimeColor(regime: string): string {
  if (regime === 'Bull') return 'text-success';
  if (regime === 'Bear') return 'text-destructive';
  return 'text-warning';
}

// ── Market Status Bar ──

const MarketStatusBar = memo(function MarketStatusBar({
  summary,
  displayIndices,
  detailsLoading,
  indexCount,
  onOpenBriefing,
}: {
  summary: VamsSummary | undefined;
  displayIndices: ApiIndex[];
  detailsLoading: boolean;
  indexCount: number;
  onOpenBriefing?: () => void;
}) {
  if (!summary) return null;

  const bulls = displayIndices.filter(i => i.regime === 'Bull').length;
  const bears = displayIndices.filter(i => i.regime === 'Bear').length;
  const neutrals = displayIndices.filter(i => i.regime === 'Neutral').length;
  const cacri = summary.cacri ?? 0;
  const cacriPositive = cacri >= 0;

  return (
    <div className="page-header">
      <h1 className="page-header-title">DASHBOARD</h1>
      <div className="page-header-divider" aria-hidden />

      {/* CACRI */}
      <div className="flex items-center gap-1.5" title="Cross-Asset Composite Risk Indicator — aggregate risk score across all tracked indices">
        <Activity className="w-3 h-3 text-muted-foreground" />
        <span className="stat-label">CACRI</span>
        <span className={`font-mono text-[13px] font-bold tabular-nums ${cacriPositive ? 'text-success' : 'text-destructive'}`}>
          {cacri > 0 ? '+' : ''}{cacri.toFixed(2)}
        </span>
      </div>

      <div className="page-header-divider" aria-hidden />

      {/* Regime counts */}
      <div className="flex items-center gap-2">
        <span className="font-mono text-[11px] tabular-nums text-success font-semibold">{bulls}B</span>
        <span className="font-mono text-[11px] tabular-nums text-destructive font-semibold">{bears}B</span>
        <span className="font-mono text-[11px] tabular-nums text-warning font-semibold">{neutrals}N</span>
      </div>

      <div className="page-header-divider" aria-hidden />

      {/* Index count + loading */}
      <span className="text-[10px] font-mono uppercase tracking-[0.08em] text-muted-foreground tabular-nums">
        {indexCount} INDICES
      </span>
      {detailsLoading && <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />}

      <div className="flex-1" />

      {/* Timestamp */}
      {summary.computed_at && (
        <div className="hidden sm:flex items-baseline gap-1.5">
          <span className="stat-label">AS OF</span>
          <span className="text-[10.5px] font-mono tabular-nums text-foreground">
            {new Date(summary.computed_at).toLocaleString('en-US', {
              month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false,
            })}
          </span>
        </div>
      )}

      {/* Briefing */}
      {onOpenBriefing && (
        <button
          onClick={onOpenBriefing}
          className="h-6 px-2.5 text-[10px] font-mono font-semibold uppercase tracking-[0.10em] border border-border/60 text-muted-foreground hover:text-foreground hover:border-border transition-colors"
        >
          BRIEFING
        </button>
      )}
    </div>
  );
});

// ── Mini Chart Card ──

const MiniChart = memo(function MiniChart({ index, theme, vamsScore, onClick }: {
  index: ApiIndex;
  theme: 'light' | 'dark';
  vamsScore: number | undefined;
  onClick: () => void;
}) {
  const dp = index.daily_prices;
  const dailyRet = index.daily_ret != null ? index.daily_ret / 100 : null;
  const isUp = (dailyRet ?? 0) >= 0;
  const vomo = index.vomo?.composite ?? null;
  const vomoHistory = index.vomo?.history?.values;
  const isDark = theme === 'dark';
  const sem = CHART_SEMANTIC[theme];

  const ret1m = fmtReturn(index.ret_1m);
  const ret3m = fmtReturn(index.ret_3m);
  const ret6m = fmtReturn(index.ret_6m);

  const fig = React.useMemo(() => {
    if (!dp || dp.dates.length === 0) return null;
    const start = Math.max(0, dp.dates.length - 130);
    const dates = dp.dates.slice(start);
    const open = dp.open.slice(start);
    const high = dp.high.slice(start);
    const low = dp.low.slice(start);
    const close = dp.close.slice(start);

    const raw = {
      data: [{
        type: 'ohlc' as const, x: dates, open, high, low, close,
        increasing: { line: { color: sem.success, width: 1 } },
        decreasing: { line: { color: sem.destructive, width: 1 } },
        showlegend: false, hoverinfo: 'none' as const,
      }],
      layout: {
        xaxis: { visible: false, rangeslider: { visible: false } },
        yaxis: {
          side: 'right' as const, showgrid: true,
          gridcolor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.03)',
          tickfont: { family: '"Space Mono", monospace', size: 9, color: isDark ? 'rgba(200,200,210,0.35)' : 'rgba(40,40,45,0.35)' },
        },
        margin: { l: 2, r: 40, t: 4, b: 4 },
        showlegend: false,
      },
    };
    return applyChartTheme(raw, theme, { transparentBackground: true });
  }, [dp, theme, isDark, sem]);

  return (
    <div
      onClick={onClick}
      className="rounded-[var(--radius)] border border-border/30 bg-card overflow-hidden hover:border-primary/30 hover:shadow-md transition-all cursor-pointer group flex flex-col shadow-sm"
    >
      {/* Header: Name | Price + Daily Return */}
      <div className="px-2.5 py-1.5 flex items-center justify-between border-b border-border/10">
        <span className="text-[12.5px] font-semibold text-foreground truncate">{index.name}</span>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[12.5px] font-mono font-bold text-foreground tabular-nums">{fmtPrice(index.price)}</span>
          <span className={`text-[11.5px] font-mono font-bold tabular-nums ${isUp ? 'text-success' : 'text-destructive'}`}>
            {dailyRet != null ? `${dailyRet > 0 ? '+' : ''}${(dailyRet * 100).toFixed(2)}%` : '—'}
          </span>
        </div>
      </div>

      {/* OHLC Sparkline */}
      <div className="h-[120px]">
        {fig ? (
          <Plot
            data={fig.data}
            layout={{ ...fig.layout, autosize: true }}
            config={{ responsive: true, displayModeBar: false, scrollZoom: false }}
            useResizeHandler
            style={{ width: '100%', height: '100%' }}
          />
        ) : (
          <div className="h-full flex items-center justify-center">
            <Loader2 className="w-3 h-3 animate-spin text-muted-foreground/20" />
          </div>
        )}
      </div>

      {/* Period Returns Row */}
      <div className="px-2.5 py-1 border-t border-border/10 flex items-center gap-3">
        <div className="flex items-center gap-1">
          <span className="text-[9.5px] font-mono text-muted-foreground/40 uppercase">1M</span>
          <span className={ret1m.cls}>{ret1m.text}</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-[9.5px] font-mono text-muted-foreground/40 uppercase">3M</span>
          <span className={ret3m.cls}>{ret3m.text}</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-[9.5px] font-mono text-muted-foreground/40 uppercase">6M</span>
          <span className={ret6m.cls}>{ret6m.text}</span>
        </div>
        {vamsScore != null && (
          <>
            <div className="flex-1" />
            <div className="flex items-center gap-1">
              <span className="text-[9.5px] font-mono text-muted-foreground/40 uppercase" title="Value and Momentum Score — cross-asset relative strength">VAMS</span>
              <span className={`font-mono text-[11px] tabular-nums font-semibold ${vamsScore >= 0 ? 'text-success' : 'text-destructive'}`}>
                {vamsScore > 0 ? '+' : ''}{vamsScore.toFixed(1)}
              </span>
            </div>
          </>
        )}
      </div>

      {/* Footer: VOMO + Sparkline | Regime */}
      <div className="px-2.5 py-1 border-t border-border/10 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          {vomo != null ? (
            <span className={`text-[11px] font-mono font-bold tabular-nums shrink-0 ${vomo >= 1 ? 'text-success' : vomo > -1 ? 'text-warning' : 'text-destructive'}`}>
              <span title="Volatility Momentum — composite signal measuring value and momentum across timeframes">VOMO</span> {vomo > 0 ? '+' : ''}{vomo.toFixed(1)}
            </span>
          ) : (
            <span className="text-[11px] font-mono text-muted-foreground/30" title="Volatility Momentum — composite signal measuring value and momentum across timeframes">VOMO —</span>
          )}
          {vomoHistory && vomoHistory.length > 2 && (
            <div className="w-[48px] h-[20px] shrink-0">
              <VomoSparkline values={vomoHistory} />
            </div>
          )}
        </div>
        <span className={`text-[10px] font-mono font-semibold uppercase tracking-wide shrink-0 ${regimeColor(index.regime)}`}>
          {index.regime || ''}
          {index.weeks_in_regime ? ` W${index.weeks_in_regime}` : ''}
        </span>
      </div>
    </div>
  );
});

// ── Technicals (lazy) ──

const Technicals = dynamic(() => import('./Technicals'), {
  ssr: false,
  loading: () => (
    <div className="h-full flex items-center justify-center">
      <Loader2 className="w-4 h-4 animate-spin text-muted-foreground/30" />
    </div>
  ),
});

// ── Main Grid ──

export default function ChartGrid({ onOpenBriefing }: { onOpenBriefing?: () => void }) {
  const { theme } = useTheme();
  const [selectedIndex, setSelectedIndex] = useState<string | null>(null);

  // Fetch summary
  const { data: summary, isLoading: summaryLoading, isError: summaryError } = useQuery({
    queryKey: ['technicals-summary'],
    queryFn: () => apiFetchJson<VamsSummary>('/api/macro/technicals/summary'),
    staleTime: 60_000, gcTime: 120_000,
  });

  const indices = summary?.indices ?? [];
  const indexNames = indices.map(i => i.name);
  const crossAssetVams = summary?.cross_asset_vams ?? {};

  // Fetch all details in parallel
  const { data: allDetails, isLoading: detailsLoading } = useQuery({
    queryKey: ['technicals-all-details', indexNames.join(',')],
    queryFn: async () => {
      const results = await Promise.allSettled(
        indexNames.map(name =>
          apiFetchJson<ApiIndex>(`/api/macro/technicals/detail?index=${encodeURIComponent(name)}`)
        )
      );
      return results.map((r, i) =>
        r.status === 'fulfilled' ? r.value : indices[i]
      );
    },
    enabled: indexNames.length > 0,
    staleTime: 120_000, gcTime: 300_000,
  });

  const displayIndices = allDetails || indices;

  // Escape to go back
  useEffect(() => {
    if (!selectedIndex) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') setSelectedIndex(null); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [selectedIndex]);

  // Expanded view
  if (selectedIndex) {
    return (
      <div className="h-full flex flex-col">
        <div className="shrink-0 px-3 lg:px-4 py-2 border-b border-border/20 flex items-center gap-3">
          <button onClick={() => setSelectedIndex(null)} className="flex items-center gap-1 text-[12.5px] font-medium text-muted-foreground hover:text-foreground transition-colors">
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Overview</span>
          </button>
        </div>
        <div className="flex-1 min-h-0">
          <Technicals key={selectedIndex} defaultIndex={selectedIndex} onOpenBriefing={onOpenBriefing} />
        </div>
      </div>
    );
  }

  if (summaryLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <LoadingSpinner label="Loading market data" size="section" />
      </div>
    );
  }

  if (summaryError) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-center max-w-xs animate-fade-in">
          <div className="w-10 h-10 rounded-[var(--radius)] bg-destructive/10 border border-destructive/20 flex items-center justify-center">
            <AlertTriangle className="w-4.5 h-4.5 text-destructive" />
          </div>
          <p className="text-[13px] font-medium text-foreground">Failed to load market data</p>
          <p className="text-[12px] text-muted-foreground">Check your connection and try refreshing the page.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Market Status Bar */}
      <MarketStatusBar
        summary={summary}
        displayIndices={displayIndices}
        detailsLoading={detailsLoading}
        indexCount={displayIndices.length}
        onOpenBriefing={onOpenBriefing}
      />

      {/* Grid */}
      <div className="flex-1 overflow-y-auto no-scrollbar p-2 sm:p-3">
        {displayIndices.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="flex flex-col items-center gap-3 text-center max-w-xs animate-fade-in">
              <div className="w-10 h-10 rounded-[var(--radius)] bg-muted flex items-center justify-center">
                <BarChart3 className="w-4.5 h-4.5 text-muted-foreground" />
              </div>
              <p className="text-[13px] font-medium text-foreground">No indices available</p>
              <p className="text-[12px] text-muted-foreground">Market data hasn&apos;t been computed yet. Run the macro engine to generate index signals.</p>
            </div>
          </div>
        ) : (
          <div className="grid gap-2 sm:gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
            {displayIndices.map((idx: any, i: number) => (
              <div key={idx.name} className={`animate-fade-in stagger-${Math.min(i + 1, 10)}`}>
                <MiniChart
                  index={idx}
                  theme={theme}
                  vamsScore={crossAssetVams[idx.name]}
                  onClick={() => setSelectedIndex(idx.name)}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
