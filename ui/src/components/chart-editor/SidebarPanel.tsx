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
      ${libraryOpen ? 'w-72' : 'w-0'} shrink-0 flex flex-col border-r border-border/60 bg-background transition-all duration-300 overflow-hidden relative z-10
    `}>
      {/* Sidebar Header */}
      <div className="h-11 shrink-0 flex items-center justify-between px-3 border-b border-border/60">
        <div className="flex items-center gap-1.5">
          {activeTab === 'library' && (
            <>
              <button
                onClick={clearEditor}
                disabled={!canCreateChart}
                className="p-1.5 rounded-md transition-all text-muted-foreground/40 hover:text-muted-foreground hover:bg-foreground/[0.06] disabled:opacity-40 disabled:cursor-not-allowed"
                title="New Analysis"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
              {canRefreshAllCharts && (
                <button
                  onClick={handleRefreshAll}
                  disabled={refreshingAll}
                  className={`p-1.5 rounded-md transition-all ${
                    refreshingAll
                      ? 'text-foreground bg-foreground/[0.08]'
                      : 'text-muted-foreground/40 hover:text-muted-foreground hover:bg-foreground/[0.06]'
                  }`}
                  title="Refresh all data"
                >
                  {refreshingAll ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />}
                </button>
              )}
            </>
          )}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] font-medium text-foreground/80">
            {activeTab === 'library' ? 'Library' : activeTab === 'data' ? 'Data' : 'Settings'}
          </span>
          {activeTab === 'library' && (
            <span className="text-[10px] tabular-nums px-1.5 py-0.5 rounded text-muted-foreground font-mono border border-border/50">
              {orderedCharts.length}
            </span>
          )}
        </div>

        <button
          onClick={() => setLibraryOpen(false)}
          className="p-1.5 rounded-lg hover:bg-accent/20 text-muted-foreground hover:text-foreground transition-colors lg:hidden"
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
                className="px-3 py-2 overflow-hidden border-b border-border/60"
              >
                <div className="border border-border/50 rounded-lg p-2">
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-[9px] font-mono text-muted-foreground/80 truncate max-w-[150px]">
                      {refreshProgress.name}
                    </span>
                    <span className="text-[9px] font-mono text-muted-foreground/60">
                      {Math.round((refreshProgress.current / refreshProgress.total) * 100)}%
                    </span>
                  </div>
                  <div className="h-1 w-full bg-foreground/5 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-foreground/40"
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
          <div className="px-3 py-2 border-b border-border/60">
            <div className="relative group">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground/50 transition-colors" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search..."
                className="w-full pl-7 pr-3 py-1.5 bg-transparent border border-border/50 rounded-md text-[11px] text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-border transition-all"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-1.5 top-1/2 -translate-y-1/2 p-0.5 rounded-full hover:bg-accent/30 text-muted-foreground/60"
                >
                  <X className="w-2 h-2" />
                </button>
              )}
            </div>
          </div>

          {/* Chart list */}
          <div className="flex-grow overflow-y-auto custom-scrollbar px-1.5 py-2 space-y-px">
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
                  className={`w-full group relative flex items-center gap-2 px-2.5 py-2 rounded-lg cursor-pointer transition-all duration-150 ${
                    currentChartId === chart.id
                      ? 'bg-foreground/[0.07] text-foreground'
                      : 'text-muted-foreground hover:bg-foreground/[0.04] hover:text-foreground'
                  }`}
                >
                  {/* Index Number */}
                  <span className="text-[10px] font-mono tabular-nums text-muted-foreground/40 shrink-0 w-4 text-right">
                    {idx + 1}
                  </span>

                  {/* Content */}
                  <div className="flex-1 min-w-0 flex flex-col items-start text-left">
                    <span className="text-[12px] font-medium leading-tight truncate w-full">
                      {chart.name || 'Untitled Analysis'}
                    </span>
                    <div className="flex items-center gap-1">
                      <span className="text-[10px] text-muted-foreground/50">
                        {chart.category || 'Analysis'}
                      </span>
                    </div>
                  </div>

                  {/* Actions on hover */}
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {canToggleExport && (
                      <button
                        onClick={(e) => { e.stopPropagation(); toggleExportPdf(chart.id, !chart.public); }}
                        className={`w-2.5 h-2.5 rounded-sm border flex items-center justify-center transition-all ${chart.public ? 'bg-emerald-500 border-emerald-400' : 'border-muted-foreground/30 hover:border-muted-foreground/50'}`}
                        title={chart.public ? "Included in PDF" : "Excluded from PDF"}
                      >
                        {chart.public && <CheckCircle2 className="w-2 h-2 text-white" />}
                      </button>
                    )}
                    {canDeleteChart(chart) && (
                      <button
                        onClick={(e) => { e.stopPropagation(); setDeleteConfirm(chart.id); }}
                        className="p-0.5 text-muted-foreground/60 hover:text-rose-400 transition-all"
                        title="Delete Analysis"
                      >
                        <Trash2 className="w-2.5 h-2.5" />
                      </button>
                    )}
                  </div>

                  {currentChartId === chart.id && (
                    <motion.div layoutId="sidebar-active" className="absolute left-0 w-0.5 h-4 bg-foreground/30 rounded-r-full" />
                  )}
                </Reorder.Item>
              ))}
            </Reorder.Group>
            {filteredCharts.length === 0 && (
              <div className="py-6 px-4 text-center">
                <Filter className="w-4 h-4 text-muted-foreground/20 mx-auto mb-1" />
                <p className="text-[8px] text-muted-foreground font-medium tracking-tight">NO MATCHES</p>
              </div>
            )}
          </div>

          <div className="p-2 border-t border-border/60">
            <button
              onClick={handleExportPDF}
              disabled={exporting || pdfCount === 0}
              className="w-full flex items-center justify-between px-3 py-2 border border-border/50 rounded-lg text-[11px] font-medium text-muted-foreground hover:text-foreground hover:border-border transition-all disabled:opacity-30"
            >
              <div className="flex items-center gap-2">
                <FileDown className="w-3 h-3" />
                Generate Report
              </div>
              <span className="text-muted-foreground/50 font-mono tabular-nums text-[10px]">{pdfCount}</span>
            </button>
          </div>
        </>
      )}

      {activeTab === 'data' && (
        <div className="flex flex-col h-full bg-background">
          <div className="p-3 border-b border-border/60">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground/40" />
              <input
                type="text"
                placeholder="Search symbols..."
                className="w-full pl-7 pr-3 py-1.5 bg-transparent border border-border/50 rounded-md text-[11px] text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-border transition-all"
              />
            </div>
          </div>
          <div className="flex-grow overflow-y-auto px-2 py-2 space-y-px">
            <div className="px-2.5 py-1 text-[10px] font-medium text-muted-foreground/50 uppercase tracking-wider mb-1">Primary Streams</div>
            {['SPX_INDEX', 'NDX_INDEX', 'EUR_USD', 'GOLD_CMD', 'UST_10Y', 'BTC_USD'].map(symbol => (
              <div key={symbol} className="group flex items-center justify-between px-2.5 py-2 rounded-lg hover:bg-foreground/[0.04] transition-colors cursor-pointer">
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/70" />
                  <span className="text-[11px] font-mono text-muted-foreground group-hover:text-foreground transition-colors">{symbol}</span>
                </div>
                <span className="text-[10px] text-muted-foreground/40 font-mono">Live</span>
              </div>
            ))}
            <div className="mt-4 mx-2 px-3 py-5 rounded-lg border border-dashed border-border/50 text-center">
              <Database className="w-4 h-4 text-muted-foreground/20 mx-auto mb-2" />
              <p className="text-[10px] text-muted-foreground/50">External API links via variables plugin.</p>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'settings' && (
        <div className="flex flex-col h-full bg-background">
          <div className="px-4 py-6 space-y-6">
            <div className="space-y-4">
              <h3 className="text-[11px] font-medium text-muted-foreground">Editor Preferences</h3>

              <div className="space-y-2">
                <div className="flex justify-between items-center text-[11px] text-muted-foreground">
                  <span>Font Size</span>
                  <span className="tabular-nums">{editorFontSize}px</span>
                </div>
                <input
                  type="range"
                  min="10"
                  max="20"
                  value={editorFontSize}
                  onChange={(e) => setEditorFontSize(parseInt(e.target.value))}
                  className="w-full h-1 rounded-full appearance-none cursor-pointer accent-foreground"
                />
              </div>

              <div className="space-y-2">
                <span className="text-[11px] text-muted-foreground">Font Family</span>
                <div className="flex flex-col gap-1 mt-1">
                  {["'JetBrains Mono', monospace", "'Fira Code', monospace", "'Ubuntu Mono', monospace"].map(font => (
                    <button
                      key={font}
                      onClick={() => setEditorFontFamily(font)}
                      className={`px-3 py-2 text-left text-[11px] font-mono rounded-lg border transition-all ${editorFontFamily === font ? 'bg-foreground/[0.07] border-border/60 text-foreground' : 'border-border/40 text-muted-foreground hover:text-foreground hover:border-border/60'}`}
                    >
                      {font.split(',')[0].replace(/'/g, '')}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-border/60">
              <button
                onClick={() => { if(confirm('Clear current analysis?')) clearEditor(); }}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 border border-border/50 rounded-lg text-muted-foreground text-[11px] hover:text-rose-500 hover:border-rose-500/30 transition-all"
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
