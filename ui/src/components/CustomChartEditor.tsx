'use client';

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import dynamic from 'next/dynamic';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch, apiFetchJson } from '@/lib/api';
import { applyChartTheme } from '@/lib/chartTheme';
import {
  Loader2, Play, Save, Code, FileText,
  Download, Copy, Trash2, Plus, Terminal, Search,
  Maximize2, Minimize2, AlertCircle, CheckCircle2,
  Eye, PanelLeftClose, PanelLeft, PanelRightClose, PanelRight, FileDown, ChevronDown,
  GripVertical, RotateCcw, Layout, Settings, Database, Activity, Layers, X, Filter,
} from 'lucide-react';
import { motion, AnimatePresence, Reorder } from 'framer-motion';
import Editor from '@monaco-editor/react';

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full w-full">
      <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
    </div>
  ),
}) as React.ComponentType<Record<string, unknown>>;

const DEFAULT_CODE = `# Investment-X Analysis Studio
# Available: pd, px, go, np, Series, MultiSeries, apply_theme(fig)
# MUST define a variable 'fig' at the end

import pandas as pd
import plotly.express as px

data = {
    'Year': [2020, 2021, 2022, 2023, 2024],
    'Value': [100, 120, 110, 135, 150]
}
df = pd.DataFrame(data)

fig = px.bar(df, x='Year', y='Value', title='New Analysis')
apply_theme(fig)
`;

interface CustomChartEditorProps {
  mode?: 'standalone' | 'integrated';
  initialChartId?: string | null;
  onClose?: () => void;
}

interface TimeseriesLookupItem {
  id: string;
  code: string;
  name?: string | null;
  category?: string | null;
  frequency?: string | null;
  source?: string | null;
}

interface CustomChartListItem {
  id: string;
  name?: string | null;
  category?: string | null;
  description?: string | null;
  tags?: string[];
  export_pdf?: boolean;
  rank?: number;
  created_by_user_id?: string | null;
  created_by_email?: string | null;
  created_by_name?: string | null;
  code?: string | null;
  figure?: any;
}

export default function CustomChartEditor({ mode = 'standalone', initialChartId, onClose }: CustomChartEditorProps) {
  const { user } = useAuth();
  const { theme } = useTheme();
  const isLight = theme === 'light';
  const queryClient = useQueryClient();
  const role = String(user?.role || '').toLowerCase();
  const isOwner = !!user && role === 'owner';
  const isAdminRole = !!user && (role === 'admin' || user.is_admin);
  const isGeneralRole = !!user && !isAdminRole && role === 'general';
  const currentUserId = user?.id || null;

  // --- State ---
  const [code, setCode] = useState<string>(DEFAULT_CODE);
  const [name, setName] = useState('Untitled Analysis');
  const [category, setCategory] = useState('ChartPack');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('');
  const [currentChartId, setCurrentChartId] = useState<string | null>(initialChartId || null);
  const [currentChartOwnerId, setCurrentChartOwnerId] = useState<string | null>(null);
  const [exportPdf, setExportPdf] = useState(true);
  const [createdByEmail, setCreatedByEmail] = useState<string | null>(null);
  const [createdByName, setCreatedByName] = useState<string | null>(null);

  const [previewFigure, setPreviewFigure] = useState<any>(null);
  const [previewError, setPreviewError] = useState<any | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const [orderedCharts, setOrderedCharts] = useState<any[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [pdfStatus, setPdfStatus] = useState<'idle' | 'exporting' | 'complete' | 'error'>('idle');
  const [graphDiv, setGraphDiv] = useState<HTMLElement | null>(null);
  const [plotRenderError, setPlotRenderError] = useState<string | null>(null);
  const [plotRetryNonce, setPlotRetryNonce] = useState(0);
  const [copying, setCopying] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [consoleExpanded, setConsoleExpanded] = useState(false);
  const [userManuallyCollapsed, setUserManuallyCollapsed] = useState(false);
  const [refreshingAll, setRefreshingAll] = useState(false);
  const [refreshProgress, setRefreshProgress] = useState({ current: 0, total: 0, name: '' });
  const [loadingChartId, setLoadingChartId] = useState<string | null>(null);

  // Default library to open
  const [libraryOpen, setLibraryOpen] = useState(true);
  const [activeTab, setActiveTab] = useState<'library' | 'data' | 'settings'>('library');
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('All');

  // Mobile: which panel is active
  const [mobilePanel, setMobilePanel] = useState<'editor' | 'workspace'>('workspace');

  const [editorWidth, setEditorWidth] = useState(440);
  const [showCodePanel, setShowCodePanel] = useState(false);
  const [showMeta, setShowMeta] = useState(mode !== 'integrated');
  const [editorFontSize, setEditorFontSize] = useState(13);
  const [editorFontFamily, setEditorFontFamily] = useState("'JetBrains Mono', monospace");
  const [isMounted, setIsMounted] = useState(false);
  const [timeseriesSearch, setTimeseriesSearch] = useState('');
  const [timeseriesQuery, setTimeseriesQuery] = useState('');
  const createdByLabel = useMemo(
    () => createdByName || createdByEmail || 'Unassigned',
    [createdByName, createdByEmail]
  );
  const loadedFromPropRef = useRef<string | null>(null);
  const isDragging = useRef(false);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(440);
  const isChartOwner = useCallback(
    (chart: { created_by_user_id?: string | null } | null | undefined) =>
      !!currentUserId &&
      !!chart?.created_by_user_id &&
      String(chart.created_by_user_id) === String(currentUserId),
    [currentUserId]
  );
  const canCreateChart = isOwner || isGeneralRole;
  const canRefreshAllCharts = isOwner || isAdminRole;

  useEffect(() => { 
    setIsMounted(true); 
    const saved = localStorage.getItem('studio-editor-width');
    if (saved) setEditorWidth(parseInt(saved, 10));
    
    // Initial panel state from local storage (default closed if not set)
    const savedPanel = localStorage.getItem('studio-show-code-panel');
    if (savedPanel !== null) {
      setShowCodePanel(savedPanel === 'true');
    }
  }, []);

  const toggleCodePanel = () => {
    const newState = !showCodePanel;
    setShowCodePanel(newState);
    localStorage.setItem('studio-show-code-panel', String(newState));
  };

  // Drag handlers for the resize handle
  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging.current) return;
      // Dragging left = wider editor, dragging right = narrower
      const delta = dragStartX.current - e.clientX;
      const newWidth = Math.min(800, Math.max(280, dragStartWidth.current + delta));
      setEditorWidth(newWidth);
    };
    const onMouseUp = (e: MouseEvent) => {
      if (isDragging.current) {
        isDragging.current = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        // Save final width
        const delta = dragStartX.current - e.clientX;
        const finalWidth = Math.min(800, Math.max(280, dragStartWidth.current + delta));
        localStorage.setItem('studio-editor-width', String(finalWidth));
        setEditorWidth(finalWidth); // Ensure state is synced
      }
    };
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };
  }, []);

  const startResize = useCallback((e: React.MouseEvent) => {
    isDragging.current = true;
    dragStartX.current = e.clientX;
    dragStartWidth.current = editorWidth;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, [editorWidth]);

  // --- Queries & Mutations ---
  const { data: savedCharts = [], refetch: refetchCharts } = useQuery<CustomChartListItem[]>({
    queryKey: ['custom-charts'],
    queryFn: () => apiFetchJson('/api/custom?include_code=false&include_figure=false'),
    enabled: true,
    staleTime: 1000 * 60 * 2,
  });

  const runTimeseriesSearch = useCallback(() => {
    setTimeseriesQuery(timeseriesSearch.trim());
  }, [timeseriesSearch]);

  const {
    data: timeseriesMatches = [],
    isLoading: timeseriesLoading,
    isError: timeseriesError,
    error: timeseriesErrorObj,
  } = useQuery<TimeseriesLookupItem[]>({
    queryKey: ['studio-timeseries-search', timeseriesQuery],
    queryFn: () =>
      apiFetchJson<TimeseriesLookupItem[]>(
        `/api/timeseries?limit=25&offset=0&search=${encodeURIComponent(timeseriesQuery)}`
      ),
    enabled: timeseriesQuery.length > 0,
    staleTime: 1000 * 60 * 2,
  });

  useEffect(() => {
    if (savedCharts.length > 0) {
      setOrderedCharts(savedCharts);
      if (!isLoaded) setIsLoaded(true);
    }
  }, [savedCharts, isLoaded]);

  // Derive unique categories for the filter dropdown
  const categories = useMemo(() => {
    const cats = new Set<string>();
    orderedCharts.forEach((c: any) => {
      if (c.category) cats.add(c.category);
    });
    return ['All', ...Array.from(cats).sort()];
  }, [orderedCharts]);

  // Filtered + searched charts
  const filteredCharts = useMemo(() => {
    let list = orderedCharts;
    if (categoryFilter !== 'All') {
      list = list.filter((c: any) => c.category === categoryFilter);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter((c: any) =>
        (c.name || '').toLowerCase().includes(q) ||
        (c.category || '').toLowerCase().includes(q) ||
        (c.tags || []).some((t: string) => t.toLowerCase().includes(q))
      );
    }
    return list;
  }, [orderedCharts, categoryFilter, searchQuery]);

  const currentChartListItem = useMemo(
    () => orderedCharts.find((c: any) => c.id === currentChartId) || null,
    [orderedCharts, currentChartId]
  );
  const effectiveCurrentOwnerId = currentChartOwnerId || currentChartListItem?.created_by_user_id || null;
  const canEditCurrentChart = useMemo(() => {
    if (!currentChartId) return canCreateChart;
    if (isOwner) return true;
    if (isAdminRole) return false;
    return !!effectiveCurrentOwnerId && !!currentUserId && String(effectiveCurrentOwnerId) === String(currentUserId);
  }, [canCreateChart, currentChartId, currentUserId, effectiveCurrentOwnerId, isAdminRole, isOwner]);
  const canToggleExport = isOwner;
  const canReorderLibrary = isOwner;
  const canDeleteChart = useCallback(
    (chart: { created_by_user_id?: string | null } | null | undefined) =>
      isOwner || (!isAdminRole && isChartOwner(chart)),
    [isAdminRole, isChartOwner, isOwner]
  );

  const isFiltering = useMemo(() => {
    return searchQuery.trim() !== '' || categoryFilter !== 'All';
  }, [searchQuery, categoryFilter]);

  // Count of charts flagged for PDF export
  const pdfCount = useMemo(() => orderedCharts.filter((c: any) => c.export_pdf).length, [orderedCharts]);
  const parseBodySafe = useCallback(async (res: Response) => {
    const text = await res.text();
    if (!text) return null;
    try {
      return JSON.parse(text);
    } catch {
      return text;
    }
  }, []);

  const toErrorPayload = useCallback((body: any, status: number) => {
    if (body && typeof body === 'object') {
      const detail = body.detail;
      if (detail && typeof detail === 'object') return detail;
      if (typeof detail === 'string') return { error: 'Request Error', message: detail };
      if (typeof body.message === 'string') return { error: 'Request Error', message: body.message };
      if (typeof body.error === 'string') return { error: body.error, message: body.message || `Request failed (${status})` };
    }
    if (typeof body === 'string') {
      return { error: 'Request Error', message: body };
    }
    return { error: 'Request Error', message: `Request failed (${status})` };
  }, []);

  const reorderMutation = useMutation({
    mutationFn: (items: any[]) => {
      const payload = { items: items.map((c: any) => ({ id: c.id })) };
      return apiFetchJson('/api/custom/reorder', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
    },
  });

  const previewMutation = useMutation({
    mutationFn: async () => {
      const res = await apiFetch('/api/custom/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
      });

      const data = await parseBodySafe(res);
      if (!res.ok) {
        throw toErrorPayload(data, res.status);
      }
      if (!data || typeof data !== 'object') {
        throw toErrorPayload(data, res.status);
      }
      return data;
    },
    onSuccess: (data: any) => {
      setPreviewFigure(data);
      setPreviewError(null);
      setSuccessMsg('Execution completed.');
      if (!userManuallyCollapsed) setConsoleExpanded(true);
    },
    onError: (err: any) => {
      setPreviewError(err);
      setSuccessMsg(null);
      setConsoleExpanded(true);
    },
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const tagList = tags.split(',').map((t: string) => t.trim()).filter(Boolean);
      const payload = { name, code, category, description, tags: tagList, export_pdf: exportPdf };
      const url = currentChartId ? `/api/custom/${currentChartId}` : '/api/custom';
      const method = currentChartId ? 'PUT' : 'POST';
      
      const res = await apiFetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await parseBodySafe(res);
      if (!res.ok) {
        throw toErrorPayload(data, res.status);
      }
      if (!data || typeof data !== 'object') {
        throw toErrorPayload(data, res.status);
      }
      return { data, method };
    },
    onSuccess: ({ data, method }: any) => {
      const savedId = method === 'POST' ? data.id : currentChartId;
      if (method === 'POST') setCurrentChartId(data.id);
      setSuccessMsg(method === 'POST' ? 'Analysis created.' : 'Analysis saved.');
      setPreviewError(null);
      setCurrentChartOwnerId(data?.created_by_user_id || null);
      setCreatedByEmail(data?.created_by_email || null);
      setCreatedByName(data?.created_by_name || null);
      if (!userManuallyCollapsed) setConsoleExpanded(true);

      // CRITICAL: Update the preview figure immediately with the one from the server
      if (data && data.figure) {
        setPreviewFigure(data.figure);
      }

      // Invalidate both lists and the specific chart figure to ensure dashboard stays in sync
      queryClient.invalidateQueries({ queryKey: ['custom-charts'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      
      if (savedId) {
        // Use refetchQueries for more aggressive update of the visible chart in background
        queryClient.refetchQueries({ queryKey: ['chart-figure', savedId] });
      }

      // If we don't have a figure yet, run preview
      if (!previewFigure && !data?.figure) previewMutation.mutate();
    },
    onError: (err: any) => {
      setPreviewError(err);
      setSuccessMsg(null);
      setConsoleExpanded(true);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (chartId: string) => {
      await apiFetchJson(`/api/custom/${chartId}`, {
        method: 'DELETE',
      });
      return chartId;
    },
    onSuccess: (chartId: string) => {
      if (currentChartId === chartId) clearEditor();
      queryClient.invalidateQueries({ queryKey: ['custom-charts'] });
      setSuccessMsg('Analysis deleted.');
      setDeleteConfirm(null);
    },
  });

  // Toggle export_pdf for a single chart inline
  const toggleExportPdf = useCallback(async (chartId: string, newValue: boolean) => {
    if (!canToggleExport) return;
    // Optimistic update
    setOrderedCharts(prev => prev.map(c => c.id === chartId ? { ...c, export_pdf: newValue } : c));
    if (currentChartId === chartId) setExportPdf(newValue);
    try {
      await apiFetchJson('/api/custom/export-pdf', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: [chartId], export_pdf: newValue }),
      });
    } catch {
      // Revert on failure
      setOrderedCharts(prev => prev.map(c => c.id === chartId ? { ...c, export_pdf: !newValue } : c));
      if (currentChartId === chartId) setExportPdf(!newValue);
    }
  }, [canToggleExport, currentChartId]);

  // --- Handlers ---
  const handlePreview = useCallback(() => {
    setSuccessMsg(null);
    setPreviewError(null);
    previewMutation.mutate();
  }, [previewMutation]);

  const handleSave = useCallback(() => {
    if (!canEditCurrentChart) {
      setSuccessMsg(null);
      setPreviewError({
        error: 'Permission Denied',
        message: 'You can only modify charts you created. Owners can modify all charts.',
      });
      return;
    }
    setSuccessMsg(null);
    setPreviewError(null);
    saveMutation.mutate();
  }, [canEditCurrentChart, saveMutation]);

  // Stable refs for keyboard shortcuts
  const previewRef = React.useRef(handlePreview);
  const saveRef = React.useRef(handleSave);
  useEffect(() => { previewRef.current = handlePreview; }, [handlePreview]);
  useEffect(() => { saveRef.current = handleSave; }, [handleSave]);

  const handleCopyChart = async () => {
    if (!graphDiv || copying) return;
    setCopying(true);
    try {
      const Plotly = (await import('plotly.js-dist-min')).default;
      const url = await Plotly.toImage(graphDiv as any, { format: 'png', width: 1200, height: 800, scale: 2 });
      const res = await fetch(url);
      const blob = await res.blob();
      await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
      setSuccessMsg('Chart copied to clipboard!');
      setTimeout(() => setCopying(false), 1000);
    } catch {
      setPreviewError('Copy failed — clipboard may not be available in this context.');
      setCopying(false);
    }
  };

  const handleExportPDF = async () => {
    setExporting(true);
    setSuccessMsg(null);
    setPreviewError(null);
    try {
      // Send empty items array — backend will auto-select export_pdf=true charts
      const res = await apiFetch('/api/custom/pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: [] }),
      });
      if (!res.ok) {
        const errData = await parseBodySafe(res);
        const errPayload = toErrorPayload(errData, res.status);
        throw new Error(errPayload?.message || 'PDF generation failed');
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
      setPdfStatus('complete');
      setSuccessMsg(`PDF exported — ${pdfCount} charts.`);
      setTimeout(() => setPdfStatus('idle'), 4000);
    } catch (err: any) {
      setPdfStatus('error');
      setPreviewError(err);
      console.error("PDF Export Error:", err);
      setTimeout(() => setPdfStatus('idle'), 4000);
    } finally {
      setExporting(false);
    }
  };

  const handleRefreshAll = async () => {
    if (!canRefreshAllCharts || refreshingAll || orderedCharts.length === 0) return;
    
    setRefreshingAll(true);
    setSuccessMsg(null);
    setPreviewError(null);
    setRefreshProgress({ current: 0, total: orderedCharts.length, name: '' });

    let errorCount = 0;
    
    for (let i = 0; i < orderedCharts.length; i++) {
      const chart = orderedCharts[i];
      setRefreshProgress(prev => ({ ...prev, current: i + 1, name: chart.name || 'Untitled' }));
      
      try {
        let chartCode = chart.code;
        if (!chartCode) {
          const detail = await apiFetchJson(`/api/custom/${chart.id}`);
          chartCode = detail?.code;
          if (chartCode) {
            setOrderedCharts((prev) =>
              prev.map((item) =>
                item.id === chart.id ? { ...item, code: chartCode } : item
              )
            );
          }
        }

        if (!chartCode) {
          errorCount++;
          continue;
        }

        const res = await apiFetch('/api/custom/preview', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code: chartCode }),
        });
        
        if (!res.ok) errorCount++;
      } catch (err) {
        errorCount++;
        console.error(`Error refreshing ${chart.name}:`, err);
      }
    }

    setRefreshingAll(false);
    if (errorCount > 0) {
      setPreviewError({ error: 'Refresh Complete', message: `Finished with ${errorCount} errors.` });
    } else {
      setSuccessMsg(`Successfully refreshed ${orderedCharts.length} charts.`);
      queryClient.invalidateQueries({ queryKey: ['custom-charts'] });
    }
  };

  const buildSeriesSnippet = useCallback((ts: TimeseriesLookupItem) => {
    const alias = ts.code.replace(/[^A-Za-z0-9_]/g, '_').toLowerCase();
    return [
      `# ${ts.name || ts.code}`,
      `${alias} = Series('${ts.code}')`,
      '',
    ].join('\n');
  }, []);

  const insertSeriesSnippet = useCallback((ts: TimeseriesLookupItem) => {
    if (!canEditCurrentChart) {
      setPreviewError({
        error: 'Permission Denied',
        message: 'You can only edit charts you created. Owners can edit all charts.',
      });
      return;
    }
    const snippet = buildSeriesSnippet(ts);
    setCode((prev) => {
      if (prev.includes(`Series('${ts.code}')`) || prev.includes(`Series("${ts.code}")`)) {
        return prev;
      }
      const needsNewline = prev.length > 0 && !prev.endsWith('\n');
      return `${prev}${needsNewline ? '\n' : ''}${snippet}`;
    });
    setSuccessMsg(`Inserted Series('${ts.code}') into code.`);
    setPreviewError(null);
  }, [buildSeriesSnippet, canEditCurrentChart]);

  const copySeriesSnippet = useCallback(async (ts: TimeseriesLookupItem) => {
    try {
      await navigator.clipboard.writeText(buildSeriesSnippet(ts));
      setSuccessMsg(`Copied snippet for ${ts.code}.`);
      setPreviewError(null);
    } catch {
      setPreviewError({ error: 'Clipboard Error', message: 'Unable to copy snippet to clipboard.' });
    }
  }, [buildSeriesSnippet]);

  const applyChartToEditor = useCallback((chart: any) => {
    setCurrentChartId(chart.id);
    setCurrentChartOwnerId(chart.created_by_user_id || null);
    setName(chart.name || 'Untitled Analysis');
    setCode(chart.code || DEFAULT_CODE);
    setCategory(chart.category || 'ChartPack');
    setDescription(chart.description || '');
    setTags(chart.tags ? chart.tags.join(', ') : '');
    setExportPdf(chart.export_pdf ?? true);
    setCreatedByEmail(chart.created_by_email || null);
    setCreatedByName(chart.created_by_name || null);
    setPreviewFigure(chart.figure || null);
    setSuccessMsg(`Loaded "${chart.name || 'Untitled'}".`);
    setPreviewError(null);
  }, []);

  const loadChart = useCallback(async (chart: any) => {
    const chartId = chart?.id;
    if (!chartId) return;
    setLoadingChartId(chartId);
    try {
      let fullChart = chart;
      if (!chart.code || !chart.figure) {
        fullChart = await apiFetchJson(`/api/custom/${chartId}`);
      }

      applyChartToEditor(fullChart);
      setOrderedCharts((prev) =>
        prev.map((item) =>
          item.id === chartId
            ? {
                ...item,
                code: fullChart.code,
                figure: fullChart.figure,
                name: fullChart.name ?? item.name,
                category: fullChart.category ?? item.category,
                description: fullChart.description ?? item.description,
                tags: fullChart.tags ?? item.tags,
                export_pdf: fullChart.export_pdf ?? item.export_pdf,
                created_by_user_id: fullChart.created_by_user_id ?? item.created_by_user_id,
                created_by_email: fullChart.created_by_email ?? item.created_by_email,
                created_by_name: fullChart.created_by_name ?? item.created_by_name,
              }
            : item
        )
      );
    } catch (err: any) {
      setPreviewError(err);
      setSuccessMsg(null);
    } finally {
      setLoadingChartId(null);
    }
  }, [applyChartToEditor]);

  const clearEditor = () => {
    setCurrentChartId(null);
    setCurrentChartOwnerId(null);
    setName('Untitled Analysis');
    setCode(DEFAULT_CODE);
    setCategory('ChartPack');
    setDescription('');
    setTags('');
    setExportPdf(true);
    setCreatedByEmail(null);
    setCreatedByName(null);
    setPreviewFigure(null);
    setSuccessMsg(null);
    setPreviewError(null);
  };

  // Handle loading chart from prop (state-based studio navigation)
  useEffect(() => {
    if (initialChartId) {
      if (loadedFromPropRef.current !== initialChartId) {
        const target = savedCharts.find((c: any) => c.id === initialChartId);
        if (target) {
          void loadChart(target);
        } else {
          void loadChart({ id: initialChartId });
        }
        loadedFromPropRef.current = initialChartId;
      }
      return;
    }

    if (initialChartId === null && currentChartId !== null) {
      // CREATE clicked — reset to blank state
      setCode(DEFAULT_CODE);
      setName('Untitled Analysis');
      setCategory('ChartPack');
      setDescription('');
      setTags('');
      setCurrentChartId(null);
      setCurrentChartOwnerId(null);
      setExportPdf(true);
      setCreatedByEmail(null);
      setCreatedByName(null);
      setPreviewFigure(null);
      setPreviewError(null);
      setSuccessMsg(null);
      loadedFromPropRef.current = null;
    }
  }, [initialChartId, currentChartId, savedCharts, loadChart]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        previewRef.current();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveRef.current();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const loading = previewMutation.isPending;
  const saving = saveMutation.isPending;
  const error = previewError ?? (saveMutation.isError ? saveMutation.error : null) ?? null;
  const themedPreviewFigure = useMemo(
    () => {
      try {
        return applyChartTheme(previewFigure, theme, { transparentBackground: true });
      } catch {
        return previewFigure;
      }
    },
    [previewFigure, theme]
  );

  useEffect(() => {
    setPlotRenderError(null);
  }, [previewFigure, theme, plotRetryNonce]);

  const handlePlotError = useCallback((err: any) => {
    const message = err?.message || 'Plot rendering failed.';
    setPlotRenderError(message);
  }, []);

  // ─────────────────────────────────────────────────────────
  // RENDER — 3-panel: [Library sidebar] | [Preview] | [Editor]
  // ─────────────────────────────────────────────────────────
  return (
    <div className={`flex w-full overflow-hidden bg-background ${mode === 'standalone' ? 'h-full' : 'h-full border-l border-border/50 shadow-2xl z-50'}`}>
      {/* ═══════════════ ACTIVITY BAR (VS Code Style) ═══════════════ */}
      {mode === 'standalone' && (
        <aside className="hidden lg:flex w-14 shrink-0 flex-col items-center py-4 gap-4 bg-card border-r border-border/50 z-20">
          <button
            onClick={() => { setActiveTab('library'); setLibraryOpen(true); }}
            className={`p-2 rounded-xl transition-all ${activeTab === 'library' && libraryOpen ? 'text-indigo-400 bg-indigo-500/10' : 'text-slate-500 hover:text-slate-300'}`}
            title="Library"
          >
            <Layout className="w-4 h-4" />
          </button>
          <button
            onClick={() => { setActiveTab('data'); setLibraryOpen(true); }}
            className={`p-2 rounded-xl transition-all ${activeTab === 'data' && libraryOpen ? 'text-indigo-400 bg-indigo-500/10' : 'text-slate-500 hover:text-slate-300'}`}
            title="Variables & Data"
          >
            <Database className="w-4 h-4" />
          </button>
          <div className="mt-auto flex flex-col gap-4 items-center">
              <button
                onClick={() => { setActiveTab('settings'); setLibraryOpen(true); }}
                className={`p-2 rounded-xl transition-all ${activeTab === 'settings' && libraryOpen ? 'text-indigo-400 bg-indigo-500/10' : 'text-slate-500 hover:text-slate-300'}`}
                title="Studio Settings"
              >
                <Settings className="w-4 h-4" />
              </button>
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-600 to-sky-600 flex items-center justify-center text-[10px] font-bold text-white mb-4">
                {name.charAt(0)}
              </div>
          </div>
        </aside>
      )}

      {/* ═══════════════ SIDEBAR PANEL ═══════════════ */}
      {mode === 'standalone' && (
        <aside className={`
          ${libraryOpen ? 'w-80' : 'w-0'} shrink-0 flex flex-col border-r border-border/50 bg-card/70 backdrop-blur-xl transition-all duration-300 overflow-hidden relative z-10
        `}>
        {/* Sidebar Header */}
        <div className="h-10 shrink-0 flex items-center justify-between px-3 border-b border-border/20 bg-foreground/[0.02]">
            <div className="flex items-center gap-1.5">
              {activeTab === 'library' && (
                <>
                  <button
                    onClick={clearEditor}
                    disabled={!canCreateChart}
                    className="p-1.5 rounded-lg transition-all text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/10 disabled:opacity-40 disabled:cursor-not-allowed"
                    title="New Analysis"
                  >
                    <Plus className="w-3.5 h-3.5" />
                  </button>
                  {canRefreshAllCharts && (
                    <button
                      onClick={handleRefreshAll}
                      disabled={refreshingAll}
                      className={`p-1.5 rounded-lg transition-all ${
                        refreshingAll
                          ? 'text-amber-400 bg-amber-500/10'
                          : 'text-muted-foreground hover:text-foreground hover:bg-accent/10'
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
               <span className="text-[9px] font-bold text-muted-foreground/70 uppercase tracking-widest">
                 {activeTab === 'library' ? 'Library' : activeTab === 'data' ? 'Data' : 'Settings'}
               </span>
               {activeTab === 'library' && (
                 <span className="text-[8px] tabular-nums px-1.5 py-0.5 rounded-full bg-sky-500/5 text-muted-foreground font-mono border border-border/20">
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
                  className="px-3 py-2 overflow-hidden border-b border-border/20"
                >
                  <div className="bg-amber-500/5 border border-amber-500/10 rounded-lg p-2">
                    <div className="flex justify-between items-center mb-1.5">
                      <span className="text-[9px] font-mono text-amber-500/80 uppercase tracking-tight truncate max-w-[150px]">
                        {refreshProgress.name}
                      </span>
                      <span className="text-[9px] font-mono text-amber-500/60">
                        {Math.round((refreshProgress.current / refreshProgress.total) * 100)}%
                      </span>
                    </div>
                    <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-gradient-to-r from-amber-600 to-amber-400"
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
                    className={`w-full group relative flex items-start gap-2 px-2 py-1 rounded cursor-pointer transition-all duration-150 border ${
                      currentChartId === chart.id
                        ? 'bg-sky-500/10 border-sky-500/10'
                        : 'border-transparent hover:bg-accent/20'
                    }`}
                  >
                    {/* Index Number */}
                    <div className={`mt-0.5 text-[8px] font-mono shrink-0 w-5 h-3 flex items-center justify-center rounded border transition-colors ${
                      currentChartId === chart.id ? 'bg-sky-500/20 text-sky-400 border-sky-500/20' : 'bg-foreground/5 text-muted-foreground/70 border-border/20'
                    }`}>
                      {idx + 1}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0 flex flex-col items-start text-left">
                      <span className={`text-[9px] font-medium leading-tight truncate w-full ${currentChartId === chart.id ? 'text-sky-300' : 'text-muted-foreground group-hover:text-foreground'}`}>
                        {chart.name || 'Untitled Analysis'}
                      </span>
                      <div className="flex items-center gap-1 opacity-50">
                        <span className="text-[7px] font-mono uppercase tracking-tighter text-muted-foreground/60">
                          {chart.category || 'ANALYSIS'}
                        </span>
                        {chart.export_pdf && <div className="w-0.5 h-0.5 rounded-full bg-emerald-500" />}
                      </div>
                    </div>

                    {/* Actions on hover */}
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        {canToggleExport && (
                          <button
                              onClick={(e) => { e.stopPropagation(); toggleExportPdf(chart.id, !chart.export_pdf); }}
                              className={`w-2.5 h-2.5 rounded-sm border flex items-center justify-center transition-all ${chart.export_pdf ? 'bg-emerald-500 border-emerald-400' : 'border-muted-foreground/30 hover:border-muted-foreground/50'}`}
                              title={chart.export_pdf ? "Included in PDF" : "Excluded from PDF"}
                          >
                              {chart.export_pdf && <CheckCircle2 className="w-2 h-2 text-white" />}
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
                      <motion.div layoutId="sidebar-active" className="absolute left-0 w-0.5 h-2.5 bg-sky-500/60 rounded-r-full" />
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

            <div className="p-2 bg-foreground/[0.02] border-t border-border/20">
                <button
                    onClick={handleExportPDF}
                    disabled={exporting || pdfCount === 0}
                    className="w-full flex items-center justify-between px-3 py-1.5 bg-secondary/30 hover:bg-secondary/50 rounded-lg text-[10px] font-semibold text-foreground disabled:opacity-30 transition-all"
                >
                    <div className="flex items-center gap-2">
                        <FileDown className="w-3 h-3" />
                        Generate Report
                    </div>
                <span className="bg-sky-500/20 text-sky-400 px-1.5 py-0.5 rounded text-[8px] font-mono tabular-nums">{pdfCount}</span>
              </button>
            </div>
          </>
        )}

        {activeTab === 'data' && (
           <div className={`flex flex-col h-full ${isLight ? 'bg-slate-50/80' : 'bg-[#05070c]/20'}`}>
              <div className="p-4 border-b border-white/5">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-600" />
                    <input
                        type="text"
                        placeholder="Search symbols..."
                        className="w-full pl-9 pr-3 py-1.5 bg-white/[0.03] border border-white/5 rounded-lg text-xs text-white focus:outline-none focus:ring-1 focus:ring-indigo-500/30"
                    />
                </div>
              </div>
              <div className="flex-grow overflow-y-auto px-2 py-3 space-y-1 custom-scrollbar">
                  <div className="px-3 py-1 text-[9px] font-bold text-slate-600 uppercase tracking-[0.2em] mb-2">Primary Streams</div>
                  {['SPX_INDEX', 'NDX_INDEX', 'EUR_USD', 'GOLD_CMD', 'UST_10Y', 'BTC_USD'].map(symbol => (
                      <div key={symbol} className="group flex items-center justify-between px-3 py-2 rounded-lg hover:bg-white/[0.03] transition-colors border border-transparent hover:border-white/5 cursor-pointer">
                          <div className="flex items-center gap-2.5">
                              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                              <span className={`text-[11px] font-mono font-bold uppercase ${isLight ? 'text-slate-600 group-hover:text-slate-900' : 'text-slate-400 group-hover:text-white'}`}>{symbol}</span>
                          </div>
                          <span className="text-[10px] text-slate-600 font-mono tracking-tighter">Live</span>
                      </div>
                  ))}
                  <div className="mt-8 px-3 py-6 rounded-xl border border-dashed border-white/10 bg-white/[0.01] text-center mx-2">
                      <Database className="w-5 h-5 text-slate-700 mx-auto mb-2" />
                      <p className="text-[10px] text-slate-600 leading-relaxed italic">External API links can be mapped here via variables plugin.</p>
                  </div>
              </div>
           </div>
        )}

        {activeTab === 'settings' && (
           <div className={`flex flex-col h-full ${isLight ? 'bg-slate-50/80' : 'bg-[#05070c]/20'}`}>
              <div className="px-6 py-8 space-y-8">
                  <div className="space-y-4">
                      <div className="flex items-center gap-2">
                          <Settings className="w-3.5 h-3.5 text-indigo-400" />
                          <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em]">Editor Preferences</h3>
                      </div>
                      
                      <div className="space-y-3">
                          <div className="flex justify-between items-center text-[10px] text-slate-500 font-mono">
                              <span>Font Size</span>
                              <span>{editorFontSize}px</span>
                          </div>
                          <input 
                              type="range" 
                              min="10" 
                              max="20" 
                              value={editorFontSize}
                              onChange={(e) => setEditorFontSize(parseInt(e.target.value))}
                              className="w-full accent-indigo-500 h-1 bg-white/10 rounded-full appearance-none cursor-pointer"
                          />
                      </div>

                      <div className="space-y-2">
                           <span className="text-[10px] text-slate-500 font-mono">Font Family</span>
                           <div className="grid grid-cols-1 gap-2">
                               {["'JetBrains Mono', monospace", "'Fira Code', monospace", "'Ubuntu Mono', monospace"].map(font => (
                                   <button 
                                       key={font}
                                       onClick={() => setEditorFontFamily(font)}
                                       className={`px-3 py-2 text-left text-[10px] font-mono rounded-lg border transition-all ${editorFontFamily === font ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400' : 'bg-white/5 border-white/5 text-slate-600 hover:text-slate-400'}`}
                                   >
                                       {font.split(',')[0].replace(/'/g, '')}
                                   </button>
                               ))}
                           </div>
                      </div>
                  </div>

                  <div className="pt-6 border-t border-white/5">
                      <button 
                        onClick={() => { if(confirm('Clear current analysis?')) clearEditor(); }}
                        className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 rounded-xl text-rose-500 text-[10px] font-bold transition-all"
                      >
                          <Trash2 className="w-3.5 h-3.5" />
                          Purge Buffer
                      </button>
                  </div>
              </div>
           </div>
        )}
      </aside>
    )}

      {/* ═══════════════ CENTER — Workspace ═══════════════ */}
      <main className="flex-grow flex flex-col min-w-0 bg-background relative">
        {/* Workspace Header / Breadcrumbs */}
        <header className="h-10 shrink-0 flex items-center justify-between px-4 border-b border-border/50 bg-card/70 backdrop-blur-md relative z-20">
            <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 shrink-0">
                    <Activity className="w-4 h-4" />
                </div>
                <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    readOnly={!canEditCurrentChart}
                    className="bg-transparent text-[13px] font-bold text-foreground placeholder-muted-foreground focus:outline-none truncate min-w-0 flex-shrink read-only:opacity-70"
                    placeholder="Untitled Analysis"
                />
                <div className="hidden sm:flex items-center gap-1.5 text-[9px] font-mono text-muted-foreground/60 shrink-0">
                    <span>{category || 'Uncategorized'}</span>
                    <span className="opacity-40">/</span>
                    <span className="truncate max-w-[80px]">{tags || 'No Tags'}</span>
                    <span className="opacity-40">/</span>
                    <span className="truncate max-w-[80px]" title={`Created by ${createdByLabel}`}>{createdByLabel}</span>
                </div>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
                <button
                    onClick={handlePreview}
                    disabled={loading}
                    className="p-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg shadow-lg shadow-indigo-600/20 transition-all active:scale-95 disabled:opacity-50"
                    title="Run (Ctrl+Enter)"
                >
                    {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                </button>
                <button
                    onClick={handleSave}
                    disabled={saving || !canEditCurrentChart}
                    className="p-2 text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 rounded-lg transition-all active:scale-95 disabled:opacity-30"
                    title="Save (Ctrl+S)"
                >
                    {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                </button>
                <button
                    onClick={() => setShowMeta(!showMeta)}
                    className={`p-2 rounded-lg transition-all ${showMeta ? 'text-indigo-400 bg-indigo-500/10 border border-indigo-500/20' : 'text-muted-foreground hover:text-foreground bg-card/60 border border-transparent hover:border-border/50'}`}
                    title="Properties"
                >
                    <Settings className="w-3.5 h-3.5" />
                </button>
                <button
                    onClick={toggleCodePanel}
                    className={`p-2 rounded-lg transition-all ${showCodePanel ? 'text-indigo-400 bg-indigo-500/10 border border-indigo-500/20' : 'text-muted-foreground hover:text-foreground bg-card/60 border border-transparent hover:border-border/50'}`}
                    title={showCodePanel ? 'Show Chart' : 'Show Code'}
                >
                    <Code className="w-3.5 h-3.5" />
                </button>
            </div>
        </header>

        {/* ═══════════════ PROPERTIES DRAWER ═══════════════ */}
        <AnimatePresence>
            {showMeta && (
                <motion.div 
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="shrink-0 bg-card border-b border-border/50 overflow-hidden z-10"
                >
                    <div className="flex flex-col gap-2 px-4 py-2 max-w-7xl mx-auto">
                        <div className="grid grid-cols-4 gap-2 items-start">
                            <div className="col-span-1 min-w-0 space-y-1">
                                <label className="text-[9px] font-bold text-slate-500 uppercase tracking-[0.2em] flex items-center gap-1.5">
                                    <Layers className="w-2.5 h-2.5 text-indigo-500" /> Category
                                </label>
                                <input
                                    type="text"
                                    value={category}
                                    onChange={(e) => setCategory(e.target.value)}
                                    readOnly={!canEditCurrentChart}
                                    className={`w-full border rounded-lg px-2 py-1 text-[10px] outline-none focus:border-indigo-500/50 transition-all font-semibold ${
                                      isLight
                                        ? 'bg-slate-50 border-slate-200 text-slate-700 placeholder:text-slate-400'
                                        : 'bg-white/[0.03] border-white/10 text-slate-300'
                                    }`}
                                    placeholder="ChartPack"
                                />
                            </div>

                            <div className="col-span-1 min-w-0 space-y-1">
                                <label className="text-[9px] font-bold text-slate-500 uppercase tracking-[0.2em] flex items-center gap-1.5">
                                    <Search className="w-2.5 h-2.5 text-indigo-500" /> Tags
                                </label>
                                <input
                                    type="text"
                                    value={tags}
                                    onChange={(e) => setTags(e.target.value)}
                                    readOnly={!canEditCurrentChart}
                                    className={`w-full border rounded-lg px-2 py-1 text-[10px] outline-none focus:border-indigo-500/50 transition-all font-mono ${
                                      isLight
                                        ? 'bg-slate-50 border-slate-200 text-slate-700 placeholder:text-slate-400'
                                        : 'bg-white/[0.03] border-white/10 text-slate-300 placeholder:text-slate-700'
                                    }`}
                                    placeholder="Volatility, Strategy..."
                                />
                            </div>

                            <div className="col-span-1 min-w-0 space-y-1">
                                <label className="text-[9px] font-bold text-slate-500 uppercase tracking-[0.2em] flex items-center gap-1.5">
                                    <Activity className="w-2.5 h-2.5 text-indigo-500" /> Created By
                                </label>
                                <input
                                    type="text"
                                    value={createdByLabel}
                                    readOnly
                                    className={`w-full border rounded-lg px-2 py-1 text-[10px] font-mono ${
                                      isLight
                                        ? 'bg-slate-50 border-slate-200 text-slate-600'
                                        : 'bg-white/[0.02] border-white/10 text-slate-400'
                                    }`}
                                />
                            </div>

                            <div className="col-span-1 min-w-0 space-y-1">
                                <label className="text-[9px] font-bold text-slate-500 uppercase tracking-[0.2em] flex items-center gap-1.5">
                                    <FileText className="w-2.5 h-2.5 text-indigo-500" /> Description
                                </label>
                                <input
                                    type="text"
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    readOnly={!canEditCurrentChart}
                                    className={`w-full border rounded-lg px-2 py-1 text-[10px] outline-none focus:border-indigo-500/50 transition-all font-medium ${
                                      isLight
                                        ? 'bg-slate-50 border-slate-200 text-slate-700 placeholder:text-slate-400'
                                        : 'bg-white/[0.03] border-white/10 text-slate-300'
                                    }`}
                                    placeholder="Describe the protocol..."
                                />
                            </div>
                        </div>

                        {mode === 'standalone' && (
                            <div className="flex items-center justify-between p-2 bg-indigo-500/[0.02] border border-indigo-500/10 rounded-lg">
                                <div className="flex items-center gap-2">
                                    <div className={`w-1.5 h-1.5 rounded-full ${exportPdf ? 'bg-emerald-500 animate-pulse' : 'bg-slate-700'}`} />
                                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Report Sync</span>
                                </div>
                                <button
                                    onClick={() => currentChartId ? toggleExportPdf(currentChartId, !exportPdf) : setExportPdf(!exportPdf)}
                                    disabled={!canToggleExport}
                                    className={`flex items-center gap-1 px-2 py-1 rounded border transition-all text-[9px] font-bold ${exportPdf ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' : 'text-slate-600 border-white/10 bg-white/5'}`}
                                >
                                    <CheckCircle2 className="w-2.5 h-2.5" />
                                    {canToggleExport ? (exportPdf ? 'ON' : 'OFF') : 'OWNER'}
                                </button>
                            </div>
                        )}
                    </div>
                </motion.div>
            )}
        </AnimatePresence>

        {/* Workspace Canvas Area */}
        <div className="flex-grow flex flex-col relative min-h-0 overflow-hidden">

            {/* Main Visualizer */}
            {(mode === 'integrated' || !showCodePanel) ? (
            <div className={`flex-grow relative flex flex-col min-h-0 p-3 md:p-4 ${isLight ? 'bg-slate-100' : 'bg-[#010205]'}`}>
                <div className={`flex-grow relative overflow-hidden rounded-2xl border ${
                  isLight
                    ? 'border-slate-200 bg-white/80 shadow-sm'
                    : 'border-border/40 bg-[#020711]'
                }`}>
                    {loadingChartId ? (
                        <div className="absolute inset-0 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm z-10">
                            <div className="relative">
                                <div className="absolute inset-0 blur-3xl bg-indigo-500/20 rounded-full" />
                                <div className={`relative w-20 h-20 rounded-3xl flex items-center justify-center backdrop-blur-sm ${
                                  isLight ? 'bg-white border border-slate-200 shadow-sm' : 'bg-white/[0.03] border border-white/10'
                                }`}>
                                    <Loader2 className={`w-8 h-8 animate-spin ${isLight ? 'text-indigo-600' : 'text-indigo-400'}`} />
                                </div>
                            </div>
                            <h3 className={`text-sm font-bold mt-6 uppercase tracking-[0.2em] ${isLight ? 'text-slate-600' : 'text-slate-400'}`}>Loading Chart</h3>
                            <p className={`text-[10px] font-mono mt-2 ${isLight ? 'text-slate-500' : 'text-slate-600'}`}>Fetching analysis data...</p>
                        </div>
                    ) : themedPreviewFigure && !plotRenderError ? (
                        <Plot
                        key={`${currentChartId || 'draft'}-${theme}-${plotRetryNonce}`}
                        data={themedPreviewFigure.data}
                        layout={{ 
                            ...themedPreviewFigure.layout, 
                            autosize: true
                        }}
                        config={{ responsive: true, displayModeBar: 'hover', displaylogo: false }}
                        style={{ width: '100%', height: '100%' }}
                        useResizeHandler={true}
                        className="w-full h-full"
                        onInitialized={(_: any, gd: any) => setGraphDiv(gd)}
                        onError={handlePlotError}
                        />
                    ) : plotRenderError ? (
                        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 px-6 text-center">
                            <div className="text-xs font-semibold text-rose-400">Chart Render Error</div>
                            <div className={`text-[11px] ${isLight ? 'text-slate-600' : 'text-slate-400'}`}>
                                {plotRenderError}
                            </div>
                            <button
                                type="button"
                                onClick={() => {
                                  setPlotRenderError(null);
                                  setPlotRetryNonce((n) => n + 1);
                                }}
                                className="h-8 px-3 rounded-md border border-border/60 text-xs text-muted-foreground hover:text-foreground"
                            >
                                Retry Render
                            </button>
                        </div>
                    ) : (
                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                            <div className="relative">
                                <div className="absolute inset-0 blur-3xl bg-indigo-500/20 rounded-full" />
                                <div className={`relative w-24 h-24 rounded-3xl flex items-center justify-center backdrop-blur-sm ${
                                  isLight ? 'bg-white border border-slate-200 shadow-sm' : 'bg-white/[0.03] border border-white/10'
                                }`}>
                                    <Activity className={`w-10 h-10 ${isLight ? 'text-slate-400' : 'text-slate-700'}`} />
                                </div>
                            </div>
                            <h3 className={`text-sm font-bold mt-6 uppercase tracking-[0.2em] ${isLight ? 'text-slate-600' : 'text-slate-400'}`}>IDE Forge Ready</h3>
                            <p className={`text-[10px] font-mono mt-2 ${isLight ? 'text-slate-500' : 'text-slate-600'}`}>Initialize analysis or select from library</p>
                        </div>
                    )}

                    {/* Quick Floating Actions */}
                    {previewFigure && (
                        <div className="absolute top-4 right-4 flex gap-2">
                            <button
                                onClick={handleCopyChart}
                                className={`p-2 rounded-xl backdrop-blur-xl border transition-all ${
                                  isLight
                                    ? 'bg-white/90 border-slate-200 text-slate-600 hover:text-slate-900 hover:border-slate-300 shadow-sm'
                                    : 'bg-black/40 border-white/10 text-slate-400 hover:text-white hover:border-white/20'
                                }`}
                                title="Copy Image"
                            >
                                {copying ? <Loader2 className="w-4 h-4 animate-spin" /> : <Copy className="w-4 h-4" />}
                            </button>
                        </div>
                    )}
                </div>
            </div>
            ) : (
                <div>Code editor placeholder - should not appear in integrated mode</div>
            )}
        </div>
      </main>


      {/* Notification Layer */}
      <AnimatePresence>
        {pdfStatus !== 'idle' && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="fixed bottom-8 right-8 z-[100] flex items-center gap-4 px-6 py-4 bg-card/90 backdrop-blur-2xl border border-border/50 rounded-2xl shadow-2xl"
          >
            <div className={`p-2 rounded-xl ${pdfStatus === 'exporting' ? 'bg-indigo-500/20 text-indigo-400' : pdfStatus === 'complete' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                {pdfStatus === 'exporting' ? <Loader2 className="w-5 h-5 animate-spin" /> : pdfStatus === 'complete' ? <CheckCircle2 className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-bold text-foreground uppercase tracking-tight">
                {pdfStatus === 'exporting' ? 'Synthesizing PDF...' : pdfStatus === 'complete' ? 'Synthesis Complete' : 'Process Failed'}
              </span>
              <span className="text-[10px] text-muted-foreground font-mono mt-0.5">
                {pdfStatus === 'exporting' ? `Building ${pdfCount} chart definitions` : pdfStatus === 'complete' ? 'File ready for archival' : 'System error encountered'}
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* Delete Confirmation Modal */}
      <AnimatePresence>
        {deleteConfirm && (
          <div className="fixed inset-0 z-[110] flex items-center justify-center p-4">
            <motion.div 
               initial={{ opacity: 0 }} 
               animate={{ opacity: 1 }} 
               exit={{ opacity: 0 }}
               onClick={() => setDeleteConfirm(null)}
               className={`absolute inset-0 backdrop-blur-sm ${isLight ? 'bg-slate-900/40' : 'bg-black/60'}`}
            />
            <motion.div
               initial={{ scale: 0.9, opacity: 0, y: 20 }}
               animate={{ scale: 1, opacity: 1, y: 0 }}
               exit={{ scale: 0.9, opacity: 0, y: 20 }}
               className="relative w-full max-w-sm bg-card border border-border/50 rounded-2xl shadow-2xl p-6"
            >
              <div className="flex items-center gap-4 mb-6">
                <div className="w-12 h-12 rounded-2xl bg-rose-500/10 flex items-center justify-center text-rose-500">
                  <Trash2 className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-foreground">Delete Analysis?</h3>
                  <p className="text-xs text-muted-foreground mt-1">This action is permanent and cannot be undone.</p>
                </div>
              </div>
              
              <div className="flex gap-3">
                <button
                  onClick={() => setDeleteConfirm(null)}
                  className="flex-1 px-4 py-2.5 bg-card/70 hover:bg-card text-foreground text-xs font-bold rounded-xl transition-all"
                >
                  Cancel
                </button>
                <button
                  onClick={() => deleteConfirm && deleteMutation.mutate(deleteConfirm)}
                  disabled={deleteMutation.isPending}
                  className="flex-1 px-4 py-2.5 bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-rose-600/20 transition-all disabled:opacity-50"
                >
                  {deleteMutation.isPending ? 'Deleting...' : 'Confirm Delete'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
