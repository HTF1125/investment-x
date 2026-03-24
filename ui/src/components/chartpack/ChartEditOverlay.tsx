'use client';

import React, { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import dynamic from 'next/dynamic';
import {
  X, Check, Loader2, Play, ChevronDown, LineChart,
  PanelRightOpen, PanelRightClose, Eye, EyeOff,
  GripVertical, AlertTriangle, Table2, Terminal,
} from 'lucide-react';
import { buildChartFigure, stripThemeFromFigure, getApiCode, type AnnotationConfig } from '@/lib/buildChartFigure';
import { applyChartTheme, COLORWAY } from '@/lib/chartTheme';
import { RANGE_MAP, RANGE_PRESETS, getPresetStartDate } from '@/lib/constants';
import { ChartErrorBoundary } from '@/components/shared/ChartErrorBoundary';
import { apiFetchJson } from '@/lib/api';
import { useQuery } from '@tanstack/react-query';
import { Reorder } from 'framer-motion';

const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false });

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center">
      <Loader2 className="w-5 h-5 animate-spin text-primary/30" />
    </div>
  ),
}) as any;

// ── Types ────────────────────────────────────────────────────────────────────

interface SelectedSeries {
  code: string; name: string; chartType: string; yAxis: string;
  yAxisIndex?: number; visible: boolean; color?: string;
  transform?: string; transformParam?: number; lineStyle?: string;
  lineWidth?: number; paneId?: number;
  showMarkers?: boolean; markerSize?: number; markerShape?: string;
  fillOpacity?: number; showDataLabels?: boolean;
}

interface ChartConfig {
  title?: string; description?: string; code?: string;
  figure?: any; chart_id?: string;
  series: SelectedSeries[];
  panes?: { id: number; label: string }[];
  annotations?: AnnotationConfig[];
  logAxes?: (number | string)[]; invertedAxes?: string[]; pctAxes?: string[];
  activeRange?: string; startDate?: string; endDate?: string;
  yAxisBases?: Record<string, number>;
  yAxisRanges?: Record<string, { min?: number; max?: number }>;
  showRecessions?: boolean; hoverMode?: string;
  showLegend?: boolean; legendPosition?: string;
  showGridlines?: boolean; gridlineStyle?: string;
  axisTitles?: Record<string, string>; titleFontSize?: number;
  showZeroline?: boolean; bargap?: number;
  [key: string]: any;
}

interface Props {
  config: ChartConfig; chartIndex: number; isLight: boolean;
  onSave: (updated: ChartConfig) => void; onClose: () => void;
}

// ── Constants ────────────────────────────────────────────────────────────────

const CHART_TYPES = [
  { key: 'line', label: 'Line' }, { key: 'bar', label: 'Bar' }, { key: 'area', label: 'Area' },
  { key: 'scatter', label: 'Scatter' }, { key: 'stackedbar', label: 'Stk Bar' }, { key: 'stackedarea', label: 'Stk Area' },
];
const LINE_STYLES = [
  { key: 'solid', label: '\u2500\u2500' }, { key: 'dash', label: '\u2504\u2504' },
  { key: 'dot', label: '\u00B7\u00B7\u00B7' }, { key: 'dashdot', label: '\u2504\u00B7' },
];
const LINE_WIDTHS = [1, 1.5, 2.5];

type Tab = 'series' | 'annotate' | 'settings';

// ── Helpers ──────────────────────────────────────────────────────────────────

function fmtNum(v: number | null | undefined, decimals = 2): string {
  if (v == null || !isFinite(v)) return '\u2014';
  return v.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

// ── Series Row ───────────────────────────────────────────────────────────────

function SeriesRowInline({
  series, index, onUpdate, panes,
}: {
  series: SelectedSeries; index: number;
  onUpdate: (updates: Partial<SelectedSeries>) => void;
  panes: { id: number; label: string }[];
}) {
  const color = series.color || COLORWAY[index % COLORWAY.length];
  const [expanded, setExpanded] = useState(false);
  const [hovered, setHovered] = useState(false);

  return (
    <div className={`border-b border-border/15 transition-colors ${expanded ? 'bg-foreground/[0.02]' : ''} ${series.visible === false ? 'opacity-40' : ''}`}>
      <div
        className="flex items-center gap-1 px-2 h-7 cursor-pointer group"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        onClick={(e) => {
          if ((e.target as HTMLElement).closest('button, input')) return;
          setExpanded(!expanded);
        }}
      >
        <GripVertical className="w-3 h-3 text-muted-foreground/25 shrink-0 cursor-grab active:cursor-grabbing" />
        <input type="color" value={color} onChange={e => onUpdate({ color: e.target.value })}
          className="w-3.5 h-3.5 rounded cursor-pointer border-0 p-0 shrink-0" onClick={e => e.stopPropagation()} />
        <span className="text-[11px] text-foreground truncate flex-1 min-w-0">{series.name || series.code}</span>
        <span className="text-[8px] font-mono text-muted-foreground/40 shrink-0">{series.chartType}</span>
        <span className={`text-[8px] font-mono font-bold shrink-0 ${(series.yAxisIndex ?? 0) > 0 ? 'text-primary' : 'text-muted-foreground/30'}`}>
          Y{(series.yAxisIndex ?? 0) + 1}
        </span>
        {hovered ? (
          <button onClick={(e) => { e.stopPropagation(); onUpdate({ visible: !series.visible }); }}
            className="w-4 h-4 flex items-center justify-center text-muted-foreground/30 hover:text-foreground transition-colors shrink-0">
            {series.visible === false ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
          </button>
        ) : (
          <ChevronDown className={`w-3 h-3 text-muted-foreground/20 shrink-0 transition-transform duration-150 ${expanded ? 'rotate-180' : ''}`} />
        )}
      </div>

      {expanded && (
        <div className="px-2 pb-2.5 pt-1.5 border-t border-border/10 space-y-2">
          {/* Chart type */}
          <div className="flex items-center gap-1 flex-wrap">
            {CHART_TYPES.map(t => (
              <button key={t.key} onClick={() => onUpdate({ chartType: t.key })}
                className={`h-[22px] px-2 rounded text-[9px] font-mono transition-colors ${
                  series.chartType === t.key ? 'bg-foreground text-background font-bold' : 'text-muted-foreground/40 hover:text-foreground hover:bg-foreground/[0.05]'
                }`}>{t.label}</button>
            ))}
          </div>
          {/* Line style + width */}
          <div className="flex items-center gap-1">
            {LINE_STYLES.map(st => (
              <button key={st.key} onClick={() => onUpdate({ lineStyle: st.key })}
                className={`h-[22px] px-2 rounded text-[9px] font-mono transition-colors ${
                  (series.lineStyle || 'solid') === st.key ? 'bg-foreground text-background' : 'text-muted-foreground/35 hover:text-foreground hover:bg-foreground/[0.05]'
                }`}>{st.label}</button>
            ))}
            <div className="w-px h-3.5 bg-border/20 mx-0.5" />
            {LINE_WIDTHS.map(w => (
              <button key={w} onClick={() => onUpdate({ lineWidth: w })}
                className={`h-[22px] w-7 rounded text-[9px] font-mono text-center transition-colors ${
                  (series.lineWidth ?? 1.5) === w ? 'bg-foreground text-background' : 'text-muted-foreground/35 hover:text-foreground hover:bg-foreground/[0.05]'
                }`}>{w}</button>
            ))}
          </div>
          {/* Axis + Pane */}
          <div className="flex items-center gap-1">
            <span className="text-[8px] font-mono text-muted-foreground/30 uppercase tracking-wider mr-0.5">Axis</span>
            {[0, 1, 2].map(yi => (
              <button key={yi} onClick={() => onUpdate({ yAxisIndex: yi })}
                className={`h-[22px] w-7 rounded text-[9px] font-mono font-bold transition-colors ${
                  (series.yAxisIndex ?? 0) === yi ? 'bg-foreground text-background' : 'text-muted-foreground/35 hover:text-foreground hover:bg-foreground/[0.05]'
                }`}>Y{yi + 1}</button>
            ))}
            {panes.length > 1 && (
              <>
                <div className="w-px h-3.5 bg-border/20 mx-0.5" />
                <span className="text-[8px] font-mono text-muted-foreground/30 uppercase tracking-wider mr-0.5">Pane</span>
                {panes.map(p => (
                  <button key={p.id} onClick={() => onUpdate({ paneId: p.id })}
                    className={`h-[22px] px-2 rounded text-[9px] font-mono transition-colors ${
                      (series.paneId ?? 0) === p.id ? 'bg-foreground text-background' : 'text-muted-foreground/35 hover:text-foreground hover:bg-foreground/[0.05]'
                    }`}>P{p.id + 1}</button>
                ))}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main Overlay ─────────────────────────────────────────────────────────────

export default function ChartEditOverlay({ config, chartIndex, isLight, onSave, onClose }: Props) {
  const [title, setTitle] = useState(config.title || '');
  const [description, setDescription] = useState(config.description || '');
  const [series, setSeries] = useState<SelectedSeries[]>(() => (config.series || []).map(s => ({ ...s })));
  const [panes, setPanes] = useState<{ id: number; label: string }[]>(config.panes || [{ id: 0, label: 'Pane 1' }]);
  const [annotations, setAnnotations] = useState<AnnotationConfig[]>((config.annotations as AnnotationConfig[]) || []);
  const [logAxes, setLogAxes] = useState<Set<string>>(() => {
    const raw = config.logAxes || [];
    // Handle both old format (numbers like [0, 1] meaning yAxisIndex) and new format (strings like ["0-0", "0-1"])
    return new Set(raw.map((v: any) => {
      const s = String(v);
      return s.includes('-') ? s : `0-${s}`;
    }));
  });
  const [invertedAxes, setInvertedAxes] = useState<Set<string>>(new Set(config.invertedAxes || []));
  const [pctAxes, setPctAxes] = useState<Set<string>>(new Set(config.pctAxes || []));
  const [activeRange, setActiveRange] = useState(config.activeRange || 'MAX');
  const [startDate, setStartDate] = useState(config.startDate || '');
  const [endDate, setEndDate] = useState(config.endDate || '');
  const [yAxisRanges, setYAxisRanges] = useState<Record<string, { min?: number; max?: number }>>(config.yAxisRanges || {});
  const [showRecessions, setShowRecessions] = useState(config.showRecessions || false);
  const [hoverMode, setHoverMode] = useState<string>(config.hoverMode || 'x unified');
  const [showLegend, setShowLegend] = useState(config.showLegend || false);
  const [showGridlines, setShowGridlines] = useState(config.showGridlines !== false);
  const [showZeroline, setShowZeroline] = useState(config.showZeroline !== false);
  const [showStats, setShowStats] = useState(false);

  // Code editor
  const [code, setCode] = useState(config.code || '');
  const [codeResult, setCodeResult] = useState<Record<string, any> | null>(null);
  const [codeRunning, setCodeRunning] = useState(false);
  const [codeError, setCodeError] = useState<string | null>(null);
  const [editorHeight, setEditorHeight] = useState(200);

  // Layout
  const [rightSidebarOpen, setRightSidebarOpen] = useState(true);
  const [sidebarWidth, setSidebarWidth] = useState(280);
  const [codeCollapsed, setCodeCollapsed] = useState(false);
  const [tab, setTab] = useState<Tab>('series');

  // Escape to close
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [onClose]);

  // ── Data ───────────────────────────────────────────────────────────────────
  // Editor always fetches live data — ignore cached config.figure so edits
  // reflect the latest time-series values.  (config.chart_id still skips
  // fetching because those are references to the Charts table, not caches.)
  const hasCode = !!config.code?.trim();
  const seriesCodes = useMemo(() => {
    if (hasCode || config.chart_id) return [];
    return (config.series || []).map(s => getApiCode(s));
  }, [hasCode, config.chart_id, config.series]);

  const { data: codeData, isLoading: codeLoading } = useQuery({
    queryKey: ['pack-chart-code', chartIndex, config.code, 0],
    queryFn: () => apiFetchJson<Record<string, any>>('/api/timeseries.exec', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code: config.code }),
    }),
    enabled: hasCode && !config.chart_id, staleTime: 120_000,
  });
  const { data: batchData, isLoading: batchLoading } = useQuery({
    queryKey: ['overlay-batch', seriesCodes],
    queryFn: () => apiFetchJson<Record<string, (string | number | null)[]>>('/api/timeseries.custom', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ codes: seriesCodes }),
    }),
    enabled: seriesCodes.length > 0, staleTime: 120_000,
  });
  const { data: lazyFigureData } = useQuery({
    queryKey: ['chart-figure', config.chart_id],
    queryFn: () => apiFetchJson<{ figure?: any }>(`/api/v1/dashboard/charts/${config.chart_id}/figure`),
    enabled: !!config.chart_id && !config.figure, staleTime: 300_000,
  });
  const rawData = codeResult || (hasCode ? codeData : batchData);
  const lazyFigure = lazyFigureData?.figure;
  const dataLoading = codeLoading || batchLoading;

  // ── Callbacks ──────────────────────────────────────────────────────────────
  const updateSeries = useCallback((code: string, u: Partial<SelectedSeries>) =>
    setSeries(p => p.map(s => s.code === code ? { ...s, ...u } : s)), []);

  const runCode = useCallback(async () => {
    const trimmed = code.trim();
    if (!trimmed) return;
    setCodeRunning(true); setCodeError(null);
    try {
      const resp = await apiFetchJson<Record<string, any>>('/api/timeseries.exec', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: trimmed }),
      });
      setCodeResult(resp);
      const cols = (resp.__columns__ as string[] | undefined) || Object.keys(resp).filter(k => k !== 'Date' && k !== '__columns__');
      setSeries(prev => {
        const m = new Map(prev.map(s => [s.code, s]));
        return cols.map(c => m.get(c) || { code: c, name: c, chartType: 'line', yAxis: 'left', yAxisIndex: 0, visible: true, transform: 'none' });
      });
    } catch (e: any) { setCodeError(e.message || 'Failed'); }
    setCodeRunning(false);
  }, [code]);

  const addAnnotation = useCallback((type: AnnotationConfig['type']) => {
    const b: AnnotationConfig = { id: `a-${Date.now()}`, type, color: '#ef4444', paneId: 0 };
    if (type === 'hline') b.y = 0;
    if (type === 'vline') b.x = new Date().toISOString().split('T')[0];
    if (type === 'text') { b.x = new Date().toISOString().split('T')[0]; b.y = 0; b.text = ''; }
    setAnnotations(p => [...p, b]);
  }, []);
  const updateAnnotation = useCallback((id: string, u: Partial<AnnotationConfig>) => setAnnotations(p => p.map(a => a.id === id ? { ...a, ...u } : a)), []);
  const removeAnnotation = useCallback((id: string) => setAnnotations(p => p.filter(a => a.id !== id)), []);

  const toggleLogAxis = useCallback((key: string) => setLogAxes(p => { const n = new Set(p); if (n.has(key)) n.delete(key); else n.add(key); return n; }), []);
  const toggleInvertAxis = useCallback((key: string) => setInvertedAxes(p => { const n = new Set(p); if (n.has(key)) n.delete(key); else n.add(key); return n; }), []);
  const togglePctAxis = useCallback((key: string) => setPctAxes(p => { const n = new Set(p); if (n.has(key)) n.delete(key); else n.add(key); return n; }), []);
  const setYAxisRange = useCallback((key: string, field: 'min' | 'max', v: string) => {
    setYAxisRanges(p => ({ ...p, [key]: { ...(p[key] || {}), [field]: v === '' ? undefined : parseFloat(v) || undefined } }));
  }, []);

  const handleRangePreset = useCallback((label: string, months: number) => {
    setActiveRange(label); setStartDate(getPresetStartDate(months)); setEndDate('');
  }, []);

  // ── Build figure ───────────────────────────────────────────────────────────
  const resolvedSeries = useMemo(() => {
    if ((hasCode || codeResult) && rawData) {
      const cols = (rawData.__columns__ as string[] | undefined) || Object.keys(rawData).filter(k => k !== 'Date' && k !== '__columns__');
      const m = new Map(series.map(s => [s.code, s]));
      return cols.map(c => m.get(c) || { code: c, name: c, chartType: 'line', yAxis: 'left', yAxisIndex: 0, visible: true, transform: 'none' });
    }
    return series;
  }, [hasCode, codeResult, rawData, series]);

  const visibleSeries = useMemo(() => resolvedSeries.filter(s => s.visible !== false), [resolvedSeries]);

  const computedStartDate = useMemo(() => {
    if (startDate) return startDate;
    const m = RANGE_MAP[activeRange];
    return m != null ? getPresetStartDate(m) : '';
  }, [startDate, activeRange]);

  const figure = useMemo(() => {
    // Editor ignores cached config.figure — always build from live data.
    // Only use lazy-loaded chart_id figures (those are external chart refs, not caches).
    if (lazyFigure) {
      const t = applyChartTheme(lazyFigure, isLight ? 'light' : 'dark') as any;
      if (t?.layout) { t.layout.title = { text: title || '' }; t.layout.margin = { ...t.layout.margin, t: title ? 30 : 8 }; }
      return t;
    }
    if (!rawData) return null;
    return buildChartFigure({
      rawData, series: visibleSeries, allSeries: resolvedSeries, panes, annotations,
      logAxes, yAxisBases: config.yAxisBases || {}, yAxisRanges, invertedAxes, pctAxes,
      isLight, title, startDate: computedStartDate, endDate,
      showRecessions, hoverMode: hoverMode as 'x unified' | 'closest' | 'x',
      showLegend, showGridlines, showZeroline,
    });
  }, [lazyFigure, rawData, visibleSeries, resolvedSeries, panes, annotations, logAxes, invertedAxes, pctAxes, yAxisRanges, isLight, title, computedStartDate, endDate, showRecessions, hoverMode, showLegend, showGridlines, showZeroline]);

  // ── Plot resize ──
  const plotContainerRef = useRef<HTMLDivElement>(null);
  const plotGraphDivRef = useRef<HTMLElement | null>(null);
  useEffect(() => {
    const el = plotContainerRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(() => {
      const gd = plotGraphDivRef.current;
      if (!gd?.isConnected || !gd.clientHeight || !gd.clientWidth) return;
      import('plotly.js-dist-min').then(({ default: Plotly }) => {
        if (gd?.isConnected && gd.clientHeight > 0 && gd.clientWidth > 0) (Plotly as any).Plots.resize(gd);
      }).catch(() => {});
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // ── Stats ──
  const stats = useMemo(() => {
    if (!rawData?.Date || !showStats) return [];
    return visibleSeries.map((s, idx) => {
      const apiCode = getApiCode(s);
      const nums = ((rawData[apiCode] || []) as (number | null)[]).filter((v): v is number => v != null);
      const color = s.color || COLORWAY[idx % COLORWAY.length];
      if (nums.length === 0) return { code: s.code, color, last: null, chgPct: null, min: null, max: null };
      const last = nums[nums.length - 1];
      const prev = nums.length > 1 ? nums[nums.length - 2] : null;
      const chgPct = prev != null && prev !== 0 ? ((last - prev) / prev) * 100 : null;
      return { code: s.code, color, last, chgPct, min: Math.min(...nums), max: Math.max(...nums) };
    });
  }, [rawData, visibleSeries, showStats]);

  // ── Save ───────────────────────────────────────────────────────────────────
  const handleSave = useCallback(() => {
    // Build a theme-neutral cached figure from current live data so the pack
    // can render this chart instantly on next load without fetching data.
    let cachedFigure: { data: any[]; layout: any } | undefined;
    if (rawData && !config.chart_id) {
      const built = buildChartFigure({
        rawData, series: visibleSeries, allSeries: resolvedSeries, panes, annotations,
        logAxes, yAxisBases: config.yAxisBases || {}, yAxisRanges, invertedAxes, pctAxes,
        isLight: false, title: title.trim() || undefined,
        startDate: computedStartDate, endDate,
        showRecessions, hoverMode: hoverMode as any,
        showLegend, showGridlines, showZeroline,
      });
      if (built) cachedFigure = stripThemeFromFigure(built);
    }

    onSave({
      ...config, title: title.trim() || undefined, description: description.trim() || undefined,
      code: code.trim() || undefined, series: resolvedSeries, panes,
      annotations: annotations.length > 0 ? annotations : undefined,
      logAxes: logAxes.size > 0 ? Array.from(logAxes) : undefined,
      invertedAxes: invertedAxes.size > 0 ? Array.from(invertedAxes) : undefined,
      pctAxes: pctAxes.size > 0 ? Array.from(pctAxes) : undefined,
      yAxisRanges: Object.keys(yAxisRanges).length > 0 ? yAxisRanges : undefined,
      activeRange, startDate, endDate,
      showRecessions, hoverMode, showLegend, showGridlines, showZeroline,
      figure: cachedFigure,
      figureCachedAt: cachedFigure ? new Date().toISOString() : undefined,
    });
  }, [config, title, description, code, resolvedSeries, panes, annotations, logAxes, invertedAxes, pctAxes, yAxisRanges, activeRange, startDate, endDate, showRecessions, hoverMode, showLegend, showGridlines, showZeroline, onSave, rawData, visibleSeries, computedStartDate, isLight]);

  const fs = { colorScheme: isLight ? 'light' : 'dark', backgroundColor: 'rgb(var(--background))', color: 'rgb(var(--foreground))' } as const;

  const toolbarPresets = useMemo(
    () => RANGE_PRESETS.filter(p => ['1M', '3M', '6M', 'YTD', '1Y', '2Y', '5Y', '10Y', '20Y', '30Y', '50Y', 'MAX'].includes(p.label)),
    [],
  );

  // Unique axis keys from series
  const axisKeys = useMemo(() => {
    const keys = new Set<string>();
    resolvedSeries.forEach(s => keys.add(`${s.paneId ?? 0}-${s.yAxisIndex ?? 0}`));
    return Array.from(keys).sort();
  }, [resolvedSeries]);

  // -- RENDER --
  return (
    <div className="fixed inset-0 top-[48px] z-[90] bg-background flex flex-col items-center">
      <div className="w-full max-w-[1440px] flex flex-col flex-1 min-h-0">

      {/* COMMAND BAR */}
      <div className="shrink-0 h-9 flex items-center gap-0 px-1.5 border-b border-border/30 bg-background overflow-x-auto">
        {/* Back button */}
        <button onClick={onClose}
          className="h-[26px] px-2 flex items-center gap-1 rounded-[var(--radius)] text-muted-foreground/50 hover:text-foreground hover:bg-foreground/[0.04] transition-colors shrink-0 mr-1"
          title="Back to pack"
          aria-label="Back to pack">
          <ChevronDown className="w-3 h-3 rotate-90" />
          <span className="text-[10px] font-mono">Pack</span>
        </button>

        <div className="w-px h-5 bg-border/20 mx-0.5 shrink-0" />

        {/* Title */}
        <input type="text" value={title} onChange={e => setTitle(e.target.value)} placeholder="Chart title"
          className="min-w-[100px] max-w-[200px] w-auto h-[26px] px-2 text-[13px] font-semibold bg-transparent border border-transparent hover:border-border/30 focus:border-border/40 rounded-[var(--radius)] text-foreground focus:outline-none transition-colors" />

        <div className="w-px h-5 bg-border/20 mx-1 shrink-0 hidden sm:block" />

        {/* Date presets — hidden on very small screens */}
        <div className="hidden sm:flex items-center gap-0.5 shrink-0">
          {toolbarPresets.map(p => (
            <button key={p.label} onClick={() => handleRangePreset(p.label, p.months)}
              className={`h-[22px] px-1.5 rounded-[3px] text-[10px] font-mono shrink-0 transition-colors ${
                activeRange === p.label ? 'bg-foreground text-background' : 'text-muted-foreground/40 hover:text-foreground'
              }`}>{p.label}</button>
          ))}
        </div>

        {/* Date inputs — hidden on small screens */}
        <input type="date" value={startDate} onChange={e => { setStartDate(e.target.value); setActiveRange(''); }}
          className="hidden md:block h-[22px] w-[95px] px-1 text-[10px] font-mono border border-border/30 rounded-[3px] focus:outline-none focus:border-primary/40 shrink-0 ml-1" style={fs} />
        <span className="hidden md:block text-[10px] text-muted-foreground/30 mx-0.5 shrink-0">{'\u2014'}</span>
        <input type="date" value={endDate} onChange={e => { setEndDate(e.target.value); setActiveRange(''); }}
          className="hidden md:block h-[22px] w-[95px] px-1 text-[10px] font-mono border border-border/30 rounded-[3px] focus:outline-none focus:border-primary/40 shrink-0" style={fs} />

        <div className="flex-1 min-w-[8px]" />

        {/* Loading */}
        {(dataLoading || codeRunning) && <Loader2 className="w-3 h-3 animate-spin text-primary/40 shrink-0 mr-1" />}

        {/* Save + Close — always visible */}
        <button onClick={handleSave} className="h-[22px] px-2 flex items-center gap-1 rounded-[3px] bg-foreground text-background text-[9px] font-mono font-medium hover:opacity-90 transition-colors shrink-0"
          aria-label="Save chart">
          <Check className="w-2.5 h-2.5" /> Save
        </button>
        <button onClick={() => setRightSidebarOpen(p => !p)}
          className="w-7 h-7 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/30 hover:text-foreground hover:bg-foreground/[0.04] transition-colors shrink-0"
          title={rightSidebarOpen ? 'Hide panel' : 'Show panel'}
          aria-label={rightSidebarOpen ? 'Hide panel' : 'Show panel'}>
          {rightSidebarOpen ? <PanelRightClose className="w-3.5 h-3.5" /> : <PanelRightOpen className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* ═══ MAIN AREA ═══ */}
      <div className="flex-1 min-h-0 flex">

        {/* CENTER COLUMN */}
        <div className="flex-1 flex flex-col min-h-0 min-w-0">

          {/* Chart */}
          <div ref={plotContainerRef} className="flex-1 min-h-0 relative">
            {dataLoading ? (
              <div className="h-full flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-primary/30" /></div>
            ) : figure ? (
              <ChartErrorBoundary>
                <Plot data={figure.data} layout={{ ...figure.layout, autosize: true }}
                  config={{ responsive: true, displayModeBar: false, displaylogo: false, scrollZoom: true }}
                  style={{ width: '100%', height: '100%' }}
                  onInitialized={(_: any, gd: HTMLElement) => { plotGraphDivRef.current = gd; }}
                />
              </ChartErrorBoundary>
            ) : (
              <div className="h-full flex items-center justify-center">
                <div className="text-center">
                  <LineChart className="w-10 h-10 mx-auto text-muted-foreground/10 mb-3" />
                  <p className="text-[14px] text-foreground/30 font-medium">Write code to load data</p>
                  <p className="text-[11px] text-muted-foreground/20 mt-1">Write a Python expression below and press Run</p>
                </div>
              </div>
            )}
          </div>

          {/* Stats */}
          {showStats && stats.length > 0 && (
            <div className="shrink-0 border-t border-border/20 max-h-[100px] overflow-y-auto no-scrollbar text-[9px] font-mono">
              <div className="flex items-center gap-0 px-2 py-0.5 border-b border-border/20 bg-foreground/[0.02]">
                <span className="w-3 shrink-0" />
                <span className="flex-1 text-[8px] uppercase tracking-[0.1em] text-muted-foreground/40 font-semibold">{'\u2014'}</span>
                <span className="w-[50px] text-right text-[8px] text-muted-foreground/40 font-semibold shrink-0">Last</span>
                <span className="w-[42px] text-right text-[8px] text-muted-foreground/40 font-semibold shrink-0">{'\u0394'}%</span>
                <span className="w-[42px] text-right text-[8px] text-muted-foreground/40 font-semibold shrink-0">Lo</span>
                <span className="w-[42px] text-right text-[8px] text-muted-foreground/40 font-semibold shrink-0">Hi</span>
              </div>
              {stats.map((row, i) => (
                <div key={row.code} className={`flex items-center gap-0 px-2 py-0.5 border-b border-border/8 ${i % 2 === 1 ? 'bg-foreground/[0.01]' : ''}`}>
                  <span className="w-2 h-2 rounded-full shrink-0 mr-1" style={{ backgroundColor: row.color }} />
                  <span className="flex-1 min-w-0 text-foreground/60 truncate">{row.code}</span>
                  <span className="w-[50px] text-right tabular-nums text-foreground shrink-0">{fmtNum(row.last)}</span>
                  <span className={`w-[42px] text-right tabular-nums font-medium shrink-0 ${row.chgPct != null && row.chgPct >= 0 ? 'text-success' : 'text-destructive'}`}>
                    {row.chgPct != null ? (row.chgPct >= 0 ? '+' : '') + fmtNum(row.chgPct, 1) + '%' : '\u2014'}
                  </span>
                  <span className="w-[42px] text-right tabular-nums text-foreground/50 shrink-0">{fmtNum(row.min)}</span>
                  <span className="w-[42px] text-right tabular-nums text-foreground/50 shrink-0">{fmtNum(row.max)}</span>
                </div>
              ))}
            </div>
          )}

          {/* Code Editor — collapsible */}
          <div className="shrink-0 border-t border-border/30 flex flex-col">
            <div
              className="h-7 flex items-center px-2.5 border-b border-border/30 gap-2 bg-card select-none cursor-pointer"
              onClick={() => setCodeCollapsed(p => !p)}
            >
              <ChevronDown className={`w-3 h-3 text-muted-foreground/40 transition-transform duration-150 shrink-0 ${codeCollapsed ? '-rotate-90' : ''}`} />
              <span className="text-[10px] font-mono text-muted-foreground/50">Python</span>
              {codeError && <span className="text-[9px] font-mono text-destructive truncate flex-1 min-w-0" title={codeError}>{codeError}</span>}
              {!codeError && <span className="text-[9px] text-muted-foreground/20 flex-1 min-w-0">{'\u2303\u21B5'} Run</span>}
              <button onClick={(e) => { e.stopPropagation(); setShowStats(p => !p); }}
                className={`h-5 px-1.5 rounded-[3px] text-[8px] font-mono transition-colors ${showStats ? 'text-primary' : 'text-muted-foreground/25 hover:text-foreground'}`}>Stats</button>
              <button onClick={(e) => { e.stopPropagation(); runCode(); }} disabled={!code.trim() || codeRunning}
                className="h-5 px-2 rounded-[3px] text-[9px] font-medium bg-foreground text-background hover:opacity-90 transition-colors disabled:opacity-30 shrink-0 flex items-center gap-1 justify-center">
                {codeRunning ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />} Run
              </button>
            </div>
            {!codeCollapsed && (
              <>
                <div style={{ height: `${editorHeight}px` }}>
                  <MonacoEditor
                    height={`${editorHeight}px`}
                    language="python"
                    theme={isLight ? 'vs' : 'vs-dark'}
                    value={code}
                    onChange={(v) => { setCode(v || ''); setCodeError(null); }}
                    beforeMount={(monaco) => {
                      import('@/lib/monacoCompletions').then(({ registerIxCompletions }) => registerIxCompletions(monaco));
                    }}
                    onMount={(editor) => {
                      editor.addAction({ id: 'run-code', label: 'Run', keybindings: [2048 | 3], run: () => runCode() });
                    }}
                    options={{
                      minimap: { enabled: false }, lineNumbers: 'on', wordWrap: 'on',
                      scrollBeyondLastLine: false, overviewRulerLanes: 0, hideCursorInOverviewRuler: true,
                      renderLineHighlight: 'none', fontSize: 12, fontFamily: 'var(--font-mono), monospace',
                      padding: { top: 8, bottom: 8 }, scrollbar: { vertical: 'auto', horizontal: 'hidden' },
                      suggestOnTriggerCharacters: true, quickSuggestions: true,
                    }}
                  />
                </div>
                <div className="h-1 cursor-row-resize bg-border/20 hover:bg-primary/20 transition-colors"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    const startY = e.clientY, startH = editorHeight;
                    const onMove = (ev: MouseEvent) => setEditorHeight(Math.max(80, Math.min(500, startH + (ev.clientY - startY))));
                    const onUp = () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); };
                    document.addEventListener('mousemove', onMove); document.addEventListener('mouseup', onUp);
                  }} />
              </>
            )}
            {/* Description */}
            <div className="shrink-0 px-3 py-1 border-t border-border/[0.08]">
              <input type="text" value={description} onChange={e => setDescription(e.target.value)}
                placeholder="Description: what does this chart show?"
                className="w-full h-5 text-[9px] font-mono text-muted-foreground/50 bg-transparent border-0 focus:outline-none focus:text-foreground placeholder:text-muted-foreground/20 transition-colors" />
            </div>
          </div>
        </div>

        {/* RIGHT SIDEBAR — resizable + collapsible */}
        <div
          className="shrink-0 flex bg-card/20 transition-[width,opacity] duration-200 ease-in-out relative"
          style={{ width: rightSidebarOpen ? sidebarWidth : 0, opacity: rightSidebarOpen ? 1 : 0, overflow: 'hidden' }}
        >
          {/* Resize handle — left edge */}
          {rightSidebarOpen && (
            <div
              className="absolute left-0 top-0 bottom-0 w-1 cursor-col-resize z-10 hover:bg-primary/20 active:bg-primary/30 transition-colors"
              onMouseDown={(e) => {
                e.preventDefault();
                const startX = e.clientX, startW = sidebarWidth;
                const onMove = (ev: MouseEvent) => setSidebarWidth(Math.max(200, Math.min(500, startW - (ev.clientX - startX))));
                const onUp = () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); };
                document.addEventListener('mousemove', onMove); document.addEventListener('mouseup', onUp);
              }}
            />
          )}
          <div className="flex flex-col h-full overflow-hidden border-l border-border/30" style={{ width: sidebarWidth, minWidth: sidebarWidth }}>
            {/* Tabs */}
            <div className="shrink-0 h-8 border-b border-border/20 flex items-center px-0.5 gap-0">
              {(['series', 'annotate', 'settings'] as Tab[]).map(t => {
                const labels: Record<Tab, string> = { series: 'Series', annotate: 'Annotate', settings: 'Settings' };
                const badge = t === 'series' && resolvedSeries.length > 0 ? resolvedSeries.length : t === 'annotate' && annotations.length > 0 ? annotations.length : null;
                return (
                  <button key={t} onClick={() => setTab(t)}
                    className={`h-8 px-2 text-[9px] font-semibold uppercase tracking-[0.06em] transition-colors relative ${tab === t ? 'text-foreground' : 'text-muted-foreground/30 hover:text-foreground'}`}>
                    {labels[t]}
                    {badge != null && <span className="ml-0.5 text-primary/60">{badge}</span>}
                    {tab === t && <span className="absolute bottom-0 left-1.5 right-1.5 h-[2px] bg-foreground rounded-full" />}
                  </button>
                );
              })}
              <div className="flex-1" />
            </div>

            {/* Series tab */}
            {tab === 'series' && (
              <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
                <div className="flex-1 overflow-y-auto custom-scrollbar min-h-0">
                  {resolvedSeries.length === 0 ? (
                    <div className="px-3 py-8 text-center"><p className="text-[10px] text-muted-foreground/25">Run code to load series</p></div>
                  ) : (
                    <Reorder.Group axis="y" values={resolvedSeries} onReorder={(v) => setSeries(v as SelectedSeries[])} as="div">
                      {resolvedSeries.map((s, i) => (
                        <Reorder.Item key={s.code} value={s} as="div" dragListener>
                          <SeriesRowInline series={s} index={i} onUpdate={u => updateSeries(s.code, u)} panes={panes} />
                        </Reorder.Item>
                      ))}
                    </Reorder.Group>
                  )}
                </div>
                {/* Axis controls */}
                {axisKeys.length > 0 && (
                  <div className="shrink-0 border-t border-border/20 px-2 py-1.5 bg-foreground/[0.015]">
                    <span className="stat-label mb-1 block">Axes</span>
                    <div className="space-y-0.5">
                      {axisKeys.map(key => {
                        const [paneId, yAxisIndex] = key.split('-').map(Number);
                        const label = panes.length > 1 ? `P${paneId + 1}\u00B7Y${yAxisIndex + 1}` : `Y${yAxisIndex + 1}`;
                        const range = yAxisRanges[key] || {};
                        return (
                          <div key={key} className="flex items-center gap-0.5">
                            <span className="text-[8px] font-mono font-bold text-muted-foreground/50 w-6 shrink-0">{label}</span>
                            <button onClick={() => toggleLogAxis(key)}
                              className={`h-[18px] px-1 text-[8px] font-mono font-bold rounded-[3px] transition-colors shrink-0 ${logAxes.has(key) ? 'bg-foreground text-background' : 'text-muted-foreground/25 hover:text-foreground'}`}>LOG</button>
                            <button onClick={() => toggleInvertAxis(key)}
                              className={`h-[18px] px-1 text-[8px] font-mono font-bold rounded-[3px] transition-colors shrink-0 ${invertedAxes.has(key) ? 'bg-foreground text-background' : 'text-muted-foreground/25 hover:text-foreground'}`}>INV</button>
                            <button onClick={() => togglePctAxis(key)}
                              className={`h-[18px] w-5 text-[8px] font-mono font-bold rounded-[3px] transition-colors shrink-0 ${pctAxes.has(key) ? 'bg-foreground text-background' : 'text-muted-foreground/25 hover:text-foreground'}`}>%</button>
                            <input type="number" value={range.min ?? ''} onChange={e => setYAxisRange(key, 'min', e.target.value)}
                              className="w-[42px] h-[18px] px-1 text-[8px] font-mono text-center border border-border/25 rounded-[3px] bg-background text-foreground focus:outline-none focus:border-primary/40" placeholder="min" step="any" />
                            <input type="number" value={range.max ?? ''} onChange={e => setYAxisRange(key, 'max', e.target.value)}
                              className="w-[42px] h-[18px] px-1 text-[8px] font-mono text-center border border-border/25 rounded-[3px] bg-background text-foreground focus:outline-none focus:border-primary/40" placeholder="max" step="any" />
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
                {/* Pane controls */}
                {panes.length > 1 && (
                  <div className="shrink-0 border-t border-border/20 px-2 py-1 flex flex-wrap items-center gap-1 bg-foreground/[0.015]">
                    <span className="stat-label">Panes</span>
                    {panes.map(p => (
                      <div key={p.id} className="flex items-center gap-0.5 bg-card border border-border/30 rounded-[3px] pl-1.5 pr-0.5 h-[18px]">
                        <span className="text-[9px] font-mono text-muted-foreground/60">{p.label}</span>
                        <button onClick={() => setPanes(prev => prev.length <= 1 ? prev : prev.filter(x => x.id !== p.id))}
                          className="w-3.5 h-3.5 flex items-center justify-center text-muted-foreground/20 hover:text-destructive transition-colors">
                          <X className="w-2.5 h-2.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Format tab */}

            {/* Annotate tab */}
            {tab === 'annotate' && (
              <div className="flex-1 overflow-y-auto custom-scrollbar px-2 py-2">
                <div className="flex items-center justify-between mb-2">
                  <span className="stat-label">Add Annotation</span>
                  <div className="flex items-center gap-0.5">
                    <button onClick={() => addAnnotation('hline')} className="h-[20px] px-1.5 text-[9px] font-mono font-medium text-muted-foreground/40 hover:text-foreground hover:bg-foreground/[0.04] rounded-[3px] transition-colors">H-Line</button>
                    <button onClick={() => addAnnotation('vline')} className="h-[20px] px-1.5 text-[9px] font-mono font-medium text-muted-foreground/40 hover:text-foreground hover:bg-foreground/[0.04] rounded-[3px] transition-colors">V-Line</button>
                    <button onClick={() => addAnnotation('text')} className="h-[20px] px-1.5 text-[9px] font-mono font-medium text-muted-foreground/40 hover:text-foreground hover:bg-foreground/[0.04] rounded-[3px] transition-colors">Text</button>
                  </div>
                </div>
                <div className="space-y-1">
                  {annotations.map(a => (
                    <div key={a.id} className="flex items-center gap-1.5 py-1 px-1.5 rounded-[var(--radius)] bg-foreground/[0.015] border border-border/10 group/a">
                      <input type="color" value={a.color} onChange={e => updateAnnotation(a.id, { color: e.target.value })} className="w-4 h-4 rounded cursor-pointer border-0 p-0 shrink-0" />
                      <span className="text-[9px] font-mono text-muted-foreground/50 shrink-0 w-5">{a.type === 'hline' ? 'H' : a.type === 'vline' ? 'V' : 'T'}</span>
                      {a.type === 'hline' && <input type="number" value={a.y ?? 0} onChange={e => updateAnnotation(a.id, { y: parseFloat(e.target.value) || 0 })}
                        className="w-14 h-5 px-1 text-[10px] font-mono text-center border border-border/30 rounded-[3px] bg-background text-foreground focus:outline-none" step="any" />}
                      {a.type === 'vline' && <>
                        <input type="date" value={a.x || ''} onChange={e => updateAnnotation(a.id, { x: e.target.value })}
                          className="h-5 px-1 text-[9px] font-mono border border-border/30 rounded-[3px] bg-background text-foreground focus:outline-none flex-1 min-w-0" style={fs} />
                        <input type="text" value={a.text || ''} placeholder="Lbl" onChange={e => updateAnnotation(a.id, { text: e.target.value })}
                          className="w-10 h-5 px-1 text-[9px] font-mono border border-border/30 rounded-[3px] bg-background text-foreground focus:outline-none" />
                      </>}
                      {a.type === 'text' && <input type="text" value={a.text || ''} placeholder="Text" onChange={e => updateAnnotation(a.id, { text: e.target.value })}
                        className="flex-1 min-w-0 h-5 px-1 text-[9px] font-mono border border-border/30 rounded-[3px] bg-background text-foreground focus:outline-none" />}
                      <button onClick={() => removeAnnotation(a.id)}
                        className="w-4 h-4 flex items-center justify-center text-muted-foreground/15 hover:text-destructive opacity-0 group-hover/a:opacity-100 transition-all shrink-0">
                        <X className="w-2.5 h-2.5" />
                      </button>
                    </div>
                  ))}
                  {annotations.length === 0 && <p className="text-[10px] text-muted-foreground/25 py-3 text-center">No annotations yet</p>}
                </div>
              </div>
            )}

            {/* Settings tab */}
            {tab === 'settings' && (
              <div className="flex-1 overflow-y-auto custom-scrollbar px-2 py-2 space-y-3">
                {/* Recession shading */}
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-[9px] font-mono font-semibold text-muted-foreground/40 uppercase tracking-wider block">Recession Shading</span>
                    <span className="text-[8px] text-muted-foreground/25">NBER recession bands</span>
                  </div>
                  <button onClick={() => setShowRecessions(p => !p)}
                    className={`w-[22px] h-[22px] flex items-center justify-center rounded-[var(--radius)] transition-colors ${showRecessions ? 'bg-primary/15 text-primary' : 'text-muted-foreground/25 hover:text-foreground'}`}>
                    <div className={`w-2.5 h-2.5 rounded-full border-2 transition-colors ${showRecessions ? 'border-primary bg-primary' : 'border-muted-foreground/25'}`} />
                  </button>
                </div>

                {/* Hover mode */}
                <div>
                  <span className="text-[9px] font-mono font-semibold text-muted-foreground/40 uppercase tracking-wider block mb-1.5">Hover Mode</span>
                  <div className="flex items-center gap-0.5">
                    {([['x unified', 'X Unified'], ['closest', 'Closest'], ['x', 'X']] as const).map(([val, label]) => (
                      <button key={val} onClick={() => setHoverMode(val)}
                        className={`h-[22px] px-2 rounded-[3px] text-[9px] font-mono transition-colors ${
                          hoverMode === val ? 'bg-foreground text-background' : 'text-muted-foreground/35 hover:text-foreground'
                        }`}>{label}</button>
                    ))}
                  </div>
                </div>

                {/* Legend */}
                <div className="flex items-center justify-between">
                  <span className="text-[9px] font-mono font-semibold text-muted-foreground/40 uppercase tracking-wider">Legend</span>
                  <button onClick={() => setShowLegend(p => !p)}
                    className={`w-[22px] h-[22px] flex items-center justify-center rounded-[var(--radius)] transition-colors ${showLegend ? 'bg-primary/15 text-primary' : 'text-muted-foreground/25 hover:text-foreground'}`}>
                    <div className={`w-2.5 h-2.5 rounded-full border-2 transition-colors ${showLegend ? 'border-primary bg-primary' : 'border-muted-foreground/25'}`} />
                  </button>
                </div>

                {/* Gridlines */}
                <div className="flex items-center justify-between">
                  <span className="text-[9px] font-mono font-semibold text-muted-foreground/40 uppercase tracking-wider">Gridlines</span>
                  <button onClick={() => setShowGridlines(p => !p)}
                    className={`w-[22px] h-[22px] flex items-center justify-center rounded-[var(--radius)] transition-colors ${showGridlines ? 'bg-primary/15 text-primary' : 'text-muted-foreground/25 hover:text-foreground'}`}>
                    <div className={`w-2.5 h-2.5 rounded-full border-2 transition-colors ${showGridlines ? 'border-primary bg-primary' : 'border-muted-foreground/25'}`} />
                  </button>
                </div>

                {/* Zero line */}
                <div className="flex items-center justify-between">
                  <span className="text-[9px] font-mono font-semibold text-muted-foreground/40 uppercase tracking-wider">Zero Line</span>
                  <button onClick={() => setShowZeroline(p => !p)}
                    className={`w-[22px] h-[22px] flex items-center justify-center rounded-[var(--radius)] transition-colors ${showZeroline ? 'bg-primary/15 text-primary' : 'text-muted-foreground/25 hover:text-foreground'}`}>
                    <div className={`w-2.5 h-2.5 rounded-full border-2 transition-colors ${showZeroline ? 'border-primary bg-primary' : 'border-muted-foreground/25'}`} />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Status bar */}
      <div className="h-6 shrink-0 border-t border-border/20 flex items-center px-2.5 gap-3 bg-foreground/[0.015] text-[9px] font-mono text-muted-foreground/40 select-none">
        <span>{resolvedSeries.length > 0 ? `${resolvedSeries.length} series` : 'No series'}</span>
        <div className="w-px h-3 bg-border/20" />
        <span>{dataLoading || codeRunning ? 'Loading...' : 'Ready'}</span>
        <div className="flex-1" />
        <span className="text-muted-foreground/20">
          <kbd className="px-0.5">^{'\u21B5'}</kbd> Run
          {' '}
          <kbd className="px-0.5">Esc</kbd> Close
        </span>
      </div>
      </div>
    </div>
  );
}
