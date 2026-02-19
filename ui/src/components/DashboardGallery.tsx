'use client';

import React, { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { 
  TrendingUp, Search, Layers, X, 
  Plus, Edit2, CheckCircle2, GripVertical, Eye, EyeOff, Loader2, RotateCcw,
  MoreVertical, ArrowUp, ArrowDown, ArrowUpToLine,
  FileDown, Monitor, Check, Info, RefreshCw
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import { Reorder, motion, AnimatePresence, useDragControls } from 'framer-motion';
import { apiFetch, apiFetchJson } from '@/lib/api';
import Chart from './Chart';

interface ChartMeta {
  id: string;
  name: string;
  category: string | null;
  description: string | null;
  updated_at: string | null;
  rank: number;
  export_pdf?: boolean;
  code?: string;
  figure?: any; // Prefetched figure data
}
interface ChartCardProps {
  chart: ChartMeta;
  isAdmin: boolean;
  isReorderable: boolean;
  onTogglePdf: (id: string, status: boolean) => void;
  isSyncing?: boolean;
  onRankChange?: (id: string, newRank: number) => void;
  index: number;
  totalCharts: number;
  onOpenStudio?: (chartId: string | null) => void;
}
const ChartCard = React.memo(function ChartCard({ 
  chart, 
  isAdmin, 
  isReorderable, 
  onTogglePdf, 
  isSyncing,
  onRankChange,
  index,
  totalCharts,
  onOpenStudio
}: ChartCardProps) {
  // Viewport-based lazy rendering
  const cardRef = useRef<HTMLDivElement>(null);
  const [isInView, setIsInView] = useState(false);

  useEffect(() => {
    const el = cardRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setIsInView(true); observer.disconnect(); } },
      { rootMargin: '200px' } // pre-load 200px before entering viewport
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  const [localRank, setLocalRank] = useState(chart.rank + 1);

  // Sync with prop if it changes externally (important when list finally sorts)
  useEffect(() => {
    setLocalRank(chart.rank + 1);
  }, [chart.rank]);

  const isModified = localRank !== chart.rank + 1;

  const handleRankSubmit = () => {
    if (isModified) {
      onRankChange?.(chart.id, localRank - 1);
    }
  };

  const content = (
    <>
      {/* Card Header */}
      <div className="px-4 py-3 flex items-center justify-between border-b border-white/5 bg-white/[0.02] relative">
         <div className="flex items-center gap-3 min-w-0 z-10">
            {/* 1. Direct Rank Input (LEFTMOST) */}
            {isAdmin && isReorderable && (
              <div className={`flex items-center gap-1 px-2 py-0.5 rounded border text-[10px] font-mono shrink-0 transition-colors ${
                isModified ? 'bg-amber-500/20 border-amber-500/40' : 'bg-sky-500/10 border-sky-500/20'
              }`}>
                <input
                  type="number"
                  value={localRank}
                  onChange={(e) => setLocalRank(parseInt(e.target.value) || 1)}
                  onBlur={handleRankSubmit}
                  onKeyDown={(e) => e.key === 'Enter' && handleRankSubmit()}
                  className={`w-8 bg-transparent focus:outline-none text-center font-bold appearance-none [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none ${
                    isModified ? 'text-amber-400' : 'text-sky-400'
                  }`}
                />
                <span className="text-slate-600">/</span>
                <span className="text-slate-500">{totalCharts}</span>
              </div>
            )}

            {/* 2. Visibility Toggle */}
            {isAdmin && (
              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onTogglePdf(chart.id, !chart.export_pdf);
                }}
                className={`p-1 transition-all rounded hover:bg-white/5 shrink-0 ${chart.export_pdf ? 'text-emerald-400' : 'text-slate-600'}`}
                title={chart.export_pdf ? "Public (Live on Dashboard)" : "Private (Draft/Admin Only)"}
              >
                {chart.export_pdf ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
              </button>
            )}

            {/* 3. Interactive Name (Click to Edit) */}
            {isAdmin ? (
              <button
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); onOpenStudio?.(chart.id); }}
                className="group/name flex items-center gap-2 min-w-0 overflow-hidden"
                title="Edit in Studio"
              >
                <span className="text-[10px] font-mono text-sky-400 uppercase tracking-widest px-2 py-0.5 bg-sky-500/10 rounded border border-sky-500/20 group-hover/name:bg-sky-500/20 group-hover/name:text-sky-300 transition-all truncate">
                  {chart.name}
                </span>
              </button>
            ) : (
              <span className="text-[10px] font-mono text-sky-400 uppercase tracking-widest px-2 py-0.5 bg-sky-500/10 rounded border border-sky-500/10 truncate">
                {chart.name}
              </span>
            )}


         </div>

         <div className="flex items-center gap-3 shrink-0">
            {chart.description && (
              <div className="relative group/tip">
                <Info className="w-3.5 h-3.5 text-slate-600 hover:text-sky-400 transition-colors cursor-help" />
                <div className="absolute right-0 top-full mt-1 w-56 px-3 py-2 bg-slate-900 border border-white/10 rounded-lg text-[10px] text-slate-400 leading-relaxed opacity-0 invisible group-hover/tip:opacity-100 group-hover/tip:visible transition-all z-50 shadow-xl">
                  {chart.description}
                </div>
              </div>
            )}
            <div className="text-[9px] text-slate-600 font-mono hidden sm:flex items-center gap-3">
                {isSyncing && <Loader2 className="w-3 h-3 animate-spin text-indigo-500" />}
                {chart.updated_at ? new Date(chart.updated_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '---'}
            </div>
         </div>
      </div>


      <div ref={cardRef} className="flex flex-col">
        {/* Chart Area — only render Plotly when in viewport */}
        <div className="bg-slate-950/20 relative w-full p-4 h-[350px]">
          {isInView ? (
            <Chart id={chart.id} initialFigure={chart.figure} />
          ) : (
            <div className="flex items-center justify-center h-full w-full">
              <Loader2 className="w-6 h-6 text-sky-400/20 animate-spin" />
            </div>
          )}
        </div>
      </div>
    </>
  );

  const className = `glass-card overflow-hidden flex flex-col group transition-all duration-300 hover:border-sky-500/30 hover:shadow-sky-500/5 relative`;

  if (isReorderable) {
    return (
      <Reorder.Item
        value={chart}
        dragListener={false}
        className={className}
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.98 }}
        whileDrag={{
          scale: 1.05,
          boxShadow: '0 25px 40px -10px rgb(0 0 0 / 0.7), 0 10px 15px -5px rgb(0 0 0 / 0.5)',
          zIndex: 100
        }}
        transition={{
          type: 'spring',
          damping: 20,
          stiffness: 400,
          mass: 0.8
        }}
      >
        {content}
      </Reorder.Item>
    );
  }

  return (
    <div className={className}>
      {content}
    </div>
  );
});

interface DashboardGalleryProps {
  categories: string[];
  chartsByCategory: Record<string, ChartMeta[]>;
  onOpenStudio?: (chartId: string | null) => void;
}

export default function DashboardGallery({ categories, chartsByCategory, onOpenStudio }: DashboardGalleryProps) {
  const { user, token } = useAuth();
  const isAdmin = user?.is_admin;
  const queryClient = useQueryClient();

  // ⚡ Performance Optimized State
  const [localCharts, setLocalCharts] = useState<ChartMeta[]>([]);
  const [originalCharts, setOriginalCharts] = useState<ChartMeta[]>([]);
  const [activeCategory, setActiveCategory] = useState<string>('All Indicators');
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  const [mounted, setMounted] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Export state
  const [exporting, setExporting] = useState(false);
  const [exportStatus, setExportStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [exportingHtml, setExportingHtml] = useState(false);
  const [exportHtmlStatus, setExportHtmlStatus] = useState<'idle' | 'success' | 'error'>('idle');

  // ⏲️ Debounce Search Query
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);


  const isOrderDirty = useMemo(() => {
    if (localCharts.length !== originalCharts.length) return false;
    // Fast ID check
    return localCharts.some((c, i) => c.id !== originalCharts[i]?.id);
  }, [localCharts, originalCharts]);

  const handleRefreshAll = async () => {
    if (isRefreshing || localCharts.length === 0) return;
    setIsRefreshing(true);
    // Concurrent refresh with limit
    const refreshBatch = localCharts.slice(0, 5); 
    await Promise.allSettled(refreshBatch.map((chart: any) => 
      apiFetch('/api/custom/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: (chart as any).code || '' }),
      })
    ));
    setIsRefreshing(false);
    queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
  };

  const handleExportPDF = async () => {
    if (exporting) return;
    setExporting(true);
    setExportStatus('idle');
    try {
      const res = await fetch('/api/custom/pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ items: [] }),
      });
      if (!res.ok) throw new Error('PDF failed');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `InvestmentX_Report_${new Date().toISOString().slice(0, 10)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      setExportStatus('success');
      setTimeout(() => setExportStatus('idle'), 3000);
    } catch {
      setExportStatus('error');
      setTimeout(() => setExportStatus('idle'), 3000);
    } finally {
      setExporting(false);
    }
  };

  const handleExportHTML = async () => {
    if (exportingHtml) return;
    setExportingHtml(true);
    setExportHtmlStatus('idle');
    try {
      const res = await fetch('/api/custom/html', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ items: [] }),
      });
      if (!res.ok) throw new Error('HTML failed');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `InvestmentX_Portfolio_${new Date().toISOString().slice(0, 10)}.html`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      setExportHtmlStatus('success');
      setTimeout(() => setExportHtmlStatus('idle'), 3000);
    } catch {
      setExportHtmlStatus('error');
      setTimeout(() => setExportHtmlStatus('idle'), 3000);
    } finally {
      setExportingHtml(false);
    }
  };

  const allCategories = useMemo(() => ['All Indicators', ...(categories || [])], [categories]);

  // 🔄 Prop to Local State Sync
  useEffect(() => {
    const uniqueChartsMap = new Map<string, ChartMeta>();
    Object.values(chartsByCategory || {}).forEach(charts => {
      if (Array.isArray(charts)) {
        charts.forEach(c => uniqueChartsMap.set(c.id, c));
      }
    });
    
    const sorted = Array.from(uniqueChartsMap.values())
      .sort((a, b) => (a.rank ?? 0) - (b.rank ?? 0));
      
    setLocalCharts(sorted);
    setOriginalCharts([...sorted]);
  }, [chartsByCategory]);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (activeCategory === 'All Indicators') return;
    if (!allCategories.includes(activeCategory)) {
        setActiveCategory(allCategories[0]);
    }
  }, [allCategories, activeCategory]);

  // 🔍 Filter & Sort charts (Memoized)
  const allFilteredCharts = useMemo(() => {
    let result = [...localCharts];

    if (!isAdmin) {
      result = result.filter(c => c.export_pdf !== false);
    }

    if (activeCategory !== 'All Indicators') {
      result = result.filter(c => c.category === activeCategory);
    }

    if (debouncedSearch.trim()) {
      const q = debouncedSearch.toLowerCase();
      result = result.filter(c => 
        (c.name || '').toLowerCase().includes(q) || 
        (c.description?.toLowerCase().includes(q))
      );
    }
    
    return result;
  }, [localCharts, isAdmin, activeCategory, debouncedSearch]);

  // No pagination: render all charts at once
  const filteredCharts = allFilteredCharts;

  const isReorderEnabled = isAdmin && !searchQuery.trim() && activeCategory === 'All Indicators';

  // 🛠️ Stable Handlers
  const togglePdfMutation = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: boolean }) => {
      return apiFetchJson(`/api/custom/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ export_pdf: status })
      });
    },
    onMutate: async ({ id, status }) => {
      setLocalCharts(prev => prev.map(c => c.id === id ? { ...c, export_pdf: status } : c));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
    }
  });

  const reorderMutation = useMutation({
    mutationFn: async (items: ChartMeta[]) => {
      return apiFetchJson('/api/custom/reorder', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: items.map(c => ({ id: c.id })) })
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      setOriginalCharts([...localCharts]);
    }
  });

  const handleTogglePdf = React.useCallback((id: string, status: boolean) => {
    togglePdfMutation.mutate({ id, status });
  }, [togglePdfMutation]);

  const handleRankChange = React.useCallback((id: string, newRank: number) => {
      setLocalCharts(prev => {
          const oldIndex = prev.findIndex(c => c.id === id);
          if (oldIndex === -1) return prev;
          
          const newIndex = Math.max(0, Math.min(newRank, prev.length - 1));
          if (oldIndex === newIndex) return prev;
          
          const next = [...prev];
          const [item] = next.splice(oldIndex, 1);
          next.splice(newIndex, 0, item);
          
          return next.map((c, i) => ({ ...c, rank: i }));
      });
  }, []);

  const handleReorder = React.useCallback((newSubset: ChartMeta[]) => {
    if (!isReorderEnabled) return;
    const subsetIds = new Set(newSubset.map(c => c.id));
    let subsetIdx = 0;
    setLocalCharts(prev => prev.map(chart => 
      subsetIds.has(chart.id) ? newSubset[subsetIdx++] : chart
    ));
  }, [isReorderEnabled]);

  const handleSaveOrder = React.useCallback(() => {
    reorderMutation.mutate(localCharts);
  }, [localCharts, reorderMutation]);

  const handleResetOrder = React.useCallback(() => {
    setLocalCharts([...originalCharts]);
  }, [originalCharts]);

  if (!mounted) {
    return (
      <div className="min-h-[800px] flex flex-col items-center justify-center gap-4 text-slate-500 font-mono">
        <Loader2 className="w-8 h-8 animate-spin text-sky-500" />
        <span className="text-xs uppercase tracking-[0.2em] opacity-40">Initializing Research Engine</span>
      </div>
    );
  }

  return (
    <div className="space-y-8 min-h-[800px]">
      {/* 🧭 Filter & Search Command Bar */}
      <div className="flex flex-col lg:flex-row gap-6 items-center justify-between sticky top-14 z-40 px-6 py-3 glass-card bg-slate-900/60 backdrop-blur-2xl border-white/10 shadow-2xl">
        <div className="flex flex-wrap items-center gap-2 pb-2 lg:pb-0 w-full lg:w-[70%]">
          {!searchQuery && (
            <div className="flex flex-wrap gap-2">
              {allCategories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setActiveCategory(cat)}
                  className={`px-4 py-1.5 text-xs font-semibold rounded-full transition-all border ${
                    activeCategory === cat
                      ? 'bg-sky-500 border-sky-400 text-white shadow-lg shadow-sky-500/20'
                      : 'bg-white/5 border-white/5 text-slate-400 hover:bg-white/10 hover:text-slate-200'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          )}
          {searchQuery && (
            <div className="flex items-center gap-2 text-sky-400 text-xs font-semibold px-4 py-1.5 bg-sky-500/10 rounded-full border border-sky-500/20">
              <Layers className="w-4 h-4" />
              Intelligence Search: Global Scope ({filteredCharts.length} matches)
            </div>
          )}
        </div>

        <div className="flex items-center gap-3 w-full lg:w-auto shrink-0">
          {isAdmin && isReorderEnabled && isOrderDirty && (
            <div className="flex items-center gap-2 pr-4 border-r border-white/10 mr-2 animate-in fade-in slide-in-from-right-4 duration-500">
               <button
                 onClick={handleSaveOrder}
                 disabled={reorderMutation.isPending}
                 className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-lg bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/20 active:scale-95"
               >
                 {reorderMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                 SAVE ORDER
               </button>
               <button
                 onClick={handleResetOrder}
                 className="p-2 text-slate-500 hover:text-rose-400 transition-colors active:rotate-180 duration-500"
                 title="Discard Changes"
               >
                 <RotateCcw className="w-4 h-4" />
               </button>
            </div>
          )}

          <div className="relative flex-grow lg:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Filter by keyword..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-10 py-2.5 bg-black/40 border border-white/10 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/50 transition-all font-light"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-white/10 rounded-md transition-colors"
                type="button"
              >
                <X className="w-3 h-3 text-slate-400" />
              </button>
            )}
          </div>

          {/* Refresh All & Export Buttons */}
          <button
            onClick={handleRefreshAll}
            disabled={isRefreshing}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-[10px] font-mono font-bold uppercase tracking-wider transition-all disabled:opacity-30 ${
              isRefreshing ? 'text-sky-400 bg-sky-500/10 border-sky-500/20' : 'text-slate-400 bg-black/40 border-white/5 hover:text-white hover:bg-white/10'
            }`}
            title="Refresh All Charts"
            type="button"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
          <div className="flex gap-1 p-1 bg-black/40 border border-white/5 rounded-xl">
            <button
              onClick={handleExportPDF}
              disabled={exporting || exportingHtml}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[10px] font-mono font-bold uppercase tracking-wider transition-all disabled:opacity-30 ${
                exportStatus === 'success' ? 'text-emerald-400 bg-emerald-500/10'
                : exportStatus === 'error' ? 'text-rose-400 bg-rose-500/10'
                : 'text-slate-400 hover:text-white hover:bg-white/10'
              }`}
              title="Export PDF Report"
              type="button"
            >
              {exporting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : exportStatus === 'success' ? <Check className="w-3.5 h-3.5" /> : <FileDown className="w-3.5 h-3.5" />}
              PDF
            </button>
            <button
              onClick={handleExportHTML}
              disabled={exporting || exportingHtml}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[10px] font-mono font-bold uppercase tracking-wider transition-all disabled:opacity-30 ${
                exportHtmlStatus === 'success' ? 'text-emerald-400 bg-emerald-500/10'
                : exportHtmlStatus === 'error' ? 'text-rose-400 bg-rose-500/10'
                : 'text-slate-400 hover:text-white hover:bg-white/10'
              }`}
              title="Export Interactive HTML"
              type="button"
            >
              {exportingHtml ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : exportHtmlStatus === 'success' ? <Check className="w-3.5 h-3.5" /> : <Monitor className="w-3.5 h-3.5" />}
              HTML
            </button>
          </div>

          {isAdmin && (
            <button
              onClick={() => onOpenStudio?.(null)}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-indigo-600/20 transition-all ml-1 active:scale-95"
            >
              <Plus className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">CREATE</span>
            </button>
          )}
        </div>
      </div>

      {/* 📊 Results Header */}
      <div className="flex items-center justify-between px-2">
        <h2 className="text-2xl font-semibold text-slate-200 flex items-center gap-3 tracking-tight">
          {debouncedSearch ? (
            <>Search Results <span className="text-sky-500/60 font-mono text-lg">[{filteredCharts.length}]</span></>
          ) : (
            <>
              <TrendingUp className="w-6 h-6 text-sky-400" />
              {activeCategory}
              <span className="text-xs font-mono font-normal text-slate-500 mt-1.5 uppercase tracking-widest">
                / {filteredCharts.length} Indicators
              </span>
            </>
          )}
        </h2>
        {isReorderEnabled && (
          <div className="flex items-center gap-2 px-3 py-1 bg-sky-500/10 border border-sky-500/20 rounded-lg animate-pulse">
             <span className="text-[10px] font-bold text-sky-400 uppercase tracking-tighter">Live Ranking Console</span>
          </div>
        )}
      </div>

      {/* 🖼️ Grid/List Display with Virtualization Support */}
      {isReorderEnabled ? (
        <Reorder.Group 
          values={filteredCharts}
          onReorder={handleReorder}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8"
        >
          {filteredCharts.map((chart, idx) => (
            <ChartCard
              key={chart.id}
              chart={chart}
              isAdmin={isAdmin || false}

              isReorderable={true}
              onTogglePdf={handleTogglePdf}
              isSyncing={reorderMutation.isPending}
              onRankChange={handleRankChange}
              index={idx}
              totalCharts={filteredCharts.length}
              onOpenStudio={onOpenStudio}
            />
          ))}
        </Reorder.Group>
      ) : (
        <div 
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8"
        >
          {filteredCharts.map((chart, idx) => (
            <ChartCard
              key={chart.id}
              chart={chart}
              isAdmin={isAdmin || false}

              isReorderable={false}
              onTogglePdf={handleTogglePdf}
              onRankChange={handleRankChange}
              index={idx}
              totalCharts={filteredCharts.length}
              onOpenStudio={onOpenStudio}
            />
          ))}
        </div>
      )}

      {/* 📭 Empty State */}
      {filteredCharts.length === 0 && (
        <div className="py-32 text-center glass-card border-dashed border-white/10 bg-transparent animate-in zoom-in-95 duration-500">
          <Layers className="w-12 h-12 text-slate-700 mx-auto mb-4 opacity-20" />
          <h3 className="text-xl font-medium text-slate-500">No matching indicators</h3>
          <p className="text-slate-600 mt-2 text-sm font-light">Try expanding your search parameters.</p>
        </div>
      )}
    </div>
  );
}
