'use client';

import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { useTheme } from '@/context/ThemeContext';
import { applyChartTheme, CHART_SEMANTIC, type PlotlyFigure } from '@/lib/chartTheme';
import { Loader2, AlertTriangle, ChevronDown } from 'lucide-react';
import dynamic from 'next/dynamic';

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => <div className="h-full w-full" />,
}) as any;

// ── Types ────────────────────────────────────────────────────────────────────

export interface VomoScores {
  '1m': number | null; '6m': number | null; '1y': number | null; composite: number | null;
  history?: { dates: string[]; values: number[] };
}

export interface ApiIndex {
  name: string;
  regime: 'Bull' | 'Bear' | 'Neutral';
  score: number;
  price: number;
  daily_ret: number | null;
  ret_1m: number | null;
  ret_3m: number | null;
  ret_6m: number | null;
  ret_1y: number | null;
  weeks_in_regime: number;
  vomo: VomoScores;
  daily_prices?: { dates: string[]; open: number[]; high: number[]; low: number[]; close: number[]; volume: number[] };
  weekly_vams?: { dates: string[]; scores: number[] };
}

interface VamsResponse {
  indices: ApiIndex[];
  cacri: number;
  cross_asset_vams: Record<string, number>;
  computed_at: string;
}

export type Period = '1M' | '3M' | '6M' | '1Y' | '3Y' | '5Y';
export const PERIODS: Period[] = ['1M', '3M', '6M', '1Y', '3Y', '5Y'];

// ── Constants ────────────────────────────────────────────────────────────────

const PERIOD_MONTHS: Record<Period, number> = { '1M': 1, '3M': 3, '6M': 6, '1Y': 12, '3Y': 36, '5Y': 60 };
const PLOT_CONFIG = {
  responsive: true,
  displayModeBar: true,
  scrollZoom: true,
  modeBarButtonsToRemove: ['lasso2d', 'select2d', 'sendDataToCloud'] as any[],
  displaylogo: false,
};
const PLOT_STYLE = { width: '100%', height: '100%' };
const MONO = '"Space Mono", "SF Mono", "Fira Code", monospace';

const SMA_COLORS = {
  sma50:  { line: '#00D2FF', label: '#00D2FF' },
  sma150: { line: '#FFB84D', label: '#FFB84D' },
  sma200: { line: '#A020F0', label: '#A020F0' },
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function periodStart(period: Period): string {
  const now = new Date();
  const d = new Date(now.getFullYear(), now.getMonth() - PERIOD_MONTHS[period], now.getDate());
  return d.toISOString().slice(0, 10);
}

function sma(arr: number[], window: number): (number | null)[] {
  const out: (number | null)[] = [];
  let sum = 0;
  for (let i = 0; i < arr.length; i++) {
    sum += arr[i];
    if (i >= window) sum -= arr[i - window];
    out.push(i >= window - 1 ? sum / window : null);
  }
  return out;
}

function ema(arr: number[], period: number): (number | null)[] {
  const k = 2 / (period + 1);
  const out: (number | null)[] = [];
  let prev: number | null = null;
  for (let i = 0; i < arr.length; i++) {
    if (i < period - 1) { out.push(null); continue; }
    if (prev === null) {
      let sum = 0;
      for (let j = i - period + 1; j <= i; j++) sum += arr[j];
      prev = sum / period;
    } else {
      prev = arr[i] * k + prev * (1 - k);
    }
    out.push(prev);
  }
  return out;
}

function hlMidpoint(high: number[], low: number[], period: number): (number | null)[] {
  const out: (number | null)[] = [];
  for (let i = 0; i < high.length; i++) {
    if (i < period - 1) { out.push(null); continue; }
    let hi = -Infinity, lo = Infinity;
    for (let j = i - period + 1; j <= i; j++) {
      hi = Math.max(hi, high[j]);
      lo = Math.min(lo, low[j]);
    }
    out.push((hi + lo) / 2);
  }
  return out;
}

function addDays(dateStr: string, n: number): string {
  const d = new Date(dateStr + 'T12:00:00');
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}


function fmtNum(v: number): string {
  if (v >= 10000) return v.toLocaleString(undefined, { maximumFractionDigits: 0 });
  if (v >= 100) return v.toLocaleString(undefined, { maximumFractionDigits: 1 });
  return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function themed(fig: PlotlyFigure, theme: 'light' | 'dark'): PlotlyFigure {
  // Preserve settings that applyChartTheme may override
  const origMargin = fig.layout.margin ? { ...fig.layout.margin } : undefined;
  const origXaxis = fig.layout.xaxis ? { ...fig.layout.xaxis } : undefined;
  const origDragmode = (fig.layout as any).dragmode;
  const out = applyChartTheme(fig, theme, { transparentBackground: true }) as PlotlyFigure;
  const tickFont = { family: MONO, size: 9 };
  for (const key of Object.keys(out.layout)) {
    if (/^[xy]axis\d*$/.test(key)) {
      const ax = (out.layout as any)[key];
      if (ax) ax.tickfont = { ...ax.tickfont, ...tickFont };
    }
  }
  // Restore margin
  if (origMargin) (out.layout as any).margin = origMargin;
  // Restore dragmode
  if (origDragmode !== undefined) (out.layout as any).dragmode = origDragmode;
  // Restore x-axis formatting
  if (origXaxis && (out.layout as any).xaxis) {
    const xax = (out.layout as any).xaxis;
    if (origXaxis.tickformat) xax.tickformat = origXaxis.tickformat;
    if (origXaxis.tickfont) xax.tickfont = { ...xax.tickfont, ...origXaxis.tickfont };
    if (origXaxis.showticklabels !== undefined) xax.showticklabels = origXaxis.showticklabels;
    if (origXaxis.showgrid !== undefined) xax.showgrid = origXaxis.showgrid;
    if (origXaxis.showline !== undefined) xax.showline = origXaxis.showline;
    if (origXaxis.linecolor) xax.linecolor = origXaxis.linecolor;
    if (origXaxis.linewidth !== undefined) xax.linewidth = origXaxis.linewidth;
    if (origXaxis.gridcolor) xax.gridcolor = origXaxis.gridcolor;
  }
  return out;
}

// ── VOMO color logic ─────────────────────────────────────────────────────────

function vomoCls(v: number | null): string {
  if (v == null) return 'text-muted-foreground/40';
  if (v >= 1) return 'text-success';
  if (v > -1) return 'text-warning';
  return 'text-destructive';
}

function vomoBorderCls(composite: number | null): string {
  if (composite == null) return 'border-border/30';
  if (composite >= 3) return 'border-success/50';
  if (composite >= 1) return 'border-success/25';
  if (composite > -1) return 'border-warning/20';
  if (composite > -3) return 'border-destructive/25';
  return 'border-destructive/50';
}

// ── Chart builder ────────────────────────────────────────────────────────────

function buildFig(idx: ApiIndex, theme: 'light' | 'dark', startStr: string): PlotlyFigure | null {
  const dp = idx.daily_prices;
  if (!dp || dp.dates.length === 0) return null;
  const isDark = theme === 'dark';
  const sem = CHART_SEMANTIC[theme];
  const n = dp.dates.length;

  // ── Compute indicators on full data ──
  const allEma21 = ema(dp.close, 21);
  const allEma55 = ema(dp.close, 55);

  // Ichimoku (9, 26, 52)
  const displacement = 26;
  const allTenkan = hlMidpoint(dp.high, dp.low, 9);
  const allKijun = hlMidpoint(dp.high, dp.low, 26);
  const senkouBRaw = hlMidpoint(dp.high, dp.low, 52);
  const allSenkouA: (number | null)[] = [];
  const allSenkouB: (number | null)[] = [];
  for (let i = 0; i < n + displacement; i++) {
    const src = i - displacement;
    if (src < 0 || src >= n) { allSenkouA.push(null); allSenkouB.push(null); continue; }
    const t = allTenkan[src], k = allKijun[src];
    allSenkouA.push(t != null && k != null ? (t + k) / 2 : null);
    allSenkouB.push(senkouBRaw[src]);
  }
  const extDates = [...dp.dates];
  if (n > 0) {
    const last = dp.dates[n - 1];
    for (let i = 1; i <= displacement; i++) extDates.push(addDays(last, i));
  }

  // MACD (12, 26, 9)
  const ema12 = ema(dp.close, 12);
  const ema26 = ema(dp.close, 26);
  const allMacdLine: (number | null)[] = dp.close.map((_, i) =>
    ema12[i] != null && ema26[i] != null ? ema12[i]! - ema26[i]! : null
  );
  const macdValid = allMacdLine.filter(v => v != null) as number[];
  const sigEma = ema(macdValid, 9);
  const allSignal: (number | null)[] = [];
  let vi = 0;
  for (let i = 0; i < n; i++) {
    if (allMacdLine[i] != null) { allSignal.push(sigEma[vi++]); } else { allSignal.push(null); }
  }
  const allHist: (number | null)[] = allMacdLine.map((m, i) =>
    m != null && allSignal[i] != null ? m - allSignal[i]! : null
  );

  // ROC (1-period, smoothed SMA 9)
  const rocRaw: number[] = dp.close.map((c, i) => i === 0 ? 0 : ((c - dp.close[i - 1]) / dp.close[i - 1]) * 100);
  const allRoc = sma(rocRaw, 9);

  // ── Slice to visible range ──
  let si = dp.dates.findIndex(d => d >= startStr);
  if (si < 0) si = 0;

  const dates = dp.dates.slice(si);
  const open = dp.open.slice(si);
  const high = dp.high.slice(si);
  const low = dp.low.slice(si);
  const close = dp.close.slice(si);
  const ema21Vis = allEma21.slice(si);
  const ema55Vis = allEma55.slice(si);
  const tenkanVis = allTenkan.slice(si);
  const kijunVis = allKijun.slice(si);
  const cloudDates = extDates.slice(si);
  const senkouAVis = allSenkouA.slice(si);
  const senkouBVis = allSenkouB.slice(si);
  const macdLine = allMacdLine.slice(si);
  const signal = allSignal.slice(si);
  const hist = allHist.slice(si);
  const roc = allRoc.slice(si);

  const lastVisDate = cloudDates.length ? cloudDates[cloudDates.length - 1] : startStr;
  const xEnd = addDays(lastVisDate, 5);

  // ── Colors ──
  const ema21Color = isDark ? 'rgba(200,200,210,0.6)' : 'rgba(30,30,40,0.5)';
  const ema55Color = isDark ? 'rgba(220,75,75,0.6)' : 'rgba(200,50,50,0.6)';
  const tenkanColor = isDark ? 'rgba(80,170,200,0.4)' : 'rgba(40,130,170,0.4)';
  const kijunColor = isDark ? 'rgba(160,110,60,0.45)' : 'rgba(140,85,35,0.45)';
  const cloudFill = isDark ? 'rgba(80,180,200,0.06)' : 'rgba(60,150,180,0.07)';
  const cloudLine = isDark ? 'rgba(80,180,200,0.15)' : 'rgba(60,150,180,0.15)';
  const macdLineColor = isDark ? 'rgba(0,180,150,0.8)' : 'rgba(0,150,130,0.8)';
  const macdSigColor = isDark ? 'rgba(220,100,50,0.6)' : 'rgba(200,80,40,0.6)';
  const macdHistColors = hist.map(v => v == null ? 'transparent'
    : v >= 0 ? (isDark ? 'rgba(0,180,150,0.5)' : 'rgba(0,160,130,0.5)')
    : (isDark ? 'rgba(0,180,150,0.25)' : 'rgba(0,160,130,0.25)')
  );
  const rocColors = roc.map(v => v == null ? 'transparent'
    : v >= 0 ? (isDark ? 'rgba(0,180,150,0.45)' : 'rgba(0,160,130,0.45)')
    : (isDark ? 'rgba(220,80,80,0.45)' : 'rgba(200,60,60,0.45)')
  );

  const tickFont = { family: MONO, size: 8, color: isDark ? 'rgba(200,200,210,0.35)' : 'rgba(40,40,45,0.35)' };
  const xTickFont = { family: MONO, size: 9, color: isDark ? 'rgba(200,200,210,0.55)' : 'rgba(40,40,45,0.55)' };
  const gridColor = isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.03)';
  const dividerColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';
  const hoverBg = isDark ? 'rgba(16,18,28,0.97)' : 'rgba(255,255,252,0.97)';
  const hoverBorder = isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.12)';
  const hoverFont = { family: '"Space Mono", monospace', size: 12, color: isDark ? '#e2e4ea' : '#1a1c24' };
  const annoColor = isDark ? 'rgba(200,200,210,0.3)' : 'rgba(40,40,45,0.3)';

  // ── Hover palette ──
  const hDim = isDark ? '#707890' : '#7a8094';
  const hVal = isDark ? '#e2e4ea' : '#1a1c24';
  const hEma21 = isDark ? '#a0a8c0' : '#3a3e50';
  const hEma55 = isDark ? '#e87070' : '#c04040';
  const hUp = isDark ? '#4ade80' : '#16a34a';
  const hDn = isDark ? '#f87171' : '#dc2626';
  const hRule = isDark ? '#2a2e40' : '#d8dae0';
  const mono = `font-family:${MONO}`;

  // ── Hover text ──
  const sans = 'font-family:"Space Mono",monospace';
  const hoverText = dates.map((_, i) => {
    const d = new Date(dates[i] + 'T12:00:00');
    const dateStr = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
    const chg = close[i] - open[i];
    const chgPct = open[i] ? ((chg / open[i]) * 100).toFixed(2) : '0.00';
    const chgCol = chg >= 0 ? hUp : hDn;
    const chgSign = chg >= 0 ? '+' : '';

    let t = `<span style="${sans};color:${hDim};font-size:10px;letter-spacing:0.3px">${dateStr}</span>`;
    t += `<br><span style="${mono};color:${hDim};font-size:9px;letter-spacing:0.5px">O </span><span style="${mono};color:${hVal};font-size:12px">${fmtNum(open[i])}</span>`;
    t += `<span style="${mono};color:${hDim};font-size:9px;letter-spacing:0.5px">  H </span><span style="${mono};color:${hVal};font-size:12px">${fmtNum(high[i])}</span>`;
    t += `<br><span style="${mono};color:${hDim};font-size:9px;letter-spacing:0.5px">L </span><span style="${mono};color:${hVal};font-size:12px">${fmtNum(low[i])}</span>`;
    t += `<span style="${mono};color:${hDim};font-size:9px;letter-spacing:0.5px">  C </span><span style="${mono};color:${hVal};font-size:12px;font-weight:600">${fmtNum(close[i])}</span>`;
    t += `<br><span style="${mono};color:${chgCol};font-size:12px;font-weight:600">${chgSign}${fmtNum(chg)}</span>`;
    t += `<span style="${mono};color:${chgCol};font-size:10px">  ${chgSign}${chgPct}%</span>`;

    const e21 = ema21Vis[i], e55 = ema55Vis[i];
    if (e21 != null || e55 != null) {
      t += `<br><span style="color:${hRule}">───────────</span>`;
      if (e21 != null) t += `<br><span style="${sans};color:${hEma21};font-size:10px">EMA 21</span> <span style="${mono};color:${hVal};font-size:11px">${fmtNum(e21)}</span>`;
      if (e55 != null) t += `<span style="${sans};color:${hDim};font-size:10px">   EMA 55</span> <span style="${mono};color:${hVal};font-size:11px">${fmtNum(e55)}</span>`;
    }
    const m = macdLine[i], s = signal[i];
    if (m != null) {
      t += `<br><span style="${sans};color:${hDim};font-size:10px">MACD</span> <span style="${mono};color:${hVal};font-size:11px">${m.toFixed(2)}</span>`;
      if (s != null) t += `<span style="${sans};color:${hDim};font-size:10px">   Signal</span> <span style="${mono};color:${hVal};font-size:11px">${s.toFixed(2)}</span>`;
    }
    const r = roc[i];
    if (r != null) {
      const rCol = r >= 0 ? hUp : hDn;
      t += `<br><span style="${sans};color:${hDim};font-size:10px">ROC</span> <span style="${mono};color:${rCol};font-size:11px">${r >= 0 ? '+' : ''}${r.toFixed(2)}%</span>`;
    }
    return t;
  });

  // ── Panel divider lines + zero lines ──
  const shapes: any[] = [
    { type: 'line', xref: 'paper', yref: 'paper', x0: 0, x1: 1, y0: 0.35, y1: 0.35, line: { color: dividerColor, width: 0.5 } },
    { type: 'line', xref: 'paper', yref: 'paper', x0: 0, x1: 1, y0: 0.17, y1: 0.17, line: { color: dividerColor, width: 0.5 } },
    { type: 'line', xref: 'paper', yref: 'y2', x0: 0, x1: 1, y0: 0, y1: 0, line: { color: dividerColor, width: 0.5, dash: 'dot' } },
    { type: 'line', xref: 'paper', yref: 'y3', x0: 0, x1: 1, y0: 0, y1: 0, line: { color: dividerColor, width: 0.5, dash: 'dot' } },
  ];

  // Panel label annotations with current values
  let macdLabel = 'MACD 12 26 9';
  let rocLabel = 'ROC 1 SMA 9';
  for (let i = macdLine.length - 1; i >= 0; i--) { if (macdLine[i] != null) { macdLabel += `  ${macdLine[i]!.toFixed(2)}`; break; } }
  for (let i = roc.length - 1; i >= 0; i--) { if (roc[i] != null) { rocLabel += `  ${roc[i]!.toFixed(2)}%`; break; } }
  const annotations: any[] = [
    { text: macdLabel, xref: 'paper', yref: 'paper', x: 0.005, y: 0.335, xanchor: 'left', yanchor: 'top', showarrow: false, font: { family: MONO, size: 7, color: annoColor } },
    { text: rocLabel, xref: 'paper', yref: 'paper', x: 0.005, y: 0.165, xanchor: 'left', yanchor: 'top', showarrow: false, font: { family: MONO, size: 7, color: annoColor } },
  ];

  const fig: PlotlyFigure = {
    data: [
      // ── Price panel (y) ──
      { type: 'scatter', x: cloudDates, y: senkouAVis, mode: 'lines', line: { color: cloudLine, width: 0.5 }, showlegend: false, hoverinfo: 'skip', yaxis: 'y' },
      { type: 'scatter', x: cloudDates, y: senkouBVis, mode: 'lines', line: { color: cloudLine, width: 0.5 }, fill: 'tonexty', fillcolor: cloudFill, showlegend: false, hoverinfo: 'skip', yaxis: 'y' },
      { type: 'scatter', x: dates, y: tenkanVis, mode: 'lines', line: { color: tenkanColor, width: 1 }, showlegend: false, hoverinfo: 'skip', yaxis: 'y' },
      { type: 'scatter', x: dates, y: kijunVis, mode: 'lines', line: { color: kijunColor, width: 1 }, showlegend: false, hoverinfo: 'skip', yaxis: 'y' },
      { type: 'ohlc', x: dates, open, high, low, close, increasing: { line: { color: sem.success, width: 1 } }, decreasing: { line: { color: sem.destructive, width: 1 } }, showlegend: false, yaxis: 'y', hoverinfo: 'none' },
      { type: 'scatter', x: dates, y: ema21Vis, mode: 'lines', line: { color: ema21Color, width: 1.2 }, showlegend: false, hoverinfo: 'skip', yaxis: 'y' },
      { type: 'scatter', x: dates, y: ema55Vis, mode: 'lines', line: { color: ema55Color, width: 1.2 }, showlegend: false, hoverinfo: 'skip', yaxis: 'y' },
      { type: 'scatter', x: dates, y: close, mode: 'lines', line: { width: 0, color: 'rgba(0,0,0,0)' }, showlegend: false, yaxis: 'y', text: hoverText, hoverinfo: 'text', hoverlabel: { bgcolor: hoverBg, bordercolor: hoverBorder, font: hoverFont } },
      // ── MACD panel (y2) ──
      { type: 'bar', x: dates, y: hist, marker: { color: macdHistColors, line: { width: 0 } }, showlegend: false, hoverinfo: 'skip', yaxis: 'y2' },
      { type: 'scatter', x: dates, y: macdLine, mode: 'lines', line: { color: macdLineColor, width: 1 }, showlegend: false, hoverinfo: 'skip', yaxis: 'y2' },
      { type: 'scatter', x: dates, y: signal, mode: 'lines', line: { color: macdSigColor, width: 1 }, showlegend: false, hoverinfo: 'skip', yaxis: 'y2' },
      // ── ROC panel (y3) ──
      { type: 'bar', x: dates, y: roc, marker: { color: rocColors, line: { width: 0 } }, showlegend: false, hoverinfo: 'skip', yaxis: 'y3' },
    ],
    layout: {
      xaxis: { type: 'date', showgrid: true, gridcolor: gridColor, showline: true, linecolor: dividerColor, linewidth: 0.5, range: [startStr, xEnd], tickformat: "%b '%y", nticks: 7, tickangle: 0, rangeslider: { visible: false }, tickfont: xTickFont, anchor: 'y3', showticklabels: true },
      yaxis:  { domain: [0.36, 1.0], showgrid: true, gridcolor: gridColor, gridwidth: 1, showline: false, side: 'right', automargin: true, tickfont: tickFont },
      yaxis2: { domain: [0.18, 0.34], showgrid: false, showline: false, side: 'right', automargin: true, tickfont: tickFont, zeroline: false },
      yaxis3: { domain: [0.0, 0.16], showgrid: false, showline: false, side: 'right', automargin: true, tickfont: tickFont, zeroline: false },
      margin: { l: 2, r: 2, t: 6, b: 62 },
      dragmode: 'zoom',
      hovermode: 'x', hoverdistance: 50, showlegend: false, shapes, annotations,
    },
  };

  return themed(fig, theme);
}

// ── Chart card ───────────────────────────────────────────────────────────────

const ChartCard = React.memo(function ChartCard({ idx, theme, startStr, indices, selectedIdx, onSelect }: {
  idx: ApiIndex; theme: 'light' | 'dark'; startStr: string;
  indices: ApiIndex[]; selectedIdx: number; onSelect: (i: number) => void;
}) {
  const fig = useMemo(() => buildFig(idx, theme, startStr), [idx, theme, startStr]);
  const layout = useMemo(() => fig ? { ...fig.layout, autosize: true } : null, [fig?.layout]);
  const vomo = idx.vomo;
  const borderCls = vomoBorderCls(vomo?.composite);
  const [showPicker, setShowPicker] = useState(false);
  const pickerRef = React.useRef<HTMLDivElement>(null);

  // Close on outside click
  React.useEffect(() => {
    if (!showPicker) return;
    const handler = (e: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) setShowPicker(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showPicker]);

  const dailyRet = useMemo(() => {
    const c = idx.daily_prices?.close;
    if (!c || c.length < 2 || !c[c.length - 2]) return null;
    return (c[c.length - 1] - c[c.length - 2]) / c[c.length - 2];
  }, [idx.daily_prices?.close]);

  return (
    <div className={`rounded-[var(--radius)] border bg-card flex flex-col overflow-hidden hover:border-foreground/20 transition-colors ${borderCls}`} style={{ minHeight: 480 }}>
      {/* Header: name dropdown + price + daily return */}
      <div className="flex items-center gap-1.5 px-2.5 py-1.5 border-b border-border/10">
        <div ref={pickerRef} className="relative">
          <button
            onClick={() => setShowPicker(p => !p)}
            className="flex items-center gap-1 text-[12.5px] font-semibold text-foreground leading-none hover:text-primary transition-colors"
          >
            {idx.name}
            <ChevronDown className="w-3 h-3 text-muted-foreground/40" />
          </button>
          {showPicker && (
            <div className="absolute left-0 top-full mt-1 z-50 min-w-[160px] rounded-[var(--radius)] border border-border/40 bg-popover shadow-lg py-1 max-h-64 overflow-y-auto">
              {indices.map((item, i) => (
                <button
                  key={item.name}
                  onClick={() => { onSelect(i); setShowPicker(false); }}
                  className={`w-full text-left px-2.5 py-1.5 text-[11.5px] font-mono transition-colors ${
                    i === selectedIdx
                      ? 'text-foreground bg-primary/10 font-semibold'
                      : 'text-foreground/70 hover:text-foreground hover:bg-foreground/[0.05]'
                  }`}
                >
                  {item.name}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="flex-1" />
        <span className="text-[12.5px] font-mono tabular-nums text-foreground/80 font-semibold shrink-0">{fmtNum(idx.price)}</span>
        {dailyRet !== null && (
          <span className={`text-[11px] font-mono tabular-nums font-bold shrink-0 ${dailyRet >= 0 ? 'text-success' : 'text-destructive'}`}>
            {dailyRet > 0 ? '+' : ''}{(dailyRet * 100).toFixed(1)}%
          </span>
        )}
      </div>

      {/* VOMO scores strip */}
      <div className="flex items-center gap-0 px-0 border-b border-border/10 bg-foreground/[0.015]">
        {/* Composite — prominent */}
        <div className="flex items-center gap-1 px-2.5 py-1 border-r border-border/10">
          <span className="text-[9.5px] font-mono text-muted-foreground/35 uppercase" title="Volatility Momentum — composite signal measuring value and momentum across timeframes">VOMO</span>
          <span className={`text-[13px] font-mono tabular-nums font-bold ${vomoCls(vomo?.composite)}`}>
            {vomo?.composite != null ? (vomo.composite > 0 ? '+' : '') + vomo.composite.toFixed(1) : '\u2014'}
          </span>
        </div>
        {/* Individual timeframes */}
        {([['1M', vomo?.['1m']], ['6M', vomo?.['6m']], ['1Y', vomo?.['1y']]] as [string, number | null][]).map(([label, v]) => (
          <div key={label} className="flex items-center gap-1 px-2 py-1 border-r border-border/10 last:border-r-0">
            <span className="text-[7px] font-mono text-muted-foreground/30 uppercase">{label}</span>
            <span className={`text-[11px] font-mono tabular-nums font-semibold ${vomoCls(v)}`}>
              {v != null ? (v > 0 ? '+' : '') + v.toFixed(1) : '\u2014'}
            </span>
          </div>
        ))}
      </div>

      {/* Chart */}
      <div className="flex-1 min-h-0">
        {fig && layout ? (
          <Plot data={fig.data} layout={layout} config={PLOT_CONFIG} useResizeHandler style={PLOT_STYLE} />
        ) : (
          <div className="h-full flex items-center justify-center"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground/20" /></div>
        )}
      </div>
    </div>
  );
});

// ── Default index name (matches first key in backend INDEX_YF) ──────────────
const DEFAULT_INDEX = 'S&P 500';

// ── Main component ───────────────────────────────────────────────────────────

export default function Technicals({ defaultIndex, onOpenBriefing }: {
  defaultIndex?: string; onOpenBriefing?: () => void;
}) {
  const { theme } = useTheme();
  const [selectedName, setSelectedName] = useState(defaultIndex || DEFAULT_INDEX);
  const [activePeriod, setActivePeriod] = useState<Period>('1Y');

  const { data: detail, isLoading, isError } = useQuery({
    queryKey: ['technicals-detail', selectedName],
    queryFn: () => apiFetchJson<ApiIndex>(`/api/macro/technicals/detail?index=${encodeURIComponent(selectedName)}`),
    staleTime: 60_000, gcTime: 120_000, refetchOnWindowFocus: false,
  });
  const { data: summary } = useQuery({
    queryKey: ['technicals-summary'],
    queryFn: () => apiFetchJson<VamsResponse>('/api/macro/technicals/summary'),
    staleTime: 60_000, gcTime: 120_000,
  });

  const startStr = useMemo(() => periodStart(activePeriod), [activePeriod]);
  const indices = summary?.indices ?? [];
  const selectedIdx = useMemo(() => {
    const i = indices.findIndex(idx => idx.name === selectedName);
    return i >= 0 ? i : 0;
  }, [indices, selectedName]);
  const current = detail ?? null;

  if (isLoading) {
    return <div className="h-full flex items-center justify-center"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground/30" /></div>;
  }

  if (isError || !current) {
    return (
      <div className="h-full flex items-center justify-center gap-2">
        <AlertTriangle className="w-3.5 h-3.5 text-muted-foreground/30" />
        <span className="text-[12.5px] text-muted-foreground/30 font-mono">Technical data unavailable</span>
      </div>
    );
  }

  return (
    <div className="h-full px-1.5 sm:px-2 pt-1 pb-1">
      <ChartCard idx={current} theme={theme} startStr={startStr} indices={indices} selectedIdx={selectedIdx} onSelect={(i) => setSelectedName(indices[i].name)} />
    </div>
  );
}
