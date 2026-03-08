'use client';

import dynamic from 'next/dynamic';
import { useEffect, useMemo, useState } from 'react';
import AppShell from '@/components/AppShell';
import { Loader2, AlertCircle, Info } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { useTheme } from '@/context/ThemeContext';
import { applyChartTheme, type PlotlyFigure } from '@/lib/chartTheme';

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center bg-background/50">
      <Loader2 className="w-5 h-5 animate-spin text-sky-500/50" />
    </div>
  ),
}) as any;

// ─── Types ──────────────────────────────────────────────────────────────────

interface Target { name: string; ticker: string; region: string; }

interface Indicator { name: string; z: number; signal: string; desc: string; }

interface RegimeStat {
  regime: string; mean_fwd_ret: number; median_fwd_ret: number;
  std: number; sharpe: number; pct_positive: number; n: number;
}

interface LiqPhaseStat {
  phase: string; mean_fwd_ret: number; median_fwd_ret: number;
  std: number; sharpe: number; pct_positive: number; n: number;
}

interface TacticalStat {
  bucket: string; mean_fwd_ret: number; median_fwd_ret: number;
  std: number; sharpe: number; pct_positive: number; n: number;
}

interface Snapshot {
  current: {
    regime: string; confidence: number; growth: number; inflation: number;
    liquidity: number; tactical: number; allocation: number; liq_phase: string;
    regime_probs: Record<string, number>;
  };
  projections: Record<string, Record<string, number>>;
  indicator_counts: Record<string, number>;
  indicators: Record<string, Indicator[]>;
  transition_matrix: { labels: string[]; values: number[][]; };
  regime_stats: RegimeStat[];
  liq_phase_stats?: LiqPhaseStat[];
  tactical_stats?: TacticalStat[];
}

interface TimeseriesData {
  dates: string[]; target_px: number[]; growth: number[]; inflation: number[];
  liquidity: number[]; tactical: number[]; allocation: number[];
  liq_phase: string[]; regime_probs: Record<string, number[]>;
}

interface BacktestStat {
  label: string; ann_return: number; ann_vol: number; sharpe: number;
  max_dd: number; info_ratio: number; tracking_err: number; ann_turnover: number;
}

interface ComponentBT {
  equity: number[]; weight: number[];
  stats: { ann_return?: number; ann_vol?: number; sharpe?: number; max_dd?: number; info_ratio?: number; ann_turnover?: number; };
}

interface BacktestData {
  dates: string[]; strategy_equity: number[]; benchmark_equity: number[];
  full_equity: number[]; strategy_weight: number[]; stats: BacktestStat[];
  regime_only?: ComponentBT; liquidity_only?: ComponentBT; tactical_only?: ComponentBT;
}

// ─── Constants ──────────────────────────────────────────────────────────────

const REGIME_COLORS: Record<string, string> = {
  Goldilocks: '#3fb950', Reflation: '#d29922', Stagflation: '#f85149', Deflation: '#bc8cff',
};

const PHASE_COLORS: Record<string, string> = {
  Spring: '#3fb950', Summer: '#d29922', Fall: '#f85149', Winter: '#bc8cff',
};

const TACTICAL_COLORS: Record<string, string> = {
  'Very Bearish': '#f85149', 'Bearish': '#f8514988', 'Neutral': '#a1a1aa',
  'Bullish': '#3fb95088', 'Very Bullish': '#3fb950',
};

const REGIME_ORDER = ['Goldilocks', 'Reflation', 'Stagflation', 'Deflation'];

type Tab = 'overview' | 'regime' | 'liquidity' | 'tactical';

const TABS: { key: Tab; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'regime', label: 'Regime' },
  { key: 'liquidity', label: 'Liquidity' },
  { key: 'tactical', label: 'Tactical' },
];

const PLOTLY_CONFIG = { responsive: true, displaylogo: false, modeBarButtonsToRemove: ['lasso2d' as const, 'select2d' as const] };

const CHART_M = { l: 52, r: 16, t: 28, b: 40 };
const CHART_M_HBAR = { l: 140, r: 16, t: 28, b: 40 };

// ─── Axis defaults ──────────────────────────────────────────────────────────
// Ensure all axes are visible with tick labels, lines, and gridlines.

const XAXIS_DATE = { type: 'date' as const, showticklabels: true, showline: true, linewidth: 1, showgrid: false };
const YAXIS_BASE = { showticklabels: true, showline: true, linewidth: 1, showgrid: true };

// ─── Helpers ────────────────────────────────────────────────────────────────

function fmt(v: number, d = 2): string { return v?.toFixed(d) ?? '-'; }
function fmtPct(v: number, d = 1): string { return `${(v * 100).toFixed(d)}%`; }
function signalColor(s: string): string {
  const l = s.toLowerCase();
  return l === 'bullish' || l === 'positive' ? 'text-emerald-500' : l === 'bearish' || l === 'negative' ? 'text-rose-500' : 'text-muted-foreground';
}
function zColor(z: number): string {
  return z > 0.5 ? '#3fb950' : z > 0 ? '#3fb950aa' : z > -0.5 ? '#f85149aa' : '#f85149';
}
function themed(fig: PlotlyFigure, theme: 'light' | 'dark'): PlotlyFigure {
  return applyChartTheme(fig, theme, { transparentBackground: true }) as PlotlyFigure;
}

// ─── Reusable Components ────────────────────────────────────────────────────

function LoadingSpinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center justify-center py-10">
      <div className="flex flex-col items-center gap-2">
        <Loader2 className="w-5 h-5 animate-spin text-sky-500/50" />
        <span className="text-[10px] text-muted-foreground/50 tracking-widest uppercase">{label ?? 'Loading'}</span>
      </div>
    </div>
  );
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center py-10">
      <div className="flex flex-col items-center gap-2 text-center">
        <AlertCircle className="w-5 h-5 text-rose-500/60" />
        <p className="text-[11px] text-muted-foreground">{message}</p>
      </div>
    </div>
  );
}

function InfoTooltip({ text }: { text: string }) {
  return (
    <span className="relative inline-flex group/tip ml-1 cursor-help align-middle">
      <Info className="w-3 h-3 text-muted-foreground/30 group-hover/tip:text-muted-foreground/60 transition-colors" />
      <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-2.5 py-1.5 text-[10px] leading-relaxed text-foreground bg-background border border-border/60 rounded-lg shadow-lg opacity-0 group-hover/tip:opacity-100 transition-opacity pointer-events-none w-[240px] z-50">
        {text}
      </span>
    </span>
  );
}

function RegimeProbBar({ probs }: { probs: Record<string, number> }) {
  return (
    <div className="w-full">
      <div className="flex rounded-lg overflow-hidden h-5 border border-border/40">
        {REGIME_ORDER.map((r) => {
          const pct = (probs[r] ?? 0) * 100;
          if (pct < 1) return null;
          return (
            <div key={r} className="flex items-center justify-center text-[9px] font-mono font-semibold transition-all duration-500"
              style={{ width: `${pct}%`, backgroundColor: REGIME_COLORS[r], color: r === 'Deflation' ? '#1a1a2e' : '#fff', minWidth: pct > 5 ? undefined : 0 }}
              title={`${r}: ${pct.toFixed(1)}%`}>
              {pct >= 10 ? `${pct.toFixed(0)}%` : ''}
            </div>
          );
        })}
      </div>
      <div className="flex gap-3 mt-1 flex-wrap">
        {REGIME_ORDER.map((r) => (
          <div key={r} className="flex items-center gap-1">
            <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: REGIME_COLORS[r] }} />
            <span className="text-[9px] text-muted-foreground">{r}</span>
            <span className="text-[9px] font-mono text-foreground tabular-nums">{fmtPct(probs[r] ?? 0)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SectionTitle({ children, info }: { children: React.ReactNode; info?: string }) {
  return (
    <h3 className="text-[12px] font-semibold text-foreground mb-2 flex items-center">
      {children}
      {info && <InfoTooltip text={info} />}
    </h3>
  );
}

/** Render a Plotly chart at given height. */
function ChartBox({ chart, height = 240 }: { chart: PlotlyFigure | null; height?: number }) {
  if (!chart) return <ErrorBox message="No data" />;
  return (
    <div style={{ height }}>
      <Plot data={chart.data} layout={{ ...chart.layout, autosize: true, margin: chart.layout?.margin ?? CHART_M }}
        config={PLOTLY_CONFIG} useResizeHandler style={{ width: '100%', height: '100%' }} />
    </div>
  );
}

/** Compact stats table row. */
function StatsRow({ label, color, values }: { label: string; color?: string; values: (string | number | React.ReactNode)[] }) {
  return (
    <tr className="border-b border-border/20">
      <td className="py-1 pr-3 font-medium text-foreground text-[11px] whitespace-nowrap">
        {color && <span className="inline-block w-2 h-2 rounded-full mr-1.5 align-middle" style={{ backgroundColor: color }} />}
        {label}
      </td>
      {values.map((v, i) => (
        <td key={i} className="text-right py-1 px-1.5 font-mono tabular-nums text-[11px] text-foreground">{v}</td>
      ))}
    </tr>
  );
}

/** Compact backtest section for embedding in each tab. */
function ComponentBacktest({ backtest, componentKey, label, color, target, theme }: {
  backtest: BacktestData; componentKey: 'regime_only' | 'liquidity_only' | 'tactical_only';
  label: string; color: string; target: string; theme: 'light' | 'dark';
}) {
  const comp = backtest[componentKey];

  const chart = useMemo(() => {
    if (!comp?.equity?.length) return null;
    const fig: PlotlyFigure = {
      data: [
        { type: 'scatter', x: backtest.dates, y: comp.equity, name: label, mode: 'lines', line: { color, width: 2 } },
        { type: 'scatter', x: backtest.dates, y: backtest.benchmark_equity, name: '50/50 Bench', mode: 'lines', line: { color: '#a1a1aa', width: 1.5, dash: 'dot' } },
      ],
      layout: { yaxis: { ...YAXIS_BASE, title: 'Cum. Return (%)', ticksuffix: '%', titlefont: { size: 10 } }, xaxis: XAXIS_DATE, hovermode: 'x unified', legend: { orientation: 'h', y: 1.08, font: { size: 9 } }, margin: CHART_M },
    };
    return themed(fig, theme);
  }, [backtest, comp, label, color, theme]);

  if (!comp?.equity?.length) return null;
  const s = comp.stats;

  return (
    <div className="space-y-3">
      <div className="panel-card p-2">
        <SectionTitle info={`Backtest of the ${label.toLowerCase()} signal in isolation vs a constant 50% equity benchmark. Includes 10bps transaction costs.`}>{label} Backtest</SectionTitle>
        <ChartBox chart={chart} height={200} />
      </div>
      {s && s.ann_return !== undefined && (
        <div className="panel-card px-3 py-2">
          <table className="w-full text-[11px]">
            <thead><tr className="border-b border-border/40">
              <th className="text-left py-1 pr-3 text-[9px] font-mono uppercase text-muted-foreground/50">Metric</th>
              <th className="text-right py-1 px-1.5 text-[9px] font-mono uppercase text-muted-foreground/50">Value</th>
            </tr></thead>
            <tbody>
              <StatsRow label="Ann. Return" values={[`${fmt(s.ann_return ?? 0, 1)}%`]} />
              <StatsRow label="Ann. Vol" values={[`${fmt(s.ann_vol ?? 0, 1)}%`]} />
              <StatsRow label="Sharpe" values={[fmt(s.sharpe ?? 0)]} />
              <StatsRow label="Max DD" values={[<span key="dd" className="text-rose-500">{fmt(s.max_dd ?? 0, 1)}%</span>]} />
              <StatsRow label="Info Ratio" values={[fmt(s.info_ratio ?? 0)]} />
              <StatsRow label="Turnover" values={[`${fmt(s.ann_turnover ?? 0, 0)}%`]} />
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/** Horizontal bar waterfall for indicator z-scores. */
function IndicatorWaterfall({ indicators, theme, title, info }: {
  indicators: Indicator[]; theme: 'light' | 'dark'; title: string; info: string;
}) {
  const chart = useMemo(() => {
    if (!indicators.length) return null;
    const sorted = [...indicators].sort((a, b) => b.z - a.z);
    const fig: PlotlyFigure = {
      data: [{
        type: 'bar', y: sorted.map(i => i.name), x: sorted.map(i => i.z),
        orientation: 'h', marker: { color: sorted.map(i => zColor(i.z)) },
        hovertemplate: '%{y}: z=%{x:.2f}<extra></extra>',
      }],
      layout: { xaxis: { ...XAXIS_DATE, type: 'linear' as any, zeroline: true, title: 'Z-Score', titlefont: { size: 10 } }, yaxis: { ...YAXIS_BASE, automargin: true, showgrid: false }, margin: CHART_M_HBAR },
    };
    return themed(fig, theme);
  }, [indicators, theme]);

  if (!indicators.length) return null;
  return (
    <div className="panel-card p-2">
      <SectionTitle info={info}>{title} ({indicators.length})</SectionTitle>
      <ChartBox chart={chart} height={Math.max(200, indicators.length * 22 + 50)} />
    </div>
  );
}

// ─── Tab: Overview ──────────────────────────────────────────────────────────

function OverviewTab({ snapshot, timeseries, tsLoading, backtest, btLoading, target }: {
  snapshot: Snapshot; timeseries: TimeseriesData | null; tsLoading: boolean;
  backtest: BacktestData | null; btLoading: boolean; target: string;
}) {
  const { theme } = useTheme();
  const { current, projections, indicator_counts, regime_stats } = snapshot;

  const compositeChart = useMemo(() => {
    if (!timeseries) return null;
    const fig: PlotlyFigure = {
      data: [
        { type: 'scatter', x: timeseries.dates, y: timeseries.growth, name: 'Growth', mode: 'lines', line: { color: '#3fb950', width: 1.5 } },
        { type: 'scatter', x: timeseries.dates, y: timeseries.inflation, name: 'Inflation', mode: 'lines', line: { color: '#f85149', width: 1.5 } },
        { type: 'scatter', x: timeseries.dates, y: timeseries.liquidity, name: 'Liquidity', mode: 'lines', line: { color: '#38bdf8', width: 1.5 } },
        { type: 'scatter', x: timeseries.dates, y: timeseries.tactical, name: 'Tactical', mode: 'lines', line: { color: '#d29922', width: 1.5 } },
      ],
      layout: { yaxis: { ...YAXIS_BASE, title: 'Z-Score', titlefont: { size: 10 } }, xaxis: XAXIS_DATE, hovermode: 'x unified', legend: { orientation: 'h', y: 1.08, font: { size: 9 } }, margin: CHART_M },
    };
    return themed(fig, theme);
  }, [timeseries, theme]);

  const equityCurveChart = useMemo(() => {
    if (!backtest) return null;
    const fig: PlotlyFigure = {
      data: [
        { type: 'scatter', x: backtest.dates, y: backtest.strategy_equity, name: 'Combined', mode: 'lines', line: { color: '#3fb950', width: 2 } },
        { type: 'scatter', x: backtest.dates, y: backtest.benchmark_equity, name: '50/50 Bench', mode: 'lines', line: { color: '#a1a1aa', width: 1.5, dash: 'dot' } },
        { type: 'scatter', x: backtest.dates, y: backtest.full_equity, name: `100% ${target}`, mode: 'lines', line: { color: '#38bdf8', width: 1.5, dash: 'dash' } },
      ],
      layout: { yaxis: { ...YAXIS_BASE, title: 'Cum. Return (%)', ticksuffix: '%', titlefont: { size: 10 } }, xaxis: XAXIS_DATE, hovermode: 'x unified', legend: { orientation: 'h', y: 1.08, font: { size: 9 } }, margin: CHART_M },
    };
    return themed(fig, theme);
  }, [backtest, target, theme]);

  return (
    <div className="space-y-3">
      {/* Regime bar */}
      <div className="panel-card px-3 py-2.5">
        <div className="flex items-center mb-1">
          <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground/50">Regime Probabilities</span>
          <InfoTooltip text="Current probability distribution across four macro regimes (Growth x Inflation quadrants). Computed via softmax distance to regime centroids in z-score space." />
        </div>
        <RegimeProbBar probs={current.regime_probs} />
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-4 sm:grid-cols-8 gap-1.5">
        {[
          { l: 'Regime', v: current.regime, t: 'Dominant Growth x Inflation quadrant based on highest probability.' },
          { l: 'Confidence', v: fmtPct(current.confidence), t: 'Probability assigned to the dominant regime. Higher = stronger conviction.' },
          { l: 'Phase', v: current.liq_phase, t: 'Liquidity cycle phase: Spring (recovering), Summer (peak), Fall (tightening), Winter (trough).' },
          { l: 'Allocation', v: fmtPct(current.allocation), t: 'Recommended equity allocation weight from the three-horizon blended model.' },
          { l: 'Growth', v: fmt(current.growth), c: current.growth >= 0 ? 'text-emerald-500' : 'text-rose-500', t: 'Growth composite z-score. Positive = expansion, negative = contraction.' },
          { l: 'Inflation', v: fmt(current.inflation), c: current.inflation <= 0 ? 'text-emerald-500' : 'text-rose-500', t: 'Inflation composite z-score. Negative (green) = disinflation, positive (red) = rising prices.' },
          { l: 'Liquidity', v: fmt(current.liquidity), c: current.liquidity >= 0 ? 'text-emerald-500' : 'text-rose-500', t: 'Global liquidity composite z-score. Positive = accommodative, negative = restrictive.' },
          { l: 'Tactical', v: fmt(current.tactical), c: current.tactical >= 0 ? 'text-emerald-500' : 'text-rose-500', t: 'Short-term positioning score. Positive = oversold/bullish setup, negative = overbought.' },
        ].map(m => (
          <div key={m.l} className="panel-card px-2 py-1.5">
            <div className="text-[8px] font-mono uppercase tracking-wider text-muted-foreground/50 flex items-center">
              {m.l}
              <InfoTooltip text={m.t} />
            </div>
            <div className={`text-[13px] font-mono font-semibold tabular-nums ${m.c ?? 'text-foreground'}`}>{m.v}</div>
          </div>
        ))}
      </div>

      {/* Composites chart + tables */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
        <div className="lg:col-span-3 panel-card p-2">
          <SectionTitle info="Historical z-score composites for all four signal axes. Each composite is the equal-weighted mean of its underlying indicators, smoothed with a 4-week EMA.">Composite Signals</SectionTitle>
          {tsLoading ? <LoadingSpinner /> : <ChartBox chart={compositeChart} height={220} />}
        </div>
        <div className="lg:col-span-2 space-y-3">
          <div className="panel-card px-3 py-2">
            <SectionTitle info="Projected regime probabilities using the empirical transition matrix. Shows how current regime probabilities evolve over 1, 3, and 6 month horizons.">Forward Projections</SectionTitle>
            <table className="w-full text-[11px]">
              <thead><tr className="border-b border-border/40">
                <th className="text-left py-1 pr-2 text-[9px] font-mono uppercase text-muted-foreground/50">Horizon</th>
                {REGIME_ORDER.map(r => <th key={r} className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">{r.slice(0, 4)}</th>)}
              </tr></thead>
              <tbody>
                {Object.entries(projections).map(([h, probs]) => (
                  <tr key={h} className="border-b border-border/20">
                    <td className="py-1 pr-2 font-medium text-foreground">{h}</td>
                    {REGIME_ORDER.map(r => <td key={r} className="text-right py-1 px-1 font-mono tabular-nums text-foreground">{fmtPct(probs[r] ?? 0)}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="panel-card px-3 py-2">
            <SectionTitle info="Historical forward returns observed when each regime was dominant. Based on 13-week forward log returns.">Regime Fwd Returns</SectionTitle>
            <table className="w-full text-[11px]">
              <thead><tr className="border-b border-border/40">
                <th className="text-left py-1 pr-2 text-[9px] font-mono uppercase text-muted-foreground/50">Regime</th>
                <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Mean</th>
                <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Sharpe</th>
                <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">%Pos</th>
              </tr></thead>
              <tbody>
                {regime_stats.map(s => (
                  <StatsRow key={s.regime} label={s.regime} color={REGIME_COLORS[s.regime]}
                    values={[`${fmt(s.mean_fwd_ret, 1)}%`, fmt(s.sharpe), `${fmt(s.pct_positive, 0)}%`]} />
                ))}
              </tbody>
            </table>
          </div>
          <div className="panel-card px-3 py-2">
            <SectionTitle info="Number of active indicators per axis after quality filters.">Indicator Coverage</SectionTitle>
            <div className="grid grid-cols-4 gap-2 text-center text-[11px]">
              {Object.entries(indicator_counts).map(([axis, count]) => (
                <div key={axis}>
                  <div className="text-[9px] font-mono uppercase text-muted-foreground/50">{axis}</div>
                  <div className="font-mono font-semibold text-foreground">{count}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Combined backtest */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
        <div className="lg:col-span-3 panel-card p-2">
          <SectionTitle info="Cumulative log return of the three-horizon blended strategy vs constant 50/50 benchmark and 100% buy-and-hold. Includes 10bps transaction costs.">Combined Strategy Backtest</SectionTitle>
          {btLoading ? <LoadingSpinner /> : <ChartBox chart={equityCurveChart} height={220} />}
        </div>
        {backtest && (
          <div className="lg:col-span-2 panel-card px-3 py-2">
            <SectionTitle info="Annualized performance metrics. IR = excess return over 50/50 benchmark / tracking error.">Performance</SectionTitle>
            <table className="w-full text-[11px]">
              <thead><tr className="border-b border-border/40">
                <th className="text-left py-1 pr-3 text-[9px] font-mono uppercase text-muted-foreground/50">Strategy</th>
                <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Return</th>
                <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Sharpe</th>
                <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Max DD</th>
                <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">IR</th>
              </tr></thead>
              <tbody>
                {backtest.stats.map((s, i) => (
                  <StatsRow key={i} label={s.label} values={[
                    `${fmt(s.ann_return, 1)}%`, fmt(s.sharpe),
                    <span key="dd" className="text-rose-500">{fmt(s.max_dd, 1)}%</span>,
                    fmt(s.info_ratio),
                  ]} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Tab: Regime (Growth x Inflation) ───────────────────────────────────────

function RegimeTab({ snapshot, timeseries, tsLoading, backtest, btLoading, target }: {
  snapshot: Snapshot; timeseries: TimeseriesData | null; tsLoading: boolean;
  backtest: BacktestData | null; btLoading: boolean; target: string;
}) {
  const { theme } = useTheme();

  const regimeProbsChart = useMemo(() => {
    if (!timeseries) return null;
    const fig: PlotlyFigure = {
      data: REGIME_ORDER.map(r => ({
        type: 'scatter' as const, x: timeseries.dates, y: timeseries.regime_probs[r],
        name: r, mode: 'lines' as const, stackgroup: 'one',
        line: { color: REGIME_COLORS[r], width: 0 }, fillcolor: REGIME_COLORS[r],
        hovertemplate: `${r}: %{y:.1%}<extra></extra>`,
      })),
      layout: { yaxis: { ...YAXIS_BASE, tickformat: '.0%', range: [0, 1] }, xaxis: XAXIS_DATE, hovermode: 'x unified', legend: { orientation: 'h', y: 1.08, font: { size: 9 } }, margin: CHART_M },
    };
    return themed(fig, theme);
  }, [timeseries, theme]);

  const compositeChart = useMemo(() => {
    if (!timeseries) return null;
    const fig: PlotlyFigure = {
      data: [
        { type: 'scatter', x: timeseries.dates, y: timeseries.growth, name: 'Growth', mode: 'lines', line: { color: '#3fb950', width: 2 } },
        { type: 'scatter', x: timeseries.dates, y: timeseries.inflation, name: 'Inflation', mode: 'lines', line: { color: '#f85149', width: 2 } },
      ],
      layout: { yaxis: { ...YAXIS_BASE, title: 'Z-Score', titlefont: { size: 10 } }, xaxis: XAXIS_DATE, hovermode: 'x unified', legend: { orientation: 'h', y: 1.08, font: { size: 9 } }, margin: CHART_M },
    };
    return themed(fig, theme);
  }, [timeseries, theme]);

  const transitionChart = useMemo(() => {
    const tm = snapshot.transition_matrix;
    if (!tm) return null;
    const fig: PlotlyFigure = {
      data: [{
        type: 'heatmap' as const, z: tm.values, x: tm.labels, y: tm.labels,
        colorscale: [[0, 'rgba(56,189,248,0.05)'], [0.5, 'rgba(56,189,248,0.4)'], [1, 'rgba(56,189,248,0.9)']],
        text: tm.values.map(row => row.map(v => `${(v * 100).toFixed(0)}%`)),
        texttemplate: '%{text}', textfont: { size: 11 },
        hovertemplate: '%{y}→%{x}: %{z:.1%}<extra></extra>', showscale: false,
      }],
      layout: { xaxis: { title: 'To', type: 'category', side: 'bottom', titlefont: { size: 10 }, showticklabels: true }, yaxis: { title: 'From', type: 'category', autorange: 'reversed', titlefont: { size: 10 }, showticklabels: true }, margin: { l: 80, r: 12, t: 12, b: 44 } },
    };
    return themed(fig, theme);
  }, [snapshot, theme]);

  const growthInds = snapshot.indicators?.growth ?? [];
  const inflationInds = snapshot.indicators?.inflation ?? [];

  return (
    <div className="space-y-3">
      <div className="panel-card px-3 py-2">
        <RegimeProbBar probs={snapshot.current.regime_probs} />
      </div>

      {/* Regime probs over time + Growth/Inflation composites */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div className="panel-card p-2">
          <SectionTitle info="Stacked area chart of regime probabilities over time. Shows how the dominant regime shifts.">Regime Probabilities</SectionTitle>
          {tsLoading ? <LoadingSpinner /> : <ChartBox chart={regimeProbsChart} height={240} />}
        </div>
        <div className="panel-card p-2">
          <SectionTitle info="Growth and inflation composite z-scores — the two axes that determine the macro regime quadrant.">Growth x Inflation</SectionTitle>
          {tsLoading ? <LoadingSpinner /> : <ChartBox chart={compositeChart} height={240} />}
        </div>
      </div>

      {/* Transition matrix + forward returns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div className="panel-card p-2">
          <SectionTitle info="Empirical regime transition probabilities. Each row shows the probability of transitioning from one regime to another in a given week.">Transition Matrix</SectionTitle>
          <ChartBox chart={transitionChart} height={220} />
        </div>
        <div className="panel-card px-3 py-2">
          <SectionTitle info="Historical 13-week forward returns by dominant regime. Mean, median, volatility, Sharpe, hit rate, and sample size.">Forward Returns by Regime</SectionTitle>
          <table className="w-full text-[11px]">
            <thead><tr className="border-b border-border/40">
              <th className="text-left py-1 pr-2 text-[9px] font-mono uppercase text-muted-foreground/50">Regime</th>
              <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Mean</th>
              <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Med</th>
              <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Vol</th>
              <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Sharpe</th>
              <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">%Pos</th>
              <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">N</th>
            </tr></thead>
            <tbody>
              {snapshot.regime_stats.map(s => (
                <StatsRow key={s.regime} label={s.regime} color={REGIME_COLORS[s.regime]}
                  values={[`${fmt(s.mean_fwd_ret, 1)}%`, `${fmt(s.median_fwd_ret, 1)}%`, `${fmt(s.std, 1)}%`, fmt(s.sharpe), `${fmt(s.pct_positive, 0)}%`, s.n]} />
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Growth + Inflation indicator waterfalls */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <IndicatorWaterfall indicators={growthInds} theme={theme} title="Growth Indicators"
          info="Individual growth indicator z-scores. Positive = expansion. Includes PMI breadth, OECD CLIs, ISM, exports, earnings revisions." />
        <IndicatorWaterfall indicators={inflationInds} theme={theme} title="Inflation Indicators"
          info="Individual inflation indicator z-scores. Positive = rising price pressures. Includes CPI, breakevens, commodity prices." />
      </div>

      {/* Regime-only backtest */}
      {backtest && !btLoading && (
        <ComponentBacktest backtest={backtest} componentKey="regime_only" label="Regime" color="#3fb950" target={target} theme={theme} />
      )}
      {btLoading && <LoadingSpinner label="Loading backtest" />}
    </div>
  );
}

// ─── Tab: Liquidity ─────────────────────────────────────────────────────────

function LiquidityTab({ snapshot, timeseries, tsLoading, backtest, btLoading, target }: {
  snapshot: Snapshot; timeseries: TimeseriesData | null; tsLoading: boolean;
  backtest: BacktestData | null; btLoading: boolean; target: string;
}) {
  const { theme } = useTheme();

  const liquidityChart = useMemo(() => {
    if (!timeseries) return null;
    const shapes: any[] = [];
    let phaseStart = 0;
    for (let i = 1; i <= timeseries.dates.length; i++) {
      if (i === timeseries.dates.length || timeseries.liq_phase[i] !== timeseries.liq_phase[phaseStart]) {
        const phase = timeseries.liq_phase[phaseStart];
        shapes.push({
          type: 'rect', xref: 'x', yref: 'paper',
          x0: timeseries.dates[phaseStart], x1: timeseries.dates[i - 1],
          y0: 0, y1: 1, fillcolor: (PHASE_COLORS[phase] ?? '#888') + '15', line: { width: 0 }, layer: 'below',
        });
        phaseStart = i;
      }
    }
    const fig: PlotlyFigure = {
      data: [{
        type: 'scatter', x: timeseries.dates, y: timeseries.liquidity,
        name: 'Liquidity', mode: 'lines', line: { color: '#38bdf8', width: 2 },
        hovertemplate: '%{x|%Y-%m-%d}: %{y:.2f}<extra></extra>',
      }],
      layout: { yaxis: { ...YAXIS_BASE, title: 'Z-Score', titlefont: { size: 10 } }, xaxis: XAXIS_DATE, shapes, margin: CHART_M },
    };
    return themed(fig, theme);
  }, [timeseries, theme]);

  const phaseStats = snapshot.liq_phase_stats ?? [];
  const liqInds = snapshot.indicators?.liquidity ?? [];

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
        <div className="lg:col-span-3 panel-card p-2">
          <SectionTitle info="Liquidity composite z-score with cycle phase backgrounds. Spring (green) = recovering, Summer (yellow) = peak, Fall (red) = tightening, Winter (purple) = trough.">Liquidity Cycle</SectionTitle>
          {tsLoading ? <LoadingSpinner /> : <ChartBox chart={liquidityChart} height={240} />}
        </div>
        <div className="lg:col-span-2 space-y-3">
          {timeseries && (
            <div className="panel-card px-3 py-2">
              <SectionTitle info="Historical time spent in each cycle phase. Based on level (above/below zero) and momentum (rising/falling).">Phase Distribution</SectionTitle>
              <div className="grid grid-cols-4 gap-2 text-center">
                {(['Spring', 'Summer', 'Fall', 'Winter'] as const).map(phase => {
                  const count = timeseries.liq_phase.filter(p => p === phase).length;
                  const pct = count / timeseries.liq_phase.length;
                  return (
                    <div key={phase}>
                      <div className="flex items-center justify-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: PHASE_COLORS[phase] }} />
                        <span className="text-[10px] text-muted-foreground">{phase}</span>
                      </div>
                      <div className="text-[14px] font-mono font-semibold tabular-nums text-foreground">{fmtPct(pct)}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          {phaseStats.length > 0 && (
            <div className="panel-card px-3 py-2">
              <SectionTitle info="Historical 13-week forward returns by liquidity phase for the target index.">Phase Forward Returns</SectionTitle>
              <table className="w-full text-[11px]">
                <thead><tr className="border-b border-border/40">
                  <th className="text-left py-1 pr-2 text-[9px] font-mono uppercase text-muted-foreground/50">Phase</th>
                  <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Mean</th>
                  <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Sharpe</th>
                  <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">%Pos</th>
                  <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">N</th>
                </tr></thead>
                <tbody>
                  {phaseStats.map(s => (
                    <StatsRow key={s.phase} label={s.phase} color={PHASE_COLORS[s.phase]}
                      values={[`${fmt(s.mean_fwd_ret, 1)}%`, fmt(s.sharpe), `${fmt(s.pct_positive, 0)}%`, s.n]} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <IndicatorWaterfall indicators={liqInds} theme={theme} title="Liquidity Indicators"
        info="Individual liquidity indicator z-scores. Includes Fed balance sheet, M2, credit impulse, yield curve, financial conditions." />

      {backtest && !btLoading && (
        <ComponentBacktest backtest={backtest} componentKey="liquidity_only" label="Liquidity" color="#38bdf8" target={target} theme={theme} />
      )}
      {btLoading && <LoadingSpinner label="Loading backtest" />}
    </div>
  );
}

// ─── Tab: Tactical ──────────────────────────────────────────────────────────

function TacticalTab({ snapshot, timeseries, tsLoading, backtest, btLoading, target }: {
  snapshot: Snapshot; timeseries: TimeseriesData | null; tsLoading: boolean;
  backtest: BacktestData | null; btLoading: boolean; target: string;
}) {
  const { theme } = useTheme();

  const tacticalChart = useMemo(() => {
    if (!timeseries) return null;
    const fig: PlotlyFigure = {
      data: [
        { type: 'scatter', x: timeseries.dates, y: timeseries.tactical, name: 'Tactical', mode: 'lines', line: { color: '#d29922', width: 2 } },
        { type: 'scatter', x: timeseries.dates, y: timeseries.allocation, name: 'Allocation', mode: 'lines', line: { color: '#38bdf8', width: 1.5, dash: 'dot' }, yaxis: 'y2' },
      ],
      layout: {
        yaxis: { ...YAXIS_BASE, title: 'Score', titlefont: { size: 10 } },
        yaxis2: { ...YAXIS_BASE, title: 'Alloc', overlaying: 'y', side: 'right', tickformat: '.0%', titlefont: { size: 10 }, showgrid: false },
        xaxis: XAXIS_DATE, hovermode: 'x unified', legend: { orientation: 'h', y: 1.08, font: { size: 9 } }, margin: CHART_M,
      },
    };
    return themed(fig, theme);
  }, [timeseries, theme]);

  const tacStats = snapshot.tactical_stats ?? [];
  const tacInds = snapshot.indicators?.tactical ?? [];

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
        <div className="lg:col-span-3 panel-card p-2">
          <SectionTitle info="Tactical composite z-score (solid) and the model's blended allocation weight (dotted). Contrarian indicators (VIX, put/call) fire bullish at market stress extremes.">Tactical Score & Allocation</SectionTitle>
          {tsLoading ? <LoadingSpinner /> : <ChartBox chart={tacticalChart} height={240} />}
        </div>
        <div className="lg:col-span-2 space-y-3">
          <div className="panel-card px-3 py-2">
            <SectionTitle info="Latest tactical composite score and the model's recommended equity allocation weight.">Current Reading</SectionTitle>
            <div className="grid grid-cols-2 gap-2 text-center">
              <div>
                <div className="text-[9px] font-mono uppercase text-muted-foreground/50">Score</div>
                <div className={`text-[16px] font-mono font-semibold ${snapshot.current.tactical >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>{fmt(snapshot.current.tactical)}</div>
              </div>
              <div>
                <div className="text-[9px] font-mono uppercase text-muted-foreground/50">Allocation</div>
                <div className="text-[16px] font-mono font-semibold text-foreground">{fmtPct(snapshot.current.allocation)}</div>
              </div>
            </div>
          </div>
          {tacStats.length > 0 && (
            <div className="panel-card px-3 py-2">
              <SectionTitle info="Historical 13-week forward returns bucketed by tactical score level. Extreme readings tend to be the most predictive.">Forward Returns by Score</SectionTitle>
              <table className="w-full text-[11px]">
                <thead><tr className="border-b border-border/40">
                  <th className="text-left py-1 pr-2 text-[9px] font-mono uppercase text-muted-foreground/50">Bucket</th>
                  <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Mean</th>
                  <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Sharpe</th>
                  <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">%Pos</th>
                  <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">N</th>
                </tr></thead>
                <tbody>
                  {tacStats.map(s => (
                    <StatsRow key={s.bucket} label={s.bucket} color={TACTICAL_COLORS[s.bucket]}
                      values={[`${fmt(s.mean_fwd_ret, 1)}%`, fmt(s.sharpe), `${fmt(s.pct_positive, 0)}%`, s.n]} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <IndicatorWaterfall indicators={tacInds} theme={theme} title="Tactical Indicators"
        info="Short-term positioning indicators. Contrarian signals (VIX, put/call) are NOT inverted — high fear readings = bullish. Credit stress indicators (HY spread, FCI) are inverted." />

      {backtest && !btLoading && (
        <ComponentBacktest backtest={backtest} componentKey="tactical_only" label="Tactical" color="#d29922" target={target} theme={theme} />
      )}
      {btLoading && <LoadingSpinner label="Loading backtest" />}
    </div>
  );
}

// ─── Main Page ──────────────────────────────────────────────────────────────

export default function MacroPage() {
  useEffect(() => { document.title = 'Macro Outlook | Investment-X'; }, []);

  const { theme } = useTheme();
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [selectedTarget, setSelectedTarget] = useState<string>('');

  const targetsQuery = useQuery({
    queryKey: ['macro-targets'],
    queryFn: () => apiFetchJson<{ targets: Target[] }>('/api/macro/targets'),
    staleTime: 300_000,
  });

  useEffect(() => {
    if (targetsQuery.data?.targets?.length && !selectedTarget) {
      setSelectedTarget(targetsQuery.data.targets[0].name);
    }
  }, [targetsQuery.data, selectedTarget]);

  const outlookQuery = useQuery({
    queryKey: ['macro-outlook', selectedTarget],
    queryFn: () => apiFetchJson<{ target_name: string; computed_at: string; snapshot: Snapshot }>(
      `/api/macro/outlook?target=${encodeURIComponent(selectedTarget)}`
    ),
    enabled: !!selectedTarget,
    staleTime: 120_000,
  });

  const timeseriesQuery = useQuery({
    queryKey: ['macro-timeseries', selectedTarget],
    queryFn: () => apiFetchJson<{ target_name: string; timeseries: TimeseriesData }>(
      `/api/macro/timeseries?target=${encodeURIComponent(selectedTarget)}`
    ),
    enabled: !!selectedTarget,
    staleTime: 120_000,
  });

  const backtestQuery = useQuery({
    queryKey: ['macro-backtest', selectedTarget],
    queryFn: () => apiFetchJson<{ target_name: string; backtest: BacktestData }>(
      `/api/macro/backtest?target=${encodeURIComponent(selectedTarget)}`
    ),
    enabled: !!selectedTarget,
    staleTime: 120_000,
  });

  const snapshot = outlookQuery.data?.snapshot ?? null;
  const timeseries = timeseriesQuery.data?.timeseries ?? null;
  const backtest = backtestQuery.data?.backtest ?? null;

  const isInitialLoading =
    targetsQuery.isLoading ||
    (!selectedTarget && !targetsQuery.isError) ||
    (!!selectedTarget && outlookQuery.isLoading);

  return (
    <AppShell>
      <div className="max-w-[1600px] mx-auto px-3 sm:px-4 lg:px-6 py-3">

        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2 mb-3">
          <h1 className="text-[16px] font-semibold text-foreground tracking-tight">Macro Outlook</h1>
          <div className="flex items-center gap-2 flex-wrap">
            <select
              value={selectedTarget}
              onChange={(e) => setSelectedTarget(e.target.value)}
              className="border border-border/50 rounded-lg px-2.5 py-1 text-[11px] focus:outline-none focus:border-sky-500/40 text-foreground cursor-pointer"
              style={{ colorScheme: theme === 'light' ? 'light' : 'dark', backgroundColor: 'rgb(var(--background))', color: 'rgb(var(--foreground))' }}
            >
              {(targetsQuery.data?.targets ?? []).map(t => (
                <option key={t.name} value={t.name}>{t.name} - {t.region}</option>
              ))}
            </select>

            {snapshot && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold border"
                style={{
                  backgroundColor: (REGIME_COLORS[snapshot.current.regime] ?? '#888') + '18',
                  borderColor: (REGIME_COLORS[snapshot.current.regime] ?? '#888') + '40',
                  color: REGIME_COLORS[snapshot.current.regime] ?? '#888',
                }}>
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: REGIME_COLORS[snapshot.current.regime] }} />
                {snapshot.current.regime}
              </span>
            )}

            {outlookQuery.data?.computed_at && (
              <span className="text-[9px] font-mono text-muted-foreground/50">
                {new Date(outlookQuery.data.computed_at).toLocaleString()}
              </span>
            )}
          </div>
        </div>

        {/* Tab navigation */}
        <div className="border-b border-border/40 mb-3">
          <div className="flex gap-0.5 overflow-x-auto no-scrollbar -mb-px">
            {TABS.map(tab => (
              <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                className={`whitespace-nowrap px-2.5 py-1.5 text-[11px] font-medium border-b-2 transition-all ${
                  activeTab === tab.key
                    ? 'text-foreground border-sky-500'
                    : 'text-muted-foreground border-transparent hover:text-foreground hover:border-foreground/20'
                }`}>
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tab content */}
        {isInitialLoading ? (
          <LoadingSpinner label="Loading macro data" />
        ) : targetsQuery.isError ? (
          <ErrorBox message="Failed to load targets." />
        ) : outlookQuery.isError ? (
          <ErrorBox message={`Failed to load data for ${selectedTarget}. ${(outlookQuery.error as any)?.message || ''}`} />
        ) : !snapshot ? (
          <ErrorBox message="No macro data available for this target." />
        ) : (
          <>
            {activeTab === 'overview' && <OverviewTab snapshot={snapshot} timeseries={timeseries} tsLoading={timeseriesQuery.isLoading} backtest={backtest} btLoading={backtestQuery.isLoading} target={selectedTarget} />}
            {activeTab === 'regime' && <RegimeTab snapshot={snapshot} timeseries={timeseries} tsLoading={timeseriesQuery.isLoading} backtest={backtest} btLoading={backtestQuery.isLoading} target={selectedTarget} />}
            {activeTab === 'liquidity' && <LiquidityTab snapshot={snapshot} timeseries={timeseries} tsLoading={timeseriesQuery.isLoading} backtest={backtest} btLoading={backtestQuery.isLoading} target={selectedTarget} />}
            {activeTab === 'tactical' && <TacticalTab snapshot={snapshot} timeseries={timeseries} tsLoading={timeseriesQuery.isLoading} backtest={backtest} btLoading={backtestQuery.isLoading} target={selectedTarget} />}
          </>
        )}
      </div>
    </AppShell>
  );
}
