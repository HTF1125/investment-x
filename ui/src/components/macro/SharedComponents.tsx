'use client';

import { Loader2, AlertCircle, Info } from 'lucide-react';
import dynamic from 'next/dynamic';
import { useTheme } from '@/context/ThemeContext';
import { THEME_TOKENS } from '@/lib/chartTheme';
import { PLOTLY_CONFIG, CHART_M, REGIME_ORDER, REGIME_COLORS } from './constants';
import { fmtPct } from './helpers';
import type { PlotlyFigure } from '@/lib/chartTheme';
import type { SummaryIndex } from './types';

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center bg-background/50">
      <Loader2 className="w-5 h-5 animate-spin text-primary/40" />
    </div>
  ),
}) as any;

export function LoadingSpinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center justify-center py-10">
      <div className="flex flex-col items-center gap-2">
        <Loader2 className="w-5 h-5 animate-spin text-primary/40" />
        <span className="text-[10px] text-muted-foreground/50 tracking-widest uppercase">{label ?? 'Loading'}</span>
      </div>
    </div>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center py-10">
      <div className="flex flex-col items-center gap-2 text-center">
        <AlertCircle className="w-5 h-5 text-destructive/60" />
        <p className="text-[11px] text-muted-foreground">{message}</p>
      </div>
    </div>
  );
}

export function InfoTooltip({ text }: { text: string }) {
  return (
    <span className="relative inline-flex group/tip ml-1 cursor-help align-middle">
      <Info className="w-3 h-3 text-muted-foreground/30 group-hover/tip:text-muted-foreground/60 transition-colors" />
      <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-2.5 py-1.5 text-[10px] leading-relaxed text-foreground bg-background border border-border/50 rounded-[var(--radius)] shadow-lg opacity-0 group-hover/tip:opacity-100 transition-opacity pointer-events-none w-[240px] z-50">
        {text}
      </span>
    </span>
  );
}

export function RegimeProbBar({ probs }: { probs: Record<string, number> }) {
  const { theme } = useTheme();
  const darkText = THEME_TOKENS[theme].text;
  const lightText = theme === 'light' ? 'rgb(255,255,255)' : 'rgb(255,255,255)';
  return (
    <div className="w-full">
      <div className="flex rounded-[var(--radius)] overflow-hidden h-5 border border-border/40">
        {REGIME_ORDER.map((r) => {
          const pct = (probs[r] ?? 0) * 100;
          if (pct < 1) return null;
          return (
            <div key={r} className="flex items-center justify-center text-[9px] font-mono font-semibold transition-all duration-500"
              style={{ width: `${pct}%`, backgroundColor: REGIME_COLORS[r], color: r === 'Deflation' ? darkText : lightText, minWidth: pct > 5 ? undefined : 0 }}
              title={`${r}: ${pct.toFixed(1)}%`}>
              {pct >= 10 ? `${pct.toFixed(0)}%` : ''}
            </div>
          );
        })}
      </div>
      <div className="flex gap-3 mt-1 flex-wrap">
        {REGIME_ORDER.map((r) => (
          <div key={r} className="flex items-center gap-1">
            <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: REGIME_COLORS[r] }} />
            <span className="text-[9px] text-muted-foreground">{r}</span>
            <span className="text-[9px] font-mono text-foreground tabular-nums">{fmtPct(probs[r] ?? 0)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SectionTitle({ children, info }: { children: React.ReactNode; info?: string }) {
  return (
    <h3 className="section-title mb-2 flex items-center">
      {children}
      {info && <InfoTooltip text={info} />}
    </h3>
  );
}

/** Render a Plotly chart at given height. */
export function ChartBox({ chart, height = 240 }: { chart: PlotlyFigure | null; height?: number }) {
  if (!chart) return <ErrorBox message="No data" />;
  return (
    <div style={{ height }}>
      <Plot data={chart.data} layout={{ ...chart.layout, autosize: true, margin: chart.layout?.margin ?? CHART_M }}
        config={PLOTLY_CONFIG} useResizeHandler style={{ width: '100%', height: '100%' }} />
    </div>
  );
}

/** Compact stats table row. */
export function StatsRow({ label, color, values }: { label: string; color?: string; values: (string | number | React.ReactNode)[] }) {
  return (
    <tr className="border-t border-border/[0.08] hover:bg-primary/[0.04] transition-colors duration-100">
      <td className="py-1 pr-3 font-medium text-foreground text-[11px] whitespace-nowrap">
        {color && <span className="inline-block w-2 h-2 rounded-full mr-1.5 align-middle" style={{ backgroundColor: color }} />}
        {label}
      </td>
      {values.map((v, i) => (
        <td key={i} className="text-right py-1 px-1.5 font-mono tabular-nums text-[11px] text-foreground">{v}</td>
      ))}
    </tr>
  );
}

// ─── Signal / Overview Components ─────────────────────────────────────────────

const SIGNAL_COLORS: Record<string, { border: string; bg: string; text: string }> = {
  'Risk-On': { border: 'border-success/60', bg: 'bg-success/8', text: 'text-success' },
  'Neutral': { border: 'border-warning/60', bg: 'bg-warning/8', text: 'text-warning' },
  'Risk-Off': { border: 'border-destructive/60', bg: 'bg-destructive/8', text: 'text-destructive' },
};

function labelColor(label: string) {
  return SIGNAL_COLORS[label] ?? SIGNAL_COLORS['Neutral'];
}

export function RegimeCard({ idx }: { idx: SummaryIndex }) {
  const colors = labelColor(idx.label);
  return (
    <div className={`panel-card px-3 py-2.5 text-left ${colors.border}`}>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[11px] font-semibold text-foreground">{idx.index_name}</span>
        <span className={`text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded ${colors.bg} ${colors.text}`}>
          {idx.label}
        </span>
      </div>
      <div className="flex items-baseline gap-3">
        <span className="text-[18px] font-mono font-bold text-foreground tabular-nums">
          {idx.eq_weight != null ? `${(idx.eq_weight * 100).toFixed(0)}%` : '—'}
        </span>
        {idx.alpha != null && (
          <span className={`text-[11px] font-mono tabular-nums ${idx.alpha >= 0 ? 'text-success' : 'text-destructive'}`}>
            {idx.alpha >= 0 ? '+' : ''}{(idx.alpha * 100).toFixed(1)}% α
          </span>
        )}
      </div>
      <div className="flex items-center justify-between mt-1">
        <div className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: REGIME_COLORS[idx.regime] ?? '#888' }} />
          <span className="text-[9px] font-mono text-muted-foreground/50">{idx.regime}</span>
        </div>
        {idx.sharpe != null && (
          <span className="text-[9px] font-mono text-muted-foreground/50">
            Sharpe {idx.sharpe.toFixed(2)}
          </span>
        )}
      </div>
    </div>
  );
}

export function PerformanceTable({ indices }: { indices: SummaryIndex[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="data-table text-[11px]">
        <thead>
          <tr>
            {['Index', 'Regime', 'Signal', 'Alloc', 'Sharpe', 'Alpha', 'Max DD', 'Return'].map((h) => (
              <th key={h} className="text-left">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {indices.map((idx) => {
            const colors = labelColor(idx.label);
            return (
              <tr key={idx.index_name}>
                <td className="py-1.5 px-2 font-medium text-foreground">{idx.index_name}</td>
                <td className="py-1.5 px-2">
                  <span className="inline-flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: REGIME_COLORS[idx.regime] ?? '#888' }} />
                    <span className="text-[10px] font-mono text-foreground">{idx.regime}</span>
                  </span>
                </td>
                <td className="py-1.5 px-2">
                  <span className={`signal-pill ${colors.bg} ${colors.text} border ${colors.border}`}>
                    {idx.label}
                  </span>
                </td>
                <td className="py-1.5 px-2 font-mono tabular-nums text-foreground text-right">
                  {idx.eq_weight != null ? `${(idx.eq_weight * 100).toFixed(0)}%` : '—'}
                </td>
                <td className="py-1.5 px-2 font-mono tabular-nums text-foreground text-right">
                  {idx.sharpe != null ? idx.sharpe.toFixed(2) : '—'}
                </td>
                <td className={`py-1.5 px-2 font-mono tabular-nums text-right ${
                  idx.alpha != null && idx.alpha >= 0 ? 'text-success' : 'text-destructive'
                }`}>
                  {idx.alpha != null ? `${idx.alpha >= 0 ? '+' : ''}${(idx.alpha * 100).toFixed(1)}%` : '—'}
                </td>
                <td className="py-1.5 px-2 font-mono tabular-nums text-destructive text-right">
                  {idx.max_dd != null ? `${(idx.max_dd * 100).toFixed(1)}%` : '—'}
                </td>
                <td className={`py-1.5 px-2 font-mono tabular-nums text-right ${
                  idx.ann_return != null && idx.ann_return >= 0 ? 'text-success' : 'text-destructive'
                }`}>
                  {idx.ann_return != null ? `${(idx.ann_return * 100).toFixed(1)}%` : '—'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
