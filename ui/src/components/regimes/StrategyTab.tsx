'use client';

import type { StrategyData, RegimeModel } from './types';
import {
  ASSET_COLORS,
  PLOTLY_CONFIG,
  getRegimeColor,
  getRegimeOrder,
} from './constants';
import { fmtPctSigned, fmtNum, hexToRgb } from './helpers';
import { Plot, PanelCard, StatLabel } from './SharedComponents';

interface Props {
  strategy: StrategyData;
  model?: RegimeModel;
}

const MODEL_COLORS: Record<string, string> = {
  wf_best_asset: '#48A86E',
  diversified: '#4895B0',
  spy_bnh: '#6B8EAE',
};

export function StrategyTab({ strategy, model }: Props) {
  if (!strategy || !strategy.models) {
    return <p className="text-muted-foreground text-[12.5px]">No strategy data for this regime.</p>;
  }

  const stateOrder = getRegimeOrder(model);

  const models = strategy.models;
  const wf = models.wf_best_asset;
  const div = models.diversified;
  const spy = models.spy_bnh;

  // Build regime shading shapes
  const shapes: any[] = [];
  if (strategy.regime_history && strategy.regime_history.dates.length > 0) {
    const dates = strategy.regime_history.dates;
    const regimes = strategy.regime_history.regimes;
    let curRegime = regimes[0];
    let segStart = dates[0];
    for (let i = 1; i < dates.length; i++) {
      if (regimes[i] !== curRegime) {
        const c = getRegimeColor(curRegime, model);
        shapes.push({
          type: 'rect', xref: 'x', yref: 'paper',
          x0: segStart, x1: dates[i], y0: 0, y1: 1,
          fillcolor: c, opacity: 0.06, line: { width: 0 },
          layer: 'below',
        });
        curRegime = regimes[i];
        segStart = dates[i];
      }
    }
    const c = getRegimeColor(curRegime, model);
    shapes.push({
      type: 'rect', xref: 'x', yref: 'paper',
      x0: segStart, x1: dates[dates.length - 1], y0: 0, y1: 1,
      fillcolor: c, opacity: 0.06, line: { width: 0 },
      layer: 'below',
    });
  }

  return (
    <div className="space-y-4">
      <div className="text-[10.5px] uppercase tracking-wider text-muted-foreground/60">
        Strategy Backtest (1-month lag) · {strategy.months} months · {strategy.start_date} – {strategy.end_date} ·
        walk-forward {strategy.wf_lookback}m lookback · {strategy.num_assets} assets
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {[
          { key: 'wf_best_asset', m: wf },
          { key: 'diversified', m: div },
          { key: 'spy_bnh', m: spy },
        ].map(({ key, m }) => {
          if (!m) return null;
          const color = MODEL_COLORS[key];
          const rgb = hexToRgb(color);
          const beatsBenchmark = spy && m.stats.sharpe >= spy.stats.sharpe;
          return (
            <div
              key={key}
              className="rounded-[var(--radius)] border p-4"
              style={{
                background: `rgba(${rgb}, 0.04)`,
                borderColor: `rgba(${rgb}, 0.25)`,
              }}
            >
              <StatLabel>{m.label}</StatLabel>
              <div className="grid grid-cols-2 gap-3 mt-2">
                <div>
                  <div className="text-[9.5px] text-muted-foreground/40 uppercase">CAGR</div>
                  <div
                    className="font-mono text-base font-bold"
                    style={{ color: beatsBenchmark ? '#48A86E' : color }}
                  >
                    {(m.stats.cagr * 100).toFixed(1)}%
                  </div>
                </div>
                <div>
                  <div className="text-[9.5px] text-muted-foreground/40 uppercase">Sharpe</div>
                  <div
                    className="font-mono text-base font-bold"
                    style={{ color: beatsBenchmark ? '#48A86E' : color }}
                  >
                    {m.stats.sharpe.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-[9.5px] text-muted-foreground/40 uppercase">Max DD</div>
                  <div className="font-mono text-base font-bold text-destructive">
                    {(m.stats.max_dd * 100).toFixed(1)}%
                  </div>
                </div>
                <div>
                  <div className="text-[9.5px] text-muted-foreground/40 uppercase">Ann Vol</div>
                  <div className="font-mono text-base font-bold">
                    {(m.stats.ann_vol * 100).toFixed(1)}%
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Equity curves */}
      <PanelCard>
        <StatLabel>Equity Curves — Growth of $1 (log scale)</StatLabel>
        <Plot
          data={[
            wf && {
              x: wf.dates, y: wf.equity, name: wf.label,
              mode: 'lines', line: { color: MODEL_COLORS.wf_best_asset, width: 2 },
            },
            div && {
              x: div.dates, y: div.equity, name: div.label,
              mode: 'lines', line: { color: MODEL_COLORS.diversified, width: 2 },
            },
            spy && {
              x: spy.dates, y: spy.equity, name: spy.label,
              mode: 'lines', line: { color: MODEL_COLORS.spy_bnh, width: 1.5, dash: 'dot' },
            },
          ].filter(Boolean)}
          layout={{
            height: 420,
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { family: 'Space Mono, monospace', size: 10, color: '#9AA4B2' },
            margin: { l: 50, r: 20, t: 30, b: 36 },
            yaxis: { title: { text: 'Growth of $1' }, type: 'log', gridcolor: 'rgba(148,163,184,0.07)', zeroline: false },
            xaxis: { gridcolor: 'rgba(148,163,184,0.07)', zeroline: false },
            legend: { orientation: 'h', y: 1.08, x: 0 },
            shapes,
          }}
          config={PLOTLY_CONFIG}
          style={{ width: '100%', height: '420px' }}
        />
      </PanelCard>

      {/* Drawdown */}
      <PanelCard>
        <StatLabel>Drawdown</StatLabel>
        <Plot
          data={[
            wf && {
              x: wf.dates, y: wf.drawdown, name: wf.label,
              mode: 'lines', line: { color: MODEL_COLORS.wf_best_asset, width: 1 },
            },
            div && {
              x: div.dates, y: div.drawdown, name: div.label,
              mode: 'lines', line: { color: MODEL_COLORS.diversified, width: 1 },
            },
            spy && {
              x: spy.dates, y: spy.drawdown, name: spy.label,
              mode: 'lines', line: { color: MODEL_COLORS.spy_bnh, width: 1, dash: 'dot' },
            },
          ].filter(Boolean)}
          layout={{
            height: 240,
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { family: 'Space Mono, monospace', size: 10, color: '#9AA4B2' },
            margin: { l: 50, r: 20, t: 30, b: 36 },
            yaxis: { title: { text: 'Drawdown %' }, gridcolor: 'rgba(148,163,184,0.07)', zeroline: false },
            xaxis: { gridcolor: 'rgba(148,163,184,0.07)', zeroline: false },
            legend: { orientation: 'h', y: 1.12, x: 0 },
          }}
          config={PLOTLY_CONFIG}
          style={{ width: '100%', height: '240px' }}
        />
      </PanelCard>

      {/* Yearly returns */}
      {strategy.yearly_returns.length > 0 && (
        <PanelCard>
          <StatLabel>Yearly Returns & Alpha</StatLabel>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="border-b border-border/30 text-muted-foreground/60 uppercase tracking-wider text-[10px]">
                  <th className="text-left py-2 px-2">Year</th>
                  <th className="text-right py-2 px-2">WF Best</th>
                  <th className="text-right py-2 px-2">Diversified</th>
                  <th className="text-right py-2 px-2">SPY</th>
                  <th className="text-right py-2 px-2">WF α</th>
                  <th className="text-right py-2 px-2">Div α</th>
                </tr>
              </thead>
              <tbody>
                {strategy.yearly_returns.map((y) => (
                  <tr key={y.year} className="border-b border-border/20 hover:bg-card/50">
                    <td className="py-1.5 px-2 font-mono">{y.year}</td>
                    <td className="py-1.5 px-2 text-right font-mono">{fmtPctSigned(y.wf_best)}</td>
                    <td className="py-1.5 px-2 text-right font-mono">{fmtPctSigned(y.diversified)}</td>
                    <td className="py-1.5 px-2 text-right font-mono">{fmtPctSigned(y.spy)}</td>
                    <td
                      className="py-1.5 px-2 text-right font-mono"
                      style={{ color: y.wf_alpha >= 0 ? '#48A86E' : '#D65656' }}
                    >
                      {fmtPctSigned(y.wf_alpha)}
                    </td>
                    <td
                      className="py-1.5 px-2 text-right font-mono"
                      style={{ color: y.div_alpha >= 0 ? '#48A86E' : '#D65656' }}
                    >
                      {fmtPctSigned(y.div_alpha)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PanelCard>
      )}

      {/* 8-state allocation table */}
      <PanelCard>
        <StatLabel>8-State Allocation Templates (Macro × Liquidity)</StatLabel>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-border/30 text-muted-foreground/60 uppercase tracking-wider text-[10px]">
                <th className="text-left py-2 px-2">Regime</th>
                <th className="text-left py-2 px-2">Liquidity</th>
                {['SPY', 'IEF', 'GLD', 'TIP', 'BIL'].map((a) => (
                  <th key={a} className="text-center py-2 px-2">{a}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {stateOrder.flatMap((r) =>
                ['Easing', 'Tightening'].map((liq) => {
                  const key = `${r}+${liq}`;
                  const tmpl = strategy.allocation_templates[key];
                  if (!tmpl) return null;
                  const rColor = getRegimeColor(r, model);
                  const lColor = liq === 'Easing' ? '#48A86E' : '#D65656';
                  return (
                    <tr key={key} className="border-b border-border/20">
                      <td className="py-1.5 px-2 font-semibold" style={{ color: rColor }}>
                        {r}
                      </td>
                      <td className="py-1.5 px-2" style={{ color: lColor }}>
                        {liq}
                      </td>
                      {['SPY', 'IEF', 'GLD', 'TIP', 'BIL'].map((a) => {
                        const w = tmpl[a] ?? 0;
                        const pct = Math.round(w * 100);
                        return (
                          <td
                            key={a}
                            className="py-1.5 px-2 text-center font-mono"
                            style={{
                              opacity: pct > 0 ? 1 : 0.25,
                              fontWeight: pct >= 40 ? 600 : pct >= 20 ? 500 : 400,
                              background: pct >= 40 ? `rgba(${hexToRgb(rColor)}, 0.10)` : 'transparent',
                            }}
                          >
                            {pct}%
                          </td>
                        );
                      })}
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </PanelCard>
    </div>
  );
}
