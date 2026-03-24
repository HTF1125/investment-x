'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import AppShell from '@/components/layout/AppShell';
import { ChartErrorBoundary } from '@/components/shared/ChartErrorBoundary';
import { apiFetchJson } from '@/lib/api';
import { getApiCode, buildChartFigure } from '@/lib/buildChartFigure';
import { applyChartTheme } from '@/lib/chartTheme';
import { useTheme } from '@/context/ThemeContext';
import { useQuery, useQueries, useQueryClient } from '@tanstack/react-query';
import {
  Loader2, Plus, Trash2, RefreshCw, ChevronLeft,
  LineChart, Edit3, Check, X, ArrowUp, ArrowDown, LayoutGrid,
} from 'lucide-react';

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
  figure?: any;
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
  name: string;
  description: string | null;
  charts: ChartConfig[];
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
  onRemove, onEdit, onMoveUp, onMoveDown, isFirst, isLast,
}: {
  config: ChartConfig; index: number; isLight: boolean;
  rawData: Record<string, (string | number | null)[]> | undefined;
  isLoading: boolean;
  onRemove: () => void; onEdit: () => void;
  onMoveUp: () => void; onMoveDown: () => void;
  isFirst: boolean; isLast: boolean;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const plotRef = useRef<HTMLElement | null>(null);

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
    if (config.figure) {
      const themed = applyChartTheme(config.figure, isLight ? 'light' : 'dark') as any;
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
  }, [config.figure, rawData, seriesList, config.panes, config.annotations, logAxesSet, isLight, config.title, startDate, endDate]);

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
    <div className="panel-card flex flex-col group/chart">
      <div className="shrink-0 h-0 relative">
        <div className="absolute right-1 top-1 z-10 flex items-center gap-0.5 opacity-0 group-hover/chart:opacity-100 transition-opacity bg-card/80 rounded-[var(--radius)] px-0.5">
          {!isFirst && (
            <button onClick={onMoveUp} className="w-5 h-5 flex items-center justify-center text-muted-foreground/30 hover:text-foreground transition-colors" title="Move up">
              <ArrowUp className="w-3 h-3" />
            </button>
          )}
          {!isLast && (
            <button onClick={onMoveDown} className="w-5 h-5 flex items-center justify-center text-muted-foreground/30 hover:text-foreground transition-colors" title="Move down">
              <ArrowDown className="w-3 h-3" />
            </button>
          )}
          <button onClick={onEdit} className="w-5 h-5 flex items-center justify-center text-muted-foreground/30 hover:text-foreground transition-colors" title="Edit">
            <Edit3 className="w-3 h-3" />
          </button>
          <button onClick={onRemove} className="w-5 h-5 flex items-center justify-center text-muted-foreground/30 hover:text-destructive transition-colors" title="Remove">
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>
      <div ref={containerRef} className="flex-1 min-h-0">
        {isLoading ? (
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
  pack, isLight, refreshKey,
  onRemoveChart, onEditChart, onMoveChart,
}: {
  pack: PackDetail; isLight: boolean; refreshKey: number;
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
      if (chart.figure) return; // Pre-rendered figures need no fetching
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
      if (chart.figure) return { rawData: undefined, isLoading: false };
      if (chart.code?.trim()) {
        return { rawData: codeDataMap.get(i), isLoading: !codeDataMap.has(i) || (codeDataMap.get(i) === undefined && codeQueries[codeChartIndices.indexOf(i)]?.isLoading) };
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

  if (pack.charts.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <LineChart className="w-10 h-10 mx-auto text-muted-foreground/10 mb-3" />
          <p className="text-[13px] font-medium text-muted-foreground/40">No charts in this pack</p>
          <button
            onClick={() => router.push(`/chartpack?chartpack=${pack.id}`)}
            className="mt-3 h-7 px-3 inline-flex items-center gap-1.5 rounded-[var(--radius)] text-[11px] font-medium bg-foreground text-background hover:opacity-90 transition-colors"
          >
            <Plus className="w-3 h-3" /> Add Chart
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3" style={{ gridAutoRows: '320px' }}>
      {pack.charts.map((chart, i) => (
        <PackChart
          key={`${pack.id}-${i}`}
          config={chart} index={i} isLight={isLight}
          rawData={chartDataList[i].rawData as any}
          isLoading={chartDataList[i].isLoading}
          onRemove={() => onRemoveChart(i)}
          onEdit={() => onEditChart(i)}
          onMoveUp={() => onMoveChart(i, i - 1)}
          onMoveDown={() => onMoveChart(i, i + 1)}
          isFirst={i === 0} isLast={i === pack.charts.length - 1}
        />
      ))}
    </div>
  );
}

// ── Main Page ──

export default function ChartPacksPage() {
  const { theme } = useTheme();
  const isLight = theme === 'light';
  const queryClient = useQueryClient();
  const router = useRouter();

  const [activePackId, setActivePackId] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newPackName, setNewPackName] = useState('');
  const [newPackDesc, setNewPackDesc] = useState('');
  const [editingName, setEditingName] = useState(false);
  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');

  const { data: packs, refetch: refetchPacks } = useQuery({
    queryKey: ['chart-packs'],
    queryFn: () => apiFetchJson<PackSummary[]>('/api/chart-packs'),
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

  const formStyle = {
    colorScheme: isLight ? 'light' as const : 'dark' as const,
    backgroundColor: 'rgb(var(--background))',
    color: 'rgb(var(--foreground))',
  };

  // ── VIEW: Pack detail ──
  if (activePackId && activePack) {
    return (
      <AppShell hideFooter>
        <div className="h-[calc(100vh-48px)] flex flex-col bg-background">
          <div className="shrink-0 h-9 flex items-center px-3 border-b border-border/30 gap-2">
            <button
              onClick={() => setActivePackId(null)}
              className="flex items-center gap-1 text-[10px] text-muted-foreground/50 hover:text-foreground transition-colors shrink-0"
            >
              <ChevronLeft className="w-3 h-3" /> All Packs
            </button>
            <div className="w-px h-4 bg-border/20 mx-1" />

            {editingName ? (
              <div className="flex items-center gap-1.5 flex-1 min-w-0">
                <input
                  autoFocus type="text" value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') handleSaveName(); if (e.key === 'Escape') setEditingName(false); }}
                  className="h-6 px-1.5 text-[12px] font-medium border border-border/50 rounded-[var(--radius)] focus:outline-none focus:border-primary/40 text-foreground bg-transparent flex-1 min-w-0"
                  style={formStyle}
                />
                <button onClick={handleSaveName} className="w-5 h-5 flex items-center justify-center text-success hover:text-success/80"><Check className="w-3.5 h-3.5" /></button>
                <button onClick={() => setEditingName(false)} className="w-5 h-5 flex items-center justify-center text-muted-foreground/30 hover:text-foreground"><X className="w-3.5 h-3.5" /></button>
              </div>
            ) : (
              <button
                onClick={() => { setEditName(activePack.name); setEditDesc(activePack.description || ''); setEditingName(true); }}
                className="flex items-center gap-1.5 text-[13px] font-semibold text-foreground hover:text-primary transition-colors group/title truncate"
              >
                {activePack.name}
                <Edit3 className="w-3 h-3 text-muted-foreground/20 group-hover/title:text-primary transition-colors shrink-0" />
              </button>
            )}

            {activePack.description && !editingName && (
              <span className="text-[10px] text-muted-foreground/30 truncate hidden sm:block">{activePack.description}</span>
            )}

            <div className="ml-auto flex items-center gap-1 shrink-0">
              <span className="text-[9px] font-mono text-muted-foreground/30 hidden sm:block">
                {activePack.charts.length} chart{activePack.charts.length !== 1 ? 's' : ''}
              </span>
              <button
                onClick={handleRefresh} disabled={refreshing}
                className="h-7 px-2 flex items-center gap-1.5 rounded-[var(--radius)] text-[10px] font-medium text-muted-foreground hover:text-foreground hover:bg-primary/[0.06] transition-colors disabled:opacity-30"
              >
                <RefreshCw className={`w-3 h-3 ${refreshing ? 'animate-spin' : ''}`} />
                <span className="hidden sm:inline">Refresh</span>
              </button>
              <button
                onClick={() => router.push(`/chartpack?chartpack=${activePack.id}`)}
                className="h-7 px-2.5 flex items-center gap-1.5 rounded-[var(--radius)] text-[10px] font-medium bg-foreground text-background hover:opacity-90 transition-colors"
              >
                <Plus className="w-3 h-3" /> Add Chart
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto custom-scrollbar p-3">
            <PackChartGrid
              pack={activePack} isLight={isLight} refreshKey={refreshKey}
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
  return (
    <AppShell hideFooter>
      <div className="h-[calc(100vh-48px)] flex flex-col bg-background">
        <div className="shrink-0 h-9 flex items-center px-4 border-b border-border/30">
          <LayoutGrid className="w-3.5 h-3.5 text-muted-foreground/40 mr-2" />
          <span className="text-[11px] font-semibold uppercase tracking-[0.06em] text-foreground">Chart Packs</span>
          <div className="ml-auto">
            <button
              onClick={() => setCreateModalOpen(true)}
              className="h-7 px-2.5 flex items-center gap-1.5 rounded-[var(--radius)] text-[10px] font-medium bg-foreground text-background hover:opacity-90 transition-colors"
            >
              <Plus className="w-3 h-3" /> New Pack
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
          {packs && packs.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {packs.map((pack) => (
                <button
                  key={pack.id}
                  onClick={() => setActivePackId(pack.id)}
                  className="panel-card text-left p-4 hover:border-primary/30 transition-colors group/pack"
                >
                  <div className="flex items-start justify-between">
                    <h3 className="text-[13px] font-semibold text-foreground group-hover/pack:text-primary transition-colors truncate">
                      {pack.name}
                    </h3>
                    <button
                      onClick={(e) => handleDeletePack(pack.id, e)}
                      className="w-5 h-5 flex items-center justify-center text-muted-foreground/15 hover:text-destructive opacity-0 group-hover/pack:opacity-100 transition-all shrink-0 -mt-0.5"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                  {pack.description && (
                    <p className="text-[10px] text-muted-foreground/40 mt-1 line-clamp-2">{pack.description}</p>
                  )}
                  <div className="flex items-center gap-3 mt-3">
                    <span className="text-[10px] font-mono text-muted-foreground/30">
                      {pack.chart_count} chart{pack.chart_count !== 1 ? 's' : ''}
                    </span>
                    <span className="text-[9px] text-muted-foreground/20">
                      {new Date(pack.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <LayoutGrid className="w-10 h-10 mx-auto text-muted-foreground/10 mb-3" />
                <p className="text-[13px] font-medium text-muted-foreground/40">No chart packs yet</p>
                <button
                  onClick={() => setCreateModalOpen(true)}
                  className="mt-3 h-7 px-3 inline-flex items-center gap-1.5 rounded-[var(--radius)] text-[11px] font-medium bg-foreground text-background hover:opacity-90 transition-colors"
                >
                  <Plus className="w-3 h-3" /> Create your first pack
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {createModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setCreateModalOpen(false)}>
          <div className="bg-card border border-border/50 rounded-[var(--radius)] shadow-lg p-4 w-[360px]" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-[12px] font-semibold uppercase tracking-wider text-foreground mb-3">New Chart Pack</h3>
            <input
              autoFocus type="text" value={newPackName}
              onChange={(e) => setNewPackName(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && newPackName.trim()) handleCreatePack(); }}
              placeholder="Pack name..."
              className="w-full px-2.5 py-1.5 text-[12px] border border-border/50 rounded-[var(--radius)] bg-background text-foreground focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/15"
              style={formStyle}
            />
            <textarea
              value={newPackDesc} onChange={(e) => setNewPackDesc(e.target.value)}
              placeholder="Description (optional)..." rows={2}
              className="w-full mt-2 px-2.5 py-1.5 text-[11px] border border-border/50 rounded-[var(--radius)] bg-background text-foreground focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/15 resize-none"
              style={formStyle}
            />
            <div className="flex gap-2 mt-3">
              <button onClick={() => setCreateModalOpen(false)} className="flex-1 h-7 rounded-[var(--radius)] text-[11px] font-medium border border-border/30 text-muted-foreground hover:text-foreground transition-colors">Cancel</button>
              <button
                onClick={handleCreatePack} disabled={!newPackName.trim()}
                className="flex-1 h-7 rounded-[var(--radius)] text-[11px] font-medium bg-foreground text-background hover:opacity-90 transition-colors disabled:opacity-30"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
