'use client';

import { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import { apiFetch, apiFetchJson, getDirectApiBase } from '@/lib/api';
import type { ChartMeta } from '@/types/chart';

// ── Types ──

export type ViewMode = 'gallery' | 'focus';

export interface FocusPanel {
  chartId: string;
}

export interface GroupedCategory {
  category: string;
  charts: ChartMeta[];
}

export interface DashboardState {
  // ── Chart data ──
  localCharts: ChartMeta[];
  originalCharts: ChartMeta[];
  setLocalCharts: React.Dispatch<React.SetStateAction<ChartMeta[]>>;

  // ── Filtering ──
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  debouncedSearch: string;
  activeCategory: string;
  setActiveCategory: (cat: string) => void;
  allFilteredCharts: ChartMeta[];
  filteredCharts: ChartMeta[];
  groupedCharts: GroupedCategory[];
  categories: string[];

  // ── View mode ──
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;
  spotlightChartId: string | null;
  setSpotlightChartId: (id: string | null) => void;
  editorChartId: string | null;
  setEditorChartId: (id: string | null) => void;

  // ── Focus view ──
  focusPanels: string[];
  setFocusPanels: React.Dispatch<React.SetStateAction<string[]>>;
  focusPanelCount: 1 | 2 | 3 | 4;
  setFocusPanelCount: (n: 1 | 2 | 3 | 4) => void;
  focusHeights: number[];
  setFocusHeights: React.Dispatch<React.SetStateAction<number[]>>;
  startFocusDrag: (idx: number, e: React.MouseEvent) => void;
  focusContainerRef: React.RefObject<HTMLDivElement | null>;

  // ── Favorites ──
  favorites: Set<string>;
  toggleFavorite: (id: string) => void;

  // ── Mutation states ──
  refreshingChartIds: Record<string, boolean>;
  deletingChartIds: Record<string, boolean>;
  copySignals: Record<string, number>;
  deleteTarget: { id: string; name: string } | null;
  setDeleteTarget: (t: { id: string; name: string } | null) => void;

  // ── Permissions ──
  isOwner: boolean;
  isAdminRole: boolean;
  isReorderEnabled: boolean;
  canManageVisibility: boolean;
  canRefreshAllCharts: boolean;
  canEditChart: (chart: ChartMeta) => boolean;
  canDeleteChart: (chart: ChartMeta) => boolean;
  canRefreshChart: (chart: ChartMeta) => boolean;

  // ── Handlers ──
  handleToggleVisibility: (id: string, status: boolean) => void;
  handleRefreshChart: (id: string) => void;
  handleCopyChart: (id: string) => void;
  handleDeleteChart: (id: string) => void;
  confirmDeleteChart: () => void;
  handleRankChange: (id: string, newRank: number) => void;
  handleSaveOrder: () => void;
  handleResetOrder: () => void;
  handleRefreshAll: () => void;
  handleExportPDF: () => void;
  handleExportHTML: () => void;
  handleOpenEditor: (chartId: string | null) => void;

  // ── Export state ──
  isRefreshing: boolean;
  exporting: boolean;
  exportingHtml: boolean;
  isOrderDirty: boolean;
  isReorderSaving: boolean;

  // ── Misc ──
  mounted: boolean;
  mainScrollRef: React.RefObject<HTMLDivElement | null>;
}

// ── Hook ──

export function useDashboardState(
  chartsByCategory: Record<string, ChartMeta[]>
): DashboardState {
  const { user } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();

  // ── Permissions ──
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

  const canEditChart = useCallback(
    (chart: ChartMeta) => isOwner || isChartOwner(chart),
    [isOwner, isChartOwner]
  );
  const canDeleteChart = canEditChart;
  const canRefreshChart = useCallback(
    (chart: ChartMeta) => canRefreshAllCharts || isChartOwner(chart),
    [canRefreshAllCharts, isChartOwner]
  );

  const isReorderEnabled = isOwner;
  const canManageVisibility = isOwner;

  // ── Chart data ──
  const [localCharts, setLocalCharts] = useState<ChartMeta[]>([]);
  const [originalCharts, setOriginalCharts] = useState<ChartMeta[]>([]);
  const [mounted, setMounted] = useState(false);

  // Sync from props
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

  useEffect(() => { setMounted(true); }, []);

  // ── Filtering ──
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState<string>('all');

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchQuery.trim().toLowerCase()), 300);
    return () => clearTimeout(t);
  }, [searchQuery]);

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

  const filteredCharts = useMemo(() => {
    if (activeCategory === 'all') return allFilteredCharts;
    return allFilteredCharts.filter(c => (c.category || 'Uncategorized') === activeCategory);
  }, [allFilteredCharts, activeCategory]);

  const groupedCharts = useMemo(() => {
    const groups = new Map<string, ChartMeta[]>();
    for (const chart of allFilteredCharts) {
      const cat = chart.category || 'Uncategorized';
      if (!groups.has(cat)) groups.set(cat, []);
      groups.get(cat)!.push(chart);
    }
    return Array.from(groups.entries()).map(([category, charts]) => ({ category, charts }));
  }, [allFilteredCharts]);

  const categories = useMemo(() => groupedCharts.map(g => g.category), [groupedCharts]);

  // ── View mode ──
  const [viewMode, setViewModeRaw] = useState<ViewMode>('gallery');
  const [spotlightChartId, setSpotlightChartId] = useState<string | null>(null);
  const [editorChartId, setEditorChartId] = useState<string | null>(null);

  const setViewMode = useCallback((mode: ViewMode) => {
    setViewModeRaw(mode);
    if (typeof window !== 'undefined') localStorage.setItem('dashboard-view-mode', mode);
  }, []);

  // Restore view mode from localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('dashboard-view-mode') as ViewMode;
      if (saved === 'gallery' || saved === 'focus') setViewModeRaw(saved);
    }
  }, []);

  // URL params: ?spotlight=chartId opens Spotlight on mount
  useEffect(() => {
    const spotlightParam = searchParams.get('spotlight');
    if (spotlightParam && mounted) {
      setSpotlightChartId(spotlightParam);
      router.replace('/', { scroll: false });
    }
    const editorParam = searchParams.get('editor');
    if (editorParam && mounted) {
      setEditorChartId(editorParam === 'new' ? 'new' : editorParam);
      router.replace('/', { scroll: false });
    }
  }, [searchParams, mounted, router]);

  // ── Focus view ──
  const [focusPanels, setFocusPanels] = useState<string[]>([]);
  const [focusPanelCount, setFocusPanelCountRaw] = useState<1 | 2 | 3 | 4>(2);
  const [focusHeights, setFocusHeights] = useState<number[]>([50, 50]);
  const isFocusDragging = useRef(false);
  const focusDragStartY = useRef(0);
  const focusDragStartHeights = useRef<number[]>([]);
  const focusDragPaneIdx = useRef(0);
  const focusContainerRef = useRef<HTMLDivElement>(null);

  const setFocusPanelCount = useCallback((n: 1 | 2 | 3 | 4) => {
    setFocusPanelCountRaw(n);
    const eq = 100 / n;
    setFocusHeights(Array.from({ length: n }, () => eq));
  }, []);

  // Drag-resize for focus panels
  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!isFocusDragging.current || !focusContainerRef.current) return;
      const totalH = focusContainerRef.current.getBoundingClientRect().height;
      if (totalH === 0) return;
      const delta = ((e.clientY - focusDragStartY.current) / totalH) * 100;
      const h = focusDragStartHeights.current;
      const idx = focusDragPaneIdx.current;
      const MIN = 15;
      let above = Math.max(MIN, h[idx] + delta);
      let below = Math.max(MIN, h[idx + 1] - delta);
      if (above + below !== h[idx] + h[idx + 1]) {
        const total = h[idx] + h[idx + 1];
        above = Math.min(total - MIN, above);
        below = total - above;
      }
      const newH = [...h];
      newH[idx] = above;
      newH[idx + 1] = below;
      setFocusHeights(newH);
    };
    const onUp = () => {
      if (isFocusDragging.current) {
        isFocusDragging.current = false;
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

  const startFocusDrag = useCallback((idx: number, e: React.MouseEvent) => {
    isFocusDragging.current = true;
    focusDragStartY.current = e.clientY;
    focusDragStartHeights.current = [...focusHeights];
    focusDragPaneIdx.current = idx;
    document.body.style.cursor = 'row-resize';
    document.body.style.userSelect = 'none';
    e.preventDefault();
  }, [focusHeights]);

  // ── Favorites ──
  const [favorites, setFavorites] = useState<Set<string>>(() => {
    if (typeof window === 'undefined') return new Set<string>();
    try {
      const saved = localStorage.getItem('ix-chart-favorites');
      return saved ? new Set(JSON.parse(saved)) : new Set<string>();
    } catch { return new Set<string>(); }
  });

  const toggleFavorite = useCallback((id: string) => {
    setFavorites(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      localStorage.setItem('ix-chart-favorites', JSON.stringify(Array.from(next)));
      return next;
    });
  }, []);

  // ── Mutation states ──
  const [refreshingChartIds, setRefreshingChartIds] = useState<Record<string, boolean>>({});
  const [deletingChartIds, setDeletingChartIds] = useState<Record<string, boolean>>({});
  const [copySignals, setCopySignals] = useState<Record<string, number>>({});
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportingHtml, setExportingHtml] = useState(false);
  const mainScrollRef = useRef<HTMLDivElement>(null);

  // ── Mutations ──
  const toggleVisibilityMutation = useMutation({
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
      return apiFetchJson(`/api/custom/${chartId}/refresh`, { method: 'POST' });
    },
    onSuccess: (data: any, chartId) => {
      if (data?.figure) {
        queryClient.setQueryData(['chart-figure', chartId], data.figure);
      } else {
        queryClient.invalidateQueries({ queryKey: ['chart-figure', chartId], exact: true });
      }
      setRefreshingChartIds(prev => { const next = { ...prev }; delete next[chartId]; return next; });
    },
    onError: (_err, chartId) => {
      setRefreshingChartIds(prev => { const next = { ...prev }; delete next[chartId]; return next; });
    },
  });

  const deleteChartMutation = useMutation({
    mutationFn: async (chartId: string) => {
      await apiFetchJson(`/api/custom/${chartId}`, { method: 'DELETE' });
      return chartId;
    },
    onSuccess: (chartId) => {
      setLocalCharts(prev => prev.filter(c => c.id !== chartId));
      setOriginalCharts(prev => prev.filter(c => c.id !== chartId));
      queryClient.removeQueries({ queryKey: ['chart-figure', chartId] });
      queryClient.setQueryData(['dashboard-summary'], (old: any) => {
        if (!old?.charts_by_category) return old;
        const updated: Record<string, any[]> = {};
        for (const [cat, charts] of Object.entries(old.charts_by_category as Record<string, any[]>)) {
          const filtered = charts.filter((c: any) => c.id !== chartId);
          if (filtered.length > 0) updated[cat] = filtered;
        }
        return { ...old, charts_by_category: updated, categories: Object.keys(updated) };
      });
      queryClient.invalidateQueries({ queryKey: ['custom-charts'] });
      setDeletingChartIds(prev => { const next = { ...prev }; delete next[chartId]; return next; });
    },
    onError: (_err, chartId) => {
      setDeletingChartIds(prev => { const next = { ...prev }; delete next[chartId]; return next; });
    },
  });

  const refreshAllMutation = useMutation({
    mutationFn: async () => {
      const res = await apiFetch('/api/task/refresh-charts', { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to trigger chart refresh');
      }
      return res.json() as Promise<{ task_id?: string }>;
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['task-processes'] });
    },
  });

  // ── Handlers ──
  const handleToggleVisibility = useCallback((id: string, status: boolean) => {
    if (!canManageVisibility) return;
    toggleVisibilityMutation.mutate({ id, status });
  }, [canManageVisibility, toggleVisibilityMutation]);

  const handleRefreshChart = useCallback((id: string) => {
    const target = localCharts.find(c => c.id === id);
    if (!target || !canRefreshChart(target)) return;
    setRefreshingChartIds(prev => ({ ...prev, [id]: true }));
    refreshChartMutation.mutate(id);
  }, [canRefreshChart, localCharts, refreshChartMutation]);

  const handleCopyChart = useCallback((id: string) => {
    setCopySignals(prev => ({ ...prev, [id]: (prev[id] || 0) + 1 }));
  }, []);

  const handleDeleteChart = useCallback((id: string) => {
    const target = localCharts.find(c => c.id === id);
    if (!target || !canDeleteChart(target)) return;
    setDeleteTarget({ id, name: target?.name || id });
  }, [canDeleteChart, localCharts]);

  const confirmDeleteChart = useCallback(() => {
    if (!deleteTarget) return;
    const id = deleteTarget.id;
    setDeletingChartIds(prev => ({ ...prev, [id]: true }));
    deleteChartMutation.mutate(id);
    setDeleteTarget(null);
  }, [deleteTarget, deleteChartMutation]);

  const handleRankChange = useCallback((id: string, newRank: number) => {
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

  const handleSaveOrder = useCallback(() => {
    if (!isReorderEnabled) return;
    reorderMutation.mutate(localCharts);
  }, [isReorderEnabled, localCharts, reorderMutation]);

  const handleResetOrder = useCallback(() => {
    setLocalCharts([...originalCharts]);
  }, [originalCharts]);

  const handleRefreshAll = useCallback(async () => {
    if (!canRefreshAllCharts || refreshAllMutation.isPending) return;
    try {
      const data = await refreshAllMutation.mutateAsync();
      if (data?.task_id) {
        queryClient.invalidateQueries({ queryKey: ['task-processes'] });
      }
    } catch {
      // TaskNotifications shows backend task status/errors
    }
  }, [canRefreshAllCharts, refreshAllMutation, queryClient]);

  const triggerBlobDownload = useCallback((blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  }, []);

  const handleExportPDF = useCallback(async () => {
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
    } catch (err) {
      console.error('PDF export error:', err);
    } finally {
      queryClient.invalidateQueries({ queryKey: ['task-processes'] });
      setExporting(false);
    }
  }, [exporting, queryClient, triggerBlobDownload]);

  const handleExportHTML = useCallback(async () => {
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
    } catch (err) {
      console.error('HTML export error:', err);
    } finally {
      queryClient.invalidateQueries({ queryKey: ['task-processes'] });
      setExportingHtml(false);
    }
  }, [exportingHtml, queryClient, triggerBlobDownload]);

  const handleOpenEditor = useCallback((chartId: string | null) => {
    setEditorChartId(chartId === null ? 'new' : chartId);
  }, []);

  // ── Derived ──
  const isOrderDirty = useMemo(() => {
    if (localCharts.length !== originalCharts.length) return false;
    return localCharts.some((c, i) => c.id !== originalCharts[i]?.id);
  }, [localCharts, originalCharts]);

  return {
    localCharts,
    originalCharts,
    setLocalCharts,
    searchQuery,
    setSearchQuery,
    debouncedSearch,
    activeCategory,
    setActiveCategory,
    allFilteredCharts,
    filteredCharts,
    groupedCharts,
    categories,
    viewMode,
    setViewMode,
    spotlightChartId,
    setSpotlightChartId,
    editorChartId,
    setEditorChartId,
    focusPanels,
    setFocusPanels,
    focusPanelCount,
    setFocusPanelCount,
    focusHeights,
    setFocusHeights,
    startFocusDrag,
    focusContainerRef,
    favorites,
    toggleFavorite,
    refreshingChartIds,
    deletingChartIds,
    copySignals,
    deleteTarget,
    setDeleteTarget,
    isOwner,
    isAdminRole,
    isReorderEnabled,
    canManageVisibility,
    canRefreshAllCharts,
    canEditChart,
    canDeleteChart,
    canRefreshChart,
    handleToggleVisibility,
    handleRefreshChart,
    handleCopyChart,
    handleDeleteChart,
    confirmDeleteChart,
    handleRankChange,
    handleSaveOrder,
    handleResetOrder,
    handleRefreshAll,
    handleExportPDF,
    handleExportHTML,
    handleOpenEditor,
    isRefreshing: refreshAllMutation.isPending,
    exporting,
    exportingHtml,
    isOrderDirty,
    isReorderSaving: reorderMutation.isPending,
    mounted,
    mainScrollRef,
  };
}
