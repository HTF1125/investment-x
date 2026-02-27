'use client';

import React, { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Layers,
  Plus, Eye, EyeOff, Loader2, Copy,
  Search,
  Info, RefreshCw, LayoutGrid, Trash2,
  X, Save, RotateCcw, FileDown,
  ChevronDown,
  FoldVertical,
  UnfoldVertical,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { apiFetch, apiFetchJson } from '@/lib/api';
import { type ChartStyle, CHART_STYLE_LABELS } from '@/lib/chartTheme';
import Chart from './Chart';
import CustomChartEditor from './CustomChartEditor';
import NavigatorShell from './NavigatorShell';

interface ChartMeta {
  id: string;
  name: string;
  category: string | null;
  description: string | null;
  updated_at: string | null;
  rank: number;
  public?: boolean;
  created_by_user_id?: string | null;
  created_by_email?: string | null;
  created_by_name?: string | null;
  code?: string;
  figure?: any; // Prefetched figure data
  chart_style?: string | null;
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
  onRankChange?: (id: string, newRank: number) => void;
  copySignal?: number;
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
  onRankChange,
  copySignal,
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
      <input
        type="number"
        value={localRank}
        onChange={(e) => setLocalRank(parseInt(e.target.value) || 1)}
        onBlur={handleRankSubmit}
        onKeyDown={(e) => e.key === 'Enter' && handleRankSubmit()}
        onClick={(e) => e.stopPropagation()}
        className={`w-5 bg-transparent focus:outline-none text-center text-[11px] font-mono tabular-nums shrink-0 appearance-none [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none transition-colors ${
          isModified ? 'text-amber-400' : 'text-muted-foreground/40 hover:text-muted-foreground/70'
        }`}
      />
    )
  );

  const renderName = () =>
    canEdit ? (
      <button
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); onOpenStudio?.(chart.id); }}
        className="text-xs font-medium text-foreground/90 leading-tight truncate hover:text-foreground transition-colors text-left"
        title="Edit in Studio"
      >
        {chart.name}
      </button>
    ) : (
      <span className="text-xs font-medium text-foreground/90 leading-tight truncate">
        {chart.name}
      </span>
    );

  const cardClassName = `bg-card border border-border/60 rounded-xl overflow-hidden flex flex-col group transition-all duration-200 hover:shadow-lg hover:shadow-black/5 dark:hover:shadow-black/30 hover:border-border relative h-full min-h-[380px]`;

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

  // Grid View Content
  return (
    <div className={cardClassName}>
      {/* Card Header */}
      <div className="px-4 py-2.5 flex items-center justify-between gap-2 border-b border-border/40">
        {/* LEFT: rank + name */}
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {renderRankInput()}
          {renderName()}
        </div>

        {/* RIGHT: action icons — uniform style */}
        <div className="flex items-center gap-0.5 shrink-0">

          {/* Visibility */}
          {canManageVisibility && (
            <button
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); onTogglePdf(chart.id, !chart.public); }}
              className="p-1 rounded transition-colors text-muted-foreground/40 hover:text-muted-foreground hover:bg-foreground/[0.06]"
              title={chart.public ? 'Public' : 'Private'}
            >
              {chart.public ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
            </button>
          )}

          {/* Refresh */}
          {canRefresh && (
            <button
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); onRefreshChart?.(chart.id); }}
              disabled={!!isRefreshingChart}
              className="p-1 rounded transition-colors text-muted-foreground/40 hover:text-muted-foreground hover:bg-foreground/[0.06] disabled:opacity-40"
              title="Refresh"
            >
              <RefreshCw className={`w-3 h-3 ${isRefreshingChart ? 'animate-spin' : ''}`} />
            </button>
          )}

          {/* Copy */}
          <button
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onCopyChart?.(chart.id); }}
            className="p-1 rounded transition-colors text-muted-foreground/40 hover:text-muted-foreground hover:bg-foreground/[0.06]"
            title="Copy image"
          >
            <Copy className="w-3 h-3" />
          </button>

          {/* Delete */}
          {canDelete && (
            <button
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); onDeleteChart?.(chart.id); }}
              disabled={!!isDeletingChart}
              className="p-1 rounded transition-colors text-muted-foreground/40 hover:text-muted-foreground hover:bg-foreground/[0.06] disabled:opacity-40"
              title="Delete"
            >
              <Trash2 className={`w-3 h-3 ${isDeletingChart ? 'animate-pulse' : ''}`} />
            </button>
          )}

          {/* Info — always last */}
          {(chart.description || chart.created_by_name || chart.created_by_email) && (
            <div className="relative" ref={infoRef}>
              <button
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); setInfoOpen(v => !v); }}
                className="p-1 rounded transition-colors text-muted-foreground/40 hover:text-muted-foreground hover:bg-foreground/[0.06]"
                title={chart.description || `by ${creatorLabel}`}
              >
                <Info className="w-3 h-3" />
              </button>
              <AnimatePresence>
                {infoOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: 4, scale: 0.96 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 4, scale: 0.96 }}
                    transition={{ duration: 0.12 }}
                    className="absolute right-0 top-full mt-1 w-52 bg-popover border border-border rounded-lg shadow-xl z-50 overflow-hidden"
                  >
                    {chart.description && (
                      <div className="px-3 py-2 text-[10px] text-muted-foreground leading-relaxed border-b border-border/50">
                        {chart.description}
                      </div>
                    )}
                    <div className="px-3 py-1.5 text-[9px] text-muted-foreground/70 font-mono">
                      <span>by {creatorLabel}</span>
                      {chart.updated_at && (
                        <span className="ml-2">{new Date(chart.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
        </div>
      </div>

      <div ref={cardRef} className="flex flex-col flex-1">
        {/* Chart Area — only render Plotly when in viewport */}
        <div className="bg-background relative w-full p-3 h-[290px] min-h-[290px] flex-1">
          {isInView ? (
            <Chart id={chart.id} initialFigure={chart.figure} chartStyle={(chart.chart_style ?? undefined) as ChartStyle | undefined} copySignal={copySignal} />
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
}

export default function DashboardGallery({ chartsByCategory }: DashboardGalleryProps) {
  const { user } = useAuth();
  const { theme, chartStyle, setChartStyle } = useTheme();
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
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  // Expanded by default for large screens
  const router = useRouter();
  const searchParams = useSearchParams();

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [collapsedSidebarCategories, setCollapsedSidebarCategories] = useState<Record<string, boolean>>({});
  const [activeStudioChartId, setActiveStudioChartId] = useState<string | null>(null);
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const syncSidebarForViewport = () => {
      if (window.innerWidth < 1024) setSidebarOpen(false);
    };

    syncSidebarForViewport();
    window.addEventListener('resize', syncSidebarForViewport);
    return () => window.removeEventListener('resize', syncSidebarForViewport);
  }, []);

  // Initial Sync from URL
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    const chartId = searchParams.get('chartId');
    const isNew = searchParams.get('new') === 'true';
    const isDesktop = typeof window !== 'undefined' && window.innerWidth >= 768;

    if (isNew) {
        setActiveStudioChartId('');
        setSidebarOpen(prev => prev || isDesktop);
    } else if (chartId) {
        setActiveStudioChartId(chartId);
        setQuickJumpId(chartId);
        setSidebarOpen(prev => prev || isDesktop);
    } else {
        setActiveStudioChartId(null);
    }
  }, [searchParams]); // intentionally omit sidebarOpen — we only auto-open on URL change, not on manual toggle

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

  const chartAnchorRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const mainScrollRef = useRef<HTMLElement>(null);
  const isAutoScrolling = useRef(false);

  // Export state
  const [exporting, setExporting] = useState(false);
  const [exportingHtml, setExportingHtml] = useState(false);

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
    } catch (err: any) {
      console.error('PDF export error:', err);
    } finally {
      queryClient.invalidateQueries({ queryKey: ['task-processes'] });
      setExporting(false);
    }
  };

  const handleExportHTML = async () => {
    if (exportingHtml) return;
    setExportingHtml(true);
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
    } catch (err: any) {
      console.error('HTML export error:', err);
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
      result = result.filter((c) => c.public !== false || isChartOwner(c));
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

  const allSidebarCategoriesCollapsed = useMemo(() => {
    if (groupedCharts.length === 0) return false;
    return groupedCharts.every(({ category }) => !!collapsedSidebarCategories[category]);
  }, [groupedCharts, collapsedSidebarCategories]);

  const toggleCollapseAllSidebarCategories = useCallback(() => {
    setCollapsedSidebarCategories((prev) => {
      const shouldCollapseAll = !groupedCharts.every(({ category }) => !!prev[category]);
      const next: Record<string, boolean> = {};
      for (const { category } of groupedCharts) {
        next[category] = shouldCollapseAll;
      }
      return next;
    });
  }, [groupedCharts]);

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
      return;
    }
    if (!quickJumpId || !filteredCharts.some((c) => c.id === quickJumpId)) {
      setQuickJumpId(filteredCharts[0].id);
    }
  }, [filteredCharts, quickJumpId]);

  const handleQuickJumpSelect = useCallback(
    (chartId: string) => {
      setQuickJumpId(chartId);

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
        body: JSON.stringify({ public: status })
      });
    },
    onMutate: async ({ id, status }) => {
      setLocalCharts(prev => prev.map(c => c.id === id ? { ...c, public: status } : c));
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
      <div className="p-4 md:p-6 space-y-6 min-h-[800px] animate-pulse">
        {/* Skeleton Stats */}
        <div className="flex items-center gap-6 pb-5 border-b border-border/40">
          {[80, 60, 72].map((w, i) => (
            <div key={i} className="space-y-1.5">
              <div className={`h-7 w-${w === 80 ? 12 : w === 60 ? 8 : 10} bg-foreground/5 rounded`} />
              <div className="h-3 w-16 bg-foreground/5 rounded" />
            </div>
          ))}
        </div>
        {/* Skeleton Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-5">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-card border border-border/60 rounded-xl h-[380px] flex flex-col overflow-hidden">
              <div className="h-10 border-b border-border/40 px-4 flex items-center gap-2">
                <div className="h-3 w-40 bg-foreground/5 rounded" />
              </div>
              <div className="flex-1 p-3">
                <div className="w-full h-full bg-foreground/[0.03] rounded-lg flex items-center justify-center">
                   <Loader2 className="w-5 h-5 text-muted-foreground/20 animate-spin" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }
  const sidebarContent = (
    <>
      {/* Search */}
      <div className="px-2 py-1.5 border-b border-border/40">
        <div className="flex items-center gap-1">
          <div className="relative group flex-1 min-w-0">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground/60 group-focus-within:text-foreground/60 transition-colors" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search..."
              className="w-full h-6 pl-6 pr-2 rounded border border-border/50 bg-background/50 text-[11px] outline-none focus:ring-1 focus:ring-sky-500/25 placeholder:text-muted-foreground/60"
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
          <button
            onClick={toggleCollapseAllSidebarCategories}
            disabled={groupedCharts.length === 0}
            className="shrink-0 h-6 w-6 inline-flex items-center justify-center rounded-md border border-border/50 text-muted-foreground/60 hover:text-foreground hover:bg-foreground/[0.05] disabled:opacity-40"
            title={allSidebarCategoriesCollapsed ? 'Expand all categories' : 'Collapse all categories'}
          >
            {allSidebarCategoriesCollapsed ? <UnfoldVertical className="w-3 h-3" /> : <FoldVertical className="w-3 h-3" />}
          </button>
        </div>
      </div>

      {/* Chart List */}
      <div className="flex-grow overflow-y-auto custom-scrollbar px-2 py-2 space-y-1">
        {groupedCharts.map(({ category, charts }) => {
          const collapsed = !!collapsedSidebarCategories[category];
          return (
            <div key={category} className="rounded-lg border border-border/40 overflow-hidden">
              <button
                onClick={() =>
                  setCollapsedSidebarCategories((prev) => ({ ...prev, [category]: !prev[category] }))
                }
                className="w-full px-2.5 py-1.5 bg-background/40 flex items-center justify-between text-left text-[10px] text-muted-foreground hover:text-foreground"
              >
                <span className="truncate">{category}</span>
                <span className="inline-flex items-center gap-1">
                  <span className="text-[9px]">{charts.length}</span>
                  <ChevronDown className={`w-3 h-3 transition-transform ${collapsed ? '-rotate-90' : 'rotate-0'}`} />
                </span>
              </button>
              {!collapsed && (
                <div className="px-1.5 py-1 space-y-px">
                  {charts.map((chart) => {
                    const isActive = chart.id === quickJumpId;
                    const idx = filteredCharts.findIndex((c) => c.id === chart.id);
                    return (
                      <button
                        key={chart.id}
                        onClick={() => handleQuickJumpSelect(chart.id)}
                        className={`w-full group relative flex items-center gap-2.5 px-2 py-1.5 rounded-md cursor-pointer transition-all duration-100 ${
                          isActive
                            ? 'bg-foreground/[0.07] text-foreground'
                            : 'text-muted-foreground hover:bg-foreground/[0.04] hover:text-foreground'
                        }`}
                      >
                        <span className={`text-[9px] font-mono tabular-nums shrink-0 w-4 text-right ${
                          isActive ? 'text-foreground/60' : 'text-muted-foreground/40'
                        }`}>
                          {idx + 1}
                        </span>
                        <div className="flex-1 min-w-0 flex flex-col items-start text-left">
                          <span className="text-[10px] font-medium leading-tight truncate w-full">
                            {chart.name || 'Untitled'}
                          </span>
                        </div>
                        {chart.public && (
                          <div className={`w-1 h-1 rounded-full shrink-0 ${isActive ? 'bg-emerald-500' : 'bg-emerald-500/40'}`} />
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
        {filteredCharts.length === 0 && (
          <div className="py-8 px-4 text-center">
            <p className="text-[10px] text-muted-foreground/50">No charts found</p>
          </div>
        )}
      </div>
    </>
  );

  return (
    <NavigatorShell
      sidebarOpen={sidebarOpen}
      onSidebarToggle={() => setSidebarOpen((o) => !o)}
      sidebarIcon={<LayoutGrid className="w-3.5 h-3.5 text-sky-400" />}
      sidebarLabel="Dashboard"
      sidebarHeaderActions={
        <>
          <button
            onClick={() => handleOpenInStudio(null)}
            className="w-5 h-5 rounded flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-foreground/8 transition-colors"
            title="New chart"
          >
            <Plus className="w-3 h-3" />
          </button>
        </>
      }
      sidebarContent={sidebarContent}
      topBarRight={
        <>
          <div className="flex items-center gap-0.5 border border-border/50 rounded p-0.5">
            {(Object.keys(CHART_STYLE_LABELS) as ChartStyle[]).map((s) => (
              <button
                key={s}
                onClick={() => setChartStyle(s)}
                className={`h-5 px-2 rounded text-[10px] font-medium transition-colors ${
                  chartStyle === s
                    ? 'bg-foreground text-background'
                    : 'text-muted-foreground hover:text-foreground hover:bg-foreground/[0.06]'
                }`}
              >
                {CHART_STYLE_LABELS[s]}
              </button>
            ))}
          </div>
          {canRefreshAllCharts && (
            <button
              onClick={handleRefreshAll}
              disabled={isRefreshing}
              className="h-6 px-2 rounded border border-border/50 text-[11px] font-medium text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 disabled:opacity-40 transition-colors"
            >
              <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          )}
          {isOwner && (
            <>
              <button
                onClick={handleExportPDF}
                disabled={exporting}
                className="h-6 px-2 rounded border border-border/50 text-[11px] font-medium text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 disabled:opacity-40 transition-colors"
              >
                <FileDown className={`w-3 h-3 ${exporting ? 'animate-pulse' : ''}`} />
                PDF
              </button>
              <button
                onClick={handleExportHTML}
                disabled={exportingHtml}
                className="h-6 px-2 rounded border border-rose-500/35 bg-rose-500/10 text-[11px] font-medium text-rose-300 hover:bg-rose-500/18 inline-flex items-center gap-1.5 disabled:opacity-40 transition-colors"
              >
                <FileDown className={`w-3 h-3 ${exportingHtml ? 'animate-pulse' : ''}`} />
                HTML
              </button>
            </>
          )}
        </>
      }
      mainScrollRef={mainScrollRef}
    >
      {/* Main Content */}
      {activeStudioChartId !== null ? (
        <div className="h-full w-full relative">
          <CustomChartEditor
            mode="integrated"
            initialChartId={activeStudioChartId === '' ? null : activeStudioChartId}
            onClose={handleCloseStudio}
          />
        </div>
      ) : (
        <div className="transition-all duration-300 p-4 md:p-6">
          {/* 🖼️ Grid Display — grouped by category */}
          <div className="space-y-8">
          {groupedCharts.map(({ category, charts: groupCharts }) => {
            return (
              <div key={category}>
                {/* Category Section Header */}
                {groupedCharts.length > 1 && (
                  <div className="flex items-center gap-3 mb-5 px-1">
                    <span className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-wider shrink-0">
                      {category}
                    </span>
                    <span className="text-[10px] text-muted-foreground/40 font-mono shrink-0">{groupCharts.length}</span>
                    <div className="h-px flex-1 bg-border/40" />
                  </div>
                )}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-5">
                  {groupCharts.map((chart, localIdx) => {
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
                          onRankChange={handleRankChange}
                          copySignal={copySignals[chart.id] || 0}
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

          {/* Empty State */}
          {filteredCharts.length === 0 && (
            <div className="py-32 text-center border border-dashed border-border/40 rounded-xl">
              <Layers className="w-8 h-8 text-muted-foreground/20 mx-auto mb-3" />
              <p className="text-sm font-medium text-muted-foreground/50">No indicators found</p>
              {searchQuery && <p className="text-xs text-muted-foreground/40 mt-1">Try a different search term</p>}
            </div>
          )}
        </div>
      )}

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
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-border/50 text-muted-foreground hover:text-foreground text-[10px] font-bold transition-colors"
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

      {/* 🗑️ Delete Confirm Modal */}
      <AnimatePresence>
        {deleteTarget && (
          <motion.div
            className="fixed inset-0 z-[220] flex items-center justify-center bg-foreground/40 dark:bg-black/60 px-4"
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
                  className="px-3 py-1.5 rounded-lg border border-border/60 text-xs text-muted-foreground hover:text-foreground hover:bg-foreground/[0.05] transition-colors"
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
    </NavigatorShell>
  );
}

