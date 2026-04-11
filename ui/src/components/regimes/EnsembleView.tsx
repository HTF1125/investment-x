'use client';

import type { EnsembleResponse, EnsembleDriver, RegimeModel } from './types';
import { ASSET_COLORS, PLOTLY_CONFIG } from './constants';
import { hexToRgb, fmtPctSigned } from './helpers';
import { Plot, PanelCard, StatLabel } from './SharedComponents';
import { StrategyTab } from './StrategyTab';

type Universe = 'broad' | 'equity';

interface Props {
  data: EnsembleResponse;
  universe: Universe;
  onUniverseChange: (u: Universe) => void;
}

const COLOR_POSITIVE = 'rgb(var(--success))';
const COLOR_NEGATIVE = 'rgb(var(--destructive))';
const COLOR_MUTED = 'rgb(var(--muted-foreground) / 0.4)';

function icColor(ic: number): string {
  const abs = Math.abs(ic);
  if (abs >= 0.15) return COLOR_POSITIVE;
  if (abs >= 0.10) return 'rgb(var(--warning))';
  return COLOR_MUTED;
}

/** Synthetic RegimeModel so StrategyTab renders correctly. */
const ENSEMBLE_MODEL: RegimeModel = {
  key: 'ensemble',
  display_name: 'IC-Weighted Ensemble',
  description: 'Walk-forward IC-weighted combination of all regimes',
  states: ['Ensemble'],
  dimensions: [],
  has_strategy: true,
  color_map: { Ensemble: '#6382ff' },
  dimension_colors: {},
  default_params: {},
};

const UNIVERSE_OPTIONS: { key: Universe; label: string; title: string }[] = [
  { key: 'broad', label: 'Broad', title: 'All 11 ETFs — equities, bonds, commodities, gold, cash' },
  { key: 'equity', label: 'Equity', title: 'Equity regions only — SPY, IWM, EFA, EEM + BIL cash' },
];

export function EnsembleView({ data, universe, onUniverseChange }: Props) {
  const meta = data.ensemble_meta;
  const weights = data.current_weights;
  const drivers = data.regime_drivers;
  const wf = data.models?.wf_best_asset;
  const spy = data.models?.spy_bnh;

  const sortedAssets = Object.entries(weights)
    .filter(([, w]) => w > 0.001)
    .sort((a, b) => b[1] - a[1]);

  const alpha = wf && spy ? wf.stats.cagr - spy.stats.cagr : 0;

  return (
    <div className="space-y-4">
      {/* ── Header ── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">IC-Weighted Ensemble</h2>
          <p className="text-[11px] text-muted-foreground/60 font-mono uppercase tracking-wider mt-1">
            {meta.total_regimes} regimes · {meta.horizon_months}M forward · p&lt;{meta.significance_threshold} threshold · {data.months} months · {meta.warmup_months}M warmup · {data.cost_bps ?? 10}bps cost
          </p>
        </div>
        <div className="flex items-center border border-border/50" role="tablist" aria-label="Universe">
          {UNIVERSE_OPTIONS.map((opt, idx) => {
            const active = opt.key === universe;
            return (
              <button
                key={opt.key}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => onUniverseChange(opt.key)}
                title={opt.title}
                className={`relative h-7 px-3 text-[10px] font-mono font-semibold uppercase tracking-[0.08em] transition-colors ${
                  active ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
                } ${idx > 0 ? 'border-l border-border/50' : ''}`}
              >
                {opt.label}
                {active && (
                  <span className="absolute left-1 right-1 bottom-0 h-[2px] bg-foreground" aria-hidden />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Stats strip ── */}
      {wf && spy && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[
            { label: 'CAGR', value: `${(wf.stats.cagr * 100).toFixed(1)}%`, color: wf.stats.cagr > spy.stats.cagr ? COLOR_POSITIVE : COLOR_NEGATIVE },
            { label: 'Sharpe', value: wf.stats.sharpe.toFixed(2), color: wf.stats.sharpe > spy.stats.sharpe ? COLOR_POSITIVE : COLOR_NEGATIVE },
            { label: 'Max DD', value: `${(wf.stats.max_dd * 100).toFixed(1)}%`, color: COLOR_NEGATIVE },
            { label: 'Alpha vs SPY', value: fmtPctSigned(alpha), color: alpha >= 0 ? COLOR_POSITIVE : COLOR_NEGATIVE },
            { label: 'SPY Sharpe', value: spy.stats.sharpe.toFixed(2), color: COLOR_MUTED },
          ].map(({ label, value, color }) => (
            <PanelCard key={label}>
              <div className="text-[9.5px] uppercase tracking-wider text-muted-foreground/50">{label}</div>
              <div className="font-mono text-xl font-bold mt-1" style={{ color }}>{value}</div>
            </PanelCard>
          ))}
        </div>
      )}

      {/* ── Current allocation ── */}
      <PanelCard>
        <StatLabel>Current Allocation</StatLabel>
        <div className="mt-3 space-y-1.5">
          {sortedAssets.map(([ticker, w]) => {
            const color = ASSET_COLORS[ticker] || '#9AA4B2';
            return (
              <div key={ticker} className="flex items-center gap-2">
                <span className="font-mono font-semibold text-[11px] w-8 text-right">{ticker}</span>
                <div className="flex-1 h-5 rounded-sm overflow-hidden bg-muted/20 relative">
                  <div
                    className="h-full rounded-sm"
                    style={{
                      width: `${Math.max(w * 100, 1)}%`,
                      background: `rgba(${hexToRgb(color)}, 0.5)`,
                    }}
                  />
                </div>
                <span className="font-mono text-[11px] w-10 text-right text-muted-foreground">{Math.round(w * 100)}%</span>
              </div>
            );
          })}
        </div>
      </PanelCard>

      {/* ── Regime drivers per asset ── */}
      <PanelCard>
        <StatLabel>Regime Drivers by Asset</StatLabel>
        <p className="text-[10px] text-muted-foreground/50 mt-0.5 mb-3">
          Which regimes predict each asset (p&lt;{meta.significance_threshold}) and their current signal
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-[11px] border-collapse">
            <thead>
              <tr className="border-b border-border/40">
                <th className="py-2 px-2 text-left text-[9.5px] uppercase tracking-wider text-muted-foreground/50">Asset</th>
                <th className="py-2 px-2 text-right text-[9.5px] uppercase tracking-wider text-muted-foreground/50">Weight</th>
                <th className="py-2 px-2 text-left text-[9.5px] uppercase tracking-wider text-muted-foreground/50">Significant Regimes (IC, Z)</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(drivers)
                .sort((a, b) => (weights[b[0]] ?? 0) - (weights[a[0]] ?? 0))
                .map(([asset, driverList]) => (
                  <tr key={asset} className="border-b border-border/20 hover:bg-[rgb(var(--surface))]/60 transition-colors">
                    <td className="py-1.5 px-2 font-mono font-semibold">{asset}</td>
                    <td className="py-1.5 px-2 text-right font-mono">
                      {weights[asset] ? `${Math.round(weights[asset] * 100)}%` : '—'}
                    </td>
                    <td className="py-1.5 px-2">
                      <div className="flex flex-wrap gap-1.5">
                        {driverList.map((d: EnsembleDriver) => (
                          <span
                            key={d.regime}
                            className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9.5px] font-mono border border-border/30"
                            title={`IC=${d.ic.toFixed(3)} Z=${d.z_current.toFixed(2)} p=${d.ic_pvalue?.toFixed(3) ?? '?'}`}
                          >
                            <span className="font-semibold">{d.regime.replace(/_/g, ' ')}</span>
                            <span style={{ color: icColor(d.ic) }}>
                              {d.ic >= 0 ? '+' : ''}{d.ic.toFixed(2)}
                            </span>
                            <span className="text-muted-foreground/50">
                              Z{d.z_current >= 0 ? '+' : ''}{d.z_current.toFixed(1)}
                            </span>
                          </span>
                        ))}
                        {driverList.length === 0 && (
                          <span className="text-muted-foreground/40 text-[10px]">no significant regime</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </PanelCard>

      {/* ── Backtest (reuse StrategyTab) ── */}
      <StrategyTab strategy={data} model={ENSEMBLE_MODEL} />
    </div>
  );
}
