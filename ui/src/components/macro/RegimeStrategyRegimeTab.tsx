'use client';

import { useMemo } from 'react';
import { useTheme } from '@/context/ThemeContext';
import type { PlotlyFigure } from '@/lib/chartTheme';
import type { RegimeStrategyBacktest, RegimeHistoryEntry } from './types';
import {
  REGIME_COLORS,
  XAXIS_DATE, YAXIS_BASE, CHART_M, CHART_M_HBAR,
} from './constants';
import { fmt, themed } from './helpers';
import { LoadingSpinner, SectionTitle, ChartBox, StatsRow } from './SharedComponents';

// ─── Helpers ────────────────────────────────────────────────────────────────

interface DurationStat { regime: string; avg: number; min: number; max: number; runs: number }

function computeDurations(history: RegimeHistoryEntry[]): DurationStat[] {
  if (!history.length) return [];
  const runs: Record<string, number[]> = {};
  let cur = history[0].regime;
  let len = 1;
  for (let i = 1; i < history.length; i++) {
    if (history[i].regime === cur) {
      len++;
    } else {
      (runs[cur] ??= []).push(len);
      cur = history[i].regime;
      len = 1;
    }
  }
  (runs[cur] ??= []).push(len);

  return Object.entries(runs).map(([regime, lengths]) => ({
    regime,
    avg: lengths.reduce((a, b) => a + b, 0) / lengths.length,
    min: Math.min(...lengths),
    max: Math.max(...lengths),
    runs: lengths.length,
  }));
}

// ─── Component ──────────────────────────────────────────────────────────────

export default function RegimeStrategyRegimeTab({ backtest, isLoading, target }: {
  backtest: RegimeStrategyBacktest | null; isLoading: boolean; target: string;
}) {
  const { theme } = useTheme();
  const regimeHistory = backtest?.regime_history ?? [];
  const current = regimeHistory.length ? regimeHistory[regimeHistory.length - 1] : null;

  // ── Quadrant scatter ──
  const quadrantChart = useMemo(() => {
    if (!regimeHistory.length) return null;

    // Group points by regime for separate traces (enables legend toggling)
    const regimes = Array.from(new Set(regimeHistory.map(r => r.regime)));
    const lastPt = regimeHistory[regimeHistory.length - 1];

    const traces: any[] = regimes.map(regime => {
      const pts = regimeHistory.filter(r => r.regime === regime);
      return {
        type: 'scatter', mode: 'markers',
        x: pts.map(p => p.growth_pctile),
        y: pts.map(p => p.inflation_pctile),
        name: regime,
        marker: {
          color: REGIME_COLORS[regime] ?? '#888',
          size: 5, opacity: 0.5,
        },
        hovertemplate: `${regime}<br>Growth: %{x:.0%}<br>Inflation: %{y:.0%}<extra></extra>`,
      };
    });

    // Current point — highlighted
    traces.push({
      type: 'scatter', mode: 'markers',
      x: [lastPt.growth_pctile], y: [lastPt.inflation_pctile],
      name: 'Current',
      marker: {
        color: REGIME_COLORS[lastPt.regime] ?? '#888',
        size: 14, symbol: 'circle',
        line: { width: 2, color: theme === 'dark' ? '#fff' : '#000' },
      },
      hovertemplate: `CURRENT — ${lastPt.regime}<br>Growth: %{x:.0%}<br>Inflation: %{y:.0%}<extra></extra>`,
    });

    const fig: PlotlyFigure = {
      data: traces,
      layout: {
        xaxis: {
          title: 'Growth Percentile', titlefont: { size: 10 },
          range: [0, 1], tickformat: '.0%',
          showticklabels: true, showline: true, linewidth: 1, showgrid: true,
        },
        yaxis: {
          title: 'Inflation Percentile', titlefont: { size: 10 },
          range: [0, 1], tickformat: '.0%',
          showticklabels: true, showline: true, linewidth: 1, showgrid: true,
        },
        hovermode: 'closest',
        legend: { orientation: 'h', y: 1.08, font: { size: 9 } },
        margin: { l: 52, r: 16, t: 28, b: 44 },
        shapes: [
          // Vertical midline
          { type: 'line', xref: 'x', yref: 'paper', x0: 0.5, x1: 0.5, y0: 0, y1: 1, line: { color: '#a1a1aa', width: 1, dash: 'dash' } },
          // Horizontal midline
          { type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: 0.5, y1: 0.5, line: { color: '#a1a1aa', width: 1, dash: 'dash' } },
        ],
        annotations: [
          { x: 0.85, y: 0.15, text: 'Goldilocks', showarrow: false, font: { size: 11, color: REGIME_COLORS['Goldilocks'] + '88' } },
          { x: 0.85, y: 0.85, text: 'Reflation', showarrow: false, font: { size: 11, color: REGIME_COLORS['Reflation'] + '88' } },
          { x: 0.15, y: 0.85, text: 'Stagflation', showarrow: false, font: { size: 11, color: REGIME_COLORS['Stagflation'] + '88' } },
          { x: 0.15, y: 0.15, text: 'Deflation', showarrow: false, font: { size: 11, color: REGIME_COLORS['Deflation'] + '88' } },
        ],
      },
    };
    return themed(fig, theme);
  }, [regimeHistory, theme]);

  // ── Timeline ──
  const timelineChart = useMemo(() => {
    if (!regimeHistory.length) return null;
    const dates = regimeHistory.map(r => r.date);
    const regimes = Array.from(new Set(regimeHistory.map(r => r.regime)));

    const traces: any[] = regimes.map(regime => ({
      type: 'bar', x: dates,
      y: regimeHistory.map(r => r.regime === regime ? 1 : null),
      name: regime,
      marker: { color: REGIME_COLORS[regime] ?? '#888' },
      hovertemplate: `${regime}<br>%{x}<extra></extra>`,
    }));

    const fig: PlotlyFigure = {
      data: traces,
      layout: {
        barmode: 'stack',
        yaxis: { ...YAXIS_BASE, showticklabels: false, showline: false, showgrid: false },
        xaxis: XAXIS_DATE,
        hovermode: 'x unified',
        legend: { orientation: 'h', y: 1.08, font: { size: 9 } },
        margin: CHART_M, bargap: 0,
      },
    };
    return themed(fig, theme);
  }, [regimeHistory, theme]);

  // ── Distribution bar ──
  const regimeCounts = useMemo(() => {
    if (!regimeHistory.length) return [];
    const counts: Record<string, number> = {};
    regimeHistory.forEach(r => { counts[r.regime] = (counts[r.regime] ?? 0) + 1; });
    const total = regimeHistory.length;
    return Object.entries(counts)
      .map(([regime, count]) => ({ regime, count, pct: (count / total) * 100 }))
      .sort((a, b) => b.count - a.count);
  }, [regimeHistory]);

  const distributionChart = useMemo(() => {
    if (!regimeCounts.length) return null;
    const fig: PlotlyFigure = {
      data: regimeCounts.map(rc => ({
        type: 'bar', orientation: 'h',
        x: [rc.pct], y: [rc.regime], name: rc.regime,
        marker: { color: REGIME_COLORS[rc.regime] ?? '#888' },
        text: [`${fmt(rc.pct, 0)}%`], textposition: 'auto',
        textfont: { size: 10 },
        hovertemplate: `${rc.regime}: ${rc.count} weeks (${fmt(rc.pct, 1)}%)<extra></extra>`,
        showlegend: false,
      })),
      layout: {
        barmode: 'stack',
        xaxis: { ...YAXIS_BASE, title: '% of Time', ticksuffix: '%', titlefont: { size: 10 } },
        yaxis: { type: 'category' as const, showticklabels: true, autorange: 'reversed' as const },
        margin: CHART_M_HBAR,
      },
    };
    return themed(fig, theme);
  }, [regimeCounts, theme]);

  // ── Duration analysis ──
  const durations = useMemo(() => computeDurations(regimeHistory), [regimeHistory]);

  // ── Stats per regime ──
  const regimeStats = useMemo(() => {
    if (!regimeHistory.length) return [];
    const groups: Record<string, RegimeHistoryEntry[]> = {};
    regimeHistory.forEach(r => { (groups[r.regime] ??= []).push(r); });
    const total = regimeHistory.length;
    return Object.entries(groups).map(([regime, entries]) => {
      const n = entries.length;
      return {
        regime, count: n,
        pct: (n / total) * 100,
        avgGrowth: entries.reduce((s, e) => s + e.growth_pctile, 0) / n,
        avgInflation: entries.reduce((s, e) => s + e.inflation_pctile, 0) / n,
        avgEqWt: entries.reduce((s, e) => s + e.eq_weight, 0) / n,
      };
    }).sort((a, b) => b.count - a.count);
  }, [regimeHistory]);

  if (isLoading) return <LoadingSpinner label="Loading regime data" />;
  if (!backtest) return null;

  return (
    <div className="space-y-3">

      {/* 1. Current Regime Card */}
      {current && (
        <div className="panel-card px-4 py-3 flex flex-wrap items-center gap-x-8 gap-y-2">
          <div>
            <div className="stat-label">Current Regime</div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="inline-block w-3 h-3 rounded-full" style={{ backgroundColor: REGIME_COLORS[current.regime] ?? '#888' }} />
              <span className="text-lg font-semibold text-foreground">{current.regime}</span>
            </div>
          </div>
          <div>
            <div className="stat-label">Equity Weight</div>
            <div className="text-lg font-mono font-semibold tabular-nums text-foreground mt-0.5">
              {fmt(current.eq_weight * 100, 0)}%
            </div>
          </div>
          <div>
            <div className="stat-label">Growth Percentile</div>
            <div className="text-[13px] font-mono tabular-nums text-foreground mt-0.5">
              {fmt(current.growth_pctile * 100, 0)}%
            </div>
          </div>
          <div>
            <div className="stat-label">Inflation Percentile</div>
            <div className="text-[13px] font-mono tabular-nums text-foreground mt-0.5">
              {fmt(current.inflation_pctile * 100, 0)}%
            </div>
          </div>
          <div>
            <div className="stat-label">As Of</div>
            <div className="text-[11px] font-mono text-muted-foreground mt-0.5">{current.date}</div>
          </div>
        </div>
      )}

      {/* 2. Quadrant Scatter */}
      <div className="panel-card p-2">
        <SectionTitle info="Growth vs inflation percentile for each rebalance period. Quadrants define the macro regime. Current position highlighted with a ring marker.">
          Growth x Inflation Quadrant
        </SectionTitle>
        <ChartBox chart={quadrantChart} height={380} />
      </div>

      {/* 3. Regime Timeline */}
      <div className="panel-card p-2">
        <SectionTitle info="Historical regime classification from the walk-forward strategy engine.">
          Regime Timeline
        </SectionTitle>
        <ChartBox chart={timelineChart} height={200} />
      </div>

      {/* 4. Distribution + Duration side-by-side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div className="panel-card p-2">
          <SectionTitle info="Percentage of time spent in each regime across the full backtest period.">
            Regime Distribution
          </SectionTitle>
          <ChartBox chart={distributionChart} height={180} />
        </div>
        <div className="panel-card px-3 py-2">
          <SectionTitle info="Consecutive-period duration analysis. Shows how long regimes persist on average (in rebalance periods).">
            Regime Duration
          </SectionTitle>
          <div className="overflow-x-auto">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="border-b border-border/40">
                  <th className="text-left py-1 pr-3 text-[9px] font-mono uppercase text-muted-foreground/50">Regime</th>
                  <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Runs</th>
                  <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Avg</th>
                  <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Min</th>
                  <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Max</th>
                </tr>
              </thead>
              <tbody>
                {durations.map(d => (
                  <StatsRow key={d.regime} label={d.regime} color={REGIME_COLORS[d.regime]}
                    values={[d.runs, fmt(d.avg, 1), d.min, d.max]} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* 5. Regime Statistics */}
      <div className="panel-card px-3 py-2">
        <SectionTitle info="Aggregate statistics per regime: frequency, average growth/inflation percentile, and average equity allocation weight.">
          Regime Statistics
        </SectionTitle>
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-border/40">
                <th className="text-left py-1 pr-3 text-[9px] font-mono uppercase text-muted-foreground/50">Regime</th>
                <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Count</th>
                <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Freq %</th>
                <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Avg Growth</th>
                <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Avg Infl</th>
                <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Avg Eq Wt</th>
              </tr>
            </thead>
            <tbody>
              {regimeStats.map(s => (
                <StatsRow key={s.regime} label={s.regime} color={REGIME_COLORS[s.regime]}
                  values={[
                    s.count,
                    `${fmt(s.pct, 1)}%`,
                    `${fmt(s.avgGrowth * 100, 0)}%`,
                    `${fmt(s.avgInflation * 100, 0)}%`,
                    `${fmt(s.avgEqWt * 100, 0)}%`,
                  ]} />
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 6. Recent Readings */}
      {regimeHistory.length > 0 && (
        <div className="panel-card px-3 py-2">
          <SectionTitle info="Most recent 12 regime readings with growth/inflation percentiles and equity weight.">
            Recent Readings
          </SectionTitle>
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
                      <span className="inline-block w-2 h-2 rounded-full mr-1 align-middle" style={{ backgroundColor: REGIME_COLORS[r.regime] ?? '#888' }} />
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
      )}
    </div>
  );
}
