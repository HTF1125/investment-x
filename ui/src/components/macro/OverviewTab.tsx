'use client';

import { useMemo } from 'react';
import { useTheme } from '@/context/ThemeContext';
import type { PlotlyFigure } from '@/lib/chartTheme';
import type { Snapshot, TimeseriesData, BacktestData } from './types';
import { REGIME_ORDER, REGIME_COLORS, XAXIS_DATE, YAXIS_BASE, CHART_M } from './constants';
import { fmt, fmtPct, themed } from './helpers';
import { LoadingSpinner, InfoTooltip, RegimeProbBar, SectionTitle, ChartBox, StatsRow } from './SharedComponents';

export default function OverviewTab({ snapshot, timeseries, tsLoading, backtest, btLoading, target }: {
  snapshot: Snapshot; timeseries: TimeseriesData | null; tsLoading: boolean;
  backtest: BacktestData | null; btLoading: boolean; target: string;
}) {
  const { theme } = useTheme();
  const { current, projections, indicator_counts, regime_stats } = snapshot;

  const trendChart = useMemo(() => {
    if (!timeseries?.sma_40w?.length) return null;
    const shapes: any[] = [];
    const trend = timeseries.trend ?? [];
    if (trend.length) {
      let start = 0;
      for (let i = 1; i <= trend.length; i++) {
        if (i === trend.length || trend[i] !== trend[start]) {
          shapes.push({
            type: 'rect', xref: 'x', yref: 'paper',
            x0: timeseries.dates[start], x1: timeseries.dates[i - 1],
            y0: 0, y1: 1,
            fillcolor: trend[start] > 0.5 ? '#3fb95010' : '#f8514910',
            line: { width: 0 }, layer: 'below',
          });
          start = i;
        }
      }
    }
    const fig: PlotlyFigure = {
      data: [
        { type: 'scatter', x: timeseries.dates, y: timeseries.target_px, name: 'Price', mode: 'lines', line: { color: '#38bdf8', width: 1.5 } },
        { type: 'scatter', x: timeseries.dates, y: timeseries.sma_40w, name: '40W SMA', mode: 'lines', line: { color: '#d29922', width: 1.5, dash: 'dash' } },
      ],
      layout: { yaxis: { ...YAXIS_BASE, title: 'Price', titlefont: { size: 10 } }, xaxis: XAXIS_DATE, shapes, hovermode: 'x unified', legend: { orientation: 'h', y: 1.08, font: { size: 9 } }, margin: CHART_M },
    };
    return themed(fig, theme);
  }, [timeseries, theme]);

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
    const traces: any[] = [
      { type: 'scatter', x: backtest.dates, y: backtest.strategy_equity, name: 'Combined', mode: 'lines', line: { color: '#3fb950', width: 2 } },
      { type: 'scatter', x: backtest.dates, y: backtest.benchmark_equity, name: '50/50 Bench', mode: 'lines', line: { color: '#a1a1aa', width: 1.5, dash: 'dot' } },
    ];
    if (backtest.binary_strategy?.equity?.length) {
      traces.push({ type: 'scatter', x: backtest.dates, y: backtest.binary_strategy.equity, name: 'Binary (90/50/10)', mode: 'lines', line: { color: '#d29922', width: 2 } });
    }
    const fig: PlotlyFigure = {
      data: traces,
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
      <div className="grid grid-cols-5 sm:grid-cols-10 gap-1.5">
        {[
          { l: 'Regime', v: current.regime, t: 'Dominant Growth x Inflation quadrant based on highest probability.' },
          { l: 'Confidence', v: fmtPct(current.confidence), t: 'Probability assigned to the dominant regime. Higher = stronger conviction.' },
          { l: 'Phase', v: current.liq_phase, t: 'Liquidity cycle phase: Spring (recovering), Summer (peak), Fall (tightening), Winter (trough).' },
          { l: 'Trend', v: current.trend_bullish == null ? '-' : (current.trend_bullish ? 'Above' : 'Below'), c: current.trend_bullish ? 'text-emerald-500' : 'text-rose-500', t: 'Price vs 40-week SMA. Above = uptrend (bullish), Below = downtrend (bearish).' },
          { l: 'Allocation', v: fmtPct(current.allocation), t: 'Recommended equity allocation weight from the three-horizon blended model.' },
          { l: 'Binary', v: current.binary_allocation != null ? fmtPct(current.binary_allocation) : '-', c: (current.binary_allocation ?? 0.5) > 0.5 ? 'text-emerald-500' : (current.binary_allocation ?? 0.5) < 0.5 ? 'text-rose-500' : 'text-foreground', t: 'Binary regime allocation (90/50/10). Trend + macro → risk-on/neutral/risk-off.' },
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

      {/* Price + SMA trend */}
      {!tsLoading && trendChart && (
        <div className="panel-card p-2">
          <SectionTitle info="Target index price vs 40-week SMA. Green background = uptrend (price above SMA), red = downtrend. The trend signal is a key input to the binary regime allocation.">Price & 40W SMA Trend</SectionTitle>
          <ChartBox chart={trendChart} height={200} />
        </div>
      )}

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
            <SectionTitle info="Historical forward returns observed when each regime was dominant. Ann. = empirical annualized return for this specific index (used by continuous model).">Regime Fwd Returns</SectionTitle>
            <table className="w-full text-[11px]">
              <thead><tr className="border-b border-border/40">
                <th className="text-left py-1 pr-2 text-[9px] font-mono uppercase text-muted-foreground/50">Regime</th>
                <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Mean</th>
                <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Sharpe</th>
                <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Ann.</th>
              </tr></thead>
              <tbody>
                {regime_stats.map(s => {
                  const empRet = snapshot.empirical_regime_returns?.[s.regime];
                  return (
                    <StatsRow key={s.regime} label={s.regime} color={REGIME_COLORS[s.regime]}
                      values={[
                        `${fmt(s.mean_fwd_ret, 1)}%`, fmt(s.sharpe),
                        empRet != null ? `${fmt(empRet * 100, 1)}%` : '-',
                      ]} />
                  );
                })}
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
          <SectionTitle info="Cumulative log return of the three-horizon blended strategy vs constant 50/50 benchmark. Includes 10bps transaction costs.">Combined Strategy Backtest</SectionTitle>
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
                {backtest.binary_strategy?.stats?.ann_return !== undefined && (
                  <StatsRow label="Binary (90/50/10)" color="#d29922" values={[
                    `${fmt(backtest.binary_strategy.stats.ann_return ?? 0, 1)}%`,
                    fmt(backtest.binary_strategy.stats.sharpe ?? 0),
                    <span key="dd" className="text-rose-500">{fmt(backtest.binary_strategy.stats.max_dd ?? 0, 1)}%</span>,
                    fmt(backtest.binary_strategy.stats.info_ratio ?? 0),
                  ]} />
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
