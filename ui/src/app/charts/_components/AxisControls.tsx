'use client';

import type { Pane, SelectedSeries } from './types';

interface AxisControlsProps {
  selectedSeries: SelectedSeries[];
  panes: Pane[];
  logAxes: Set<string>;
  toggleLogAxis: (paneId: number, yAxisIndex: number) => void;
  invertedAxes: Set<string>;
  toggleInvertAxis: (paneId: number, yAxisIndex: number) => void;
  pctAxes: Set<string>;
  togglePctAxis: (paneId: number, yAxisIndex: number) => void;
  yAxisRanges: Record<string, { min?: number; max?: number }>;
  setYAxisRange: (paneId: number, yAxisIndex: number, range: { min?: number; max?: number }) => void;
}

export default function AxisControls({
  selectedSeries,
  panes,
  logAxes,
  toggleLogAxis,
  invertedAxes,
  toggleInvertAxis,
  pctAxes,
  togglePctAxis,
  yAxisRanges,
  setYAxisRange,
}: AxisControlsProps) {
  const axisKeys = new Set<string>();
  selectedSeries.forEach((s) => axisKeys.add(`${s.paneId ?? 0}-${s.yAxisIndex ?? 0}`));
  const sorted = Array.from(axisKeys).sort();
  if (sorted.length === 0) return null;

  return (
    <div className="shrink-0 border-t border-border/20 px-2 py-1.5 bg-foreground/[0.015]">
      <span className="stat-label mb-1 block">Axes</span>
      <div className="space-y-0.5">
        {sorted.map((key) => {
          const [paneId, yAxisIndex] = key.split('-').map(Number);
          const isLog = logAxes.has(key);
          const isInv = invertedAxes.has(key);
          const isPct = pctAxes.has(key);
          const range = yAxisRanges[key] || {};
          const label = panes.length > 1 ? `P${paneId + 1}\u00B7Y${yAxisIndex + 1}` : `Y${yAxisIndex + 1}`;
          return (
            <div key={key} className="flex items-center gap-0.5">
              <span className="text-[9.5px] font-mono font-bold text-muted-foreground/50 w-6 shrink-0">{label}</span>
              <button
                onClick={() => toggleLogAxis(paneId, yAxisIndex)}
                className={`h-[18px] px-1 text-[9.5px] font-mono font-bold rounded-[3px] transition-colors shrink-0 ${
                  isLog ? 'bg-foreground text-background' : 'text-muted-foreground/25 hover:text-foreground'
                }`}
                title="Log scale"
              >
                LOG
              </button>
              <button
                onClick={() => toggleInvertAxis(paneId, yAxisIndex)}
                className={`h-[18px] px-1 text-[9.5px] font-mono font-bold rounded-[3px] transition-colors shrink-0 ${
                  isInv ? 'bg-foreground text-background' : 'text-muted-foreground/25 hover:text-foreground'
                }`}
                title="Invert axis"
              >
                INV
              </button>
              <button
                onClick={() => togglePctAxis(paneId, yAxisIndex)}
                className={`h-[18px] w-5 text-[9.5px] font-mono font-bold rounded-[3px] transition-colors shrink-0 ${
                  isPct ? 'bg-foreground text-background' : 'text-muted-foreground/25 hover:text-foreground'
                }`}
                title="Percent format"
              >
                %
              </button>
              <input
                type="number"
                value={range.min ?? ''}
                onChange={(e) => {
                  const v = e.target.value;
                  setYAxisRange(paneId, yAxisIndex, { ...range, min: v === '' ? undefined : parseFloat(v) });
                }}
                className="w-[42px] h-[18px] px-1 text-[9.5px] font-mono text-center border border-border/25 rounded-[3px] bg-background text-foreground focus:outline-none focus:border-primary/40"
                placeholder="min"
                step="any"
              />
              <input
                type="number"
                value={range.max ?? ''}
                onChange={(e) => {
                  const v = e.target.value;
                  setYAxisRange(paneId, yAxisIndex, { ...range, max: v === '' ? undefined : parseFloat(v) });
                }}
                className="w-[42px] h-[18px] px-1 text-[9.5px] font-mono text-center border border-border/25 rounded-[3px] bg-background text-foreground focus:outline-none focus:border-primary/40"
                placeholder="max"
                step="any"
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
