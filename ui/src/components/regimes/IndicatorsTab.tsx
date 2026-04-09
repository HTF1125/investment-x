'use client';

import { useState, useEffect } from 'react';
import type { TimeseriesData, RegimeModel } from './types';
import { PLOTLY_CONFIG, getDimensionColor } from './constants';
import { hexToRgb, fmtZ } from './helpers';
import { Plot, PanelCard, StatLabel } from './SharedComponents';

interface Props {
  ts: TimeseriesData;
  model?: RegimeModel;
}

// Map dimension names to indicator prefixes. Mirrors the logic in
// ix/core/regimes/base.py `_dimension_prefixes` — first letter + underscore,
// with overrides for clashing dimensions (Level × Trend).
function dimPrefix(dim: string): string {
  const overrides: Record<string, string> = { Level: 'lv_', Trend: 'tr_' };
  return overrides[dim] ?? dim[0].toLowerCase() + '_';
}

export function IndicatorsTab({ ts, model }: Props) {
  const dims = model?.dimensions ?? ['Growth', 'Inflation', 'Liquidity'];
  const [dim, setDim] = useState<string>(dims[0]);

  // Reset selected dimension when model changes
  useEffect(() => {
    if (!dims.includes(dim)) setDim(dims[0]);
  }, [model?.key]);

  const prefix = dimPrefix(dim);
  const compKey = `${dim}_Z`;
  const color = getDimensionColor(dim, model);

  // Get all indicator series matching this dimension prefix
  const parts = Object.keys(ts.indicators || {}).filter(
    (k) => k.startsWith(prefix) && k !== 'g_Claims4WMA'
  );

  if (parts.length === 0 && !ts.composites[compKey]) {
    return <p className="text-muted-foreground text-[12.5px]">No indicator data for {dim}.</p>;
  }

  const traces: any[] = parts.map((p) => ({
    x: ts.dates,
    y: ts.indicators[p],
    name: p.replace(prefix, ''),
    mode: 'lines',
    line: { width: 1.2 },
    opacity: 0.6,
    hovertemplate: `<b>${p.replace(prefix, '')}</b>: %{y:+.2f}<extra></extra>`,
  }));

  if (ts.composites[compKey]) {
    traces.push({
      x: ts.dates,
      y: ts.composites[compKey],
      name: `${dim} Composite`,
      mode: 'lines',
      line: { color, width: 2.5 },
      hovertemplate: `<b>Composite</b>: %{y:+.2f}<extra></extra>`,
    });
  }

  // Current readings (last non-null value of each indicator)
  const lastIdx = ts.dates.length - 1;
  const readings: { name: string; z: number; signal: string; isComposite: boolean }[] = [];
  for (const p of parts) {
    const series = ts.indicators[p];
    if (!series) continue;
    // Find last non-null
    let lastVal: number | null = null;
    for (let i = series.length - 1; i >= 0; i--) {
      if (series[i] !== null) {
        lastVal = series[i] as number;
        break;
      }
    }
    if (lastVal !== null) {
      readings.push({
        name: p.replace(prefix, ''),
        z: lastVal,
        signal: lastVal > 0 ? '▲ Positive' : '▼ Negative',
        isComposite: false,
      });
    }
  }
  if (ts.composites[compKey]) {
    const compSeries = ts.composites[compKey];
    let lastComp: number | null = null;
    for (let i = compSeries.length - 1; i >= 0; i--) {
      if (compSeries[i] !== null) {
        lastComp = compSeries[i] as number;
        break;
      }
    }
    if (lastComp !== null) {
      readings.push({
        name: `★ ${dim} Composite`,
        z: lastComp,
        signal: lastComp > 0 ? '▲ Positive' : '▼ Negative',
        isComposite: true,
      });
    }
  }

  return (
    <div className="space-y-4">
      {/* Dimension selector */}
      <div className="flex gap-2">
        {dims.map((d) => {
          const dColor = getDimensionColor(d, model);
          const active = dim === d;
          return (
            <button
              key={d}
              onClick={() => setDim(d)}
              className={`px-3 py-1.5 text-[11.5px] uppercase tracking-wider rounded-[var(--radius)] border transition-colors ${
                active
                  ? 'border-foreground text-foreground'
                  : 'border-border/40 text-muted-foreground hover:border-border/70'
              }`}
              style={active ? { color: dColor, borderColor: dColor } : {}}
            >
              {d}
            </button>
          );
        })}
      </div>

      <PanelCard>
        <StatLabel>{dim} Indicators vs Composite</StatLabel>
        <Plot
          data={traces}
          layout={{
            height: 380,
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { family: 'Space Mono, monospace', size: 10, color: '#9AA4B2' },
            margin: { l: 50, r: 20, t: 40, b: 36 },
            yaxis: {
              title: { text: 'Z-Score' },
              gridcolor: 'rgba(148,163,184,0.07)',
              zeroline: false,
            },
            xaxis: { gridcolor: 'rgba(148,163,184,0.07)', zeroline: false },
            legend: { orientation: 'h', y: 1.08, font: { size: 9 } },
            shapes: [
              {
                type: 'line', xref: 'paper', x0: 0, x1: 1, y0: 0, y1: 0,
                line: { color: '#48525E', width: 1, dash: 'dot' },
              },
            ],
          }}
          config={PLOTLY_CONFIG}
          style={{ width: '100%', height: '380px' }}
        />
      </PanelCard>

      <PanelCard>
        <StatLabel>Current Readings</StatLabel>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-[11.5px]">
            <thead>
              <tr className="border-b border-border/30 text-muted-foreground/60 uppercase tracking-wider text-[10px]">
                <th className="text-left py-2 px-2">Indicator</th>
                <th className="text-right py-2 px-2">Z-Score</th>
                <th className="text-right py-2 px-2">Signal</th>
                <th className="text-right py-2 px-2">|σ|</th>
              </tr>
            </thead>
            <tbody>
              {readings.map((r, i) => (
                <tr
                  key={i}
                  className={`border-b border-border/20 hover:bg-card/50 ${
                    r.isComposite ? 'font-bold' : ''
                  }`}
                >
                  <td className="py-1.5 px-2">{r.name}</td>
                  <td
                    className="py-1.5 px-2 text-right font-mono"
                    style={{ color: r.z > 0 ? '#48A86E' : '#D65656' }}
                  >
                    {fmtZ(r.z, 3)}
                  </td>
                  <td
                    className="py-1.5 px-2 text-right"
                    style={{ color: r.z > 0 ? '#48A86E' : '#D65656' }}
                  >
                    {r.signal}
                  </td>
                  <td className="py-1.5 px-2 text-right font-mono text-muted-foreground">
                    {Math.abs(r.z).toFixed(2)}σ
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PanelCard>

      {/* Correlation matrix */}
      {ts.correlations && ts.correlations[dim] && (
        <PanelCard>
          <StatLabel>Inter-Indicator Correlation — {dim}</StatLabel>
          <Plot
            data={[
              {
                z: ts.correlations[dim].matrix,
                x: ts.correlations[dim].names,
                y: ts.correlations[dim].names,
                text: ts.correlations[dim].matrix.map((row) =>
                  row.map((v) => v.toFixed(2))
                ),
                texttemplate: '%{text}',
                textfont: { size: 10 },
                type: 'heatmap',
                colorscale: [[0, '#D65656'], [0.5, '#141620'], [1, '#48A86E']],
                zmid: 0,
                zmin: -1,
                zmax: 1,
                showscale: false,
              },
            ]}
            layout={{
              height: 280,
              paper_bgcolor: 'rgba(0,0,0,0)',
              plot_bgcolor: 'rgba(0,0,0,0)',
              font: { family: 'Space Mono, monospace', size: 9, color: '#9AA4B2' },
              margin: { l: 110, r: 20, t: 50, b: 20 },
              xaxis: { side: 'top' },
              yaxis: { autorange: 'reversed' },
            }}
            config={PLOTLY_CONFIG}
            style={{ width: '100%', height: '280px' }}
          />
        </PanelCard>
      )}
    </div>
  );
}
