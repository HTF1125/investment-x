'use client';

import React, { useState } from 'react';
import { Reorder } from 'framer-motion';
import { PanelTop } from 'lucide-react';
import FormatPanel from '@/components/chart-editor/FormatPanel';
import AnnotationsPanel from './AnnotationsPanel';
import SeriesRow from './SeriesRow';
import AxisControls from './AxisControls';
import PaneControls from './PaneControls';
import type { SelectedSeries, Pane, Annotation } from './types';

type Tab = 'series' | 'format' | 'annotate';

interface RightSidebarProps {
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
  // Format
  showLegend: boolean;
  setShowLegend: (v: boolean) => void;
  legendPosition: string;
  setLegendPosition: (v: string) => void;
  showGridlines: boolean;
  setShowGridlines: (v: boolean) => void;
  gridlineStyle: string;
  setGridlineStyle: (v: string) => void;
  showZeroline: boolean;
  setShowZeroline: (v: boolean) => void;
  titleFontSize: number;
  setTitleFontSize: (v: number) => void;
  bargap: number | undefined;
  setBargap: (v: number | undefined) => void;
  axisTitles: Record<string, string>;
  setAxisTitles: (v: Record<string, string>) => void;
  paneCount: number;
  // Annotations
  annotations: Annotation[];
  onAddAnnotation: (type: Annotation['type']) => void;
  onUpdateAnnotation: (id: string, updates: Partial<Annotation>) => void;
  onRemoveAnnotation: (id: string) => void;
  formStyle: React.CSSProperties;
}

export default function RightSidebar({
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
  showLegend,
  setShowLegend,
  legendPosition,
  setLegendPosition,
  showGridlines,
  setShowGridlines,
  gridlineStyle,
  setGridlineStyle,
  showZeroline,
  setShowZeroline,
  titleFontSize,
  setTitleFontSize,
  bargap,
  setBargap,
  axisTitles,
  setAxisTitles,
  paneCount,
  annotations,
  onAddAnnotation,
  onUpdateAnnotation,
  onRemoveAnnotation,
  formStyle,
}: RightSidebarProps) {
  const [tab, setTab] = useState<Tab>('series');

  if (!open) return null;

  const axisKeys = (() => {
    const keys = new Set<string>();
    selectedSeries.forEach((s) => keys.add(`${s.paneId ?? 0}-${s.yAxisIndex ?? 0}`));
    return Array.from(keys).sort();
  })();

  return (
    <div className="w-[280px] shrink-0 border-l border-border/30 flex flex-col bg-card/20 overflow-hidden">
      {/* Tab header */}
      <div className="shrink-0 h-8 border-b border-border/20 flex items-center px-0.5 gap-0">
        {(['series', 'format', 'annotate'] as Tab[]).map((t) => {
          const labels: Record<Tab, string> = { series: 'Series', format: 'Format', annotate: 'Annotate' };
          const badge = t === 'series' && selectedSeries.length > 0
            ? selectedSeries.length
            : t === 'annotate' && annotations.length > 0
            ? annotations.length
            : null;
          return (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`h-8 px-2 text-[11px] font-semibold uppercase tracking-[0.06em] transition-colors relative ${
                tab === t ? 'text-foreground' : 'text-muted-foreground/30 hover:text-foreground'
              }`}
            >
              {labels[t]}
              {badge != null && <span className="ml-0.5 text-primary/60">{badge}</span>}
              {tab === t && <span className="absolute bottom-0 left-1.5 right-1.5 h-[2px] bg-foreground rounded-full" />}
            </button>
          );
        })}

        <div className="flex-1" />

        {/* Add pane button — always visible */}
        <button
          onClick={onAddPane}
          className="w-5 h-5 flex items-center justify-center rounded-[3px] text-muted-foreground/25 hover:text-foreground hover:bg-foreground/[0.04] transition-colors mr-1"
          title="Add pane"
        >
          <PanelTop className="w-3 h-3" />
        </button>
      </div>

      {/* Tab content */}
      {tab === 'series' && (
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          {/* Series list */}
          <div className="flex-1 overflow-y-auto custom-scrollbar min-h-0">
            {selectedSeries.length === 0 ? (
              <div className="px-3 py-8 text-center">
                <p className="text-[11.5px] text-muted-foreground/25">Run code to load series</p>
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
      )}

      {tab === 'format' && (
        <FormatPanel
          showLegend={showLegend}
          onShowLegendChange={setShowLegend}
          legendPosition={legendPosition}
          onLegendPositionChange={setLegendPosition}
          showGridlines={showGridlines}
          onShowGridlinesChange={setShowGridlines}
          gridlineStyle={gridlineStyle}
          onGridlineStyleChange={setGridlineStyle}
          showZeroline={showZeroline}
          onShowZerolineChange={setShowZeroline}
          titleFontSize={titleFontSize}
          onTitleFontSizeChange={setTitleFontSize}
          bargap={bargap}
          onBargapChange={setBargap}
          axisTitles={axisTitles}
          onAxisTitlesChange={setAxisTitles}
          series={selectedSeries}
          onUpdateSeries={(code, updates) => onUpdateSeries(code, updates as Partial<SelectedSeries>)}
          hasBarSeries={selectedSeries.some((s) => s.chartType === 'bar' || s.chartType === 'stackedbar')}
          axisKeys={axisKeys}
          paneCount={paneCount}
        />
      )}

      {tab === 'annotate' && (
        <AnnotationsPanel
          annotations={annotations}
          onAdd={onAddAnnotation}
          onUpdate={onUpdateAnnotation}
          onRemove={onRemoveAnnotation}
          formStyle={formStyle}
        />
      )}
    </div>
  );
}
