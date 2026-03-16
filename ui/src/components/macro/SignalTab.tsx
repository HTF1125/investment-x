'use client';

import { LoadingSpinner, SectionTitle } from './SharedComponents';
import type { SummaryIndex, CurrentSignalData } from './types';

const SIGNAL_COLORS: Record<string, { border: string; bg: string; text: string }> = {
  'Risk-On': { border: 'border-success/60', bg: 'bg-success/8', text: 'text-success' },
  'Neutral': { border: 'border-warning/60', bg: 'bg-warning/8', text: 'text-warning' },
  'Risk-Off': { border: 'border-destructive/60', bg: 'bg-destructive/8', text: 'text-destructive' },
};

const CAT_ORDER = ['Growth', 'Inflation', 'Liquidity', 'Tactical'] as const;
const CAT_COLORS: Record<string, string> = {
  Growth: '#3fb950', Inflation: '#f0883e', Liquidity: '#58a6ff', Tactical: '#bc8cff',
};

function labelColor(label: string) {
  return SIGNAL_COLORS[label] ?? SIGNAL_COLORS['Neutral'];
}

// ─── Regime Card ─────────────────────────────────────────────────────────────

function RegimeCard({
  idx,
  selected,
  onClick,
}: {
  idx: SummaryIndex;
  selected: boolean;
  onClick: () => void;
}) {
  const colors = labelColor(idx.label);
  return (
    <button
      onClick={onClick}
      className={`panel-card px-3 py-2.5 text-left transition-all cursor-pointer ${colors.border} ${
        selected ? 'ring-1 ring-primary/40' : ''
      }`}
    >
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
      {idx.sharpe != null && (
        <div className="mt-1 text-[9px] font-mono text-muted-foreground/50">
          Sharpe {idx.sharpe.toFixed(2)}
        </div>
      )}
    </button>
  );
}

// ─── Category Breakdown ──────────────────────────────────────────────────────

function CategoryBreakdown({ catSignals }: { catSignals: Record<string, { eq_weight: number; label: string; date: string }> }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
      {CAT_ORDER.map((cat) => {
        const sig = catSignals[cat];
        if (!sig) return null;
        const colors = labelColor(sig.label);
        return (
          <div key={cat} className={`panel-card px-2.5 py-2 ${colors.border}`}>
            <div className="flex items-center gap-1.5 mb-1">
              <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: CAT_COLORS[cat] }} />
              <span className="stat-label">{cat}</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-[15px] font-mono font-bold text-foreground tabular-nums">
                {(sig.eq_weight * 100).toFixed(0)}%
              </span>
              <span className={`text-[10px] font-mono font-semibold ${colors.text}`}>
                {sig.label}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Factor Readings ─────────────────────────────────────────────────────────

function FactorReadings({ signal }: { signal: CurrentSignalData | null }) {
  if (!signal?.factor_selections) return null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {CAT_ORDER.map((cat) => {
        const factors = signal.factor_selections[cat];
        if (!factors?.length) return null;
        return (
          <div key={cat} className="panel-card px-3 py-2">
            <div className="flex items-center gap-1.5 mb-2">
              <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: CAT_COLORS[cat] }} />
              <span className="text-[11px] font-semibold text-foreground">{cat}</span>
              <span className="text-[9px] font-mono text-muted-foreground/40 ml-auto">
                {factors.length} factors
              </span>
            </div>
            <div className="space-y-0.5">
              {factors.slice(0, 8).map((f) => (
                <div key={f.name} className="flex items-center gap-2 text-[10px]">
                  <span className="text-muted-foreground truncate flex-1">{f.name}</span>
                  <span className={`font-mono tabular-nums font-semibold ${
                    f.ic > 0 ? 'text-success' : f.ic < 0 ? 'text-destructive' : 'text-muted-foreground'
                  }`}>
                    {f.ic > 0 ? '+' : ''}{f.ic.toFixed(3)}
                  </span>
                  {/* IC bar */}
                  <div className="w-12 h-1 bg-border/30 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${Math.min(Math.abs(f.ic) / 0.3 * 100, 100)}%`,
                        backgroundColor: f.ic > 0 ? '#3fb950' : '#f85149',
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Performance Table ───────────────────────────────────────────────────────

function PerformanceTable({ indices }: { indices: SummaryIndex[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[11px]">
        <thead>
          <tr className="border-b border-border/30">
            {['Index', 'Regime', 'Alloc', 'Sharpe', 'Alpha', 'Max DD', 'Return'].map((h) => (
              <th key={h} className="py-1.5 px-2 text-left font-semibold text-muted-foreground/60 text-[10px] uppercase tracking-wider">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {indices.map((idx) => {
            const colors = labelColor(idx.label);
            return (
              <tr key={idx.index_name} className="border-b border-border/15 hover:bg-card/50">
                <td className="py-1.5 px-2 font-medium text-foreground">{idx.index_name}</td>
                <td className="py-1.5 px-2">
                  <span className={`text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded ${colors.bg} ${colors.text}`}>
                    {idx.label}
                  </span>
                </td>
                <td className="py-1.5 px-2 font-mono tabular-nums text-foreground">
                  {idx.eq_weight != null ? `${(idx.eq_weight * 100).toFixed(0)}%` : '—'}
                </td>
                <td className="py-1.5 px-2 font-mono tabular-nums text-foreground">
                  {idx.sharpe != null ? idx.sharpe.toFixed(2) : '—'}
                </td>
                <td className={`py-1.5 px-2 font-mono tabular-nums ${
                  idx.alpha != null && idx.alpha >= 0 ? 'text-success' : 'text-destructive'
                }`}>
                  {idx.alpha != null ? `${idx.alpha >= 0 ? '+' : ''}${(idx.alpha * 100).toFixed(1)}%` : '—'}
                </td>
                <td className="py-1.5 px-2 font-mono tabular-nums text-destructive">
                  {idx.max_dd != null ? `${(idx.max_dd * 100).toFixed(1)}%` : '—'}
                </td>
                <td className={`py-1.5 px-2 font-mono tabular-nums ${
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

// ─── Main Component ──────────────────────────────────────────────────────────

export default function SignalTab({
  summary,
  signal,
  signalLoading,
  selectedIndex,
  onSelectIndex,
}: {
  summary: SummaryIndex[] | null;
  signal: CurrentSignalData | null;
  signalLoading: boolean;
  selectedIndex: string;
  onSelectIndex: (idx: string) => void;
}) {
  if (!summary?.length) {
    return <LoadingSpinner label="Loading signals" />;
  }

  const selectedSummary = summary.find((s) => s.index_name === selectedIndex) ?? summary[0];

  return (
    <div className="space-y-3">
      {/* Regime Cards Grid */}
      <div>
        <SectionTitle info="Current regime signal and equity allocation for each index. Click to see category breakdown.">
          Regime Signals
        </SectionTitle>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-1.5">
          {summary.map((idx) => (
            <RegimeCard
              key={idx.index_name}
              idx={idx}
              selected={idx.index_name === selectedIndex}
              onClick={() => onSelectIndex(idx.index_name)}
            />
          ))}
        </div>
      </div>

      {/* Category Breakdown for selected index */}
      {selectedSummary.category_signals && (
        <div>
          <SectionTitle info="Per-category signal breakdown showing Growth, Inflation, Liquidity, and Tactical composites.">
            {selectedIndex} — Category Breakdown
          </SectionTitle>
          <CategoryBreakdown catSignals={selectedSummary.category_signals} />
        </div>
      )}

      {/* Factor Readings for selected index */}
      <div>
        <SectionTitle info="IC-ranked factor selections currently active for this index. IC = Information Coefficient (Spearman correlation with forward returns).">
          {selectedIndex} — Factor Readings
        </SectionTitle>
        {signalLoading ? (
          <LoadingSpinner label="Loading factor data" />
        ) : signal?.factor_selections ? (
          <FactorReadings signal={signal} />
        ) : (
          <div className="text-[10px] text-muted-foreground/40 py-4 text-center">
            No factor data available
          </div>
        )}
      </div>

      {/* Performance Table */}
      <div className="panel-card px-3 py-2">
        <SectionTitle info="Walk-forward backtest performance for the Blended (4-category) strategy across all indices.">
          Performance Summary
        </SectionTitle>
        <PerformanceTable indices={summary} />
      </div>
    </div>
  );
}
