'use client';

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useSearchParams, useRouter } from 'next/navigation';
import AppShell from '@/components/AppShell';
import { ChartErrorBoundary } from '@/components/ChartErrorBoundary';
import { apiFetchJson } from '@/lib/api';
import { getApiCode, buildChartFigure } from '@/lib/buildChartFigure';
import { useTheme } from '@/context/ThemeContext';
import { useDebounce } from '@/lib/hooks/useDebounce';
import { useQuery } from '@tanstack/react-query';
import { Reorder } from 'framer-motion';
import {
  Search, LineChart, BarChart3, AreaChart, ScatterChart, Layers,
  Loader2, X, Plus, GripVertical,
  ChevronDown, ChevronRight, RotateCcw, AlertTriangle,
  Copy, Download, Save, FolderOpen, Trash2,
  Minus, Type, PanelTop, Table2, Terminal, MoreVertical, Play, GripHorizontal,
  Eye, EyeOff,
} from 'lucide-react';

// ─── Dynamic Imports ─────────────────────────────────────────────────────────

const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false });

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-3">
        <Loader2 className="w-6 h-6 animate-spin text-primary/40" />
        <span className="text-[11px] text-muted-foreground/50 tracking-widest uppercase">Loading Chart</span>
      </div>
    </div>
  ),
}) as any;

// ─── Types ───────────────────────────────────────────────────────────────────

interface TimeseriesMeta {
  id: string;
  code: string;
  name: string | null;
  category: string | null;
  asset_class: string | null;
  source: string | null;
  frequency: string | null;
  start: string | null;
  end: string | null;
  num_data: number | null;
  country: string | null;
}

type TransformType = 'none' | 'pctchg' | 'yoy' | 'ma' | 'zscore' | 'diff' | 'drawdown' | 'rebase' | 'log';
type LineStyle = 'solid' | 'dash' | 'dot' | 'dashdot';

interface SelectedSeries {
  code: string;
  name: string;
  chartType: ChartType;
  yAxis: 'left' | 'right'; // kept for workspace compat, ignored
  yAxisIndex?: number; // 0=Y1, 1=Y2, 2=Y3
  visible: boolean;
  color?: string;
  transform?: TransformType;
  transformParam?: number;
  lineStyle?: LineStyle;
  lineWidth?: number;
  paneId?: number;
}

type ChartType = 'line' | 'bar' | 'area' | 'scatter' | 'stackedbar' | 'stackedarea';

interface Pane {
  id: number;
  label: string;
}

interface Annotation {
  id: string;
  type: 'hline' | 'vline' | 'text';
  x?: string;
  y?: number;
  text?: string;
  color: string;
  paneId: number;
}

interface WorkspaceSummary {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

// ─── Constants ───────────────────────────────────────────────────────────────

const TRANSFORMS: { key: TransformType; label: string; hasParam?: boolean; defaultParam?: number }[] = [
  { key: 'none', label: 'None' },
  { key: 'pctchg', label: '%Chg', hasParam: true, defaultParam: 1 },
  { key: 'yoy', label: 'YoY%' },
  { key: 'ma', label: 'MA', hasParam: true, defaultParam: 20 },
  { key: 'zscore', label: 'Z-Score', hasParam: true, defaultParam: 252 },
  { key: 'diff', label: 'Diff', hasParam: true, defaultParam: 1 },
  { key: 'drawdown', label: 'Drawdown' },
  { key: 'rebase', label: 'Rebase' },
  { key: 'log', label: 'Log' },
];

const LINE_STYLES: { key: LineStyle; label: string }[] = [
  { key: 'solid', label: 'Solid' },
  { key: 'dash', label: 'Dash' },
  { key: 'dot', label: 'Dot' },
  { key: 'dashdot', label: 'DashDot' },
];

const LINE_WIDTHS = [1, 1.5, 2.5];

const COLORWAY = [
  '#00D2FF', '#FF69B4', '#A020F0', '#00FF66', '#FFB84D',
  '#ef4444', '#3b82f6', '#f59e0b', '#8b5cf6', '#06b6d4',
];

const CHART_TYPES: { key: ChartType; label: string; icon: React.ReactNode }[] = [
  { key: 'line', label: 'Line', icon: <LineChart className="w-3.5 h-3.5" /> },
  { key: 'bar', label: 'Bar', icon: <BarChart3 className="w-3.5 h-3.5" /> },
  { key: 'area', label: 'Area', icon: <AreaChart className="w-3.5 h-3.5" /> },
  { key: 'scatter', label: 'Scatter', icon: <ScatterChart className="w-3.5 h-3.5" /> },
  { key: 'stackedbar', label: 'Stacked Bar', icon: <Layers className="w-3.5 h-3.5" /> },
  { key: 'stackedarea', label: 'Stacked Area', icon: <Layers className="w-3.5 h-3.5" /> },
];

const RANGE_PRESETS = [
  { label: '1M', months: 1 },
  { label: '3M', months: 3 },
  { label: '6M', months: 6 },
  { label: 'YTD', months: -1 },
  { label: '1Y', months: 12 },
  { label: '3Y', months: 36 },
  { label: '5Y', months: 60 },
  { label: 'MAX', months: 0 },
];

// ─── Helpers ─────────────────────────────────────────────────────────────────

function getPresetStartDate(months: number): string {
  if (months === 0) return '';
  const now = new Date();
  if (months === -1) return `${now.getFullYear()}-01-01`;
  const d = new Date(now);
  d.setMonth(d.getMonth() - months);
  return d.toISOString().slice(0, 10);
}



function fmtNum(v: number | null | undefined, decimals = 2): string {
  if (v == null || !isFinite(v)) return '\u2014';
  return v.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function generateExpressionLabel(expr: string): string {
  const seriesMatch = expr.match(/Series\(["']([^"']+)["']\)/);
  if (seriesMatch) {
    let label = seriesMatch[1];
    const transforms: string[] = [];
    const rollingMatch = expr.match(/\.rolling\((\d+)\)\.(\w+)\(\)/);
    if (rollingMatch) transforms.push(`rolling ${rollingMatch[1]} ${rollingMatch[2]}`);
    const pctMatch = expr.match(/\.pct_change\((\d+)?\)/);
    if (pctMatch) transforms.push(`pct_change${pctMatch[1] ? ` ${pctMatch[1]}` : ''}`);
    const resampleMatch = expr.match(/\.resample\(["'](\w+)["']\)\.(\w+)\(\)/);
    if (resampleMatch) transforms.push(`${resampleMatch[2]} ${resampleMatch[1]}`);
    const wrapperMatch = expr.match(/^(\w+)\(Series/);
    if (wrapperMatch && wrapperMatch[1] !== 'Series') transforms.unshift(wrapperMatch[1]);
    if (transforms.length > 0) label += ` (${transforms.join(', ')})`;
    return label.length > 40 ? label.slice(0, 37) + '...' : label;
  }
  return expr.length > 40 ? expr.slice(0, 37) + '...' : expr;
}

// ─── Color Picker Popover ────────────────────────────────────────────────────

function ColorPicker({ color, onChange }: { color: string; onChange: (c: string) => void }) {
  const [open, setOpen] = useState(false);
  const [hex, setHex] = useState(color);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => { setHex(color); }, [color]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="w-3 h-3 rounded-full shrink-0 cursor-pointer ring-1 ring-border/20 hover:ring-border/50 transition-all"
        style={{ backgroundColor: color }}
        title="Change color"
      />
      {open && (
        <div className="absolute left-0 top-full mt-1 p-2 bg-card border border-border/50 rounded-[var(--radius)] shadow-lg z-50 w-[140px]">
          <div className="grid grid-cols-5 gap-1.5 mb-2">
            {COLORWAY.map((c) => (
              <button
                key={c}
                onClick={() => { onChange(c); setOpen(false); }}
                className={`w-5 h-5 rounded-full transition-all ${
                  color === c ? 'ring-2 ring-foreground ring-offset-1 ring-offset-card' : 'hover:ring-1 hover:ring-border/50'
                }`}
                style={{ backgroundColor: c }}
              />
            ))}
          </div>
          <input
            type="text"
            value={hex}
            onChange={(e) => setHex(e.target.value)}
            onBlur={() => {
              if (/^#[0-9a-fA-F]{6}$/.test(hex)) { onChange(hex); setOpen(false); }
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && /^#[0-9a-fA-F]{6}$/.test(hex)) { onChange(hex); setOpen(false); }
            }}
            className="w-full px-1.5 py-1 text-[10px] font-mono border border-border/50 rounded-[var(--radius)] bg-background text-foreground focus:outline-none focus:border-primary/40"
            placeholder="#FF0000"
          />
        </div>
      )}
    </div>
  );
}

// ─── Dropdown Button (reusable) ──────────────────────────────────────────────

function DropdownButton({
  label,
  children,
  active,
}: {
  label: React.ReactNode;
  children: React.ReactNode;
  active?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className={`flex items-center gap-0.5 h-[22px] px-1.5 rounded-[var(--radius)] border text-[10px] font-mono transition-colors ${
          active
            ? 'border-primary/30 text-primary'
            : 'border-border/30 text-muted-foreground hover:text-foreground hover:border-border/50'
        }`}
      >
        {label}
        <ChevronDown className="w-2.5 h-2.5" />
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 bg-card border border-border/50 rounded-[var(--radius)] shadow-lg z-50 py-0.5 min-w-[90px]">
          {typeof children === 'function'
            ? (children as any)(() => setOpen(false))
            : children}
        </div>
      )}
    </div>
  );
}

// ─── Series Row (right panel — single horizontal line) ──────────────────────

function SeriesRow({
  series,
  index,
  onRemove,
  onUpdate,
  hasError,
  panes,
  isLogAxis,
  onToggleLog,
  isInvertedAxis,
  onToggleInvert,
  isPctAxis,
  onTogglePct,
  yAxisBase,
  onSetYAxisBase,
  yAxisRange,
  onSetYAxisRange,
}: {
  series: SelectedSeries;
  index: number;
  onRemove: () => void;
  onUpdate: (updates: Partial<SelectedSeries>) => void;
  hasError?: boolean;
  panes: Pane[];
  isLogAxis: boolean;
  onToggleLog: () => void;
  isInvertedAxis: boolean;
  onToggleInvert: () => void;
  isPctAxis: boolean;
  onTogglePct: () => void;
  yAxisBase: number;
  onSetYAxisBase: (base: number) => void;
  yAxisRange: { min?: number; max?: number };
  onSetYAxisRange: (range: { min?: number; max?: number }) => void;
}) {
  const color = series.color || COLORWAY[index % COLORWAY.length];
  const isExpression = series.code.includes('(');
  const currentTransform = TRANSFORMS.find((t) => t.key === (series.transform || 'none'));

  const [editingName, setEditingName] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [menuOpen]);

  // Summaries for non-default settings shown as badges
  const hasNonDefaultStyle = (series.lineStyle && series.lineStyle !== 'solid') || (series.lineWidth != null && series.lineWidth !== 1.5);
  const hasNonDefaultAxis = (series.yAxisIndex ?? 0) > 0;
  const hasTransform = series.transform && series.transform !== 'none';

  return (
    <div className={`border-b border-border/15 group hover:bg-primary/[0.02] transition-colors ${series.visible === false ? 'opacity-40' : ''}`}>
      <div className="flex items-center gap-1 px-1.5 py-1">
        <button
          onClick={() => onUpdate({ visible: series.visible === false ? true : false })}
          className="w-4 h-4 flex items-center justify-center text-muted-foreground/30 hover:text-foreground transition-colors shrink-0"
          title={series.visible === false ? 'Show series' : 'Hide series'}
        >
          {series.visible === false ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
        </button>
        <GripVertical className="w-3 h-3 text-muted-foreground/20 shrink-0 cursor-grab" />
        <ColorPicker color={color} onChange={(c) => onUpdate({ color: c })} />

        {/* Name */}
        {editingName ? (
          <input
            autoFocus
            defaultValue={series.name}
            onBlur={(e) => { onUpdate({ name: e.target.value || series.code }); setEditingName(false); }}
            onKeyDown={(e) => { if (e.key === 'Enter') { onUpdate({ name: (e.target as HTMLInputElement).value || series.code }); setEditingName(false); } if (e.key === 'Escape') setEditingName(false); }}
            className="w-[70px] min-w-0 text-[10px] font-mono text-foreground bg-transparent border-b border-primary/40 focus:outline-none px-0 py-0"
          />
        ) : (
          <span
            className="text-[10px] font-mono font-medium text-foreground truncate cursor-text max-w-[70px] flex-1 min-w-0"
            title={`${series.name}${series.name !== series.code ? ` (${series.code})` : ''} — double-click to rename`}
            onDoubleClick={() => setEditingName(true)}
          >
            {hasError && <AlertTriangle className="w-2.5 h-2.5 text-warning inline mr-0.5" />}
            {series.name}
          </span>
        )}

        {/* Chart type cycle — still inline, shows icon */}
        <button
          onClick={() => {
            const keys = CHART_TYPES.map((t) => t.key);
            const next = keys[(keys.indexOf(series.chartType) + 1) % keys.length];
            onUpdate({ chartType: next });
          }}
          className="h-[18px] px-0.5 rounded-[2px] text-muted-foreground/40 hover:text-foreground transition-colors shrink-0"
          title={`Chart: ${CHART_TYPES.find((t) => t.key === series.chartType)?.label || series.chartType}`}
        >
          {CHART_TYPES.find((t) => t.key === series.chartType)?.icon}
        </button>

        {/* Y-axis cycle (inline) */}
        <button
          onClick={() => onUpdate({ yAxisIndex: ((series.yAxisIndex ?? 0) + 1) % 3 })}
          className={`h-[18px] px-1 rounded-[2px] text-[8px] font-mono font-bold transition-colors shrink-0 ${
            (series.yAxisIndex ?? 0) > 0 ? 'text-primary bg-primary/10' : 'text-muted-foreground/30 hover:text-foreground'
          }`}
          title={`Y-axis: Y${(series.yAxisIndex ?? 0) + 1}`}
        >
          Y{(series.yAxisIndex ?? 0) + 1}
        </button>

        {/* Compact badges for non-default settings */}
        {isLogAxis && (
          <span className="text-[8px] font-mono font-bold text-primary bg-primary/10 px-1 h-[16px] leading-[16px] rounded-[2px] shrink-0">log</span>
        )}
        {isInvertedAxis && (
          <span className="text-[8px] font-mono font-bold text-primary bg-primary/10 px-1 h-[16px] leading-[16px] rounded-[2px] shrink-0">inv</span>
        )}
        {isPctAxis && (
          <span className="text-[8px] font-mono font-bold text-primary bg-primary/10 px-1 h-[16px] leading-[16px] rounded-[2px] shrink-0">%</span>
        )}
        {hasTransform && (
          <span className="text-[8px] font-mono text-primary px-1 h-[16px] leading-[16px] rounded-[2px] shrink-0">
            {currentTransform?.label}
          </span>
        )}
        {(yAxisRange.min != null || yAxisRange.max != null) && (
          <span className="text-[8px] font-mono font-bold text-primary bg-primary/10 px-1 h-[16px] leading-[16px] rounded-[2px] shrink-0" title={`Y range: ${yAxisRange.min ?? 'auto'} – ${yAxisRange.max ?? 'auto'}`}>rng</span>
        )}

        {/* Overflow dropdown — all settings */}
        <div className="relative shrink-0 ml-auto" ref={menuRef}>
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="w-5 h-[18px] flex items-center justify-center text-muted-foreground/25 hover:text-foreground transition-colors rounded-[2px] hover:bg-primary/[0.06]"
          >
            <MoreVertical className="w-3 h-3" />
          </button>
          {menuOpen && (
            <div className="absolute right-0 top-full mt-1 bg-card border border-border/50 rounded-[var(--radius)] shadow-lg z-50 py-0.5 min-w-[130px] max-h-[320px] overflow-y-auto no-scrollbar">
              {/* Chart type */}
              <div className="px-2 pt-1 pb-0.5">
                <span className="text-[8px] font-mono uppercase tracking-[0.1em] text-muted-foreground/30">Type</span>
              </div>
              {CHART_TYPES.map((t) => (
                <button
                  key={t.key}
                  onClick={() => { onUpdate({ chartType: t.key }); setMenuOpen(false); }}
                  className={`w-full text-left px-2.5 py-1 text-[10px] font-mono hover:bg-primary/[0.06] transition-colors flex items-center gap-1.5 ${
                    series.chartType === t.key ? 'text-primary' : 'text-muted-foreground'
                  }`}
                >
                  {t.icon} {t.label}
                </button>
              ))}

              {/* Line style */}
              <div className="border-t border-border/20 my-0.5" />
              <div className="px-2 pt-1 pb-0.5">
                <span className="text-[8px] font-mono uppercase tracking-[0.1em] text-muted-foreground/30">Style</span>
              </div>
              {LINE_STYLES.map((st) => (
                <button
                  key={st.key}
                  onClick={() => { onUpdate({ lineStyle: st.key }); setMenuOpen(false); }}
                  className={`w-full text-left px-2.5 py-1 text-[10px] font-mono hover:bg-primary/[0.06] transition-colors ${
                    (series.lineStyle || 'solid') === st.key ? 'text-primary' : 'text-muted-foreground'
                  }`}
                >
                  {st.label}
                </button>
              ))}

              {/* Line width */}
              <div className="border-t border-border/20 my-0.5" />
              <div className="px-2 pt-1 pb-0.5">
                <span className="text-[8px] font-mono uppercase tracking-[0.1em] text-muted-foreground/30">Width</span>
              </div>
              <div className="flex items-center gap-1 px-2.5 py-1">
                {LINE_WIDTHS.map((w) => (
                  <button
                    key={w}
                    onClick={() => { onUpdate({ lineWidth: w }); }}
                    className={`h-5 px-1.5 text-[9px] font-mono rounded-[2px] transition-colors ${
                      (series.lineWidth ?? 1.5) === w ? 'text-primary bg-primary/10' : 'text-muted-foreground/40 hover:text-foreground'
                    }`}
                  >
                    {w}
                  </button>
                ))}
              </div>

              {/* Y-axis */}
              <div className="border-t border-border/20 my-0.5" />
              <div className="px-2 pt-1 pb-0.5">
                <span className="text-[8px] font-mono uppercase tracking-[0.1em] text-muted-foreground/30">Y-Axis</span>
              </div>
              <div className="flex items-center gap-1 px-2.5 py-1">
                {[0, 1, 2].map((yi) => (
                  <button
                    key={yi}
                    onClick={() => { onUpdate({ yAxisIndex: yi }); }}
                    className={`h-5 px-1.5 text-[9px] font-mono font-bold rounded-[2px] transition-colors ${
                      (series.yAxisIndex ?? 0) === yi ? 'text-primary bg-primary/10' : 'text-muted-foreground/40 hover:text-foreground'
                    }`}
                  >
                    Y{yi + 1}
                  </button>
                ))}
              </div>

              {/* Log */}
              <button
                onClick={() => { onToggleLog(); setMenuOpen(false); }}
                className={`w-full text-left px-2.5 py-1 text-[10px] font-mono hover:bg-primary/[0.06] transition-colors ${
                  isLogAxis ? 'text-primary' : 'text-muted-foreground'
                }`}
              >
                Log scale {isLogAxis ? '✓' : ''}
              </button>

              {/* Invert Y-axis */}
              <button
                onClick={() => { onToggleInvert(); setMenuOpen(false); }}
                className={`w-full text-left px-2.5 py-1 text-[10px] font-mono hover:bg-primary/[0.06] transition-colors ${
                  isInvertedAxis ? 'text-primary' : 'text-muted-foreground'
                }`}
              >
                Invert {isInvertedAxis ? '✓' : ''}
              </button>

              {/* Percent format */}
              <button
                onClick={() => { onTogglePct(); setMenuOpen(false); }}
                className={`w-full text-left px-2.5 py-1 text-[10px] font-mono hover:bg-primary/[0.06] transition-colors ${
                  isPctAxis ? 'text-primary' : 'text-muted-foreground'
                }`}
              >
                Percent % {isPctAxis ? '✓' : ''}
              </button>

              {/* Y-axis range */}
              <div className="border-t border-border/20 my-0.5" />
              <div className="px-2 pt-1 pb-0.5">
                <span className="text-[8px] font-mono uppercase tracking-[0.1em] text-muted-foreground/30">Y-Axis Range</span>
              </div>
              <div className="px-2.5 py-1 flex items-center gap-1">
                <input
                  type="number"
                  value={yAxisRange.min ?? ''}
                  onChange={(e) => {
                    const v = e.target.value;
                    onSetYAxisRange({ ...yAxisRange, min: v === '' ? undefined : parseFloat(v) });
                  }}
                  className="w-1/2 h-5 px-1 text-[10px] font-mono text-center border border-border/25 rounded-[2px] bg-background text-foreground focus:outline-none"
                  onClick={(e) => e.stopPropagation()}
                  placeholder="Min"
                  step="any"
                />
                <input
                  type="number"
                  value={yAxisRange.max ?? ''}
                  onChange={(e) => {
                    const v = e.target.value;
                    onSetYAxisRange({ ...yAxisRange, max: v === '' ? undefined : parseFloat(v) });
                  }}
                  className="w-1/2 h-5 px-1 text-[10px] font-mono text-center border border-border/25 rounded-[2px] bg-background text-foreground focus:outline-none"
                  onClick={(e) => e.stopPropagation()}
                  placeholder="Max"
                  step="any"
                />
              </div>

              {/* Transforms */}
              <div className="border-t border-border/20 my-0.5" />
              <div className="px-2 pt-1 pb-0.5">
                <span className="text-[8px] font-mono uppercase tracking-[0.1em] text-muted-foreground/30">Transform</span>
              </div>
              {TRANSFORMS.map((t) => (
                <button
                  key={t.key}
                  onClick={() => { onUpdate({ transform: t.key, transformParam: t.defaultParam }); setMenuOpen(false); }}
                  className={`w-full text-left px-2.5 py-1 text-[10px] font-mono hover:bg-primary/[0.06] transition-colors ${
                    (series.transform || 'none') === t.key ? 'text-primary' : 'text-muted-foreground'
                  }`}
                >
                  {t.label}
                </button>
              ))}
              {currentTransform?.hasParam && series.transform && series.transform !== 'none' && (
                <div className="px-2.5 py-1 border-t border-border/20">
                  <input
                    type="number"
                    value={series.transformParam ?? currentTransform.defaultParam ?? ''}
                    onChange={(e) => onUpdate({ transformParam: parseInt(e.target.value) || undefined })}
                    className="w-full h-5 px-1 text-[10px] font-mono text-center border border-border/25 rounded-[2px] bg-background text-foreground focus:outline-none"
                    onClick={(e) => e.stopPropagation()}
                  />
                </div>
              )}

              {/* Pane assignment */}
              {panes.length > 1 && (
                <>
                  <div className="border-t border-border/20 my-0.5" />
                  <div className="px-2 pt-1 pb-0.5">
                    <span className="text-[8px] font-mono uppercase tracking-[0.1em] text-muted-foreground/30">Pane</span>
                  </div>
                  {panes.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => { onUpdate({ paneId: p.id }); setMenuOpen(false); }}
                      className={`w-full text-left px-2.5 py-1 text-[10px] font-mono hover:bg-primary/[0.06] transition-colors ${
                        (series.paneId ?? 0) === p.id ? 'text-primary' : 'text-muted-foreground'
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                </>
              )}
            </div>
          )}
        </div>

        {/* Remove */}
        <button
          onClick={onRemove}
          className="w-4 h-4 flex items-center justify-center text-muted-foreground/15 hover:text-destructive transition-colors opacity-0 group-hover:opacity-100 shrink-0"
        >
          <X className="w-2.5 h-2.5" />
        </button>
      </div>
    </div>
  );
}

// ─── Statistics Panel ────────────────────────────────────────────────────────

function StatsPanel({
  rawData,
  visibleSeries,
  selectedSeries,
}: {
  rawData: Record<string, (string | number | null)[]>;
  visibleSeries: SelectedSeries[];
  selectedSeries: SelectedSeries[];
}) {
  const stats = useMemo(() => {
    if (!rawData?.Date) return [];
    return visibleSeries.map((s) => {
      const apiCode = getApiCode(s);
      let values = ((rawData[apiCode] || []) as (number | null)[]);
      if (s.transform === 'log') {
        values = values.map((v) => (v != null && v > 0 ? Math.log(v) : null));
      }
      const nums = values.filter((v): v is number => v != null);
      const color = s.color || COLORWAY[selectedSeries.indexOf(s) % COLORWAY.length];
      if (nums.length === 0) return { code: s.code, color, last: null, chg: null, chgPct: null, min: null, max: null, mean: null, std: null };
      const last = nums[nums.length - 1];
      const prev = nums.length > 1 ? nums[nums.length - 2] : null;
      const chg = prev != null ? last - prev : null;
      const chgPct = prev != null && prev !== 0 ? ((last - prev) / prev) * 100 : null;
      const min = Math.min(...nums);
      const max = Math.max(...nums);
      const mean = nums.reduce((a, b) => a + b, 0) / nums.length;
      const std = Math.sqrt(nums.reduce((a, b) => a + (b - mean) ** 2, 0) / nums.length);
      return { code: s.code, color, last, chg, chgPct, min, max, mean, std };
    });
  }, [rawData, visibleSeries, selectedSeries]);

  if (stats.length === 0) return null;

  return (
    <div className="text-[10px] font-mono">
      {stats.map((row) => (
        <div key={row.code} className="flex items-center gap-1.5 px-2 py-1 border-b border-border/10">
          <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: row.color }} />
          <span className="text-foreground truncate flex-1 min-w-0">{row.code}</span>
          <span className="text-foreground tabular-nums">{fmtNum(row.last)}</span>
          <span className={`tabular-nums ${row.chgPct != null && row.chgPct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {row.chgPct != null ? (row.chgPct >= 0 ? '+' : '') + fmtNum(row.chgPct, 1) + '%' : '\u2014'}
          </span>
        </div>
      ))}
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

function ChartsPageInner() {
  useEffect(() => {
    document.title = 'Charts | Investment-X';
  }, []);

  const { theme } = useTheme();
  const isLight = theme === 'light';
  const searchParams = useSearchParams();
  const router = useRouter();

  // ── Pack context from URL params ──
  const addToPackId = searchParams.get('addToPack') || null;
  const [packEditCtx, setPackEditCtx] = useState<{ packId: string; chartIndex: number } | null>(null);

  // ── Search state ──
  const [searchQuery, setSearchQuery] = useState('');
  const [searchFocused, setSearchFocused] = useState(false);
  const debouncedSearch = useDebounce(searchQuery, 300);
  const searchRef = useRef<HTMLDivElement>(null);

  const { data: searchResults, isLoading: searchLoading } = useQuery({
    queryKey: ['timeseries-search', debouncedSearch],
    queryFn: () => {
      const params = new URLSearchParams({ search: debouncedSearch, limit: '30' });
      return apiFetchJson<TimeseriesMeta[]>(`/api/timeseries?${params}`);
    },
    enabled: debouncedSearch.length >= 1,
    staleTime: 60_000,
  });

  // ── Code editor state ──
  const CODE_TEMPLATE = `result = MultiSeries(**{\n  "SPY": Series("SPY US EQUITY:PX_LAST"),\n  "QQQ": Series("QQQ US EQUITY:PX_LAST"),\n})`;
  const [expressionMode, setExpressionMode] = useState(false);
  const [expression, setExpression] = useState(() => {
    if (typeof window === 'undefined') return CODE_TEMPLATE;
    return localStorage.getItem('ix-chart-code') || CODE_TEMPLATE;
  });
  const [codeRunning, setCodeRunning] = useState(false);
  const [codeError, setCodeError] = useState('');
  // Data returned from code exec — keyed by column name, merged with API data
  const [codeData, setCodeData] = useState<Record<string, (string | number | null)[]> | null>(null);
  const [editorHeight, setEditorHeight] = useState(160);

  // ── Series state ──
  const [selectedSeries, setSelectedSeries] = useState<SelectedSeries[]>([]);
  const [activeRange, setActiveRange] = useState('MAX');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // ── Chart state ──
  const [chartTitle, setChartTitle] = useState('');
  const [showStats, setShowStats] = useState(false);
  const [copyState, setCopyState] = useState<'idle' | 'done'>('idle');

  // ── Pane state ──
  const [panes, setPanes] = useState<Pane[]>([{ id: 0, label: 'Pane 1' }]);
  // Log scale per y-axis: Set of "paneId-yAxisIndex" keys
  const [logAxes, setLogAxes] = useState<Set<string>>(new Set());
  const toggleLogAxis = useCallback((paneId: number, yAxisIndex: number) => {
    const key = `${paneId}-${yAxisIndex}`;
    setLogAxes((prev) => { const next = new Set(prev); if (next.has(key)) next.delete(key); else next.add(key); return next; });
  }, []);
  // Y-axis base per axis: Record of "paneId-yAxisIndex" → base value (default 0 = tozero)
  const [yAxisBases, setYAxisBases] = useState<Record<string, number>>({});
  const setYAxisBase = useCallback((paneId: number, yAxisIndex: number, base: number) => {
    const key = `${paneId}-${yAxisIndex}`;
    setYAxisBases((prev) => ({ ...prev, [key]: base }));
  }, []);
  // Manual Y-axis ranges: Record of "paneId-yAxisIndex" → {min?, max?}
  const [yAxisRanges, setYAxisRanges] = useState<Record<string, { min?: number; max?: number }>>({});
  const setYAxisRange = useCallback((paneId: number, yAxisIndex: number, range: { min?: number; max?: number }) => {
    const key = `${paneId}-${yAxisIndex}`;
    setYAxisRanges((prev) => {
      // Remove entry if both min and max are undefined
      if (range.min == null && range.max == null) {
        const next = { ...prev };
        delete next[key];
        return next;
      }
      return { ...prev, [key]: range };
    });
  }, []);
  // Inverted Y-axes: Set of "paneId-yAxisIndex" keys
  const [invertedAxes, setInvertedAxes] = useState<Set<string>>(new Set());
  const toggleInvertAxis = useCallback((paneId: number, yAxisIndex: number) => {
    const key = `${paneId}-${yAxisIndex}`;
    setInvertedAxes((prev) => { const next = new Set(prev); if (next.has(key)) next.delete(key); else next.add(key); return next; });
  }, []);
  // Percentage-format Y-axes: Set of "paneId-yAxisIndex" keys
  const [pctAxes, setPctAxes] = useState<Set<string>>(new Set());
  const togglePctAxis = useCallback((paneId: number, yAxisIndex: number) => {
    const key = `${paneId}-${yAxisIndex}`;
    setPctAxes((prev) => { const next = new Set(prev); if (next.has(key)) next.delete(key); else next.add(key); return next; });
  }, []);
  // NBER recession shading
  const [showRecessions, setShowRecessions] = useState(false);
  // Rebase all series
  const [allRebased, setAllRebased] = useState(false);
  // Crosshair / hover mode
  const [hoverMode, setHoverMode] = useState<'x unified' | 'closest' | 'x'>('x unified');

  // ── Annotation state ──
  const [annotations, setAnnotations] = useState<Annotation[]>([]);

  // ── Workspace state ──
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([]);
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [workspaceName, setWorkspaceName] = useState('');
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(null);
  const [actionsMenuOpen, setActionsMenuOpen] = useState(false);
  const actionsMenuRef = useRef<HTMLDivElement>(null);

  // ── Pack state ──
  const [saveToPackOpen, setSaveToPackOpen] = useState(false);
  const [savingToPack, setSavingToPack] = useState(false);

  // ── Right panel sections ──
  const [showAnnotations, setShowAnnotations] = useState(false);

  // ── Load chart from pack edit context ──
  const hasLoadedPackEdit = useRef(false);
  useEffect(() => {
    if (hasLoadedPackEdit.current) return;
    if (searchParams.get('editPack') !== '1') return;
    const raw = sessionStorage.getItem('ix-edit-pack');
    if (!raw) return;
    hasLoadedPackEdit.current = true;
    try {
      const ctx = JSON.parse(raw);
      setPackEditCtx({ packId: ctx.packId, chartIndex: ctx.chartIndex });
      const c = ctx.chart;
      if (c.series) setSelectedSeries(c.series);
      if (c.panes) setPanes(c.panes);
      if (c.annotations) setAnnotations(c.annotations);
      if (c.logAxes) setLogAxes(new Set(c.logAxes));
      if (c.yAxisBases) setYAxisBases(c.yAxisBases);
      if (c.yAxisRanges) setYAxisRanges(c.yAxisRanges);
      if (c.invertedAxes) setInvertedAxes(new Set(c.invertedAxes));
      if (c.pctAxes) setPctAxes(new Set(c.pctAxes));
      if (c.showRecessions !== undefined) setShowRecessions(c.showRecessions);
      if (c.hoverMode !== undefined) setHoverMode(c.hoverMode);
      if (c.activeRange !== undefined) setActiveRange(c.activeRange);
      if (c.startDate !== undefined) setStartDate(c.startDate);
      if (c.endDate !== undefined) setEndDate(c.endDate);
      if (c.title !== undefined) setChartTitle(c.title);
      if (c.code) {
        setExpression(c.code);
        setExpressionMode(true);
        // Auto-run the code
        setTimeout(() => runCode(c.code), 100);
      } else {
        // Clear stale code state so it doesn't contaminate this series-based chart
        localStorage.removeItem('ix-chart-code');
        setCodeData(null);
        setExpression(CODE_TEMPLATE);
        setExpressionMode(false);
      }
    } catch {}
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  // Close menus on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (searchFocused && searchRef.current && !searchRef.current.contains(e.target as Node)) setSearchFocused(false);
      if (actionsMenuOpen && actionsMenuRef.current && !actionsMenuRef.current.contains(e.target as Node)) setActionsMenuOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [searchFocused, actionsMenuOpen]);

  const selectedCodes = useMemo(
    () => new Set(selectedSeries.map((s) => s.code)),
    [selectedSeries],
  );

  const addSeries = useCallback(
    (code: string, name: string) => {
      setSelectedSeries((prev) => {
        if (prev.some((s) => s.code === code)) return prev;
        return [...prev, { code, name, chartType: 'line', yAxis: 'left', yAxisIndex: 0, visible: true, transform: 'none' }];
      });
      setSearchQuery('');
      setSearchFocused(false);
    },
    [],
  );

  const runCode = useCallback(async (codeOverride?: string) => {
    const trimmed = (codeOverride ?? expression).trim();
    if (!trimmed) return;
    if (!trimmed.includes('result')) {
      setCodeError('Code must assign a DataFrame to "result"');
      return;
    }
    setCodeError('');
    setCodeRunning(true);

    try {
      const resp = await apiFetchJson<Record<string, any>>('/api/timeseries.exec', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: trimmed }),
      });
      const columns: string[] = resp.__columns__ || Object.keys(resp).filter((k) => k !== 'Date' && k !== '__columns__');
      if (columns.length === 0) {
        setCodeError('Code returned no columns');
        return;
      }
      // Store the returned data directly — these columns don't exist in DB
      const data: Record<string, (string | number | null)[]> = { Date: resp.Date };
      for (const col of columns) data[col] = resp[col];
      setCodeData(data);

      // Sync series list to match dataframe columns — preserve settings for
      // columns that still exist, add new ones, drop stale ones
      const colSet = new Set(columns);
      setSelectedSeries((prev) => {
        const prevByCode = new Map(prev.map((s) => [s.code, s]));
        return columns.map((col) => {
          const existing = prevByCode.get(col);
          if (existing) return existing; // keep user-customized settings
          return {
            code: col,
            name: col,
            chartType: 'line' as ChartType,
            yAxis: 'left' as const,
            yAxisIndex: 0,
            visible: true,
            transform: 'none' as TransformType,
          };
        });
      });
      // Persist code so it auto-runs on refresh
      localStorage.setItem('ix-chart-code', trimmed);
      setExpressionMode(false);
    } catch (err: any) {
      setCodeError(err?.message || err?.body?.detail || 'Execution failed');
    } finally {
      setCodeRunning(false);
    }
  }, [expression]);

  // Auto-run saved code on mount (skip when in pack context to avoid stale code)
  const hasAutoRun = useRef(false);
  useEffect(() => {
    if (hasAutoRun.current) return;
    if (searchParams.get('editPack') || searchParams.get('addToPack')) return;
    const saved = typeof window !== 'undefined' ? localStorage.getItem('ix-chart-code') : null;
    if (saved && saved.trim() && saved.includes('result')) {
      hasAutoRun.current = true;
      runCode(saved);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const removeSeries = useCallback((code: string) => {
    setSelectedSeries((prev) => prev.filter((s) => s.code !== code));
  }, []);

  const updateSeries = useCallback((code: string, updates: Partial<SelectedSeries>) => {
    setSelectedSeries((prev) =>
      prev.map((s) => (s.code === code ? { ...s, ...updates } : s)),
    );
  }, []);

  const clearAll = useCallback(() => {
    setSelectedSeries([]);
    setActiveRange('MAX');
    setStartDate('');
    setEndDate('');
    setShowStats(false);
    setPanes([{ id: 0, label: 'Pane 1' }]);
    setAnnotations([]);
    setLogAxes(new Set());
    setYAxisBases({});
    setYAxisRanges({});
    setInvertedAxes(new Set());
    setPctAxes(new Set());
    setShowRecessions(false);
    setAllRebased(false);
    setHoverMode('x unified');
    setCodeData(null);
    setExpression(CODE_TEMPLATE);
    localStorage.removeItem('ix-chart-code');
    setActiveWorkspaceId(null);
  }, []);

  // ── Pane management ──
  const addPane = useCallback(() => {
    setPanes((prev) => {
      const nextId = Math.max(...prev.map((p) => p.id)) + 1;
      return [...prev, { id: nextId, label: `Pane ${nextId + 1}` }];
    });
  }, []);

  const removePane = useCallback((paneId: number) => {
    setPanes((prev) => {
      if (prev.length <= 1) return prev;
      const filtered = prev.filter((p) => p.id !== paneId);
      setSelectedSeries((ss) =>
        ss.map((s) => (s.paneId === paneId ? { ...s, paneId: filtered[0].id } : s)),
      );
      setAnnotations((a) => a.filter((ann) => ann.paneId !== paneId));
      return filtered;
    });
  }, []);

  // ── Annotation management ──
  const addAnnotation = useCallback((type: Annotation['type']) => {
    const id = `ann-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    const base: Annotation = { id, type, color: '#ef4444', paneId: 0 };
    if (type === 'hline') base.y = 0;
    if (type === 'vline') base.x = new Date().toISOString().slice(0, 10);
    if (type === 'text') { base.x = new Date().toISOString().slice(0, 10); base.y = 0; base.text = 'Note'; }
    setAnnotations((prev) => [...prev, base]);
    setShowAnnotations(true);
  }, []);

  const updateAnnotation = useCallback((id: string, updates: Partial<Annotation>) => {
    setAnnotations((prev) => prev.map((a) => (a.id === id ? { ...a, ...updates } : a)));
  }, []);

  const removeAnnotation = useCallback((id: string) => {
    setAnnotations((prev) => prev.filter((a) => a.id !== id));
  }, []);

  // ── Workspace save/load ──
  const fetchWorkspaces = useCallback(async () => {
    try {
      const data = await apiFetchJson<WorkspaceSummary[]>('/api/chart-workspaces');
      setWorkspaces(data);
    } catch { /* user not logged in or API unavailable */ }
  }, []);

  const saveWorkspace = useCallback(async (name: string) => {
    const config = {
      series: selectedSeries, panes, annotations, logAxes: Array.from(logAxes), yAxisBases, yAxisRanges,
      invertedAxes: Array.from(invertedAxes), pctAxes: Array.from(pctAxes),
      showRecessions, hoverMode,
      activeRange, startDate, endDate, chartTitle, showStats,
    };
    try {
      if (activeWorkspaceId) {
        await apiFetchJson(`/api/chart-workspaces/${activeWorkspaceId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, config }),
        });
      } else {
        const resp = await apiFetchJson<{ id: string }>('/api/chart-workspaces', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, config }),
        });
        setActiveWorkspaceId(resp.id);
      }
      setSaveModalOpen(false);
      fetchWorkspaces();
    } catch { /* silently fail */ }
  }, [selectedSeries, panes, annotations, logAxes, yAxisBases, yAxisRanges, invertedAxes, pctAxes, showRecessions, hoverMode, activeRange, startDate, endDate, chartTitle, showStats, activeWorkspaceId, fetchWorkspaces]);

  const loadWorkspaceById = useCallback(async (id: string) => {
    try {
      const detail = await apiFetchJson<{ config: any; name: string }>(`/api/chart-workspaces/${id}`);
      const c = detail.config;
      if (c.series) setSelectedSeries(c.series);
      if (c.panes) setPanes(c.panes);
      if (c.annotations) setAnnotations(c.annotations);
      if (c.logAxes) setLogAxes(new Set(c.logAxes));
      if (c.yAxisBases) setYAxisBases(c.yAxisBases);
      if (c.yAxisRanges) setYAxisRanges(c.yAxisRanges);
      if (c.invertedAxes) setInvertedAxes(new Set(c.invertedAxes));
      if (c.pctAxes) setPctAxes(new Set(c.pctAxes));
      if (c.showRecessions !== undefined) setShowRecessions(c.showRecessions);
      if (c.hoverMode !== undefined) setHoverMode(c.hoverMode);
      if (c.activeRange !== undefined) setActiveRange(c.activeRange);
      if (c.startDate !== undefined) setStartDate(c.startDate);
      if (c.endDate !== undefined) setEndDate(c.endDate);
      if (c.chartTitle !== undefined) setChartTitle(c.chartTitle);
      if (c.showStats !== undefined) setShowStats(c.showStats);
      setActiveWorkspaceId(id);
      setWorkspaceName(detail.name);
      setActionsMenuOpen(false);
    } catch { /* silently fail */ }
  }, []);

  const deleteWorkspace = useCallback(async (id: string) => {
    try {
      await apiFetchJson(`/api/chart-workspaces/${id}`, { method: 'DELETE' });
      if (activeWorkspaceId === id) setActiveWorkspaceId(null);
      fetchWorkspaces();
    } catch { /* silently fail */ }
  }, [activeWorkspaceId, fetchWorkspaces]);

  useEffect(() => { fetchWorkspaces(); }, [fetchWorkspaces]);

  // ── Pack helpers ──
  const { data: packList = [], isLoading: packsLoading } = useQuery({
    queryKey: ['chart-packs'],
    queryFn: () => apiFetchJson<{ id: string; name: string }[]>('/api/chart-packs'),
    enabled: saveToPackOpen,
    staleTime: 10_000,
  });

  const buildChartConfig = useCallback((): Record<string, any> => {
    const chart: Record<string, any> = {
      title: chartTitle, series: selectedSeries, panes, annotations,
      logAxes: Array.from(logAxes), yAxisBases, yAxisRanges,
      invertedAxes: Array.from(invertedAxes), pctAxes: Array.from(pctAxes),
      showRecessions, hoverMode,
      activeRange, startDate, endDate,
    };
    if (codeData && expression?.trim()) chart.code = expression.trim();
    return chart;
  }, [chartTitle, selectedSeries, panes, annotations, logAxes, yAxisBases, yAxisRanges, invertedAxes, pctAxes, showRecessions, hoverMode, activeRange, startDate, endDate, codeData, expression]);

  const saveChartToPack = useCallback(async (packId: string) => {
    setSavingToPack(true);
    try {
      await apiFetchJson(`/api/chart-packs/${packId}/charts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chart: buildChartConfig() }),
      });
      setSaveToPackOpen(false);
    } catch { /* silently fail */ }
    setSavingToPack(false);
  }, [buildChartConfig]);

  const updatePackChart = useCallback(async () => {
    if (!packEditCtx) return;
    setSavingToPack(true);
    try {
      const pack = await apiFetchJson<{ charts: any[] }>(`/api/chart-packs/${packEditCtx.packId}`);
      const charts = [...pack.charts];
      charts[packEditCtx.chartIndex] = buildChartConfig();
      await apiFetchJson(`/api/chart-packs/${packEditCtx.packId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ charts }),
      });
      sessionStorage.removeItem('ix-edit-pack');
      const pid = packEditCtx.packId;
      setPackEditCtx(null);
      router.push(`/chartpack?chartpack=${pid}`);
    } catch {}
    setSavingToPack(false);
  }, [packEditCtx, buildChartConfig, router]);

  const addChartToPack = useCallback(async () => {
    if (!addToPackId || selectedSeries.length === 0) return;
    setSavingToPack(true);
    try {
      await apiFetchJson(`/api/chart-packs/${addToPackId}/charts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chart: buildChartConfig() }),
      });
      router.push(`/chartpack?chartpack=${addToPackId}`);
    } catch {}
    setSavingToPack(false);
  }, [addToPackId, selectedSeries.length, buildChartConfig, router]);

  // ── Data fetching ──
  const visibleSeries = useMemo(
    () => selectedSeries.filter((s) => s.visible !== false),
    [selectedSeries],
  );

  // Only fetch codes NOT already provided by codeData
  const codeDataKeys = useMemo(() => new Set(codeData ? Object.keys(codeData).filter((k) => k !== 'Date') : []), [codeData]);

  const codesParam = useMemo(
    () => selectedSeries.map((s) => getApiCode(s)).filter((c) => !codeDataKeys.has(c)),
    [selectedSeries, codeDataKeys],
  );

  const debouncedCodes = useDebounce(codesParam, 300);

  const { data: apiData, isLoading, isFetching } = useQuery({
    queryKey: ['chart-data', debouncedCodes],
    queryFn: async () => {
      const url = '/api/timeseries.custom';
      const body = { codes: debouncedCodes };
      return apiFetchJson<Record<string, (string | number | null)[]>>(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
    },
    enabled: debouncedCodes.length > 0,
    staleTime: 120_000,
  });

  // Merge API data + code data into a single rawData object
  const rawData = useMemo(() => {
    if (!apiData && !codeData) return undefined;
    if (!apiData) return codeData ?? undefined;
    if (!codeData) return apiData;
    // Merge: use codeData dates as base if no API data dates, else API dates
    const merged: Record<string, (string | number | null)[]> = { ...apiData };
    // If API returned no Date but codeData has, use codeData's
    if ((!merged.Date || merged.Date.length === 0) && codeData.Date) {
      merged.Date = codeData.Date;
    }
    // Copy code columns into merged (they use codeData's date axis)
    for (const [key, vals] of Object.entries(codeData)) {
      if (key !== 'Date' && !merged[key]) merged[key] = vals;
    }
    return merged;
  }, [apiData, codeData]);

  const failedCodes = useMemo(() => {
    if (!rawData) return new Set<string>();
    const responseKeys = new Set(Object.keys(rawData));
    return new Set(selectedSeries.filter((s) => !responseKeys.has(getApiCode(s))).map((s) => s.code));
  }, [rawData, selectedSeries]);

  // ── Build Plotly figure ──
  const figure = useMemo(() => {
    if (!rawData) return null;
    return buildChartFigure({
      rawData,
      series: visibleSeries,
      allSeries: selectedSeries,
      panes,
      annotations,
      logAxes,
      yAxisBases,
      yAxisRanges,
      invertedAxes,
      pctAxes,
      isLight,
      title: chartTitle,
      startDate,
      endDate,
      showRecessions,
      hoverMode,
    });
  }, [rawData, visibleSeries, selectedSeries, isLight, chartTitle, panes, annotations, logAxes, yAxisBases, yAxisRanges, invertedAxes, pctAxes, startDate, endDate, showRecessions, hoverMode]);

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

  const handleRangePreset = useCallback((label: string, months: number) => {
    setActiveRange(label);
    setStartDate(getPresetStartDate(months));
    setEndDate('');
  }, []);

  const handleCopyPng = useCallback(async () => {
    const gd = plotGraphDivRef.current;
    if (!gd) return;
    try {
      const Plotly = (await import('plotly.js-dist-min')).default;
      const url = await (Plotly as any).toImage(gd, { format: 'png', width: 1200, height: 800, scale: 2 });
      const res = await fetch(url);
      const blob = await res.blob();
      await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
      setCopyState('done');
      setTimeout(() => setCopyState('idle'), 1500);
    } catch {}
  }, []);

  const handleDownloadCsv = useCallback(() => {
    if (!rawData?.Date) return;
    const dates = rawData.Date as string[];
    const cols = visibleSeries.map((s) => ({
      header: s.code + (s.transform && s.transform !== 'none' ? ` (${s.transform})` : ''),
      apiCode: getApiCode(s), transform: s.transform,
    }));
    const headers = ['Date', ...cols.map((c) => c.header)];
    const rows = dates.map((d, i) => {
      const vals = cols.map((c) => {
        let v = (rawData[c.apiCode] as (number | null)[])?.[i];
        if (c.transform === 'log' && v != null && v > 0) v = Math.log(v);
        return v ?? '';
      });
      return [d, ...vals].join(',');
    });
    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chart_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [rawData, visibleSeries]);

  const formStyle = {
    colorScheme: isLight ? 'light' as const : 'dark' as const,
    backgroundColor: 'rgb(var(--background))',
    color: 'rgb(var(--foreground))',
  };

  const hasRightPanel = selectedSeries.length > 0;

  // ── Render ──
  return (
    <AppShell hideFooter>
      <div className="h-[calc(100vh-48px)] flex flex-col bg-background">

        {/* ═══════════════════ TOP TOOLBAR ═══════════════════ */}
        <div className="shrink-0 h-9 border-b border-border/30 flex items-center px-2 gap-1">

          {/* Code editor toggle */}
          <button
            onClick={() => { if (!expressionMode && !expression.trim()) setExpression(CODE_TEMPLATE); setExpressionMode(!expressionMode); }}
            className={`w-[26px] h-[26px] flex items-center justify-center rounded-[var(--radius)] shrink-0 transition-colors ${
              expressionMode ? 'bg-primary/15 text-primary' : 'text-muted-foreground/30 hover:text-foreground hover:bg-primary/[0.06]'
            }`}
            title="Code editor"
          >
            <Terminal className="w-3.5 h-3.5" />
          </button>

          {/* ── Scrollable middle section ── */}
          <div className="flex-1 flex items-center gap-1 overflow-x-auto no-scrollbar min-w-0">
            <div className="w-px h-4 bg-border/20 mx-0.5 shrink-0" />

            {/* ── Date Range Presets ── */}
            {RANGE_PRESETS.map((p) => (
              <button
                key={p.label}
                onClick={() => handleRangePreset(p.label, p.months)}
                className={`h-[26px] px-1.5 rounded-[var(--radius)] text-[10px] font-mono font-medium shrink-0 transition-colors ${
                  activeRange === p.label
                    ? 'bg-primary/15 text-primary'
                    : 'text-muted-foreground/40 hover:text-foreground hover:bg-primary/[0.06]'
                }`}
              >
                {p.label}
              </button>
            ))}
            <input
              type="date"
              value={startDate}
              onChange={(e) => { setStartDate(e.target.value); setActiveRange(''); }}
              className="h-[26px] w-[105px] px-1 text-[10px] font-mono border border-border/30 rounded-[var(--radius)] focus:outline-none focus:border-primary/40 shrink-0"
              style={formStyle}
              title="Start"
            />
            <input
              type="date"
              value={endDate}
              onChange={(e) => { setEndDate(e.target.value); setActiveRange(''); }}
              className="h-[26px] w-[105px] px-1 text-[10px] font-mono border border-border/30 rounded-[var(--radius)] focus:outline-none focus:border-primary/40 shrink-0"
              style={formStyle}
              title="End"
            />
            <div className="w-px h-4 bg-border/20 mx-0.5 shrink-0" />

            {/* Recession shading toggle */}
            <button
              onClick={() => setShowRecessions(!showRecessions)}
              className={`h-[26px] px-1.5 rounded-[var(--radius)] text-[10px] font-mono font-medium shrink-0 transition-colors ${
                showRecessions
                  ? 'bg-primary/15 text-primary'
                  : 'text-muted-foreground/40 hover:text-foreground hover:bg-primary/[0.06]'
              }`}
              title="NBER recession shading"
            >
              REC
            </button>

            {/* Rebase/Index all toggle */}
            <button
              onClick={() => {
                const next = !allRebased;
                setAllRebased(next);
                setSelectedSeries((prev) => prev.map((s) => ({ ...s, transform: next ? 'rebase' : 'none' })));
              }}
              className={`h-[26px] px-1.5 rounded-[var(--radius)] text-[10px] font-mono font-medium shrink-0 transition-colors ${
                allRebased
                  ? 'bg-primary/15 text-primary'
                  : 'text-muted-foreground/40 hover:text-foreground hover:bg-primary/[0.06]'
              }`}
              title="Rebase / index all series to 100"
            >
              IDX
            </button>

            {/* Hover mode cycle */}
            <button
              onClick={() => {
                const modes: ('x unified' | 'closest' | 'x')[] = ['x unified', 'closest', 'x'];
                const next = modes[(modes.indexOf(hoverMode) + 1) % modes.length];
                setHoverMode(next);
              }}
              className={`h-[26px] px-1.5 rounded-[var(--radius)] text-[10px] font-mono font-medium shrink-0 transition-colors ${
                hoverMode !== 'x unified'
                  ? 'bg-primary/15 text-primary'
                  : 'text-muted-foreground/40 hover:text-foreground hover:bg-primary/[0.06]'
              }`}
              title={`Crosshair mode: ${hoverMode}`}
            >
              {hoverMode === 'x unified' ? 'UNI' : hoverMode === 'closest' ? 'CLO' : 'X'}
            </button>

          </div>

          {/* ── Right: actions ── */}
          {packEditCtx && (
            <button
              onClick={updatePackChart}
              disabled={savingToPack}
              className="w-[26px] h-[26px] flex items-center justify-center rounded-[var(--radius)] bg-foreground text-background hover:opacity-90 transition-colors disabled:opacity-30 shrink-0"
              title="Update in Pack"
            >
              {savingToPack ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
            </button>
          )}
          {addToPackId && !packEditCtx && (
            <button
              onClick={addChartToPack}
              disabled={savingToPack || selectedSeries.length === 0}
              className="w-[26px] h-[26px] flex items-center justify-center rounded-[var(--radius)] bg-foreground text-background hover:opacity-90 transition-colors disabled:opacity-30 shrink-0"
              title="Add to Pack"
            >
              {savingToPack ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
            </button>
          )}
          <Link
            href="/chartpack"
            className="w-[26px] h-[26px] flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/40 hover:text-foreground hover:bg-primary/[0.06] transition-colors shrink-0"
            title="Packs"
          >
            <FolderOpen className="w-3 h-3" />
          </Link>
          {isFetching && <Loader2 className="w-3 h-3 animate-spin text-primary/40 shrink-0" />}

          {/* Actions dropdown */}
          <div className="relative shrink-0" ref={actionsMenuRef}>
            <button
              onClick={() => { setActionsMenuOpen(!actionsMenuOpen); if (!actionsMenuOpen) fetchWorkspaces(); }}
              className="w-[26px] h-[26px] flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/30 hover:text-foreground hover:bg-primary/[0.06] transition-colors"
              title="Actions"
            >
              <MoreVertical className="w-3.5 h-3.5" />
            </button>
            {actionsMenuOpen && (
              <div className="absolute right-0 top-full mt-1 bg-card border border-border/50 rounded-[var(--radius)] shadow-lg z-50 py-0.5 min-w-[180px]">
                <button
                  onClick={() => { handleCopyPng(); setActionsMenuOpen(false); }}
                  className="w-full flex items-center gap-2.5 px-3 py-1.5 text-[11px] text-muted-foreground hover:text-foreground hover:bg-primary/[0.06] transition-colors"
                >
                  <Copy className="w-3.5 h-3.5" /> Copy PNG
                </button>
                <button
                  onClick={() => { handleDownloadCsv(); setActionsMenuOpen(false); }}
                  className="w-full flex items-center gap-2.5 px-3 py-1.5 text-[11px] text-muted-foreground hover:text-foreground hover:bg-primary/[0.06] transition-colors"
                >
                  <Download className="w-3.5 h-3.5" /> Download CSV
                </button>
                <div className="border-t border-border/20 my-0.5" />
                <button
                  onClick={() => { setWorkspaceName(chartTitle || ''); setSaveModalOpen(true); setActionsMenuOpen(false); }}
                  className="w-full flex items-center gap-2.5 px-3 py-1.5 text-[11px] text-muted-foreground hover:text-foreground hover:bg-primary/[0.06] transition-colors"
                >
                  <Save className="w-3.5 h-3.5" /> Save workspace
                </button>
                {selectedSeries.length > 0 && (
                  <button
                    onClick={() => { setSaveToPackOpen(true); setActionsMenuOpen(false); }}
                    className="w-full flex items-center gap-2.5 px-3 py-1.5 text-[11px] text-muted-foreground hover:text-foreground hover:bg-primary/[0.06] transition-colors"
                  >
                    <FolderOpen className="w-3.5 h-3.5" /> Save to Pack
                  </button>
                )}

                {/* Load workspace submenu */}
                {workspaces.length > 0 && (
                  <>
                    <div className="border-t border-border/20 my-0.5" />
                    <div className="px-3 py-1 text-[9px] font-bold uppercase tracking-widest text-muted-foreground/30">Workspaces</div>
                    {workspaces.map((ws) => (
                      <div key={ws.id} className="flex items-center gap-1 px-3 py-1 hover:bg-primary/[0.06] transition-colors group/ws">
                        <button
                          onClick={() => { loadWorkspaceById(ws.id); setActionsMenuOpen(false); }}
                          className="flex-1 text-left text-[11px] font-mono text-muted-foreground hover:text-foreground truncate"
                        >
                          {ws.name}
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); deleteWorkspace(ws.id); }}
                          className="w-4 h-4 flex items-center justify-center text-muted-foreground/20 hover:text-destructive opacity-0 group-hover/ws:opacity-100 transition-all"
                        >
                          <Trash2 className="w-2.5 h-2.5" />
                        </button>
                      </div>
                    ))}
                  </>
                )}

                {selectedSeries.length > 0 && (
                  <>
                    <div className="border-t border-border/20 my-0.5" />
                    <button
                      onClick={() => { clearAll(); setActionsMenuOpen(false); }}
                      className="w-full flex items-center gap-2.5 px-3 py-1.5 text-[11px] text-destructive hover:bg-destructive/[0.06] transition-colors"
                    >
                      <RotateCcw className="w-3.5 h-3.5" /> Clear all
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ═══════════════════ CODE EDITOR ═══════════════════ */}
        {expressionMode && (
          <div className="shrink-0 border-b border-border/30 flex flex-col bg-card/30">
            {/* Editor toolbar */}
            <div className="h-7 flex items-center px-2.5 border-b border-border/20 gap-2">
              <Terminal className="w-3 h-3 text-muted-foreground/30" />
              <span className="text-[10px] font-mono font-medium text-muted-foreground/40 uppercase tracking-wider">Code</span>

              {codeError && (
                <span className="text-[9px] font-mono text-destructive truncate flex-1 min-w-0 ml-2" title={codeError}>{codeError}</span>
              )}
              {!codeError && (
                <span className="text-[9px] text-muted-foreground/20 flex-1 min-w-0 ml-2">
                  Ctrl+Enter to run
                </span>
              )}

              <button
                onClick={() => runCode()}
                disabled={!expression.trim() || codeRunning}
                className="h-[22px] px-2.5 rounded-[var(--radius)] text-[10px] font-medium bg-foreground text-background hover:opacity-90 transition-colors disabled:opacity-30 shrink-0 flex items-center gap-1.5 justify-center"
              >
                {codeRunning ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                Run
              </button>
              <button
                onClick={() => setExpressionMode(false)}
                className="w-5 h-5 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/25 hover:text-foreground hover:bg-primary/[0.06] transition-colors shrink-0"
                title="Close editor"
              >
                <X className="w-3 h-3" />
              </button>
            </div>

            {/* Monaco editor */}
            <div style={{ height: `${editorHeight}px` }}>
              <MonacoEditor
                height={`${editorHeight}px`}
                language="python"
                theme={isLight ? 'vs' : 'vs-dark'}
                value={expression}
                onChange={(v) => { setExpression(v || ''); setCodeError(''); }}
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

            {/* Resize handle */}
            <div
              className="h-[6px] cursor-row-resize flex items-center justify-center hover:bg-primary/[0.06] transition-colors group/resize"
              onMouseDown={(e) => {
                e.preventDefault();
                const startY = e.clientY;
                const startH = editorHeight;
                const onMove = (ev: MouseEvent) => {
                  const delta = ev.clientY - startY;
                  setEditorHeight(Math.max(80, Math.min(500, startH + delta)));
                };
                const onUp = () => {
                  document.removeEventListener('mousemove', onMove);
                  document.removeEventListener('mouseup', onUp);
                };
                document.addEventListener('mousemove', onMove);
                document.addEventListener('mouseup', onUp);
              }}
            >
              <GripHorizontal className="w-4 h-2.5 text-muted-foreground/15 group-hover/resize:text-muted-foreground/40 transition-colors" />
            </div>
          </div>
        )}

        {/* ═══════════════════ MAIN AREA ═══════════════════ */}
        <div className="flex-1 flex min-h-0">

          {/* ── Chart Column ── */}
          <div className="flex-1 flex flex-col min-h-0 min-w-0">
            {/* Chart */}
            <div ref={plotContainerRef} className="flex-1 min-h-0 relative">
              {selectedSeries.length === 0 ? (
                <div className="h-full flex items-center justify-center">
                  <div className="text-center">
                    <LineChart className="w-10 h-10 mx-auto text-muted-foreground/10 mb-3" />
                    <p className="text-[13px] font-medium text-muted-foreground/40">Add time series to chart</p>
                    <p className="text-[11px] text-muted-foreground/25 mt-1">Search to add series, or click <Terminal className="w-3 h-3 inline" /> to write code</p>
                  </div>
                </div>
              ) : isLoading ? (
                <div className="h-full flex items-center justify-center">
                  <Loader2 className="w-6 h-6 animate-spin text-primary/30" />
                </div>
              ) : figure ? (
                <ChartErrorBoundary>
                  <Plot
                    data={figure.data}
                    layout={figure.layout}
                    config={{
                      responsive: true, displayModeBar: 'hover' as const, displaylogo: false, scrollZoom: true,
                      modeBarButtonsToRemove: ['select2d', 'lasso2d', 'sendDataToCloud'],
                    }}
                    style={{ width: '100%', height: '100%' }}
                    onInitialized={(_: any, gd: HTMLElement) => { plotGraphDivRef.current = gd; }}
                  />
                </ChartErrorBoundary>
              ) : null}
            </div>
          </div>

          {/* ── Right Panel: Series & Controls ── */}
          {hasRightPanel && (
            <div className="w-[260px] shrink-0 border-l border-border/30 flex flex-col bg-card/20 overflow-hidden">
              {/* Chart title */}
              <div className="shrink-0 px-2 py-1.5 border-b border-border/20">
                <input
                  type="text"
                  value={chartTitle}
                  onChange={(e) => setChartTitle(e.target.value)}
                  placeholder="Chart title..."
                  className="w-full h-[24px] px-1.5 text-[11px] font-medium border border-border/30 rounded-[var(--radius)] focus:outline-none focus:border-primary/40 text-foreground placeholder:text-muted-foreground/20 bg-transparent"
                  style={formStyle}
                />
              </div>

              {/* Series header */}
              <div className="shrink-0 px-2 py-1 border-b border-border/20 flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">
                  Series
                  <span className="ml-1.5 text-muted-foreground/25 normal-case tracking-normal">{selectedSeries.length}</span>
                </span>
                <div className="flex items-center gap-0.5">
                  <button
                    onClick={() => setShowStats(!showStats)}
                    className={`w-5 h-5 flex items-center justify-center rounded-[2px] transition-colors ${
                      showStats ? 'text-primary' : 'text-muted-foreground/25 hover:text-foreground'
                    }`}
                    title="Show stats"
                  >
                    <Table2 className="w-3 h-3" />
                  </button>
                  <button
                    onClick={addPane}
                    className="w-5 h-5 flex items-center justify-center rounded-[2px] text-muted-foreground/25 hover:text-foreground transition-colors"
                    title="Add pane"
                  >
                    <PanelTop className="w-3 h-3" />
                  </button>
                  <button
                    onClick={() => setShowAnnotations(!showAnnotations)}
                    className={`w-5 h-5 flex items-center justify-center rounded-[2px] transition-colors ${
                      showAnnotations ? 'text-primary' : 'text-muted-foreground/25 hover:text-foreground'
                    }`}
                    title="Annotations"
                  >
                    <Type className="w-3 h-3" />
                  </button>
                </div>
              </div>

              {/* Stats (compact, in panel) */}
              {showStats && rawData && (
                <div className="shrink-0 border-b border-border/20">
                  <StatsPanel rawData={rawData} visibleSeries={visibleSeries} selectedSeries={selectedSeries} />
                </div>
              )}

              {/* Series list with drag reorder */}
              <div className="flex-1 overflow-y-auto custom-scrollbar">
                <Reorder.Group axis="y" values={selectedSeries} onReorder={setSelectedSeries} as="div">
                  {selectedSeries.map((s, i) => (
                    <Reorder.Item key={s.code} value={s} as="div" dragListener>
                      <SeriesRow
                        series={s}
                        index={i}
                        onRemove={() => removeSeries(s.code)}
                        onUpdate={(updates) => updateSeries(s.code, updates)}
                        hasError={failedCodes.has(s.code)}
                        panes={panes}
                        isLogAxis={logAxes.has(`${s.paneId ?? 0}-${s.yAxisIndex ?? 0}`)}
                        onToggleLog={() => toggleLogAxis(s.paneId ?? 0, s.yAxisIndex ?? 0)}
                        isInvertedAxis={invertedAxes.has(`${s.paneId ?? 0}-${s.yAxisIndex ?? 0}`)}
                        onToggleInvert={() => toggleInvertAxis(s.paneId ?? 0, s.yAxisIndex ?? 0)}
                        isPctAxis={pctAxes.has(`${s.paneId ?? 0}-${s.yAxisIndex ?? 0}`)}
                        onTogglePct={() => togglePctAxis(s.paneId ?? 0, s.yAxisIndex ?? 0)}
                        yAxisBase={yAxisBases[`${s.paneId ?? 0}-${s.yAxisIndex ?? 0}`] ?? 0}
                        onSetYAxisBase={(base) => setYAxisBase(s.paneId ?? 0, s.yAxisIndex ?? 0, base)}
                        yAxisRange={yAxisRanges[`${s.paneId ?? 0}-${s.yAxisIndex ?? 0}`] ?? {}}
                        onSetYAxisRange={(range) => setYAxisRange(s.paneId ?? 0, s.yAxisIndex ?? 0, range)}
                      />
                    </Reorder.Item>
                  ))}
                </Reorder.Group>
              </div>

              {/* Y-Axis controls — one row per active axis */}
              {(() => {
                const axisKeys = new Set<string>();
                selectedSeries.forEach((s) => axisKeys.add(`${s.paneId ?? 0}-${s.yAxisIndex ?? 0}`));
                const sorted = Array.from(axisKeys).sort();
                if (sorted.length === 0) return null;
                return (
                  <div className="shrink-0 border-t border-border/20 px-2 py-1.5">
                    <span className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/30 mb-1 block">Y-Axis</span>
                    {sorted.map((key) => {
                      const [paneId, yAxisIndex] = key.split('-').map(Number);
                      const isLog = logAxes.has(key);
                      const isInv = invertedAxes.has(key);
                      const isPct = pctAxes.has(key);
                      const range = yAxisRanges[key] || {};
                      const label = panes.length > 1 ? `P${paneId + 1}·Y${yAxisIndex + 1}` : `Y${yAxisIndex + 1}`;
                      return (
                        <div key={key} className="flex items-center gap-1 py-0.5">
                          <span className="text-[9px] font-mono font-bold text-muted-foreground/50 w-5 shrink-0">{label}</span>
                          <button
                            onClick={() => toggleLogAxis(paneId, yAxisIndex)}
                            className={`h-5 px-1 text-[8px] font-mono font-bold rounded-[2px] transition-colors shrink-0 ${
                              isLog ? 'text-primary bg-primary/10' : 'text-muted-foreground/30 hover:text-foreground hover:bg-primary/[0.06]'
                            }`}
                            title="Log scale"
                          >
                            LOG
                          </button>
                          <button
                            onClick={() => toggleInvertAxis(paneId, yAxisIndex)}
                            className={`h-5 px-1 text-[8px] font-mono font-bold rounded-[2px] transition-colors shrink-0 ${
                              isInv ? 'text-primary bg-primary/10' : 'text-muted-foreground/30 hover:text-foreground hover:bg-primary/[0.06]'
                            }`}
                            title="Invert axis"
                          >
                            INV
                          </button>
                          <button
                            onClick={() => togglePctAxis(paneId, yAxisIndex)}
                            className={`h-5 px-1 text-[8px] font-mono font-bold rounded-[2px] transition-colors shrink-0 ${
                              isPct ? 'text-primary bg-primary/10' : 'text-muted-foreground/30 hover:text-foreground hover:bg-primary/[0.06]'
                            }`}
                            title="Percent format"
                          >
                            %
                          </button>
                          <input
                            type="number"
                            value={range.min ?? ''}
                            onChange={(e) => {
                              const v = e.target.value;
                              setYAxisRange(paneId, yAxisIndex, { ...range, min: v === '' ? undefined : parseFloat(v) });
                            }}
                            className="w-[46px] h-5 px-1 text-[9px] font-mono text-center border border-border/25 rounded-[2px] bg-background text-foreground focus:outline-none focus:border-primary/40"
                            placeholder="min"
                            step="any"
                          />
                          <input
                            type="number"
                            value={range.max ?? ''}
                            onChange={(e) => {
                              const v = e.target.value;
                              setYAxisRange(paneId, yAxisIndex, { ...range, max: v === '' ? undefined : parseFloat(v) });
                            }}
                            className="w-[46px] h-5 px-1 text-[9px] font-mono text-center border border-border/25 rounded-[2px] bg-background text-foreground focus:outline-none focus:border-primary/40"
                            placeholder="max"
                            step="any"
                          />
                        </div>
                      );
                    })}
                  </div>
                );
              })()}

              {/* Pane controls */}
              {panes.length > 1 && (
                <div className="shrink-0 border-t border-border/20 px-2 py-1 flex items-center gap-1.5">
                  <span className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/30">Panes</span>
                  {panes.map((p) => (
                    <div key={p.id} className="flex items-center gap-0.5">
                      <span className="text-[10px] font-mono text-muted-foreground">{p.label}</span>
                      <button onClick={() => removePane(p.id)} className="w-4 h-4 flex items-center justify-center text-muted-foreground/20 hover:text-destructive transition-colors">
                        <X className="w-2.5 h-2.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Annotations section */}
              {showAnnotations && (
                <div className="shrink-0 border-t border-border/20 px-2 py-1.5 max-h-[160px] overflow-y-auto custom-scrollbar">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/30">Annotations</span>
                    <div className="flex items-center gap-0.5">
                      <button onClick={() => addAnnotation('hline')} className="h-4 px-1 text-[9px] font-mono text-muted-foreground/40 hover:text-foreground transition-colors" title="H-Line">H</button>
                      <button onClick={() => addAnnotation('vline')} className="h-4 px-1 text-[9px] font-mono text-muted-foreground/40 hover:text-foreground transition-colors" title="V-Line">V</button>
                      <button onClick={() => addAnnotation('text')} className="h-4 px-1 text-[9px] font-mono text-muted-foreground/40 hover:text-foreground transition-colors" title="Text">T</button>
                    </div>
                  </div>
                  {annotations.map((ann) => (
                    <div key={ann.id} className="flex items-center gap-1.5 py-0.5 group/ann">
                      <input
                        type="color"
                        value={ann.color}
                        onChange={(e) => updateAnnotation(ann.id, { color: e.target.value })}
                        className="w-4 h-4 rounded cursor-pointer border-0 p-0 shrink-0"
                      />
                      <span className="text-[9px] font-mono text-muted-foreground/50 shrink-0 w-5">{ann.type === 'hline' ? 'H' : ann.type === 'vline' ? 'V' : 'T'}</span>
                      {ann.type === 'hline' && (
                        <input type="number" value={ann.y ?? 0} onChange={(e) => updateAnnotation(ann.id, { y: parseFloat(e.target.value) || 0 })}
                          className="w-14 h-5 px-1 text-[10px] font-mono text-center border border-border/30 rounded-[var(--radius)] bg-background text-foreground focus:outline-none" step="any" />
                      )}
                      {ann.type === 'vline' && (
                        <>
                          <input type="date" value={ann.x || ''} onChange={(e) => updateAnnotation(ann.id, { x: e.target.value })}
                            className="h-5 px-1 text-[9px] font-mono border border-border/30 rounded-[var(--radius)] bg-background text-foreground focus:outline-none flex-1 min-w-0" style={formStyle} />
                          <input type="text" value={ann.text || ''} onChange={(e) => updateAnnotation(ann.id, { text: e.target.value })} placeholder="Lbl"
                            className="w-10 h-5 px-1 text-[9px] font-mono border border-border/30 rounded-[var(--radius)] bg-background text-foreground focus:outline-none" />
                        </>
                      )}
                      {ann.type === 'text' && (
                        <>
                          <input type="text" value={ann.text || ''} onChange={(e) => updateAnnotation(ann.id, { text: e.target.value })} placeholder="Text"
                            className="flex-1 min-w-0 h-5 px-1 text-[9px] font-mono border border-border/30 rounded-[var(--radius)] bg-background text-foreground focus:outline-none" />
                        </>
                      )}
                      <button onClick={() => removeAnnotation(ann.id)}
                        className="w-4 h-4 flex items-center justify-center text-muted-foreground/15 hover:text-destructive opacity-0 group-hover/ann:opacity-100 transition-all shrink-0">
                        <X className="w-2.5 h-2.5" />
                      </button>
                    </div>
                  ))}
                  {annotations.length === 0 && (
                    <p className="text-[10px] text-muted-foreground/25 py-1">Click H, V, or T to add</p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* ═══════════════════ SAVE MODAL ═══════════════════ */}
        {saveModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setSaveModalOpen(false)}>
            <div className="bg-card border border-border/50 rounded-[var(--radius)] shadow-lg p-4 w-[320px]" onClick={(e) => e.stopPropagation()}>
              <h3 className="text-[12px] font-semibold uppercase tracking-wider text-foreground mb-3">Save Workspace</h3>
              <input
                autoFocus
                type="text"
                value={workspaceName}
                onChange={(e) => setWorkspaceName(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && workspaceName.trim()) saveWorkspace(workspaceName.trim()); }}
                placeholder="Workspace name..."
                className="w-full px-2.5 py-1.5 text-[12px] border border-border/50 rounded-[var(--radius)] bg-background text-foreground focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/15"
                style={formStyle}
              />
              <div className="flex gap-2 mt-3">
                <button onClick={() => setSaveModalOpen(false)} className="flex-1 h-7 rounded-[var(--radius)] text-[11px] font-medium border border-border/30 text-muted-foreground hover:text-foreground transition-colors">Cancel</button>
                <button
                  onClick={() => workspaceName.trim() && saveWorkspace(workspaceName.trim())}
                  disabled={!workspaceName.trim()}
                  className="flex-1 h-7 rounded-[var(--radius)] text-[11px] font-medium bg-foreground text-background hover:opacity-90 transition-colors disabled:opacity-30"
                >
                  {activeWorkspaceId ? 'Update' : 'Save'}
                </button>
              </div>
            </div>
          </div>
        )}
        {/* ═══════════════════ SAVE TO PACK MODAL ═══════════════════ */}
        {saveToPackOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setSaveToPackOpen(false)}>
            <div className="bg-card border border-border/50 rounded-[var(--radius)] shadow-lg p-4 w-[320px]" onClick={(e) => e.stopPropagation()}>
              <h3 className="text-[12px] font-semibold uppercase tracking-wider text-foreground mb-3">Save to Pack</h3>
              {packsLoading ? (
                <div className="flex items-center justify-center py-6">
                  <Loader2 className="w-4 h-4 animate-spin text-primary/40" />
                </div>
              ) : packList.length > 0 ? (
                <div className="flex flex-col gap-1 max-h-[240px] overflow-y-auto custom-scrollbar">
                  {packList.map((pack) => (
                    <button
                      key={pack.id}
                      onClick={() => saveChartToPack(pack.id)}
                      disabled={savingToPack}
                      className="w-full text-left px-3 py-2 rounded-[var(--radius)] text-[11px] font-medium text-foreground hover:bg-primary/[0.06] border border-border/20 transition-colors disabled:opacity-30"
                    >
                      {pack.name}
                    </button>
                  ))}
                </div>
              ) : (
                <p className="text-[11px] text-muted-foreground/40 py-4 text-center">
                  No packs yet. Create one in <a href="/chartpack" className="text-primary hover:underline">Chart Packs</a>.
                </p>
              )}
              <div className="flex gap-2 mt-3">
                <button onClick={() => setSaveToPackOpen(false)} className="flex-1 h-7 rounded-[var(--radius)] text-[11px] font-medium border border-border/30 text-muted-foreground hover:text-foreground transition-colors">Cancel</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

export default function ChartsPage() {
  return (
    <Suspense>
      <ChartsPageInner />
    </Suspense>
  );
}
