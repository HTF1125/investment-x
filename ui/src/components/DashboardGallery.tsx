'use client';

import React, { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Layers,
  Plus, Eye, EyeOff, Loader2, Copy,
  Search,
  Info, RefreshCw, LayoutGrid, Trash2,
  Save, RotateCcw,
  Rows2,
  FileText, FileCode,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { apiFetch, apiFetchJson, getDirectApiBase } from '@/lib/api';
import { useFocusTrap } from '@/hooks/useFocusTrap';
import Chart from './Chart';

type LayoutMode = 'grid' | 'stack';

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
  onEditInStudio?: (chartId: string) => void;
  expanded?: boolean;
  interactive?: boolean;
  onClick?: () => void;
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
  onEditInStudio,
  expanded = false,
  interactive = true,
  onClick,
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
        aria-label={`Rank for ${chart.name || 'chart'}`}
        className={`w-4 bg-transparent focus:outline-none text-center text-[9px] font-mono tabular-nums shrink-0 appearance-none [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none transition-colors ${
          isModified ? 'text-primary' : 'text-muted-foreground/40 hover:text-muted-foreground/70'
        }`}
      />
    )
  );

  const renderName = () =>
    canEdit ? (
      <button
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); onEditInStudio?.(chart.id); }}
        className="text-[10px] font-medium text-foreground/80 leading-none truncate hover:text-foreground transition-colors text-left"
        title="Edit in Studio"
      >
        {chart.name}
      </button>
    ) : (
      <span className="text-[10px] font-medium text-foreground/80 leading-none truncate">
        {chart.name}
      </span>
    );

  const cardClassName = `bg-card border border-border/30 rounded-[var(--radius)] overflow-hidden flex flex-col group transition-all duration-200 hover:border-border/50 relative focus-within:ring-1 focus-within:ring-primary/20 ${expanded ? 'h-full' : 'h-full min-h-[260px] max-h-[400px]'}`;

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
    <article className={cardClassName} aria-label={`Chart: ${chart.name || 'Untitled'}`}>
      {/* Card Header */}
      <div className="px-2.5 py-1 flex items-center justify-between gap-1.5 border-b border-border/25">
        {/* LEFT: rank + name */}
        <div className="flex items-center gap-1.5 min-w-0 flex-1">
          {renderRankInput()}
          {renderName()}
        </div>

        {/* RIGHT: always-visible indicators + hover-reveal actions */}
        <div className="flex items-center shrink-0">
          <div className="flex items-center gap-0 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
            {canManageVisibility && (
              <button
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); onTogglePdf(chart.id, !chart.public); }}
                className="p-1 rounded transition-colors text-muted-foreground/40 hover:text-muted-foreground hover:bg-primary/10"
                title={chart.public ? 'Public' : 'Private'}
                aria-label={chart.public ? 'Set private' : 'Set public'}
              >
                {chart.public ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
              </button>
            )}
            {canRefresh && (
              <button
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); onRefreshChart?.(chart.id); }}
                disabled={!!isRefreshingChart}
                className="p-1 rounded transition-colors text-muted-foreground/40 hover:text-muted-foreground hover:bg-primary/10 disabled:opacity-40"
                title="Refresh"
                aria-label="Refresh chart"
              >
                <RefreshCw className={`w-3 h-3 ${isRefreshingChart ? 'animate-spin' : ''}`} />
              </button>
            )}
            <button
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); onCopyChart?.(chart.id); }}
              className="p-1 rounded transition-colors text-muted-foreground/40 hover:text-muted-foreground hover:bg-primary/10"
              title="Copy image"
              aria-label="Copy chart image"
            >
              <Copy className="w-3 h-3" />
            </button>
            {canDelete && (
              <button
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); onDeleteChart?.(chart.id); }}
                disabled={!!isDeletingChart}
                className="p-1 rounded transition-colors text-muted-foreground/40 hover:text-muted-foreground hover:bg-primary/10 disabled:opacity-40"
                title="Delete"
                aria-label="Delete chart"
              >
                <Trash2 className={`w-3 h-3 ${isDeletingChart ? 'animate-pulse' : ''}`} />
              </button>
            )}
            {(chart.description || chart.created_by_name || chart.created_by_email) && (
              <div className="relative" ref={infoRef}>
                <button
                  onClick={(e) => { e.preventDefault(); e.stopPropagation(); setInfoOpen(v => !v); }}
                  className="p-1 rounded transition-colors text-muted-foreground/40 hover:text-muted-foreground hover:bg-primary/10"
                  title={chart.description || `by ${creatorLabel}`}
                  aria-label="Chart info"
                  aria-expanded={infoOpen}
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
                      className="absolute right-0 top-full mt-1 w-52 bg-popover border border-border rounded-lg shadow-md z-50 overflow-hidden"
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
      </div>

      <div
        ref={cardRef}
        className={`flex flex-col flex-1 min-h-0${onClick ? ' cursor-pointer' : ''}`}
        onClick={onClick}
        tabIndex={onClick ? 0 : undefined}
        role={onClick ? 'button' : undefined}
        aria-label={onClick ? `View ${chart.name || 'chart'}` : undefined}
        onKeyDown={onClick ? (e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(); } } : undefined}
      >
        {/* Chart Area — only render Plotly when in viewport */}
        <div className={`bg-background relative w-full p-1.5 ${expanded ? 'flex-1 min-h-0' : 'flex-1 min-h-[160px]'}`}>
          {isInView ? (
            <Chart
              id={chart.id}
              initialFigure={chart.figure}
              copySignal={copySignal}
              interactive={interactive}
            />
          ) : (
            <div className="relative h-full w-full overflow-hidden rounded-lg border border-border/20 bg-background/90">
              <motion.div
                className="absolute inset-y-0 -left-1/3 w-1/3 bg-gradient-to-r from-transparent via-primary/5 to-transparent"
                animate={{ x: ['0%', '360%'] }}
                transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              />
              <div className="absolute inset-0 p-3 flex flex-col justify-between">
                <div className="space-y-2">
                  <div className="h-3 w-28 rounded bg-primary/10 animate-pulse" />
                  <div className="h-2 w-16 rounded bg-muted/50 animate-pulse" />
                </div>
                <div className="grid grid-cols-8 gap-1 items-end h-20">
                  {Array.from({ length: 8 }).map((_, i) => (
                    <div
                      key={i}
                      className="rounded-sm bg-primary/15 animate-pulse"
                      style={{ height: `${25 + ((i * 13) % 60)}%`, animationDelay: `${i * 80}ms` }}
                    />
                  ))}
                </div>
                <div className="flex items-center justify-center">
                  <Loader2 className="w-4 h-4 text-primary/20 animate-spin" />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </article>
  );
});


function DeleteConfirmInner({
  deleteTarget,
  onCancel,
  onConfirm,
}: {
  deleteTarget: { id: string; name: string };
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
      <div id="delete-modal-title" className="text-sm font-semibold text-foreground mb-1">Delete Chart</div>
      <div className="text-xs text-muted-foreground mb-4">
        Delete <span className="text-rose-400 font-mono font-medium">{deleteTarget.name}</span>? This action cannot be undone.
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

interface DashboardGalleryProps {
  chartsByCategory: Record<string, ChartMeta[]>;
}

export default function DashboardGallery({ chartsByCategory }: DashboardGalleryProps) {
  const { user } = useAuth();
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
  const router = useRouter();

  // Performance Optimized State
  const [localCharts, setLocalCharts] = useState<ChartMeta[]>([]);
  const [originalCharts, setOriginalCharts] = useState<ChartMeta[]>([]);
  const [refreshingChartIds, setRefreshingChartIds] = useState<Record<string, boolean>>({});
  const [deletingChartIds, setDeletingChartIds] = useState<Record<string, boolean>>({});
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
  const [copySignals, setCopySignals] = useState<Record<string, number>>({});

  const [mounted, setMounted] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState<string>('all');

  // Layout mode (grid / stack) — gracefully handle stored 'single' from before
  const [layoutMode, setLayoutMode] = useState<LayoutMode>(() => {
    if (typeof window === 'undefined') return 'grid';
    const stored = localStorage.getItem('dashboard-layout-mode');
    if (stored === 'grid' || stored === 'stack') return stored;
    return 'grid';
  });

  // Stack mode
  const [stackChartCount, setStackChartCount] = useState<2 | 3 | 4>(2);
  const [stackHeights, setStackHeights] = useState<number[]>([50, 50]);
  const isStackDragging = useRef(false);
  const stackDragStartY = useRef(0);
  const stackDragStartHeights = useRef<number[]>([]);
  const stackDragPaneIdx = useRef(0);
  const stackContainerRef = useRef<HTMLDivElement>(null);

  // Persist layout mode
  useEffect(() => {
    if (typeof window !== 'undefined') localStorage.setItem('dashboard-layout-mode', layoutMode);
  }, [layoutMode]);

  // Reset stack heights when count changes
  useEffect(() => {
    const eq = 100 / stackChartCount;
    setStackHeights(Array.from({ length: stackChartCount }, () => eq));
  }, [stackChartCount]);

  // Navigate to Studio for editing
  const handleEditInStudio = useCallback((chartId: string) => {
    router.push(`/studio?chartId=${chartId}`);
  }, [router]);

  // Navigate to Studio for new chart
  const handleNewChart = useCallback(() => {
    router.push('/studio?new=true');
  }, [router]);

  const mainScrollRef = useRef<HTMLDivElement>(null);

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

  const triggerBlobDownload = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  };

  const handleExportPDF = async () => {
    if (exporting) return;
    setExporting(true);
    try {
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('items', JSON.stringify([]));
      formData.append('theme', 'light');
      const res = await fetch(`${getDirectApiBase()}/api/custom/pdf`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        credentials: 'include',
        body: formData,
      });
      if (!res.ok) throw new Error(await res.text());
      const blob = await res.blob();
      triggerBlobDownload(blob, `InvestmentX_Report_${new Date().toISOString().slice(0, 10)}.pdf`);
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
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('items', JSON.stringify([]));
      formData.append('theme', 'light');
      const res = await fetch(`${getDirectApiBase()}/api/custom/html`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        credentials: 'include',
        body: formData,
      });
      if (!res.ok) throw new Error(await res.text());
      const blob = await res.blob();
      triggerBlobDownload(blob, `InvestmentX_Portfolio_${new Date().toISOString().slice(0, 10)}.html`);
    } catch (err: any) {
      console.error('HTML export error:', err);
    } finally {
      queryClient.invalidateQueries({ queryKey: ['task-processes'] });
      setExportingHtml(false);
    }
  };

  // Prop to Local State Sync
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

  // Filter & Sort charts (Memoized)
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

  // Category + search filtering
  const filteredCharts = useMemo(() => {
    if (activeCategory === 'all') return allFilteredCharts;
    return allFilteredCharts.filter(c => (c.category || 'Uncategorized') === activeCategory);
  }, [allFilteredCharts, activeCategory]);

  // Group ALL filtered charts by category (for tab labels and "All" view)
  const groupedCharts = useMemo(() => {
    const groups = new Map<string, ChartMeta[]>();
    for (const chart of allFilteredCharts) {
      const cat = chart.category || 'Uncategorized';
      if (!groups.has(cat)) groups.set(cat, []);
      groups.get(cat)!.push(chart);
    }
    return Array.from(groups.entries()).map(([category, charts]) => ({ category, charts }));
  }, [allFilteredCharts]);

  // Derive category list for tabs
  const categories = useMemo(() => groupedCharts.map(g => g.category), [groupedCharts]);


  // Keyboard navigation
  const keyNavHandlerRef = useRef<(e: KeyboardEvent) => void>(() => {});
  useEffect(() => {
    keyNavHandlerRef.current = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (
        ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) ||
        target.contentEditable === 'true' ||
        target.closest('.monaco-editor')
      ) return;
    };
  }, [filteredCharts, layoutMode]);

  useEffect(() => {
    const h = (e: KeyboardEvent) => keyNavHandlerRef.current(e);
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, []);

  // Stack drag-resize
  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!isStackDragging.current || !stackContainerRef.current) return;
      const totalH = stackContainerRef.current.getBoundingClientRect().height;
      if (totalH === 0) return;
      const delta = ((e.clientY - stackDragStartY.current) / totalH) * 100;
      const h = stackDragStartHeights.current;
      const idx = stackDragPaneIdx.current;
      const MIN = 15;
      let above = Math.max(MIN, h[idx] + delta);
      let below = Math.max(MIN, h[idx + 1] - delta);
      // Re-clamp the other side if clamping caused overflow
      if (above + below !== h[idx] + h[idx + 1]) {
        const total = h[idx] + h[idx + 1];
        above = Math.min(total - MIN, above);
        below = total - above;
      }
      const newH = [...h];
      newH[idx] = above;
      newH[idx + 1] = below;
      setStackHeights(newH);
    };
    const onUp = () => {
      if (isStackDragging.current) {
        isStackDragging.current = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      }
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, []);

  const startStackDrag = useCallback((idx: number, e: React.MouseEvent) => {
    isStackDragging.current = true;
    stackDragStartY.current = e.clientY;
    stackDragStartHeights.current = [...stackHeights];
    stackDragPaneIdx.current = idx;
    document.body.style.cursor = 'row-resize';
    document.body.style.userSelect = 'none';
    e.preventDefault();
  }, [stackHeights]);


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

  // Stable Handlers
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
    onSuccess: (data: any, chartId) => {
      if (data?.figure) {
        queryClient.setQueryData(['chart-figure', chartId], data.figure);
      } else {
        queryClient.invalidateQueries({ queryKey: ['chart-figure', chartId], exact: true });
      }
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
      <div className="p-2 md:p-3 space-y-4 min-h-[600px] animate-pulse w-full">
        {/* Skeleton Grid */}
        <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))' }}>
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-card border border-border/30 rounded-[var(--radius)] h-[260px] max-h-[400px] flex flex-col overflow-hidden">
              <div className="h-6 border-b border-border/25 px-2.5 flex items-center gap-1.5">
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

  const displayGroups = activeCategory === 'all'
    ? groupedCharts
    : [{ category: activeCategory, charts: filteredCharts }];

  return (
    <div className="h-[calc(100vh-48px)] flex flex-col overflow-hidden">
      {/* Combined tab bar: category tabs | search | layout + actions */}
      <div className="px-4 sm:px-5 lg:px-6 border-b border-border/25 shrink-0">
        <div className="flex items-center gap-2 -mb-px">
          {/* Category tabs */}
          <div className="flex gap-0.5 overflow-x-auto no-scrollbar flex-1 min-w-0">
            <button
              onClick={() => setActiveCategory('all')}
              className={`tab-link ${activeCategory === 'all' ? 'active' : ''}`}
            >
              All
              <span className="ml-1 text-[9px] text-muted-foreground/40 font-mono">{allFilteredCharts.length}</span>
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
                  <span className="ml-1 text-[9px] text-muted-foreground/40 font-mono">{count}</span>
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

          {/* Layout mode buttons */}
          {([
            { mode: 'grid' as LayoutMode, icon: <LayoutGrid className="w-3 h-3" />, label: 'Grid' },
            { mode: 'stack' as LayoutMode, icon: <Rows2 className="w-3 h-3" />, label: 'Stack' },
          ]).map(({ mode, icon, label }) => (
            <button
              key={mode}
              onClick={() => setLayoutMode(mode)}
              className={`w-5 h-5 rounded flex items-center justify-center transition-colors ${
                layoutMode === mode
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground hover:bg-primary/10'
              }`}
              title={`${label} mode`}
              aria-label={`${label} mode`}
              aria-pressed={layoutMode === mode}
            >
              {icon}
            </button>
          ))}

          {/* Stack count */}
          {layoutMode === 'stack' && (
            <>
              <div className="w-px h-3 bg-border/40 mx-0.5" />
              {([2, 3, 4] as const).map(n => (
                <button
                  key={n}
                  onClick={() => setStackChartCount(n)}
                  className={`w-5 h-5 rounded text-[10px] font-mono transition-colors ${
                    stackChartCount === n
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:text-foreground hover:bg-primary/10'
                  }`}
                  title={`${n} panes`}
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
            onClick={handleNewChart}
            className="w-5 h-5 rounded flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-primary/10 transition-colors"
            title="New chart"
            aria-label="New chart"
          >
            <Plus className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Main content */}
      <div ref={mainScrollRef} className={`flex-1 min-h-0 ${layoutMode === 'grid' ? 'overflow-y-auto' : 'overflow-hidden'}`}>
      {layoutMode === 'stack' ? (
        /* STACK MODE */
        <div ref={stackContainerRef} className="h-full flex flex-col overflow-hidden max-w-[1400px] mx-auto w-full">
          {filteredCharts.slice(0, stackChartCount).map((chart, paneIdx) => (
            <React.Fragment key={chart.id}>
              <div
                className="overflow-hidden flex flex-col"
                style={{ height: `${stackHeights[paneIdx] ?? (100 / stackChartCount)}%` }}
              >
                <ChartCard
                  chart={chart}
                  expanded={true}
                  canEdit={canEditChart(chart)}
                  canRefresh={canRefreshChart(chart)}
                  canDelete={canDeleteChart(chart)}
                  canManageVisibility={canManageVisibility}
                  isReorderable={false}
                  onTogglePdf={handleTogglePdf}
                  onRefreshChart={handleRefreshChart}
                  onCopyChart={handleCopyFromHeader}
                  onDeleteChart={handleDeleteChart}
                  isRefreshingChart={!!refreshingChartIds[chart.id]}
                  isDeletingChart={!!deletingChartIds[chart.id]}
                  onRankChange={handleRankChange}
                  copySignal={copySignals[chart.id] || 0}
                  onEditInStudio={handleEditInStudio}
                />
              </div>
              {paneIdx < Math.min(stackChartCount, filteredCharts.length) - 1 && (
                <div
                  className="h-1 shrink-0 cursor-row-resize bg-border/40 hover:bg-primary/40 active:bg-primary/60 transition-colors"
                  onMouseDown={(e) => startStackDrag(paneIdx, e)}
                />
              )}
            </React.Fragment>
          ))}
        </div>
      ) : (
        <div className="transition-all duration-300 p-2 md:p-3 w-full">
          {/* Grid Display — grouped by category */}
          <div className="space-y-4">
          {displayGroups.map(({ category, charts: groupCharts }) => (
              <div key={category}>
                {/* Category Section Header — only when showing all categories */}
                {displayGroups.length > 1 && (
                  <div className="flex items-center gap-2 mb-2 px-0.5">
                    <span className="text-[9px] font-semibold text-muted-foreground/50 uppercase tracking-[0.15em] shrink-0">
                      {category}
                    </span>
                    <span className="text-[9px] text-muted-foreground/30 font-mono shrink-0 tabular-nums">{groupCharts.length}</span>
                    <div className="h-px flex-1 bg-border/30" />
                  </div>
                )}
                <div className="grid gap-3 [&>*]:max-h-[400px]" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))' }}>
                  {groupCharts.map((chart) => (
                      <div
                        key={chart.id}
                        id={`chart-anchor-${chart.id}`}
                        className="h-full flex flex-col"
                        style={{ contentVisibility: 'auto', containIntrinsicSize: '0 300px' }}
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
                          onEditInStudio={handleEditInStudio}
                        />
                      </div>
                    ))}
                </div>
              </div>
            ))}
          </div>

          {/* Empty State */}
          {filteredCharts.length === 0 && (
            <div className="py-20 text-center border border-dashed border-border/30 rounded-lg">
              <Layers className="w-8 h-8 text-muted-foreground/20 mx-auto mb-3" />
              <p className="text-sm font-medium text-muted-foreground/50">No indicators found</p>
              {searchQuery && <p className="text-xs text-muted-foreground/40 mt-1">Try a different search term</p>}
            </div>
          )}
        </div>
      )}

      {/* Save Order Floating Bar */}
      <AnimatePresence>
        {isReorderEnabled && isOrderDirty && (
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
                onClick={handleResetOrder}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-[var(--radius)] border border-border/50 text-muted-foreground hover:text-foreground text-[10px] font-semibold transition-colors"
              >
                <RotateCcw className="w-3 h-3" /> Reset
              </button>
              <button
                onClick={handleSaveOrder}
                disabled={reorderMutation.isPending}
                className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-primary/15 border border-primary/30 hover:bg-primary/25 text-primary text-[10px] font-bold transition-colors disabled:opacity-50"
              >
                {reorderMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                Save Order
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Delete Confirm Modal */}
      <AnimatePresence>
        {deleteTarget && (
          <motion.div
            className="fixed inset-0 z-[220] flex items-center justify-center bg-black/50 backdrop-blur-sm px-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setDeleteTarget(null)}
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-modal-title"
          >
            <DeleteConfirmInner
              deleteTarget={deleteTarget}
              onCancel={() => setDeleteTarget(null)}
              onConfirm={confirmDeleteChart}
            />
          </motion.div>
        )}
      </AnimatePresence>
      </div>
    </div>
  );
}
