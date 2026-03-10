'use client';

import React from 'react';
import { Layers } from 'lucide-react';
import ChartTile from './ChartTile';
import type { DashboardState } from '@/hooks/useDashboardState';

interface GalleryViewProps {
  state: DashboardState;
}

export default function GalleryView({ state }: GalleryViewProps) {
  const displayGroups =
    state.activeCategory === 'all'
      ? state.groupedCharts
      : [{ category: state.activeCategory, charts: state.filteredCharts }];

  const hasCharts = displayGroups.some((g) => g.charts.length > 0);

  return (
    <div ref={state.mainScrollRef as React.RefObject<HTMLDivElement>} className="overflow-y-auto flex-1 p-3 md:p-4">
      {hasCharts ? (
        displayGroups.map((group) => {
          if (group.charts.length === 0) return null;

          return (
            <div key={group.category} className="mb-6">
              {/* ── Section header (only when showing all categories) ── */}
              {state.activeCategory === 'all' && (
                <div className="flex items-center gap-3 px-1 mb-3">
                  <span className="text-[9px] font-semibold text-muted-foreground/50 uppercase tracking-[0.15em] shrink-0">
                    {group.category}
                  </span>
                  <span className="text-[9px] font-mono text-muted-foreground/30">
                    {group.charts.length}
                  </span>
                  <div className="flex-1 h-px bg-border/20" />
                </div>
              )}

              {/* ── Chart grid ── */}
              <div className="grid grid-cols-12 gap-3">
                {group.charts.map((chart) => (
                  <div
                    key={chart.id}
                    id={`chart-anchor-${chart.id}`}
                    className="col-span-12 md:col-span-6 min-h-[260px] max-h-[400px]"
                    style={{
                      contentVisibility: 'auto',
                      containIntrinsicSize: '0 300px',
                    }}
                  >
                    <ChartTile
                      chart={chart}
                      canEdit={state.canEditChart(chart)}
                      canRefresh={state.canRefreshChart(chart)}
                      canDelete={state.canDeleteChart(chart)}
                      canManageVisibility={state.canManageVisibility}
                      onToggleVisibility={state.handleToggleVisibility}
                      onRefresh={state.handleRefreshChart}
                      onCopy={state.handleCopyChart}
                      onDelete={state.handleDeleteChart}
                      isRefreshing={!!state.refreshingChartIds[chart.id]}
                      copySignal={state.copySignals[chart.id] || 0}
                      onOpenSpotlight={state.setSpotlightChartId}
                      isFavorite={state.favorites.has(chart.id)}
                      onToggleFavorite={state.toggleFavorite}
                    />
                  </div>
                ))}
              </div>
            </div>
          );
        })
      ) : (
        /* ── Empty state ── */
        <div className="flex flex-col items-center justify-center py-24 text-muted-foreground/40">
          <Layers className="w-10 h-10 mb-3 stroke-[1.2]" />
          <span className="text-sm font-medium">No charts found</span>
        </div>
      )}
    </div>
  );
}
