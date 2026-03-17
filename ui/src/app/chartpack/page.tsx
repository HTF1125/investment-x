'use client';

import React, { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import { useRouter, useSearchParams } from 'next/navigation';
import AppShell from '@/components/AppShell';
import { ChartErrorBoundary } from '@/components/ChartErrorBoundary';
import { apiFetchJson } from '@/lib/api';
import { getApiCode, buildChartFigure } from '@/lib/buildChartFigure';
import { applyChartTheme } from '@/lib/chartTheme';
import { useTheme } from '@/context/ThemeContext';
import { useQuery, useQueries, useQueryClient } from '@tanstack/react-query';
import {
  Loader2, Plus, Trash2, RefreshCw, ChevronLeft, ChevronRight,
  LineChart, Edit3, Check, X, ArrowUp, ArrowDown, LayoutGrid,
  Globe, Lock, Users,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

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
  code?: string;
  /** Pre-rendered Plotly figure (inline). */
  figure?: any;
  /** Reference to a Charts table record — figure loaded lazily. */
  chart_id?: string;
  series: SelectedSeries[];
  panes?: { id: number; label: string }[];
  annotations?: any[];
  logAxes?: number[];
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

function getPresetStartDate(months: number): string {
  if (months === 0) return '';
  const now = new Date();
  if (months === -1) return `${now.getFullYear()}-01-01`;
  const d = new Date(now);
  d.setMonth(d.getMonth() - months);
  return d.toISOString().slice(0, 10);
}

const RANGE_MAP: Record<string, number> = {
  '1M': 1, '3M': 3, '6M': 6, 'YTD': -1, '1Y': 12, '3Y': 36, '5Y': 60, 'MAX': 0,
};

// ── PackChart: memoized chart tile that receives data as props ──

const PackChart = React.memo(function PackChart({
  config, index, isLight, rawData, isLoading,
  onRemove, onEdit, onMoveUp, onMoveDown, isFirst, isLast, readOnly,
}: {
  config: ChartConfig; index: number; isLight: boolean;
  rawData: Record<string, (string | number | null)[]> | undefined;
  isLoading: boolean;
  onRemove: () => void; onEdit: () => void;
  onMoveUp: () => void; onMoveDown: () => void;
  isFirst: boolean; isLast: boolean; readOnly?: boolean;
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

  const logAxesSet = useMemo(() => new Set((config.logAxes || []).map(String)), [config.logAxes]);

  const figure = useMemo(() => {
    // Pre-rendered figure: inline or lazy-loaded by chart_id
    const sourceFig = config.figure || lazyFigure?.figure;
    if (sourceFig) {
      const themed = applyChartTheme(sourceFig, isLight ? 'light' : 'dark') as any;
      if (!themed) return null;
      if (config.title && themed.layout) {
        themed.layout.title = {
          text: config.title,
          font: { size: 12, color: isLight ? '#020617' : '#dbeafe', family: 'Inter, sans-serif' },
          x: 0.5, xanchor: 'center',
        };
      }
      return themed;
    }
    if (!rawData) return null;
    return buildChartFigure({
      rawData, series: seriesList, panes: config.panes,
      annotations: config.annotations as any, logAxes: logAxesSet,
      yAxisBases: (config as any).yAxisBases || {},
      yAxisRanges: (config as any).yAxisRanges || {},
      isLight, title: config.title, startDate, endDate, compact: true,
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

  return (
    <div className="panel-card flex flex-col group/chart overflow-hidden">
      {/* Floating toolbar */}
      {!readOnly && <div className="shrink-0 h-0 relative z-10">
        <div className="absolute right-1.5 top-1.5 flex items-center gap-px rounded-[var(--radius)] border border-border/30 bg-card/95 shadow-sm opacity-0 group-hover/chart:opacity-100 transition-opacity duration-150">
          {!isFirst && (
            <button onClick={onMoveUp} className="w-6 h-6 flex items-center justify-center text-muted-foreground/40 hover:text-foreground hover:bg-primary/[0.08] transition-colors rounded-l-[var(--radius)]" title="Move up">
              <ArrowUp className="w-3 h-3" />
            </button>
          )}
          {!isLast && (
            <button onClick={onMoveDown} className="w-6 h-6 flex items-center justify-center text-muted-foreground/40 hover:text-foreground hover:bg-primary/[0.08] transition-colors" title="Move down">
              <ArrowDown className="w-3 h-3" />
            </button>
          )}
          <button onClick={onEdit} className="w-6 h-6 flex items-center justify-center text-muted-foreground/40 hover:text-foreground hover:bg-primary/[0.08] transition-colors" title="Edit">
            <Edit3 className="w-3 h-3" />
          </button>
          <button onClick={onRemove} className="w-6 h-6 flex items-center justify-center text-muted-foreground/40 hover:text-destructive hover:bg-destructive/10 transition-colors rounded-r-[var(--radius)]" title="Remove">
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>}
      <div ref={containerRef} className="flex-1 min-h-0">
        {isLoading || figLoading ? (
          <div className="h-full flex items-center justify-center"><Loader2 className="w-4 h-4 animate-spin text-primary/30" /></div>
        ) : figure ? (
          <ChartErrorBoundary>
            <Plot data={figure.data} layout={figure.layout}
              config={{ responsive: true, displayModeBar: false, displaylogo: false, scrollZoom: true }}
              style={{ width: '100%', height: '100%' }}
              onInitialized={handlePlotInit} />
          </ChartErrorBoundary>
        ) : (
          <div className="h-full flex items-center justify-center text-[10px] text-muted-foreground/30">No data</div>
        )}
      </div>
    </div>
  );
});

// ── PackChartGrid: handles batch data fetching for all charts ──

function PackChartGrid({
  pack, isLight, refreshKey, readOnly,
  onRemoveChart, onEditChart, onMoveChart,
}: {
  pack: PackDetail; isLight: boolean; refreshKey: number; readOnly?: boolean;
  onRemoveChart: (i: number) => void;
  onEditChart: (i: number) => void;
  onMoveChart: (from: number, to: number) => void;
}) {
  const router = useRouter();

  // Separate charts into figure-based, code-based, and series-based
  const { seriesChartIndices, codeChartIndices, allCodes } = useMemo(() => {
    const seriesIdx: number[] = [];
    const codeIdx: number[] = [];
    const codes = new Set<string>();
    pack.charts.forEach((chart, i) => {
      // Pre-rendered or lazy-loaded figures need no data fetching
      if (chart.figure || chart.chart_id) return;
      if (chart.code?.trim()) {
        codeIdx.push(i);
      } else {
        seriesIdx.push(i);
        chart.series?.forEach((s) => codes.add(getApiCode(s)));
      }
    });
    return { seriesChartIndices: seriesIdx, codeChartIndices: codeIdx, allCodes: Array.from(codes) };
  }, [pack.charts]);

  // ONE batch fetch for all series-based charts
  const { data: batchData, isLoading: batchLoading } = useQuery({
    queryKey: ['pack-batch-data', pack.id, allCodes, refreshKey],
    queryFn: () => apiFetchJson<Record<string, (string | number | null)[]>>('/api/timeseries.custom', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ codes: allCodes }),
    }),
    enabled: allCodes.length > 0,
    staleTime: 120_000,
  });

  // Individual code executions for code-based charts (can't batch these)
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
  }, [pack.charts, batchData, batchLoading, codeDataMap, codeQueries, codeChartIndices]);

  // Pagination: 6 charts per page
  const PAGE_SIZE = 6;
  const [page, setPage] = useState(0);
  const totalPages = Math.ceil(pack.charts.length / PAGE_SIZE);

  // Reset page when pack changes
  useEffect(() => { setPage(0); }, [pack.id]);

  if (pack.charts.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center max-w-[240px]">
          <div className="w-12 h-12 mx-auto rounded-full bg-primary/[0.05] flex items-center justify-center mb-4">
            <LineChart className="w-5 h-5 text-muted-foreground/20" />
          </div>
          <p className="text-[13px] font-medium text-muted-foreground/50">Empty pack</p>
          <p className="text-[10px] text-muted-foreground/25 mt-1.5 leading-relaxed">
            {readOnly ? 'This pack has no charts yet.' : 'Add charts from the builder to start monitoring.'}
          </p>
          {!readOnly && (
            <button
              onClick={() => router.push(`/charts?addToPack=${pack.id}`)}
              className="mt-4 h-8 px-4 inline-flex items-center gap-1.5 rounded-[var(--radius)] text-[11px] font-medium bg-foreground text-background hover:opacity-90 transition-colors"
            >
              <Plus className="w-3.5 h-3.5" /> Add Chart
            </button>
          )}
        </div>
      </div>
    );
  }

  const startIdx = page * PAGE_SIZE;
  const chartsToRender = pack.charts.slice(startIdx, startIdx + PAGE_SIZE);

  return (
    <>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3" style={{ gridAutoRows: '320px' }}>
        {chartsToRender.map((chart, localIdx) => {
          const i = startIdx + localIdx;
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
              isFirst={i === 0} isLast={i === pack.charts.length - 1}
              readOnly={readOnly}
            />
          );
        })}
      </div>
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-1.5 pt-4 pb-2">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="w-7 h-7 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/40 hover:text-foreground hover:bg-primary/[0.06] transition-colors disabled:opacity-20 disabled:pointer-events-none"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          {Array.from({ length: totalPages }, (_, p) => (
            <button
              key={p}
              onClick={() => setPage(p)}
              className={`w-7 h-7 flex items-center justify-center rounded-[var(--radius)] text-[10px] font-mono transition-colors ${
                p === page
                  ? 'bg-foreground text-background font-bold'
                  : 'text-muted-foreground/40 hover:text-foreground hover:bg-primary/[0.06]'
              }`}
            >
              {p + 1}
            </button>
          ))}
          <button
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page === totalPages - 1}
            className="w-7 h-7 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/40 hover:text-foreground hover:bg-primary/[0.06] transition-colors disabled:opacity-20 disabled:pointer-events-none"
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

  const handleRefresh = useCallback(() => {
    setRefreshing(true);
    queryClient.invalidateQueries({ queryKey: ['pack-batch-data'] });
    queryClient.invalidateQueries({ queryKey: ['pack-chart-code'] });
    setRefreshKey((k) => k + 1);
    setTimeout(() => setRefreshing(false), 800);
  }, [queryClient]);

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

  const handleDeletePack = useCallback(async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await apiFetchJson(`/api/chart-packs/${id}`, { method: 'DELETE' });
      if (activePackId === id) setActivePackId(null);
      refetchPacks();
    } catch {}
  }, [activePackId, refetchPacks]);

  const handleRemoveChart = useCallback(async (chartIndex: number) => {
    if (!activePack) return;
    const charts = activePack.charts.filter((_, i) => i !== chartIndex);
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
    if (!activePack) return;
    sessionStorage.setItem('ix-edit-pack', JSON.stringify({
      packId: activePack.id, chartIndex, chart: activePack.charts[chartIndex],
    }));
    router.push('/charts?editPack=1');
  }, [activePack, router]);

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
          {/* ── Detail header ── */}
          <div className="shrink-0 border-b border-border/30">
            <div className="h-10 flex items-center px-4 gap-3">
              <button
                onClick={() => setActivePackId(null)}
                className="flex items-center gap-1.5 text-[10px] font-medium text-muted-foreground/50 hover:text-foreground transition-colors shrink-0 -ml-1"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">All Packs</span>
              </button>

              <div className="w-px h-4 bg-border/20" />

              {editingName && isOwner ? (
                <div className="flex items-center gap-1.5 flex-1 min-w-0">
                  <div className="flex flex-col gap-1 flex-1 min-w-0">
                    <input
                      autoFocus type="text" value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') handleSaveName(); if (e.key === 'Escape') setEditingName(false); }}
                      className="h-7 px-2 text-[13px] font-semibold border border-border/50 rounded-[var(--radius)] focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/15 text-foreground bg-transparent w-full"
                      style={formStyle}
                    />
                    <input
                      type="text" value={editDesc}
                      onChange={(e) => setEditDesc(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') handleSaveName(); if (e.key === 'Escape') setEditingName(false); }}
                      placeholder="Description (optional)"
                      className="h-6 px-2 text-[10px] border border-border/50 rounded-[var(--radius)] focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/15 text-foreground bg-transparent w-full placeholder:text-muted-foreground/25"
                      style={formStyle}
                    />
                  </div>
                  <button onClick={handleSaveName} className="btn-icon text-success hover:text-success/80 hover:bg-success/10"><Check className="w-3.5 h-3.5" /></button>
                  <button onClick={() => setEditingName(false)} className="btn-icon text-muted-foreground/30 hover:text-foreground hover:bg-primary/[0.06]"><X className="w-3.5 h-3.5" /></button>
                </div>
              ) : (
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  {isOwner ? (
                    <button
                      onClick={() => { setEditName(activePack.name); setEditDesc(activePack.description || ''); setEditingName(true); }}
                      className="flex items-center gap-1.5 min-w-0 group/title"
                    >
                      <span className="text-[14px] font-semibold text-foreground truncate">{activePack.name}</span>
                      <Edit3 className="w-3 h-3 text-muted-foreground/15 group-hover/title:text-primary transition-colors shrink-0" />
                    </button>
                  ) : (
                    <span className="text-[14px] font-semibold text-foreground truncate">{activePack.name}</span>
                  )}
                  {activePack.creator_name && !isOwner && (
                    <>
                      <div className="w-px h-3 bg-border/15 hidden md:block" />
                      <span className="text-[10px] text-muted-foreground/30 hidden md:block">by {activePack.creator_name}</span>
                    </>
                  )}
                  {activePack.description && (
                    <>
                      <div className="w-px h-3 bg-border/15 hidden md:block" />
                      <span className="text-[10px] text-muted-foreground/25 truncate hidden md:block max-w-[300px]">{activePack.description}</span>
                    </>
                  )}
                </div>
              )}

              <div className="flex items-center gap-1.5 shrink-0">
                <span className="stat-label hidden sm:block mr-1">
                  {activePack.charts.length} chart{activePack.charts.length !== 1 ? 's' : ''}
                </span>
                {isOwner && (
                  <button
                    onClick={() => router.push(`/charts?addToPack=${activePack.id}`)}
                    className="btn-toolbar flex items-center gap-1 bg-foreground text-background hover:opacity-90 transition-colors"
                    title="Add chart"
                  >
                    <Plus className="w-3 h-3" />
                    <span className="text-[10px] hidden sm:inline">Add Chart</span>
                  </button>
                )}
                {isOwner && (
                  <button
                    onClick={handleTogglePublish}
                    className={`btn-icon transition-colors ${
                      activePack.is_published
                        ? 'text-success hover:text-success/80 hover:bg-success/10'
                        : 'text-muted-foreground/40 hover:text-foreground hover:bg-primary/[0.06]'
                    }`}
                    title={activePack.is_published ? 'Published — click to unpublish' : 'Private — click to publish'}
                  >
                    {activePack.is_published ? <Globe className="w-3 h-3" /> : <Lock className="w-3 h-3" />}
                  </button>
                )}
                <button
                  onClick={handleRefresh} disabled={refreshing}
                  className="btn-icon text-muted-foreground hover:text-foreground hover:bg-primary/[0.06] transition-colors disabled:opacity-30"
                  title="Refresh"
                >
                  <RefreshCw className={`w-3 h-3 ${refreshing ? 'animate-spin' : ''}`} />
                </button>
              </div>
            </div>
          </div>

          {/* ── Chart grid ── */}
          <div className="flex-1 overflow-y-auto custom-scrollbar p-3">
            <PackChartGrid
              pack={activePack} isLight={isLight} refreshKey={refreshKey}
              readOnly={!isOwner}
              onRemoveChart={handleRemoveChart}
              onEditChart={handleEditChart}
              onMoveChart={handleMoveChart}
            />
          </div>
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
        <div className="shrink-0 h-10 flex items-center px-4 border-b border-border/30">
          <LayoutGrid className="w-3.5 h-3.5 text-muted-foreground/30 mr-2" />
          <div className="flex items-center gap-1">
            {user && (
              <button
                onClick={() => setListTab('mine')}
                className={`h-7 px-2.5 text-[11px] font-semibold uppercase tracking-[0.06em] rounded-[var(--radius)] transition-colors ${
                  listTab === 'mine' ? 'text-foreground bg-primary/[0.08]' : 'text-muted-foreground/40 hover:text-foreground'
                }`}
              >
                My Packs
                {packs && packs.length > 0 && (
                  <span className="ml-1.5 text-[10px] font-mono text-muted-foreground/25">{packs.length}</span>
                )}
              </button>
            )}
            <button
              onClick={() => setListTab('published')}
              className={`h-7 px-2.5 text-[11px] font-semibold uppercase tracking-[0.06em] rounded-[var(--radius)] transition-colors flex items-center gap-1.5 ${
                listTab === 'published' ? 'text-foreground bg-primary/[0.08]' : 'text-muted-foreground/40 hover:text-foreground'
              }`}
            >
              <Users className="w-3 h-3" />
              Published
              {publishedPacks && publishedPacks.length > 0 && (
                <span className="text-[10px] font-mono text-muted-foreground/25">{publishedPacks.length}</span>
              )}
            </button>
          </div>
          {user && (
            <div className="ml-auto">
              <button
                onClick={() => setCreateModalOpen(true)}
                className="btn-toolbar flex items-center gap-1.5 bg-foreground text-background hover:opacity-90 transition-colors"
              >
                <Plus className="w-3 h-3" />
                <span className="text-[10px]">New Pack</span>
              </button>
            </div>
          )}
        </div>

        {/* ── Pack cards ── */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
          {currentPacks && currentPacks.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {currentPacks.map((pack) => (
                <button
                  key={pack.id}
                  onClick={() => setActivePackId(pack.id)}
                  className="panel-card text-left px-4 py-3.5 hover:border-primary/25 transition-all duration-150 group/pack relative"
                >
                  {/* Delete — top-right corner (only for own packs) */}
                  {listTab === 'mine' && (
                    <button
                      onClick={(e) => handleDeletePack(pack.id, e)}
                      className="absolute top-2 right-2 w-6 h-6 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/10 hover:text-destructive hover:bg-destructive/10 opacity-0 group-hover/pack:opacity-100 transition-all"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  )}

                  {/* Title + publish badge */}
                  <div className="flex items-center gap-1.5 pr-6">
                    <h3 className="text-[13px] font-semibold text-foreground group-hover/pack:text-primary transition-colors truncate">
                      {pack.name}
                    </h3>
                    {listTab === 'mine' && pack.is_published && (
                      <span title="Published"><Globe className="w-3 h-3 text-success/60 shrink-0" /></span>
                    )}
                  </div>

                  {/* Description or creator */}
                  {pack.description ? (
                    <p className="text-[10px] text-muted-foreground/35 mt-1.5 line-clamp-2 leading-relaxed">{pack.description}</p>
                  ) : (
                    <div className="mt-1.5" />
                  )}

                  {/* Footer stats */}
                  <div className="flex items-center gap-2 mt-3 pt-2.5 border-t border-border/15">
                    <div className="flex items-center gap-1.5">
                      <LineChart className="w-3 h-3 text-muted-foreground/20" />
                      <span className="stat-label">{pack.chart_count} chart{pack.chart_count !== 1 ? 's' : ''}</span>
                    </div>
                    {listTab === 'published' && pack.creator_name && (
                      <>
                        <span className="text-muted-foreground/10">|</span>
                        <span className="text-[9px] font-mono text-muted-foreground/25">{pack.creator_name}</span>
                      </>
                    )}
                    <span className="text-muted-foreground/10">|</span>
                    <span className="text-[9px] font-mono text-muted-foreground/20 tabular-nums">
                      {new Date(pack.updated_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="text-center max-w-[260px]">
                <div className="w-12 h-12 mx-auto rounded-full bg-primary/[0.05] flex items-center justify-center mb-4">
                  {listTab === 'published' ? <Users className="w-5 h-5 text-muted-foreground/20" /> : <LayoutGrid className="w-5 h-5 text-muted-foreground/20" />}
                </div>
                <p className="text-[13px] font-medium text-muted-foreground/50">
                  {listTab === 'published' ? 'No published packs yet' : 'No chart packs yet'}
                </p>
                <p className="text-[10px] text-muted-foreground/25 mt-1.5 leading-relaxed">
                  {listTab === 'published'
                    ? 'Published packs from other users will appear here.'
                    : 'Create a pack to organize and monitor your charts in one view.'}
                </p>
                {listTab === 'mine' && (
                  <button
                    onClick={() => setCreateModalOpen(true)}
                    className="mt-4 h-8 px-4 inline-flex items-center gap-1.5 rounded-[var(--radius)] text-[11px] font-medium bg-foreground text-background hover:opacity-90 transition-colors"
                  >
                    <Plus className="w-3.5 h-3.5" /> Create your first pack
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Create modal ── */}
      {createModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-[2px]" onClick={() => setCreateModalOpen(false)}>
          <div className="bg-card border border-border/50 rounded-[var(--radius)] shadow-md p-5 w-[380px]" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-[13px] font-semibold text-foreground mb-4">New Chart Pack</h3>
            <div className="space-y-3">
              <div>
                <label className="stat-label block mb-1.5">Name</label>
                <input
                  autoFocus type="text" value={newPackName}
                  onChange={(e) => setNewPackName(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && newPackName.trim()) handleCreatePack(); }}
                  placeholder="e.g. Macro Dashboard, Equity Watchlist..."
                  className="w-full h-8 px-2.5 text-[12px] border border-border/50 rounded-[var(--radius)] bg-background text-foreground focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/15 placeholder:text-muted-foreground/25"
                  style={formStyle}
                />
              </div>
              <div>
                <label className="stat-label block mb-1.5">Description <span className="text-muted-foreground/20 normal-case tracking-normal">(optional)</span></label>
                <textarea
                  value={newPackDesc} onChange={(e) => setNewPackDesc(e.target.value)}
                  placeholder="What's in this pack?" rows={2}
                  className="w-full px-2.5 py-2 text-[11px] border border-border/50 rounded-[var(--radius)] bg-background text-foreground focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/15 resize-none placeholder:text-muted-foreground/25"
                  style={formStyle}
                />
              </div>
            </div>
            <div className="flex gap-2 mt-5">
              <button onClick={() => setCreateModalOpen(false)} className="flex-1 h-8 rounded-[var(--radius)] text-[11px] font-medium border border-border/30 text-muted-foreground hover:text-foreground hover:bg-primary/[0.04] transition-colors">Cancel</button>
              <button
                onClick={handleCreatePack} disabled={!newPackName.trim()}
                className="flex-1 h-8 rounded-[var(--radius)] text-[11px] font-medium bg-foreground text-background hover:opacity-90 transition-colors disabled:opacity-30"
              >
                Create Pack
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
