'use client';

import React from 'react';
import {
  Plus, Search, Loader2, RotateCcw, Trash2,
  CheckCircle2, PanelLeftClose, FileDown, Filter,
  Database, X,
} from 'lucide-react';
import { motion, AnimatePresence, Reorder } from 'framer-motion';
import type { ChartEditorState } from '@/hooks/useChartEditor';

interface SidebarPanelProps {
  state: ChartEditorState;
}

export default function SidebarPanel({ state }: SidebarPanelProps) {
  const {
    activeTab,
    libraryOpen,
    setLibraryOpen,
    orderedCharts,
    setOrderedCharts,
    filteredCharts,
    searchQuery,
    setSearchQuery,
    currentChartId,
    canCreateChart,
    canRefreshAllCharts,
    canReorderLibrary,
    canToggleExport,
    canDeleteChart,
    isFiltering,
    refreshingAll,
    refreshProgress,
    pdfCount,
    exporting,
    loadChart,
    clearEditor,
    handleRefreshAll,
    handleExportPDF,
    toggleExportPdf,
    setDeleteConfirm,
    editorFontSize,
    setEditorFontSize,
    editorFontFamily,
    setEditorFontFamily,
  } = state;

  return (
    <aside className={`
      ${libraryOpen ? 'w-72' : 'w-0'} shrink-0 flex flex-col border-r border-border/30 bg-card transition-all duration-300 overflow-hidden relative z-10
    `}>
      {/* Sidebar Header */}
      <div className="h-10 shrink-0 flex items-center justify-between px-2.5 border-b border-border/30">
        <div className="flex items-center gap-0.5">
          {activeTab === 'library' && (
            <>
              <button
                onClick={clearEditor}
                disabled={!canCreateChart}
                className="btn-icon"
                title="New Analysis"
                aria-label="New Analysis"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
              {canRefreshAllCharts && (
                <button
                  onClick={handleRefreshAll}
                  disabled={refreshingAll}
                  className={`btn-icon ${refreshingAll ? 'text-primary bg-primary/10' : ''}`}
                  title="Refresh all data"
                >
                  {refreshingAll ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />}
                </button>
              )}
            </>
          )}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.06em] text-foreground/60">
            {activeTab === 'library' ? 'Library' : activeTab === 'data' ? 'Data' : 'Settings'}
          </span>
          {activeTab === 'library' && (
            <span className="text-[9px] tabular-nums px-1.5 py-0.5 rounded-[var(--radius)] text-muted-foreground/60 font-mono border border-border/40 bg-foreground/[0.03]">
              {orderedCharts.length}
            </span>
          )}
        </div>

        <button
          onClick={() => setLibraryOpen(false)}
          className="btn-icon lg:hidden"
          title="Close sidebar"
          aria-label="Close sidebar"
        >
          <PanelLeftClose className="w-3.5 h-3.5" />
        </button>
      </div>

      {activeTab === 'library' && (
        <>
          {/* Refresh All Progress Bar */}
          <AnimatePresence>
            {canRefreshAllCharts && refreshingAll && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="px-3 py-2 overflow-hidden border-b border-border/30"
              >
                <div className="border border-border/30 rounded-[var(--radius)] p-2">
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-[9px] font-mono text-muted-foreground/60 truncate max-w-[150px]">
                      {refreshProgress.name}
                    </span>
                    <span className="stat-label">
                      {Math.round((refreshProgress.current / refreshProgress.total) * 100)}%
                    </span>
                  </div>
                  <div className="h-0.5 w-full bg-primary/[0.08] rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-primary/50"
                      initial={{ width: 0 }}
                      animate={{ width: `${(refreshProgress.current / refreshProgress.total) * 100}%` }}
                      transition={{ duration: 0.3 }}
                    />
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Search */}
          <div className="px-2.5 py-2 border-b border-border/30">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground/30 pointer-events-none" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search..."
                className="w-full pl-7 pr-7 py-1.5 bg-background border border-border/40 rounded-[var(--radius)] text-[11px] text-foreground placeholder:text-muted-foreground/30 focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/20 transition-all"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 flex items-center justify-center rounded-full hover:bg-primary/10 text-muted-foreground/40 transition-colors"
                >
                  <X className="w-2.5 h-2.5" />
                </button>
              )}
            </div>
          </div>

          {/* Chart list */}
          <div className="flex-grow overflow-y-auto px-1.5 py-1.5">
            <Reorder.Group
              axis="y"
              values={filteredCharts}
              onReorder={(newItems) => {
                if (!isFiltering && canReorderLibrary) {
                  setOrderedCharts(newItems);
                }
              }}
              className="space-y-px"
            >
              {filteredCharts.map((chart: any, idx: number) => (
                <Reorder.Item
                  key={chart.id}
                  value={chart}
                  dragListener={canReorderLibrary && !isFiltering}
                  onClick={() => void loadChart(chart)}
                  className={`w-full group relative flex items-center gap-2 px-2 py-1.5 rounded-[var(--radius)] cursor-pointer transition-all duration-150 ${
                    currentChartId === chart.id
                      ? 'bg-primary/[0.08] border border-primary/15 text-foreground'
                      : 'border border-transparent text-muted-foreground hover:bg-foreground/[0.03] hover:border-border/20 hover:text-foreground'
                  }`}
                >
                  {/* Drag handle — only visible when reorder enabled */}
                  {canReorderLibrary && !isFiltering && (
                    <span className="shrink-0 text-muted-foreground/15 group-hover:text-muted-foreground/35 transition-colors cursor-grab active:cursor-grabbing">
                      <Database className="w-3 h-3" />
                    </span>
                  )}

                  {/* Index Number */}
                  {(!canReorderLibrary || isFiltering) && (
                    <span className="text-[10px] font-mono tabular-nums text-muted-foreground/30 shrink-0 w-4 text-right">
                      {idx + 1}
                    </span>
                  )}

                  {/* Content */}
                  <div className="flex-1 min-w-0 flex flex-col items-start text-left">
                    <span className="text-[11.5px] font-medium leading-snug truncate w-full">
                      {chart.name || 'Untitled Analysis'}
                    </span>
                    {chart.category && (
                      <span className="text-[9px] font-mono text-muted-foreground/35 truncate w-full">
                        {chart.category}
                      </span>
                    )}
                  </div>

                  {/* Actions on hover */}
                  <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                    {canToggleExport && (
                      <button
                        onClick={(e) => { e.stopPropagation(); toggleExportPdf(chart.id, !chart.public); }}
                        className={`w-4 h-4 rounded-sm border flex items-center justify-center transition-all ${
                          chart.public
                            ? 'bg-success/80 border-success/50'
                            : 'border-border/50 hover:border-primary/40'
                        }`}
                        title={chart.public ? "Included in PDF" : "Excluded from PDF"}
                      >
                        {chart.public && <CheckCircle2 className="w-2.5 h-2.5 text-white" />}
                      </button>
                    )}
                    {canDeleteChart(chart) && (
                      <button
                        onClick={(e) => { e.stopPropagation(); setDeleteConfirm(chart.id); }}
                        className="w-5 h-5 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/40 hover:text-destructive hover:bg-destructive/10 transition-all"
                        title="Delete Analysis"
                        aria-label="Delete Analysis"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    )}
                  </div>

                  {currentChartId === chart.id && (
                    <motion.div layoutId="sidebar-active" className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-3.5 bg-primary/50 rounded-r-full" />
                  )}
                </Reorder.Item>
              ))}
            </Reorder.Group>
            {filteredCharts.length === 0 && (
              <div className="py-8 px-4 text-center">
                <Filter className="w-3.5 h-3.5 text-muted-foreground/20 mx-auto mb-2" />
                <p className="stat-label">No matches</p>
              </div>
            )}
          </div>

          <div className="px-2.5 py-2 border-t border-border/30">
            <button
              onClick={handleExportPDF}
              disabled={exporting || pdfCount === 0}
              className="w-full btn-toolbar justify-between h-8 px-3 disabled:opacity-30"
            >
              <div className="flex items-center gap-1.5">
                <FileDown className="w-3 h-3" />
                <span>Generate Report</span>
              </div>
              <span className="stat-label">{pdfCount}</span>
            </button>
          </div>
        </>
      )}

      {activeTab === 'data' && (
        <div className="flex flex-col h-full">
          <div className="px-2.5 py-2 border-b border-border/30">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground/30 pointer-events-none" />
              <input
                type="text"
                placeholder="Search symbols..."
                className="w-full pl-7 pr-3 py-1.5 bg-background border border-border/40 rounded-[var(--radius)] text-[11px] text-foreground placeholder:text-muted-foreground/30 focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/20 transition-all"
              />
            </div>
          </div>
          <div className="flex-grow overflow-y-auto px-1.5 py-2">
            <div className="px-2 py-1 stat-label mb-1">Primary Streams</div>
            {['SPX_INDEX', 'NDX_INDEX', 'EUR_USD', 'GOLD_CMD', 'UST_10Y', 'BTC_USD'].map(symbol => (
              <div key={symbol} className="group flex items-center justify-between px-2 py-1.5 rounded-[var(--radius)] hover:bg-foreground/[0.03] border border-transparent hover:border-border/20 transition-all cursor-pointer">
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-success/60 shrink-0" />
                  <span className="text-[11px] font-mono text-muted-foreground/70 group-hover:text-foreground transition-colors">{symbol}</span>
                </div>
                <span className="stat-label text-success/60">Live</span>
              </div>
            ))}
            <div className="mt-3 mx-1 px-3 py-5 rounded-[var(--radius)] border border-dashed border-border/30 text-center">
              <Database className="w-3.5 h-3.5 text-muted-foreground/20 mx-auto mb-2" />
              <p className="text-[10px] text-muted-foreground/40 leading-relaxed">External API links via variables plugin.</p>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'settings' && (
        <div className="flex flex-col h-full">
          <div className="px-3 py-4 space-y-5">
            <div className="space-y-3">
              <p className="stat-label">Editor Preferences</p>

              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-[11px] text-muted-foreground/70">Font Size</span>
                  <span className="stat-label">{editorFontSize}px</span>
                </div>
                <input
                  type="range"
                  min="10"
                  max="20"
                  value={editorFontSize}
                  onChange={(e) => setEditorFontSize(parseInt(e.target.value))}
                  className="w-full h-0.5 rounded-full appearance-none cursor-pointer accent-primary"
                />
              </div>

              <div className="space-y-1.5">
                <span className="text-[11px] text-muted-foreground/70">Font Family</span>
                <div className="flex flex-col gap-1 mt-0.5">
                  {["'JetBrains Mono', monospace", "'Fira Code', monospace", "'Ubuntu Mono', monospace"].map(font => (
                    <button
                      key={font}
                      onClick={() => setEditorFontFamily(font)}
                      className={`px-3 py-1.5 text-left text-[11px] font-mono rounded-[var(--radius)] border transition-all ${
                        editorFontFamily === font
                          ? 'bg-primary/[0.08] border-primary/20 text-foreground'
                          : 'border-border/30 text-muted-foreground/60 hover:text-foreground hover:border-border/50 hover:bg-foreground/[0.02]'
                      }`}
                    >
                      {font.split(',')[0].replace(/'/g, '')}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-border/20">
              <button
                onClick={() => { if(confirm('Clear current analysis?')) clearEditor(); }}
                className="btn-danger w-full"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Clear Editor
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
