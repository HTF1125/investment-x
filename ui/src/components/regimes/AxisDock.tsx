'use client';

import { useState } from 'react';
import { useQueries } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import type { RegimeModel, CurrentStateResponse, InputRegimeState } from './types';

/** Compact 24-month z-score sparkline rendered inline in each AxisDock tile.
 * Reads from current_state.dimensions[<dim>].history (populated by the
 * standalone /current endpoint) and clamps to [-2, +2] so all sparklines
 * stay visually comparable across axes. */
function MiniSparkline({
  values,
  width = 80,
  height = 14,
}: {
  values: number[] | undefined;
  width?: number;
  height?: number;
}) {
  if (!values || values.length < 2) return null;
  const clamped = values.map((v) => Math.max(-2, Math.min(2, v)));
  const stepX = width / (clamped.length - 1);
  const points = clamped
    .map((v, i) => {
      const x = i * stepX;
      const y = height - ((v + 2) / 4) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
  const zeroY = height / 2;
  return (
    <svg width={width} height={height} className="overflow-visible">
      <line
        x1="0"
        x2={width}
        y1={zeroY}
        y2={zeroY}
        stroke="rgb(var(--border))"
        strokeDasharray="2 2"
        strokeWidth="0.5"
      />
      <polyline
        fill="none"
        stroke="rgb(var(--foreground) / 0.85)"
        strokeWidth="1"
        strokeLinejoin="round"
        strokeLinecap="round"
        points={points}
      />
    </svg>
  );
}

interface Props {
  models: RegimeModel[];
  selectedKeys: Set<string>;
  onToggle: (key: string) => void;
  /** Per-regime overrides from the active composition.
   * When present, the tile shows these values (aligned to the joint
   * composite's date) instead of the standalone snapshot's latest data —
   * keeps the dock numerically consistent with the dim cards inside
   * CurrentStateTab. */
  overrides?: Record<string, InputRegimeState>;
}

/** Axis Dock — full-width row of regime tiles, each showing the live current
 * state of that 1D regime. Acts as both the navigation (click to toggle into
 * the composition) and a summary dashboard ("what is each axis saying right
 * now?") in one compact strip.
 *
 * Parallel-fetches each regime's current state via TanStack Query so the
 * tiles populate independently as data arrives.
 */
export function AxisDock({ models, selectedKeys, onToggle, overrides }: Props) {
  // Mobile-only collapse. On < sm the dock starts collapsed and only renders
  // the currently-selected tiles (+ an expand toggle). On sm+ this state is
  // ignored and all tiles render via `sm:grid` always-visible classes.
  const [mobileExpanded, setMobileExpanded] = useState(false);

  const queries = useQueries({
    queries: models.map((m) => ({
      queryKey: ['regime-current', m.key],
      queryFn: () =>
        apiFetchJson<CurrentStateResponse>(`/api/regimes/${m.key}/current`),
      staleTime: 120_000,
    })),
  });

  const selectedCount = selectedKeys.size;
  const totalCount = models.length;

  return (
    <div>
      {/* Mobile-only summary/toggle bar — hidden on sm+ */}
      <div className="sm:hidden flex items-center justify-between gap-2 mb-1.5">
        <span className="stat-label">
          AXES · <span className="text-foreground">{selectedCount}</span>/{totalCount}
        </span>
        <button
          type="button"
          onClick={() => setMobileExpanded((e) => !e)}
          className="font-mono text-[10px] uppercase tracking-[0.08em] px-2 h-6 border border-border/50 text-muted-foreground hover:text-foreground hover:border-border transition-colors"
          aria-expanded={mobileExpanded}
          aria-label={mobileExpanded ? 'Collapse axis dock' : 'Show all axes'}
        >
          {mobileExpanded ? '[−] CLOSE' : selectedCount === 0 ? '[+] PICK' : '[+] ALL'}
        </button>
      </div>

      {/* On mobile (< sm), when the dock is expanded we bound it to at most
          half the viewport height and let tiles beyond that scroll inside
          the dock. Prevents the bottom tiles from being clipped below
          the tab bar / content when all N axes are open. Desktop (sm+)
          uses the normal flow since the xl:grid-cols-9 row fits in one
          line and no scroll is needed. */}
      <div
        className={`grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-9 gap-1.5 ${
          mobileExpanded ? 'max-h-[50vh] overflow-y-auto no-scrollbar sm:max-h-none sm:overflow-visible pr-0.5' : ''
        }`}
      >
      {models.map((m, i) => {
        const q = queries[i];
        const cs = q.data?.current_state;
        const ov = overrides?.[m.key];
        const dom = ov?.dominant ?? cs?.dominant ?? '—';
        const active = selectedKeys.has(m.key);
        const probSrc = ov?.dominant_probability ?? cs?.dominant_probability;
        const prob = probSrc != null ? Math.round(probSrc * 100) : null;
        const months = ov?.months_in_regime ?? cs?.months_in_regime ?? 0;
        const convictionSrc = ov?.conviction ?? cs?.conviction;
        const conviction = convictionSrc != null ? Math.round(convictionSrc) : null;

        const dims = cs?.dimensions ?? {};
        const firstDim = Object.values(dims)[0];
        const sparkValues =
          ov?.z_history && ov.z_history.length > 1 ? ov.z_history : firstDim?.history;
        const zLatest =
          sparkValues && sparkValues.length > 0 ? sparkValues[sparkValues.length - 1] : null;
        const accelSrc = ov?.z_acceleration ?? firstDim?.acceleration;

        const zColorClass =
          zLatest == null
            ? 'text-muted-foreground'
            : zLatest > 0.3
            ? 'text-success'
            : zLatest < -0.3
            ? 'text-destructive'
            : 'text-foreground';

        const hiddenOnMobile = !active && !mobileExpanded;

        return (
          <button
            key={m.key}
            onClick={() => onToggle(m.key)}
            className={`group relative border px-2 py-1.5 text-left transition-colors focus:outline-none focus:ring-1 focus:ring-accent/50 ${
              hiddenOnMobile ? 'hidden sm:block' : ''
            } ${
              active
                ? 'border-accent bg-accent/[0.06]'
                : 'border-border/50 bg-card hover:border-border'
            }`}
            style={{ borderRadius: 'calc(var(--radius) - 2px)' }}
          >
            {/* Top row: axis name — full width */}
            <div className="flex items-center justify-between gap-1">
              <span className="text-[9px] uppercase tracking-[0.10em] font-mono font-semibold text-muted-foreground leading-tight truncate">
                {m.display_name.split(' (')[0]}
              </span>
              {active && <span className="text-[9px] font-mono text-accent leading-none">●</span>}
            </div>

            {/* Two-column body: state + sparkline | z-score numeric */}
            <div className="mt-1 grid grid-cols-[1fr_56px] gap-2 items-end">
              <div className="min-w-0">
                <div
                  className="text-[11px] font-semibold tracking-tight leading-tight truncate text-foreground h-[14px]"
                  title={dom}
                >
                  {q.isLoading && !ov ? (
                    <span className="text-muted-foreground">…</span>
                  ) : (
                    dom
                  )}
                </div>
                <div className="mt-1 h-[14px] flex items-center">
                  {sparkValues && sparkValues.length > 1 && (
                    <MiniSparkline values={sparkValues} />
                  )}
                </div>
              </div>
              <div className="text-right leading-none">
                <div className={`text-[15px] font-mono tabular-nums font-semibold ${zColorClass}`}>
                  {zLatest != null ? (zLatest >= 0 ? '+' : '') + zLatest.toFixed(2) : '—'}
                </div>
                <div className="text-[8.5px] font-mono uppercase tracking-[0.06em] text-muted-foreground mt-1 tabular-nums">
                  {months}MO
                </div>
              </div>
            </div>

            {/* Footer: prob + conviction + accel */}
            <div className="mt-1 flex items-baseline justify-between text-[9px] font-mono">
              <span className="text-muted-foreground">
                <span className="uppercase tracking-[0.06em]">P</span>{' '}
                <span className="tabular-nums text-foreground/80">
                  {prob !== null ? `${prob}%` : '—'}
                </span>
                {conviction !== null && (
                  <>
                    <span className="mx-1 text-muted-foreground/50">·</span>
                    <span className="uppercase tracking-[0.06em]">C</span>{' '}
                    <span
                      className={`tabular-nums ${
                        conviction >= 50
                          ? 'text-success'
                          : conviction >= 30
                          ? 'text-warning'
                          : 'text-destructive'
                      }`}
                    >
                      {conviction}
                    </span>
                  </>
                )}
              </span>
              {accelSrc != null && (
                <span
                  className={`tabular-nums ${accelSrc >= 0 ? 'text-success' : 'text-destructive'}`}
                  title={`3M Δz ${accelSrc.toFixed(2)}`}
                >
                  {accelSrc >= 0 ? '▲' : '▼'}
                  {Math.abs(accelSrc).toFixed(1)}
                </span>
              )}
            </div>
          </button>
        );
      })}
      </div>
    </div>
  );
}
