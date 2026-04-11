'use client';

import type { TimeseriesData, RegimeModel } from './types';
import {
  PLOTLY_CONFIG,
  getRegimeColor,
  getDimensionColor,
  getRegimeOrder,
} from './constants';
import { hexToRgb } from './helpers';
import { Plot, PanelCard, StatLabel } from './SharedComponents';

interface Props {
  ts: TimeseriesData;
  model?: RegimeModel;
}

export function HistoryTab({ ts, model }: Props) {
  if (!ts || !ts.dates || ts.dates.length === 0) {
    return <p className="text-muted-foreground text-[12.5px]">No timeseries data.</p>;
  }

  // Use the model's declared state order so non-macro regimes (Credit, Dollar)
  // render in their semantic order instead of the macro default.
  const stateOrder = getRegimeOrder(model);
  const dimOrder = model?.dimensions ?? ['Growth', 'Inflation', 'Liquidity'];

  // Stacked area — use smoothed probabilities so the last data point
  // matches the CurrentStateTab hero probability (both read S_P_*).
  // Fall back to raw_probabilities for backward compatibility with
  // snapshots computed before the rename.
  const probSource = ts.smoothed_probabilities ?? ts.raw_probabilities ?? ts.probabilities ?? {};
  const probTraces = stateOrder
    .filter((r) => probSource[r])
    .map((r) => ({
      x: ts.dates,
      y: probSource[r],
      name: r,
      stackgroup: 'one',
      groupnorm: 'fraction' as const,
      fillcolor: `rgba(${hexToRgb(getRegimeColor(r, model))}, 0.65)`,
      line: { width: 0.8, color: getRegimeColor(r, model), shape: 'spline', smoothing: 0.6 },
      hovertemplate: '<b>%{data.name}</b>  %{y:.2f}<extra></extra>',
    }));

  // Composite z-scores — use model's dimensions
  const compTraces = dimOrder
    .filter((d) => ts.composites[`${d}_Z`])
    .map((d) => {
      const color = getDimensionColor(d, model);
      return {
        x: ts.dates,
        y: ts.composites[`${d}_Z`],
        name: d,
        mode: 'lines',
        line: { color, width: 2, shape: 'spline', smoothing: 0.6 },
        fill: 'tozeroy' as const,
        fillcolor: `rgba(${hexToRgb(color)}, 0.08)`,
        hovertemplate: '<b>%{data.name}</b>  %{y:+.2f}σ<extra></extra>',
      };
    });

  // Shared hover/axis styling — steel palette literals (Plotly needs concrete colors)
  const STEEL_TEXT = 'rgb(218,222,228)';
  const STEEL_MUTED = 'rgb(128,136,148)';
  const STEEL_GRID = 'rgba(198,204,214,0.05)';
  const STEEL_TICK = 'rgba(128,136,148,0.25)';
  const STEEL_PAPER = 'rgb(20,23,28)';

  const BODY_FONT = 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  const hoverlabel = {
    bgcolor: 'rgba(20,23,28,0.94)',
    bordercolor: 'rgba(128,136,148,0.35)',
    font: { family: BODY_FONT, size: 11, color: STEEL_TEXT },
    align: 'left' as const,
  };
  const spikeAxis = {
    showspikes: true,
    spikemode: 'across' as const,
    spikedash: 'dot' as const,
    spikethickness: 1,
    spikecolor: 'rgba(128,136,148,0.4)',
  };

  return (
    <div className="space-y-4">
      <PanelCard>
        <StatLabel>Regime Probability History — stacked area shows transitions</StatLabel>
        <Plot
          data={probTraces}
          layout={{
            height: 320,
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { family: BODY_FONT, size: 10, color: STEEL_MUTED },
            margin: { l: 52, r: 16, t: 36, b: 36 },
            hovermode: 'x unified',
            hoverlabel,
            yaxis: {
              title: { text: 'Probability', font: { family: BODY_FONT, size: 10, color: STEEL_MUTED }, standoff: 8 },
              tickfont: { family: BODY_FONT },
              tickformat: '.0%',
              range: [0, 1],
              gridcolor: STEEL_GRID,
              zeroline: false,
              fixedrange: true,
              ticks: 'outside',
              ticklen: 3,
              tickcolor: STEEL_TICK,
            },
            xaxis: {
              tickfont: { family: BODY_FONT },
              gridcolor: STEEL_GRID,
              zeroline: false,
              hoverformat: '%b %Y',
              tickformat: '%Y',
              ticks: 'outside',
              ticklen: 3,
              tickcolor: STEEL_TICK,
              ...spikeAxis,
            },
            legend: {
              orientation: 'h',
              y: 1.12,
              x: 0,
              xanchor: 'left',
              font: { family: BODY_FONT, size: 10, color: STEEL_TEXT },
              bgcolor: 'rgba(0,0,0,0)',
              itemsizing: 'constant',
              traceorder: 'normal',
            },
          }}
          config={PLOTLY_CONFIG}
          style={{ width: '100%', height: '320px' }}
        />
      </PanelCard>

      <PanelCard>
        <StatLabel>Composite Z-Scores — {dimOrder.join(' · ')}</StatLabel>
        <Plot
          data={compTraces}
          layout={{
            height: 280,
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { family: 'Space Mono, monospace', size: 10, color: STEEL_MUTED },
            margin: { l: 52, r: 16, t: 36, b: 36 },
            hovermode: 'x unified',
            hoverlabel,
            yaxis: {
              title: { text: 'Z-Score', font: { size: 10, color: STEEL_MUTED }, standoff: 8 },
              gridcolor: STEEL_GRID,
              zeroline: true,
              zerolinecolor: STEEL_TICK,
              zerolinewidth: 1,
              ticks: 'outside',
              ticklen: 3,
              tickcolor: STEEL_TICK,
              tickformat: '+.1f',
            },
            xaxis: {
              gridcolor: STEEL_GRID,
              zeroline: false,
              hoverformat: '%b %Y',
              tickformat: '%Y',
              ticks: 'outside',
              ticklen: 3,
              tickcolor: STEEL_TICK,
              ...spikeAxis,
            },
            legend: {
              orientation: 'h',
              y: 1.12,
              x: 0,
              xanchor: 'left',
              font: { size: 10, color: STEEL_TEXT },
              bgcolor: 'rgba(0,0,0,0)',
              itemsizing: 'constant',
            },
            shapes: [
              // ±1σ reference bands
              {
                type: 'rect', xref: 'paper', x0: 0, x1: 1, y0: -1, y1: 1,
                fillcolor: 'rgba(198,204,214,0.04)', line: { width: 0 }, layer: 'below',
              },
            ],
          }}
          config={PLOTLY_CONFIG}
          style={{ width: '100%', height: '280px' }}
        />
      </PanelCard>

      {/* Transition matrix + durations side-by-side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {ts.transition_matrix && Object.keys(ts.transition_matrix).length > 0 && (
          <PanelCard>
            <StatLabel>Transition Probability Matrix — P(row → col)</StatLabel>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-[11.5px]">
                <thead>
                  <tr className="border-b border-border/30 text-muted-foreground/60 uppercase tracking-wider text-[10px]">
                    <th className="text-left py-2 px-2">From \ To</th>
                    {stateOrder.map((r) => (
                      <th key={r} className="text-center py-2 px-2" style={{ color: getRegimeColor(r, model) }}>
                        {r.slice(0, 4)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {stateOrder.map((from) => {
                    const row = ts.transition_matrix![from] || {};
                    return (
                      <tr key={from} className="border-b border-border/20">
                        <td
                          className="py-2 px-2 font-semibold"
                          style={{ color: getRegimeColor(from, model) }}
                        >
                          {from}
                        </td>
                        {stateOrder.map((to) => {
                          const p = row[to] ?? 0;
                          const pct = Math.round(p * 100);
                          const isDiagonal = from === to;
                          const cellColor =
                            isDiagonal && pct >= 50
                              ? 'rgb(var(--success))'
                              : !isDiagonal && pct >= 20
                              ? 'rgb(var(--accent))'
                              : pct === 0
                              ? 'rgb(var(--muted-foreground) / 0.4)'
                              : undefined;
                          return (
                            <td
                              key={to}
                              className="py-2 px-2 text-center font-mono"
                              style={{
                                color: cellColor,
                                fontWeight: isDiagonal ? 600 : pct >= 20 ? 500 : 400,
                                background: isDiagonal
                                  ? `rgba(${hexToRgb(getRegimeColor(from, model))}, 0.05)`
                                  : 'transparent',
                              }}
                            >
                              {pct}%
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </PanelCard>
        )}

        {ts.durations && (
          <PanelCard>
            <StatLabel>Average Regime Duration</StatLabel>
            <Plot
              data={[
                {
                  x: stateOrder.map((r) => ts.durations![r]?.avg_months ?? 0),
                  y: stateOrder,
                  type: 'bar',
                  orientation: 'h',
                  marker: { color: stateOrder.map((r) => getRegimeColor(r, model)) },
                  text: stateOrder.map((r) =>
                    `${(ts.durations![r]?.avg_months ?? 0).toFixed(1)}mo (${ts.durations![r]?.episodes ?? 0} ep)`
                  ),
                  textposition: 'outside',
                  textfont: { size: 10, family: BODY_FONT },
                  hovertemplate: '<b>%{y}</b>: %{text}<extra></extra>',
                },
              ]}
              layout={{
                height: 260,
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: { family: BODY_FONT, size: 10, color: STEEL_MUTED },
                margin: { l: 90, r: 100, t: 30, b: 30 },
                xaxis: {
                  title: { text: 'Avg Duration (months)', font: { family: BODY_FONT } },
                  tickfont: { family: BODY_FONT },
                  gridcolor: STEEL_GRID,
                  zeroline: false,
                },
                yaxis: { autorange: 'reversed', tickfont: { family: BODY_FONT } },
                showlegend: false,
              }}
              config={PLOTLY_CONFIG}
              style={{ width: '100%', height: '260px' }}
            />
          </PanelCard>
        )}
      </div>

      {/* Recent transitions table */}
      {ts.transitions_recent && ts.transitions_recent.length > 0 && (
        <PanelCard>
          <StatLabel>Recent Regime Transitions (last 36 months)</StatLabel>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-[11.5px]">
              <thead>
                <tr className="border-b border-border/30 text-muted-foreground/60 uppercase tracking-wider text-[10px]">
                  <th className="text-left py-2 px-2">Date</th>
                  <th className="text-left py-2 px-2">Regime</th>
                  <th className="text-right py-2 px-2">Probability</th>
                </tr>
              </thead>
              <tbody>
                {ts.transitions_recent.map((row, i) => (
                  <tr key={i} className="border-b border-border/20 hover:bg-card/50">
                    <td className="py-1.5 px-2 font-mono text-muted-foreground">{row.date}</td>
                    <td
                      className="py-1.5 px-2 font-semibold"
                      style={{ color: getRegimeColor(row.regime, model) }}
                    >
                      {row.regime}
                    </td>
                    <td className="py-1.5 px-2 text-right font-mono">{row.probability}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PanelCard>
      )}
    </div>
  );
}
