'use client';

import { useState } from 'react';
import type { AssetAnalytics, RegimeModel, AssetStat } from './types';
import { getRegimeColor, getRegimeOrder } from './constants';
import { hexToRgb } from './helpers';
import { PanelCard, StatLabel } from './SharedComponents';

interface Props {
  analytics: AssetAnalytics;
  model?: RegimeModel;
}

type MetricKey = 'ann_ret' | 'sharpe' | 'max_dd' | 'ann_vol' | 'win_rate';

const METRIC_OPTIONS: { key: MetricKey; label: string; short: string; title: string }[] = [
  { key: 'ann_ret', label: 'Annual Return', short: 'Return', title: 'Annualized return in this regime' },
  { key: 'sharpe', label: 'Sharpe Ratio', short: 'Sharpe', title: 'Annualized Sharpe ratio (excess return / volatility)' },
  { key: 'max_dd', label: 'Max Drawdown', short: 'Max DD', title: 'Maximum peak-to-trough drawdown in this regime' },
  { key: 'ann_vol', label: 'Volatility', short: 'Vol', title: 'Annualized volatility (stdev of returns)' },
  { key: 'win_rate', label: 'Win Rate', short: 'Win %', title: 'Share of months with positive return' },
];

// Institutional palette: 3-tier semantic colors via CSS vars.
// Inline style resolves var() at paint time, so these strings work in JSX.
const COLOR_POSITIVE = 'rgb(var(--success))';
const COLOR_NEGATIVE = 'rgb(var(--destructive))';
const COLOR_NEUTRAL = 'rgb(var(--warning))';
const COLOR_MUTED = 'rgb(var(--muted-foreground) / 0.4)';

function retColor(ret: number | null | undefined): string {
  if (ret === null || ret === undefined) return COLOR_MUTED;
  if (ret > 0.05) return COLOR_POSITIVE;
  if (ret > -0.05) return COLOR_NEUTRAL;
  return COLOR_NEGATIVE;
}

function sharpeColor(sharpe: number | null | undefined): string {
  if (sharpe === null || sharpe === undefined) return COLOR_MUTED;
  if (sharpe > 0.5) return COLOR_POSITIVE;
  if (sharpe > 0.0) return COLOR_NEUTRAL;
  return COLOR_NEGATIVE;
}

/** Cohen's d color tiers — 3-tier semantic (institutional). */
function cohensDColor(d: number | null | undefined): string {
  if (d === null || d === undefined) return COLOR_MUTED;
  const ad = Math.abs(d);
  if (ad >= 0.5) return COLOR_POSITIVE;
  if (ad >= 0.2) return COLOR_NEUTRAL;
  return COLOR_NEGATIVE;
}

function pValueTier(p: number | null | undefined): string {
  if (p === null || p === undefined) return '';
  if (p < 0.001) return '***';
  if (p < 0.01) return '**';
  if (p < 0.05) return '*';
  if (p < 0.10) return '†';
  return '';
}

function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined) return '—';
  return `${(v * 100).toFixed(digits)}%`;
}

function fmtSharpe(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—';
  return v.toFixed(2);
}

function volColor(v: number | null | undefined): string {
  if (v === null || v === undefined) return COLOR_MUTED;
  if (v < 0.18) return COLOR_POSITIVE;
  if (v < 0.28) return COLOR_NEUTRAL;
  return COLOR_NEGATIVE;
}

function winColor(v: number | null | undefined): string {
  if (v === null || v === undefined) return COLOR_MUTED;
  if (v >= 0.55) return COLOR_POSITIVE;
  if (v >= 0.45) return COLOR_NEUTRAL;
  return COLOR_NEGATIVE;
}

function ddColor(v: number | null | undefined): string {
  if (v === null || v === undefined) return COLOR_MUTED;
  // max_dd is negative (e.g. -0.25)
  if (v > -0.15) return COLOR_POSITIVE;
  if (v > -0.30) return COLOR_NEUTRAL;
  return COLOR_NEGATIVE;
}

function getMetricValue(a: AssetStat | undefined, m: MetricKey): number | null | undefined {
  if (!a) return undefined;
  return a[m];
}

function formatMetric(v: number | null | undefined, m: MetricKey): string {
  if (v === null || v === undefined) return '—';
  switch (m) {
    case 'ann_ret':
    case 'ann_vol':
      return `${(v * 100).toFixed(1)}%`;
    case 'max_dd':
      return `${(v * 100).toFixed(0)}%`;
    case 'win_rate':
      return `${Math.round(v * 100)}%`;
    case 'sharpe':
      return v.toFixed(2);
  }
}

function metricColor(v: number | null | undefined, m: MetricKey): string {
  switch (m) {
    case 'ann_ret':
      return retColor(v);
    case 'sharpe':
      return sharpeColor(v);
    case 'ann_vol':
      return volColor(v);
    case 'win_rate':
      return winColor(v);
    case 'max_dd':
      return ddColor(v);
  }
}

export function AssetPerformanceTab({ analytics, model }: Props) {
  const [metric, setMetric] = useState<MetricKey>('ann_ret');

  if (!analytics || !analytics.per_regime_stats) {
    return (
      <p className="text-muted-foreground text-[12.5px]">
        No asset analytics for this regime.
      </p>
    );
  }

  const activeMetric = METRIC_OPTIONS.find((o) => o.key === metric)!;

  const stateOrder = getRegimeOrder(model);
  const liqSplits = analytics.liquidity_splits || {};
  const hasLiqSplits = Object.keys(liqSplits).length > 0;
  const regimeCounts = analytics.regime_counts || {};
  const separation = analytics.regime_separation || {};

  // Build a lookup: {asset -> {state -> AssetStat}}
  const lookup: Record<string, Record<string, AssetStat>> = {};
  for (const state of stateOrder) {
    const stats = analytics.per_regime_stats[state];
    if (!stats) continue;
    for (const a of stats.assets) {
      if (!lookup[a.ticker]) lookup[a.ticker] = {};
      lookup[a.ticker][state] = a;
    }
  }

  // Sort tickers by |Cohen's d| descending — best-separated assets first.
  // Assets without separation data sink to the bottom.
  const tickers = [...analytics.tickers].sort((a, b) => {
    const da = Math.abs(separation[a]?.cohens_d ?? -Infinity);
    const db = Math.abs(separation[b]?.cohens_d ?? -Infinity);
    return db - da;
  });

  return (
    <div className="space-y-4">
      {/* ── Unified 2D table: all regimes × all assets × selectable metric ── */}
      <PanelCard>
        <div className="flex flex-wrap items-baseline justify-between gap-3 mb-3">
          <StatLabel>Asset Performance by Regime</StatLabel>
          <div className="flex items-center border border-border/50" role="tablist" aria-label="Metric">
            {METRIC_OPTIONS.map((opt, idx) => {
              const active = opt.key === metric;
              return (
                <button
                  key={opt.key}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  onClick={() => setMetric(opt.key)}
                  title={opt.title}
                  className={`relative h-6 px-2.5 text-[10px] font-mono font-semibold uppercase tracking-[0.08em] transition-colors ${
                    active ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
                  } ${idx > 0 ? 'border-l border-border/50' : ''}`}
                >
                  {opt.short}
                  {active && (
                    <span className="absolute left-1 right-1 bottom-0 h-[2px] bg-accent" aria-hidden />
                  )}
                </button>
              );
            })}
          </div>
          <span className="text-[10.5px] text-muted-foreground/60 basis-full md:basis-auto">
            Sorted by |Cohen&apos;s d| · showing {activeMetric.label} · n&lt;12 dimmed
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-[11px] border-collapse">
            <thead>
              <tr className="border-b border-border/40">
                <th className="py-2 px-2 text-left text-[9.5px] uppercase tracking-wider text-muted-foreground/50 sticky left-0 bg-background align-bottom">
                  Asset
                </th>
                <th
                  className="py-2 px-2 text-right text-[9.5px] uppercase tracking-wider text-muted-foreground/50 border-l border-border/40 align-bottom"
                  title="Cohen's d — standardized mean difference between best and worst regime states. Scale-free, comparable across assets and regimes. Finance thresholds: |d|>0.2 meaningful, |d|>0.5 strong, |d|>1.0 exceptional. ***p<0.001, **p<0.01, *p<0.05, †p<0.10 from Welch's t-test (best vs worst state)."
                >
                  Cohen d
                </th>
                {stateOrder.map((state) => {
                  const color = getRegimeColor(state, model);
                  const rgb = hexToRgb(color);
                  const count = regimeCounts[state]?.months ?? 0;
                  return (
                    <th
                      key={state}
                      className="py-2 px-2 text-center text-[10px] font-bold uppercase tracking-[0.06em] border-l border-border/30 align-bottom whitespace-nowrap leading-tight min-w-[92px]"
                      style={{
                        color,
                        background: `rgba(${rgb}, 0.04)`,
                      }}
                    >
                      <div className="truncate" title={state}>{state}</div>
                      <div className="text-[9px] font-mono tabular-nums text-muted-foreground mt-0.5 normal-case tracking-normal">
                        {count} mo
                      </div>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {tickers.map((ticker) => {
                const sep = separation[ticker];
                const d = sep?.cohens_d;
                const p = sep?.p_value;
                const stars = pValueTier(p);
                return (
                  <tr key={ticker} className="border-b border-border/20 odd:bg-[rgb(var(--surface))]/30 hover:bg-[rgb(var(--surface))]/60 transition-colors">
                    <td className="py-1.5 px-2 font-mono font-semibold sticky left-0 bg-background">
                      {ticker}
                    </td>
                    <td
                      className="py-1.5 px-2 text-right font-mono font-semibold border-l border-border/40"
                      style={{ color: cohensDColor(d) }}
                      title={
                        sep
                          ? `Cohen's d = ${d?.toFixed(3) ?? '—'} (best=${sep.best_state} vs worst=${sep.worst_state}) · Welch p = ${p?.toExponential(2) ?? '—'} · n = ${sep.n}`
                          : 'no data'
                      }
                    >
                      {d !== null && d !== undefined ? d.toFixed(2) : '—'}
                      {stars && (
                        <span className="text-[9px] ml-0.5 text-muted-foreground">
                          {stars}
                        </span>
                      )}
                    </td>
                    {stateOrder.map((state) => {
                      const a = lookup[ticker]?.[state];
                      const rgb = hexToRgb(getRegimeColor(state, model));
                      const n = a?.months ?? 0;
                      const dim = !a || n < 12;
                      const opacity = dim ? 0.45 : 1;
                      const value = getMetricValue(a, metric);
                      return (
                        <td
                          key={`${ticker}-${state}`}
                          className="py-1.5 px-2 text-right font-mono border-l border-border/30"
                          style={{
                            color: metricColor(value, metric),
                            opacity,
                            background: `rgba(${rgb}, 0.02)`,
                            fontWeight: metric === 'sharpe' ? 600 : 500,
                          }}
                          title={
                            a
                              ? `${ticker} · ${state}\nReturn: ${fmtPct(a.ann_ret)}\nSharpe: ${fmtSharpe(a.sharpe)}\nVol: ${fmtPct(a.ann_vol)}\nMax DD: ${fmtPct(a.max_dd, 0)}\nWin rate: ${fmtPct(a.win_rate, 0)}\nn = ${n} months`
                              : 'no data'
                          }
                        >
                          {formatMetric(value, metric)}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Expected returns row — separate because it's across-regime */}
        {Object.keys(analytics.expected_returns || {}).length > 0 && (
          <div className="mt-4 pt-3 border-t border-border/30">
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground/60 mb-2">
              Current Probability-Weighted Expected Annual Return
            </div>
            <div className="flex flex-wrap gap-2">
              {Object.entries(analytics.expected_returns)
                .sort((a, b) => b[1] - a[1])
                .map(([ticker, ret]) => (
                  <div
                    key={ticker}
                    className="rounded-[var(--radius)] border border-border/40 px-2.5 py-1.5 text-[11px]"
                    style={{
                      background: `rgba(${hexToRgb(retColor(ret))}, 0.06)`,
                      borderColor: `rgba(${hexToRgb(retColor(ret))}, 0.25)`,
                    }}
                  >
                    <span className="font-mono font-semibold">{ticker}</span>
                    <span
                      className="font-mono ml-2"
                      style={{ color: retColor(ret) }}
                    >
                      {ret >= 0 ? '+' : ''}
                      {(ret * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
            </div>
          </div>
        )}
      </PanelCard>

      {/* ── 3D Liquidity split table (macro regimes only) ── */}
      {hasLiqSplits && (
        <PanelCard>
          <div className="flex justify-between items-baseline mb-3">
            <StatLabel>3D Asset Performance — Regime × Liquidity</StatLabel>
            <span className="text-[10.5px] text-muted-foreground/60">
              Annualized return · cells with n&lt;12 dimmed
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-[11px] border-collapse">
              <thead>
                <tr className="border-b border-border/40">
                  <th className="py-1.5 px-2 text-left text-[9.5px] uppercase tracking-wider text-muted-foreground/50 sticky left-0 bg-background">
                    Asset
                  </th>
                  {stateOrder.map((r) => (
                    <th
                      key={r}
                      colSpan={2}
                      className="py-1.5 px-2 text-center text-[10px] font-bold uppercase tracking-wider border-l border-border/30 whitespace-normal break-words leading-tight min-w-[96px] max-w-[140px]"
                      style={{ color: getRegimeColor(r, model) }}
                    >
                      {r}
                    </th>
                  ))}
                </tr>
                <tr className="border-b border-border/40">
                  <th className="sticky left-0 bg-background" />
                  {stateOrder.flatMap((r) => [
                    <th
                      key={`${r}-sup`}
                      className="py-1.5 px-2 text-center text-[9px] uppercase tracking-wider text-success/80 border-l border-border/30"
                    >
                      +Liq
                    </th>,
                    <th
                      key={`${r}-str`}
                      className="py-1.5 px-2 text-center text-[9px] uppercase tracking-wider text-destructive/70"
                    >
                      −Liq
                    </th>,
                  ])}
                </tr>
              </thead>
              <tbody>
                {tickers.map((t) => (
                  <tr key={t} className="border-b border-border/20 odd:bg-[rgb(var(--surface))]/30 hover:bg-[rgb(var(--surface))]/60 transition-colors">
                    <td className="py-1.5 px-2 font-mono font-semibold sticky left-0 bg-background">
                      {t}
                    </td>
                    {stateOrder.flatMap((r) => {
                      const cells: React.ReactElement[] = [];
                      for (const liqState of ['supportive', 'stressed'] as const) {
                        const bucket = liqSplits[r]?.[liqState];
                        const a = bucket?.assets.find((x) => x.ticker === t);
                        const n = a?.months ?? 0;
                        const ret = a?.ann_ret;
                        const dim = n < 12;
                        cells.push(
                          <td
                            key={`${t}-${r}-${liqState}`}
                            className="py-1.5 px-2 text-center font-mono border-l border-border/30"
                            style={{
                              color: retColor(ret),
                              opacity: dim ? 0.4 : 1,
                            }}
                          >
                            {fmtPct(ret)}
                          </td>,
                        );
                      }
                      return cells;
                    })}
                  </tr>
                ))}
                <tr className="border-t border-border/30 text-muted-foreground/40 text-[9.5px]">
                  <td className="py-1.5 px-2 uppercase tracking-wider sticky left-0 bg-background">
                    months
                  </td>
                  {stateOrder.flatMap((r) => [
                    <td
                      key={`${r}-sup-n`}
                      className="py-1.5 px-2 text-right font-mono border-l border-border/30"
                    >
                      {liqSplits[r]?.supportive?.months ?? 0}
                    </td>,
                    <td key={`${r}-str-n`} className="py-1.5 px-2 text-right font-mono">
                      {liqSplits[r]?.stressed?.months ?? 0}
                    </td>,
                  ])}
                </tr>
              </tbody>
            </table>
          </div>
        </PanelCard>
      )}
    </div>
  );
}
