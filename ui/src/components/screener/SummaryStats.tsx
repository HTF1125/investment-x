'use client';

import { useMemo } from 'react';
import type { ScreenerStock } from './types';

interface Props {
  stocks: ScreenerStock[];
}

export default function SummaryStats({ stocks }: Props) {
  const stats = useMemo(() => {
    if (!stocks.length) return null;
    const trendConfirmed = stocks.filter(s => s.trend_confirmed).length;
    const highMomentum = stocks.filter(s => (s.vomo_composite ?? 0) >= 2).length;
    const avgVomo = stocks.reduce((sum, s) => sum + (s.vomo_composite ?? 0), 0) / stocks.length;
    const avgDrawdown = stocks.reduce((sum, s) => sum + (s.drawdown_52w ?? 0), 0) / stocks.length;

    // Top sector by count
    const sectorCounts: Record<string, number> = {};
    for (const s of stocks) {
      if (s.sector) sectorCounts[s.sector] = (sectorCounts[s.sector] || 0) + 1;
    }
    const topSector = Object.entries(sectorCounts).sort((a, b) => b[1] - a[1])[0];

    return {
      universe: stocks.length,
      trendConfirmed,
      trendPct: Math.round((trendConfirmed / stocks.length) * 100),
      highMomentum,
      avgVomo: avgVomo.toFixed(2),
      avgDrawdown: avgDrawdown.toFixed(1),
      topSector: topSector ? `${topSector[0]} (${topSector[1]})` : '-',
    };
  }, [stocks]);

  if (!stats) return null;

  const cards = [
    { label: 'Universe', value: stats.universe.toString() },
    { label: 'Trend Confirmed', value: `${stats.trendConfirmed}`, sub: `${stats.trendPct}%` },
    { label: 'Avg VOMO', value: stats.avgVomo, title: 'Volatility Momentum — composite signal measuring value and momentum across timeframes' },
    { label: 'VOMO > 2', value: stats.highMomentum.toString(), title: 'Stocks with VOMO composite score above 2' },
    { label: 'Top Sector', value: stats.topSector, mono: false },
    { label: 'Avg Drawdown', value: `${stats.avgDrawdown}%` },
  ];

  return (
    <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 mb-3">
      {cards.map(card => (
        <div key={card.label} className="panel-card px-3 py-2" title={card.title}>
          <div className="stat-label mb-0.5">{card.label}</div>
          <div className={`text-[14px] font-semibold text-foreground ${card.mono === false ? 'text-[13px]' : 'font-mono tabular-nums'}`}>
            {card.value}
            {card.sub && (
              <span className="text-[11.5px] text-muted-foreground/50 ml-1">{card.sub}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
