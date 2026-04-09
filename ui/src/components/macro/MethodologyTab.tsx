'use client';

import { useMemo } from 'react';
import { useTheme } from '@/context/ThemeContext';
import { CHART_SEMANTIC, type PlotlyFigure } from '@/lib/chartTheme';
import { REGIME_COLORS, CHART_M, YAXIS_BASE } from './constants';
import { themed } from './helpers';
import { SectionTitle, ChartBox } from './SharedComponents';

export default function MethodologyTab() {
  const { theme } = useTheme();
  const GREEN = CHART_SEMANTIC[theme].success;
  const RED = CHART_SEMANTIC[theme].destructive;
  const ORANGE = CHART_SEMANTIC[theme].warning;
  const ACCENT = CHART_SEMANTIC[theme].primary;
  const PURPLE = CHART_SEMANTIC[theme].primary;
  const MUTED = CHART_SEMANTIC[theme].neutral;

  const quadrantChart = useMemo((): PlotlyFigure => {
    const fig: PlotlyFigure = {
      data: [
        { type: 'scatter', x: [0.25], y: [0.75], text: ['GOLDILOCKS\nG+, I-\n90% Equity'], mode: 'text', textfont: { size: 14, color: GREEN }, showlegend: false },
        { type: 'scatter', x: [0.75], y: [0.75], text: ['REFLATION\nG+, I+\n70% Equity'], mode: 'text', textfont: { size: 14, color: ORANGE }, showlegend: false },
        { type: 'scatter', x: [0.25], y: [0.25], text: ['DEFLATION\nG-, I-\n30% Equity'], mode: 'text', textfont: { size: 14, color: ACCENT }, showlegend: false },
        { type: 'scatter', x: [0.75], y: [0.25], text: ['STAGFLATION\nG-, I+\n10% Equity'], mode: 'text', textfont: { size: 14, color: RED }, showlegend: false },
      ],
      layout: {
        xaxis: { title: 'Inflation Signal', range: [0, 1], showgrid: false, showline: true, linewidth: 1 },
        yaxis: { title: 'Growth Signal', range: [0, 1], showgrid: false, showline: true, linewidth: 1 },
        shapes: [
          { type: 'line', x0: 0.5, x1: 0.5, y0: 0, y1: 1, line: { color: MUTED, width: 1, dash: 'dash' } },
          { type: 'line', x0: 0, x1: 1, y0: 0.5, y1: 0.5, line: { color: MUTED, width: 1, dash: 'dash' } },
        ],
        margin: { ...CHART_M, t: 16 },
        hovermode: false as any,
      },
    };
    return themed(fig, theme);
  }, [theme]);

  return (
    <div className="space-y-4">
      {/* Investment Problem */}
      <div className="panel-card p-4">
        <SectionTitle>The Investment Problem</SectionTitle>
        <p className="text-[13px] text-muted-foreground leading-relaxed mb-3">
          Asset allocation is the single most important decision for any investor.
          Getting the equity weight right during regime transitions accounts for the
          vast majority of long-term risk-adjusted returns.
        </p>
        <p className="text-[13px] text-muted-foreground leading-relaxed mb-3">
          The core insight: <span className="text-foreground font-semibold">binary regime switching</span> dramatically
          outperforms continuous allocation tilting.
        </p>
        <table className="data-table text-[12.5px] font-mono">
          <thead>
            <tr>
              <th className="text-left">Approach</th>
              <th className="text-left">Mechanism</th>
              <th className="text-right">Typical Alpha</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="py-1.5 text-muted-foreground">Continuous tilts</td>
              <td className="py-1.5 text-muted-foreground">+/-20% around 50%</td>
              <td className="text-right py-1.5 text-muted-foreground">~0.5%/yr</td>
            </tr>
            <tr>
              <td className="py-1.5 text-foreground font-medium">Binary regime switching</td>
              <td className="py-1.5 text-foreground">90%/50%/10% equity</td>
              <td className="text-right py-1.5 text-success font-semibold">~3-5%/yr</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* 90/50/10 Rule */}
      <div className="panel-card p-4">
        <SectionTitle>The 90/50/10 Allocation Rule</SectionTitle>
        <p className="text-[13px] text-muted-foreground leading-relaxed mb-3">
          Two independent signals classify the regime:
        </p>
        <ol className="text-[13px] text-muted-foreground leading-relaxed mb-3 list-decimal list-inside space-y-1">
          <li><span className="text-foreground font-medium">Trend signal:</span> Is price above 40-week SMA?</li>
          <li><span className="text-foreground font-medium">Macro composite:</span> Is factor composite above trailing median?</li>
        </ol>
        <table className="data-table text-[12.5px] font-mono">
          <thead>
            <tr>
              <th className="text-center">Trend</th>
              <th className="text-center">Macro</th>
              <th className="text-left">Classification</th>
              <th className="text-right">Equity Wt</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="text-center py-1.5 text-success">Bullish</td>
              <td className="text-center py-1.5 text-success">Bullish</td>
              <td className="py-1.5 text-foreground font-medium">Full Risk-On</td>
              <td className="text-right py-1.5 text-success font-semibold">90%</td>
            </tr>
            <tr>
              <td className="text-center py-1.5 text-muted-foreground">Mixed</td>
              <td className="text-center py-1.5 text-muted-foreground">Mixed</td>
              <td className="py-1.5 text-foreground font-medium">Neutral</td>
              <td className="text-right py-1.5 text-muted-foreground font-semibold">50%</td>
            </tr>
            <tr>
              <td className="text-center py-1.5 text-destructive">Bearish</td>
              <td className="text-center py-1.5 text-destructive">Bearish</td>
              <td className="py-1.5 text-foreground font-medium">Full Risk-Off</td>
              <td className="text-right py-1.5 text-destructive font-semibold">10%</td>
            </tr>
          </tbody>
        </table>
        <p className="text-[11.5px] text-muted-foreground/50 mt-2">Benchmark: static 50% equity / 50% cash allocation.</p>
      </div>

      {/* Factor Categories */}
      <div className="panel-card p-4">
        <SectionTitle>Factor Categories</SectionTitle>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[
            { name: 'Growth', color: GREEN, items: ['PMI diffusion (manufacturing & services)', 'OECD Composite Leading Indicators', 'ISM new orders, NO-Inventory spread', 'CESI breadth & momentum', 'Asian exports, global trade', 'Earnings revision ratios', 'Housing, confidence, labor'], theory: 'Growth acceleration leads equity returns by 3-6 months.' },
            { name: 'Inflation', color: ORANGE, items: ['CPI/PCE components & momentum', 'Breakeven inflation rates', 'Inflation surprise indices (Citi)', 'Wage growth (average hourly earnings)', 'Commodity prices (CRB, oil, metals)'], theory: 'Rising inflation forces tightening, compresses multiples, erodes real earnings.' },
            { name: 'Liquidity', color: ACCENT, items: ['Central bank balance sheets (Fed, ECB, BOJ, PBOC)', 'M2 money supply (US, China)', 'Credit impulse & bank lending', 'Financial Conditions Indices', 'Yield curve shape (2s10s, 3m10y)', 'Monetary policy expectations'], theory: 'Expanding liquidity lowers discount rates and eases financial conditions.' },
            { name: 'Tactical', color: PURPLE, items: ['Volatility structure (VIX, RVX, GVZ)', 'Credit spreads (HY/IG ratio)', 'Positioning (CFTC net specs)', 'Sector rotation (breadth, dispersion)', 'Cross-asset signals (risk on/off)', 'Put/call ratios'], theory: 'Many are contrarian -- high VIX and wide spreads predict higher forward returns.' },
          ].map(cat => (
            <div key={cat.name} className="border border-border/30 rounded-[var(--radius)] p-3">
              <div className="flex items-center gap-2 mb-2.5">
                <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: cat.color }} />
                <span className="text-[12.5px] font-semibold uppercase tracking-[0.06em] text-foreground/80">{cat.name}</span>
              </div>
              <ul className="text-[12.5px] text-muted-foreground space-y-0.5 mb-2.5">
                {cat.items.map(item => (
                  <li key={item} className="flex items-start gap-1.5">
                    <span className="text-border/60 mt-0.5 shrink-0">–</span>
                    {item}
                  </li>
                ))}
              </ul>
              <p className="text-[11.5px] text-muted-foreground/55 font-mono border-t border-border/20 pt-2 mt-2">{cat.theory}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Factor Selection Process */}
      <div className="panel-card p-4">
        <SectionTitle>Factor Selection Process</SectionTitle>
        <ol className="text-[13px] text-muted-foreground leading-relaxed space-y-2">
          {[
            ['Apply publication lags', 'Shift each indicator by its known publication delay (1-12 weeks) to eliminate look-ahead bias.'],
            ['Compute trailing IC', 'Spearman rank correlation between z-score and per-category forward returns (Growth 26w, Inflation 13w, Liquidity 13w, Tactical 8w) using ONLY prior 5 years.'],
            ['Rank by |IC|', 'Strongest predictors first.'],
            ['Correlation filter (rho = 0.60)', 'Skip indicators too correlated with already-selected ones.'],
            ['Select top 10', 'First 10 surviving indicators.'],
            ['Build composite', 'Equal-weight raw z-scores into a single signal per category.'],
            ['Blend categories', 'Equal-weight across Growth, Inflation, Liquidity, Tactical.'],
            ['Circuit breakers', 'Override to risk-off if VIX > 35 or index drops >10% from 52-week high.'],
            ['Hold', 'Maintain equity weight until next 8-week rebalance. Deduct 10bps transaction cost per trade.'],
          ].map(([label, desc], i) => (
            <li key={i} className="flex gap-3">
              <span className="stat-label shrink-0 mt-0.5 w-4 text-right">{i + 1}.</span>
              <span><span className="text-foreground font-medium">{label}:</span> {desc}</span>
            </li>
          ))}
        </ol>
      </div>

      {/* Regime Quadrant */}
      <div className="panel-card p-4">
        <SectionTitle>Regime Quadrant Model</SectionTitle>
        <p className="text-[13px] text-muted-foreground leading-relaxed mb-3">
          Two separate composites (Growth and Inflation) classify the environment into four quadrants:
        </p>
        <ChartBox chart={quadrantChart} height={300} />
      </div>

      {/* Critical Lessons */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="panel-card p-4 border-destructive/25">
          <SectionTitle>What NOT to Do</SectionTitle>
          <ul className="text-[12.5px] text-muted-foreground space-y-1.5">
            {[
              'Do NOT include Global M2 — zero IC, pure noise',
              'Do NOT use continuous allocation tilts — caps alpha at <1%/yr',
              'Do NOT judge by weekly hit rate (~55%) — alpha concentrates in rare bear avoidance',
            ].map((item, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-destructive/70 mt-0.5 shrink-0">–</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
        <div className="panel-card p-4 border-success/25">
          <SectionTitle>What Works</SectionTitle>
          <ul className="text-[12.5px] text-muted-foreground space-y-1.5">
            {[
              'Raw z-score composites — no IC-sign direction flipping',
              'Equal-weighting across indicators AND categories (no in-sample optimization)',
              'Correlation filter (0.60) essential — prevents loading correlated variants',
              'Per-category horizons (Growth 6m, Inflation 3m, Liquidity 3m, Tactical 2m)',
              'VIX circuit breaker (>35) and drawdown override (>10%) for tail risk protection',
              'Allocation capped at 10-100% (no leverage) — alpha is from avoidance, not amplification',
            ].map((item, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-success/70 mt-0.5 shrink-0">–</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Composite Direction */}
      <div className="panel-card p-4">
        <SectionTitle>Composite Direction</SectionTitle>
        <p className="text-[13px] text-muted-foreground leading-relaxed mb-3">
          Composites are built from <span className="text-foreground font-medium">raw z-score averages</span> — no IC-sign flipping.
          Each composite directly reflects its economic axis (e.g. high inflation composite = high inflation).
          For allocation, categories where a high reading is bearish have their percentile inverted:
        </p>
        <table className="data-table text-[12.5px] font-mono">
          <thead>
            <tr>
              <th className="text-left">Category</th>
              <th className="text-center">Direction</th>
              <th className="text-left">Logic</th>
            </tr>
          </thead>
          <tbody>
            {[
              { cat: 'Growth', dir: 'Direct', logic: 'High composite = strong growth = bullish', color: GREEN },
              { cat: 'Inflation', dir: 'Inverted', logic: 'High composite = high inflation = bearish → percentile inverted for allocation', color: ORANGE },
              { cat: 'Liquidity', dir: 'Direct', logic: 'High composite = ample liquidity = bullish', color: ACCENT },
              { cat: 'Tactical', dir: 'Direct', logic: 'Mixed signals selected by predictive power (|IC| ranking)', color: PURPLE },
            ].map(r => (
              <tr key={r.cat}>
                <td className="py-1.5 font-semibold" style={{ color: r.color }}>{r.cat}</td>
                <td className="text-center py-1.5 text-foreground">{r.dir}</td>
                <td className="py-1.5 text-muted-foreground">{r.logic}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
