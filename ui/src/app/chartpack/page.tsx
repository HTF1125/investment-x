'use client';

import React, { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import { useRouter, useSearchParams } from 'next/navigation';
import AppShell from '@/components/layout/AppShell';
import { ChartErrorBoundary } from '@/components/shared/ChartErrorBoundary';
import { apiFetchJson } from '@/lib/api';
import { getApiCode, buildChartFigure } from '@/lib/buildChartFigure';
import { applyChartTheme, COLORWAY } from '@/lib/chartTheme';
import { RANGE_MAP, getPresetStartDate } from '@/lib/constants';
import { useTheme } from '@/context/ThemeContext';
import { useQuery, useQueries, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import {
  Loader2, Plus, Trash2, RefreshCw, ChevronLeft, ChevronRight,
  LineChart, Edit3, Check, X, ArrowUp, ArrowDown, LayoutGrid,
  Globe, Lock, Users, Clock, FolderOutput, MoreVertical, AlertTriangle, Search,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import ChartEditOverlay from '@/components/chartpack/ChartEditOverlay';

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center">
      <Loader2 className="w-4 h-4 animate-spin text-primary/30" />
    </div>
  ),
}) as any;

// ── Types ──

interface PackSummary {
  id: string;
  name: string;
  description: string | null;
  chart_count: number;
  is_published: boolean;
  creator_name?: string | null;
  created_at: string;
  updated_at: string;
}

interface SelectedSeries {
  code: string;
  name: string;
  chartType: string;
  yAxis: string;
  yAxisIndex?: number;
  visible: boolean;
  color?: string;
  transform?: string;
  transformParam?: number;
  lineStyle?: string;
  lineWidth?: number;
  paneId?: number;
}

interface ChartConfig {
  title?: string;
  description?: string;
  code?: string;
  /** Pre-rendered Plotly figure (inline). */
  figure?: any;
  /** ISO timestamp of when the figure was cached. */
  figureCachedAt?: string;
  /** Reference to a Charts table record — figure loaded lazily. */
  chart_id?: string;
  series: SelectedSeries[];
  panes?: { id: number; label: string }[];
  annotations?: any[];
  logAxes?: (number | string)[];
  activeRange?: string;
  startDate?: string;
  endDate?: string;
}

interface PackDetail {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  charts: ChartConfig[];
  is_published: boolean;
  creator_name?: string | null;
  created_at: string;
  updated_at: string;
}

// ── Helpers ──

function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return shortDate(iso);
}

// ── ConfirmDialog ──

function ConfirmDialog({ title, message, confirmLabel, onConfirm, onCancel }: {
  title: string; message: React.ReactNode; confirmLabel?: string;
  onConfirm: () => void; onCancel: () => void;
}) {
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-foreground/20 dark:bg-black/60" onClick={onCancel}>
      <div className="bg-card border border-destructive/30 rounded-[var(--radius)] w-full max-w-sm shadow-lg p-5 mx-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-md bg-destructive/15 flex items-center justify-center border border-destructive/30 shrink-0">
            <AlertTriangle className="w-4 h-4 text-destructive" />
          </div>
          <div>
            <h3 className="text-[13px] font-semibold text-foreground">{title}</h3>
            <p className="text-[10px] text-muted-foreground/50 mt-0.5">This action cannot be undone</p>
          </div>
        </div>
        <p className="text-[12px] text-muted-foreground leading-relaxed mb-5">{message}</p>
        <div className="flex items-center justify-end gap-2">
          <button onClick={onCancel} className="px-4 py-1.5 text-[11px] font-semibold text-muted-foreground hover:text-foreground bg-background hover:bg-accent/40 rounded-[var(--radius)] transition-all border border-border/50">
            Cancel
          </button>
          <button onClick={onConfirm} className="flex items-center gap-1.5 px-4 py-1.5 text-[11px] font-semibold bg-destructive hover:bg-destructive/90 text-destructive-foreground rounded-[var(--radius)] transition-all">
            <Trash2 className="w-3 h-3" />
            {confirmLabel || 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── ChartMenu: three-dot dropdown ──

function ChartMenu({ onEdit, onMoveUp, onMoveDown, onCopyMove, onRemove, onRefresh, hasCachedFigure, isFirst, isLast }: {
  onEdit: () => void; onMoveUp: () => void; onMoveDown: () => void;
  onCopyMove: () => void; onRemove: () => void; onRefresh: () => void;
  hasCachedFigure: boolean; isFirst: boolean; isLast: boolean;
}) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const item = (onClick: () => void, icon: React.ReactNode, label: string, destructive?: boolean) => (
    <button
      onClick={() => { onClick(); setOpen(false); }}
      className={`w-full flex items-center gap-2 px-2.5 py-1.5 text-[11px] rounded-[calc(var(--radius)-2px)] transition-colors ${
        destructive
          ? 'text-destructive hover:bg-destructive/10'
          : 'text-foreground/70 hover:text-foreground hover:bg-foreground/[0.05]'
      }`}
    >
      {icon}{label}
    </button>
  );

  return (
    <div ref={menuRef} className="relative pointer-events-auto">
      <button
        onClick={(e) => { e.stopPropagation(); setOpen((o) => !o); }}
        className="w-7 h-7 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/30 hover:text-foreground hover:bg-foreground/[0.06] transition-colors"
        aria-label="Chart actions"
      >
        <MoreVertical className="w-3.5 h-3.5" />
      </button>
      {open && (
        <div className="absolute right-0 top-8 z-20 w-[160px] py-1 bg-card border border-border/50 rounded-[var(--radius)] shadow-lg animate-fade-in">
          {item(onEdit, <Edit3 className="w-3 h-3" />, 'Edit chart')}
          {hasCachedFigure && item(onRefresh, <RefreshCw className="w-3 h-3" />, 'Refresh data')}
          {item(onCopyMove, <FolderOutput className="w-3 h-3" />, 'Copy / Move')}
          {!isFirst && item(onMoveUp, <ArrowUp className="w-3 h-3" />, 'Move up')}
          {!isLast && item(onMoveDown, <ArrowDown className="w-3 h-3" />, 'Move down')}
          <div className="my-1 border-t border-border/20" />
          {item(onRemove, <Trash2 className="w-3 h-3" />, 'Remove', true)}
        </div>
      )}
    </div>
  );
}

// ── PackChart: memoized chart tile that receives data as props ──

const PackChart = React.memo(function PackChart({
  config, index, isLight, rawData, isLoading,
  onRemove, onEdit, onMoveUp, onMoveDown, onCopyMove, onRefresh,
  isFirst, isLast, readOnly, pageIndex,
}: {
  config: ChartConfig; index: number; isLight: boolean;
  rawData: Record<string, (string | number | null)[]> | undefined;
  isLoading: boolean;
  onRemove: () => void; onEdit: () => void;
  onMoveUp: () => void; onMoveDown: () => void;
  onCopyMove: () => void; onRefresh: () => void;
  isFirst: boolean; isLast: boolean; readOnly?: boolean;
  pageIndex?: number;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const plotRef = useRef<HTMLElement | null>(null);

  // Lazy-load figure from Charts table when chart_id is present
  const { data: lazyFigure, isLoading: figLoading } = useQuery({
    queryKey: ['chart-figure', config.chart_id],
    queryFn: () => apiFetchJson<{ figure?: any }>(`/api/v1/dashboard/charts/${config.chart_id}/figure`),
    enabled: !!config.chart_id && !config.figure,
    staleTime: 5 * 60_000,
    gcTime: 10 * 60_000,
  });

  const seriesList = useMemo(() => {
    const hasCode = !!config.code?.trim();
    if (hasCode && rawData) {
      const columns = Object.keys(rawData).filter((k) => k !== 'Date');
      const byCode = new Map(config.series.map((s) => [s.code, s]));
      return columns.map((col) => byCode.get(col) || {
        code: col, name: col, chartType: 'line', yAxis: 'left', yAxisIndex: 0, visible: true, transform: 'none',
      });
    }
    return config.series;
  }, [config.code, rawData, config.series]);

  const startDate = useMemo(() => {
    if (config.startDate) return config.startDate;
    const months = RANGE_MAP[config.activeRange || 'MAX'];
    return months != null ? getPresetStartDate(months) : '';
  }, [config.startDate, config.activeRange]);
  const endDate = config.endDate || '';

  const logAxesSet = useMemo(() => new Set((config.logAxes || []).map((v: any) => {
    const s = String(v);
    return s.includes('-') ? s : `0-${s}`;
  })), [config.logAxes]);

  const figure = useMemo(() => {
    // Pre-rendered figure: inline or lazy-loaded by chart_id
    const sourceFig = config.figure || lazyFigure?.figure;
    if (sourceFig) {
      const themed = applyChartTheme(sourceFig, isLight ? 'light' : 'dark') as any;
      if (!themed) return null;
      // Clear in-chart title — we display it in the card header
      if (themed.layout) {
        themed.layout.title = { text: '' };
        themed.layout.margin = { ...themed.layout.margin, t: 8 };
      }
      return themed;
    }
    if (!rawData) return null;
    // Build without title — shown externally
    return buildChartFigure({
      rawData, series: seriesList, panes: config.panes,
      annotations: config.annotations as any, logAxes: logAxesSet,
      yAxisBases: (config as any).yAxisBases || {},
      yAxisRanges: (config as any).yAxisRanges || {},
      invertedAxes: new Set((config as any).invertedAxes || []),
      isLight, title: undefined, startDate, endDate, compact: true,
      showLegend: (config as any).showLegend,
      legendPosition: (config as any).legendPosition,
      showGridlines: (config as any).showGridlines,
      gridlineStyle: (config as any).gridlineStyle,
      axisTitles: (config as any).axisTitles,
      titleFontSize: (config as any).titleFontSize,
      showZeroline: (config as any).showZeroline,
      bargap: (config as any).bargap,
    });
  }, [config.figure, lazyFigure, rawData, seriesList, config.panes, config.annotations, logAxesSet, isLight, config.title, startDate, endDate]);

  // Debounced resize — cache Plotly ref to avoid repeated dynamic imports
  const plotlyRef = useRef<any>(null);
  useEffect(() => {
    const el = containerRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    let timer: ReturnType<typeof setTimeout>;
    const observer = new ResizeObserver(() => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        const gd = plotRef.current;
        if (!gd?.isConnected || !gd.clientHeight || !gd.clientWidth) return;
        if (plotlyRef.current) {
          plotlyRef.current.Plots.resize(gd);
        } else {
          import('plotly.js-dist-min').then(({ default: Plotly }) => {
            plotlyRef.current = Plotly;
            if (gd?.isConnected && gd.clientHeight > 0 && gd.clientWidth > 0) (Plotly as any).Plots.resize(gd);
          }).catch(() => {});
        }
      }, 150);
    });
    observer.observe(el);
    return () => { clearTimeout(timer); observer.disconnect(); };
  }, []);

  const handlePlotInit = useCallback((_: any, gd: HTMLElement) => { plotRef.current = gd; }, []);

  const seriesCount = config.series?.length || 0;
  const stagger = typeof pageIndex === 'number' ? Math.min(pageIndex + 1, 9) : 1;
  const [confirmRemove, setConfirmRemove] = useState(false);

  const MAX_TAGS = 4;
  const seriesTags = (config.series || []).map((s, idx) => ({
    name: s.name || s.code,
    color: s.color || COLORWAY[idx % COLORWAY.length],
  }));
  const visibleTags = seriesTags.slice(0, MAX_TAGS);
  const extraCount = seriesTags.length - MAX_TAGS;

  return (
    <>
      <div
        className={`panel-card animate-fade-in stagger-${stagger} hover:border-primary/25 relative group/chart overflow-hidden flex flex-col transition-colors`}
      >
        {/* Edit button — bottom-right corner on hover */}
        {!readOnly && (
          <button
            onClick={(e) => { e.stopPropagation(); onEdit(); }}
            className="absolute bottom-2 right-2 z-10 opacity-0 group-hover/chart:opacity-100 transition-opacity duration-150 cursor-pointer"
            aria-label="Edit chart"
          >
            <div className="w-6 h-6 flex items-center justify-center rounded-[var(--radius)] bg-card/90 border border-border/30 hover:bg-foreground/[0.06] hover:border-border/50 transition-colors">
              <Edit3 className="w-3 h-3 text-muted-foreground/50" />
            </div>
          </button>
        )}

        {/* ── Card header ── */}
        <div className="shrink-0 px-2.5 pt-2 pb-1.5 border-b border-border/20">
            <div className="flex items-center gap-1.5">
              <button
                onClick={(e) => { e.stopPropagation(); onEdit(); }}
                className="text-[11px] font-semibold text-foreground/80 truncate flex-1 min-w-0 text-left hover:text-primary transition-colors"
                title="Click to edit"
              >
                {config.title || `Chart ${index + 1}`}
              </button>

              {seriesCount > 0 && (
                <span className="shrink-0 px-1.5 py-px rounded-full bg-foreground/[0.04] text-[9px] font-mono text-muted-foreground/50 tabular-nums">
                  {seriesCount}
                </span>
              )}

              {/* Cached figure indicator */}
              {config.figureCachedAt && (
                <span
                  className="shrink-0 flex items-center gap-0.5 text-[8px] font-mono text-muted-foreground/25"
                  title={`Cached ${new Date(config.figureCachedAt).toLocaleString()}`}
                >
                  <Clock className="w-2.5 h-2.5" />
                </span>
              )}

              {/* Three-dot menu — visible on hover */}
              {!readOnly && (
                <div className="shrink-0 opacity-0 group-hover/chart:opacity-100 transition-opacity duration-150">
                  <ChartMenu
                    onEdit={onEdit} onMoveUp={onMoveUp} onMoveDown={onMoveDown}
                    onCopyMove={onCopyMove} onRemove={() => setConfirmRemove(true)}
                    onRefresh={onRefresh} hasCachedFigure={!!config.figure}
                    isFirst={isFirst} isLast={isLast}
                  />
                </div>
              )}
            </div>

            {config.description && (
              <p className="text-[9px] leading-snug text-muted-foreground/40 mt-0.5 line-clamp-2">{config.description}</p>
            )}

            {visibleTags.length > 0 && (
              <div className="flex items-center gap-1 mt-1 overflow-hidden">
                {visibleTags.map(({ name, color }) => (
                  <span key={name} className="shrink-0 max-w-[100px] truncate inline-flex items-center gap-1 px-1.5 py-px rounded bg-foreground/[0.04] text-[9px] font-mono text-muted-foreground/60">
                    <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
                    {name}
                  </span>
                ))}
                {extraCount > 0 && (
                  <span className="shrink-0 text-[9px] font-mono text-muted-foreground/30">
                    +{extraCount}
                  </span>
                )}
              </div>
            )}
          </div>

        {/* ── Chart area ── */}
        <div ref={containerRef} className="flex-1 min-h-0">
          {isLoading || figLoading ? (
            <div className="h-full w-full animate-pulse bg-foreground/[0.03] rounded-b-[var(--radius)]" />
          ) : figure ? (
            <ChartErrorBoundary>
              <Plot data={figure.data} layout={{ ...figure.layout, dragmode: false }}
                config={{ responsive: true, displayModeBar: false, displaylogo: false, scrollZoom: false }}
                style={{ width: '100%', height: '100%' }}
                onInitialized={handlePlotInit} />
            </ChartErrorBoundary>
          ) : (
            <div className="h-full flex flex-col items-center justify-center gap-1.5">
              <LineChart className="w-4 h-4 text-muted-foreground/15" />
              <span className="text-[11px] text-muted-foreground/30">No data</span>
            </div>
          )}
        </div>
      </div>

      {confirmRemove && (
        <ConfirmDialog
          title="Remove chart"
          message={<>Remove <span className="font-semibold text-foreground">{config.title || `Chart ${index + 1}`}</span> from this pack?</>}
          confirmLabel="Remove"
          onConfirm={() => { setConfirmRemove(false); onRemove(); }}
          onCancel={() => setConfirmRemove(false)}
        />
      )}
    </>
  );
});

// ── PackChartGrid: handles batch data fetching for all charts ──

function PackChartGrid({
  pack, isLight, refreshKey, readOnly,
  onRemoveChart, onEditChart, onMoveChart, onCopyMoveChart, onRefreshChart, onAddChart,
}: {
  pack: PackDetail; isLight: boolean; refreshKey: number; readOnly?: boolean;
  onRemoveChart: (i: number) => void;
  onEditChart: (i: number) => void;
  onMoveChart: (from: number, to: number) => void;
  onCopyMoveChart: (i: number) => void;
  onRefreshChart: (i: number) => void;
  onAddChart?: () => void;
}) {
  const router = useRouter();

  // ── Pagination & search state (hoisted above data fetching to scope queries) ──
  const PAGE_SIZE = 9;
  const pageKey = `ix-pack-page-${pack.id}`;
  const totalPages = Math.max(1, Math.ceil(pack.charts.length / PAGE_SIZE));
  const [page, setPage] = useState(() => {
    const stored = sessionStorage.getItem(pageKey);
    const p = stored ? parseInt(stored, 10) : 0;
    return Math.min(p, Math.max(0, Math.ceil(pack.charts.length / PAGE_SIZE) - 1));
  });

  // Persist page changes
  useEffect(() => { sessionStorage.setItem(pageKey, String(page)); }, [pageKey, page]);

  // Restore page when pack changes; clamp if charts were removed
  useEffect(() => {
    const stored = sessionStorage.getItem(pageKey);
    const p = stored ? parseInt(stored, 10) : 0;
    setPage(Math.min(p, totalPages - 1));
  }, [pack.id, pageKey, totalPages]);

  const [searchQuery, setSearchQuery] = useState('');

  // Filter charts by search query, keeping original indices
  const filteredCharts = useMemo(() => {
    if (!searchQuery.trim()) return pack.charts.map((c, i) => ({ chart: c, origIdx: i }));
    const q = searchQuery.toLowerCase();
    return pack.charts
      .map((c, i) => ({ chart: c, origIdx: i }))
      .filter(({ chart }) =>
        (chart.title || '').toLowerCase().includes(q) ||
        (chart.description || '').toLowerCase().includes(q) ||
        chart.series?.some((s) => (s.name || s.code).toLowerCase().includes(q))
      );
  }, [pack.charts, searchQuery]);

  // Compute which original chart indices are visible (current page + next page for prefetch)
  const visibleOrigIndices = useMemo(() => {
    const filteredTotal = filteredCharts.length;
    const filteredTotalPages = Math.max(1, Math.ceil(filteredTotal / PAGE_SIZE));
    const safePage = Math.min(page, filteredTotalPages - 1);
    const startIdx = safePage * PAGE_SIZE;
    // Current page + next page (prefetch)
    const endIdx = Math.min(startIdx + PAGE_SIZE * 2, filteredTotal);
    const indices = new Set<number>();
    for (let i = startIdx; i < endIdx; i++) {
      indices.add(filteredCharts[i].origIdx);
    }
    return indices;
  }, [filteredCharts, page]);

  // Separate charts into figure-based, code-based, and series-based — scoped to visible pages
  const { codeChartIndices, allCodes } = useMemo(() => {
    const codeIdx: number[] = [];
    const codes = new Set<string>();
    pack.charts.forEach((chart, i) => {
      if (!visibleOrigIndices.has(i)) return;
      // Pre-rendered or lazy-loaded figures need no data fetching
      if (chart.figure || chart.chart_id) return;
      if (chart.code?.trim()) {
        codeIdx.push(i);
      } else {
        chart.series?.forEach((s) => codes.add(getApiCode(s)));
      }
    });
    return { codeChartIndices: codeIdx, allCodes: Array.from(codes) };
  }, [pack.charts, visibleOrigIndices]);

  // ONE batch fetch for visible series-based charts
  const { data: batchData, isLoading: batchLoading } = useQuery({
    queryKey: ['pack-batch-data', pack.id, allCodes, refreshKey],
    queryFn: () => apiFetchJson<Record<string, (string | number | null)[]>>('/api/timeseries.custom', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ codes: allCodes }),
    }),
    enabled: allCodes.length > 0,
    staleTime: 120_000,
    placeholderData: keepPreviousData,
  });

  // Individual code executions for visible code-based charts only
  const codeQueries = useQueries({
    queries: codeChartIndices.map((i) => ({
      queryKey: ['pack-chart-code', i, pack.charts[i].code, refreshKey],
      queryFn: () => apiFetchJson<Record<string, any>>('/api/timeseries.exec', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: pack.charts[i].code }),
      }),
      staleTime: 120_000,
    })),
  });

  // Build a map: codeChartIndex → its query result
  const codeDataMap = useMemo(() => {
    const map = new Map<number, Record<string, any[]> | undefined>();
    codeChartIndices.forEach((chartIdx, queryIdx) => {
      const result = codeQueries[queryIdx]?.data;
      if (!result) { map.set(chartIdx, undefined); return; }
      const columns: string[] = result.__columns__ || Object.keys(result).filter((k) => k !== 'Date' && k !== '__columns__');
      const data: Record<string, any[]> = { Date: result.Date };
      for (const col of columns) data[col] = result[col];
      map.set(chartIdx, data);
    });
    return map;
  }, [codeChartIndices, codeQueries]);

  // For each chart, compute its rawData slice from the batch or code results
  const chartDataList = useMemo(() => {
    return pack.charts.map((chart, i) => {
      // Pre-rendered figure — no data needed
      if (chart.figure || chart.chart_id) return { rawData: undefined, isLoading: false };
      // Not on visible pages — don't provide data (will load when paged to)
      if (!visibleOrigIndices.has(i)) return { rawData: undefined, isLoading: false };
      if (chart.code?.trim()) {
        const rd = codeDataMap.get(i);
        return { rawData: rd, isLoading: !codeDataMap.has(i) || (rd === undefined && codeQueries[codeChartIndices.indexOf(i)]?.isLoading) };
      }
      // Extract this chart's columns from the batch
      if (!batchData) return { rawData: undefined, isLoading: batchLoading };
      const slice: Record<string, (string | number | null)[]> = { Date: batchData.Date };
      chart.series.forEach((s) => {
        const key = getApiCode(s);
        if (batchData[key]) slice[key] = batchData[key];
      });
      return { rawData: slice, isLoading: false };
    });
  }, [pack.charts, batchData, batchLoading, codeDataMap, codeQueries, codeChartIndices, visibleOrigIndices]);

  if (pack.charts.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center max-w-[220px]">
          <div className="w-10 h-10 mx-auto panel-card flex items-center justify-center mb-4">
            <LineChart className="w-4 h-4 text-muted-foreground/25" />
          </div>
          <p className="text-[12px] font-semibold text-foreground/50">Empty pack</p>
          <p className="text-[10px] text-muted-foreground/35 mt-1.5 leading-relaxed">
            {readOnly ? 'This pack has no charts yet.' : 'Add charts from the builder to start monitoring.'}
          </p>
          {!readOnly && onAddChart && (
            <button
              onClick={onAddChart}
              className="btn-primary mt-4"
            >
              <Plus className="w-3.5 h-3.5" /> Add chart
            </button>
          )}
        </div>
      </div>
    );
  }

  const filteredTotal = filteredCharts.length;
  const filteredTotalPages = Math.max(1, Math.ceil(filteredTotal / PAGE_SIZE));
  const safePage = Math.min(page, filteredTotalPages - 1);
  const startIdx = safePage * PAGE_SIZE;
  const chartsToRender = filteredCharts.slice(startIdx, startIdx + PAGE_SIZE);
  const showFrom = filteredTotal > 0 ? startIdx + 1 : 0;
  const showTo = Math.min(startIdx + PAGE_SIZE, filteredTotal);

  return (
    <>
      {/* Search bar — only show when pack has enough charts */}
      {pack.charts.length > PAGE_SIZE && (
        <div className="mb-3 relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground/30 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setPage(0); }}
            placeholder="Filter by title or series..."
            className="w-full h-7 pl-7 pr-2.5 text-[11px] border border-border/30 rounded-[var(--radius)] bg-transparent text-foreground placeholder:text-muted-foreground/25 focus:outline-none focus:ring-1 focus:ring-primary/25"
          />
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-3" style={{ gridAutoRows: '310px' }}>
        {chartsToRender.map(({ chart, origIdx }, localIdx) => {
          const i = origIdx;
          return (
            <PackChart
              key={`${pack.id}-${i}`}
              config={chart} index={i} isLight={isLight}
              rawData={chartDataList[i]?.rawData as any}
              isLoading={chartDataList[i]?.isLoading ?? false}
              onRemove={() => onRemoveChart(i)}
              onEdit={() => onEditChart(i)}
              onMoveUp={() => onMoveChart(i, i - 1)}
              onMoveDown={() => onMoveChart(i, i + 1)}
              onCopyMove={() => onCopyMoveChart(i)}
              onRefresh={() => onRefreshChart(i)}
              isFirst={i === 0} isLast={i === pack.charts.length - 1}
              readOnly={readOnly}
              pageIndex={localIdx}
            />
          );
        })}
      </div>
      {filteredTotalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-4 pb-2">
          <span className="text-[10px] font-mono text-muted-foreground/40 tabular-nums mr-2">
            {showFrom}–{showTo} of {filteredTotal}{searchQuery && ` (${pack.charts.length} total)`}
          </span>
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="w-7 h-7 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/40 hover:text-foreground hover:bg-primary/[0.06] transition-colors disabled:opacity-40 disabled:pointer-events-none"
            aria-label="Previous page"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          {Array.from({ length: filteredTotalPages }, (_, p) => (
            <button
              key={p}
              onClick={() => setPage(p)}
              className={`w-7 h-7 flex items-center justify-center rounded-[var(--radius)] text-[10px] font-mono transition-colors ${
                p === page
                  ? 'bg-primary text-primary-foreground font-bold'
                  : 'text-muted-foreground/40 hover:text-foreground hover:bg-primary/[0.06]'
              }`}
              aria-label={`Page ${p + 1}`}
              aria-current={p === page ? 'page' : undefined}
            >
              {p + 1}
            </button>
          ))}
          <button
            onClick={() => setPage((p) => Math.min(filteredTotalPages - 1, p + 1))}
            disabled={page === filteredTotalPages - 1}
            className="w-7 h-7 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/40 hover:text-foreground hover:bg-primary/[0.06] transition-colors disabled:opacity-40 disabled:pointer-events-none"
            aria-label="Next page"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

    </>
  );
}

// ── Main Page ──

function ChartPacksPageInner() {
  const { theme } = useTheme();
  const isLight = theme === 'light';
  const queryClient = useQueryClient();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();

  const activePackId = searchParams.get('chartpack') || null;
  const setActivePackId = useCallback((id: string | null) => {
    if (id) {
      router.push(`/chartpack?chartpack=${id}`);
    } else {
      router.push('/chartpack');
    }
  }, [router]);

  const [refreshKey, setRefreshKey] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newPackName, setNewPackName] = useState('');
  const [newPackDesc, setNewPackDesc] = useState('');
  const [editingName, setEditingName] = useState(false);
  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [listTab, setListTab] = useState<'mine' | 'published'>(() =>
    user ? 'mine' : 'published'
  );
  const [copyMoveChartIndex, setCopyMoveChartIndex] = useState<number | null>(null);
  const [copyMoveTarget, setCopyMoveTarget] = useState<string | null>(null);
  const [copyMoveLoading, setCopyMoveLoading] = useState(false);
  const [deletePackTarget, setDeletePackTarget] = useState<{ id: string; name: string } | null>(null);
  const [editingChartIndex, setEditingChartIndex] = useState<number | null>(null);

  const { data: packs, refetch: refetchPacks } = useQuery({
    queryKey: ['chart-packs'],
    queryFn: () => apiFetchJson<PackSummary[]>('/api/chart-packs'),
    staleTime: 30_000,
    enabled: !!user,
  });

  const { data: publishedPacks, refetch: refetchPublished } = useQuery({
    queryKey: ['chart-packs-published'],
    queryFn: () => apiFetchJson<PackSummary[]>('/api/chart-packs/published'),
    staleTime: 30_000,
  });

  const { data: activePack, refetch: refetchPack } = useQuery({
    queryKey: ['chart-pack', activePackId],
    queryFn: () => apiFetchJson<PackDetail>(`/api/chart-packs/${activePackId}`),
    enabled: !!activePackId,
    staleTime: 30_000,
  });

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    // Strip cached figures from all charts so they re-fetch live data
    if (activePack) {
      const charts = activePack.charts.map(({ figure, figureCachedAt, ...rest }: any) => rest);
      try {
        await apiFetchJson(`/api/chart-packs/${activePack.id}`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ charts }),
        });
        refetchPack();
      } catch {}
    }
    queryClient.invalidateQueries({ queryKey: ['pack-batch-data'] });
    queryClient.invalidateQueries({ queryKey: ['pack-chart-code'] });
    setRefreshKey((k) => k + 1);
    setTimeout(() => setRefreshing(false), 800);
  }, [activePack, queryClient, refetchPack]);

  const handleRefreshChart = useCallback(async (chartIndex: number) => {
    if (!activePack) return;
    const charts = activePack.charts.map((c: any, i: number) => {
      if (i !== chartIndex) return c;
      const { figure, figureCachedAt, ...rest } = c;
      return rest;
    });
    try {
      await apiFetchJson(`/api/chart-packs/${activePack.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ charts }),
      });
      refetchPack();
    } catch {}
    queryClient.invalidateQueries({ queryKey: ['pack-batch-data'] });
    queryClient.invalidateQueries({ queryKey: ['pack-chart-code'] });
    setRefreshKey((k) => k + 1);
  }, [activePack, queryClient, refetchPack]);

  const handleCreatePack = useCallback(async () => {
    if (!newPackName.trim()) return;
    try {
      const pack = await apiFetchJson<PackDetail>('/api/chart-packs', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newPackName.trim(), description: newPackDesc.trim() || null, charts: [] }),
      });
      setActivePackId(pack.id);
      setCreateModalOpen(false);
      setNewPackName('');
      setNewPackDesc('');
      refetchPacks();
    } catch {}
  }, [newPackName, newPackDesc, refetchPacks]);

  const handleDeletePackClick = useCallback((id: string, name: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDeletePackTarget({ id, name });
  }, []);

  const handleDeletePackConfirm = useCallback(async () => {
    if (!deletePackTarget) return;
    try {
      await apiFetchJson(`/api/chart-packs/${deletePackTarget.id}`, { method: 'DELETE' });
      if (activePackId === deletePackTarget.id) setActivePackId(null);
      refetchPacks();
    } catch {}
    setDeletePackTarget(null);
  }, [deletePackTarget, activePackId, refetchPacks]);

  const handleRemoveChart = useCallback(async (chartIndex: number) => {
    if (!activePack) return;
    // Soft-delete: mark chart as deleted instead of removing from array
    const charts = activePack.charts.map((c, i) =>
      i === chartIndex ? { ...c, deleted: true } : c,
    );
    try {
      await apiFetchJson(`/api/chart-packs/${activePack.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ charts }),
      });
      refetchPack();
      refetchPacks();
    } catch {}
  }, [activePack, refetchPack, refetchPacks]);

  const handleEditChart = useCallback((chartIndex: number) => {
    setEditingChartIndex(chartIndex);
  }, []);

  // Open overlay with blank config for adding a new chart
  const handleAddChart = useCallback(() => {
    if (!activePack) return;
    // Use index -1 as sentinel for "new chart"
    setEditingChartIndex(-1);
  }, [activePack]);

  const handleSaveEditedChart = useCallback(async (updatedConfig: ChartConfig) => {
    if (!activePack || editingChartIndex == null) return;
    let charts: ChartConfig[];
    if (editingChartIndex === -1) {
      // Adding a new chart — append to pack
      charts = [...activePack.charts, updatedConfig];
    } else {
      // Editing existing chart — replace in place
      charts = activePack.charts.map((c, i) =>
        i === editingChartIndex ? updatedConfig : c,
      );
    }
    try {
      await apiFetchJson(`/api/chart-packs/${activePack.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ charts }),
      });
      refetchPack();
    } catch {}
    setEditingChartIndex(null);
  }, [activePack, editingChartIndex, refetchPack]);

  const handleMoveChart = useCallback(async (from: number, to: number) => {
    if (!activePack) return;
    const charts = [...activePack.charts];
    const [moved] = charts.splice(from, 1);
    charts.splice(to, 0, moved);
    try {
      await apiFetchJson(`/api/chart-packs/${activePack.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ charts }),
      });
      refetchPack();
    } catch {}
  }, [activePack, refetchPack]);

  const handleUpdateDescription = useCallback(async (chartIndex: number, description: string) => {
    if (!activePack) return;
    const charts = activePack.charts.map((c, i) =>
      i === chartIndex ? { ...c, description: description || undefined } : c,
    );
    try {
      await apiFetchJson(`/api/chart-packs/${activePack.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ charts }),
      });
      refetchPack();
    } catch {}
  }, [activePack, refetchPack]);

  const handleSaveName = useCallback(async () => {
    if (!activePack || !editName.trim()) return;
    try {
      await apiFetchJson(`/api/chart-packs/${activePack.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: editName.trim(), description: editDesc.trim() || null }),
      });
      setEditingName(false);
      refetchPack();
      refetchPacks();
    } catch {}
  }, [activePack, editName, editDesc, refetchPack, refetchPacks]);

  const handleTogglePublish = useCallback(async () => {
    if (!activePack) return;
    const prev = activePack.is_published;
    const next = !prev;
    // Optimistic update
    queryClient.setQueryData(['chart-pack', activePack.id], (old: PackDetail | undefined) =>
      old ? { ...old, is_published: next } : old,
    );
    try {
      await apiFetchJson(`/api/chart-packs/${activePack.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_published: next }),
      });
      refetchPack();
      refetchPacks();
      refetchPublished();
    } catch (err) {
      console.error('Failed to toggle publish:', err);
      // Rollback
      queryClient.setQueryData(['chart-pack', activePack.id], (old: PackDetail | undefined) =>
        old ? { ...old, is_published: prev } : old,
      );
    }
  }, [activePack, queryClient, refetchPack, refetchPacks, refetchPublished]);

  const handleCopyToPack = useCallback(async () => {
    if (copyMoveChartIndex == null || !copyMoveTarget || !activePack) return;
    setCopyMoveLoading(true);
    try {
      const chart = activePack.charts[copyMoveChartIndex];
      await apiFetchJson(`/api/chart-packs/${copyMoveTarget}/charts`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chart }),
      });
      setCopyMoveChartIndex(null);
      setCopyMoveTarget(null);
      refetchPacks();
    } catch (err) { console.error(err); } finally { setCopyMoveLoading(false); }
  }, [copyMoveChartIndex, copyMoveTarget, activePack, refetchPacks]);

  const handleMoveToPackAction = useCallback(async () => {
    if (copyMoveChartIndex == null || !copyMoveTarget || !activePack) return;
    setCopyMoveLoading(true);
    try {
      const chart = activePack.charts[copyMoveChartIndex];
      // Add to target
      await apiFetchJson(`/api/chart-packs/${copyMoveTarget}/charts`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chart }),
      });
      // Soft-delete from source
      const charts = activePack.charts.map((c, i) =>
        i === copyMoveChartIndex ? { ...c, deleted: true } : c,
      );
      await apiFetchJson(`/api/chart-packs/${activePack.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ charts }),
      });
      setCopyMoveChartIndex(null);
      setCopyMoveTarget(null);
      refetchPack();
      refetchPacks();
    } catch (err) { console.error(err); } finally { setCopyMoveLoading(false); }
  }, [copyMoveChartIndex, copyMoveTarget, activePack, refetchPack, refetchPacks]);

  const formStyle = {
    colorScheme: isLight ? 'light' as const : 'dark' as const,
    backgroundColor: 'rgb(var(--background))',
    color: 'rgb(var(--foreground))',
  };

  // ── VIEW: Pack detail ──
  if (activePackId && activePack) {
    const isOwner = !!user && user.id === activePack.user_id;
    return (
      <AppShell hideFooter>
        <div className="h-[calc(100vh-48px)] flex flex-col bg-background">
          {/* ── Merged header bar: back, title, stats, toolbar ── */}
          <div className="shrink-0 h-11 flex items-center px-4 gap-3 border-b border-border/30">
            <button
              onClick={() => setActivePackId(null)}
              className="flex items-center gap-1 text-[10px] font-medium text-muted-foreground/50 hover:text-foreground transition-colors shrink-0 -ml-1"
              aria-label="Back to all packs"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Packs</span>
            </button>

            <div className="w-px h-4 bg-border/20" />

            {editingName && isOwner ? (
              <div className="flex items-center gap-1.5 flex-1 min-w-0">
                <div className="flex items-center gap-1.5 flex-1 min-w-0">
                  <input
                    autoFocus type="text" value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') handleSaveName(); if (e.key === 'Escape') setEditingName(false); }}
                    className="h-7 px-2 text-[12px] font-semibold border border-border/50 rounded-[var(--radius)] focus:outline-none focus:ring-2 focus:ring-primary/25 text-foreground bg-transparent flex-1 min-w-0"
                    style={formStyle}
                  />
                  <input
                    type="text" value={editDesc}
                    onChange={(e) => setEditDesc(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') handleSaveName(); if (e.key === 'Escape') setEditingName(false); }}
                    placeholder="Description"
                    className="h-7 px-2 text-[12px] border border-border/50 rounded-[var(--radius)] focus:outline-none focus:ring-2 focus:ring-primary/25 text-foreground bg-transparent flex-1 min-w-0 placeholder:text-muted-foreground/25 hidden md:block"
                    style={formStyle}
                  />
                </div>
                <button onClick={handleSaveName} className="btn-icon text-success hover:text-success/80 hover:bg-success/10" aria-label="Save"><Check className="w-3.5 h-3.5" /></button>
                <button onClick={() => setEditingName(false)} className="btn-icon text-muted-foreground/30 hover:text-foreground hover:bg-primary/[0.06]" aria-label="Cancel"><X className="w-3.5 h-3.5" /></button>
              </div>
            ) : (
              <div className="flex items-center gap-2 min-w-0 flex-1">
                {isOwner ? (
                  <button
                    onClick={() => { setEditName(activePack.name); setEditDesc(activePack.description || ''); setEditingName(true); }}
                    className="flex items-center gap-1.5 min-w-0 group/title"
                  >
                    <span className="text-[13px] font-semibold text-foreground truncate">{activePack.name}</span>
                    <Edit3 className="w-3 h-3 text-muted-foreground/15 group-hover/title:text-primary transition-colors shrink-0" />
                  </button>
                ) : (
                  <span className="text-[13px] font-semibold text-foreground truncate">{activePack.name}</span>
                )}
                {activePack.description && (
                  <span className="text-[10px] text-muted-foreground/30 truncate hidden md:block max-w-[200px]" title={activePack.description}>{activePack.description}</span>
                )}

                <div className="w-px h-3 bg-border/15 hidden lg:block" />

                <span className="stat-label hidden lg:inline shrink-0">
                  {activePack.charts.length} chart{activePack.charts.length !== 1 ? 's' : ''}
                </span>
                <div className="flex items-center gap-1 text-muted-foreground/25 hidden lg:flex shrink-0">
                  <Clock className="w-2.5 h-2.5" />
                  <span className="text-[9px] font-mono tabular-nums">{relativeTime(activePack.updated_at)}</span>
                </div>
                {activePack.creator_name && !isOwner && (
                  <span className="text-[9px] text-muted-foreground/30 hidden lg:inline shrink-0">by {activePack.creator_name}</span>
                )}
              </div>
            )}

            <div className="flex items-center gap-1.5 shrink-0">
              {isOwner && (
                <button
                  onClick={handleTogglePublish}
                  className={`btn-toolbar ${
                    activePack.is_published
                      ? 'bg-success/10 text-success border-success/20 hover:bg-success/15 hover:border-success/30'
                      : ''
                  }`}
                  title={activePack.is_published ? 'Published — click to unpublish' : 'Private — click to publish'}
                >
                  {activePack.is_published ? <Globe className="w-2.5 h-2.5" /> : <Lock className="w-2.5 h-2.5" />}
                  <span className="hidden sm:inline">{activePack.is_published ? 'Published' : 'Private'}</span>
                </button>
              )}
              {isOwner && (
                <button
                  onClick={handleAddChart}
                  className="btn-primary"
                  title="Add chart"
                >
                  <Plus className="w-3 h-3" />
                  <span className="hidden sm:inline">Add chart</span>
                </button>
              )}
              <button
                onClick={handleRefresh} disabled={refreshing}
                className="btn-icon"
                title="Refresh"
                aria-label="Refresh data"
              >
                <RefreshCw className={`w-3 h-3 ${refreshing ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          {/* ── Chart grid ── */}
          <div className="flex-1 overflow-y-auto no-scrollbar p-3">
            <PackChartGrid
              pack={activePack} isLight={isLight} refreshKey={refreshKey}
              readOnly={!isOwner}
              onRemoveChart={handleRemoveChart}
              onEditChart={handleEditChart}
              onMoveChart={handleMoveChart}
              onCopyMoveChart={(i) => { setCopyMoveChartIndex(i); setCopyMoveTarget(null); }}
              onRefreshChart={handleRefreshChart}
              onAddChart={handleAddChart}
            />
          </div>

          {/* ── Edit overlay ── */}
          {editingChartIndex != null && activePack && (
            <ChartEditOverlay
              config={editingChartIndex === -1 ? { series: [], code: '' } : activePack.charts[editingChartIndex]}
              chartIndex={editingChartIndex === -1 ? activePack.charts.length : editingChartIndex}
              isLight={isLight}
              onSave={handleSaveEditedChart}
              onClose={() => setEditingChartIndex(null)}
            />
          )}

          {/* ── Copy / Move modal ── */}
          {copyMoveChartIndex != null && activePack && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/20 dark:bg-black/60" onClick={() => setCopyMoveChartIndex(null)}>
              <div className="panel-card shadow-md p-5 w-[380px] mx-4" onClick={(e) => e.stopPropagation()}>
                <div className="flex items-center justify-between mb-1">
                  <h3 className="text-[13px] font-semibold text-foreground">Copy / Move chart</h3>
                  <button onClick={() => setCopyMoveChartIndex(null)} className="btn-icon" aria-label="Close">
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
                <p className="stat-label mb-4 truncate">
                  {activePack.charts[copyMoveChartIndex]?.title || `Chart ${copyMoveChartIndex + 1}`}
                </p>

                {packs && packs.filter((p) => p.id !== activePack.id).length > 0 ? (
                  <>
                    <label className="stat-label block mb-1.5">Select target pack</label>
                    <div className="space-y-px max-h-[220px] overflow-y-auto no-scrollbar mb-4">
                      {packs.filter((p) => p.id !== activePack.id).map((p) => (
                        <button
                          key={p.id}
                          onClick={() => setCopyMoveTarget(p.id)}
                          className={`w-full text-left px-3 py-2 rounded-[var(--radius)] flex items-center gap-2 transition-colors ${
                            copyMoveTarget === p.id
                              ? 'bg-primary/[0.08] border border-primary/20 text-foreground'
                              : 'border border-transparent hover:bg-foreground/[0.03] hover:border-border/20'
                          }`}
                        >
                          <LineChart className="w-3 h-3 text-primary/30 shrink-0" />
                          <span className="text-[12px] font-medium text-foreground truncate flex-1">{p.name}</span>
                          <span className="stat-label shrink-0">{p.chart_count}</span>
                        </button>
                      ))}
                    </div>

                    <div className="flex gap-2">
                      <button
                        onClick={handleCopyToPack}
                        disabled={!copyMoveTarget || copyMoveLoading}
                        className="btn-primary flex-1"
                      >
                        {copyMoveLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Copy'}
                      </button>
                      <button
                        onClick={handleMoveToPackAction}
                        disabled={!copyMoveTarget || copyMoveLoading}
                        className="btn-secondary flex-1"
                      >
                        {copyMoveLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Move'}
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="text-center py-6">
                    <p className="text-[11px] text-muted-foreground/40">No other packs available.</p>
                    <p className="text-[10px] text-muted-foreground/25 mt-1.5">Create another pack first to copy or move charts.</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </AppShell>
    );
  }

  // ── VIEW: Pack list (default) ──
  const currentPacks = listTab === 'mine' ? packs : publishedPacks;
  return (
    <AppShell hideFooter>
      <div className="h-[calc(100vh-48px)] flex flex-col bg-background">
        {/* ── List header ── */}
        <div className="shrink-0 border-b border-border/30">
          {/* Row 1: Page title + "New Pack" button */}
          <div className="h-10 flex items-center px-4">
            <LayoutGrid className="w-3.5 h-3.5 text-muted-foreground/30 mr-2" />
            <h1 className="page-title">ChartPack</h1>
            {user && (
              <div className="ml-auto">
                <button
                  onClick={() => setCreateModalOpen(true)}
                  className="btn-primary"
                >
                  <Plus className="w-3 h-3" />
                  <span>New pack</span>
                </button>
              </div>
            )}
          </div>
          {/* Row 2: Tabs */}
          <div className="flex items-center gap-0.5 px-4 -mb-px">
            {user && (
              <button
                onClick={() => setListTab('mine')}
                className={`tab-link ${listTab === 'mine' ? 'active' : ''}`}
                aria-selected={listTab === 'mine'}
              >
                My Packs
                {packs && packs.length > 0 && (
                  <span className="ml-1.5 text-[10px] font-mono text-muted-foreground/25">{packs.length}</span>
                )}
              </button>
            )}
            <button
              onClick={() => setListTab('published')}
              className={`tab-link inline-flex items-center gap-1.5 ${listTab === 'published' ? 'active' : ''}`}
              aria-selected={listTab === 'published'}
            >
              <Users className="w-3 h-3" />
              Published
              {publishedPacks && publishedPacks.length > 0 && (
                <span className="text-[10px] font-mono text-muted-foreground/25">{publishedPacks.length}</span>
              )}
            </button>
          </div>
        </div>

        {/* ── Pack cards ── */}
        <div className="flex-1 overflow-y-auto no-scrollbar p-4">
          {currentPacks && currentPacks.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-3">
              {currentPacks.map((pack, idx) => (
                <button
                  key={pack.id}
                  onClick={() => setActivePackId(pack.id)}
                  className={`panel-card text-left overflow-hidden hover:border-primary/25 hover:shadow-md transition-all duration-150 group/pack relative flex flex-col animate-fade-in stagger-${Math.min(idx + 1, 10)}`}
                >
                  {/* Color density bar — visual chart preview */}
                  <div className="h-1 w-full flex gap-px overflow-hidden">
                    {pack.chart_count > 0
                      ? Array.from({ length: Math.min(pack.chart_count, 10) }, (_, i) => (
                          <div key={i} className="flex-1 h-full" style={{ backgroundColor: COLORWAY[i % COLORWAY.length], opacity: 0.55 }} />
                        ))
                      : <div className="flex-1 h-full bg-border/15" />
                    }
                  </div>

                  <div className="px-3 py-2.5 flex flex-col flex-1">
                    {/* Delete — visible on hover */}
                    {listTab === 'mine' && (
                      <button
                        onClick={(e) => handleDeletePackClick(pack.id, pack.name, e)}
                        className="absolute top-3 right-2.5 btn-icon w-6 h-6 opacity-0 group-hover/pack:opacity-100 text-muted-foreground/30 hover:text-destructive hover:bg-destructive/10 transition-all"
                        aria-label={`Delete ${pack.name}`}
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    )}

                    {/* Title + publish badge */}
                    <div className="flex items-center gap-2 pr-7">
                      <h3 className="text-[12px] font-semibold text-foreground group-hover/pack:text-primary transition-colors duration-150 truncate">
                        {pack.name}
                      </h3>
                      {listTab === 'mine' && pack.is_published && (
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-[3px] bg-success/[0.08] text-success border border-success/20 text-[8px] font-mono font-bold uppercase tracking-wider shrink-0">
                          <span className="w-1 h-1 rounded-full bg-success/70" />
                          Live
                        </span>
                      )}
                    </div>

                    {/* Description */}
                    {pack.description && (
                      <p className="text-[10px] text-muted-foreground/40 mt-1 line-clamp-2 leading-relaxed">{pack.description}</p>
                    )}

                    {/* Footer stats */}
                    <div className="flex items-center gap-3 mt-auto pt-2.5 border-t border-border/15">
                      <div className="flex items-center gap-1">
                        <LineChart className="w-3 h-3 text-primary/30" />
                        <span className="stat-label">{pack.chart_count} chart{pack.chart_count !== 1 ? 's' : ''}</span>
                      </div>
                      {listTab === 'published' && pack.creator_name && (
                        <span className="text-[9px] font-mono text-muted-foreground/30 truncate">{pack.creator_name}</span>
                      )}
                      <span className="text-[9px] font-mono text-muted-foreground/25 tabular-nums ml-auto">
                        {shortDate(pack.updated_at)}
                      </span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="text-center max-w-[260px]">
                <div className="w-10 h-10 mx-auto panel-card flex items-center justify-center mb-4">
                  {listTab === 'published' ? <Users className="w-4 h-4 text-muted-foreground/25" /> : <LayoutGrid className="w-4 h-4 text-muted-foreground/25" />}
                </div>
                <p className="text-[12px] font-medium text-foreground/50">
                  {listTab === 'published' ? 'No published packs yet' : 'No chart packs yet'}
                </p>
                <p className="text-[10px] text-muted-foreground/35 mt-1.5 leading-relaxed">
                  {listTab === 'published'
                    ? 'Published packs from other users will appear here.'
                    : 'Create a pack to organize and monitor your charts in one view.'}
                </p>
                {listTab === 'mine' && (
                  <button
                    onClick={() => setCreateModalOpen(true)}
                    className="btn-primary mt-4"
                  >
                    <Plus className="w-3.5 h-3.5" /> Create your first pack
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Delete pack confirmation ── */}
      {deletePackTarget && (
        <ConfirmDialog
          title="Delete chart pack"
          message={<>Delete <span className="font-semibold text-foreground">{deletePackTarget.name}</span>? The pack and all its charts will be archived.</>}
          confirmLabel="Delete"
          onConfirm={handleDeletePackConfirm}
          onCancel={() => setDeletePackTarget(null)}
        />
      )}

      {/* ── Create modal ── */}
      {createModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/20 dark:bg-black/60" onClick={() => setCreateModalOpen(false)}>
          <div className="panel-card shadow-md p-5 w-[380px] mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-[13px] font-semibold text-foreground">New chart pack</h3>
              <button onClick={() => setCreateModalOpen(false)} className="btn-icon" aria-label="Close">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            <p className="stat-label mb-4">Organize charts into a monitoring view</p>
            <div className="space-y-3">
              <div>
                <label className="stat-label block mb-1.5">Name</label>
                <input
                  autoFocus type="text" value={newPackName}
                  onChange={(e) => setNewPackName(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && newPackName.trim()) handleCreatePack(); }}
                  placeholder="e.g. Macro Dashboard, Equity Watchlist..."
                  className="w-full h-8 px-2.5 text-[12px] border border-border/50 rounded-[var(--radius)] focus:outline-none focus:ring-2 focus:ring-primary/25 placeholder:text-muted-foreground/25"
                  style={formStyle}
                />
              </div>
              <div>
                <label className="stat-label block mb-1.5">
                  Description
                  <span className="text-muted-foreground/25 normal-case tracking-normal font-sans ml-1">(optional)</span>
                </label>
                <textarea
                  value={newPackDesc} onChange={(e) => setNewPackDesc(e.target.value)}
                  placeholder="What's in this pack?" rows={2}
                  className="w-full px-2.5 py-2 text-[12px] border border-border/50 rounded-[var(--radius)] focus:outline-none focus:ring-2 focus:ring-primary/25 resize-none placeholder:text-muted-foreground/25"
                  style={formStyle}
                />
              </div>
            </div>
            <div className="flex gap-2 mt-5">
              <button onClick={() => setCreateModalOpen(false)} className="btn-secondary flex-1">Cancel</button>
              <button
                onClick={handleCreatePack} disabled={!newPackName.trim()}
                className="btn-primary flex-1"
              >
                Create pack
              </button>
            </div>
          </div>
        </div>
      )}

    </AppShell>
  );
}

export default function ChartPackPage() {
  return (
    <Suspense>
      <ChartPacksPageInner />
    </Suspense>
  );
}
