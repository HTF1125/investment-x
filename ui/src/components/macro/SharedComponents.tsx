'use client';

import { Loader2, AlertCircle, Info } from 'lucide-react';
import dynamic from 'next/dynamic';
import { PLOTLY_CONFIG, CHART_M, REGIME_ORDER, REGIME_COLORS } from './constants';
import { fmtPct } from './helpers';
import type { PlotlyFigure } from '@/lib/chartTheme';

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
        <AlertCircle className="w-5 h-5 text-rose-500/60" />
        <p className="text-[11px] text-muted-foreground">{message}</p>
      </div>
    </div>
  );
}

export function InfoTooltip({ text }: { text: string }) {
  return (
    <span className="relative inline-flex group/tip ml-1 cursor-help align-middle">
      <Info className="w-3 h-3 text-muted-foreground/30 group-hover/tip:text-muted-foreground/60 transition-colors" />
      <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-2.5 py-1.5 text-[10px] leading-relaxed text-foreground bg-background border border-border/50 rounded-lg shadow-lg opacity-0 group-hover/tip:opacity-100 transition-opacity pointer-events-none w-[240px] z-50">
        {text}
      </span>
    </span>
  );
}

export function RegimeProbBar({ probs }: { probs: Record<string, number> }) {
  return (
    <div className="w-full">
      <div className="flex rounded-lg overflow-hidden h-5 border border-border/40">
        {REGIME_ORDER.map((r) => {
          const pct = (probs[r] ?? 0) * 100;
          if (pct < 1) return null;
          return (
            <div key={r} className="flex items-center justify-center text-[9px] font-mono font-semibold transition-all duration-500"
              style={{ width: `${pct}%`, backgroundColor: REGIME_COLORS[r], color: r === 'Deflation' ? '#1a1a2e' : '#fff', minWidth: pct > 5 ? undefined : 0 }}
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
    <h3 className="text-[12px] font-semibold text-foreground mb-2 flex items-center">
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
    <tr className="border-b border-border/20">
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
