'use client';

import React from 'react';
import { PanelTop } from 'lucide-react';
import { Reorder } from 'framer-motion';
import type { SelectedSeries, Pane } from './types';
import SeriesRow from './SeriesRow';
import AxisControls from './AxisControls';
import PaneControls from './PaneControls';

interface LeftSidebarProps {
  open: boolean;
  // Series
  selectedSeries: SelectedSeries[];
  setSelectedSeries: React.Dispatch<React.SetStateAction<SelectedSeries[]>>;
  onRemoveSeries: (code: string) => void;
  onUpdateSeries: (code: string, updates: Partial<SelectedSeries>) => void;
  failedCodes: Set<string>;
  // Panes
  panes: Pane[];
  onAddPane: () => void;
  onRemovePane: (paneId: number) => void;
  // Axis controls
  logAxes: Set<string>;
  toggleLogAxis: (paneId: number, yAxisIndex: number) => void;
  invertedAxes: Set<string>;
  toggleInvertAxis: (paneId: number, yAxisIndex: number) => void;
  pctAxes: Set<string>;
  togglePctAxis: (paneId: number, yAxisIndex: number) => void;
  yAxisRanges: Record<string, { min?: number; max?: number }>;
  setYAxisRange: (paneId: number, yAxisIndex: number, range: { min?: number; max?: number }) => void;
}

export default function LeftSidebar({
  open,
  selectedSeries,
  setSelectedSeries,
  onRemoveSeries,
  onUpdateSeries,
  failedCodes,
  panes,
  onAddPane,
  onRemovePane,
  logAxes,
  toggleLogAxis,
  invertedAxes,
  toggleInvertAxis,
  pctAxes,
  togglePctAxis,
  yAxisRanges,
  setYAxisRange,
}: LeftSidebarProps) {
  if (!open) return null;

  return (
    <div className="w-[240px] shrink-0 border-r border-border/30 flex flex-col bg-card/20 overflow-hidden">
      {/* Header */}
      <div className="shrink-0 h-8 border-b border-border/20 flex items-center px-2.5 gap-1.5">
        <span className="text-[9px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/50 flex-1">
          Series
          {selectedSeries.length > 0 && (
            <span className="ml-1 text-primary/60">{selectedSeries.length}</span>
          )}
        </span>
        <button
          onClick={onAddPane}
          className="w-5 h-5 flex items-center justify-center rounded-[3px] text-muted-foreground/25 hover:text-foreground hover:bg-foreground/[0.04] transition-colors"
          title="Add pane"
        >
          <PanelTop className="w-3 h-3" />
        </button>
      </div>

      {/* Series list */}
      <div className="flex-1 overflow-y-auto custom-scrollbar min-h-0">
        {selectedSeries.length === 0 ? (
          <div className="px-3 py-6 text-center">
            <p className="text-[10px] text-muted-foreground/25">Run code to load series</p>
          </div>
        ) : (
          <Reorder.Group axis="y" values={selectedSeries} onReorder={setSelectedSeries} as="div">
            {selectedSeries.map((s, i) => (
              <Reorder.Item key={s.code} value={s} as="div" dragListener>
                <SeriesRow
                  series={s}
                  index={i}
                  onRemove={() => onRemoveSeries(s.code)}
                  onUpdate={(updates) => onUpdateSeries(s.code, updates)}
                  hasError={failedCodes.has(s.code)}
                  panes={panes}
                />
              </Reorder.Item>
            ))}
          </Reorder.Group>
        )}
      </div>

      {/* Axis controls */}
      <AxisControls
        selectedSeries={selectedSeries}
        panes={panes}
        logAxes={logAxes}
        toggleLogAxis={toggleLogAxis}
        invertedAxes={invertedAxes}
        toggleInvertAxis={toggleInvertAxis}
        pctAxes={pctAxes}
        togglePctAxis={togglePctAxis}
        yAxisRanges={yAxisRanges}
        setYAxisRange={setYAxisRange}
      />

      {/* Pane controls */}
      <PaneControls panes={panes} onRemovePane={onRemovePane} />
    </div>
  );
}
