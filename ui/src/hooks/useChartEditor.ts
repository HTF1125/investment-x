'use client';

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch, apiFetchJson, getDirectApiBase } from '@/lib/api';
import { applyChartTheme } from '@/lib/chartTheme';
import { DEFAULT_CHART_CODE } from '@/lib/constants';
import type { CustomChartListItem } from '@/types/chart';

// ─── Types ────────────────────────────────────────────────────────────

export interface TimeseriesLookupItem {
  id: string;
  code: string;
  name?: string | null;
  category?: string | null;
  frequency?: string | null;
  source?: string | null;
}

export type ActiveTab = 'library' | 'data' | 'settings';
export type MobilePanel = 'editor' | 'workspace';
export type PdfStatus = 'idle' | 'exporting' | 'complete' | 'error';

export interface RefreshProgress {
  current: number;
  total: number;
  name: string;
}

export interface UseChartEditorOptions {
  mode: 'standalone' | 'integrated';
  initialChartId?: string | null;
  onClose?: () => void;
}

// ─── Hook ─────────────────────────────────────────────────────────────

export function useChartEditor({ mode, initialChartId }: UseChartEditorOptions) {
  const { user } = useAuth();
  const { theme } = useTheme();
  const isLight = theme === 'light';
  const queryClient = useQueryClient();
  const role = String(user?.role || '').toLowerCase();
  const isOwner = !!user && role === 'owner';
  const isAdminRole = !!user && (role === 'admin' || user.is_admin);
  const isGeneralRole = !!user && !isAdminRole && role === 'general';
  const currentUserId = user?.id || null;

  // ─── Code state ───────────────────────────────────────────────────
  const [code, _setCode] = useState<string>(DEFAULT_CHART_CODE);
  const codeRef = useRef<string>(DEFAULT_CHART_CODE);
  const setCode = useCallback((v: string | ((prev: string) => string)) => {
    if (typeof v === 'function') {
      _setCode((prev) => {
        const next = v(prev);
        codeRef.current = next;
        return next;
      });
    } else {
      codeRef.current = v;
      _setCode(v);
    }
  }, []);

  // ─── Chart metadata state ────────────────────────────────────────
  const [name, setName] = useState('Untitled Analysis');
  const [category, setCategory] = useState('ChartPack');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('');
  const [currentChartId, setCurrentChartId] = useState<string | null>(initialChartId || null);
  const [currentChartOwnerId, setCurrentChartOwnerId] = useState<string | null>(null);
  const [exportPdf, setExportPdf] = useState(true);
  const [createdByEmail, setCreatedByEmail] = useState<string | null>(null);
  const [createdByName, setCreatedByName] = useState<string | null>(null);

  // ─── Preview state ───────────────────────────────────────────────
  const [previewFigure, setPreviewFigure] = useState<any>(null);
  const [previewError, setPreviewError] = useState<any | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // ─── Library / list state ────────────────────────────────────────
  const [orderedCharts, setOrderedCharts] = useState<any[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  // ─── UI state ────────────────────────────────────────────────────
  const [exporting, setExporting] = useState(false);
  const [pdfStatus, setPdfStatus] = useState<PdfStatus>('idle');
  const [plotRenderError, setPlotRenderError] = useState<string | null>(null);
  const [plotRetryNonce, setPlotRetryNonce] = useState(0);
  const [copying, setCopying] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [consoleExpanded, setConsoleExpanded] = useState(false);
  const [userManuallyCollapsed, setUserManuallyCollapsed] = useState(false);
  const [refreshingAll, setRefreshingAll] = useState(false);
  const [refreshProgress, setRefreshProgress] = useState<RefreshProgress>({ current: 0, total: 0, name: '' });
  const [loadingChartId, setLoadingChartId] = useState<string | null>(null);

  // ─── Sidebar / panel state ───────────────────────────────────────
  const [libraryOpen, setLibraryOpen] = useState(true);
  const [activeTab, setActiveTab] = useState<ActiveTab>('library');
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('All');
  const [mobilePanel, setMobilePanel] = useState<MobilePanel>('workspace');

  // ─── Editor layout state ─────────────────────────────────────────
  const [editorWidth, setEditorWidth] = useState(440);
  const [showPreview, setShowPreview] = useState(mode !== 'integrated');
  const [showCode, setShowCode] = useState(true);
  const [showMeta, setShowMeta] = useState(mode !== 'integrated');
  const [editorFontSize, setEditorFontSize] = useState(13);
  const [editorFontFamily, setEditorFontFamily] = useState("'JetBrains Mono', monospace");
  const [isMounted, setIsMounted] = useState(false);

  // ─── Timeseries lookup state ─────────────────────────────────────
  const [timeseriesSearch, setTimeseriesSearch] = useState('');
  const [timeseriesQuery, setTimeseriesQuery] = useState('');

  // ─── Derived values ──────────────────────────────────────────────
  const createdByLabel = useMemo(
    () => createdByName || createdByEmail || 'Unassigned',
    [createdByName, createdByEmail]
  );

  // ─── Refs ────────────────────────────────────────────────────────
  const loadedFromPropRef = useRef<string | null>(null);
  const codeEditorRef = useRef<any>(null);
  const savedCursorPos = useRef<{ lineNumber: number; column: number } | null>(null);
  const isDragging = useRef(false);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(440);

  // ─── Permission helpers ──────────────────────────────────────────
  const isChartOwner = useCallback(
    (chart: { created_by_user_id?: string | null } | null | undefined) =>
      !!currentUserId &&
      !!chart?.created_by_user_id &&
      String(chart.created_by_user_id) === String(currentUserId),
    [currentUserId]
  );
  const canCreateChart = isOwner || isGeneralRole;
  const canRefreshAllCharts = isOwner || isAdminRole;

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

  const pdfCount = useMemo(() => orderedCharts.filter((c: any) => c.public).length, [orderedCharts]);

  // ─── Init effects ────────────────────────────────────────────────
  useEffect(() => {
    setIsMounted(true);
    const saved = localStorage.getItem('studio-editor-width');
    if (saved) setEditorWidth(parseInt(saved, 10));
    if (mode !== 'integrated') {
      const savedPreview = localStorage.getItem('studio-show-preview');
      if (savedPreview !== null) setShowPreview(savedPreview !== 'false');
    }
    const savedCode = localStorage.getItem('studio-show-code');
    if (savedCode !== null) setShowCode(savedCode !== 'false');
  }, []);

  const togglePreview = useCallback(() => {
    const next = !showPreview;
    setShowPreview(next);
    localStorage.setItem('studio-show-preview', String(next));
  }, [showPreview]);

  const toggleCode = useCallback(() => {
    const next = !showCode;
    setShowCode(next);
    localStorage.setItem('studio-show-code', String(next));
  }, [showCode]);

  // ─── Drag resize ─────────────────────────────────────────────────
  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging.current) return;
      const delta = dragStartX.current - e.clientX;
      const newWidth = Math.min(800, Math.max(280, dragStartWidth.current + delta));
      setEditorWidth(newWidth);
    };
    const onMouseUp = (e: MouseEvent) => {
      if (isDragging.current) {
        isDragging.current = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        const delta = dragStartX.current - e.clientX;
        const finalWidth = Math.min(800, Math.max(280, dragStartWidth.current + delta));
        localStorage.setItem('studio-editor-width', String(finalWidth));
        setEditorWidth(finalWidth);
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

  // ─── Queries & Mutations ─────────────────────────────────────────
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

  // ─── Derived lists ───────────────────────────────────────────────
  const categories = useMemo(() => {
    const cats = new Set<string>();
    orderedCharts.forEach((c: any) => {
      if (c.category) cats.add(c.category);
    });
    return ['All', ...Array.from(cats).sort()];
  }, [orderedCharts]);

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

  // ─── Utility helpers ─────────────────────────────────────────────
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

  // ─── Mutations ───────────────────────────────────────────────────
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
    mutationFn: async (codeToRun: string) => {
      const res = await apiFetch('/api/custom/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: codeToRun }),
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
    mutationFn: async (codeToSave: string) => {
      const tagList = tags.split(',').map((t: string) => t.trim()).filter(Boolean);
      const payload = { name, code: codeToSave, category, description, tags: tagList, public: exportPdf };
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

      if (data && data.figure) {
        setPreviewFigure(data.figure);
      }

      queryClient.invalidateQueries({ queryKey: ['custom-charts'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });

      if (savedId) {
        queryClient.refetchQueries({ queryKey: ['chart-figure', savedId] });
      }

      if (!previewFigure && !data?.figure) {
        const fallbackCode = codeEditorRef.current ? codeEditorRef.current.getValue() : codeRef.current;
        previewMutation.mutate(fallbackCode);
      }
    },
    onError: (err: any) => {
      setPreviewError(err);
      setSuccessMsg(null);
      setConsoleExpanded(true);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (chartId: string) => {
      await apiFetchJson(`/api/custom/${chartId}`, { method: 'DELETE' });
      return chartId;
    },
    onSuccess: (chartId: string) => {
      if (currentChartId === chartId) clearEditor();
      queryClient.invalidateQueries({ queryKey: ['custom-charts'] });
      setSuccessMsg('Analysis deleted.');
      setDeleteConfirm(null);
    },
  });

  // ─── Actions ─────────────────────────────────────────────────────
  const toggleExportPdf = useCallback(async (chartId: string, newValue: boolean) => {
    if (!canToggleExport) return;
    setOrderedCharts(prev => prev.map(c => c.id === chartId ? { ...c, public: newValue } : c));
    if (currentChartId === chartId) setExportPdf(newValue);
    try {
      await apiFetchJson('/api/custom/public', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: [chartId], public: newValue }),
      });
    } catch {
      setOrderedCharts(prev => prev.map(c => c.id === chartId ? { ...c, public: !newValue } : c));
      if (currentChartId === chartId) setExportPdf(!newValue);
    }
  }, [canToggleExport, currentChartId]);

  const handlePreview = useCallback(() => {
    const currentCode = codeEditorRef.current ? codeEditorRef.current.getValue() : codeRef.current;
    setSuccessMsg(null);
    setPreviewError(null);
    previewMutation.mutate(currentCode);
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
    const currentCode = codeEditorRef.current ? codeEditorRef.current.getValue() : codeRef.current;
    setSuccessMsg(null);
    setPreviewError(null);
    saveMutation.mutate(currentCode);
  }, [canEditCurrentChart, saveMutation]);

  // Stable refs for keyboard shortcuts
  const previewRef = useRef(handlePreview);
  const saveRef = useRef(handleSave);
  useEffect(() => { previewRef.current = handlePreview; }, [handlePreview]);
  useEffect(() => { saveRef.current = handleSave; }, [handleSave]);

  const handleCopyChart = useCallback(async () => {
    if (!previewFigure || copying) return;
    setCopying(true);
    try {
      const Plotly = (await import('plotly.js-dist-min')).default;
      const themed = applyChartTheme(previewFigure, theme, { transparentBackground: false });
      if (!themed) return;
      const url = await Plotly.toImage(
        { data: themed.data, layout: { ...themed.layout, width: 1200, height: 800 } },
        { format: 'png', scale: 2 }
      );
      const res = await fetch(url);
      const blob = await res.blob();
      await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
      setSuccessMsg('Chart copied to clipboard!');
      setTimeout(() => setCopying(false), 1000);
    } catch (err: any) {
      setPreviewError('Copy failed — ' + (err?.message || 'clipboard may not be available in this context.'));
      setCopying(false);
    }
  }, [previewFigure, copying, theme]);

  const handleExportPDF = useCallback(async () => {
    setExporting(true);
    setSuccessMsg(null);
    setPreviewError(null);
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
      const formData = new FormData();
      formData.append('items', JSON.stringify([]));
      formData.append('theme', 'light');
      const res = await fetch(`${getDirectApiBase()}/api/custom/pdf`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        credentials: 'include',
        body: formData,
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
  }, [parseBodySafe, toErrorPayload, pdfCount]);

  const handleRefreshAll = useCallback(async () => {
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
  }, [canRefreshAllCharts, refreshingAll, orderedCharts, queryClient]);

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
    const editor = codeEditorRef.current;

    if (editor) {
      const model = editor.getModel();
      const currentValue: string = model?.getValue() ?? '';
      if (currentValue.includes(`Series('${ts.code}')`) || currentValue.includes(`Series("${ts.code}")`)) {
        setSuccessMsg(`Series('${ts.code}') already in code.`);
        return;
      }
      const position = editor.getPosition() ?? savedCursorPos.current;
      if (position && model) {
        const lineContent: string = model.getLineContent(position.lineNumber);
        const needsLeadingNewline = position.column > 1 || lineContent.trim().length > 0;
        editor.executeEdits('insert-series', [{
          range: {
            startLineNumber: position.lineNumber,
            startColumn: position.column,
            endLineNumber: position.lineNumber,
            endColumn: position.column,
          },
          text: (needsLeadingNewline ? '\n' : '') + snippet,
        }]);
        editor.focus();
        setSuccessMsg(`Inserted Series('${ts.code}') at cursor.`);
        setPreviewError(null);
        return;
      }
    }

    // Fallback: append to end
    setCode((prev) => {
      if (prev.includes(`Series('${ts.code}')`) || prev.includes(`Series("${ts.code}")`)) {
        return prev;
      }
      const needsNewline = prev.length > 0 && !prev.endsWith('\n');
      return `${prev}${needsNewline ? '\n' : ''}${snippet}`;
    });
    setSuccessMsg(`Inserted Series('${ts.code}') into code.`);
    setPreviewError(null);
  }, [buildSeriesSnippet, canEditCurrentChart, setCode]);

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
    setCode(chart.code || DEFAULT_CHART_CODE);
    setCategory(chart.category || 'ChartPack');
    setDescription(chart.description || '');
    setTags(chart.tags ? chart.tags.join(', ') : '');
    setExportPdf(chart.public ?? true);
    setCreatedByEmail(chart.created_by_email || null);
    setCreatedByName(chart.created_by_name || null);
    setPreviewFigure(chart.figure || null);
    setSuccessMsg(`Loaded "${chart.name || 'Untitled'}".`);
    setPreviewError(null);
  }, [setCode]);

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
                public: fullChart.public ?? item.public,
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

  const clearEditor = useCallback(() => {
    setCurrentChartId(null);
    setCurrentChartOwnerId(null);
    setName('Untitled Analysis');
    setCode(DEFAULT_CHART_CODE);
    setCategory('ChartPack');
    setDescription('');
    setTags('');
    setExportPdf(true);
    setCreatedByEmail(null);
    setCreatedByName(null);
    setPreviewFigure(null);
    setSuccessMsg(null);
    setPreviewError(null);
  }, [setCode]);

  // ─── Load from prop effect ───────────────────────────────────────
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
      setCode(DEFAULT_CHART_CODE);
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
  }, [initialChartId, currentChartId, savedCharts, loadChart, setCode]);

  // ─── Keyboard shortcuts ──────────────────────────────────────────
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

  // ─── Computed preview state ──────────────────────────────────────
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

  // ─── Return ──────────────────────────────────────────────────────
  return {
    // Theme
    theme,
    isLight,

    // Auth / permissions
    isOwner,
    canCreateChart,
    canRefreshAllCharts,
    canEditCurrentChart,
    canToggleExport,
    canReorderLibrary,
    canDeleteChart,

    // Code
    code,
    setCode,
    codeRef,
    codeEditorRef,
    savedCursorPos,

    // Chart metadata
    name,
    setName,
    category,
    setCategory,
    description,
    setDescription,
    tags,
    setTags,
    currentChartId,
    currentChartOwnerId,
    exportPdf,
    setExportPdf,
    createdByLabel,

    // Preview
    previewFigure,
    themedPreviewFigure,
    previewError,
    successMsg,
    loading,
    saving,
    error,

    // Library
    orderedCharts,
    setOrderedCharts,
    filteredCharts,
    categories,
    isFiltering,

    // UI state
    exporting,
    pdfStatus,
    pdfCount,
    plotRenderError,
    setPlotRenderError,
    plotRetryNonce,
    setPlotRetryNonce,
    copying,
    deleteConfirm,
    setDeleteConfirm,
    consoleExpanded,
    setConsoleExpanded,
    userManuallyCollapsed,
    setUserManuallyCollapsed,
    refreshingAll,
    refreshProgress,
    loadingChartId,

    // Sidebar
    libraryOpen,
    setLibraryOpen,
    activeTab,
    setActiveTab,
    searchQuery,
    setSearchQuery,
    categoryFilter,
    setCategoryFilter,
    mobilePanel,
    setMobilePanel,

    // Editor layout
    editorWidth,
    showPreview,
    togglePreview,
    showCode,
    toggleCode,
    showMeta,
    setShowMeta,
    editorFontSize,
    setEditorFontSize,
    editorFontFamily,
    setEditorFontFamily,
    isMounted,
    startResize,

    // Timeseries
    timeseriesSearch,
    setTimeseriesSearch,
    timeseriesQuery,
    setTimeseriesQuery,
    timeseriesMatches,
    timeseriesLoading,
    runTimeseriesSearch,

    // Actions
    handlePreview,
    handleSave,
    handleCopyChart,
    handleExportPDF,
    handleRefreshAll,
    handlePlotError,
    toggleExportPdf,
    loadChart,
    clearEditor,
    insertSeriesSnippet,
    copySeriesSnippet,

    // Mutations (for isPending checks etc)
    reorderMutation,
    deleteMutation,
  };
}

/** The return type of useChartEditor, for typing sub-component props. */
export type ChartEditorState = ReturnType<typeof useChartEditor>;
