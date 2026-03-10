'use client';

import { useRouter } from 'next/navigation';
import {
  LayoutGrid,
  Rows2,
  RefreshCw,
  FileText,
  FileCode,
  Plus,
  Search,
} from 'lucide-react';
import type { DashboardState } from '@/hooks/useDashboardState';

interface DashboardToolbarProps {
  state: DashboardState;
}

export default function DashboardToolbar({ state }: DashboardToolbarProps) {
  const router = useRouter();
  const {
    // Filtering
    searchQuery,
    setSearchQuery,
    activeCategory,
    setActiveCategory,
    allFilteredCharts,
    groupedCharts,
    categories,

    // View mode
    viewMode,
    setViewMode,

    // Focus view
    focusPanelCount,
    setFocusPanelCount,

    // Permissions
    isOwner,
    canRefreshAllCharts,

    // Handlers
    handleRefreshAll,
    handleExportPDF,
    handleExportHTML,

    // Export / mutation state
    isRefreshing,
    exporting,
    exportingHtml,
  } = state;

  return (
    <div className="px-4 sm:px-5 lg:px-6 border-b border-border/25 shrink-0 h-10">
      <div className="flex items-center gap-2 -mb-px h-full">
        {/* Category tabs */}
        <div className="flex gap-0.5 overflow-x-auto no-scrollbar flex-1 min-w-0">
          <button
            onClick={() => setActiveCategory('all')}
            className={`tab-link ${activeCategory === 'all' ? 'active' : ''}`}
          >
            All
            <span className="ml-1 text-[9px] text-muted-foreground/40 font-mono">
              {allFilteredCharts.length}
            </span>
          </button>
          {categories.map(cat => {
            const count = groupedCharts.find(g => g.category === cat)?.charts.length ?? 0;
            return (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`tab-link ${activeCategory === cat ? 'active' : ''}`}
              >
                {cat}
                <span className="ml-1 text-[9px] text-muted-foreground/40 font-mono">
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Search */}
        <div className="relative shrink-0">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground/35 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search..."
            aria-label="Search charts"
            className="w-28 focus:w-44 transition-all pl-7 pr-2 py-1.5 text-[11px] font-medium bg-transparent border border-border/40 rounded-md text-foreground placeholder:text-muted-foreground/30 focus:outline-none focus:border-primary/40"
          />
        </div>

        <div className="w-px h-3 bg-border/30" />

        {/* View mode buttons */}
        <button
          onClick={() => setViewMode('gallery')}
          className={`w-5 h-5 rounded flex items-center justify-center transition-colors ${
            viewMode === 'gallery'
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:text-foreground hover:bg-primary/10'
          }`}
          title="Gallery mode"
          aria-label="Gallery mode"
          aria-pressed={viewMode === 'gallery'}
        >
          <LayoutGrid className="w-3 h-3" />
        </button>
        <button
          onClick={() => setViewMode('focus')}
          className={`w-5 h-5 rounded flex items-center justify-center transition-colors ${
            viewMode === 'focus'
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:text-foreground hover:bg-primary/10'
          }`}
          title="Focus mode"
          aria-label="Focus mode"
          aria-pressed={viewMode === 'focus'}
        >
          <Rows2 className="w-3 h-3" />
        </button>

        {/* Focus panel count */}
        {viewMode === 'focus' && (
          <>
            <div className="w-px h-3 bg-border/40 mx-0.5" />
            {([1, 2, 3, 4] as const).map(n => (
              <button
                key={n}
                onClick={() => setFocusPanelCount(n)}
                className={`w-5 h-5 rounded text-[10px] font-mono transition-colors ${
                  focusPanelCount === n
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground hover:bg-primary/10'
                }`}
                title={`${n} panel${n > 1 ? 's' : ''}`}
              >
                {n}
              </button>
            ))}
          </>
        )}

        {(canRefreshAllCharts || isOwner) && <div className="w-px h-3 bg-border/40 mx-0.5" />}

        {/* Actions */}
        {canRefreshAllCharts && (
          <button
            onClick={handleRefreshAll}
            disabled={isRefreshing}
            className="w-5 h-5 rounded flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-primary/10 disabled:opacity-40 transition-colors"
            title="Refresh all charts"
            aria-label="Refresh all charts"
          >
            <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
        )}
        {isOwner && (
          <>
            <button
              onClick={handleExportPDF}
              disabled={exporting}
              className="w-5 h-5 rounded flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-primary/10 disabled:opacity-40 transition-colors"
              title="Export PDF"
              aria-label="Export PDF"
            >
              <FileText className={`w-3 h-3 ${exporting ? 'animate-pulse' : ''}`} />
            </button>
            <button
              onClick={handleExportHTML}
              disabled={exportingHtml}
              className="w-5 h-5 rounded flex items-center justify-center text-rose-400 hover:text-rose-300 hover:bg-rose-500/[0.08] disabled:opacity-40 transition-colors"
              title="Export HTML"
              aria-label="Export HTML"
            >
              <FileCode className={`w-3 h-3 ${exportingHtml ? 'animate-pulse' : ''}`} />
            </button>
          </>
        )}

        <div className="w-px h-3 bg-border/40 mx-0.5" />

        <button
          onClick={() => router.push('/studio?new=true')}
          className="w-5 h-5 rounded flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-primary/10 transition-colors"
          title="New chart"
          aria-label="New chart"
        >
          <Plus className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}
