'use client';

import { useMemo } from 'react';
import { useTheme } from '@/context/ThemeContext';
import type { PlotlyFigure } from '@/lib/chartTheme';
import type { Snapshot, TimeseriesData, BacktestData } from './types';
import { REGIME_ORDER, REGIME_COLORS, XAXIS_DATE, YAXIS_BASE, CHART_M } from './constants';
import { fmt, themed } from './helpers';
import { LoadingSpinner, RegimeProbBar, SectionTitle, ChartBox, StatsRow } from './SharedComponents';
import ComponentBacktest from './ComponentBacktest';
import IndicatorWaterfall from './IndicatorWaterfall';

export default function RegimeTab({ snapshot, timeseries, tsLoading, backtest, btLoading, target }: {
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
        colorscale: [[0, 'rgba(148,163,184,0.05)'], [0.5, 'rgba(148,163,184,0.4)'], [1, 'rgba(148,163,184,0.9)']],
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
          <table className="w-full text-[12.5px]">
            <thead><tr className="border-b border-border/40">
              <th className="text-left py-1 pr-2 text-[11px] font-mono uppercase text-muted-foreground/50">Regime</th>
              <th className="text-right py-1 px-1 text-[11px] font-mono uppercase text-muted-foreground/50">Mean</th>
              <th className="text-right py-1 px-1 text-[11px] font-mono uppercase text-muted-foreground/50">Med</th>
              <th className="text-right py-1 px-1 text-[11px] font-mono uppercase text-muted-foreground/50">Vol</th>
              <th className="text-right py-1 px-1 text-[11px] font-mono uppercase text-muted-foreground/50">Sharpe</th>
              <th className="text-right py-1 px-1 text-[11px] font-mono uppercase text-muted-foreground/50">%Pos</th>
              <th className="text-right py-1 px-1 text-[11px] font-mono uppercase text-muted-foreground/50">N</th>
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
