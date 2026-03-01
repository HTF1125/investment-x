'use client';

import React, { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Layers,
  Plus, Eye, EyeOff, Loader2, Copy,
  Search,
  Info, RefreshCw, LayoutGrid, Trash2,
  X, Save, RotateCcw, FileDown,
  ChevronDown, ChevronLeft, ChevronRight,
  FoldVertical, UnfoldVertical,
  Square, Rows2, Link2, Link2Off,
  LayoutTemplate, ScanLine, Terminal, MonitorPlay,
  FileText, FileCode, Play, Code2,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';
import { useQueryClient, useMutation, useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { apiFetch, apiFetchJson } from '@/lib/api';
import { type ChartStyle, CHART_STYLE_LABELS } from '@/lib/chartTheme';
import Chart, { type HoverPoint } from './Chart';
import CustomChartEditor from './CustomChartEditor';
import NavigatorShell from './NavigatorShell';
import dynamic from 'next/dynamic';

const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false, loading: () => <div className="flex-1 flex items-center justify-center text-muted-foreground/40"><Loader2 className="w-5 h-5 animate-spin" /></div> });

type LayoutMode = 'grid' | 'single' | 'stack';

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
  expanded?: boolean;
  syncXRange?: [any, any] | null;
  onXRangeChange?: (range: [any, any] | null) => void;
  unsavedChanges?: boolean;
  onSaveChart?: (id: string) => void;
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
  onOpenStudio,
  expanded = false,
  syncXRange,
  onXRangeChange,
  unsavedChanges,
  onSaveChart,
}: ChartCardProps) {
  // Viewport-based lazy rendering
  const cardRef = useRef<HTMLDivElement>(null);
  const [isInView, setIsInView] = useState(false);
  const [hoverPoints, setHoverPoints] = useState<HoverPoint[] | null>(null);

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

  const cardClassName = `bg-card border border-border/60 rounded-xl overflow-hidden flex flex-col group transition-all duration-200 hover:shadow-lg hover:shadow-black/5 dark:hover:shadow-black/30 hover:border-border relative ${expanded ? 'h-full' : 'h-full min-h-[380px]'}`;

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

          {/* Save (unsaved changes indicator) */}
          {unsavedChanges && (
            <button
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); onSaveChart?.(chart.id); }}
              className="p-1 rounded transition-colors text-sky-400 hover:text-sky-300 hover:bg-sky-500/10 animate-pulse"
              title="Save changes"
            >
              <Save className="w-3 h-3" />
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

      <div ref={cardRef} className="flex flex-col flex-1 min-h-0">
        {/* Chart Area — only render Plotly when in viewport */}
        <div className={`bg-background relative w-full p-3 ${expanded ? 'flex-1 min-h-0' : 'h-[290px] min-h-[290px]'}`}>
          {/* Hover data overlay — Feature 2+3 */}
          {hoverPoints && hoverPoints.length > 0 && (
            <div className="absolute top-4 left-4 right-4 z-10 flex items-center gap-x-2 gap-y-0 flex-wrap pointer-events-none">
              {hoverPoints.map((pt, i) => {
                const hasZ = pt.z !== undefined || pt.value !== undefined;
                const val = pt.z ?? pt.value ?? pt.y;
                const formattedVal = typeof val === 'number' ? val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : String(val);
                const suffix = typeof pt.text === 'string' && pt.text.includes('%') && typeof val === 'number' ? '%' : '';

                return (
                  <span key={i} className="text-[10px] font-mono bg-background/80 backdrop-blur-sm rounded px-1.5 py-0.5 text-foreground/80 border border-border/30 shadow-sm leading-none flex items-center h-5">
                    {pt.name && !hasZ && <span className="text-muted-foreground/60 mr-1">{pt.name}:</span>}
                    {hasZ && typeof pt.y === 'string' && <span className="text-muted-foreground/60 mr-1">{pt.y}:</span>}
                    {formattedVal}{suffix}
                    {pt.x !== undefined && (
                      <span className="text-muted-foreground/50 ml-1">
                        @ {typeof pt.x === 'number' ? pt.x.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : String(pt.x)}
                      </span>
                    )}
                  </span>
                );
              })}
            </div>
          )}
          {isInView ? (
            <Chart
              id={chart.id}
              initialFigure={chart.figure}
              chartStyle={(chart.chart_style ?? undefined) as ChartStyle | undefined}
              copySignal={copySignal}
              onHoverData={setHoverPoints}
              syncXRange={syncXRange}
              onXRangeChange={onXRangeChange}
            />
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
  const [dirtyChartIds, setDirtyChartIds] = useState<Set<string>>(new Set());
  // Store code for dirty charts so we can save without re-entering edit mode
  const dirtyChartData = useRef<Record<string, { code: string; name: string; category: string }>>({});

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

  // ── Inline Chart Editor State ──
  const [editingChartId, setEditingChartId] = useState<string | null>(null);
  const [editCode, setEditCode] = useState('');
  const [editName, setEditName] = useState('');
  const [editCategory, setEditCategory] = useState('');
  const [editPreviewFigure, setEditPreviewFigure] = useState<any>(null);
  const [editError, setEditError] = useState<string | null>(null);
  const [editSuccess, setEditSuccess] = useState<string | null>(null);
  const [editLoading, setEditLoading] = useState(false);
  const [editSaving, setEditSaving] = useState(false);
  const [editTsSearch, setEditTsSearch] = useState('');
  const [editTsQuery, setEditTsQuery] = useState('');
  const editCodeRef = useRef<any>(null);
  const prevLayoutBeforeEdit = useRef<LayoutMode>('grid');

  // Timeseries search for inline editor
  const { data: editTsResults = [], isLoading: editTsLoading } = useQuery<{ id: string; code: string; name?: string | null; category?: string | null }[]>({
    queryKey: ['inline-ts-search', editTsQuery],
    queryFn: () => apiFetchJson(`/api/timeseries?limit=20&offset=0&search=${encodeURIComponent(editTsQuery)}`),
    enabled: editTsQuery.length > 0,
    staleTime: 1000 * 60 * 2,
  });

  // ── Layout mode (grid / single / stack) ──
  const [layoutMode, setLayoutMode] = useState<LayoutMode>(() =>
    typeof window !== 'undefined' ? (localStorage.getItem('dashboard-layout-mode') as LayoutMode) || 'grid' : 'grid'
  );
  const prevLayoutModeRef = useRef<LayoutMode>('grid');

  // Single mode: index into filteredCharts
  const [singleChartIdx, setSingleChartIdx] = useState(0);

  // Stack mode
  const [stackChartCount, setStackChartCount] = useState<2 | 3 | 4>(2);
  const [stackHeights, setStackHeights] = useState<number[]>([50, 50]);
  const isStackDragging = useRef(false);
  const stackDragStartY = useRef(0);
  const stackDragStartHeights = useRef<number[]>([]);
  const stackDragPaneIdx = useRef(0);
  const stackContainerRef = useRef<HTMLDivElement>(null);

  // X-axis sync
  const [syncXAxis, setSyncXAxis] = useState<boolean>(() =>
    typeof window !== 'undefined' ? localStorage.getItem('dashboard-sync-xaxis') === 'true' : false
  );
  const [xSyncRange, setXSyncRange] = useState<[any, any] | null>(null);
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const syncSidebarForViewport = () => {
      if (window.innerWidth < 1024) setSidebarOpen(false);
    };

    syncSidebarForViewport();
    window.addEventListener('resize', syncSidebarForViewport);
    return () => window.removeEventListener('resize', syncSidebarForViewport);
  }, []);

  // Persist layout mode
  useEffect(() => {
    if (typeof window !== 'undefined') localStorage.setItem('dashboard-layout-mode', layoutMode);
  }, [layoutMode]);

  // Reset stack heights when count changes
  useEffect(() => {
    const eq = 100 / stackChartCount;
    setStackHeights(Array.from({ length: stackChartCount }, () => eq));
  }, [stackChartCount]);

  // Keep singleChartIdx in sync with scroll-spy quickJumpId (grid mode drives it)
  useEffect(() => {
    const idx = filteredCharts.findIndex(c => c.id === quickJumpId);
    if (idx !== -1 && layoutMode !== 'single') setSingleChartIdx(idx);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quickJumpId]); // intentionally narrow — only sync when quickJumpId changes

  const handleXRangeChange = useCallback((range: [any, any] | null) => {
    if (syncXAxis) setXSyncRange(range);
  }, [syncXAxis]);

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

  // Override onOpenStudio → inline editing mode
  const handleOpenInStudio = useCallback(async (chartId: string | null) => {
    if (!chartId) return;
    // Save current layout so we can restore on close
    prevLayoutBeforeEdit.current = layoutMode;
    setEditLoading(true);
    setEditError(null);
    setEditSuccess(null);
    setEditPreviewFigure(null);
    try {
      const full = await apiFetchJson(`/api/custom/${chartId}`);
      setEditCode(full.code || '');
      setEditName(full.name || 'Untitled');
      setEditCategory(full.category || '');
      setEditPreviewFigure(full.figure || null);
      setEditingChartId(chartId);
      // Switch to single-chart mode, focused on this chart
      const idx = localCharts.findIndex(c => c.id === chartId);
      if (idx !== -1) setSingleChartIdx(idx);
      setLayoutMode('single');
    } catch (err: any) {
      setEditError(err?.message || 'Failed to load chart');
    } finally {
      setEditLoading(false);
    }
  }, [layoutMode, localCharts]);

  const handleCloseInlineEdit = useCallback(() => {
    // Update local chart data with latest run result so dashboard reflects changes
    if (editingChartId && editPreviewFigure) {
      setLocalCharts(prev => prev.map(c =>
        c.id === editingChartId ? { ...c, figure: editPreviewFigure, name: editName } : c
      ));
    }
    setEditingChartId(null);
    setEditCode('');
    setEditName('');
    setEditCategory('');
    setEditPreviewFigure(null);
    setEditError(null);
    setEditSuccess(null);
    setEditTsSearch('');
    setEditTsQuery('');
    setLayoutMode(prevLayoutBeforeEdit.current);
  }, [editingChartId, editPreviewFigure, editName]);
  
  const handleCloseStudio = useCallback(() => {
    router.push('/', { scroll: false });
  }, [router]);

  // Inline editor: Run code
  const handleInlineRun = useCallback(async () => {
    if (!editCode.trim() || !editingChartId) return;
    setEditLoading(true);
    setEditError(null);
    setEditSuccess(null);
    try {
      const res = await apiFetch('/api/custom/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: editCode }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail?.message || data?.detail || 'Execution failed');
      // Update the local chart with the new figure and exit editing to show the chart
      setLocalCharts(prev => prev.map(c =>
        c.id === editingChartId ? { ...c, figure: data, name: editName, code: editCode } : c
      ));
      // Mark as dirty (unsaved)
      setDirtyChartIds(prev => new Set(prev).add(editingChartId));
      dirtyChartData.current[editingChartId] = { code: editCode, name: editName, category: editCategory };
      setEditingChartId(null);
    } catch (err: any) {
      setEditError(err?.message || 'Execution failed');
    } finally {
      setEditLoading(false);
    }
  }, [editCode, editingChartId, editName]);

  // Inline editor: Save chart
  const handleInlineSave = useCallback(async () => {
    if (!editingChartId) return;
    setEditSaving(true);
    setEditError(null);
    setEditSuccess(null);
    try {
      const res = await apiFetch(`/api/custom/${editingChartId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: editName, code: editCode, category: editCategory }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail?.message || data?.detail || 'Save failed');
      if (data?.figure) setEditPreviewFigure(data.figure);
      setEditSuccess('Saved successfully.');
      // Refresh dashboard data
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      // Update local chart data
      setLocalCharts(prev => prev.map(c => c.id === editingChartId ? { ...c, name: editName, category: editCategory, figure: data?.figure || c.figure, code: editCode } : c));
      // Clear dirty state
      setDirtyChartIds(prev => { const next = new Set(prev); next.delete(editingChartId); return next; });
      delete dirtyChartData.current[editingChartId];
    } catch (err: any) {
      setEditError(err?.message || 'Save failed');
    } finally {
      setEditSaving(false);
    }
  }, [editingChartId, editCode, editName, editCategory, queryClient]);

  // Save unsaved chart from card header icon
  const handleSaveUnsavedChart = useCallback(async (chartId: string) => {
    const data = dirtyChartData.current[chartId];
    if (!data) return;
    try {
      const res = await apiFetch(`/api/custom/${chartId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: data.name, code: data.code, category: data.category }),
      });
      const result = await res.json();
      if (!res.ok) throw new Error(result?.detail || 'Save failed');
      // Update local chart with server figure
      if (result?.figure) {
        setLocalCharts(prev => prev.map(c => c.id === chartId ? { ...c, figure: result.figure } : c));
      }
      // Clear dirty
      setDirtyChartIds(prev => { const next = new Set(prev); next.delete(chartId); return next; });
      delete dirtyChartData.current[chartId];
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
    } catch (err: any) {
      console.error('Save failed:', err);
    }
  }, [queryClient]);

  // Inline editor: Insert timeseries snippet
  const handleInsertTs = useCallback((code: string, name?: string | null) => {
    const alias = code.replace(/[^A-Za-z0-9_]/g, '_').toLowerCase();
    const snippet = `\n# ${name || code}\n${alias} = Series('${code}')\n`;
    const editor = editCodeRef.current;
    if (editor) {
      const model = editor.getModel();
      const pos = editor.getPosition();
      if (pos && model) {
        editor.executeEdits('insert-series', [{
          range: { startLineNumber: pos.lineNumber, startColumn: pos.column, endLineNumber: pos.lineNumber, endColumn: pos.column },
          text: snippet,
        }]);
        editor.focus();
        setEditSuccess(`Inserted Series('${code}')`);
        return;
      }
    }
    setEditCode(prev => prev + snippet);
    setEditSuccess(`Inserted Series('${code}')`);
  }, []);

  // Keyboard shortcuts for inline editor
  useEffect(() => {
    if (!editingChartId) return;
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); handleInlineRun(); }
      if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); handleInlineSave(); }
      if (e.key === 'Escape') { handleCloseInlineEdit(); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [editingChartId, handleInlineRun, handleInlineSave, handleCloseInlineEdit]);

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
      const res = await fetch('/api/custom/pdf', {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
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
      const res = await fetch('/api/custom/html', {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
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
      } else if (layoutMode === 'single') {
        const idx = filteredCharts.findIndex(c => c.id === chartId);
        if (idx !== -1) setSingleChartIdx(idx);
      } else {
        scrollToChart(chartId);
      }
    },
    [scrollToChart, activeStudioChartId, router, layoutMode, filteredCharts]
  );

  // ── Keyboard navigation ──
  const keyNavHandlerRef = useRef<(e: KeyboardEvent) => void>(() => {});
  useEffect(() => {
    keyNavHandlerRef.current = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) || target.contentEditable === 'true') return;
      const len = filteredCharts.length;
      if (!len) return;

      if (e.key === 'j' || (e.key === 'ArrowDown' && layoutMode !== 'grid')) {
        e.preventDefault();
        const next = (singleChartIdx + 1) % len;
        setSingleChartIdx(next);
        setQuickJumpId(filteredCharts[next].id);
        if (layoutMode === 'grid') scrollToChart(filteredCharts[next].id);
      }
      if (e.key === 'k' || (e.key === 'ArrowUp' && layoutMode !== 'grid')) {
        e.preventDefault();
        const prev = (singleChartIdx - 1 + len) % len;
        setSingleChartIdx(prev);
        setQuickJumpId(filteredCharts[prev].id);
        if (layoutMode === 'grid') scrollToChart(filteredCharts[prev].id);
      }
      if (e.key === 'f') {
        setLayoutMode(cur => {
          if (cur === 'single') return prevLayoutModeRef.current;
          prevLayoutModeRef.current = cur;
          return 'single';
        });
      }
      if (e.key === 'Escape') setLayoutMode('grid');
    };
  }, [filteredCharts, layoutMode, singleChartIdx, scrollToChart]);

  useEffect(() => {
    const h = (e: KeyboardEvent) => keyNavHandlerRef.current(e);
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, []);

  // ── Stack drag-resize ──
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
      mainClassName={layoutMode !== 'grid' ? 'overflow-hidden' : ''}
      topBarRight={
        <>
          {/* Group 1: Layout mode */}
          {([
            { mode: 'grid' as LayoutMode, icon: <LayoutGrid className="w-3 h-3" />, label: 'Grid' },
            { mode: 'single' as LayoutMode, icon: <Square className="w-3 h-3" />, label: 'Single' },
            { mode: 'stack' as LayoutMode, icon: <Rows2 className="w-3 h-3" />, label: 'Stack' },
          ]).map(({ mode, icon, label }) => (
            <button
              key={mode}
              onClick={() => setLayoutMode(mode)}
              className={`w-5 h-5 rounded flex items-center justify-center transition-colors ${
                layoutMode === mode
                  ? 'bg-foreground text-background'
                  : 'text-muted-foreground hover:text-foreground hover:bg-foreground/[0.06]'
              }`}
              title={`${label} mode`}
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
                      ? 'bg-foreground text-background'
                      : 'text-muted-foreground hover:text-foreground hover:bg-foreground/[0.06]'
                  }`}
                  title={`${n} panes`}
                >
                  {n}
                </button>
              ))}
            </>
          )}

          <div className="w-px h-3 bg-border/40 mx-0.5" />

          {/* Group 2: X-axis sync */}
          <button
            onClick={() => {
              const next = !syncXAxis;
              setSyncXAxis(next);
              localStorage.setItem('dashboard-sync-xaxis', String(next));
              if (!next) setXSyncRange(null);
            }}
            className={`w-5 h-5 rounded flex items-center justify-center transition-colors ${
              syncXAxis
                ? 'text-sky-400 bg-sky-500/10 hover:bg-sky-500/20'
                : 'text-muted-foreground hover:text-foreground hover:bg-foreground/[0.06]'
            }`}
            title={syncXAxis ? 'X-axis synced — click to disable' : 'Sync X-axis across charts'}
          >
            {syncXAxis ? <Link2 className="w-3 h-3" /> : <Link2Off className="w-3 h-3" />}
          </button>

          <div className="w-px h-3 bg-border/40 mx-0.5" />

          {/* Group 3: Chart style */}
          {([
            { style: 'default' as ChartStyle, icon: <LayoutTemplate className="w-3 h-3" />, label: 'Default' },
            { style: 'minimal' as ChartStyle, icon: <ScanLine className="w-3 h-3" />, label: 'Minimal' },
            { style: 'terminal' as ChartStyle, icon: <Terminal className="w-3 h-3" />, label: 'Terminal' },
            { style: 'presentation' as ChartStyle, icon: <MonitorPlay className="w-3 h-3" />, label: 'Presentation' },
          ]).map(({ style, icon, label }) => (
            <button
              key={style}
              onClick={() => setChartStyle(style)}
              className={`w-5 h-5 rounded flex items-center justify-center transition-colors ${
                chartStyle === style
                  ? 'bg-foreground text-background'
                  : 'text-muted-foreground hover:text-foreground hover:bg-foreground/[0.06]'
              }`}
              title={label}
            >
              {icon}
            </button>
          ))}

          {(canRefreshAllCharts || isOwner) && <div className="w-px h-3 bg-border/40 mx-0.5" />}

          {/* Group 4: Actions */}
          {canRefreshAllCharts && (
            <button
              onClick={handleRefreshAll}
              disabled={isRefreshing}
              className="w-5 h-5 rounded flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-foreground/[0.06] disabled:opacity-40 transition-colors"
              title="Refresh all charts"
            >
              <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`} />
            </button>
          )}
          {isOwner && (
            <>
              <button
                onClick={handleExportPDF}
                disabled={exporting}
                className="w-5 h-5 rounded flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-foreground/[0.06] disabled:opacity-40 transition-colors"
                title="Export PDF"
              >
                <FileText className={`w-3 h-3 ${exporting ? 'animate-pulse' : ''}`} />
              </button>
              <button
                onClick={handleExportHTML}
                disabled={exportingHtml}
                className="w-5 h-5 rounded flex items-center justify-center text-rose-400 hover:text-rose-300 hover:bg-rose-500/[0.08] disabled:opacity-40 transition-colors"
                title="Export HTML"
              >
                <FileCode className={`w-3 h-3 ${exportingHtml ? 'animate-pulse' : ''}`} />
              </button>
            </>
          )}
        </>
      }
      mainScrollRef={mainScrollRef}
    >
      {/* Main Content */}
      {layoutMode === 'single' ? (
        /* ── SINGLE MODE ── */
        <div className="h-full flex flex-col overflow-hidden">
          {/* Chart nav strip */}
          <div className="h-8 px-3 border-b border-border/40 shrink-0 flex items-center gap-2">
            <button
              onClick={() => {
                const prev = (singleChartIdx - 1 + filteredCharts.length) % filteredCharts.length;
                setSingleChartIdx(prev);
                setQuickJumpId(filteredCharts[prev]?.id ?? '');
              }}
              disabled={filteredCharts.length <= 1}
              className="w-5 h-5 rounded flex items-center justify-center text-muted-foreground hover:text-foreground disabled:opacity-30 transition-colors"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="text-xs font-medium text-foreground/80 flex-1 truncate text-center">
              {filteredCharts[singleChartIdx]?.name ?? ''}
            </span>
            <button
              onClick={() => {
                const next = (singleChartIdx + 1) % filteredCharts.length;
                setSingleChartIdx(next);
                setQuickJumpId(filteredCharts[next]?.id ?? '');
              }}
              disabled={filteredCharts.length <= 1}
              className="w-5 h-5 rounded flex items-center justify-center text-muted-foreground hover:text-foreground disabled:opacity-30 transition-colors"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Main chart area */}
          <div className="flex-1 min-h-0 p-3">
            {filteredCharts[singleChartIdx] && (
              editingChartId === filteredCharts[singleChartIdx].id ? (
                /* ── INLINE EDITING: code editor replaces chart content inside same card frame ── */
                <div className="bg-card border border-border/60 rounded-xl overflow-hidden flex flex-col h-full">
                  {/* Card header — matches ChartCard style */}
                  <div className="px-4 py-2.5 flex items-center justify-between gap-2 border-b border-border/40">
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      <Code2 className="w-3.5 h-3.5 text-sky-400 shrink-0" />
                      <input
                        value={editName}
                        onChange={e => setEditName(e.target.value)}
                        className="text-xs font-medium bg-transparent border-none outline-none text-foreground flex-1 min-w-0"
                        placeholder="Chart name"
                      />
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={handleInlineRun}
                        disabled={editLoading}
                        className="flex items-center gap-1 h-6 px-2 rounded text-[11px] font-medium bg-emerald-500/15 text-emerald-400 hover:bg-emerald-500/25 transition-colors disabled:opacity-50"
                        title="Run (Ctrl+Enter)"
                      >
                        {editLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                        Run
                      </button>
                      <button
                        onClick={handleInlineSave}
                        disabled={editSaving}
                        className="flex items-center gap-1 h-6 px-2 rounded text-[11px] font-medium bg-sky-500/15 text-sky-400 hover:bg-sky-500/25 transition-colors disabled:opacity-50"
                        title="Save (Ctrl+S)"
                      >
                        {editSaving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                        Save
                      </button>
                      <button
                        onClick={handleCloseInlineEdit}
                        className="p-1 rounded transition-colors text-muted-foreground/40 hover:text-muted-foreground hover:bg-foreground/[0.06]"
                        title="Close (Esc)"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  </div>

                  {/* Status bar */}
                  {(editError || editSuccess) && (
                    <div className={`px-3 py-1 text-[11px] font-mono shrink-0 ${editError ? 'bg-rose-500/10 text-rose-400' : 'bg-emerald-500/10 text-emerald-400'}`}>
                      {editError || editSuccess}
                    </div>
                  )}

                  {/* Code editor — fills the chart area */}
                  <div className="flex-1 min-h-0">
                    <MonacoEditor
                      height="100%"
                      language="python"
                      theme={theme === 'light' ? 'vs' : 'vs-dark'}
                      value={editCode}
                      onChange={(v: string | undefined) => setEditCode(v || '')}
                      onMount={(editor: any) => { editCodeRef.current = editor; }}
                      options={{
                        minimap: { enabled: false },
                        fontSize: 13,
                        fontFamily: "'JetBrains Mono', monospace",
                        padding: { top: 8 },
                        lineNumbers: 'on',
                        scrollBeyondLastLine: false,
                        wordWrap: 'on',
                        tabSize: 4,
                        automaticLayout: true,
                      }}
                    />
                  </div>

                  {/* Timeseries search strip */}
                  <div className="h-[100px] shrink-0 border-t border-border/40 flex flex-col">
                    <div className="px-2 py-1 flex items-center gap-1.5">
                      <Search className="w-3 h-3 text-muted-foreground/50" />
                      <input
                        value={editTsSearch}
                        onChange={e => setEditTsSearch(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') setEditTsQuery(editTsSearch.trim()); }}
                        placeholder="Search timeseries..."
                        className="flex-1 text-xs bg-transparent border-none outline-none text-foreground placeholder:text-muted-foreground/40"
                      />
                      <button
                        onClick={() => setEditTsQuery(editTsSearch.trim())}
                        className="text-[10px] px-1.5 py-0.5 rounded bg-foreground/[0.06] text-muted-foreground hover:text-foreground transition-colors"
                      >
                        Go
                      </button>
                    </div>
                    <div className="flex-1 overflow-y-auto px-1">
                      {editTsLoading && <div className="p-1 text-[11px] text-muted-foreground/40"><Loader2 className="w-3 h-3 animate-spin inline mr-1" />Searching...</div>}
                      {editTsResults.map(ts => (
                        <button
                          key={ts.id}
                          onClick={() => handleInsertTs(ts.code, ts.name)}
                          className="w-full text-left px-2 py-0.5 text-[11px] rounded hover:bg-foreground/[0.04] transition-colors group flex items-center gap-2"
                        >
                          <span className="font-mono text-sky-400/80 shrink-0">{ts.code}</span>
                          <span className="text-muted-foreground/60 truncate flex-1">{ts.name || ''}</span>
                          <Plus className="w-3 h-3 text-muted-foreground/30 group-hover:text-emerald-400 shrink-0" />
                        </button>
                      ))}
                      {!editTsLoading && editTsQuery && editTsResults.length === 0 && (
                        <div className="p-1 text-[11px] text-muted-foreground/30">No results</div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                /* ── Normal chart view ── */
                <ChartCard
                  key={filteredCharts[singleChartIdx].id}
                  chart={filteredCharts[singleChartIdx]}
                  expanded={true}
                  canEdit={canEditChart(filteredCharts[singleChartIdx])}
                  canRefresh={canRefreshChart(filteredCharts[singleChartIdx])}
                  canDelete={canDeleteChart(filteredCharts[singleChartIdx])}
                  canManageVisibility={canManageVisibility}
                  isReorderable={false}
                  onTogglePdf={handleTogglePdf}
                  onRefreshChart={handleRefreshChart}
                  onCopyChart={handleCopyFromHeader}
                  onDeleteChart={handleDeleteChart}
                  isRefreshingChart={!!refreshingChartIds[filteredCharts[singleChartIdx].id]}
                  isDeletingChart={!!deletingChartIds[filteredCharts[singleChartIdx].id]}
                  onRankChange={handleRankChange}
                  copySignal={copySignals[filteredCharts[singleChartIdx].id] || 0}
                  onOpenStudio={handleOpenInStudio}
                  syncXRange={syncXAxis ? xSyncRange : null}
                  onXRangeChange={handleXRangeChange}
                  unsavedChanges={dirtyChartIds.has(filteredCharts[singleChartIdx].id)}
                  onSaveChart={handleSaveUnsavedChart}
                />
              )
            )}
          </div>

          {/* Thumbnail strip */}
          <div className="h-[68px] border-t border-border/40 flex overflow-x-auto no-scrollbar shrink-0 bg-background/50">
            {filteredCharts.map((chart, idx) => {
              const isActive = idx === singleChartIdx;
              return (
                <button
                  key={chart.id}
                  onClick={() => { setSingleChartIdx(idx); setQuickJumpId(chart.id); }}
                  className={`shrink-0 h-full px-3 flex flex-col justify-center items-start border-b-2 transition-all duration-100 text-left ${
                    isActive
                      ? 'border-sky-500 bg-sky-500/[0.07] text-foreground'
                      : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-foreground/[0.04]'
                  }`}
                  style={{ minWidth: '90px', maxWidth: '150px' }}
                >
                  <span className="text-[10px] font-medium leading-tight truncate w-full">{chart.name}</span>
                  {chart.category && (
                    <span className="text-[9px] text-muted-foreground/50 truncate w-full mt-0.5">{chart.category}</span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      ) : layoutMode === 'stack' ? (
        /* ── STACK MODE ── */
        <div ref={stackContainerRef} className="h-full flex flex-col overflow-hidden">
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
                  onOpenStudio={handleOpenInStudio}
                  syncXRange={syncXAxis ? xSyncRange : null}
                  onXRangeChange={handleXRangeChange}
                  unsavedChanges={dirtyChartIds.has(chart.id)}
                  onSaveChart={handleSaveUnsavedChart}
                />
              </div>
              {paneIdx < Math.min(stackChartCount, filteredCharts.length) - 1 && (
                <div
                  className="h-1 shrink-0 cursor-row-resize bg-border/40 hover:bg-sky-500/40 active:bg-sky-500/60 transition-colors"
                  onMouseDown={(e) => startStackDrag(paneIdx, e)}
                />
              )}
            </React.Fragment>
          ))}
        </div>
      ) : (
        <div className="transition-all duration-300 p-4 md:p-6 max-w-screen-xl mx-auto w-full">
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
                          syncXRange={syncXAxis ? xSyncRange : null}
                          onXRangeChange={handleXRangeChange}
                          unsavedChanges={dirtyChartIds.has(chart.id)}
                          onSaveChart={handleSaveUnsavedChart}
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

