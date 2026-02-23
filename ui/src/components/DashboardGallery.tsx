'use client';

import React, { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { 
  Layers, 
  Plus, Edit2, CheckCircle2, Eye, EyeOff, Loader2, RotateCcw, Copy,
  MoreVertical, ArrowUp, ArrowDown,
  FileDown, Monitor, Check, Info, RefreshCw, LayoutGrid, List as ListIcon, Trash2,
  ChevronDown
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
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
  const creatorLabel = chart.created_by_name || chart.created_by_email || 'Unknown';

  const handleRankSubmit = () => {
    if (isModified) {
      onRankChange?.(chart.id, localRank - 1);
    }
  };

  const renderRankInput = () => (
    isReorderable && (
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
          className="p-1 rounded hover:bg-white/5 text-slate-500 hover:text-sky-300 transition-colors"
          title="Move up"
          aria-label="Move chart up"
          disabled={index === 0}
        >
          <ArrowUp className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={(e) => { e.preventDefault(); e.stopPropagation(); onMoveDown?.(chart.id); }}
          className="p-1 rounded hover:bg-white/5 text-slate-500 hover:text-sky-300 transition-colors"
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

    const className = `glass-card overflow-hidden flex flex-col group transition-all duration-300 hover:border-sky-500/30 hover:shadow-sky-500/5 relative h-full min-h-[380px]`;

  // Grid View Content (Hardcoded)
  return (
    <div className={className}>
      {/* Card Header */}
      <div className="px-3 sm:px-4 py-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-border/50 bg-card/10 relative">
         <div className="flex flex-wrap items-center gap-2 sm:gap-3 min-w-0 z-10 w-full sm:w-auto">
            {renderRankInput()}
            {renderOrderButtons()}
            {renderVisibilityToggle()}
            {renderName()}
         </div>

         <div className="flex items-center justify-between sm:justify-end gap-2 sm:gap-3 w-full sm:w-auto shrink-0">
            {(canRefresh || canDelete || !!onCopyChart) && (
              <div className="flex items-center gap-1">
                {canRefresh && (
                  <button
                    onClick={(e) => { e.preventDefault(); e.stopPropagation(); onRefreshChart?.(chart.id); }}
                    disabled={!!isRefreshingChart}
                    className="p-1 rounded hover:bg-white/5 text-slate-500 hover:text-sky-300 transition-colors disabled:opacity-50"
                    title="Rerun and save chart"
                    aria-label="Refresh chart"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isRefreshingChart ? 'animate-spin text-sky-400' : ''}`} />
                  </button>
                )}
                <button
                  onClick={(e) => { e.preventDefault(); e.stopPropagation(); onCopyChart?.(chart.id); }}
                  className="p-1 rounded hover:bg-white/5 text-slate-500 hover:text-sky-300 transition-colors"
                  title="Copy chart image"
                  aria-label="Copy chart"
                >
                  <Copy className="w-3.5 h-3.5" />
                </button>
                {canDelete && (
                  <button
                    onClick={(e) => { e.preventDefault(); e.stopPropagation(); onDeleteChart?.(chart.id); }}
                    disabled={!!isDeletingChart}
                    className="p-1 rounded hover:bg-rose-500/10 text-slate-500 hover:text-rose-400 transition-colors disabled:opacity-50"
                    title="Delete chart"
                    aria-label="Delete chart"
                  >
                    <Trash2 className={`w-3.5 h-3.5 ${isDeletingChart ? 'animate-pulse text-rose-400' : ''}`} />
                  </button>
                )}
              </div>
            )}
            {chart.description && (
              <div className="relative group/tip">
                <Info className="w-3.5 h-3.5 text-slate-600 hover:text-sky-400 transition-colors cursor-help" />
                <div className="absolute right-0 top-full mt-1 w-56 px-3 py-2 bg-popover border border-border rounded-lg text-[10px] text-muted-foreground leading-relaxed opacity-0 invisible group-hover/tip:opacity-100 group-hover/tip:visible transition-all z-50 shadow-xl">
                  {chart.description}
                </div>
              </div>
            )}
            <div className="text-[9px] text-slate-600 font-mono hidden sm:flex items-center gap-3">
                <span className="max-w-[180px] truncate" title={`Created by ${creatorLabel}`}>
                  by {creatorLabel}
                </span>
                {isSyncing && <Loader2 className="w-3 h-3 animate-spin text-indigo-500" />}
                {chart.updated_at ? new Date(chart.updated_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '---'}
            </div>
         </div>
      </div>

      <div ref={cardRef} className="flex flex-col flex-1">
        {/* Chart Area — only render Plotly when in viewport */}
        <div className="bg-slate-950/20 relative w-full p-4 h-[290px] min-h-[290px] flex-1">
          {isInView ? (
            <Chart id={chart.id} initialFigure={chart.figure} copySignal={copySignal} />
          ) : (
            <div className="relative h-full w-full overflow-hidden rounded-lg border border-sky-500/10 bg-[linear-gradient(120deg,rgba(8,12,20,0.95),rgba(10,16,28,0.95),rgba(8,12,20,0.95))]">
              <motion.div
                className="absolute inset-y-0 -left-1/3 w-1/3 bg-gradient-to-r from-transparent via-sky-400/10 to-transparent"
                animate={{ x: ['0%', '360%'] }}
                transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              />
              <div className="absolute inset-0 p-6 flex flex-col justify-between">
                <div className="space-y-3">
                  <div className="h-4 w-40 rounded bg-sky-500/15 animate-pulse" />
                  <div className="h-3 w-24 rounded bg-slate-500/20 animate-pulse" />
                </div>
                <div className="grid grid-cols-8 gap-2 items-end h-32">
                  {Array.from({ length: 8 }).map((_, i) => (
                    <div
                      key={i}
                      className="rounded-sm bg-cyan-500/20 animate-pulse"
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
  categories: string[];
  chartsByCategory: Record<string, ChartMeta[]>;
  onOpenStudio?: (chartId: string | null) => void;
}

export default function DashboardGallery({ chartsByCategory, onOpenStudio }: DashboardGalleryProps) {
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

  // ⚡ Performance Optimized State
  const [localCharts, setLocalCharts] = useState<ChartMeta[]>([]);
  const [originalCharts, setOriginalCharts] = useState<ChartMeta[]>([]);
  const [refreshingChartIds, setRefreshingChartIds] = useState<Record<string, boolean>>({});
  const [deletingChartIds, setDeletingChartIds] = useState<Record<string, boolean>>({});
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
  const [copySignals, setCopySignals] = useState<Record<string, number>>({});

  const [mounted, setMounted] = useState(false);
  const [showActionMenu, setShowActionMenu] = useState(false);
  const [quickJumpId, setQuickJumpId] = useState('');
  const [showQuickJumpMenu, setShowQuickJumpMenu] = useState(false);
  
  const actionRef = useRef<HTMLDivElement>(null);
  const quickJumpRef = useRef<HTMLDivElement>(null);
  const chartAnchorRefs = useRef<Record<string, HTMLDivElement | null>>({});

  // Close menus on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (actionRef.current && !actionRef.current.contains(event.target as Node)) {
        setShowActionMenu(false);
      }
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
      queryClient.invalidateQueries({ queryKey: ['task-processes'] });
      const res = await apiFetch('/api/custom/pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
      queryClient.invalidateQueries({ queryKey: ['task-processes'] });
      setExporting(false);
    }
  };

  const handleExportHTML = async () => {
    if (exportingHtml) return;
    setExportingHtml(true);
    setExportHtmlStatus('idle');
    try {
      queryClient.invalidateQueries({ queryKey: ['task-processes'] });
      const res = await apiFetch('/api/custom/html', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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

  // 🔍 Filter & Sort charts (Memoized)
  const allFilteredCharts = useMemo(() => {
    let result = [...localCharts];

    if (!isOwner && !isAdminRole) {
      result = result.filter((c) => c.export_pdf !== false || isChartOwner(c));
    }
    
    return result;
  }, [localCharts, isOwner, isAdminRole, isChartOwner]);

  // No pagination: render all charts at once
  const filteredCharts = allFilteredCharts;
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
    const stickyOffset = 120;
    const y = target.getBoundingClientRect().top + window.scrollY - stickyOffset;
    window.scrollTo({ top: Math.max(0, y), behavior: 'smooth' });
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
      scrollToChart(chartId);
    },
    [scrollToChart]
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
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      queryClient.invalidateQueries({ queryKey: ['custom-charts'] });
      queryClient.invalidateQueries({ queryKey: ['chart-figure', chartId], exact: false });
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
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
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
    <div className="space-y-6 min-h-[800px]">
      {/* 🧭 Fixed Navigator Controls */}
      <div
        className="fixed top-12 left-0 right-0 z-50 border-b border-slate-200/80 dark:border-border/50 shadow-2xl bg-white/95 dark:bg-black/95 backdrop-blur-md"
      >
        <div className="mx-auto w-full max-w-[1800px] px-2 sm:px-4 md:px-6 py-2.5 md:py-3">
          <div className="flex items-center gap-2 sm:gap-3 md:gap-4">
            <div className="min-w-0 flex-1 rounded-2xl border border-sky-300/70 dark:border-sky-500/20 bg-gradient-to-r from-sky-100/85 via-indigo-100/65 to-cyan-100/85 dark:from-sky-500/10 dark:via-indigo-500/10 dark:to-cyan-500/10 px-2.5 sm:px-3 py-2.5 flex items-center gap-2 shadow-lg shadow-sky-900/5 dark:shadow-black/20">
              <div className="hidden lg:flex items-center gap-2 text-[10px] uppercase tracking-[0.16em] text-sky-700 dark:text-sky-300 font-bold shrink-0">
                <ListIcon className="w-3.5 h-3.5" />
                Navigator
              </div>
              <button
                type="button"
                onClick={() => {
                  setShowQuickJumpMenu(false);
                  handleQuickJumpStep(-1);
                }}
                disabled={quickJumpIndex <= 0}
                className="px-2.5 py-1.5 rounded-lg border border-sky-300/80 dark:border-sky-500/25 bg-white/90 dark:bg-black/20 text-[11px] text-slate-700 dark:text-slate-300 hover:text-sky-900 dark:hover:text-white hover:bg-sky-100/80 dark:hover:bg-sky-500/10 disabled:opacity-55 disabled:cursor-not-allowed transition-colors"
              >
                Prev
              </button>
              <div className="relative min-w-0 flex-1" ref={quickJumpRef}>
                <button
                  type="button"
                  onClick={() => setShowQuickJumpMenu((prev) => !prev)}
                  className={`w-full flex items-center justify-between gap-2 px-3 py-1.5 rounded-xl border text-[11px] transition-all ${
                    showQuickJumpMenu
                      ? 'border-sky-500/60 bg-white text-slate-900 shadow-lg shadow-sky-200/60 dark:border-sky-400/50 dark:bg-sky-500/10 dark:text-white dark:shadow-sky-500/20'
                      : 'border-sky-300/80 bg-white/90 text-slate-800 hover:bg-sky-100/70 dark:border-sky-500/25 dark:bg-black/25 dark:text-slate-100 dark:hover:bg-sky-500/10'
                  }`}
                >
                  <span className="truncate">{quickJumpLabel}</span>
                  <ChevronDown className={`w-3.5 h-3.5 shrink-0 transition-transform ${showQuickJumpMenu ? 'rotate-180 text-sky-700 dark:text-sky-300' : 'text-slate-500 dark:text-slate-400'}`} />
                </button>
                <AnimatePresence>
                  {showQuickJumpMenu && (
                    <motion.div
                      initial={{ opacity: 0, y: 8, scale: 0.98 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 6, scale: 0.98 }}
                      className="absolute left-0 right-0 top-full mt-2 z-50 rounded-xl border border-sky-300/80 dark:border-sky-500/25 bg-white/95 dark:bg-slate-950/95 backdrop-blur-md shadow-2xl shadow-slate-900/10 dark:shadow-black/40 p-1.5"
                    >
                      <div className="max-h-[320px] overflow-y-auto custom-scrollbar pr-1">
                        {filteredCharts.map((chart, idx) => {
                          const isActive = chart.id === quickJumpId;
                          return (
                            <button
                              key={chart.id}
                              type="button"
                              onClick={() => handleQuickJumpSelect(chart.id)}
                              className={`w-full text-left px-2.5 py-2 rounded-lg text-[11px] transition-colors ${
                                isActive
                                  ? 'bg-sky-100 text-sky-900 border border-sky-300 dark:bg-sky-500/20 dark:text-sky-200 dark:border-sky-400/30'
                                  : 'text-slate-700 hover:bg-sky-50 dark:text-slate-200 dark:hover:bg-white/5'
                              }`}
                            >
                              <span className="font-semibold text-sky-700 dark:text-sky-300/90 mr-1">{idx + 1}.</span>
                              <span className="align-middle">{chart.name || `Chart ${idx + 1}`}</span>
                            </button>
                          );
                        })}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
              <button
                type="button"
                onClick={() => {
                  setShowQuickJumpMenu(false);
                  handleQuickJumpStep(1);
                }}
                disabled={quickJumpIndex < 0 || quickJumpIndex >= filteredCharts.length - 1}
                className="px-2.5 py-1.5 rounded-lg border border-sky-300/80 dark:border-sky-500/25 bg-white/90 dark:bg-black/20 text-[11px] text-slate-700 dark:text-slate-300 hover:text-sky-900 dark:hover:text-white hover:bg-sky-100/80 dark:hover:bg-sky-500/10 disabled:opacity-55 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
              <div className="text-[10px] font-mono text-slate-700 dark:text-slate-300/80 shrink-0 rounded-md px-2 py-1 bg-white/90 dark:bg-black/20 border border-sky-300/70 dark:border-sky-500/15">
                {quickJumpIndex >= 0 ? `${quickJumpIndex + 1}/${filteredCharts.length}` : `0/${filteredCharts.length}`}
              </div>
            </div>

            <div className="flex items-center justify-end gap-1.5 sm:gap-3 shrink-0 w-auto">
              {isReorderEnabled && isOrderDirty && (
                <div className="animate-in fade-in slide-in-from-right-4 duration-500">
                  <button
                    onClick={handleSaveOrder}
                    disabled={reorderMutation.isPending}
                    className="flex items-center gap-2 px-3 sm:px-4 py-2.5 rounded-xl text-xs font-bold transition-all shadow-lg bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/20 active:scale-95 whitespace-nowrap"
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
                    flex items-center gap-1.5 sm:gap-2 p-2 sm:p-2.5 bg-white/85 dark:bg-secondary/10 border rounded-xl transition-all duration-300
                    ${showActionMenu ? 'border-sky-500/60 bg-sky-100/70 dark:bg-sky-500/5 shadow-lg shadow-sky-500/10' : 'border-sky-300/70 dark:border-border/50 hover:bg-sky-100/70 dark:hover:bg-accent/10'}
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

                <AnimatePresence>
                  {showActionMenu && (
                    <motion.div
                      initial={{ opacity: 0, y: 10, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 10, scale: 0.95 }}
                      className="absolute right-0 top-full mt-2 w-52 !bg-white dark:!bg-slate-900 border border-border/50 rounded-xl shadow-2xl p-1 z-50 overflow-hidden !opacity-100"
                      style={{ backgroundColor: 'rgb(var(--background))' }}
                    >
                      {canRefreshAllCharts && (
                        <>
                          <button
                            onClick={() => { handleRefreshAll(); setShowActionMenu(false); }}
                            disabled={isRefreshing}
                            className="w-full flex items-center justify-between px-2.5 py-2 rounded-lg text-[11px] font-semibold text-foreground hover:bg-slate-100 dark:hover:bg-white/5 transition-all group/opt disabled:opacity-30"
                          >
                            <div className="flex items-center gap-2.5">
                              <div className="w-6 h-6 rounded-md bg-sky-500/10 flex items-center justify-center border border-sky-500/20 group-hover/opt:border-sky-500/40">
                                <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-sky-400' : 'text-sky-400'}`} />
                              </div>
                              <span>Refresh Charts</span>
                            </div>
                            {isRefreshing && <span className="text-[9px] text-sky-500 animate-pulse font-mono font-bold tracking-tighter">LIVE</span>}
                          </button>

                          <div className="h-px bg-border/20 my-1 mx-1" />
                        </>
                      )}

                      <button
                        onClick={() => { handleExportPDF(); setShowActionMenu(false); }}
                        disabled={exporting}
                        className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-[11px] font-semibold text-foreground hover:bg-slate-100 dark:hover:bg-white/5 transition-all group/opt disabled:opacity-30"
                      >
                        <div className="w-6 h-6 rounded-md bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20 group-hover/opt:border-emerald-500/40">
                          <FileDown className={`w-3.5 h-3.5 ${exporting ? 'animate-pulse text-emerald-400' : 'text-emerald-400'}`} />
                        </div>
                        <span>
                          {exporting ? 'Processing PDF...' : 'To PDF'}
                        </span>
                      </button>

                      <button
                        onClick={() => { handleExportHTML(); setShowActionMenu(false); }}
                        disabled={exportingHtml}
                        className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-[11px] font-semibold text-foreground hover:bg-slate-100 dark:hover:bg-white/5 transition-all group/opt disabled:opacity-30"
                      >
                        <div className="w-6 h-6 rounded-md bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 group-hover/opt:border-indigo-500/40">
                          <Monitor className={`w-3.5 h-3.5 ${exportingHtml ? 'animate-pulse text-indigo-400' : 'text-indigo-400'}`} />
                        </div>
                        <span>
                          {exportingHtml ? 'Packaging...' : 'To HTML'}
                        </span>
                      </button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="h-[84px] md:h-[92px]" />

      {/* 🖼️ Grid Display */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 sm:gap-8">
        {filteredCharts.map((chart, idx) => (
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
              delay: idx % 6 * 0.05
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
              onOpenStudio={onOpenStudio}
            />
          </motion.div>
        ))}
      </div>

      {/* 📭 Empty State */}
      {filteredCharts.length === 0 && (
        <div className="py-32 text-center glass-card border-dashed border-white/10 bg-transparent animate-in zoom-in-95 duration-500">
          <Layers className="w-12 h-12 text-slate-700 mx-auto mb-4 opacity-20" />
          <h3 className="text-xl font-medium text-slate-500">No matching indicators</h3>
          <p className="text-slate-600 mt-2 text-sm font-light">No charts available with your current access.</p>
        </div>
      )}

      <AnimatePresence>
        {deleteTarget && (
          <motion.div
            className="fixed inset-0 z-[220] flex items-center justify-center bg-black/60 backdrop-blur-sm px-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setDeleteTarget(null)}
          >
            <motion.div
              className="w-full max-w-md rounded-2xl border border-rose-400/30 bg-slate-950 shadow-2xl shadow-rose-900/20 p-5"
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
