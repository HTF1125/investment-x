'use client';

import { useState } from 'react';
import { Info } from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';
import type { CurrentState, RegimeModel } from './types';
import {
  ASSET_COLORS,
  PLOTLY_CONFIG,
  getRegimeColor,
  getDimensionColor,
  getRegimeDescription,
} from './constants';
import { fmtPct, fmtZ, hexToRgb } from './helpers';
import { Plot, PanelCard, StatLabel } from './SharedComponents';

interface Props {
  state: CurrentState;
  model?: RegimeModel;
}

/** Inline SVG sparkline for dimension Z history. Renders a single
 * smoothed polyline normalized to the [-2, +2] z range and a faint
 * zero baseline. Returns null if there's no data. */
function Sparkline({
  values,
  width = 90,
  height = 22,
}: {
  values: number[] | undefined;
  color?: string;
  width?: number;
  height?: number;
}) {
  if (!values || values.length < 2) return null;
  // Clamp to [-2, +2] z range so sparklines across dimensions stay
  // visually comparable.
  const clamped = values.map((v) => Math.max(-2, Math.min(2, v)));
  const range = 4;
  const stepX = width / (clamped.length - 1);
  const points = clamped
    .map((v, i) => {
      const x = i * stepX;
      const y = height - ((v + 2) / range) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
  const zeroY = height / 2;
  const last = clamped[clamped.length - 1];
  const lastX = (clamped.length - 1) * stepX;
  const lastY = height - ((last + 2) / range) * height;
  return (
    <svg width={width} height={height} className="overflow-visible">
      <line
        x1="0"
        x2={width}
        y1={zeroY}
        y2={zeroY}
        stroke="rgb(var(--border))"
        strokeDasharray="2 2"
        strokeWidth="0.75"
      />
      <polyline
        fill="none"
        stroke="rgb(var(--foreground) / 0.85)"
        strokeWidth="1.25"
        strokeLinejoin="round"
        strokeLinecap="round"
        points={points}
      />
      <circle cx={lastX} cy={lastY} r="1.75" fill="rgb(var(--accent))" />
    </svg>
  );
}

/** Joint state shorthand chips. Splits "Strong+Appreciating+Steep" into
 * three colored pills using the joint model's per-dimension colors. */
function JointStateChips({ dom, model }: { dom: string; model?: RegimeModel }) {
  const parts = dom.split('+');
  if (parts.length < 2) return null;
  const dims = model?.dimensions ?? [];
  return (
    <div className="flex items-center gap-1 flex-wrap mt-2">
      {parts.map((p, i) => {
        const dimName = dims[i];
        const c = dimName ? getDimensionColor(dimName, model) : undefined;
        return (
          <span
            key={i}
            className="px-1.5 py-0.5 text-[9.5px] font-mono font-semibold uppercase tracking-[0.04em] text-foreground border border-border bg-card"
            style={c ? { borderLeft: `3px solid ${c}` } : undefined}
            title={dimName}
          >
            {p}
          </span>
        );
      })}
    </div>
  );
}

export function CurrentStateTab({ state, model }: Props) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const [gatesExplainerOpen, setGatesExplainerOpen] = useState(false);

  if (!state || state.error || !state.date) {
    return <p className="text-muted-foreground text-[12.5px]">No regime data available.</p>;
  }

  const dom = state.dominant;
  const domColor = getRegimeColor(dom, model);
  const domRgb = hexToRgb(domColor);
  const domDesc = getRegimeDescription(dom, model);

  const regimeDims = model?.dimensions ?? Object.keys(state.dimensions ?? {});
  const isComposite = (dom.split('+').length > 1);

  // Conviction color by threshold (red < 40, amber 40-60, green > 60)
  const convictionColor =
    state.conviction >= 60 ? 'rgb(var(--success))' :
    state.conviction >= 40 ? 'rgb(var(--warning))' : 'rgb(var(--destructive))';

  return (
    <div className="space-y-4">
      {/* ── Decision Card — top row (composite mode only) ── */}
      {state.decision_card && (() => {
        const dc = state.decision_card!;
        const verdictColor =
          dc.verdict === 'RISK-ON' ? 'rgb(var(--success))' :
          dc.verdict === 'RISK-OFF' ? 'rgb(var(--destructive))' :
          dc.verdict === 'MIXED' ? 'rgb(var(--warning))' : 'rgb(var(--muted-foreground))';
        const gates = dc.gates;
        const passCount = Object.values(gates).filter(Boolean).length;
        const passColor =
          passCount === 4 ? 'rgb(var(--success))' :
          passCount >= 2 ? 'rgb(var(--warning))' : 'rgb(var(--destructive))';
        const gateMeta = [
          {
            key: 'dc1_separation',
            label: 'D1',
            name: 'Separation',
            threshold: '|Cohen\u2019s d| ≥ 0.40',
            tip: 'Separation |d| ≥ 0.40',
            explain:
              'The forward-return gap between the best and worst state in this composite is large enough to act on. Measured as Cohen\u2019s d across historical monthly returns; below 0.40 the states overlap too much to distinguish.',
          },
          {
            key: 'dc2_persistence',
            label: 'D2',
            name: 'Persistence',
            threshold: 'Avg run ≥ 4 months',
            tip: 'Avg run ≥ 4mo',
            explain:
              'Historical runs in this state last long enough to trade without getting whipsawed. Sub-4-month regimes flip too fast to capture the signal with monthly rebalancing.',
          },
          {
            key: 'dc3_conviction',
            label: 'D3',
            name: 'Conviction',
            threshold: 'Conviction ≥ 40 / 100',
            tip: 'Conviction ≥ 40',
            explain:
              'Current dominant-state probability is high enough relative to alternatives. Below 40 the model is effectively saying "I don\u2019t know which regime we\u2019re in" and the decision becomes noise.',
          },
          {
            key: 'dc4_sample_size',
            label: 'D4',
            name: 'Sample Size',
            threshold: 'Sample ≥ 30 months',
            tip: 'Sample ≥ 30mo',
            explain:
              'This composite state has been observed long enough in history for the per-state statistics (mean return, Sharpe, win rate) to be reliable. Thin samples produce fragile tilts.',
          },
        ] as const;
        return (
          <div
            className="panel-card p-4"
            style={{ borderLeft: `3px solid ${verdictColor}` }}
          >
            <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
              {/* Verdict */}
              <div className="flex items-baseline gap-2">
                <StatLabel>Decision</StatLabel>
                <span
                  className="text-[15px] font-bold font-mono tracking-wide"
                  style={{ color: verdictColor }}
                >
                  {dc.verdict}
                </span>
                {dc.primary_ticker && (
                  <span className="text-[10px] text-muted-foreground/60 font-mono">
                    vs {dc.primary_ticker}
                  </span>
                )}
              </div>

              {/* Tilt long */}
              {dc.tilt_long.length > 0 && (
                <div className="flex items-baseline gap-1.5">
                  <StatLabel>Tilt Long</StatLabel>
                  {dc.tilt_long.map((t) => (
                    <span
                      key={t}
                      className="px-1.5 py-0.5 rounded text-[10.5px] font-mono font-semibold"
                      style={{
                        color: 'rgb(var(--success))',
                        background: 'rgb(var(--success) / 0.08)',
                        border: '1px solid rgb(var(--success) / 0.30)',
                      }}
                    >
                      {t}
                    </span>
                  ))}
                </div>
              )}

              {/* Tilt short */}
              {dc.tilt_short.length > 0 && (
                <div className="flex items-baseline gap-1.5">
                  <StatLabel>Avoid</StatLabel>
                  {dc.tilt_short.map((t) => (
                    <span
                      key={t}
                      className="px-1.5 py-0.5 rounded text-[10.5px] font-mono font-semibold"
                      style={{
                        color: 'rgb(var(--destructive))',
                        background: 'rgb(var(--destructive) / 0.08)',
                        border: '1px solid rgb(var(--destructive) / 0.30)',
                      }}
                    >
                      {t}
                    </span>
                  ))}
                </div>
              )}

              {/* DC gates */}
              <div className="flex items-baseline gap-2 ml-auto">
                <StatLabel>Gates</StatLabel>
                <span className="font-mono text-[11px] font-semibold" style={{ color: passColor }}>
                  {passCount}/4
                </span>
                <div className="flex gap-1">
                  {gateMeta.map(({ key, label, tip }) => {
                    const passed = gates[key as keyof typeof gates];
                    return (
                      <span
                        key={key}
                        title={tip}
                        className="text-[9.5px] font-mono px-1 py-0.5 rounded"
                        style={{
                          color: passed ? 'rgb(var(--success))' : 'rgb(var(--destructive))',
                          background: passed ? 'rgb(var(--success) / 0.08)' : 'rgb(var(--destructive) / 0.06)',
                        }}
                      >
                        {passed ? '✓' : '✗'}{label}
                      </span>
                    );
                  })}
                </div>
                <button
                  type="button"
                  onClick={() => setGatesExplainerOpen((v) => !v)}
                  aria-expanded={gatesExplainerOpen}
                  aria-label={gatesExplainerOpen ? 'Hide gates explanation' : 'Show gates explanation'}
                  title={gatesExplainerOpen ? 'Hide explanation' : 'What are the gates?'}
                  className="ml-1 inline-flex items-center justify-center w-4 h-4 text-muted-foreground hover:text-foreground transition-colors"
                >
                  <Info className="w-3 h-3" />
                </button>
              </div>
            </div>

            {/* Gates explainer — expanded on click of the info button */}
            {gatesExplainerOpen && (
              <div className="mt-3 pt-3 border-t border-border/30">
                <div className="flex items-baseline justify-between mb-2">
                  <StatLabel>Decision Gates · 4-Factor Filter</StatLabel>
                  <span className="text-[9.5px] font-mono uppercase tracking-[0.06em] text-muted-foreground">
                    All 4 must pass for high-conviction trade
                  </span>
                </div>
                <p className="text-[11px] text-muted-foreground leading-relaxed mb-3 max-w-[68ch]">
                  Gates stop the macro decision framework from acting on regimes that are
                  statistically weak, too short-lived, uncertain, or under-sampled. Each gate
                  is a binary quality check: <span className="text-success font-mono">✓ pass</span> or
                  {' '}<span className="text-destructive font-mono">✗ fail</span>. Treat
                  {' '}<span className="text-foreground font-semibold">4/4</span> as high-conviction,
                  {' '}<span className="text-foreground font-semibold">2–3/4</span> as directional only,
                  {' '}<span className="text-foreground font-semibold">0–1/4</span> as noise — stand aside.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                  {gateMeta.map(({ key, label, name, threshold, explain }) => {
                    const passed = gates[key as keyof typeof gates];
                    const color = passed ? 'rgb(var(--success))' : 'rgb(var(--destructive))';
                    return (
                      <div
                        key={key}
                        className="panel-card p-2.5"
                        style={{ borderLeft: `2px solid ${color}` }}
                      >
                        <div className="flex items-baseline justify-between gap-2">
                          <div className="flex items-baseline gap-2 min-w-0">
                            <span
                              className="text-[10px] font-mono font-bold tabular-nums"
                              style={{ color }}
                            >
                              {passed ? '✓' : '✗'}{label}
                            </span>
                            <span className="text-[11px] font-semibold text-foreground uppercase tracking-[0.04em] truncate">
                              {name}
                            </span>
                          </div>
                          <span className="text-[9.5px] font-mono text-muted-foreground whitespace-nowrap">
                            {threshold}
                          </span>
                        </div>
                        <p className="text-[10.5px] text-muted-foreground leading-relaxed mt-1.5">
                          {explain}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Watch row */}
            {dc.watch.length > 0 && (
              <div className="mt-3 pt-3 border-t border-border/30">
                <div className="flex items-baseline gap-2 flex-wrap">
                  <StatLabel>Watch (12M Markov)</StatLabel>
                  {dc.watch.map((w, i) => (
                    <span key={i} className="text-[11px] font-mono text-muted-foreground/80">
                      <span className="text-muted-foreground/60">{w.axis}:</span>{' '}
                      <span className="text-destructive">{w.from}</span>
                      <span className="text-muted-foreground/40">{' → '}</span>
                      <span className="text-success">{w.to}</span>
                    </span>
                  ))}
                </div>
                <p className="text-[9.5px] text-muted-foreground/50 mt-1.5 font-mono uppercase tracking-[0.06em]">
                  current state probability projected to drop &lt;70% of today
                </p>
              </div>
            )}
          </div>
        );
      })()}

      {/* ── Top: Regime banner + Probabilities ── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Regime banner — 2/5 cols — flat panel with colored left rule */}
        <div
          className="lg:col-span-2 panel-card p-4 relative"
          style={{ borderLeft: `3px solid ${domColor}` }}
        >
          <StatLabel>Current Regime · {state.date}</StatLabel>
          {isComposite ? (
            <>
              <JointStateChips dom={dom} model={model} />
              <p className="text-[11.5px] text-muted-foreground mt-2 leading-snug">{domDesc}</p>
            </>
          ) : (
            <>
              <div
                className="text-[18px] font-bold tracking-tight mt-2 uppercase"
                style={{ color: domColor }}
              >
                {dom}
              </div>
              <p className="text-[11.5px] text-muted-foreground mt-1 leading-snug">{domDesc}</p>
            </>
          )}
          <div className="flex items-baseline gap-3 mt-3">
            <span
              className="text-[28px] font-bold font-mono tabular-nums leading-none"
              style={{ color: domColor }}
            >
              {(state.dominant_probability * 100).toFixed(0)}%
            </span>
            <span className="text-[10px] font-mono uppercase tracking-[0.08em] text-muted-foreground">
              {state.months_in_regime}MO IN STATE
            </span>
          </div>

          {/* Conviction bar with thresholds (red <40, amber 40-60, green >60) */}
          <div className="mt-4">
            <div className="flex justify-between mb-1">
              <StatLabel>Conviction</StatLabel>
              <span className="font-mono text-[11px]" style={{ color: convictionColor }}>
                {state.conviction.toFixed(0)}/100
              </span>
            </div>
            <div className="relative h-1.5 bg-border/30 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{ width: `${state.conviction}%`, background: convictionColor }}
              />
              {/* threshold ticks at 40 + 60 */}
              <div className="absolute top-0 bottom-0 w-px bg-foreground/35" style={{ left: '40%' }} />
              <div className="absolute top-0 bottom-0 w-px bg-foreground/35" style={{ left: '60%' }} />
            </div>
            <div className="relative h-3 mt-0.5">
              <span className="absolute text-[8.5px] text-muted-foreground/40 font-mono" style={{ left: '0%' }}>0</span>
              <span className="absolute text-[8.5px] text-muted-foreground/40 font-mono" style={{ left: '38%' }}>40</span>
              <span className="absolute text-[8.5px] text-muted-foreground/40 font-mono" style={{ left: '58%' }}>60</span>
              <span className="absolute text-[8.5px] text-muted-foreground/40 font-mono" style={{ right: '0%' }}>100</span>
            </div>
          </div>

          {/* Tactical / Strategic */}
          {state.tactical_regime && (
            <div className="mt-4 pt-4 border-t border-border/30 space-y-1.5">
              <div className="flex justify-between text-[11px]">
                <span className="text-muted-foreground">Tactical (1-3m)</span>
                <span
                  className="font-semibold"
                  style={{ color: getRegimeColor(state.tactical_regime, model) }}
                >
                  {state.tactical_regime}
                </span>
              </div>
              <div className="flex justify-between text-[11px]">
                <span className="text-muted-foreground">Strategic (6-12m)</span>
                <span
                  className="font-semibold"
                  style={{ color: getRegimeColor(state.strategic_regime, model) }}
                >
                  {state.strategic_regime}
                </span>
              </div>
              {state.transitioning && (
                <p className="text-[10px] text-amber-500 uppercase tracking-wider mt-1">
                  ⚠ Regime transitioning
                </p>
              )}
            </div>
          )}

          {/* Historical context (merged from Regime Profile) */}
          {state.regime_stats && (() => {
            const rs = state.regime_stats!;
            const fmtRet = (v: number | null | undefined) =>
              v == null ? '—' : `${v >= 0 ? '+' : ''}${(v * 100).toFixed(1)}%`;
            const fmtSharpe = (v: number | null | undefined) =>
              v == null ? '—' : v.toFixed(2);
            const fmtWin = (v: number | null | undefined) =>
              v == null ? '—' : `${Math.round(v * 100)}%`;
            const maturity =
              rs.avg_run_months > 0
                ? Math.min(rs.current_run_months / rs.avg_run_months, 1.99)
                : 0;
            const maturityPct = Math.round(maturity * 50); // 50% bar = avg
            return (
              <>
                {/* Frequency + Maturity */}
                <div className="mt-4 pt-4 border-t border-border/30 grid grid-cols-2 gap-4">
                  <div>
                    <StatLabel>Frequency</StatLabel>
                    <div className="mt-1 flex items-baseline gap-1.5">
                      <span className="text-[18px] font-bold font-mono tabular-nums leading-none text-foreground">
                        {rs.frequency_pct.toFixed(0)}%
                      </span>
                      <span className="text-[9.5px] font-mono uppercase tracking-[0.06em] text-muted-foreground">
                        {rs.occurrences}EP
                      </span>
                    </div>
                    <p className="text-[9.5px] font-mono tabular-nums text-muted-foreground mt-1">
                      {rs.months_in_state}/{rs.total_months}MO
                    </p>
                  </div>
                  <div>
                    <StatLabel>Maturity</StatLabel>
                    <div className="mt-1 flex items-baseline gap-1.5">
                      <span className="text-[18px] font-bold font-mono tabular-nums leading-none text-foreground">
                        {rs.current_run_months}M
                      </span>
                      <span className="text-[9.5px] font-mono uppercase tracking-[0.06em] text-muted-foreground">
                        /{rs.avg_run_months.toFixed(1)}AVG
                      </span>
                    </div>
                    <div className="h-1 mt-2 bg-border/30 overflow-hidden relative">
                      <div
                        className="h-full"
                        style={{
                          width: `${Math.min(maturityPct, 100)}%`,
                          background: domColor,
                        }}
                      />
                      <div
                        className="absolute top-0 bottom-0 w-px bg-border"
                        style={{ left: '50%' }}
                      />
                    </div>
                  </div>
                </div>

                {/* Best / Worst asset (incl. drawdown) */}
                <div className="mt-4 pt-4 border-t border-border/30 grid grid-cols-2 gap-4">
                  <div>
                    <StatLabel>Best Asset</StatLabel>
                    {rs.best_asset ? (
                      <>
                        <div className="mt-1 flex items-baseline gap-2">
                          <span className="text-[16px] font-bold font-mono text-foreground leading-none">
                            {rs.best_asset.ticker}
                          </span>
                          <span className="text-[12px] font-mono tabular-nums text-success font-semibold">
                            {fmtRet(rs.best_asset.ann_ret)}
                          </span>
                        </div>
                        <p className="text-[9.5px] font-mono tabular-nums text-muted-foreground mt-1 uppercase tracking-[0.04em]">
                          SH {fmtSharpe(rs.best_asset.sharpe)} · W {fmtWin(rs.best_asset.win_rate)}
                          {rs.best_asset.max_dd != null && (
                            <> · DD {fmtRet(rs.best_asset.max_dd)}</>
                          )}
                        </p>
                      </>
                    ) : (
                      <p className="text-[11px] text-muted-foreground mt-1">No data</p>
                    )}
                  </div>
                  <div>
                    <StatLabel>Worst Asset</StatLabel>
                    {rs.worst_asset ? (
                      <>
                        <div className="mt-1 flex items-baseline gap-2">
                          <span className="text-[16px] font-bold font-mono text-foreground leading-none">
                            {rs.worst_asset.ticker}
                          </span>
                          <span className="text-[12px] font-mono tabular-nums text-destructive font-semibold">
                            {fmtRet(rs.worst_asset.ann_ret)}
                          </span>
                        </div>
                        <p className="text-[9.5px] font-mono tabular-nums text-muted-foreground mt-1 uppercase tracking-[0.04em]">
                          SH {fmtSharpe(rs.worst_asset.sharpe)} · W {fmtWin(rs.worst_asset.win_rate)}
                          {rs.worst_asset.max_dd != null && (
                            <> · DD {fmtRet(rs.worst_asset.max_dd)}</>
                          )}
                        </p>
                      </>
                    ) : (
                      <p className="text-[11px] text-muted-foreground mt-1">No data</p>
                    )}
                  </div>
                </div>

                {/* Separation footnote */}
                {rs.top_separation && rs.top_separation.cohens_d != null && (
                  <div className="mt-3 pt-3 border-t border-border/30 text-[10px] text-muted-foreground/60 leading-relaxed">
                    <span>Top sep: </span>
                    <span className="text-foreground font-semibold font-mono">
                      {rs.top_separation.ticker}
                    </span>
                    {' '}
                    <span className="font-mono">
                      d={rs.top_separation.cohens_d.toFixed(2)}
                    </span>
                    {rs.top_separation.p_value != null && (
                      <span className="font-mono">
                        {' · '}p={rs.top_separation.p_value < 0.001 ? '<0.001' : rs.top_separation.p_value.toFixed(3)}
                      </span>
                    )}
                    {rs.top_separation.best_state && (
                      <>
                        {' · best '}
                        <span
                          className="font-semibold"
                          style={{ color: getRegimeColor(rs.top_separation.best_state, model) }}
                        >
                          {rs.top_separation.best_state}
                        </span>
                      </>
                    )}
                  </div>
                )}
              </>
            );
          })()}
        </div>

        {/* Regime Probabilities — multi-horizon Markov table — 3/5 cols */}
        <div className="lg:col-span-3">
        <PanelCard>
          <div className="flex items-baseline justify-between">
            <StatLabel>Regime Probabilities</StatLabel>
            <span className="text-[9.5px] uppercase tracking-[0.08em] text-muted-foreground/50 font-mono">
              Markov forward · Now → 12M
            </span>
          </div>
          {(() => {
            const horizons = state.forward_horizons || {};
            const horizonKeys = ['1', '3', '6', '12'] as const;
            const sortedRegimes = Object.entries(state.probabilities).sort(
              (a, b) => b[1] - a[1]
            );
            return (
              <div className="mt-3 overflow-x-auto">
                <table className="w-full text-[11px] font-mono">
                  <thead>
                    <tr className="border-b border-border/30 text-muted-foreground/55 uppercase tracking-[0.08em] text-[9.5px]">
                      <th className="text-left py-1.5 pr-2 font-normal">Regime</th>
                      <th className="text-right py-1.5 px-1.5 font-normal">Now</th>
                      <th className="text-right py-1.5 px-1.5 font-normal">1M</th>
                      <th className="text-right py-1.5 px-1.5 font-normal">3M</th>
                      <th className="text-right py-1.5 px-1.5 font-normal">6M</th>
                      <th className="text-right py-1.5 pl-1.5 font-normal">12M</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedRegimes.map(([regime, prob]) => {
                      const rc = getRegimeColor(regime, model);
                      const cur = Math.round(prob * 100);
                      const isActive = regime === dom;
                      const cellFor = (h: typeof horizonKeys[number]) => {
                        const v = horizons[h]?.[regime];
                        if (v == null) return null;
                        return Math.round(v * 100);
                      };
                      const v12 = cellFor('12');
                      const delta12 = v12 != null ? v12 - cur : null;
                      const renderCell = (val: number | null) => {
                        if (val == null) return <span className="text-muted-foreground/30">—</span>;
                        const diff = val - cur;
                        const dColor =
                          diff > 1 ? 'rgb(var(--success))' :
                          diff < -1 ? 'rgb(var(--destructive))' : 'currentColor';
                        return (
                          <span style={{ color: dColor, opacity: isActive ? 1 : 0.75 }}>
                            {val}%
                          </span>
                        );
                      };
                      return (
                        <tr
                          key={regime}
                          className="border-b border-border/15"
                          style={{
                            background: isActive ? `rgba(${hexToRgb(rc)}, 0.05)` : undefined,
                          }}
                        >
                          <td
                            className="py-1.5 pr-2 text-left whitespace-nowrap"
                            style={{
                              color: rc,
                              fontWeight: isActive ? 700 : 500,
                              opacity: isActive ? 1 : 0.85,
                            }}
                          >
                            {regime}
                          </td>
                          <td
                            className="py-1.5 px-1.5 text-right"
                            style={{
                              color: rc,
                              fontWeight: isActive ? 700 : 500,
                            }}
                          >
                            {cur}%
                          </td>
                          <td className="py-1.5 px-1.5 text-right text-muted-foreground/75">
                            {renderCell(cellFor('1'))}
                          </td>
                          <td className="py-1.5 px-1.5 text-right text-muted-foreground/75">
                            {renderCell(cellFor('3'))}
                          </td>
                          <td className="py-1.5 px-1.5 text-right text-muted-foreground/75">
                            {renderCell(cellFor('6'))}
                          </td>
                          <td className="py-1.5 pl-1.5 text-right text-muted-foreground/75">
                            <div className="inline-flex items-baseline gap-1">
                              {renderCell(v12)}
                              {delta12 != null && Math.abs(delta12) >= 2 && (
                                <span
                                  className="text-[8.5px]"
                                  style={{ color: delta12 > 0 ? 'rgb(var(--success))' : 'rgb(var(--destructive))' }}
                                >
                                  {delta12 > 0 ? '▲' : '▼'}
                                  {Math.abs(delta12)}
                                </span>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            );
          })()}

          {/* Cycle Acceleration — dimension-aware, always-on */}
          {regimeDims.some((d) => state.dimensions?.[d]?.acceleration != null) && (
            <div className="mt-4 pt-4 border-t border-border/30">
              <StatLabel>Cycle Acceleration · 3M Δz</StatLabel>
              <div
                className="mt-2 grid gap-3"
                style={{
                  gridTemplateColumns: `repeat(${Math.min(regimeDims.length, 3)}, minmax(0, 1fr))`,
                }}
              >
                {regimeDims.map((dim) => {
                  const accel = state.dimensions?.[dim]?.acceleration;
                  if (accel == null) return null;
                  const isUp = accel >= 0;
                  // Default: rising = green. Inflation flips because rising
                  // inflation is bad for forward equity returns.
                  const inflationLike = /inflation/i.test(dim);
                  const goodSign = inflationLike ? !isUp : isUp;
                  const color = goodSign ? 'rgb(var(--success))' : 'rgb(var(--destructive))';
                  return (
                    <div key={dim} className="flex justify-between text-[11.5px]">
                      <span className="text-muted-foreground truncate" title={dim}>
                        {dim}
                      </span>
                      <span className="font-mono" style={{ color }}>
                        {isUp ? '▲' : '▼'} {fmtZ(accel)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </PanelCard>
        </div>
      </div>

      {/* ── Dimension detail cards — deeper per-axis breakdown ── */}
      <div className="flex items-baseline justify-between pt-2 pb-1 border-b border-border/30">
        <StatLabel>Dimension Detail</StatLabel>
        <span className="text-[9px] font-mono uppercase tracking-[0.08em] text-muted-foreground">
          {regimeDims.length} active · full composite breakdown
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {regimeDims.map((dim) => {
          const d = state.dimensions?.[dim];
          if (!d) return null;
          const color = getDimensionColor(dim, model);
          const rgb = hexToRgb(color);
          const dirColor = d.z >= 0 ? color : 'rgb(var(--muted-foreground))';
          return (
            <div
              key={dim}
              className="panel-card p-4"
              style={{ borderLeft: `3px solid ${color}` }}
            >
              <div className="flex items-start justify-between gap-2">
                <StatLabel>{dim}</StatLabel>
                {d.history && d.history.length > 1 && (
                  <Sparkline values={d.history} width={80} height={18} />
                )}
              </div>
              <div className="flex items-baseline gap-2 mt-3 mb-3">
                <span className="text-[22px] font-bold font-mono tabular-nums leading-none" style={{ color }}>
                  {fmtZ(d.z)}
                </span>
                <span className="text-[11px] font-semibold uppercase tracking-[0.04em]" style={{ color: dirColor }}>
                  {d.direction}
                </span>
                {d.acceleration != null && (() => {
                  const isUp = d.acceleration >= 0;
                  const inflationLike = /inflation/i.test(dim);
                  const goodSign = inflationLike ? !isUp : isUp;
                  const ac = goodSign ? 'rgb(var(--success))' : 'rgb(var(--destructive))';
                  return (
                    <span
                      className="ml-auto text-[10px] font-mono tabular-nums"
                      style={{ color: ac }}
                      title="3-month acceleration in z-units"
                    >
                      {isUp ? '▲' : '▼'} {fmtZ(d.acceleration)}
                    </span>
                  );
                })()}
              </div>
              <div className="h-1.5 bg-border/30 overflow-hidden mb-1">
                <div
                  className="h-full"
                  style={{ width: `${Math.round(d.p * 100)}%`, background: color }}
                />
              </div>
              <p className="text-[9.5px] font-mono tabular-nums text-muted-foreground mb-3 uppercase tracking-[0.04em]">
                {Math.round(d.p * 100)}% IN {d.direction} · SCORE {d.score}/{d.total}
              </p>
              {d.components.length > 0 && (
                <div className="border-t border-border/30 pt-2 space-y-1">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-[9.5px] uppercase tracking-[0.08em] text-muted-foreground/50">
                      Top Drivers
                    </span>
                    {d.components.length > 5 && (
                      <span className="text-[9.5px] text-muted-foreground/40 font-mono">
                        {d.components.length} total
                      </span>
                    )}
                  </div>
                  {d.components.slice(0, 5).map((c) => (
                    <div key={c.name} className="flex justify-between items-center">
                      <span className="text-[10.5px] text-muted-foreground/60 truncate">
                        {c.name}
                      </span>
                      <span
                        className="text-[10.5px] font-mono"
                        style={{ color: c.z >= 0 ? color : 'rgb(var(--muted-foreground))' }}
                      >
                        {fmtZ(c.z)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ── Market confirmation + Allocation ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Market confirmation */}
        {state.market_confirmation && (
          <PanelCard>
            <div className="flex justify-between items-center mb-3">
              <StatLabel>Market Confirmation</StatLabel>
              <span
                className="text-[12px] font-bold"
                style={{
                  color: state.market_confirmation.score >= 4 ? 'rgb(var(--success))' :
                         state.market_confirmation.score <= 1 ? 'rgb(var(--destructive))' : 'rgb(var(--warning))',
                }}
              >
                {state.market_confirmation.verdict}
              </span>
            </div>
            <div className="space-y-2">
              {state.market_confirmation.signals.map((s) => {
                const color = s.aligned === true ? 'rgb(var(--success))' :
                              s.aligned === false ? 'rgb(var(--destructive))' : 'rgb(var(--warning))';
                const icon = s.aligned === true ? '✓' :
                             s.aligned === false ? '✗' : '~';
                return (
                  <div key={s.name} className="flex justify-between items-center">
                    <span className="text-[11.5px] text-muted-foreground/70">{s.name}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[11.5px] font-mono" style={{ color }}>
                        {s.value}
                      </span>
                      <span className="text-[12px]" style={{ color }}>{icon}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </PanelCard>
        )}

        {/* Current allocation */}
        {state.current_allocation && (
          <PanelCard>
            <div className="flex justify-between items-center mb-3">
              <StatLabel>Current Allocation</StatLabel>
              <span className="text-[10.5px] text-muted-foreground/60">
                {state.current_allocation.macro_regime} + {state.current_allocation.liquidity_regime}
              </span>
            </div>
            <div className="space-y-2">
              {Object.entries(state.current_allocation.weights)
                .filter(([_, w]) => w > 0)
                .sort((a, b) => b[1] - a[1])
                .map(([asset, w]) => {
                  const color = ASSET_COLORS[asset] || 'rgb(var(--muted-foreground))';
                  const pct = Math.round(w * 100);
                  return (
                    <div key={asset} className="flex items-center gap-3">
                      <span className="text-[11px] font-mono w-8" style={{ color }}>
                        {asset}
                      </span>
                      <div className="flex-1 h-3 bg-border/30 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{ width: `${pct}%`, background: color }}
                        />
                      </div>
                      <span className="text-[11px] font-mono w-10 text-right text-muted-foreground">
                        {pct}%
                      </span>
                    </div>
                  );
                })}
            </div>
          </PanelCard>
        )}
      </div>
    </div>
  );
}
