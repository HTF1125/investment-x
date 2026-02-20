'use client';

import React, { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { 
  TrendingUp, Search, Layers, X, 
  Plus, Edit2, CheckCircle2, GripVertical, Eye, EyeOff, Loader2, RotateCcw,
  MoreVertical, ArrowUp, ArrowDown, ArrowUpToLine,
  FileDown, Monitor, Check, Info, RefreshCw, LayoutGrid, List as ListIcon,
  ChevronDown
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import { Reorder, motion, AnimatePresence, useDragControls, DragControls } from 'framer-motion';
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
  dragControls?: DragControls;
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
  onOpenStudio,
  dragControls
}: ChartCardProps) {
  // Viewport-based lazy rendering
  const cardRef = useRef<HTMLDivElement>(null);
  const [isInView, setIsInView] = useState(false);

  useEffect(() => {
    const el = cardRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => { 
        if (entry.isIntersecting) { 
          // Add a small randomized delay to prevent CPU spikes when multiple cards intersect
          const delay = Math.random() * 200;
          setTimeout(() => setIsInView(true), delay);
          observer.disconnect(); 
        } 
      },
      { rootMargin: '400px', threshold: 0.01 } // Proactive loading
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

  const renderRankInput = () => (
    isAdmin && isReorderable && (
      <div className={`flex items-center gap-1 px-2 py-0.5 rounded border text-[10px] font-mono shrink-0 transition-colors ${
        isModified ? 'bg-amber-500/20 border-amber-500/40' : 'bg-sky-500/10 border-sky-500/20'
      }`}>
        <input
          type="number"
          value={localRank}
          onChange={(e) => setLocalRank(parseInt(e.target.value) || 1)}
          onBlur={handleRankSubmit}
          onKeyDown={(e) => e.key === 'Enter' && handleRankSubmit()}
          onClick={(e) => e.stopPropagation()}
          className={`w-8 bg-transparent focus:outline-none text-center font-bold appearance-none [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none ${
            isModified ? 'text-amber-400' : 'text-sky-400'
          }`}
        />
        <span className="text-slate-600">/</span>
        <span className="text-slate-500">{totalCharts}</span>
      </div>
    )
  );

  const renderVisibilityToggle = () => (
    isAdmin && (
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
    )
  );

  const renderName = () => (
    isAdmin ? (
      <button
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); onOpenStudio?.(chart.id); }}
        className="group/name flex items-center gap-2 min-w-0 overflow-hidden text-left"
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
    )
  );

    const className = `glass-card overflow-hidden flex flex-col group transition-all duration-300 hover:border-sky-500/30 hover:shadow-sky-500/5 relative h-full min-h-[450px]`;

  // Grid View Content (Hardcoded)
  return (
    <div className={className}>
      {/* Card Header */}
      <div className="px-4 py-3 flex items-center justify-between border-b border-border/50 bg-card/10 relative">
         <div className="flex items-center gap-3 min-w-0 z-10">
            {renderRankInput()}
            {renderVisibilityToggle()}
            {renderName()}
         </div>

         <div className="flex items-center gap-3 shrink-0">
            {chart.description && (
              <div className="relative group/tip">
                <Info className="w-3.5 h-3.5 text-slate-600 hover:text-sky-400 transition-colors cursor-help" />
                <div className="absolute right-0 top-full mt-1 w-56 px-3 py-2 bg-popover border border-border rounded-lg text-[10px] text-muted-foreground leading-relaxed opacity-0 invisible group-hover/tip:opacity-100 group-hover/tip:visible transition-all z-50 shadow-xl">
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

      <div ref={cardRef} className="flex flex-col flex-1">
        {/* Chart Area — only render Plotly when in viewport */}
        <div className="bg-slate-950/20 relative w-full p-4 h-[350px] min-h-[350px] flex-1">
          {isInView ? (
            <Chart id={chart.id} initialFigure={chart.figure} />
          ) : (
            <div className="flex items-center justify-center h-full w-full">
              <Loader2 className="w-6 h-6 text-sky-400/20 animate-spin" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

// Wrapper for Drag Controls
const DraggableChartCard = React.memo((props: ChartCardProps) => {
    const { chart, isReorderable, index } = props;
    const controls = useDragControls();
    
    // Grid View: anywhere is a drag listener
    const dragListener = true; 

    if (!isReorderable) {
      return (
        <motion.div
           className="h-full flex flex-col"
           initial={{ opacity: 0, y: 20 }}
           whileInView={{ opacity: 1, y: 0 }}
           viewport={{ once: true, margin: "-50px" }}
           transition={{ 
             duration: 0.5, 
             ease: [0.23, 1, 0.32, 1], // Premium easeOutQuint
             delay: index % 6 * 0.05 // Stagger based on column index
           }}
        >
           <ChartCard {...props} />
        </motion.div>
      );
    }
  
    return (
      <Reorder.Item
        value={chart}
        dragListener={dragListener}
        dragControls={controls}
        className="h-full" // Ensure height in grid
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.98 }}
        whileDrag={{
          scale: 1.02,
          boxShadow: '0 25px 50px -12px rgb(0 0 0 / 0.5)',
          zIndex: 50
        }}
        transition={{ duration: 0.2 }}
      >
        <ChartCard 
            dragControls={controls} 
            {...props} 
        />
      </Reorder.Item>
    );
});

DraggableChartCard.displayName = 'DraggableChartCard';


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
  const [showCategoryMenu, setShowCategoryMenu] = useState(false);
  const [showActionMenu, setShowActionMenu] = useState(false);
  
  const categoryRef = useRef<HTMLDivElement>(null);
  const actionRef = useRef<HTMLDivElement>(null);

  // Close menus on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (categoryRef.current && !categoryRef.current.contains(event.target as Node)) {
        setShowCategoryMenu(false);
      }
      if (actionRef.current && !actionRef.current.contains(event.target as Node)) {
        setShowActionMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

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
      <div className="space-y-8 min-h-[800px] animate-pulse">
        {/* Skeleton Command Bar */}
        <div className="h-16 w-full glass-card bg-card/5 border-border/50 rounded-xl" />
        
        {/* Skeleton Header */}
        <div className="flex justify-between items-center px-2">
          <div className="h-8 w-64 bg-card/10 rounded-lg" />
          <div className="h-6 w-32 bg-card/5 rounded-lg" />
        </div>

        {/* Skeleton Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="glass-card h-[450px] flex flex-col overflow-hidden opacity-50">
              <div className="h-12 border-b border-border/50 bg-card/10" />
              <div className="flex-1 p-4">
                <div className="w-full h-full bg-card/5 rounded-xl flex items-center justify-center">
                   <Loader2 className="w-6 h-6 text-sky-500/20 animate-spin" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 min-h-[800px]">
      {/* 🧭 Unified Command Bar (Single Line Architecture) */}
      <div 
        className="flex flex-row items-center gap-4 sticky top-12 z-40 px-6 py-4 border-b !bg-white dark:!bg-black border-border/50 shadow-2xl !opacity-100"
        style={{ backgroundColor: 'rgb(var(--background))' }}
      >
        
        {/* LEFT: Premium Category Selector */}
        <div className="shrink-0" ref={categoryRef}>
          {!searchQuery && (
            <div className="relative">
              <button 
                onClick={() => setShowCategoryMenu(!showCategoryMenu)}
                className={`
                  flex items-center gap-2 pl-3.5 sm:pl-4 pr-3.5 sm:pr-4 py-2.5 
                  bg-secondary/10 border rounded-xl transition-all duration-300
                  ${showCategoryMenu ? 'border-sky-500/50 bg-sky-500/5 shadow-lg shadow-sky-500/10' : 'border-border/50 hover:bg-accent/10'}
                `}
              >
                <Layers className={`w-4 h-4 transition-colors ${showCategoryMenu ? 'text-sky-400' : 'text-sky-400/70'}`} />
                <span className="hidden sm:inline text-xs font-bold text-foreground uppercase tracking-wider truncate max-w-[140px]">
                  {activeCategory}
                </span>
                <ChevronDown className={`w-3.5 h-3.5 text-muted-foreground transition-transform duration-300 ${showCategoryMenu ? 'rotate-180 text-foreground' : ''}`} />
              </button>
              
              <AnimatePresence>
                {showCategoryMenu && (
                  <motion.div 
                    initial={{ opacity: 0, y: 10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 10, scale: 0.95 }}
                    className="absolute left-0 top-full mt-2 w-64 !bg-white dark:!bg-slate-900 border border-border/50 rounded-2xl shadow-2xl p-1.5 z-50 overflow-hidden !opacity-100"
                    style={{ backgroundColor: 'rgb(var(--background))' }}
                  >
                    <div className="px-3 py-2 text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] border-b border-border/30 mb-1 flex items-center justify-between">
                      Indicator Scope
                      <div className="w-1 h-1 rounded-full bg-sky-500 animate-pulse" />
                    </div>
                    
                    <div className="max-h-[300px] overflow-y-auto custom-scrollbar">
                      {allCategories.map((cat) => (
                        <button
                          key={cat}
                          onClick={() => {
                            setActiveCategory(cat);
                            setShowCategoryMenu(false);
                          }}
                          className={`
                            w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-bold transition-all
                            ${activeCategory === cat 
                              ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30 shadow-inner' 
                              : 'text-foreground/70 hover:bg-white/5 hover:text-foreground'
                            }
                          `}
                        >
                          <span className="uppercase tracking-wider">{cat}</span>
                          {activeCategory === cat && <CheckCircle2 className="w-3.5 h-3.5" />}
                        </button>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
          {searchQuery && (
            <div className="flex items-center gap-2 text-sky-400 text-[10px] font-black px-4 py-3 bg-sky-500/10 rounded-xl border border-sky-500/20 whitespace-nowrap tracking-widest uppercase">
              <Search className="w-4 h-4" />
              Intelligence Results
            </div>
          )}
        </div>

        {/* CENTER: Expansive Search Bar */}
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search Indicators..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-11 pr-11 py-2.5 bg-secondary/10 border border-border/50 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/50 transition-all font-light"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-4 top-1/2 -translate-y-1/2 p-1 hover:bg-accent/10 rounded-md transition-colors"
              type="button"
            >
              <X className="w-4 h-4 text-muted-foreground" />
            </button>
          )}
        </div>

        {/* RIGHT: Consolidated System Actions Dropdown */}
        <div className="flex items-center gap-4 shrink-0">
          {isAdmin && isReorderEnabled && isOrderDirty && (
            <div className="animate-in fade-in slide-in-from-right-4 duration-500">
               <button
                 onClick={handleSaveOrder}
                 disabled={reorderMutation.isPending}
                 className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shadow-lg bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/20 active:scale-95 whitespace-nowrap"
               >
                 {reorderMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                 <span className="hidden sm:inline">SAVE RANK</span>
               </button>
            </div>
          )}

          <div className="relative" ref={actionRef}>
            <button 
              onClick={() => setShowActionMenu(!showActionMenu)}
              className={`
                flex items-center gap-2 p-2.5 bg-secondary/10 border rounded-xl transition-all duration-300
                ${showActionMenu ? 'border-sky-500/50 bg-sky-500/5 shadow-lg shadow-sky-500/10' : 'border-border/50 hover:bg-accent/10'}
              `}
            >
              <div className="relative">
                <RefreshCw className={`w-4 h-4 transition-colors ${isRefreshing ? 'animate-spin text-sky-400' : showActionMenu ? 'text-sky-400' : 'text-muted-foreground'}`} />
                {(exporting || exportingHtml) && (
                  <div className="absolute -top-1 -right-1 w-2 h-2 bg-sky-500 rounded-full animate-pulse" />
                )}
              </div>
              <ChevronDown className={`w-3 h-3 text-muted-foreground transition-transform duration-300 ${showActionMenu ? 'rotate-180 text-foreground' : ''}`} />
            </button>

            {/* Premium Action Dropdown Menu */}
            <AnimatePresence>
              {showActionMenu && (
                <motion.div 
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  className="absolute right-0 top-full mt-2 w-64 !bg-white dark:!bg-slate-900 border border-border/50 rounded-2xl shadow-2xl p-1.5 z-50 overflow-hidden !opacity-100"
                  style={{ backgroundColor: 'rgb(var(--background))' }}
                >
                  <div className="px-3 py-2 text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] border-b border-border/30 mb-1 flex items-center justify-between">
                    Resource Actions
                    <div className="w-1 h-1 rounded-full bg-indigo-500 animate-pulse" />
                  </div>
                  
                  <button
                    onClick={() => { handleRefreshAll(); setShowActionMenu(false); }}
                    disabled={isRefreshing}
                    className="w-full flex items-center justify-between px-3 py-3 rounded-lg text-xs font-bold text-foreground hover:bg-white/5 transition-all group/opt disabled:opacity-30"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-7 h-7 rounded-lg bg-sky-500/10 flex items-center justify-center border border-sky-500/20 group-hover/opt:border-sky-500/40">
                        <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-sky-400' : 'text-sky-400'}`} />
                      </div>
                      <span className="uppercase tracking-wider">Sync Data</span>
                    </div>
                    {isRefreshing && <span className="text-[9px] text-sky-500 animate-pulse font-mono font-bold tracking-tighter">LIVE</span>}
                  </button>

                  <div className="h-px bg-border/20 my-1 mx-2" />

                  <button
                    onClick={() => { handleExportPDF(); setShowActionMenu(false); }}
                    disabled={exporting}
                    className="w-full flex items-center gap-3 px-3 py-3 rounded-lg text-xs font-bold text-foreground hover:bg-white/5 transition-all group/opt disabled:opacity-30"
                  >
                    <div className="w-7 h-7 rounded-lg bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20 group-hover/opt:border-emerald-500/40">
                      <FileDown className={`w-3.5 h-3.5 ${exporting ? 'animate-pulse text-emerald-400' : 'text-emerald-400'}`} />
                    </div>
                    <span className="uppercase tracking-wider">
                      {exporting ? 'Processing PDF...' : 'Generate PDF'}
                    </span>
                  </button>

                  <button
                    onClick={() => { handleExportHTML(); setShowActionMenu(false); }}
                    disabled={exportingHtml}
                    className="w-full flex items-center gap-3 px-3 py-3 rounded-lg text-xs font-bold text-foreground hover:bg-white/5 transition-all group/opt disabled:opacity-30"
                  >
                    <div className="w-7 h-7 rounded-lg bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 group-hover/opt:border-indigo-500/40">
                      <Monitor className={`w-3.5 h-3.5 ${exportingHtml ? 'animate-pulse text-indigo-400' : 'text-indigo-400'}`} />
                    </div>
                    <span className="uppercase tracking-wider">
                      {exportingHtml ? 'Packaging...' : 'Web Archive'}
                    </span>
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* 📊 Results Header */}
      <div className="flex items-center justify-between px-2">
        <h2 className="text-2xl font-semibold text-foreground flex items-center gap-3 tracking-tight">
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

      {/* 🖼️ Grid Display */}
        {isReorderEnabled ? (
          <Reorder.Group 
            values={filteredCharts}
            onReorder={handleReorder}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8"
          >
            {filteredCharts.map((chart, idx) => (
              <DraggableChartCard
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {filteredCharts.map((chart, idx) => (
              <DraggableChartCard
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
