'use client';

import type { SummaryIndex } from './types';
import { LoadingSpinner, RegimeCard, PerformanceTable, SectionTitle } from './SharedComponents';
import CrossMarketTab from './CrossMarketTab';
import RobustnessTab from './RobustnessTab';

export default function OverviewTab({ summary }: {
  summary: SummaryIndex[] | null;
}) {
  if (!summary?.length) {
    return <LoadingSpinner label="Loading overview" />;
  }

  return (
    <div className="space-y-3">
      {/* Regime Signals Grid */}
      <div>
        <SectionTitle info="Current regime signal and equity allocation for each index. Shows walk-forward regime classification, equity weight, and backtest alpha.">
          Regime Signals
        </SectionTitle>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-1.5">
          {summary.map((idx) => (
            <RegimeCard key={idx.index_name} idx={idx} />
          ))}
        </div>
      </div>

      {/* Performance Summary Table */}
      <div className="panel-card px-3 py-2">
        <SectionTitle info="Walk-forward backtest performance for the Blended (4-category) strategy across all indices.">
          Performance Summary
        </SectionTitle>
        <PerformanceTable indices={summary} />
      </div>

      {/* Cross-Market Analysis */}
      <CrossMarketTab />

      {/* Robustness Analysis */}
      <RobustnessTab />
    </div>
  );
}
