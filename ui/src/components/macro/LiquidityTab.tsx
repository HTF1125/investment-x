'use client';

import { useMemo } from 'react';
import { useTheme } from '@/context/ThemeContext';
import type { PlotlyFigure } from '@/lib/chartTheme';
import type { Snapshot, TimeseriesData, BacktestData } from './types';
import { PHASE_COLORS, XAXIS_DATE, YAXIS_BASE, CHART_M } from './constants';
import { fmt, fmtPct, themed } from './helpers';
import { LoadingSpinner, SectionTitle, ChartBox, StatsRow } from './SharedComponents';
import ComponentBacktest from './ComponentBacktest';
import IndicatorWaterfall from './IndicatorWaterfall';

export default function LiquidityTab({ snapshot, timeseries, tsLoading, backtest, btLoading, target }: {
  snapshot: Snapshot; timeseries: TimeseriesData | null; tsLoading: boolean;
  backtest: BacktestData | null; btLoading: boolean; target: string;
}) {
  const { theme } = useTheme();

  const liquidityChart = useMemo(() => {
    if (!timeseries) return null;
    const shapes: any[] = [];
    let phaseStart = 0;
    for (let i = 1; i <= timeseries.dates.length; i++) {
      if (i === timeseries.dates.length || timeseries.liq_phase[i] !== timeseries.liq_phase[phaseStart]) {
        const phase = timeseries.liq_phase[phaseStart];
        shapes.push({
          type: 'rect', xref: 'x', yref: 'paper',
          x0: timeseries.dates[phaseStart], x1: timeseries.dates[i - 1],
          y0: 0, y1: 1, fillcolor: (PHASE_COLORS[phase] ?? '#888') + '15', line: { width: 0 }, layer: 'below',
        });
        phaseStart = i;
      }
    }
    const fig: PlotlyFigure = {
      data: [{
        type: 'scatter', x: timeseries.dates, y: timeseries.liquidity,
        name: 'Liquidity', mode: 'lines', line: { color: '#38bdf8', width: 2 },
        hovertemplate: '%{x|%Y-%m-%d}: %{y:.2f}<extra></extra>',
      }],
      layout: { yaxis: { ...YAXIS_BASE, title: 'Z-Score', titlefont: { size: 10 } }, xaxis: XAXIS_DATE, shapes, margin: CHART_M },
    };
    return themed(fig, theme);
  }, [timeseries, theme]);

  const phaseStats = snapshot.liq_phase_stats ?? [];
  const liqInds = snapshot.indicators?.liquidity ?? [];

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
        <div className="lg:col-span-3 panel-card p-2">
          <SectionTitle info="Liquidity composite z-score with cycle phase backgrounds. Spring (green) = recovering, Summer (yellow) = peak, Fall (red) = tightening, Winter (purple) = trough.">Liquidity Cycle</SectionTitle>
          {tsLoading ? <LoadingSpinner /> : <ChartBox chart={liquidityChart} height={240} />}
        </div>
        <div className="lg:col-span-2 space-y-3">
          {timeseries && (
            <div className="panel-card px-3 py-2">
              <SectionTitle info="Historical time spent in each cycle phase. Based on level (above/below zero) and momentum (rising/falling).">Phase Distribution</SectionTitle>
              <div className="grid grid-cols-4 gap-2 text-center">
                {(['Spring', 'Summer', 'Fall', 'Winter'] as const).map(phase => {
                  const count = timeseries.liq_phase.filter(p => p === phase).length;
                  const pct = count / timeseries.liq_phase.length;
                  return (
                    <div key={phase}>
                      <div className="flex items-center justify-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: PHASE_COLORS[phase] }} />
                        <span className="text-[10px] text-muted-foreground">{phase}</span>
                      </div>
                      <div className="text-[14px] font-mono font-semibold tabular-nums text-foreground">{fmtPct(pct)}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          {phaseStats.length > 0 && (
            <div className="panel-card px-3 py-2">
              <SectionTitle info="Historical 13-week forward returns by liquidity phase for the target index.">Phase Forward Returns</SectionTitle>
              <table className="w-full text-[11px]">
                <thead><tr className="border-b border-border/40">
                  <th className="text-left py-1 pr-2 text-[9px] font-mono uppercase text-muted-foreground/50">Phase</th>
                  <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Mean</th>
                  <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Sharpe</th>
                  <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">%Pos</th>
                  <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">N</th>
                </tr></thead>
                <tbody>
                  {phaseStats.map(s => (
                    <StatsRow key={s.phase} label={s.phase} color={PHASE_COLORS[s.phase]}
                      values={[`${fmt(s.mean_fwd_ret, 1)}%`, fmt(s.sharpe), `${fmt(s.pct_positive, 0)}%`, s.n]} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <IndicatorWaterfall indicators={liqInds} theme={theme} title="Liquidity Indicators"
        info="Individual liquidity indicator z-scores. Includes Fed balance sheet, M2, credit impulse, yield curve, financial conditions." />

      {backtest && !btLoading && (
        <ComponentBacktest backtest={backtest} componentKey="liquidity_only" label="Liquidity" color="#38bdf8" target={target} theme={theme} />
      )}
      {btLoading && <LoadingSpinner label="Loading backtest" />}
    </div>
  );
}
