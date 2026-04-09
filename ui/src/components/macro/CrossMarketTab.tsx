'use client';

import { useMemo } from 'react';
import { useTheme } from '@/context/ThemeContext';
import type { PlotlyFigure } from '@/lib/chartTheme';
import { STRAT_COLORS, CHART_M, YAXIS_BASE } from './constants';
import { themed } from './helpers';
import { SectionTitle, ChartBox } from './SharedComponents';

// ── Hard-coded research data (from reports/wf_backtest_all_indices.md) ──

const INDICES = ['ACWI', 'S&P 500', 'Nasdaq 100', 'DAX', 'Nikkei 225', 'KOSPI', 'Hang Seng', 'Shanghai Comp', 'Stoxx 50', 'FTSE 100'];

const SHARPE_DATA: Record<string, number[]> = {
  Growth:    [1.00, 0.72, 0.88, 0.55, 0.66, 0.82, 0.54, 0.52, 0.43, 0.01],
  Tactical:  [1.09, 0.60, 0.66, 0.42, 0.54, 0.80, 0.26, 0.57, 0.65, 0.01],
  Regime:    [0.77, 0.81, 0.80, 0.51, 0.52, 0.81, 0.43, 0.29, 0.48, 0.01],
  Benchmark: [0.69, 0.50, 0.63, 0.40, 0.36, 0.50, 0.26, 0.26, 0.39, 0.01],
};

const ALPHA_DATA: Record<string, number[]> = {
  Growth:    [3.0, 2.0, 3.1, 2.4, 3.0, 3.4, 3.4, 4.3, 1.5, -1.7],
  Inflation: [0.5, 1.3, 2.7, 0.6, 2.9, 1.6, 2.0, 5.4, 1.7, -0.7],
  Liquidity: [1.2, 1.4, 1.4, 0.5, 1.7, 3.1, 2.1, 3.0, -1.3, 0.7],
  Tactical:  [3.2, 1.4, 0.8, 0.8, 2.2, 3.0, 0.3, 3.5, 3.2, -0.5],
  Regime:    [2.4, 2.2, 2.4, 2.5, 2.4, 3.2, 2.5, 1.3, 2.3, -0.0],
};

const MH_INDICES = ['KOSPI', 'S&P 500', 'Nikkei 225', 'Euro Stoxx 50', 'MSCI EM', 'Shanghai Comp', 'DAX', 'FTSE 100', 'Hang Seng'];
const MH_HORIZONS = ['4w', '8w', '13w', '26w', '52w'];
const MH_ICS: Record<string, number[]> = {
  'KOSPI':         [0.233, 0.302, 0.354, 0.327, 0.223],
  'S&P 500':       [0.149, 0.199, 0.248, 0.235, 0.145],
  'Nikkei 225':    [0.172, 0.231, 0.273, 0.283, 0.208],
  'Euro Stoxx 50': [0.234, 0.309, 0.362, 0.348, 0.214],
  'MSCI EM':       [0.226, 0.290, 0.319, 0.318, 0.289],
  'Shanghai Comp': [0.207, 0.270, 0.287, 0.302, 0.277],
  'DAX':           [0.183, 0.237, 0.282, 0.291, 0.177],
  'FTSE 100':      [0.147, 0.211, 0.247, 0.212, 0.110],
  'Hang Seng':     [0.124, 0.168, 0.184, 0.184, 0.145],
};

const MH_COLORS = ['#3fb950', '#f85149', '#58a6ff', '#f0883e', '#bc8cff', '#39d2c0', '#d29922', '#8b949e', '#e6e6e6'];

const TOP_INDICATORS = [
  { name: 'CESI Breadth', category: 'Growth', ic: '+0.1776', direction: 'Bullish when rising' },
  { name: 'Global Trade', category: 'Growth', ic: '+0.1750', direction: 'Bullish when rising' },
  { name: 'CRB Index', category: 'Inflation', ic: '-0.1527', direction: 'Bullish when falling' },
  { name: 'OECD CLI EM', category: 'Growth', ic: '+0.1493', direction: 'Bullish when rising' },
  { name: '10Y Breakeven', category: 'Inflation', ic: '-0.1483', direction: 'Bullish when falling' },
  { name: 'HY/IG Ratio', category: 'Tactical', ic: '-0.1404', direction: 'Bullish when falling' },
  { name: 'US Sector Breadth', category: 'Tactical', ic: '-0.1300', direction: 'Bullish when falling' },
  { name: 'FCI US', category: 'Liquidity', ic: '+0.1104', direction: 'Bullish when rising (contrarian)' },
  { name: 'Inflation Surprise', category: 'Inflation', ic: '+0.0973', direction: 'Bullish when rising' },
  { name: 'ISM Mfg Momentum', category: 'Growth', ic: '+0.0846', direction: 'Bullish when rising' },
  { name: 'VIX', category: 'Tactical', ic: '+0.0804', direction: 'Bullish when rising (contrarian)' },
  { name: 'Fed Net Liquidity', category: 'Liquidity', ic: '+0.0788', direction: 'Bullish when rising' },
  { name: 'EPS Breadth', category: 'Growth', ic: '+0.0701', direction: 'Bullish when rising' },
  { name: 'ISM New Orders', category: 'Growth', ic: '+0.0672', direction: 'Bullish when rising' },
  { name: 'Cyclical/Defensive', category: 'Growth', ic: '+0.0654', direction: 'Bullish when rising' },
];

const SUMMARY_ROWS = [
  { strategy: 'Growth', sharpe: '0.61', alpha: '+2.4%/yr', beat: '9/10 (90%)' },
  { strategy: 'Tactical', sharpe: '0.56', alpha: '+1.8%/yr', beat: '9/10 (90%)' },
  { strategy: 'Regime', sharpe: '0.54', alpha: '+2.1%/yr', beat: '9/10 (90%)' },
  { strategy: 'Inflation', sharpe: '0.56', alpha: '+1.8%/yr', beat: '9/10 (90%)' },
  { strategy: 'Liquidity', sharpe: '0.50', alpha: '+1.4%/yr', beat: '9/10 (90%)' },
  { strategy: '50% Benchmark', sharpe: '0.40', alpha: '-', beat: '-' },
];

export default function CrossMarketTab() {
  const { theme } = useTheme();

  // Sharpe heatmap
  const sharpeChart = useMemo((): PlotlyFigure => {
    const strats = ['Growth', 'Tactical', 'Regime', 'Benchmark'];
    const fig: PlotlyFigure = {
      data: [{
        type: 'heatmap',
        z: strats.map(s => SHARPE_DATA[s]),
        x: INDICES,
        y: strats,
        colorscale: 'RdYlGn',
        zmin: 0, zmax: 1.1,
        text: strats.map(s => SHARPE_DATA[s].map(v => v.toFixed(2))),
        texttemplate: '%{text}',
        textfont: { size: 11 },
        hovertemplate: '%{y} / %{x}: %{z:.2f}<extra></extra>',
      }],
      layout: {
        margin: { ...CHART_M, l: 80, b: 60 },
        xaxis: { tickangle: -45, showline: true, linewidth: 1 },
        yaxis: { autorange: 'reversed' as any, showline: true, linewidth: 1 },
      },
    };
    return themed(fig, theme);
  }, [theme]);

  // Alpha heatmap
  const alphaChart = useMemo((): PlotlyFigure => {
    const strats = ['Growth', 'Inflation', 'Liquidity', 'Tactical', 'Regime'];
    const fig: PlotlyFigure = {
      data: [{
        type: 'heatmap',
        z: strats.map(s => ALPHA_DATA[s]),
        x: INDICES,
        y: strats,
        colorscale: 'RdYlGn',
        zmid: 0, zmin: -2, zmax: 6,
        text: strats.map(s => ALPHA_DATA[s].map(v => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`)),
        texttemplate: '%{text}',
        textfont: { size: 10 },
        hovertemplate: '%{y} / %{x}: %{text}<extra></extra>',
      }],
      layout: {
        margin: { ...CHART_M, l: 80, b: 60 },
        xaxis: { tickangle: -45, showline: true, linewidth: 1 },
        yaxis: { autorange: 'reversed' as any, showline: true, linewidth: 1 },
      },
    };
    return themed(fig, theme);
  }, [theme]);

  // Multi-horizon IC chart
  const mhChart = useMemo((): PlotlyFigure => {
    const fig: PlotlyFigure = {
      data: MH_INDICES.map((idx, i) => ({
        type: 'scatter' as const,
        x: MH_HORIZONS,
        y: MH_ICS[idx],
        name: idx,
        mode: 'lines+markers' as const,
        line: { color: MH_COLORS[i % MH_COLORS.length], width: 2 },
        marker: { size: 5 },
      })),
      layout: {
        yaxis: { ...YAXIS_BASE, title: 'IC', titlefont: { size: 10 } },
        xaxis: { title: 'Forward Horizon', titlefont: { size: 10 }, showline: true, linewidth: 1 },
        hovermode: 'x unified' as any,
        legend: { orientation: 'h' as const, y: -0.25, font: { size: 9 } },
        margin: { ...CHART_M, b: 80 },
      },
    };
    return themed(fig, theme);
  }, [theme]);

  return (
    <div className="space-y-6">
      <p className="text-[13px] text-muted-foreground leading-relaxed">
        The strategy uses the SAME global macro indicator pool for all indices.
        No index-specific tuning is performed. Results below from walk-forward backtests across 10 global equity indices.
      </p>

      {/* Sharpe Heatmap */}
      <div className="panel-card p-4">
        <SectionTitle info="Walk-forward, equal-weighted, 5Y lookback, quarterly rebalance">Sharpe Ratio Heatmap (Index x Strategy)</SectionTitle>
        <ChartBox chart={sharpeChart} height={260} />
      </div>

      {/* Alpha Heatmap */}
      <div className="panel-card p-4">
        <SectionTitle info="Strategy ann return minus benchmark ann return">Annual Alpha vs 50% Benchmark (Index x Strategy)</SectionTitle>
        <ChartBox chart={alphaChart} height={300} />
      </div>

      {/* Cross-Strategy Summary */}
      <div className="panel-card p-4">
        <SectionTitle>Cross-Strategy Summary (Averaged Across Indices)</SectionTitle>
        <div className="overflow-x-auto">
          <table className="w-full text-[12.5px] font-mono">
            <thead>
              <tr className="border-b border-border/20">
                <th className="text-left py-1.5 text-muted-foreground/50 font-semibold uppercase tracking-wider text-[11px]">Strategy</th>
                <th className="text-right py-1.5 text-muted-foreground/50 font-semibold uppercase tracking-wider text-[11px]">Avg Sharpe</th>
                <th className="text-right py-1.5 text-muted-foreground/50 font-semibold uppercase tracking-wider text-[11px]">Avg Alpha</th>
                <th className="text-right py-1.5 text-muted-foreground/50 font-semibold uppercase tracking-wider text-[11px]">% Indices Beat</th>
              </tr>
            </thead>
            <tbody>
              {SUMMARY_ROWS.map(r => (
                <tr key={r.strategy} className="border-b border-border/10">
                  <td className="py-1.5 font-medium" style={{ color: STRAT_COLORS[r.strategy] ?? undefined }}>
                    {r.strategy}
                  </td>
                  <td className="text-right py-1.5 tabular-nums text-foreground">{r.sharpe}</td>
                  <td className={`text-right py-1.5 tabular-nums ${r.alpha.startsWith('+') ? 'text-emerald-500' : 'text-muted-foreground'}`}>{r.alpha}</td>
                  <td className="text-right py-1.5 tabular-nums text-foreground">{r.beat}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Multi-Horizon IC */}
      <div className="panel-card p-4">
        <SectionTitle info="Spearman rank IC of binary regime composite vs forward returns">Composite IC by Forward Horizon</SectionTitle>
        <ChartBox chart={mhChart} height={350} />
        <div className="mt-3 text-[12.5px] text-muted-foreground space-y-1">
          <p>- IC peaks at 13-26 weeks for most indices (sweet spot for macro signals)</p>
          <p>- 4-week IC is lowest -- macro signals are noisy at short horizons</p>
          <p>- 52-week IC drops off -- mean reversion dilutes predictive power</p>
          <p>- Euro Stoxx 50 shows the highest IC at 13w (+0.362)</p>
        </div>
      </div>

      {/* Top Indicators */}
      <div className="panel-card p-4">
        <SectionTitle>Top Indicators by IC (Full-Sample Average)</SectionTitle>
        <div className="overflow-x-auto">
          <table className="w-full text-[12.5px] font-mono">
            <thead>
              <tr className="border-b border-border/20">
                <th className="text-left py-1.5 text-muted-foreground/50 font-semibold uppercase tracking-wider text-[11px]">Indicator</th>
                <th className="text-left py-1.5 text-muted-foreground/50 font-semibold uppercase tracking-wider text-[11px]">Category</th>
                <th className="text-right py-1.5 text-muted-foreground/50 font-semibold uppercase tracking-wider text-[11px]" title="Information Coefficient — predictive accuracy of an indicator">Avg IC</th>
                <th className="text-left py-1.5 text-muted-foreground/50 font-semibold uppercase tracking-wider text-[11px]">Direction</th>
              </tr>
            </thead>
            <tbody>
              {TOP_INDICATORS.map(ind => (
                <tr key={ind.name} className="border-b border-border/10">
                  <td className="py-1.5 text-foreground font-medium">{ind.name}</td>
                  <td className="py-1.5" style={{ color: STRAT_COLORS[ind.category] }}>{ind.category}</td>
                  <td className={`text-right py-1.5 tabular-nums ${ind.ic.startsWith('+') ? 'text-emerald-500' : 'text-rose-500'}`}>{ind.ic}</td>
                  <td className="py-1.5 text-muted-foreground">{ind.direction}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
