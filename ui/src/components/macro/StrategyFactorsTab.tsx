'use client';

import { useMemo, useState } from 'react';
import { useTheme } from '@/context/ThemeContext';
import type { PlotlyFigure } from '@/lib/chartTheme';
import type { FactorCategory, CurrentSignalData } from './types';
import { STRAT_COLORS, CHART_M_HBAR, YAXIS_BASE, CHART_M } from './constants';
import { fmt, themed } from './helpers';
import { LoadingSpinner, SectionTitle, ChartBox } from './SharedComponents';

const CATEGORIES = ['Growth', 'Inflation', 'Liquidity', 'Tactical'] as const;

const REGIME_COLORS_MAP: Record<string, string> = {
  'Risk-On': '#3fb950', 'Neutral': '#d29922', 'Risk-Off': '#f85149',
};

export default function StrategyFactorsTab({ factors, signal, isLoading, target }: {
  factors: Record<string, FactorCategory> | null;
  signal: CurrentSignalData | null;
  isLoading: boolean; target: string;
}) {
  const { theme } = useTheme();
  const [selectedCat, setSelectedCat] = useState<string>('Growth');

  const cat = factors?.[selectedCat] ?? null;

  // ── Selection frequency bar chart ──
  const frequencyChart = useMemo(() => {
    if (!cat?.frequency?.length) return null;
    const top = cat.frequency.slice(0, 20);
    const fig: PlotlyFigure = {
      data: [{
        type: 'bar',
        y: top.map(f => f.indicator),
        x: top.map(f => f.count),
        orientation: 'h',
        marker: { color: STRAT_COLORS[selectedCat] ?? '#888' },
        text: top.map(f => `${f.count}/${cat.n_rebalances} (${fmt(f.pct, 0)}%)`),
        textposition: 'auto',
        textfont: { size: 10 },
        hovertemplate: '%{y}: %{x} selections<extra></extra>',
      }],
      layout: {
        yaxis: { ...YAXIS_BASE, autorange: 'reversed', showgrid: false },
        xaxis: { ...YAXIS_BASE, title: 'Selection Count', titlefont: { size: 10 }, showgrid: true },
        margin: CHART_M_HBAR,
      },
    };
    return themed(fig, theme);
  }, [cat, selectedCat, theme]);

  // ── IC heatmap ──
  const icHeatmapChart = useMemo(() => {
    if (!cat?.ic_heatmap?.values?.length) return null;
    const hm = cat.ic_heatmap;
    // Take top 15 indicators by row
    const topN = Math.min(15, hm.indicators.length);
    const indicators = hm.indicators.slice(0, topN);
    const values = hm.values.slice(0, topN);

    const fig: PlotlyFigure = {
      data: [{
        type: 'heatmap',
        z: values,
        x: hm.dates,
        y: indicators,
        colorscale: 'RdBu',
        zmid: 0,
        zmin: -0.3,
        zmax: 0.3,
        showscale: true,
        colorbar: { thickness: 12, len: 0.8, tickfont: { size: 9 } },
        hovertemplate: '%{y}<br>%{x}: %{z:.4f}<extra></extra>',
      }],
      layout: {
        xaxis: { type: 'date', showticklabels: true, showline: true, linewidth: 1, side: 'bottom', title: 'Date', titlefont: { size: 10 } },
        yaxis: { ...YAXIS_BASE, autorange: 'reversed', showgrid: false, title: 'Indicator', titlefont: { size: 10 } },
        margin: { l: 160, r: 60, t: 12, b: 40 },
      },
    };
    return themed(fig, theme);
  }, [cat, theme]);

  // ── Signal section ──
  const catSignals = signal?.category_signals ?? {};
  const factorSelections = signal?.factor_selections ?? {};
  const regimeSignal = catSignals['Regime'] ?? null;

  if (isLoading) return <LoadingSpinner label="Loading factor data" />;
  if (!factors) return null;

  return (
    <div className="space-y-3">
      {/* Current signal overview */}
      {signal && (
        <div className="space-y-1.5">
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-1.5">
            {CATEGORIES.map(c => {
              const sig = catSignals[c];
              if (!sig) return null;
              return (
                <div key={c} className="panel-card px-2 py-1.5">
                  <div className="stat-label">{c}</div>
                  <div className="text-[13px] font-mono font-semibold tabular-nums text-foreground">
                    {fmt(sig.eq_weight * 100, 0)}%
                    <span className={`text-[10px] ml-1 ${sig.label === 'Risk-On' ? 'text-emerald-500' : sig.label === 'Risk-Off' ? 'text-rose-500' : 'text-muted-foreground'}`}>
                      {sig.label}
                    </span>
                  </div>
                </div>
              );
            })}
            {regimeSignal && (
              <div className="panel-card px-2 py-1.5">
                <div className="stat-label">Regime</div>
                <div className="text-[13px] font-mono font-semibold tabular-nums text-foreground">
                  <span className="inline-block w-2 h-2 rounded-full mr-1 align-middle" style={{ backgroundColor: REGIME_COLORS_MAP[regimeSignal.regime ?? ''] ?? '#888' }} />
                  {regimeSignal.regime ?? '-'}
                  <span className="text-[10px] text-muted-foreground ml-1">{fmt(regimeSignal.eq_weight * 100, 0)}%</span>
                </div>
              </div>
            )}
          </div>

          {/* Regime percentiles */}
          {regimeSignal?.growth_pctile != null && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
              <div className="panel-card px-2 py-1.5">
                <div className="stat-label">Growth Percentile</div>
                <div className="text-[13px] font-mono font-semibold tabular-nums text-foreground">{fmt((regimeSignal.growth_pctile ?? 0) * 100, 0)}%</div>
              </div>
              <div className="panel-card px-2 py-1.5">
                <div className="stat-label">Inflation Percentile</div>
                <div className="text-[13px] font-mono font-semibold tabular-nums text-foreground">{fmt((regimeSignal.inflation_pctile ?? 0) * 100, 0)}%</div>
              </div>
              <div className="panel-card px-2 py-1.5">
                <div className="stat-label">Signal Date</div>
                <div className="text-[13px] font-mono font-semibold tabular-nums text-foreground">{regimeSignal.date}</div>
              </div>
            </div>
          )}

          {/* Factor selections per category */}
          <div className="panel-card px-3 py-2">
            <SectionTitle info="Current IC-weighted factor selections for each category strategy.">Active Factors</SectionTitle>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {CATEGORIES.map(c => {
                const sel = factorSelections[c];
                if (!sel?.length) return null;
                return (
                  <div key={c}>
                    <div className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground/50 mb-1 flex items-center">
                      <span className="inline-block w-2 h-2 rounded-full mr-1.5" style={{ backgroundColor: STRAT_COLORS[c] }} />
                      {c} ({sel.length})
                    </div>
                    <div className="space-y-0.5">
                      {sel.map((f, i) => (
                        <div key={i} className="flex items-center justify-between text-[10px]">
                          <span className="text-foreground truncate mr-2">{f.name}</span>
                          <span className={`font-mono tabular-nums shrink-0 ${f.ic > 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                            {f.ic > 0 ? '+' : ''}{f.ic.toFixed(4)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Category selector */}
      <div className="border-b border-border/25">
        <div className="flex gap-0.5 -mb-px">
          {CATEGORIES.map(c => (
            <button key={c} onClick={() => setSelectedCat(c)}
              className={`tab-link ${selectedCat === c ? 'active' : ''}`}>
              <span className="inline-block w-2 h-2 rounded-full mr-1.5 align-middle" style={{ backgroundColor: STRAT_COLORS[c] }} />
              {c}
            </button>
          ))}
        </div>
      </div>

      {/* Category details */}
      {cat && (
        <>
          {/* Category summary */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
            <div className="panel-card px-2 py-1.5">
              <div className="stat-label">Rebalances</div>
              <div className="text-[13px] font-mono font-semibold tabular-nums text-foreground">{cat.n_rebalances}</div>
            </div>
            <div className="panel-card px-2 py-1.5">
              <div className="stat-label">Unique Indicators</div>
              <div className="text-[13px] font-mono font-semibold tabular-nums text-foreground">{cat.n_unique_indicators}</div>
            </div>
            <div className="panel-card px-2 py-1.5">
              <div className="stat-label">Latest Selection</div>
              <div className="text-[13px] font-mono font-semibold tabular-nums text-foreground">{cat.latest_selection?.date ?? '-'}</div>
            </div>
          </div>

          {/* Frequency chart + top 10 table */}
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
            <div className="lg:col-span-3 panel-card p-2">
              <SectionTitle info={`Top 20 most frequently selected indicators for ${selectedCat} across all walk-forward rebalances.`}>Selection Frequency</SectionTitle>
              <ChartBox chart={frequencyChart} height={500} />
            </div>
            <div className="lg:col-span-2 space-y-3">
              <div className="panel-card px-3 py-2">
                <SectionTitle info="Top 10 indicators by selection frequency.">Top 10 Indicators</SectionTitle>
                <table className="w-full text-[11px]">
                  <thead>
                    <tr className="border-b border-border/40">
                      <th className="text-left py-1 pr-2 text-[9px] font-mono uppercase text-muted-foreground/50">Indicator</th>
                      <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Count</th>
                      <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Freq</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(cat.frequency ?? []).slice(0, 10).map((f, i) => (
                      <tr key={i} className="border-b border-border/20">
                        <td className="py-1 pr-2 text-foreground text-[11px] truncate max-w-[180px]">{f.indicator}</td>
                        <td className="text-right py-1 px-1 font-mono tabular-nums text-[11px] text-foreground">{f.count}</td>
                        <td className="text-right py-1 px-1 font-mono tabular-nums text-[11px] text-foreground">{fmt(f.pct, 0)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Latest selection */}
              {cat.latest_selection?.indicators?.length > 0 && (
                <div className="panel-card px-3 py-2">
                  <SectionTitle info="Indicators selected at the most recent walk-forward rebalance, with their trailing information coefficient.">Latest Selection</SectionTitle>
                  <table className="w-full text-[11px]">
                    <thead>
                      <tr className="border-b border-border/40">
                        <th className="text-left py-1 pr-2 text-[9px] font-mono uppercase text-muted-foreground/50">Indicator</th>
                        <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">IC</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cat.latest_selection.indicators.map((ind, i) => (
                        <tr key={i} className="border-b border-border/20">
                          <td className="py-1 pr-2 text-foreground text-[11px] truncate max-w-[200px]">{ind.name}</td>
                          <td className={`text-right py-1 px-1 font-mono tabular-nums text-[11px] ${ind.ic > 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                            {ind.ic > 0 ? '+' : ''}{ind.ic.toFixed(4)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* IC heatmap */}
          {cat.ic_heatmap?.values?.length > 0 && (
            <div className="panel-card p-2">
              <SectionTitle info={`Information coefficient heatmap for top indicators across rebalancing dates. Blue = positive IC (predictive), Red = negative IC.`}>IC Heatmap</SectionTitle>
              <ChartBox chart={icHeatmapChart} height={400} />
            </div>
          )}
        </>
      )}
    </div>
  );
}
