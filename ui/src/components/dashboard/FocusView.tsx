'use client';

import React, { useState, useMemo, useCallback } from 'react';
import { ChevronDown, RefreshCw, Copy, Pencil, Loader2 } from 'lucide-react';
import dynamic from 'next/dynamic';
import Chart from '@/components/Chart';
import type { DashboardState } from '@/hooks/useDashboardState';
import type { ChartMeta } from '@/types/chart';

const CustomChartEditor = dynamic(() => import('../CustomChartEditor'), {
  ssr: false,
  loading: () => (
    <div className="flex-1 flex items-center justify-center text-muted-foreground/40">
      <Loader2 className="w-5 h-5 animate-spin" />
    </div>
  ),
});

interface FocusViewProps {
  state: DashboardState;
}

export default function FocusView({ state }: FocusViewProps) {
  const {
    focusPanels,
    setFocusPanels,
    focusPanelCount,
    focusHeights,
    focusContainerRef,
    startFocusDrag,
    filteredCharts,
    refreshingChartIds,
    copySignals,
    handleRefreshChart,
    handleCopyChart,
    canEditChart,
    canRefreshChart,
  } = state;

  // Track which chart is being edited inline (only one at a time)
  const [editingChartId, setEditingChartId] = useState<string | null>(null);

  // Build the resolved panel chart IDs: use focusPanels first, then auto-fill from filteredCharts
  const resolvedPanelIds = useMemo(() => {
    const ids: (string | null)[] = [];
    for (let i = 0; i < focusPanelCount; i++) {
      if (focusPanels[i] && filteredCharts.some(c => c.id === focusPanels[i])) {
        ids.push(focusPanels[i]);
      } else if (filteredCharts[i]) {
        ids.push(filteredCharts[i].id);
      } else {
        ids.push(null);
      }
    }
    return ids;
  }, [focusPanels, focusPanelCount, filteredCharts]);

  // Map chart IDs to ChartMeta for quick lookup
  const chartMap = useMemo(() => {
    const map = new Map<string, ChartMeta>();
    for (const c of filteredCharts) map.set(c.id, c);
    return map;
  }, [filteredCharts]);

  const handleSwapChart = useCallback((panelIndex: number, chartId: string) => {
    // Close editor if the swapped panel was being edited
    setEditingChartId(null);
    setFocusPanels(prev => {
      const next = [...resolvedPanelIds];
      next[panelIndex] = chartId;
      return next.map(id => id ?? '');
    });
  }, [setFocusPanels, resolvedPanelIds]);

  const handleToggleEdit = useCallback((chartId: string) => {
    setEditingChartId(prev => prev === chartId ? null : chartId);
  }, []);

  const handleCloseEditor = useCallback(() => {
    setEditingChartId(null);
  }, []);

  if (filteredCharts.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground/40">
        <div className="text-center">
          <p className="text-sm font-medium">No charts available</p>
          <p className="text-xs mt-1">Create a chart or adjust your filters</p>
        </div>
      </div>
    );
  }

  const panels = resolvedPanelIds.slice(0, focusPanelCount);

  return (
    <div ref={focusContainerRef as React.RefObject<HTMLDivElement>} className="h-full flex flex-col overflow-hidden">
      {panels.map((chartId, paneIdx) => {
        const chart = chartId ? chartMap.get(chartId) ?? null : null;
        const isEditing = chart !== null && editingChartId === chart.id;
        return (
          <React.Fragment key={paneIdx}>
            {/* Panel */}
            <div
              className="overflow-hidden flex flex-col min-h-0"
              style={{ height: `${focusHeights[paneIdx]}%` }}
            >
              {/* Panel header */}
              <PanelHeader
                chart={chart}
                panelIndex={paneIdx}
                filteredCharts={filteredCharts}
                onSwapChart={handleSwapChart}
                onEdit={handleToggleEdit}
                onRefresh={handleRefreshChart}
                onCopy={handleCopyChart}
                isRefreshing={chartId ? !!refreshingChartIds[chartId] : false}
                canEdit={chart ? canEditChart(chart) : false}
                canRefresh={chart ? canRefreshChart(chart) : false}
                isEditing={isEditing}
              />
              {/* Chart area / Editor */}
              <div className="flex-1 min-h-0 bg-background">
                {isEditing ? (
                  <CustomChartEditor
                    mode="integrated"
                    initialChartId={chart.id}
                    onClose={handleCloseEditor}
                  />
                ) : chart ? (
                  <Chart
                    id={chart.id}
                    initialFigure={chart.figure as any}
                    copySignal={copySignals[chart.id]}
                    interactive={true}
                    scrollZoom={true}
                  />
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground/30 text-xs font-mono">
                    EMPTY PANEL
                  </div>
                )}
              </div>
            </div>
            {/* Divider between panels */}
            {paneIdx < panels.length - 1 && (
              <div
                className="h-1 shrink-0 cursor-row-resize bg-border/40 hover:bg-primary/40 active:bg-primary/60 transition-colors"
                onMouseDown={(e) => startFocusDrag(paneIdx, e)}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ── Panel Header ──

interface PanelHeaderProps {
  chart: ChartMeta | null;
  panelIndex: number;
  filteredCharts: ChartMeta[];
  onSwapChart: (panelIndex: number, chartId: string) => void;
  onEdit: (chartId: string) => void;
  onRefresh: (chartId: string) => void;
  onCopy: (chartId: string) => void;
  isRefreshing: boolean;
  canEdit: boolean;
  canRefresh: boolean;
  isEditing: boolean;
}

function PanelHeader({
  chart,
  panelIndex,
  filteredCharts,
  onSwapChart,
  onEdit,
  onRefresh,
  onCopy,
  isRefreshing,
  canEdit,
  canRefresh,
  isEditing,
}: PanelHeaderProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = React.useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  React.useEffect(() => {
    if (!dropdownOpen) return;
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [dropdownOpen]);

  return (
    <div className="h-8 shrink-0 flex items-center gap-2 px-3 border-b border-border/20 bg-card">
      {/* Chart name + swap dropdown */}
      <div ref={dropdownRef} className="relative flex items-center gap-1 min-w-0 flex-1">
        <button
          onClick={() => setDropdownOpen(prev => !prev)}
          className="flex items-center gap-1 min-w-0 hover:text-foreground transition-colors"
        >
          <span className="text-xs font-medium text-foreground/80 truncate">
            {chart?.name || 'Select chart'}
          </span>
          <ChevronDown className="w-3 h-3 text-muted-foreground/50 shrink-0" />
        </button>

        {chart?.category && (
          <span className="text-[9px] font-mono text-muted-foreground/40 shrink-0 hidden sm:inline-block">
            {chart.category}
          </span>
        )}

        {/* Dropdown menu */}
        {dropdownOpen && (
          <div className="absolute top-full left-0 z-50 mt-1 w-64 max-h-60 overflow-y-auto rounded-[var(--radius)] border border-border/50 bg-card shadow-lg no-scrollbar">
            {filteredCharts.map(c => (
              <button
                key={c.id}
                onClick={() => {
                  onSwapChart(panelIndex, c.id);
                  setDropdownOpen(false);
                }}
                className={`w-full text-left px-3 py-1.5 text-xs hover:bg-primary/5 transition-colors flex items-center gap-2 ${
                  c.id === chart?.id ? 'bg-primary/10 text-foreground' : 'text-foreground/70'
                }`}
              >
                <span className="truncate flex-1">{c.name || 'Untitled'}</span>
                {c.category && (
                  <span className="text-[9px] font-mono text-muted-foreground/30 shrink-0">
                    {c.category}
                  </span>
                )}
              </button>
            ))}
            {filteredCharts.length === 0 && (
              <div className="px-3 py-2 text-xs text-muted-foreground/40">No charts</div>
            )}
          </div>
        )}
      </div>

      {/* Action buttons */}
      {chart && (
        <div className="flex items-center gap-0.5 shrink-0">
          {canEdit && (
            <button
              onClick={() => onEdit(chart.id)}
              title={isEditing ? 'Close editor' : 'Edit'}
              className={`btn-icon transition-colors ${
                isEditing
                  ? 'text-primary bg-primary/10'
                  : 'text-muted-foreground/50 hover:text-foreground'
              }`}
            >
              <Pencil className="w-3 h-3" />
            </button>
          )}
          {canRefresh && (
            <button
              onClick={() => onRefresh(chart.id)}
              disabled={isRefreshing}
              title="Refresh"
              className="btn-icon text-muted-foreground/50 hover:text-foreground transition-colors disabled:opacity-40"
            >
              <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`} />
            </button>
          )}
          <button
            onClick={() => onCopy(chart.id)}
            title="Copy as PNG"
            className="btn-icon text-muted-foreground/50 hover:text-foreground transition-colors"
          >
            <Copy className="w-3 h-3" />
          </button>
        </div>
      )}
    </div>
  );
}
