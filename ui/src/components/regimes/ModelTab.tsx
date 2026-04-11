'use client';

import type { MetaData, QualitySnapshot, RegimeModel } from './types';
import { getRegimeColor, getDimensionColor } from './constants';
import { PanelCard, StatLabel, TierBadge } from './SharedComponents';

interface Props {
  meta: MetaData;
  model?: RegimeModel;
}

// ─────────────────────────────────────────────────────────────────────
// Tier 1 breakdown table — driven entirely by model.quality
// ─────────────────────────────────────────────────────────────────────

type BarRow = {
  bar: string;
  name: string;
  threshold: string;
  actual: string;
  pass: boolean | null | undefined;
  help: string;
};

function fmtPct(v: number | null | undefined, decimals = 2): string {
  if (v == null || !Number.isFinite(v)) return '—';
  return `${(v * 100).toFixed(decimals)}%`;
}
function fmtNum(v: number | null | undefined, decimals = 2): string {
  if (v == null || !Number.isFinite(v)) return '—';
  return v.toFixed(decimals);
}

function buildTier1Rows(q: QualitySnapshot): BarRow[] {
  return [
    {
      bar: 'T1.1',
      name: 'Coverage',
      threshold: '≥ 85%',
      actual: fmtPct(q.coverage),
      pass: q.t11_coverage_pass,
      help: 'Fraction of monthly history where the regime produces a dominant state.',
    },
    {
      bar: 'T1.2',
      name: 'Median run length',
      threshold: '≥ 4 mo',
      actual: `${fmtNum(q.median_run_months, 1)} mo`,
      pass: q.t12_run_length_pass,
      help: 'Median contiguous months spent in a single state — eliminates chattering noise.',
    },
    {
      bar: 'T1.3',
      name: 'Min state n',
      threshold: '≥ 30',
      actual: q.min_state_n != null ? String(q.min_state_n) : '—',
      pass: q.t13_min_n_pass,
      help: 'Smallest number of observations across all declared states.',
    },
    {
      bar: 'T1.4',
      name: 'Vol-norm spread',
      threshold: '≥ 0.40',
      actual: fmtNum(q.vol_normalized_spread, 2),
      pass: q.t14_volnorm_pass,
      help: 'Best-vs-worst annualized return gap as Sharpe-delta (spread / target vol). Primary quality gate at 1M frequency.',
    },
    {
      bar: 'T1.5',
      name: 'Welch p',
      threshold: 'info only',
      actual: fmtNum(q.welch_p, 4),
      pass: null,  // informational at 1M — not a tier gate
      help: 'Welch two-sided t-test — informational at 1M frequency (too conservative for n=30-60 monthly returns). Not a tier gate.',
    },
    {
      bar: 'T1.6',
      name: 'Subsample sign',
      threshold: 'consistent',
      actual: q.subsample_sign_consistent == null ? '—' : q.subsample_sign_consistent ? 'consistent' : 'flipped',
      pass: q.t16_subsample_pass,
      help: 'Best state direction holds in both pre-2010 and post-2010 halves of the history.',
    },
    {
      bar: 'T1.7',
      name: 'Param sensitivity',
      threshold: 'robust / sensitive',
      actual: q.sensitivity_verdict ?? '—',
      pass: q.t17_sensitivity_pass,
      help: '16-cell grid sweep around defaults — fragile = sign flip or median spread < half default.',
    },
    {
      bar: 'T1.8',
      name: 'State balance',
      threshold: '≠ degenerate',
      actual: q.state_balance_verdict ?? '—',
      pass: q.t18_balance_pass,
      help: 'Soft check on state distribution uniformity (Shannon entropy).',
    },
  ];
}

/** Mini sensitivity visualization: min / default / median / max spreads
 *  plotted as four dots on a single axis scaled to the observed range. */
function SensitivityBar({ q }: { q: QualitySnapshot }) {
  const d = q.grid_default_spread;
  const med = q.grid_median_spread;
  const mn = q.grid_min_spread;
  const mx = q.grid_max_spread;
  if (d == null || med == null || mn == null || mx == null) return null;
  const vals = [d, med, mn, mx];
  const lo = Math.min(...vals, 0);
  const hi = Math.max(...vals, 0);
  const range = hi - lo || 1;
  const pos = (v: number) => `${((v - lo) / range) * 100}%`;
  const defaultIsMax = d >= mx - 1e-9;
  return (
    <div className="relative h-6">
      {/* Axis */}
      <div className="absolute left-0 right-0 top-1/2 h-[1px] bg-border/60" />
      {/* Zero tick */}
      {lo < 0 && hi > 0 && (
        <div
          className="absolute top-0 bottom-0 w-[1px] bg-border/80"
          style={{ left: pos(0) }}
        />
      )}
      {/* min / max range bar */}
      <div
        className="absolute top-1/2 -translate-y-1/2 h-[3px] bg-foreground/20"
        style={{ left: pos(mn), width: `calc(${pos(mx)} - ${pos(mn)})` }}
      />
      {/* median marker */}
      <div
        className="absolute top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-foreground/60"
        style={{ left: pos(med), transform: 'translate(-50%, -50%)' }}
        title={`median ${fmtPct(med)}`}
      />
      {/* default marker (emphasized) */}
      <div
        className={`absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full ${
          defaultIsMax ? 'bg-success' : 'bg-foreground'
        } border border-background`}
        style={{ left: pos(d), transform: 'translate(-50%, -50%)' }}
        title={`default ${fmtPct(d)}`}
      />
    </div>
  );
}

function RobustnessSection({ quality }: { quality: QualitySnapshot }) {
  const rows = buildTier1Rows(quality);
  const n_fragile = quality.grid_fragile_cells ?? 0;
  const n_flips = quality.grid_sign_flips ?? 0;
  return (
    <>
      <PanelCard>
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2.5">
            <StatLabel>Robustness</StatLabel>
            <TierBadge tier={quality.tier} title={quality.tier_rationale} />
          </div>
          <div className="text-[10.5px] font-mono text-muted-foreground/80 text-right">
            {quality.target} · {quality.horizon_months}M · n={quality.n_observations}
          </div>
        </div>
        {quality.tier_rationale && (
          <p className="mt-2 text-[11px] text-muted-foreground font-mono">
            {quality.tier_rationale}
          </p>
        )}

        {/* Tier 1 table */}
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-border/30 text-muted-foreground/60 uppercase tracking-wider text-[10px]">
                <th className="text-left py-2 px-2 w-[48px]">Bar</th>
                <th className="text-left py-2 px-2">Test</th>
                <th className="text-left py-2 px-2">Threshold</th>
                <th className="text-left py-2 px-2">Actual</th>
                <th className="text-center py-2 px-2 w-[60px]">Pass</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr
                  key={r.bar}
                  className="border-b border-border/20 hover:bg-card/50"
                  title={r.help}
                >
                  <td className="py-1.5 px-2 font-mono text-muted-foreground/80">{r.bar}</td>
                  <td className="py-1.5 px-2 text-foreground">{r.name}</td>
                  <td className="py-1.5 px-2 font-mono text-muted-foreground">{r.threshold}</td>
                  <td className="py-1.5 px-2 font-mono text-foreground">{r.actual}</td>
                  <td className="py-1.5 px-2 text-center">
                    {r.pass == null ? (
                      <span className="text-muted-foreground/60">—</span>
                    ) : r.pass ? (
                      <span className="text-success font-mono">✓</span>
                    ) : (
                      <span className="text-destructive font-mono">✗</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PanelCard>

      {/* Sensitivity grid visualization */}
      <PanelCard>
        <div className="flex items-center justify-between gap-2">
          <StatLabel>Sensitivity Grid · 16 Cells</StatLabel>
          <div className="text-[10.5px] font-mono text-muted-foreground">
            fragile <span className="text-foreground">{n_fragile}/16</span>
            <span className="mx-1.5 text-border">·</span>
            flips <span className={n_flips > 0 ? 'text-destructive' : 'text-foreground'}>{n_flips}</span>
          </div>
        </div>
        <p className="mt-1.5 text-[11px] text-muted-foreground">
          16-cell parameter sweep around defaults (z_window × sensitivity × halflife × confirm).
          Black dot = default spread, gray dot = grid median, gray bar = min→max range.
        </p>
        <div className="mt-3">
          <SensitivityBar q={quality} />
          <div className="mt-1.5 flex items-center justify-between text-[10px] font-mono text-muted-foreground">
            <span>min {fmtPct(quality.grid_min_spread)}</span>
            <span>med {fmtPct(quality.grid_median_spread)}</span>
            <span>default {fmtPct(quality.grid_default_spread)}</span>
            <span>max {fmtPct(quality.grid_max_spread)}</span>
          </div>
        </div>
      </PanelCard>

      {/* Orthogonality overlaps */}
      {quality.overlaps && quality.overlaps.length > 0 && (
        <PanelCard>
          <StatLabel>D11 Overlaps · High Correlation</StatLabel>
          <p className="mt-1.5 text-[11px] text-muted-foreground">
            Registered regimes whose composite z-score correlates at |ρ| {'>'} 0.60 with this one.
            Composing with any of these double-counts the underlying signal.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {quality.overlaps.map((o) => (
              <span
                key={o.key}
                className="inline-flex items-baseline gap-1.5 px-2 py-1 border border-warning/40 bg-warning/5 rounded-sm font-mono text-[11px]"
              >
                <span className="text-foreground">{o.key}</span>
                <span className="text-warning">
                  {o.rho >= 0 ? '+' : ''}{o.rho.toFixed(2)}
                </span>
                <span className="text-muted-foreground/70 text-[9.5px]">n={o.n}</span>
              </span>
            ))}
          </div>
        </PanelCard>
      )}
    </>
  );
}

export function ModelTab({ meta, model }: Props) {
  if (!meta) {
    return <p className="text-muted-foreground text-[12.5px]">No methodology data.</p>;
  }

  return (
    <div className="space-y-4">
      <PanelCard>
        <h2 className="text-base font-bold text-foreground">{meta.model_name}</h2>
        <p className="text-[12.5px] text-muted-foreground mt-1">{meta.description}</p>
      </PanelCard>

      {/* Universal quality snapshot — rendered first, above the regime
       * definitions and methodology blocks. Single-axis regimes only —
       * composite models don't have a quality snapshot of their own. */}
      {model?.quality && <RobustnessSection quality={model.quality} />}

      {/* Regime definitions */}
      {meta.regime_definitions && (
        <PanelCard>
          <StatLabel>Regime Definitions</StatLabel>
          <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
            {Object.entries(meta.regime_definitions).map(([name, def]) => {
              const color = getRegimeColor(name, model);
              return (
                <div
                  key={name}
                  className="panel-card p-3"
                  style={{ borderLeft: `3px solid ${color}` }}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold" style={{ color }}>{name}</span>
                    <span className="text-[10.5px] font-mono text-muted-foreground/60">
                      Growth {def.growth} · Inflation {def.inflation}
                    </span>
                  </div>
                  <p className="text-[11.5px] text-muted-foreground">{def.description}</p>
                </div>
              );
            })}
          </div>
        </PanelCard>
      )}

      {/* Methodology */}
      <PanelCard>
        <StatLabel>Methodology</StatLabel>
        <div className="mt-3 space-y-2">
          {Object.entries(meta.methodology).map(([key, value]) => (
            <div key={key} className="grid grid-cols-1 md:grid-cols-4 gap-2">
              <div className="text-[10.5px] uppercase tracking-wider text-muted-foreground/60 font-mono">
                {key.replace(/_/g, ' ')}
              </div>
              <div className="md:col-span-3 text-[11.5px] text-foreground">
                {value}
              </div>
            </div>
          ))}
        </div>
      </PanelCard>

      {/* Indicator documentation */}
      {meta.indicator_docs &&
        Object.entries(meta.indicator_docs).map(([dim, docs]) => {
          const color = getDimensionColor(dim, model);
          return (
            <PanelCard key={dim}>
              <div className="flex items-center justify-between mb-2">
                <StatLabel>{dim} Indicators</StatLabel>
                <span
                  className="text-[10.5px] uppercase tracking-wider"
                  style={{ color }}
                >
                  {docs.indicators.length} components
                </span>
              </div>
              <p className="text-[11.5px] text-muted-foreground mb-3">{docs.description}</p>
              <div className="overflow-x-auto">
                <table className="w-full text-[11px]">
                  <thead>
                    <tr className="border-b border-border/30 text-muted-foreground/60 uppercase tracking-wider text-[10px]">
                      <th className="text-left py-2 px-2">Indicator</th>
                      <th className="text-left py-2 px-2">Code</th>
                      <th className="text-center py-2 px-2">Lag</th>
                      <th className="text-left py-2 px-2">Type</th>
                      <th className="text-left py-2 px-2">Rationale</th>
                    </tr>
                  </thead>
                  <tbody>
                    {docs.indicators.map((ind) => (
                      <tr key={ind.name} className="border-b border-border/20 hover:bg-card/50">
                        <td className="py-1.5 px-2 font-semibold" style={{ color }}>
                          {ind.name}
                        </td>
                        <td className="py-1.5 px-2 font-mono text-muted-foreground text-[10.5px]">
                          {ind.code}
                        </td>
                        <td className="py-1.5 px-2 text-center font-mono">{ind.lag}m</td>
                        <td className="py-1.5 px-2 text-muted-foreground">{ind.type}</td>
                        <td className="py-1.5 px-2 text-muted-foreground/80">{ind.rationale}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </PanelCard>
          );
        })}
    </div>
  );
}
