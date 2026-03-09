'use client';

import { useMemo } from 'react';
import { useTheme } from '@/context/ThemeContext';
import type { PlotlyFigure } from '@/lib/chartTheme';
import type { Snapshot, TimeseriesData, BacktestData } from './types';
import { TACTICAL_COLORS, XAXIS_DATE, YAXIS_BASE, CHART_M } from './constants';
import { fmt, fmtPct, themed } from './helpers';
import { LoadingSpinner, SectionTitle, ChartBox, StatsRow } from './SharedComponents';
import ComponentBacktest from './ComponentBacktest';
import IndicatorWaterfall from './IndicatorWaterfall';

export default function TacticalTab({ snapshot, timeseries, tsLoading, backtest, btLoading, target }: {
  snapshot: Snapshot; timeseries: TimeseriesData | null; tsLoading: boolean;
  backtest: BacktestData | null; btLoading: boolean; target: string;
}) {
  const { theme } = useTheme();

  const tacticalChart = useMemo(() => {
    if (!timeseries) return null;
    const fig: PlotlyFigure = {
      data: [
        { type: 'scatter', x: timeseries.dates, y: timeseries.tactical, name: 'Tactical', mode: 'lines', line: { color: '#d29922', width: 2 } },
        { type: 'scatter', x: timeseries.dates, y: timeseries.allocation, name: 'Allocation', mode: 'lines', line: { color: '#38bdf8', width: 1.5, dash: 'dot' }, yaxis: 'y2' },
      ],
      layout: {
        yaxis: { ...YAXIS_BASE, title: 'Score', titlefont: { size: 10 } },
        yaxis2: { ...YAXIS_BASE, title: 'Alloc', overlaying: 'y', side: 'right', tickformat: '.0%', titlefont: { size: 10 }, showgrid: false },
        xaxis: XAXIS_DATE, hovermode: 'x unified', legend: { orientation: 'h', y: 1.08, font: { size: 9 } }, margin: CHART_M,
      },
    };
    return themed(fig, theme);
  }, [timeseries, theme]);

  const tacStats = snapshot.tactical_stats ?? [];
  const tacInds = snapshot.indicators?.tactical ?? [];

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
        <div className="lg:col-span-3 panel-card p-2">
          <SectionTitle info="Tactical composite z-score (solid) and the model's blended allocation weight (dotted). Contrarian indicators (VIX, put/call) fire bullish at market stress extremes.">Tactical Score & Allocation</SectionTitle>
          {tsLoading ? <LoadingSpinner /> : <ChartBox chart={tacticalChart} height={240} />}
        </div>
        <div className="lg:col-span-2 space-y-3">
          <div className="panel-card px-3 py-2">
            <SectionTitle info="Latest tactical composite score and the model's recommended equity allocation weight.">Current Reading</SectionTitle>
            <div className="grid grid-cols-2 gap-2 text-center">
              <div>
                <div className="text-[9px] font-mono uppercase text-muted-foreground/50">Score</div>
                <div className={`text-[16px] font-mono font-semibold ${snapshot.current.tactical >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>{fmt(snapshot.current.tactical)}</div>
              </div>
              <div>
                <div className="text-[9px] font-mono uppercase text-muted-foreground/50">Allocation</div>
                <div className="text-[16px] font-mono font-semibold text-foreground">{fmtPct(snapshot.current.allocation)}</div>
              </div>
            </div>
          </div>
          {tacStats.length > 0 && (
            <div className="panel-card px-3 py-2">
              <SectionTitle info="Historical 13-week forward returns bucketed by tactical score level. Extreme readings tend to be the most predictive.">Forward Returns by Score</SectionTitle>
              <table className="w-full text-[11px]">
                <thead><tr className="border-b border-border/40">
                  <th className="text-left py-1 pr-2 text-[9px] font-mono uppercase text-muted-foreground/50">Bucket</th>
                  <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Mean</th>
                  <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">Sharpe</th>
                  <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">%Pos</th>
                  <th className="text-right py-1 px-1 text-[9px] font-mono uppercase text-muted-foreground/50">N</th>
                </tr></thead>
                <tbody>
                  {tacStats.map(s => (
                    <StatsRow key={s.bucket} label={s.bucket} color={TACTICAL_COLORS[s.bucket]}
                      values={[`${fmt(s.mean_fwd_ret, 1)}%`, fmt(s.sharpe), `${fmt(s.pct_positive, 0)}%`, s.n]} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <IndicatorWaterfall indicators={tacInds} theme={theme} title="Tactical Indicators"
        info="Short-term positioning indicators. Contrarian signals (VIX, put/call) are NOT inverted — high fear readings = bullish. Credit stress indicators (HY spread, FCI) are inverted." />

      {backtest && !btLoading && (
        <ComponentBacktest backtest={backtest} componentKey="tactical_only" label="Tactical" color="#d29922" target={target} theme={theme} />
      )}
      {btLoading && <LoadingSpinner label="Loading backtest" />}
    </div>
  );
}
