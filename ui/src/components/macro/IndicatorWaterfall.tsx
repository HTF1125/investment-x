'use client';

import { useMemo } from 'react';
import type { PlotlyFigure } from '@/lib/chartTheme';
import type { Indicator } from './types';
import { XAXIS_DATE, YAXIS_BASE, CHART_M_HBAR } from './constants';
import { zColor, themed } from './helpers';
import { SectionTitle, ChartBox } from './SharedComponents';

/** Horizontal bar waterfall for indicator z-scores. */
export default function IndicatorWaterfall({ indicators, theme, title, info }: {
  indicators: Indicator[]; theme: 'light' | 'dark'; title: string; info: string;
}) {
  const chart = useMemo(() => {
    if (!indicators.length) return null;
    const sorted = [...indicators].sort((a, b) => b.z - a.z);
    const fig: PlotlyFigure = {
      data: [{
        type: 'bar', y: sorted.map(i => i.name), x: sorted.map(i => i.z),
        orientation: 'h', marker: { color: sorted.map(i => zColor(i.z)) },
        hovertemplate: '%{y}: z=%{x:.2f}<extra></extra>',
      }],
      layout: { xaxis: { ...XAXIS_DATE, type: 'linear' as any, zeroline: true, title: 'Z-Score', titlefont: { size: 10 } }, yaxis: { ...YAXIS_BASE, automargin: true, showgrid: false }, margin: CHART_M_HBAR },
    };
    return themed(fig, theme);
  }, [indicators, theme]);

  if (!indicators.length) return null;
  return (
    <div className="panel-card p-2">
      <SectionTitle info={info}>{title} ({indicators.length})</SectionTitle>
      <ChartBox chart={chart} height={Math.max(200, indicators.length * 22 + 50)} />
    </div>
  );
}
