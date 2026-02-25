'use client';

import React, { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Layers,
  Plus, Eye, EyeOff, Loader2, Copy,
  ArrowUp, ArrowDown, Search,
  Info, RefreshCw, LayoutGrid, Trash2,
  X, Filter, PanelLeftClose, PanelLeftOpen, Save, RotateCcw, FileDown,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { apiFetch, apiFetchJson } from '@/lib/api';
import Chart from './Chart';
import CustomChartEditor from './CustomChartEditor';

interface ChartMeta {
  id: string;
  name: string;
  category: string | null;
  description: string | null;
  updated_at: string | null;
  rank: number;
  export_pdf?: boolean;
  created_by_user_id?: string | null;
  created_by_email?: string | null;
  created_by_name?: string | null;
  code?: string;
  figure?: any; // Prefetched figure data
}

interface ChartCardProps {
  chart: ChartMeta;
  canEdit: boolean;
  canRefresh: boolean;
  canDelete: boolean;
  canManageVisibility: boolean;
  isReorderable: boolean;
  onTogglePdf: (id: string, status: boolean) => void;
  onRefreshChart?: (id: string) => void;
  onCopyChart?: (id: string) => void;
  onDeleteChart?: (id: string) => void;
  isRefreshingChart?: boolean;
  isDeletingChart?: boolean;
  isSyncing?: boolean;
  onRankChange?: (id: string, newRank: number) => void;
  onMoveUp?: (id: string) => void;
  onMoveDown?: (id: string) => void;
  copySignal?: number;
  index: number;
  totalCharts: number;
  onOpenStudio?: (chartId: string | null) => void;
}

const ChartCard = React.memo(function ChartCard({ 
  chart, 
  canEdit,
  canRefresh,
  canDelete,
  canManageVisibility,
  isReorderable, 
  onTogglePdf, 
  onRefreshChart,
  onCopyChart,
  onDeleteChart,
  isRefreshingChart,
  isDeletingChart,
  isSyncing,
  onRankChange,
  onMoveUp,
  onMoveDown,
  copySignal,
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

    if (typeof IntersectionObserver === 'undefined') {
      setIsInView(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        // Keep charts mounted slightly before/after viewport, then unmount once far away.
        setIsInView(entry.isIntersecting);
      },
      { rootMargin: '500px 0px 500px 0px', threshold: 0 }
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
  const creatorLabel = chart.created_by_name || chart.created_by_email || 'Unknown';

  const handleRankSubmit = () => {
    if (isModified) {
      onRankChange?.(chart.id, localRank - 1);
    }
  };

  const renderRankInput = () => (
    isReorderable && (
      <div className={`flex items-center gap-0.5 px-1 py-0.5 rounded border text-[10px] font-mono shrink-0 transition-colors ${
        isModified ? 'bg-amber-500/20 border-amber-500/40' : 'bg-sky-500/10 border-sky-500/20'
      }`}>
        <input
          type="number"
          value={localRank}
          onChange={(e) => setLocalRank(parseInt(e.target.value) || 1)}
          onBlur={handleRankSubmit}
          onKeyDown={(e) => e.key === 'Enter' && handleRankSubmit()}
          onClick={(e) => e.stopPropagation()}
          className={`w-5 bg-transparent focus:outline-none text-center font-bold appearance-none [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none ${
            isModified ? 'text-amber-400' : 'text-sky-400'
          }`}
        />
      </div>
    )
  );

  const renderVisibilityToggle = () => (
    canManageVisibility && (
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

  const renderOrderButtons = () => (
    isReorderable && (
      <div className="flex items-center gap-1 shrink-0">
        <button
          onClick={(e) => { e.preventDefault(); e.stopPropagation(); onMoveUp?.(chart.id); }}
          className="p-1 rounded hover:bg-accent/30 text-muted-foreground/60 hover:text-sky-400 transition-colors"
          title="Move up"
          aria-label="Move chart up"
          disabled={index === 0}
        >
          <ArrowUp className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={(e) => { e.preventDefault(); e.stopPropagation(); onMoveDown?.(chart.id); }}
          className="p-1 rounded hover:bg-accent/30 text-muted-foreground/60 hover:text-sky-400 transition-colors"
          title="Move down"
          aria-label="Move chart down"
          disabled={index === totalCharts - 1}
        >
          <ArrowDown className="w-3.5 h-3.5" />
        </button>
      </div>
    )
  );

  const renderName = () => (
    canEdit ? (
      <button
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); onOpenStudio?.(chart.id); }}
        className="group/name flex items-center gap-2 min-w-0 text-left"
        title="Edit in Studio"
      >
        <span className="text-[10px] font-mono text-foreground/80 group-hover/name:text-foreground transition-all leading-tight">
          {chart.name}
        </span>
      </button>
    ) : (
      <span className="text-[10px] font-mono text-foreground/80 leading-tight">
        {chart.name}
      </span>
    )
  );

    const className = `glass-card overflow-hidden flex flex-col group transition-all duration-300 hover:border-sky-500/30 hover:shadow-sky-500/5 relative h-full min-h-[380px]`;

  const [infoOpen, setInfoOpen] = useState(false);
  const infoRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!infoOpen) return;
    function handleClick(e: MouseEvent) {
      if (infoRef.current && !infoRef.current.contains(e.target as Node)) setInfoOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [infoOpen]);

  // Grid View Content (Hardcoded)
  return (
    <div className={className}>
      {/* Card Header */}
      <div className="px-3 py-1.5 flex items-center justify-between gap-2 border-b border-border/50 bg-card/10 relative">
         <div className="flex items-center gap-1.5 min-w-0 flex-1 z-10">
            {renderRankInput()}
            {renderOrderButtons()}
            {renderVisibilityToggle()}
            {renderName()}
         </div>

         <div className="relative shrink-0" ref={infoRef}>
            <button
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); setInfoOpen(v => !v); }}
              className={`p-1 rounded transition-colors ${infoOpen ? 'text-sky-400 bg-sky-500/10' : 'text-muted-foreground/50 hover:text-foreground'}`}
              title="Chart info & actions"
              aria-label="Chart info and actions"
            >
              <Info className="w-3.5 h-3.5" />
            </button>
            <AnimatePresence>
              {infoOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 4, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 4, scale: 0.96 }}
                  transition={{ duration: 0.12 }}
                  className="absolute right-0 top-full mt-1 w-56 bg-popover border border-border rounded-lg shadow-xl z-50 overflow-hidden"
                >
                  {chart.description && (
                    <div className="px-3 py-2 text-[10px] text-muted-foreground leading-relaxed border-b border-border/50">
                      {chart.description}
                    </div>
                  )}
                  <div className="px-3 py-1.5 text-[9px] text-muted-foreground/70 font-mono border-b border-border/50">
                    <span title={`Created by ${creatorLabel}`}>by {creatorLabel}</span>
                    {chart.updated_at && (
                      <span className="ml-2">{new Date(chart.updated_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                    )}
                  </div>
                  {(canRefresh || canDelete || !!onCopyChart) && (
                    <div className="p-1.5 flex flex-col gap-0.5">
                      {canRefresh && (
                        <button
                          onClick={(e) => { e.preventDefault(); e.stopPropagation(); onRefreshChart?.(chart.id); setInfoOpen(false); }}
                          disabled={!!isRefreshingChart}
                          className="flex items-center gap-2 w-full px-2 py-1.5 rounded text-[11px] text-muted-foreground hover:text-foreground hover:bg-accent/20 transition-colors disabled:opacity-50"
                        >
                          <RefreshCw className={`w-3 h-3 ${isRefreshingChart ? 'animate-spin text-sky-400' : ''}`} />
                          Refresh
                        </button>
                      )}
                      <button
                        onClick={(e) => { e.preventDefault(); e.stopPropagation(); onCopyChart?.(chart.id); setInfoOpen(false); }}
                        className="flex items-center gap-2 w-full px-2 py-1.5 rounded text-[11px] text-muted-foreground hover:text-foreground hover:bg-accent/20 transition-colors"
                      >
                        <Copy className="w-3 h-3" />
                        Copy image
                      </button>
                      {canDelete && (
                        <button
                          onClick={(e) => { e.preventDefault(); e.stopPropagation(); onDeleteChart?.(chart.id); setInfoOpen(false); }}
                          disabled={!!isDeletingChart}
                          className="flex items-center gap-2 w-full px-2 py-1.5 rounded text-[11px] text-muted-foreground hover:text-rose-400 hover:bg-rose-500/10 transition-colors disabled:opacity-50"
                        >
                          <Trash2 className={`w-3 h-3 ${isDeletingChart ? 'animate-pulse text-rose-400' : ''}`} />
                          Delete
                        </button>
                      )}
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
         </div>
      </div>

      <div ref={cardRef} className="flex flex-col flex-1">
        {/* Chart Area — only render Plotly when in viewport */}
        <div className="bg-background/80 dark:bg-slate-950/20 relative w-full p-4 h-[290px] min-h-[290px] flex-1">
          {isInView ? (
            <Chart id={chart.id} initialFigure={chart.figure} copySignal={copySignal} />
          ) : (
            <div className="relative h-full w-full overflow-hidden rounded-lg border border-border/20 bg-background/90">
              <motion.div
                className="absolute inset-y-0 -left-1/3 w-1/3 bg-gradient-to-r from-transparent via-primary/5 to-transparent"
                animate={{ x: ['0%', '360%'] }}
                transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              />
              <div className="absolute inset-0 p-6 flex flex-col justify-between">
                <div className="space-y-3">
                  <div className="h-4 w-40 rounded bg-primary/10 animate-pulse" />
                  <div className="h-3 w-24 rounded bg-muted/50 animate-pulse" />
                </div>
                <div className="grid grid-cols-8 gap-2 items-end h-32">
                  {Array.from({ length: 8 }).map((_, i) => (
                    <div
                      key={i}
                      className="rounded-sm bg-primary/15 animate-pulse"
                      style={{ height: `${25 + ((i * 13) % 60)}%`, animationDelay: `${i * 80}ms` }}
                    />
                  ))}
                </div>
                <div className="flex items-center justify-center">
                  <Loader2 className="w-5 h-5 text-sky-400/30 animate-spin" />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
});


interface DashboardGalleryProps {
  chartsByCategory: Record<string, ChartMeta[]>;
  onOpenStudio?: (chartId: string | null) => void;
}

export default function DashboardGallery({ chartsByCategory }: DashboardGalleryProps) {
  const { user } = useAuth();
  const { theme } = useTheme();
  const role = String(user?.role || '').toLowerCase();
  const isOwner = !!user && role === 'owner';
  const isAdminRole = !!user && (role === 'admin' || user.is_admin);
  const canRefreshAllCharts = isOwner || isAdminRole;
  const currentUserId = user?.id || null;

  const isChartOwner = useCallback(
    (chart: ChartMeta) => {
      if (!currentUserId || !chart.created_by_user_id) return false;
      return String(chart.created_by_user_id) === String(currentUserId);
    },
    [currentUserId]
  );
  const queryClient = useQueryClient();

  // ⚡ Performance Optimized State
  const [localCharts, setLocalCharts] = useState<ChartMeta[]>([]);
  const [originalCharts, setOriginalCharts] = useState<ChartMeta[]>([]);
  const [refreshingChartIds, setRefreshingChartIds] = useState<Record<string, boolean>>({});
  const [deletingChartIds, setDeletingChartIds] = useState<Record<string, boolean>>({});
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
  const [copySignals, setCopySignals] = useState<Record<string, number>>({});

  const [mounted, setMounted] = useState(false);
  const [quickJumpId, setQuickJumpId] = useState('');
  const [showQuickJumpMenu, setShowQuickJumpMenu] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  // Expanded by default for large screens
  const router = useRouter();
  const searchParams = useSearchParams();

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeStudioChartId, setActiveStudioChartId] = useState<string | null>(null);

  // Initial Sync from URL
  useEffect(() => {
    const chartId = searchParams.get('chartId');
    const isNew = searchParams.get('new') === 'true';
    const isDesktop = typeof window !== 'undefined' && window.innerWidth >= 768;

    if (isNew) {
        setActiveStudioChartId('');
        if (!sidebarOpen && isDesktop) setSidebarOpen(true);
    } else if (chartId) {
        setActiveStudioChartId(chartId);
        setQuickJumpId(chartId);
        if (!sidebarOpen && isDesktop) setSidebarOpen(true);
    } else {
        setActiveStudioChartId(null);
    }
  }, [searchParams, sidebarOpen]);

  // Override onOpenStudio to stay in this page
  const handleOpenInStudio = useCallback((chartId: string | null) => {
    if (chartId) {
        router.push(`?chartId=${encodeURIComponent(chartId)}`, { scroll: false });
    } else {
        router.push('?new=true', { scroll: false });
    }
  }, [router]);
  
  const handleCloseStudio = useCallback(() => {
    router.push('/', { scroll: false });
  }, [router]);

  const quickJumpRef = useRef<HTMLDivElement>(null);
  const chartAnchorRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const mainScrollRef = useRef<HTMLElement>(null);
  const isAutoScrolling = useRef(false);

  // Initial Sidebar State for Mobile
  useEffect(() => {
    if (typeof window !== 'undefined' && window.innerWidth < 1024) {
      setSidebarOpen(false);
    }
  }, []);

  // Close quick-jump menu on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (quickJumpRef.current && !quickJumpRef.current.contains(event.target as Node)) {
        setShowQuickJumpMenu(false);
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

  const refreshChartsMutation = useMutation({
    mutationFn: async () => {
      const res = await apiFetch('/api/task/refresh-charts', { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to trigger chart refresh');
      }
      return res.json() as Promise<{ task_id?: string }>;
    },
    onSettled: () => {
      // Bottom-right TaskNotifications consumes this feed.
      queryClient.invalidateQueries({ queryKey: ['task-processes'] });
    },
  });

  const isRefreshing = refreshChartsMutation.isPending;


  const isOrderDirty = useMemo(() => {
    if (localCharts.length !== originalCharts.length) return false;
    // Fast ID check
    return localCharts.some((c, i) => c.id !== originalCharts[i]?.id);
  }, [localCharts, originalCharts]);

  const handleRefreshAll = useCallback(async () => {
    if (!canRefreshAllCharts || isRefreshing) return;
    try {
      const data = await refreshChartsMutation.mutateAsync();
      if (data?.task_id) {
        queryClient.invalidateQueries({ queryKey: ['task-processes'] });
      }
    } catch (e) {
      // Keep UI resilient; TaskNotifications shows backend task status/errors.
    }
  }, [canRefreshAllCharts, isRefreshing, refreshChartsMutation, queryClient]);

  const handleExportPDF = async () => {
    if (exporting) return;
    setExporting(true);
    setExportStatus('idle');
    try {
      const res = await apiFetch('/api/custom/pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: [], theme }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'PDF export failed');
      }
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
    } catch (err: any) {
      console.error('PDF export error:', err);
      setExportStatus('error');
      setTimeout(() => setExportStatus('idle'), 3000);
    } finally {
      queryClient.invalidateQueries({ queryKey: ['task-processes'] });
      setExporting(false);
    }
  };

  const handleExportHTML = async () => {
    if (exportingHtml) return;
    setExportingHtml(true);
    setExportHtmlStatus('idle');
    try {
      const res = await apiFetch('/api/custom/html', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: [], theme }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'HTML export failed');
      }
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
    } catch (err: any) {
      console.error('HTML export error:', err);
      setExportHtmlStatus('error');
      setTimeout(() => setExportHtmlStatus('idle'), 3000);
    } finally {
      queryClient.invalidateQueries({ queryKey: ['task-processes'] });
      setExportingHtml(false);
    }
  };

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

  // Debounce search input (300ms)
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchQuery.trim().toLowerCase()), 300);
    return () => clearTimeout(t);
  }, [searchQuery]);

  // 🔍 Filter & Sort charts (Memoized)
  const allFilteredCharts = useMemo(() => {
    let result = [...localCharts];

    if (debouncedSearch) {
      result = result.filter(c =>
        `${c.name || ''}|${c.category || ''}|${c.description || ''}`.toLowerCase().includes(debouncedSearch)
      );
    }

    if (!isOwner && !isAdminRole) {
      result = result.filter((c) => c.export_pdf !== false || isChartOwner(c));
    }

    return result;
  }, [localCharts, isOwner, isAdminRole, isChartOwner, debouncedSearch]);

  // No pagination: render all charts at once
  const filteredCharts = allFilteredCharts;

  // Group filtered charts by category (preserving rank order within each group)
  const groupedCharts = useMemo(() => {
    const groups = new Map<string, ChartMeta[]>();
    for (const chart of filteredCharts) {
      const cat = chart.category || 'Uncategorized';
      if (!groups.has(cat)) groups.set(cat, []);
      groups.get(cat)!.push(chart);
    }
    return Array.from(groups.entries()).map(([category, charts]) => ({ category, charts }));
  }, [filteredCharts]);

  // 📡 Active Chart Tracking (Scroll Spy)
  useEffect(() => {
    if (filteredCharts.length === 0) return;

    const observerOptions = {
      root: mainScrollRef.current, // scroll spy against the actual scroll container
      rootMargin: '-10% 0px -70% 0px',
      threshold: 0
    };

    const observer = new IntersectionObserver((entries) => {
      if (isAutoScrolling.current) return;
      
      const intersecting = entries.find(e => e.isIntersecting);
      if (intersecting) {
        setQuickJumpId(intersecting.target.id.replace('chart-anchor-', ''));
      }
    }, observerOptions);

    filteredCharts.forEach(chart => {
      const el = document.getElementById(`chart-anchor-${chart.id}`);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [filteredCharts]);
  const quickJumpIndex = useMemo(
    () => filteredCharts.findIndex((c) => c.id === quickJumpId),
    [filteredCharts, quickJumpId]
  );
  const quickJumpLabel = useMemo(() => {
    if (quickJumpIndex < 0) return 'Select chart';
    const chart = filteredCharts[quickJumpIndex];
    if (!chart) return 'Select chart';
    return `${quickJumpIndex + 1}. ${chart.name || `Chart ${quickJumpIndex + 1}`}`;
  }, [filteredCharts, quickJumpIndex]);

  const setChartAnchorRef = useCallback(
    (chartId: string) => (node: HTMLDivElement | null) => {
      if (node) {
        chartAnchorRefs.current[chartId] = node;
        return;
      }
      delete chartAnchorRefs.current[chartId];
    },
    []
  );

  const scrollToChart = useCallback((chartId: string) => {
    if (!chartId) return;
    const target =
      chartAnchorRefs.current[chartId] ||
      document.getElementById(`chart-anchor-${chartId}`);
    if (!target) return;

    const container = mainScrollRef.current;
    if (!container) return;

    isAutoScrolling.current = true;
    const stickyOffset = 16;
    const y = target.getBoundingClientRect().top - container.getBoundingClientRect().top + container.scrollTop - stickyOffset;

    container.scrollTo({ top: Math.max(0, y), behavior: 'smooth' });

    // Clear auto-scroll flag after animation
    setTimeout(() => {
      isAutoScrolling.current = false;
    }, 800);
  }, []);

  useEffect(() => {
    if (filteredCharts.length === 0) {
      if (quickJumpId) setQuickJumpId('');
      if (showQuickJumpMenu) setShowQuickJumpMenu(false);
      return;
    }
    if (!quickJumpId || !filteredCharts.some((c) => c.id === quickJumpId)) {
      setQuickJumpId(filteredCharts[0].id);
    }
  }, [filteredCharts, quickJumpId, showQuickJumpMenu]);

  const handleQuickJumpSelect = useCallback(
    (chartId: string) => {
      setQuickJumpId(chartId);
      setShowQuickJumpMenu(false);

      // Close navigator on mobile when selecting a chart
      if (typeof window !== 'undefined' && window.innerWidth < 768) {
        setSidebarOpen(false);
      }

      // If we are in Studio view, switch the active chart via URL
      if (activeStudioChartId !== null) {
        router.push(`?chartId=${encodeURIComponent(chartId)}`, { scroll: false });
      } else {
        scrollToChart(chartId);
      }
    },
    [scrollToChart, activeStudioChartId, router]
  );

  const handleQuickJumpStep = useCallback(
    (delta: number) => {
      if (filteredCharts.length === 0) return;
      const currentIndex = filteredCharts.findIndex((c) => c.id === quickJumpId);
      const baseIndex = currentIndex >= 0 ? currentIndex : 0;
      const nextIndex = Math.max(0, Math.min(baseIndex + delta, filteredCharts.length - 1));
      const next = filteredCharts[nextIndex];
      if (!next) return;
      handleQuickJumpSelect(next.id);
    },
    [filteredCharts, quickJumpId, handleQuickJumpSelect]
  );

  const isReorderEnabled = isOwner;
  const canManageVisibility = isOwner;
  const canEditChart = useCallback(
    (chart: ChartMeta) => isOwner || isChartOwner(chart),
    [isOwner, isChartOwner]
  );
  const canDeleteChart = canEditChart;
  const canRefreshChart = useCallback(
    (chart: ChartMeta) => canRefreshAllCharts || isChartOwner(chart),
    [canRefreshAllCharts, isChartOwner]
  );

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

  const refreshChartMutation = useMutation({
    mutationFn: async (chartId: string) => {
      return apiFetchJson(`/api/custom/${chartId}/refresh`, {
        method: 'POST',
      });
    },
    onSuccess: (_data, chartId) => {
      // Refetch only the specific chart figure — not all of them
      queryClient.invalidateQueries({ queryKey: ['chart-figure', chartId], exact: true });
      setRefreshingChartIds((prev) => {
        const next = { ...prev };
        delete next[chartId];
        return next;
      });
    },
    onError: (_err, chartId) => {
      setRefreshingChartIds((prev) => {
        const next = { ...prev };
        delete next[chartId];
        return next;
      });
    },
  });

  const deleteChartMutation = useMutation({
    mutationFn: async (chartId: string) => {
      await apiFetchJson(`/api/custom/${chartId}`, { method: 'DELETE' });
      return chartId;
    },
    onSuccess: (chartId) => {
      setLocalCharts((prev) => prev.filter((c) => c.id !== chartId));
      setOriginalCharts((prev) => prev.filter((c) => c.id !== chartId));
      // Remove the deleted chart from cache directly — no need to refetch all figures
      queryClient.removeQueries({ queryKey: ['chart-figure', chartId] });
      queryClient.setQueryData(['dashboard-summary'], (old: any) => {
        if (!old?.charts_by_category) return old;
        const updated: Record<string, any[]> = {};
        for (const [cat, charts] of Object.entries(old.charts_by_category as Record<string, any[]>)) {
          const filtered = charts.filter((c: any) => c.id !== chartId);
          if (filtered.length > 0) updated[cat] = filtered;
        }
        return {
          ...old,
          charts_by_category: updated,
          categories: Object.keys(updated),
        };
      });
      queryClient.invalidateQueries({ queryKey: ['custom-charts'] });
      setDeletingChartIds((prev) => {
        const next = { ...prev };
        delete next[chartId];
        return next;
      });
    },
    onError: (_err, chartId) => {
      setDeletingChartIds((prev) => {
        const next = { ...prev };
        delete next[chartId];
        return next;
      });
    },
  });

  const handleTogglePdf = React.useCallback((id: string, status: boolean) => {
    if (!canManageVisibility) return;
    togglePdfMutation.mutate({ id, status });
  }, [canManageVisibility, togglePdfMutation]);

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

  const handleMoveBy = React.useCallback((id: string, delta: number) => {
    setLocalCharts(prev => {
      const oldIndex = prev.findIndex(c => c.id === id);
      if (oldIndex === -1) return prev;
      const newIndex = Math.max(0, Math.min(oldIndex + delta, prev.length - 1));
      if (oldIndex === newIndex) return prev;

      const next = [...prev];
      const [item] = next.splice(oldIndex, 1);
      next.splice(newIndex, 0, item);
      return next.map((c, i) => ({ ...c, rank: i }));
    });
  }, []);

  const handleSaveOrder = React.useCallback(() => {
    if (!isReorderEnabled) return;
    reorderMutation.mutate(localCharts);
  }, [isReorderEnabled, localCharts, reorderMutation]);

  const handleResetOrder = React.useCallback(() => {
    setLocalCharts([...originalCharts]);
  }, [originalCharts]);

  const handleRefreshChart = React.useCallback((id: string) => {
    const target = localCharts.find((c) => c.id === id);
    if (!target || !canRefreshChart(target)) return;
    setRefreshingChartIds((prev) => ({ ...prev, [id]: true }));
    refreshChartMutation.mutate(id);
  }, [canRefreshChart, localCharts, refreshChartMutation]);

  const handleCopyFromHeader = React.useCallback((id: string) => {
    setCopySignals((prev) => ({ ...prev, [id]: (prev[id] || 0) + 1 }));
  }, []);

  const handleDeleteChart = React.useCallback((id: string) => {
    const target = localCharts.find((c) => c.id === id);
    if (!target || !canDeleteChart(target)) return;
    setDeleteTarget({ id, name: target?.name || id });
  }, [canDeleteChart, localCharts]);

  const confirmDeleteChart = React.useCallback(() => {
    if (!deleteTarget) return;
    const id = deleteTarget.id;
    setDeletingChartIds((prev) => ({ ...prev, [id]: true }));
    deleteChartMutation.mutate(id);
    setDeleteTarget(null);
  }, [deleteTarget, deleteChartMutation]);

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
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
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
    <div className="flex h-[calc(100vh-48px)] relative bg-background overflow-hidden">
      {/* 🧭 Sidebar Navigator - Now a Flex Sibling for Desktop */}
      <aside
        className={`
          shrink-0 transition-all duration-300 flex flex-col border-r border-border/50 bg-background backdrop-blur-2xl z-[95] overflow-hidden
          ${sidebarOpen ? 'w-80 border-r' : 'w-0 border-r-0'}
          fixed inset-y-0 left-0 top-12 md:relative md:top-0 h-[calc(100vh-48px)]
        `}
      >
        <div className="h-12 shrink-0 flex items-center justify-between px-3 border-b border-border/20 bg-foreground/[0.02]">
            <div className="flex items-center gap-1.5">
              <button 
                onClick={handleCloseStudio}
                className={`p-1.5 rounded-lg transition-all ${!activeStudioChartId ? 'bg-sky-500/10 text-sky-400' : 'text-muted-foreground hover:text-foreground'}`}
                title="Dashboard View"
              >
                <LayoutGrid className="w-3.5 h-3.5" />
              </button>
              <div className="h-4 w-px bg-border/30 mx-0.5" />
              <button 
                onClick={() => handleOpenInStudio(null)}
                className={`p-1.5 rounded-lg transition-all ${activeStudioChartId === null && sidebarOpen ? 'text-emerald-400 hover:text-emerald-300' : 'text-muted-foreground hover:text-foreground'}`}
                title="Create New Analysis"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="flex items-center gap-2">
               <span className="text-[9px] font-bold text-muted-foreground/70 uppercase tracking-widest">Navigator</span>
               <span className="text-[8px] tabular-nums px-1.5 py-0.5 rounded-full bg-sky-500/5 text-muted-foreground font-mono border border-border/20">
                  {filteredCharts.length}
               </span>
            </div>

            <button 
              onClick={() => setSidebarOpen(false)}
              className="p-1.5 rounded-lg hover:bg-accent/20 text-muted-foreground hover:text-foreground transition-colors"
              title="Close Sidebar"
            >
              <PanelLeftClose className="w-3.5 h-3.5" />
            </button>
        </div>

        {/* Action Buttons */}
        <div className="shrink-0 border-t border-border/20 p-2 flex gap-1">
          {canRefreshAllCharts && (
            <button
              onClick={handleRefreshAll}
              disabled={isRefreshing}
              className="flex-1 flex items-center justify-center p-1.5 rounded-lg text-sky-400 bg-sky-500/10 hover:bg-sky-500/20 border border-sky-500/20 transition-all disabled:opacity-50"
              title="Refresh all charts"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            </button>
          )}
          {isOwner && (
            <>
              <button
                onClick={handleExportPDF}
                disabled={exporting}
                className="flex-1 flex items-center justify-center p-1.5 rounded-lg text-rose-400 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 transition-all disabled:opacity-50"
                title={exporting ? 'Generating PDF...' : 'Download PDF'}
              >
                <FileDown className={`w-3.5 h-3.5 ${exporting ? 'animate-pulse' : ''}`} />
              </button>
              <button
                onClick={handleExportHTML}
                disabled={exportingHtml}
                className="flex-1 flex items-center justify-center p-1.5 rounded-lg text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 transition-all disabled:opacity-50"
                title={exportingHtml ? 'Generating HTML...' : 'Download HTML'}
              >
                <FileDown className={`w-3.5 h-3.5 ${exportingHtml ? 'animate-pulse' : ''}`} />
              </button>
            </>
          )}
        </div>

        {/* Search - Ultra Compact */}
        <div className="px-3 py-2 border-b border-border/20 bg-foreground/[0.01]">
          <div className="relative group">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground/50 group-focus-within:text-sky-500 transition-colors" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search..."
              className="w-full pl-7 pr-3 py-1 bg-secondary/30 border border-border/30 rounded text-[9px] text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-0 transition-all"
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

        {/* Scrollable Indicator List - Compact Items */}
        <div className="flex-grow overflow-y-auto custom-scrollbar px-1.5 py-2 space-y-px">
          {filteredCharts.map((chart, idx) => {
            const isActive = chart.id === quickJumpId;
            return (
              <button
                key={chart.id}
                onClick={() => handleQuickJumpSelect(chart.id)}
                className={`w-full group relative flex items-start gap-2 px-2 py-1 rounded cursor-pointer transition-all duration-150 border ${
                  isActive
                    ? 'bg-sky-500/10 border-sky-500/10'
                    : 'border-transparent hover:bg-accent/20'
                }`}
              >
                {/* 🔢 Index Number - Smaller */}
                <div className={`mt-0.5 text-[8px] font-mono shrink-0 w-5 h-3 flex items-center justify-center rounded border transition-colors ${
                  isActive ? 'bg-sky-500/20 text-sky-400 border-sky-500/20' : 'bg-foreground/5 text-muted-foreground/70 border-border/20'
                }`}>
                  {idx + 1}
                </div>

                {/* 📝 Content - Smaller */}
                <div className="flex-1 min-w-0 flex flex-col items-start text-left">
                  <span className={`text-[9px] font-medium leading-tight truncate w-full ${isActive ? 'text-sky-300' : 'text-muted-foreground group-hover:text-foreground'}`}>
                    {chart.name || 'Untitled'}
                  </span>
                  <div className="flex items-center gap-1 opacity-50">
                    <span className="text-[7px] font-mono uppercase tracking-tighter text-muted-foreground/60">
                      {chart.category || 'ANALYSIS'}
                    </span>
                    {chart.export_pdf && <div className="w-0.5 h-0.5 rounded-full bg-emerald-500" />}
                  </div>
                </div>

                {isActive && (
                   <motion.div layoutId="sidebar-active" className="absolute left-0 w-0.5 h-2.5 bg-sky-500/60 rounded-r-full" />
                )}
              </button>
            );
          })}
          {filteredCharts.length === 0 && (
            <div className="py-6 px-4 text-center">
               <Filter className="w-4 h-4 text-slate-900 mx-auto mb-1 opacity-10" />
               <p className="text-[8px] text-slate-700 font-medium tracking-tight">NO MATCHES</p>
            </div>
          )}
        </div>
      </aside>

      {/* 🧭 Mobile Overlay Backdrop - Below Sidebar but Above Content */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSidebarOpen(false)}
            className="md:hidden fixed inset-0 top-12 z-[90] bg-foreground/40 dark:bg-black/60 backdrop-blur-sm"
          />
        )}
      </AnimatePresence>

      {/* Main Content Area - Scrollable Flex Child */}
      <main ref={mainScrollRef} className="flex-1 min-w-0 h-full overflow-y-auto custom-scrollbar relative flex flex-col bg-background">
        {activeStudioChartId !== null ? (
          <div className="h-full w-full relative">
             {!sidebarOpen && (
               <button
                 onClick={() => setSidebarOpen(true)}
                 className="absolute left-3 top-3 z-[40] p-2 rounded-lg border border-sky-500/30 bg-sky-500/10 text-sky-400 hover:bg-sky-500/20 transition-all active:scale-95"
                 title="Open Navigator"
               >
                 <PanelLeftOpen className="w-4 h-4" />
               </button>
             )}
             <CustomChartEditor
                mode="integrated"
                initialChartId={activeStudioChartId === '' ? null : activeStudioChartId}
                onClose={handleCloseStudio}
             />
          </div>
        ) : (
          <div className={`transition-all duration-300 p-4 md:p-8 xl:p-10 ${sidebarOpen ? 'xl:pr-16 2xl:pr-24' : ''}`}>
            {/* Toggle Button (when sidebar is closed) */}
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="fixed left-4 top-16 z-[40] p-3 rounded-xl border border-sky-500/30 bg-sky-500/10 text-sky-400 hover:bg-sky-500/20 shadow-xl shadow-sky-500/10 transition-all active:scale-95"
                title="Open Navigator"
              >
                <PanelLeftOpen className="w-5 h-5" />
              </button>
            )}

            {/* 🖼️ Grid Display — grouped by category */}
            <div className={`space-y-8 mx-auto ${sidebarOpen ? 'max-w-[1400px]' : 'max-w-[1600px]'}`}>
            {groupedCharts.map(({ category, charts: groupCharts }) => {
              const globalOffset = filteredCharts.indexOf(groupCharts[0]);
              return (
                <div key={category}>
                  {/* Category Section Header */}
                  {groupedCharts.length > 1 && (
                    <div className="flex items-center gap-3 mb-4 px-1">
                      <div className="h-px flex-1 bg-border/30" />
                      <span className="text-[9px] font-mono font-bold uppercase tracking-[0.25em] text-muted-foreground/50 px-2 shrink-0">
                        {category}
                      </span>
                      <span className="text-[8px] font-mono text-muted-foreground/30 shrink-0">
                        {groupCharts.length}
                      </span>
                      <div className="h-px flex-1 bg-border/30" />
                    </div>
                  )}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8 lg:gap-10">
                    {groupCharts.map((chart, localIdx) => {
                      const idx = globalOffset + localIdx;
                      return (
                        <motion.div
                          key={chart.id}
                          id={`chart-anchor-${chart.id}`}
                          ref={setChartAnchorRef(chart.id)}
                          className="h-full flex flex-col"
                          initial={{ opacity: 0, y: 20 }}
                          whileInView={{ opacity: 1, y: 0 }}
                          viewport={{ once: true, margin: "-50px" }}
                          transition={{
                            duration: 0.5,
                            ease: [0.23, 1, 0.32, 1],
                            delay: localIdx % 4 * 0.05
                          }}
                        >
                          <ChartCard
                            chart={chart}
                            canEdit={canEditChart(chart)}
                            canRefresh={canRefreshChart(chart)}
                            canDelete={canDeleteChart(chart)}
                            canManageVisibility={canManageVisibility}
                            isReorderable={isReorderEnabled}
                            onTogglePdf={handleTogglePdf}
                            onRefreshChart={handleRefreshChart}
                            onCopyChart={handleCopyFromHeader}
                            onDeleteChart={handleDeleteChart}
                            isRefreshingChart={!!refreshingChartIds[chart.id]}
                            isDeletingChart={!!deletingChartIds[chart.id]}
                            isSyncing={reorderMutation.isPending}
                            onRankChange={handleRankChange}
                            onMoveUp={(id) => handleMoveBy(id, -1)}
                            onMoveDown={(id) => handleMoveBy(id, 1)}
                            copySignal={copySignals[chart.id] || 0}
                            index={idx}
                            totalCharts={filteredCharts.length}
                            onOpenStudio={handleOpenInStudio}
                          />
                        </motion.div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>

          {/* 📭 Empty State */}
          {filteredCharts.length === 0 && (
            <div className="py-32 text-center glass-card border-dashed border-border/20 bg-transparent animate-in zoom-in-95 duration-500">
              <Layers className="w-12 h-12 text-slate-700 mx-auto mb-4 opacity-20" />
              <h3 className="text-xl font-medium text-slate-500">No matching indicators</h3>
              <p className="text-slate-600 mt-2 text-sm font-light">No charts available with your current access.</p>
            </div>
          )}
          </div>
        )}
      </main>
      {/* 💾 Save Order Floating Bar */}
      <AnimatePresence>
        {isReorderEnabled && isOrderDirty && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ duration: 0.2 }}
            className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[200] flex items-center gap-3 px-4 py-2.5 bg-popover border border-amber-500/30 rounded-2xl shadow-2xl shadow-amber-500/10"
          >
            <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            <span className="text-[11px] font-mono text-amber-300 uppercase tracking-widest">Unsaved order changes</span>
            <div className="flex items-center gap-2 ml-2">
              <button
                onClick={handleResetOrder}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-white/10 text-slate-400 hover:text-white text-[10px] font-bold transition-colors"
              >
                <RotateCcw className="w-3 h-3" /> Reset
              </button>
              <button
                onClick={handleSaveOrder}
                disabled={reorderMutation.isPending}
                className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-amber-500 hover:bg-amber-400 text-black text-[10px] font-bold transition-colors disabled:opacity-50"
              >
                {reorderMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                Save Order
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {deleteTarget && (
          <motion.div
            className="fixed inset-0 z-[220] flex items-center justify-center bg-foreground/40 dark:bg-black/60 backdrop-blur-sm px-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setDeleteTarget(null)}
          >
            <motion.div
              className="w-full max-w-md rounded-2xl border border-rose-400/30 bg-popover shadow-2xl shadow-rose-900/20 p-5"
              initial={{ y: 16, scale: 0.97, opacity: 0 }}
              animate={{ y: 0, scale: 1, opacity: 1 }}
              exit={{ y: 10, scale: 0.98, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="text-sm font-semibold text-foreground mb-1">Delete Chart</div>
              <div className="text-xs text-muted-foreground mb-4">
                Delete <span className="text-rose-300 font-mono">{deleteTarget.name}</span>? This action cannot be undone.
              </div>
              <div className="flex items-center justify-end gap-2">
                <button
                  onClick={() => setDeleteTarget(null)}
                  className="px-3 py-1.5 rounded-lg border border-border/60 text-xs text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmDeleteChart}
                  className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold transition-colors"
                >
                  Delete
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
