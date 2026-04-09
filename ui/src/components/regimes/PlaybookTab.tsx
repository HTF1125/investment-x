'use client';

import type { AssetAnalytics, RegimeModel } from './types';
import { PLOTLY_CONFIG, getRegimeColor, getRegimeOrder } from './constants';
import { hexToRgb, fmtPctSigned } from './helpers';
import { Plot, PanelCard, StatLabel } from './SharedComponents';

interface Props {
  analytics: AssetAnalytics;
  model?: RegimeModel;
}

export function PlaybookTab({ analytics, model }: Props) {
  if (!analytics) {
    return <p className="text-muted-foreground text-[12.5px]">No playbook data for this regime.</p>;
  }

  const stateOrder = getRegimeOrder(model);
  const tickers = analytics.tickers;

  // Returns by regime heatmap
  const z: number[][] = [];
  const text: string[][] = [];
  for (const t of tickers) {
    const row_z: number[] = [];
    const row_t: string[] = [];
    for (const regime of stateOrder) {
      const stats = analytics.per_regime_stats[regime];
      const a = stats?.assets.find((x) => x.ticker === t);
      const n = a?.months ?? 0;
      if (!a || a.ann_ret === null || n < 3) {
        row_z.push(NaN);
        row_t.push(`—<br>n=${n}`);
      } else if (n < 12) {
        row_z.push(NaN);
        row_t.push(`⚠ ${(a.ann_ret * 100).toFixed(1)}%<br>n=${n}`);
      } else {
        row_z.push(a.ann_ret);
        row_t.push(`${(a.ann_ret * 100).toFixed(1)}%<br>n=${n}`);
      }
    }
    z.push(row_z);
    text.push(row_t);
  }

  // Expected returns horizontal bar
  const expectedSorted = Object.entries(analytics.expected_returns)
    .sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-4">
      <PanelCard>
        <StatLabel>Average Annualised Returns by Dominant Regime — n&lt;12 greyed</StatLabel>
        <Plot
          data={[
            {
              z, x: stateOrder, y: tickers,
              text, texttemplate: '%{text}',
              textfont: { size: 11, family: 'Space Mono' },
              type: 'heatmap',
              colorscale: [[0, '#D65656'], [0.5, '#141620'], [1, '#48A86E']],
              zmid: 0, showscale: true,
              colorbar: { thickness: 10, len: 0.8 },
            },
          ]}
          layout={{
            height: 460,
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { family: 'Space Mono, monospace', size: 10, color: '#9AA4B2' },
            margin: { l: 50, r: 20, t: 50, b: 20 },
            xaxis: { side: 'top' },
          }}
          config={PLOTLY_CONFIG}
          style={{ width: '100%', height: '460px' }}
        />
      </PanelCard>

      {/* Regime count summary */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {stateOrder.map((r) => {
          const c = analytics.regime_counts[r];
          const color = getRegimeColor(r, model);
          const rgb = hexToRgb(color);
          return (
            <div
              key={r}
              className="rounded-[var(--radius)] border p-3 text-center"
              style={{ background: `rgba(${rgb}, 0.04)`, borderColor: `rgba(${rgb}, 0.20)` }}
            >
              <div className="text-[10px] uppercase tracking-wider opacity-70" style={{ color }}>
                {r}
              </div>
              <div className="text-xl font-bold font-mono mt-0.5" style={{ color }}>
                {c?.months ?? 0}
              </div>
              <div className="text-[10px] text-muted-foreground/40">
                months ({(c?.pct ?? 0).toFixed(0)}%)
              </div>
            </div>
          );
        })}
        {analytics.regime_counts.Mixed && (
          <div
            className="rounded-[var(--radius)] border p-3 text-center"
            style={{
              background: `rgba(${hexToRgb('#7D8596')}, 0.04)`,
              borderColor: `rgba(${hexToRgb('#7D8596')}, 0.20)`,
            }}
          >
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground/60">
              Mixed
            </div>
            <div className="text-xl font-bold font-mono mt-0.5 text-muted-foreground">
              {analytics.regime_counts.Mixed.months}
            </div>
            <div className="text-[10px] text-muted-foreground/40">
              months ({analytics.regime_counts.Mixed.pct.toFixed(0)}%)
            </div>
          </div>
        )}
      </div>

      <PanelCard>
        <StatLabel>Expected Return Given Current Regime Probabilities</StatLabel>
        <Plot
          data={[
            {
              x: expectedSorted.map(([_, v]) => v * 100),
              y: expectedSorted.map(([t, _]) => t),
              type: 'bar',
              orientation: 'h',
              marker: {
                color: expectedSorted.map(([_, v]) => (v > 0 ? '#48A86E' : '#D65656')),
              },
              text: expectedSorted.map(([_, v]) => `${(v * 100).toFixed(1)}%`),
              textposition: 'outside',
              textfont: { size: 10, family: 'Space Mono' },
              hovertemplate: '<b>%{y}</b>: %{text}<extra></extra>',
            },
          ]}
          layout={{
            height: 320,
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { family: 'Space Mono, monospace', size: 10, color: '#9AA4B2' },
            margin: { l: 50, r: 60, t: 30, b: 36 },
            xaxis: {
              title: { text: 'Expected Annualised Return (%)' },
              gridcolor: 'rgba(148,163,184,0.07)',
              zeroline: false,
            },
            yaxis: { autorange: 'reversed' },
            showlegend: false,
            shapes: [
              { type: 'line', x0: 0, x1: 0, yref: 'paper', y0: 0, y1: 1, line: { color: '#48525E', width: 1 } },
            ],
          }}
          config={PLOTLY_CONFIG}
          style={{ width: '100%', height: '320px' }}
        />
        {analytics.small_sample_regimes.length > 0 && (
          <div className="mt-2 px-3 py-2 rounded-[var(--radius)] bg-amber-500/5 border border-amber-500/25">
            <p className="text-[10.5px] text-muted-foreground">
              <span className="text-amber-500 font-semibold">⚠ Small sample warning — </span>
              {analytics.small_sample_regimes.join(', ')} have &lt;12 months of data. Treat as directional only.
            </p>
          </div>
        )}
      </PanelCard>
    </div>
  );
}
