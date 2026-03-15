'use client';

import { useMemo } from 'react';
import { useTheme } from '@/context/ThemeContext';
import type { PlotlyFigure } from '@/lib/chartTheme';
import type { RegimeStrategyBacktest } from './types';
import { STRAT_COLORS, STRAT_ORDER, XAXIS_DATE, YAXIS_BASE, CHART_M } from './constants';
import { fmt, fmtPct, themed } from './helpers';
import { LoadingSpinner, SectionTitle, ChartBox, StatsRow } from './SharedComponents';

const REGIME_COLORS_MAP: Record<string, string> = {
  'Risk-On': '#3fb950', 'Neutral': '#d29922', 'Risk-Off': '#f85149',
};

export default function StrategyTab({ backtest, isLoading, target }: {
  backtest: RegimeStrategyBacktest | null; isLoading: boolean; target: string;
}) {
  const { theme } = useTheme();

  const strategies = backtest?.strategies ?? {};
  const benchmark = backtest?.benchmark;
  const stratKeys = useMemo(() =>
    STRAT_ORDER.filter(k => k in strategies),
    [strategies],
  );

  // ── Derived metrics ──
  const bestStrat = useMemo(() => {
    if (!stratKeys.length) return null;
    return stratKeys.reduce((best, k) =>
      strategies[k].sharpe > strategies[best].sharpe ? k : best,
      stratKeys[0],
    );
  }, [stratKeys, strategies]);

  const bestAlpha = useMemo(() => {
    if (!stratKeys.length) return 0;
    return Math.max(...stratKeys.map(k => strategies[k].alpha));
  }, [stratKeys, strategies]);

  const beatingBenchmark = useMemo(() => {
    if (!benchmark || !stratKeys.length) return 0;
    return stratKeys.filter(k => strategies[k].sharpe > benchmark.sharpe).length;
  }, [stratKeys, strategies, benchmark]);

  // ── Cumulative returns chart ──
  const cumulativeChart = useMemo(() => {
    if (!stratKeys.length) return null;
    const first = strategies[stratKeys[0]];
    if (!first?.cumulative?.dates?.length) return null;

    const traces: any[] = stratKeys.map(k => ({
      type: 'scatter', x: strategies[k].cumulative.dates,
      y: strategies[k].cumulative.strategy,
      name: k, mode: 'lines',
      line: { color: STRAT_COLORS[k] ?? '#888', width: 1.5 },
    }));
    // Benchmark (dashed gray)
    traces.push({
      type: 'scatter', x: first.cumulative.dates,
      y: first.cumulative.benchmark,
      name: 'Benchmark', mode: 'lines',
      line: { color: '#a1a1aa', width: 1.5, dash: 'dash' },
    });
    // 100% index (dotted faint)
    traces.push({
      type: 'scatter', x: first.cumulative.dates,
      y: first.cumulative.index,
      name: '100% Index', mode: 'lines',
      line: { color: '#a1a1aa44', width: 1, dash: 'dot' },
    });

    const fig: PlotlyFigure = {
      data: traces,
      layout: {
        yaxis: { ...YAXIS_BASE, title: 'Cumulative Return', tickformat: '.0%', titlefont: { size: 10 } },
        xaxis: XAXIS_DATE,
        hovermode: 'x unified',
        legend: { orientation: 'h', y: 1.08, font: { size: 9 } },
        margin: CHART_M,
      },
    };
    return themed(fig, theme);
  }, [stratKeys, strategies, theme]);

  // ── Equity weight chart ──
  const eqWeightChart = useMemo(() => {
    if (!stratKeys.length) return null;
    const first = strategies[stratKeys[0]];
    if (!first?.eq_weight?.dates?.length) return null;

    const traces: any[] = stratKeys.map(k => ({
      type: 'scatter', x: strategies[k].eq_weight.dates,
      y: strategies[k].eq_weight.values.map((v: number) => v * 100),
      name: k, mode: 'lines',
      line: { color: STRAT_COLORS[k] ?? '#888', width: 1.5 },
    }));

    const fig: PlotlyFigure = {
      data: traces,
      layout: {
        yaxis: { ...YAXIS_BASE, title: 'Equity Weight (%)', range: [0, 100], titlefont: { size: 10 } },
        xaxis: XAXIS_DATE,
        hovermode: 'x unified',
        legend: { orientation: 'h', y: 1.08, font: { size: 9 } },
        margin: CHART_M,
        shapes: [{
          type: 'line', xref: 'paper', x0: 0, x1: 1,
          yref: 'y', y0: 50, y1: 50,
          line: { color: '#a1a1aa', width: 1, dash: 'dash' },
        }],
      },
    };
    return themed(fig, theme);
  }, [stratKeys, strategies, theme]);

  // ── Drawdown chart ──
  const drawdownChart = useMemo(() => {
    if (!stratKeys.length) return null;
    const first = strategies[stratKeys[0]];
    if (!first?.drawdown?.dates?.length) return null;

    const traces: any[] = stratKeys.map(k => ({
      type: 'scatter', x: strategies[k].drawdown.dates,
      y: strategies[k].drawdown.values.map((v: number) => v * 100),
      name: k, mode: 'lines',
      line: { color: STRAT_COLORS[k] ?? '#888', width: 1.5 },
      fill: 'tozeroy', fillcolor: (STRAT_COLORS[k] ?? '#888') + '10',
    }));

    const fig: PlotlyFigure = {
      data: traces,
      layout: {
        yaxis: { ...YAXIS_BASE, title: 'Drawdown (%)', titlefont: { size: 10 } },
        xaxis: XAXIS_DATE,
        hovermode: 'x unified',
        legend: { orientation: 'h', y: 1.08, font: { size: 9 } },
        margin: CHART_M,
      },
    };
    return themed(fig, theme);
  }, [stratKeys, strategies, theme]);

  // ── Rolling 1Y excess return chart ──
  const rollingExcessChart = useMemo(() => {
    if (!stratKeys.length) return null;
    const first = strategies[stratKeys[0]];
    if (!first?.rolling_excess?.dates?.length) return null;

    const traces: any[] = stratKeys.map(k => ({
      type: 'scatter', x: strategies[k].rolling_excess.dates,
      y: strategies[k].rolling_excess.values.map((v: number) => v * 100),
      name: k, mode: 'lines',
      line: { color: STRAT_COLORS[k] ?? '#888', width: 1.5 },
    }));

    const fig: PlotlyFigure = {
      data: traces,
      layout: {
        yaxis: { ...YAXIS_BASE, title: 'Rolling 1Y Excess (%)', titlefont: { size: 10 } },
        xaxis: XAXIS_DATE,
        hovermode: 'x unified',
        legend: { orientation: 'h', y: 1.08, font: { size: 9 } },
        margin: CHART_M,
        shapes: [{
          type: 'line', xref: 'paper', x0: 0, x1: 1,
          yref: 'y', y0: 0, y1: 0,
          line: { color: '#a1a1aa', width: 1, dash: 'dash' },
        }],
      },
    };
    return themed(fig, theme);
  }, [stratKeys, strategies, theme]);

  // ── Year-by-year alpha ──
  const yearlyAlphaData = useMemo(() => {
    if (!stratKeys.length) return { years: [] as string[], rows: [] as { year: string; alphas: Record<string, number> }[] };
    const allYears = new Set<string>();
    stratKeys.forEach(k => Object.keys(strategies[k].yearly_alpha ?? {}).forEach(y => allYears.add(y)));
    const years = Array.from(allYears).sort();
    const rows = years.map(y => ({
      year: y,
      alphas: Object.fromEntries(stratKeys.map(k => [k, strategies[k].yearly_alpha?.[y] ?? 0])),
    }));
    return { years, rows };
  }, [stratKeys, strategies]);

  // ── Regime history chart ──
  const regimeHistory = backtest?.regime_history ?? [];
  const regimeHistoryChart = useMemo(() => {
    if (!regimeHistory.length) return null;
    const dates = regimeHistory.map(r => r.date);
    const regimes = Array.from(new Set(regimeHistory.map(r => r.regime)));
    const traces: any[] = regimes.map(regime => {
      const y = regimeHistory.map(r => r.regime === regime ? 1 : null);
      return {
        type: 'bar', x: dates, y, name: regime,
        marker: { color: REGIME_COLORS_MAP[regime] ?? '#888' },
        hovertemplate: `${regime}<br>%{x}<extra></extra>`,
      };
    });

    const fig: PlotlyFigure = {
      data: traces,
      layout: {
        barmode: 'stack',
        yaxis: { ...YAXIS_BASE, showticklabels: false, showline: false, showgrid: false },
        xaxis: XAXIS_DATE,
        hovermode: 'x unified',
        legend: { orientation: 'h', y: 1.08, font: { size: 9 } },
        margin: CHART_M,
        bargap: 0,
      },
    };
    return themed(fig, theme);
  }, [regimeHistory, theme]);

  const regimeCounts = useMemo(() => {
    if (!regimeHistory.length) return [];
    const counts: Record<string, number> = {};
    regimeHistory.forEach(r => { counts[r.regime] = (counts[r.regime] ?? 0) + 1; });
    const total = regimeHistory.length;
    return Object.entries(counts).map(([regime, count]) => ({
      regime, count, pct: (count / total) * 100,
    }));
  }, [regimeHistory]);

  if (isLoading) return <LoadingSpinner label="Loading strategy backtest" />;
  if (!backtest) return null;

  return (
    <div className="space-y-3">
      {/* Summary metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
        <div className="panel-card px-2 py-1.5">
          <div className="stat-label">Best Strategy</div>
          <div className="text-[13px] font-mono font-semibold tabular-nums text-foreground">
            {bestStrat ?? '-'}
            {bestStrat && <span className="text-[10px] text-muted-foreground ml-1">({fmt(strategies[bestStrat].sharpe)} SR)</span>}
          </div>
        </div>
        <div className="panel-card px-2 py-1.5">
          <div className="stat-label">Benchmark Sharpe</div>
          <div className="text-[13px] font-mono font-semibold tabular-nums text-foreground">
            {benchmark ? fmt(benchmark.sharpe) : '-'}
          </div>
        </div>
        <div className="panel-card px-2 py-1.5">
          <div className="stat-label">Best Alpha</div>
          <div className={`text-[13px] font-mono font-semibold tabular-nums ${bestAlpha > 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
            {bestAlpha > 0 ? '+' : ''}{fmt(bestAlpha * 100, 1)}%/yr
          </div>
        </div>
        <div className="panel-card px-2 py-1.5">
          <div className="stat-label">Beating Benchmark</div>
          <div className="text-[13px] font-mono font-semibold tabular-nums text-foreground">
            {beatingBenchmark}/{stratKeys.length}
          </div>
        </div>
      </div>

      {/* Performance table */}
      <div className="panel-card px-3 py-2">
        <SectionTitle info="Annualized walk-forward backtest performance for each category strategy vs 50/50 benchmark. Alpha = ann. excess return.">Strategy Performance</SectionTitle>
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-border/40">
                <th className="text-left py-1 pr-3 text-[9px] font-mono uppercase text-muted-foreground/50">Strategy</th>
                <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Ann Ret</th>
                <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Sharpe</th>
                <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Max DD</th>
                <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">IR</th>
                <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Hit</th>
                <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Avg Wt</th>
                <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Alpha</th>
              </tr>
            </thead>
            <tbody>
              {stratKeys.map(k => {
                const s = strategies[k];
                return (
                  <StatsRow key={k} label={k} color={STRAT_COLORS[k]} values={[
                    `${fmt(s.ann_return * 100, 1)}%`,
                    fmt(s.sharpe),
                    <span key="dd" className="text-rose-500">{fmt(s.max_dd * 100, 1)}%</span>,
                    fmt(s.ir),
                    `${fmt(s.hit_rate * 100, 0)}%`,
                    `${fmt(s.avg_eq_wt * 100, 0)}%`,
                    <span key="a" className={s.alpha > 0 ? 'text-emerald-500' : 'text-rose-500'}>
                      {s.alpha > 0 ? '+' : ''}{fmt(s.alpha * 100, 1)}%
                    </span>,
                  ]} />
                );
              })}
              {benchmark && (
                <StatsRow label="Benchmark" values={[
                  `${fmt(benchmark.ann_return * 100, 1)}%`,
                  fmt(benchmark.sharpe),
                  <span key="dd" className="text-rose-500">{fmt(benchmark.max_dd * 100, 1)}%</span>,
                  '-', '-', '50%', '-',
                ]} />
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Cumulative returns */}
      <div className="panel-card p-2">
        <SectionTitle info="Cumulative returns for each category strategy vs 50/50 benchmark and 100% index. Walk-forward out-of-sample.">Cumulative Returns</SectionTitle>
        <ChartBox chart={cumulativeChart} height={400} />
      </div>

      {/* Equity weight + drawdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div className="panel-card p-2">
          <SectionTitle info="Equity allocation weight over time for each strategy. Dashed line = 50% benchmark weight.">Equity Weight</SectionTitle>
          <ChartBox chart={eqWeightChart} height={300} />
        </div>
        <div className="panel-card p-2">
          <SectionTitle info="Peak-to-trough drawdown for each strategy.">Drawdown</SectionTitle>
          <ChartBox chart={drawdownChart} height={300} />
        </div>
      </div>

      {/* Rolling excess */}
      <div className="panel-card p-2">
        <SectionTitle info="Rolling 1-year excess return (strategy minus benchmark). Above zero = outperformance.">Rolling 1Y Excess Return</SectionTitle>
        <ChartBox chart={rollingExcessChart} height={300} />
      </div>

      {/* Year-by-year alpha */}
      {yearlyAlphaData.rows.length > 0 && (
        <div className="panel-card px-3 py-2">
          <SectionTitle info="Year-by-year alpha (annualized excess return) for each strategy.">Yearly Alpha</SectionTitle>
          <div className="overflow-x-auto">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="border-b border-border/40">
                  <th className="text-left py-1 pr-3 text-[9px] font-mono uppercase text-muted-foreground/50">Year</th>
                  {stratKeys.map(k => (
                    <th key={k} className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">
                      <span className="inline-block w-2 h-2 rounded-full mr-1 align-middle" style={{ backgroundColor: STRAT_COLORS[k] }} />
                      {k.slice(0, 4)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {yearlyAlphaData.rows.map(row => (
                  <tr key={row.year} className="border-b border-border/20">
                    <td className="py-1 pr-3 font-medium text-foreground text-[11px] font-mono">{row.year}</td>
                    {stratKeys.map(k => {
                      const v = row.alphas[k] ?? 0;
                      return (
                        <td key={k} className={`text-right py-1 px-1 font-mono tabular-nums text-[11px] ${v > 0 ? 'text-emerald-500' : v < 0 ? 'text-rose-500' : 'text-foreground'}`}>
                          {v > 0 ? '+' : ''}{fmt(v * 100, 1)}%
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Regime history */}
      {regimeHistory.length > 0 && (
        <div className="space-y-3">
          <div className="panel-card p-2">
            <SectionTitle info="Historical regime classification from the walk-forward strategy engine.">Regime History</SectionTitle>
            <ChartBox chart={regimeHistoryChart} height={200} />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
            {regimeCounts.map(rc => (
              <div key={rc.regime} className="panel-card px-2 py-1.5">
                <div className="stat-label">{rc.regime}</div>
                <div className="text-[13px] font-mono font-semibold tabular-nums text-foreground">
                  <span className="inline-block w-2 h-2 rounded-full mr-1.5 align-middle" style={{ backgroundColor: REGIME_COLORS_MAP[rc.regime] ?? '#888' }} />
                  {rc.count} <span className="text-[10px] text-muted-foreground">({fmt(rc.pct, 0)}%)</span>
                </div>
              </div>
            ))}
          </div>

          {/* Recent 12 readings */}
          <div className="panel-card px-3 py-2">
            <SectionTitle info="Most recent 12 regime readings with growth/inflation percentiles and equity weight.">Recent Readings</SectionTitle>
            <div className="overflow-x-auto">
              <table className="w-full text-[11px]">
                <thead>
                  <tr className="border-b border-border/40">
                    <th className="text-left py-1 pr-3 text-[9px] font-mono uppercase text-muted-foreground/50">Date</th>
                    <th className="text-left py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Regime</th>
                    <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Growth %ile</th>
                    <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Infl %ile</th>
                    <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Eq Wt</th>
                  </tr>
                </thead>
                <tbody>
                  {regimeHistory.slice(-12).reverse().map(r => (
                    <tr key={r.date} className="border-b border-border/20">
                      <td className="py-1 pr-3 font-mono tabular-nums text-[11px] text-foreground">{r.date}</td>
                      <td className="py-1 px-1 text-[11px] text-foreground">
                        <span className="inline-block w-2 h-2 rounded-full mr-1 align-middle" style={{ backgroundColor: REGIME_COLORS_MAP[r.regime] ?? '#888' }} />
                        {r.regime}
                      </td>
                      <td className="text-right py-1 px-1 font-mono tabular-nums text-[11px] text-foreground">{fmt(r.growth_pctile * 100, 0)}%</td>
                      <td className="text-right py-1 px-1 font-mono tabular-nums text-[11px] text-foreground">{fmt(r.inflation_pctile * 100, 0)}%</td>
                      <td className="text-right py-1 px-1 font-mono tabular-nums text-[11px] text-foreground">{fmt(r.eq_weight * 100, 0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
