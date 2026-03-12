'use client';

import React, { useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import {
  RefreshCw, FileText, FileCode, Plus, Search,
  Layers, Loader2, Save, RotateCcw,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useFocusTrap } from '@/hooks/useFocusTrap';
import { useDashboardCharts } from '@/hooks/useDashboardCharts';
import { useDashboardActions } from '@/hooks/useDashboardActions';
import { useDashboardPermissions } from '@/hooks/useDashboardPermissions';
import ChartTile from './ChartTile';
import { ChartErrorBoundary } from '@/components/ChartErrorBoundary';
import type { ChartMeta } from '@/types/chart';

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
      className="w-full max-w-sm panel-card p-5"
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
        <button onClick={onCancel} className="btn-secondary h-7 text-[10px]">Cancel</button>
        <button onClick={onConfirm} className="btn-danger h-7 text-[10px]">Delete</button>
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
      className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[200] flex items-center gap-3 px-4 py-2.5 bg-popover/95 backdrop-blur-md border border-primary/30 rounded-[var(--radius)] shadow-lg shadow-black/20"
    >
      <div className="w-2 h-2 rounded-full bg-primary animate-pulse" aria-hidden="true" />
      <span className="text-[11px] font-mono text-primary uppercase tracking-widest">Unsaved order</span>
      <div className="flex items-center gap-2 ml-1">
        <button onClick={onReset} className="btn-toolbar h-6 text-[10px]">
          <RotateCcw className="w-3 h-3" /> Reset
        </button>
        <button onClick={onSave} disabled={isSaving} className="btn-primary h-6 text-[10px]">
          {isSaving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
          Save Order
        </button>
      </div>
    </motion.div>
  );
}

// ── Main Dashboard Component ──

interface DashboardProps {
  chartsByCategory: Record<string, ChartMeta[]>;
}

export default function Dashboard({ chartsByCategory }: DashboardProps) {
  const router = useRouter();
  const perms = useDashboardPermissions();
  const charts = useDashboardCharts(chartsByCategory);
  const onVisibilityToggled = useCallback(
    (id: string, status: boolean) => charts.updateChartOptimistic(id, { public: status }),
    [charts.updateChartOptimistic],
  );
  const actions = useDashboardActions({
    onChartDeleted: charts.removeChart,
    onVisibilityToggled,
    onOrderSaved: charts.resetOrder,
  });

  const openChart = useCallback((chartId: string) => {
    router.push(`/?chartId=${chartId}`);
  }, [router]);

  // Use ref for allCharts to avoid recreating handlers on every chart list change
  const allChartsRef = useRef(charts.allCharts);
  allChartsRef.current = charts.allCharts;

  // Delete handler
  const handleDeleteChart = useCallback((id: string) => {
    const target = allChartsRef.current.find(c => c.id === id);
    if (!target || !perms.canDeleteChart(target)) return;
    actions.setDeleteTarget({ id, name: target.name || id });
  }, [perms, actions]);

  // Refresh handler
  const handleRefreshChart = useCallback((id: string) => {
    const target = allChartsRef.current.find(c => c.id === id);
    if (!target || !perms.canRefreshChart(target)) return;
    actions.refreshChart(id);
  }, [perms, actions]);

  // Visibility handler
  const handleToggleVisibility = useCallback((id: string, status: boolean) => {
    if (!perms.canManageVisibility) return;
    actions.toggleVisibility(id, status);
  }, [perms, actions]);

  // Gallery groups
  const displayGroups = charts.activeCategory === 'all'
    ? charts.groupedCharts
    : [{ category: charts.activeCategory, charts: charts.filteredCharts }];

  const hasCharts = displayGroups.some(g => g.charts.length > 0);
  const totalVisible = charts.filteredCharts.length;

  return (
    <div className="h-[calc(100vh-48px)] flex flex-col overflow-hidden">
      {/* ── Toolbar ── */}
      <div className="px-4 sm:px-5 lg:px-6 border-b border-border/20 shrink-0">
        <div className="flex items-center gap-2 h-11">
          {/* Category tabs */}
          <div className="flex gap-0.5 overflow-x-auto no-scrollbar flex-1 min-w-0 -mb-px">
            <button
              onClick={() => charts.setActiveCategory('all')}
              className={`tab-link ${charts.activeCategory === 'all' ? 'active' : ''}`}
            >
              All
              <span className="ml-1.5 text-[9px] text-muted-foreground/30 font-mono tabular-nums">
                {charts.allCharts.length}
              </span>
            </button>
            {charts.categories.map(cat => {
              const count = charts.groupedCharts.find(g => g.category === cat)?.charts.length ?? 0;
              return (
                <button
                  key={cat}
                  onClick={() => charts.setActiveCategory(cat)}
                  className={`tab-link ${charts.activeCategory === cat ? 'active' : ''}`}
                >
                  {cat}
                  <span className="ml-1.5 text-[9px] text-muted-foreground/30 font-mono tabular-nums">
                    {count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Search */}
          <div className="relative shrink-0">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground/30 pointer-events-none" />
            <input
              type="text"
              value={charts.searchQuery}
              onChange={(e) => charts.setSearchQuery(e.target.value)}
              placeholder="Filter..."
              aria-label="Filter charts"
              className="w-24 focus:w-40 transition-all pl-7 pr-2 py-1 text-[11px] font-medium bg-transparent border border-border/30 rounded-[var(--radius)] text-foreground placeholder:text-muted-foreground/25 focus:outline-none focus:border-primary/30 focus:bg-primary/[0.02]"
            />
          </div>

          <div className="w-px h-4 bg-border/20 mx-0.5" />

          {/* Actions */}
          {perms.canRefreshAll && (
            <button
              onClick={actions.refreshAll}
              disabled={actions.isRefreshing}
              className="btn-icon w-6 h-6"
              title="Refresh all charts"
            >
              <RefreshCw className={`w-3 h-3 ${actions.isRefreshing ? 'animate-spin' : ''}`} />
            </button>
          )}
          {perms.isOwner && (
            <>
              <button
                onClick={actions.exportPDF}
                disabled={actions.exporting}
                className="btn-icon w-6 h-6"
                title="Export PDF"
              >
                <FileText className={`w-3 h-3 ${actions.exporting ? 'animate-pulse' : ''}`} />
              </button>
              <button
                onClick={actions.exportHTML}
                disabled={actions.exportingHtml}
                className="btn-icon w-6 h-6 text-rose-400/60 hover:text-rose-400 hover:bg-rose-500/[0.08]"
                title="Export HTML"
              >
                <FileCode className={`w-3 h-3 ${actions.exportingHtml ? 'animate-pulse' : ''}`} />
              </button>
            </>
          )}

          <div className="w-px h-4 bg-border/20 mx-0.5" />

          <button
            onClick={() => router.push('/?new=true')}
            className="btn-icon w-6 h-6"
            title="New chart"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* ── Chart Gallery ── */}
      <div className="overflow-y-auto flex-1 min-h-0">
        <div className="p-3 sm:p-4 lg:p-5">
          {hasCharts ? (
            displayGroups.map((group, gi) => {
              if (group.charts.length === 0) return null;
              return (
                <div key={group.category} className={gi > 0 ? 'mt-8' : ''}>
                  {charts.activeCategory === 'all' && (
                    <div className="flex items-center gap-3 mb-3 px-0.5">
                      <span className="stat-label text-[9px]">
                        {group.category}
                      </span>
                      <span className="text-[9px] font-mono text-muted-foreground/20 tabular-nums">
                        {group.charts.length}
                      </span>
                      <div className="flex-1 h-px bg-border/10" />
                    </div>
                  )}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                    {group.charts.map((chart, ci) => (
                      <motion.div
                        key={chart.id}
                        id={`chart-anchor-${chart.id}`}
                        initial={ci < 12 ? { opacity: 0, y: 8 } : false}
                        animate={{ opacity: 1, y: 0 }}
                        transition={ci < 12 ? { duration: 0.2, delay: ci * 0.025 } : { duration: 0 }}
                        style={{
                          contentVisibility: 'auto',
                          containIntrinsicSize: '0 248px',
                        }}
                      >
                        <ChartErrorBoundary>
                          <ChartTile
                            chart={chart}
                            canEdit={perms.canEditChart(chart)}
                            canRefresh={perms.canRefreshChart(chart)}
                            canDelete={perms.canDeleteChart(chart)}
                            canManageVisibility={perms.canManageVisibility}
                            onToggleVisibility={handleToggleVisibility}
                            onRefresh={handleRefreshChart}
                            onCopy={actions.copyChart}
                            onDelete={handleDeleteChart}
                            isRefreshing={!!actions.refreshingChartIds[chart.id]}
                            copySignal={actions.copySignals[chart.id] || 0}
                            onOpenSpotlight={openChart}
                            isFavorite={charts.favorites.has(chart.id)}
                            onToggleFavorite={charts.toggleFavorite}
                          />
                        </ChartErrorBoundary>
                      </motion.div>
                    ))}
                  </div>
                </div>
              );
            })
          ) : (
            <div className="flex flex-col items-center justify-center py-32 text-muted-foreground/30">
              <Layers className="w-10 h-10 mb-3 stroke-[1.2]" />
              <span className="text-sm font-medium">No charts found</span>
              {charts.searchQuery && (
                <button
                  onClick={() => charts.setSearchQuery('')}
                  className="mt-3 text-[11px] text-primary hover:underline"
                >
                  Clear filter
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Save Order Bar ── */}
      <AnimatePresence>
        {perms.canReorder && charts.isOrderDirty && (
          <SaveOrderBar
            onReset={charts.resetOrder}
            onSave={() => actions.saveOrder(charts.allCharts)}
            isSaving={actions.isReorderSaving}
          />
        )}
      </AnimatePresence>

      {/* ── Delete Confirmation Modal ── */}
      <AnimatePresence>
        {actions.deleteTarget && (
          <motion.div
            className="fixed inset-0 z-[220] flex items-center justify-center bg-black/50 backdrop-blur-sm px-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => actions.setDeleteTarget(null)}
            role="dialog"
            aria-modal="true"
          >
            <DeleteConfirmModal
              target={actions.deleteTarget}
              onCancel={() => actions.setDeleteTarget(null)}
              onConfirm={actions.confirmDelete}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
