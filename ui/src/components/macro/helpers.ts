import { applyChartTheme, type PlotlyFigure } from '@/lib/chartTheme';

export function fmt(v: number, d = 2): string { return v?.toFixed(d) ?? '-'; }
export function fmtPct(v: number, d = 1): string { return `${(v * 100).toFixed(d)}%`; }
export function signalColor(s: string): string {
  const l = s.toLowerCase();
  return l === 'bullish' || l === 'positive' ? 'text-emerald-500' : l === 'bearish' || l === 'negative' ? 'text-rose-500' : 'text-muted-foreground';
}
export function zColor(z: number): string {
  return z > 0.5 ? '#3fb950' : z > 0 ? '#3fb950aa' : z > -0.5 ? '#f85149aa' : '#f85149';
}
export function themed(fig: PlotlyFigure, theme: 'light' | 'dark'): PlotlyFigure {
  return applyChartTheme(fig, theme, { transparentBackground: true }) as PlotlyFigure;
}
