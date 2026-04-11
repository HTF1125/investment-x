'use client';

import { AlertCircle } from 'lucide-react';
import dynamic from 'next/dynamic';
import CanonicalLoadingSpinner, {
  DynamicImportLoader,
} from '@/components/shared/LoadingSpinner';
import type { QualitySnapshot, ForwardValidation, RegimeModel, RegimeTier, RegimeVerdict } from './types';

export const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => <DynamicImportLoader />,
}) as any;

/** @deprecated — re-export of the canonical loader in `components/shared/`. */
export function LoadingSpinner({ label }: { label?: string }) {
  return <CanonicalLoadingSpinner label={label} size="section" />;
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center py-10">
      <div className="flex flex-col items-center gap-2 text-center">
        <AlertCircle className="w-5 h-5 text-destructive/80" />
        <p className="text-[12.5px] text-muted-foreground">{message}</p>
      </div>
    </div>
  );
}

export function StatLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-[10px] font-mono font-semibold uppercase tracking-[0.12em] text-muted-foreground">
      {children}
    </span>
  );
}

export function PanelCard({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`panel-card p-4 ${className}`}>
      {children}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Robustness surface — TierBadge, PassFailChip, RobustnessCard
// ─────────────────────────────────────────────────────────────────────

const TIER_LABEL: Record<RegimeTier, string> = {
  tier1: 'TIER 1',
  tier2: 'TIER 2',
  sensitive: 'SENSITIVE',
  weak: 'WEAK',
  draft: 'DRAFT',
};

const TIER_TEXT: Record<RegimeTier, string> = {
  tier1: 'text-foreground',
  tier2: 'text-foreground',
  sensitive: 'text-foreground',
  weak: 'text-destructive',
  draft: 'text-muted-foreground',
};

const TIER_BORDER: Record<RegimeTier, string> = {
  tier1: 'border-foreground/60',
  tier2: 'border-foreground',
  sensitive: 'border-warning/60',
  weak: 'border-destructive/60',
  draft: 'border-border/60',
};

const TIER_BG: Record<RegimeTier, string> = {
  tier1: 'bg-foreground/5',
  tier2: 'bg-foreground/10',
  sensitive: 'bg-warning/10',
  weak: 'bg-destructive/10',
  draft: 'bg-muted/30',
};

export function TierBadge({ tier, title }: { tier: RegimeTier; title?: string }) {
  return (
    <span
      title={title ?? TIER_LABEL[tier]}
      className={`inline-flex items-center px-2 py-0.5 border rounded-sm font-mono text-[10px] font-bold tracking-[0.1em] ${TIER_BORDER[tier]} ${TIER_TEXT[tier]} ${TIER_BG[tier]}`}
    >
      {TIER_LABEL[tier]}
    </span>
  );
}

/** Tiny color dot for compact tile views (no text). */
export function TierDot({ tier, title }: { tier: RegimeTier; title?: string }) {
  const color: Record<RegimeTier, string> = {
    tier1: 'bg-foreground',
    tier2: 'bg-foreground',
    sensitive: 'bg-warning',
    weak: 'bg-destructive',
    draft: 'bg-muted-foreground/50',
  };
  return (
    <span
      title={title ?? TIER_LABEL[tier]}
      className={`inline-block w-1.5 h-1.5 rounded-full ${color[tier]}`}
    />
  );
}

// ─── Forward-looking verdict components (v2) ────────────────────────

const VERDICT_COLOR: Record<RegimeVerdict, string> = {
  STRONG: 'bg-success',
  PASS: 'bg-foreground',
  WEAK: 'bg-warning',
  FAIL: 'bg-destructive',
  NOT_RUN: 'bg-muted-foreground/50',
};

const VERDICT_TEXT: Record<RegimeVerdict, string> = {
  STRONG: 'text-success',
  PASS: 'text-foreground',
  WEAK: 'text-warning',
  FAIL: 'text-destructive',
  NOT_RUN: 'text-muted-foreground',
};

const VERDICT_BORDER: Record<RegimeVerdict, string> = {
  STRONG: 'border-success/60',
  PASS: 'border-foreground/60',
  WEAK: 'border-warning/60',
  FAIL: 'border-destructive/60',
  NOT_RUN: 'border-border/60',
};

const VERDICT_BG: Record<RegimeVerdict, string> = {
  STRONG: 'bg-success/10',
  PASS: 'bg-foreground/5',
  WEAK: 'bg-warning/10',
  FAIL: 'bg-destructive/10',
  NOT_RUN: 'bg-muted/30',
};

/** Tiny verdict dot for AxisDock tiles. */
export function VerdictDot({ verdict, title }: { verdict: RegimeVerdict; title?: string }) {
  return (
    <span
      title={title ?? verdict}
      className={`inline-block w-1.5 h-1.5 rounded-full ${VERDICT_COLOR[verdict]}`}
    />
  );
}

/** Larger pill badge showing verdict text (for RobustnessCard headers). */
export function VerdictBadge({ verdict, title }: { verdict: RegimeVerdict; title?: string }) {
  return (
    <span
      title={title}
      className={`inline-flex items-center px-1.5 py-0.5 border rounded-sm font-mono text-[9px] uppercase tracking-[0.08em] ${VERDICT_TEXT[verdict]} ${VERDICT_BORDER[verdict]} ${VERDICT_BG[verdict]}`}
    >
      {verdict}
    </span>
  );
}

/** Forward-looking validation card — PM-first layout.
 *  Leads with per-state returns (the actionable information), then shows
 *  the IC curve and quality metrics in a collapsible detail row. */
export function ForwardValidationCard({ fwd, model }: { fwd: ForwardValidation; model?: RegimeModel }) {
  const pct = (v: number | null) => v != null ? `${(v * 100).toFixed(0)}%` : '—';
  const fmtIc = (v: number | null) => v != null ? `${v >= 0 ? '+' : ''}${v.toFixed(3)}` : '—';

  const targetTicker = fwd.target?.split(':')[0] ?? 'target';
  const horizonLabel = `${fwd.horizon_months}M`;

  return (
    <PanelCard>
      {/* ── Header: verdict + target context ── */}
      <div className="flex items-center justify-between gap-2 flex-wrap mb-3">
        <div className="flex items-center gap-2">
          <StatLabel>Signal Quality</StatLabel>
          <VerdictBadge
            verdict={fwd.verdict}
            title={
              fwd.verdict === 'STRONG' ? 'IC >= 0.10, spread > 0.50x vol, hit rate >= 60%, OOS stable'
              : fwd.verdict === 'PASS' ? 'All mandatory bars pass but fewer than 4 excellence criteria'
              : fwd.verdict === 'WEAK' ? (fwd.issues.join('; ') || 'Below quality floor on multiple criteria')
              : fwd.verdict === 'FAIL' ? (fwd.issues.join('; ') || 'Insufficient data or negative spread')
              : 'Validation not run'
            }
          />
          {fwd.issues.length > 0 && (
            <span className="text-[10px] text-warning" title={fwd.issues.join('; ')}>
              {fwd.issues.length} issue{fwd.issues.length > 1 ? 's' : ''}
            </span>
          )}
        </div>
        <span
          className="text-[10.5px] font-mono text-muted-foreground/70"
          title={`Validated against ${fwd.target} forward returns using ${fwd.n_observations} monthly observations since 2000`}
        >
          n={fwd.n_observations} months
        </span>
      </div>

      {/* ── Row 1: Per-state forward returns (the PM-actionable info) ── */}
      {Object.keys(fwd.per_state).length > 0 && (
        <div className="mb-3">
          <div className="flex items-baseline gap-1.5 mb-2">
            <span className="stat-label">
              {targetTicker} {horizonLabel} Forward Return by Regime State
            </span>
            <span className="text-[9.5px] text-muted-foreground/50">(annualized)</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
            {Object.entries(fwd.per_state).map(([state, stats]) => {
              const isBest = state === fwd.best_state;
              const isWorst = state === fwd.worst_state;
              const color = model?.color_map?.[state];
              const retStr = stats.mean_ann != null
                ? `${stats.mean_ann >= 0 ? '+' : ''}${(stats.mean_ann * 100).toFixed(1)}%`
                : '—';
              return (
                <div
                  key={state}
                  className={`rounded-[var(--radius)] border px-2.5 py-2 ${
                    isBest ? 'border-success/40 bg-success/[0.04]' :
                    isWorst ? 'border-destructive/40 bg-destructive/[0.04]' :
                    'border-border/30'
                  }`}
                  title={`When this regime is in ${state}, ${targetTicker} averages ${retStr} annualized over the next ${fwd.horizon_months} months. Vol: ${stats.vol_ann != null ? `${(stats.vol_ann * 100).toFixed(1)}%` : '—'}. Sharpe: ${stats.sharpe?.toFixed(2) ?? '—'}. Based on ${stats.n} monthly observations.`}
                >
                  <div className="flex items-center gap-1.5 mb-1">
                    {color && <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: color }} />}
                    <span className="text-[11px] font-mono font-semibold text-foreground uppercase tracking-[0.04em]">
                      {state}
                    </span>
                  </div>
                  <span className={`text-[18px] font-mono font-bold tabular-nums leading-none ${
                    stats.mean_ann != null && stats.mean_ann >= 0 ? 'text-success' : 'text-destructive'
                  }`}>
                    {retStr}
                  </span>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[9.5px] font-mono text-muted-foreground/50">
                      n={stats.n} · SR {stats.sharpe?.toFixed(2) ?? '—'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
          {fwd.spread_ann != null && (
            <p className="text-[10px] font-mono text-muted-foreground/50 mt-1.5"
               title={`Annualized return spread between best state (${fwd.best_state}) and worst state (${fwd.worst_state}). Cohen's d: ${fwd.cohens_d?.toFixed(2) ?? '—'}. Welch p: ${fwd.welch_p?.toFixed(4) ?? '—'}`}
            >
              Spread: {fwd.spread_ann >= 0 ? '+' : ''}{(fwd.spread_ann * 100).toFixed(1)}% ({fwd.best_state} vs {fwd.worst_state})
              {fwd.welch_p != null && <> · p={fwd.welch_p < 0.0001 ? '<0.0001' : fwd.welch_p.toFixed(4)}</>}
            </p>
          )}
        </div>
      )}

      {/* ── Row 2: IC curve + quality metrics ── */}
      <div className="border-t border-border/20 pt-2.5">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-x-4 gap-y-2">
          <MetricCell
            label="Hit Rate"
            value={pct(fwd.hit_rate)}
            sub={`${fwd.drawdown_events} drawdowns`}
            tooltip={`Of the ${fwd.drawdown_events} times ${targetTicker} drew down >10% from peak, how often was the regime in its worst state (${fwd.worst_state ?? '—'}) between the peak and the trough? 100% means every major drawdown was caught.`}
            good={fwd.hit_rate != null && fwd.hit_rate >= 0.60}
            bad={fwd.hit_rate != null && fwd.hit_rate < 0.50}
          />
          <MetricCell
            label="DD Avoid"
            value={pct(fwd.dd_avoidance_pct)}
            sub="worst-25% months"
            tooltip={`Of the worst 25% of monthly returns for ${targetTicker}, what percentage occurred when the regime was NOT in its best state? High = regime warns you before bad months. B&H max DD: ${fwd.bh_max_dd != null ? `${(fwd.bh_max_dd * 100).toFixed(1)}%` : '—'}`}
            good={fwd.dd_avoidance_pct != null && fwd.dd_avoidance_pct >= 0.50}
            bad={fwd.dd_avoidance_pct != null && fwd.dd_avoidance_pct < 0.30}
          />
          <MetricCell
            label="OOS"
            value={(() => {
              if (fwd.oos_sign_consistent === false) return 'Flipped';
              if (fwd.oos_spread_decay != null) return `${(fwd.oos_spread_decay * 100).toFixed(0)}% kept`;
              if (fwd.oos_sign_consistent === true) return 'Stable';
              return '—';
            })()}
            sub={fwd.spread_pre2010 != null ? `${(fwd.spread_pre2010 * 100).toFixed(0)}% → ${fwd.spread_post2010 != null ? `${(fwd.spread_post2010 * 100).toFixed(0)}%` : '—'}` : undefined}
            tooltip={`Out-of-sample: history split at Jan 2010. Shows what % of the pre-2010 spread survived post-2010. 100%+ = signal held or strengthened. <30% = signal collapsed — it mostly worked in one era only. Pre-2010 spread: ${fwd.spread_pre2010 != null ? `${(fwd.spread_pre2010 * 100).toFixed(1)}%` : '—'}, IC: ${fmtIc(fwd.ic_pre2010)}. Post-2010 spread: ${fwd.spread_post2010 != null ? `${(fwd.spread_post2010 * 100).toFixed(1)}%` : '—'}, IC: ${fmtIc(fwd.ic_post2010)}.`}
            good={fwd.oos_spread_decay != null && fwd.oos_spread_decay >= 0.50}
            bad={fwd.oos_sign_consistent === false || (fwd.oos_spread_decay != null && fwd.oos_spread_decay < 0.30)}
          />
          <MetricCell
            label="FPR"
            value={pct(fwd.false_positive_rate)}
            sub={`${fwd.n_transitions} flips`}
            tooltip={`False Positive Rate: how often the signal crosses 0.5 and reverts within 2 months. FPR < 20% is clean; > 40% = noisy, better used in composition. Total regime transitions: ${fwd.n_transitions}.`}
            good={fwd.false_positive_rate != null && fwd.false_positive_rate <= 0.20}
            bad={fwd.false_positive_rate != null && fwd.false_positive_rate > 0.40}
          />
        </div>
      </div>
    </PanelCard>
  );
}

/** Compact per-axis validation row for composite mode. Shows verdict,
 *  IC peak, target, and designed horizon for each input axis. */
export function CompositeForwardStrip({ models }: { models: RegimeModel[] }) {
  if (!models.length) return null;
  const hasAnyForward = models.some((m) => m.forward);
  if (!hasAnyForward) return null;

  // Collect D11 offenders (same as CompositeRobustnessStrip)
  const keys = new Set(models.map((m) => m.key));
  const seen = new Set<string>();
  const offenders: Array<{ a: string; b: string; rho: number }> = [];
  for (const m of models) {
    const ov = m.quality?.overlaps ?? [];
    for (const o of ov) {
      if (!keys.has(o.key)) continue;
      const [a, b] = [m.key, o.key].sort();
      const pairId = `${a}|${b}`;
      if (seen.has(pairId)) continue;
      seen.add(pairId);
      offenders.push({ a, b, rho: o.rho });
    }
  }
  offenders.sort((x, y) => Math.abs(y.rho) - Math.abs(x.rho));

  return (
    <PanelCard>
      <div className="flex items-center justify-between gap-2 mb-2.5">
        <StatLabel>Input Axes · {models.length} Regimes</StatLabel>
        {offenders.length === 0 && (
          <span className="text-[10px] font-mono uppercase tracking-[0.06em] text-success">orthogonal</span>
        )}
      </div>

      {/* Per-axis rows */}
      <div className="space-y-1.5">
        {models.map((m) => {
          const fwd = m.forward;
          if (!fwd) return (
            <div key={m.key} className="flex items-center gap-2 text-[11px] text-muted-foreground">
              <span className="font-mono font-semibold uppercase">{m.key}</span>
              <span>— no validation data</span>
            </div>
          );

          const targetTicker = fwd.target?.split(':')[0] ?? '';
          const ic1m = getIc1m(fwd);
          const spreadStr = fwd.spread_ann != null
            ? `${fwd.spread_ann >= 0 ? '+' : ''}${(fwd.spread_ann * 100).toFixed(1)}%`
            : '—';

          return (
            <div
              key={m.key}
              className="flex items-center gap-3 text-[11px]"
              title={`${m.display_name}: validated against ${targetTicker} 1M return. IC = ${ic1m != null ? `${ic1m >= 0 ? '+' : ''}${ic1m.toFixed(3)}` : '—'}. Best/worst state return spread: ${spreadStr}. OOS: ${fwd.oos_sign_consistent === true ? 'stable' : fwd.oos_sign_consistent === false ? 'flipped' : '—'}.`}
            >
              <VerdictDot verdict={fwd.verdict} />
              <span className="font-mono font-semibold text-foreground uppercase tracking-[0.04em] w-[120px] truncate">
                {m.key.replace(/_/g, ' ')}
              </span>
              <span className={`font-mono tabular-nums ${
                ic1m != null && ic1m >= 0.10 ? 'text-success' :
                ic1m != null && ic1m < 0.05 ? 'text-destructive' :
                'text-muted-foreground'
              }`}>
                IC {ic1m != null ? `${ic1m >= 0 ? '+' : ''}${ic1m.toFixed(2)}` : '—'}
              </span>
              <span className="font-mono text-muted-foreground/50">
                spread {spreadStr}
              </span>
              <span className={`font-mono text-muted-foreground/50 ${
                fwd.oos_sign_consistent === true ? 'text-success' :
                fwd.oos_sign_consistent === false ? 'text-destructive' : ''
              }`}>
                OOS {fwd.oos_sign_consistent === true ? 'stable' : fwd.oos_sign_consistent === false ? 'flipped' : '—'}
              </span>
            </div>
          );
        })}
      </div>

      {/* D11 overlap warnings */}
      {offenders.length > 0 && (
        <div className="mt-2.5 pt-2 border-t border-border/20">
          <div className="flex items-start gap-1.5">
            <AlertCircle className="w-3 h-3 text-warning shrink-0 mt-0.5" />
            <div className="text-[10px] text-warning leading-relaxed">
              {offenders.map(({ a, b, rho }) => (
                <span key={`${a}|${b}`} className="mr-3">
                  <span className="font-mono">{a}</span> ~ <span className="font-mono">{b}</span>{' '}
                  <span className="font-mono">(|r|={Math.abs(rho).toFixed(2)})</span>
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </PanelCard>
  );
}

/** Get the 1-month IC from the ic_curve, which is the standard
 *  measure: "does this regime predict what the target does next month?" */
function getIc1m(fwd: ForwardValidation): number | null {
  return fwd.ic_curve?.['1'] ?? null;
}

/** Single metric cell with tooltip for the ForwardValidationCard grid. */
function MetricCell({
  label,
  value,
  sub,
  tooltip,
  good,
  bad,
}: {
  label: string;
  value: string;
  sub?: string;
  tooltip?: string;
  good?: boolean;
  bad?: boolean;
}) {
  const valueColor = good ? 'text-success' : bad ? 'text-destructive' : 'text-foreground';
  return (
    <div className="flex flex-col group/metric relative" title={tooltip}>
      <span className="stat-label mb-0.5 cursor-help border-b border-dotted border-muted-foreground/30">{label}</span>
      <span className={`text-[13px] font-mono font-semibold tabular-nums ${valueColor}`}>{value}</span>
      {sub && <span className="text-[9.5px] font-mono text-muted-foreground/50">{sub}</span>}
    </div>
  );
}

export function PassFailChip({
  label,
  pass,
  detail,
}: {
  label: string;
  pass: boolean | null | undefined;
  detail?: string;
}) {
  const state = pass === null || pass === undefined ? 'na' : pass ? 'ok' : 'fail';
  const cls =
    state === 'ok'
      ? 'border-success/40 text-success bg-success/5'
      : state === 'fail'
        ? 'border-destructive/40 text-destructive bg-destructive/5'
        : 'border-border/50 text-muted-foreground bg-muted/30';
  const symbol = state === 'ok' ? '✓' : state === 'fail' ? '✗' : '·';
  return (
    <span
      title={detail}
      className={`inline-flex items-center gap-1 px-2 py-0.5 border rounded-sm font-mono text-[10px] uppercase tracking-[0.06em] ${cls}`}
    >
      <span>{symbol}</span>
      <span>{label}</span>
    </span>
  );
}

function fmtPct(v: number | null | undefined, decimals = 2): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return '—';
  return `${(v * 100).toFixed(decimals)}%`;
}

function fmtNum(v: number | null | undefined, decimals = 2): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return '—';
  return v.toFixed(decimals);
}

/** Compact robustness card showing tier badge + Tier 1 pass/fail chips +
 *  raw metric line + overlap warnings. Designed to slot into the top of
 *  CurrentStateTab. */
export function RobustnessCard({ quality }: { quality: QualitySnapshot | null | undefined }) {
  if (!quality) {
    return (
      <PanelCard>
        <div className="flex items-center justify-between gap-2">
          <StatLabel>Robustness</StatLabel>
          <span className="text-[11px] text-muted-foreground">
            No quality snapshot available — run <span className="font-mono">scripts/quality_snapshot_regimes.py</span>.
          </span>
        </div>
      </PanelCard>
    );
  }

  return (
    <PanelCard>
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <StatLabel>Robustness</StatLabel>
          <TierBadge tier={quality.tier} title={quality.tier_rationale} />
          {quality.phase_pair_waiver_applied && (
            <span
              title="Standalone T1.4 waived because this is the trend half of a level/trend phase pair."
              className="inline-flex items-center px-1.5 py-0.5 border border-border/40 rounded-sm font-mono text-[9px] uppercase tracking-[0.08em] text-muted-foreground bg-muted/30"
            >
              phase-pair waiver
            </span>
          )}
        </div>
        <span className="text-[10.5px] font-mono text-muted-foreground/70">
          {quality.target} · {quality.horizon_months}M · n={quality.n_observations}
        </span>
      </div>

      {/* Pass/fail chip row */}
      <div className="mt-3 flex flex-wrap gap-1.5">
        <PassFailChip
          label={`vol-norm ${fmtNum(quality.vol_normalized_spread)}`}
          pass={quality.t14_volnorm_pass}
          detail="T1.4 — vol-normalized spread (Sharpe-delta) ≥ 0.40"
        />
        <PassFailChip
          label={`spread ${fmtPct(quality.spread_ann)}`}
          pass={quality.spread_ann !== null && quality.spread_ann >= 0.05 ? true : quality.spread_ann === null ? null : false}
          detail="Annualized best-vs-worst forward return spread"
        />
        <PassFailChip
          label={`p ${fmtNum(quality.welch_p, 4)}`}
          pass={null}
          detail="Welch p — informational at 1M (not a tier gate)"
        />
        <PassFailChip
          label={`cov ${fmtPct(quality.coverage)}`}
          pass={quality.t11_coverage_pass}
          detail="T1.1 — coverage ≥ 85%"
        />
        <PassFailChip
          label={`run ${fmtNum(quality.median_run_months, 1)}m`}
          pass={quality.t12_run_length_pass}
          detail="T1.2 — median run length ≥ 4 months"
        />
        <PassFailChip
          label={`min n ${quality.min_state_n ?? '—'}`}
          pass={quality.t13_min_n_pass}
          detail="T1.3 — every state ≥ 30 obs"
        />
        <PassFailChip
          label="subsample"
          pass={quality.t16_subsample_pass}
          detail="T1.6 — sign consistent across pre/post-2010 split"
        />
        <PassFailChip
          label={quality.sensitivity_verdict ?? 'sens —'}
          pass={quality.t17_sensitivity_pass}
          detail="T1.7 — parameter sensitivity verdict ∈ {robust, sensitive}"
        />
        <PassFailChip
          label={quality.state_balance_verdict ?? 'bal —'}
          pass={quality.t18_balance_pass}
          detail="T1.8 — state balance ≠ degenerate"
        />
      </div>

      {/* Tier rationale — why this verdict */}
      {quality.tier_rationale && (
        <p className="mt-2 text-[11px] text-muted-foreground font-mono">
          {quality.tier_rationale}
        </p>
      )}

      {/* Overlap warnings (D11) */}
      {quality.overlaps && quality.overlaps.length > 0 && (
        <div className="mt-3 pt-3 border-t border-border/30">
          <div className="flex items-start gap-2 text-[11px] text-warning">
            <AlertCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
            <div>
              <span className="font-semibold">D11 overlap</span> · high correlation with{' '}
              {quality.overlaps.map((o, i) => (
                <span key={o.key} className="font-mono">
                  {i > 0 && ', '}
                  {o.key} ({o.rho >= 0 ? '+' : ''}{o.rho.toFixed(2)})
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </PanelCard>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Composite mode: per-axis quality strip + orthogonality pre-flight
// ─────────────────────────────────────────────────────────────────────

/** One compact row per input axis in a composition. Shows a mini tier
 *  badge, key name, target/horizon, and a 3-metric mini stat line. Also
 *  renders a single pre-flight banner if any pair in the composition
 *  crosses the D11 orthogonality bar (|ρ| > 0.60). */
export function CompositeRobustnessStrip({ models }: { models: RegimeModel[] }) {
  const keys = new Set(models.map((m) => m.key));

  // Collect D11 offenders among the selected set (each listed once per
  // direction then deduped). overlaps is symmetric in the JSON, so we
  // sort the pair and key by "a|b".
  const seen = new Set<string>();
  const offenders: Array<{ a: string; b: string; rho: number }> = [];
  for (const m of models) {
    const ov = m.quality?.overlaps ?? [];
    for (const o of ov) {
      if (!keys.has(o.key)) continue;
      const [a, b] = [m.key, o.key].sort();
      const pairId = `${a}|${b}`;
      if (seen.has(pairId)) continue;
      seen.add(pairId);
      offenders.push({ a, b, rho: o.rho });
    }
  }
  offenders.sort((x, y) => Math.abs(y.rho) - Math.abs(x.rho));

  return (
    <PanelCard>
      <div className="flex items-center justify-between gap-2 mb-3">
        <StatLabel>Composite Robustness · {models.length} Axes</StatLabel>
        {offenders.length === 0 && (
          <span className="text-[10px] font-mono uppercase tracking-[0.06em] text-success">
            ✓ orthogonal
          </span>
        )}
      </div>

      {/* Per-axis rows */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {models.map((m) => {
          const q = m.quality;
          return (
            <div
              key={m.key}
              className="flex items-center justify-between gap-2 px-2.5 py-1.5 border border-border/40 rounded-sm bg-card/50"
            >
              <div className="flex items-center gap-2 min-w-0">
                {q?.tier ? (
                  <TierBadge tier={q.tier} title={q.tier_rationale} />
                ) : (
                  <span className="text-[10px] font-mono text-muted-foreground">—</span>
                )}
                <span className="text-[11px] font-semibold text-foreground truncate">
                  {m.key}
                </span>
              </div>
              <div className="flex items-center gap-2 text-[10px] font-mono text-muted-foreground shrink-0">
                {q?.target && (
                  <span title="Locked target and horizon">
                    {q.target.split(' ')[0]} · {q.horizon_months}M
                  </span>
                )}
                {q?.vol_normalized_spread != null && (
                  <span
                    className={
                      q.t14_volnorm_pass === false ? 'text-destructive' : 'text-foreground'
                    }
                    title="T1.4 vol-normalized spread"
                  >
                    d={q.vol_normalized_spread.toFixed(2)}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* D11 pre-flight banner */}
      {offenders.length > 0 && (
        <div className="mt-3 pt-3 border-t border-border/30">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0 text-warning" />
            <div className="text-[11px] text-warning">
              <span className="font-semibold">D11 overlap</span> · this composition
              double-counts {offenders.length} pair{offenders.length > 1 ? 's' : ''}:
              <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 font-mono text-[10.5px]">
                {offenders.slice(0, 6).map((o) => (
                  <span key={`${o.a}|${o.b}`}>
                    {o.a} ↔ {o.b}{' '}
                    <span className="text-foreground/70">
                      ({o.rho >= 0 ? '+' : ''}{o.rho.toFixed(2)})
                    </span>
                  </span>
                ))}
              </div>
              <p className="mt-1.5 text-muted-foreground text-[10.5px] font-sans">
                High correlation inflates joint-state conviction without adding information.
                Consider removing one of each offending pair.
              </p>
            </div>
          </div>
        </div>
      )}
    </PanelCard>
  );
}
