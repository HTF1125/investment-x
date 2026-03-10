'use client';

import React, { useMemo } from 'react';
import { Loader2, Save, RotateCcw, Layers } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useFocusTrap } from '@/hooks/useFocusTrap';
import { useDashboardState } from '@/hooks/useDashboardState';
import type { ChartMeta } from '@/types/chart';
import DashboardToolbar from './DashboardToolbar';
import GalleryView from './GalleryView';
import FocusView from './FocusView';
import Spotlight from './Spotlight';

// ── Delete Confirmation Modal ──

function DeleteConfirmModal({
  target,
  onCancel,
  onConfirm,
}: {
  target: { id: string; name: string };
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const focusTrapRef = useFocusTrap(true, onCancel);
  return (
    <motion.div
      ref={focusTrapRef}
      className="w-full max-w-sm rounded-md border border-border/50 bg-popover shadow-lg p-5"
      initial={{ y: 16, scale: 0.97, opacity: 0 }}
      animate={{ y: 0, scale: 1, opacity: 1 }}
      exit={{ y: 10, scale: 0.98, opacity: 0 }}
      onClick={(e: React.MouseEvent) => e.stopPropagation()}
    >
      <div className="text-sm font-semibold text-foreground mb-1">Delete Chart</div>
      <div className="text-xs text-muted-foreground mb-4">
        Delete <span className="text-rose-400 font-mono font-medium">{target.name}</span>? This action cannot be undone.
      </div>
      <div className="flex items-center justify-end gap-2">
        <button
          onClick={onCancel}
          className="px-3 py-1.5 rounded-lg border border-border/50 text-xs text-muted-foreground hover:text-foreground hover:bg-primary/[0.08] transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={onConfirm}
          className="px-3 py-1.5 rounded-lg bg-rose-500/15 border border-rose-500/30 hover:bg-rose-500/25 text-rose-400 text-xs font-semibold transition-colors"
        >
          Delete
        </button>
      </div>
    </motion.div>
  );
}

// ── Save Order Bar ──

function SaveOrderBar({
  onReset,
  onSave,
  isSaving,
}: {
  onReset: () => void;
  onSave: () => void;
  isSaving: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      transition={{ duration: 0.2 }}
      role="status"
      aria-live="polite"
      className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[200] flex items-center gap-3 px-4 py-2.5 bg-popover/95 backdrop-blur-md border border-primary/30 rounded-md shadow-lg shadow-black/20"
    >
      <div className="w-2 h-2 rounded-full bg-primary animate-pulse" aria-hidden="true" />
      <span className="text-[11px] font-mono text-primary uppercase tracking-widest">Unsaved order</span>
      <div className="flex items-center gap-2 ml-1">
        <button
          onClick={onReset}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-[var(--radius)] border border-border/50 text-muted-foreground hover:text-foreground text-[10px] font-semibold transition-colors"
        >
          <RotateCcw className="w-3 h-3" /> Reset
        </button>
        <button
          onClick={onSave}
          disabled={isSaving}
          className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-primary/15 border border-primary/30 hover:bg-primary/25 text-primary text-[10px] font-bold transition-colors disabled:opacity-50"
        >
          {isSaving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
          Save Order
        </button>
      </div>
    </motion.div>
  );
}

// ── Loading Skeleton ──

function DashboardSkeleton() {
  return (
    <div className="p-2 md:p-3 space-y-4 min-h-[600px] animate-pulse w-full">
      <div className="grid grid-cols-12 gap-3">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="col-span-12 md:col-span-6 bg-card border border-border/30 rounded-[var(--radius)] min-h-[260px] max-h-[400px] flex flex-col overflow-hidden">
            <div className="h-8 border-b border-border/25 px-2.5 flex items-center gap-1.5">
              <div className="h-2 w-28 bg-primary/[0.06] rounded" />
            </div>
            <div className="flex-1 p-1.5">
              <div className="w-full h-full bg-primary/[0.04] rounded flex items-center justify-center">
                <Loader2 className="w-4 h-4 text-muted-foreground/20 animate-spin" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main Component ──

interface DashboardWorkspaceProps {
  chartsByCategory: Record<string, ChartMeta[]>;
  onChartSelected?: (chartId: string) => void;
}

export default function DashboardWorkspace({ chartsByCategory, onChartSelected }: DashboardWorkspaceProps) {
  const state = useDashboardState(chartsByCategory);

  // Handle external chart selection (from Ctrl+K via AppShell)
  React.useEffect(() => {
    if (onChartSelected) return; // Will be handled via callback, not state
  }, [onChartSelected]);

  // Spotlight chart data
  const spotlightChart = useMemo(() => {
    if (!state.spotlightChartId) return null;
    return state.allFilteredCharts.find(c => c.id === state.spotlightChartId) ||
      state.localCharts.find(c => c.id === state.spotlightChartId) || null;
  }, [state.spotlightChartId, state.allFilteredCharts, state.localCharts]);

  const spotlightIndex = useMemo(() => {
    if (!state.spotlightChartId) return 0;
    const idx = state.filteredCharts.findIndex(c => c.id === state.spotlightChartId);
    return idx >= 0 ? idx : 0;
  }, [state.spotlightChartId, state.filteredCharts]);

  const handleSpotlightNavigate = React.useCallback((index: number) => {
    const chart = state.filteredCharts[index];
    if (chart) state.setSpotlightChartId(chart.id);
  }, [state.filteredCharts, state.setSpotlightChartId]);

  const handleSpotlightClose = React.useCallback(() => {
    state.setSpotlightChartId(null);
  }, [state.setSpotlightChartId]);

  if (!state.mounted) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="h-[calc(100vh-48px)] flex flex-col overflow-hidden">
      {/* Toolbar: category tabs + search + view toggle + actions */}
      <DashboardToolbar state={state} />

      {/* Main content area */}
      <div className="flex-1 min-h-0 flex overflow-hidden">
        <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
          {state.viewMode === 'gallery' ? (
            <GalleryView state={state} />
          ) : (
            <FocusView state={state} />
          )}
        </div>
      </div>

      {/* Save Order Floating Bar */}
      <AnimatePresence>
        {state.isReorderEnabled && state.isOrderDirty && (
          <SaveOrderBar
            onReset={state.handleResetOrder}
            onSave={state.handleSaveOrder}
            isSaving={state.isReorderSaving}
          />
        )}
      </AnimatePresence>

      {/* Delete Confirmation Modal */}
      <AnimatePresence>
        {state.deleteTarget && (
          <motion.div
            className="fixed inset-0 z-[220] flex items-center justify-center bg-black/50 backdrop-blur-sm px-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => state.setDeleteTarget(null)}
            role="dialog"
            aria-modal="true"
          >
            <DeleteConfirmModal
              target={state.deleteTarget}
              onCancel={() => state.setDeleteTarget(null)}
              onConfirm={state.confirmDeleteChart}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Spotlight Overlay */}
      <AnimatePresence>
        {spotlightChart && (
          <Spotlight
            chart={spotlightChart}
            charts={state.filteredCharts}
            currentIndex={spotlightIndex}
            onClose={handleSpotlightClose}
            onNavigate={handleSpotlightNavigate}
            canEdit={state.canEditChart(spotlightChart)}
            canRefresh={state.canRefreshChart(spotlightChart)}
            canDelete={state.canDeleteChart(spotlightChart)}
            canManageVisibility={state.canManageVisibility}
            onCopy={state.handleCopyChart}
            onRefresh={state.handleRefreshChart}
            onDelete={(chartId: string) => {
              state.setSpotlightChartId(null);
              state.handleDeleteChart(chartId);
            }}
            onToggleVisibility={state.handleToggleVisibility}
            isRefreshing={!!state.refreshingChartIds[spotlightChart.id]}
            copySignal={state.copySignals[spotlightChart.id] || 0}
            isFavorite={state.favorites.has(spotlightChart.id)}
            onToggleFavorite={state.toggleFavorite}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
