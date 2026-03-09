'use client';

import { useMemo } from 'react';
import type { PlotlyFigure } from '@/lib/chartTheme';
import type { BacktestData } from './types';
import { XAXIS_DATE, YAXIS_BASE, CHART_M } from './constants';
import { fmt, themed } from './helpers';
import { SectionTitle, ChartBox, StatsRow } from './SharedComponents';

/** Compact backtest section for embedding in each tab. */
export default function ComponentBacktest({ backtest, componentKey, label, color, target, theme }: {
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
