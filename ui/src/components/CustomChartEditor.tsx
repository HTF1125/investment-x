'use client';

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import dynamic from 'next/dynamic';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch, apiFetchJson } from '@/lib/api';
import {
  Loader2, Play, Save, Code, FileText, 
  Download, Copy, Trash2, Plus, Terminal, Search,
  Maximize2, Minimize2, AlertCircle, CheckCircle2,
  Eye, PanelLeftClose, PanelLeft, PanelRightClose, PanelRight, FileDown, ChevronDown,
  GripVertical, RotateCcw, Layout, Settings, Database, Activity, Layers,
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
}) as any;

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

export default function CustomChartEditor({ mode = 'standalone', initialChartId, onClose }: CustomChartEditorProps) {
  const { token } = useAuth();
  const { theme } = useTheme();
  const isLight = theme === 'light';
  const queryClient = useQueryClient();

  // --- State ---
  const [code, setCode] = useState<string>(DEFAULT_CODE);
  const [name, setName] = useState('Untitled Analysis');
  const [category, setCategory] = useState('Personal');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('');
  const [currentChartId, setCurrentChartId] = useState<string | null>(initialChartId || null);
  const [exportPdf, setExportPdf] = useState(true);

  const [previewFigure, setPreviewFigure] = useState<any>(null);
  const [previewError, setPreviewError] = useState<any | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const [orderedCharts, setOrderedCharts] = useState<any[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [pdfStatus, setPdfStatus] = useState<'idle' | 'exporting' | 'complete' | 'error'>('idle');
  const [graphDiv, setGraphDiv] = useState<HTMLElement | null>(null);
  const [copying, setCopying] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [consoleExpanded, setConsoleExpanded] = useState(true);
  const [userManuallyCollapsed, setUserManuallyCollapsed] = useState(false);
  const [refreshingAll, setRefreshingAll] = useState(false);
  const [refreshProgress, setRefreshProgress] = useState({ current: 0, total: 0, name: '' });

  // Default library to open
  const [libraryOpen, setLibraryOpen] = useState(true);
  const [activeTab, setActiveTab] = useState<'library' | 'data' | 'settings'>('library');
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('All');

  // Mobile: which panel is active
  const [mobilePanel, setMobilePanel] = useState<'editor' | 'workspace'>('workspace');

  const [editorWidth, setEditorWidth] = useState(440);
  const [showCodePanel, setShowCodePanel] = useState(false);
  const [showMeta, setShowMeta] = useState(true);
  const [editorFontSize, setEditorFontSize] = useState(13);
  const [editorFontFamily, setEditorFontFamily] = useState("'JetBrains Mono', monospace");
  const [isMounted, setIsMounted] = useState(false);
  const loadedFromPropRef = useRef<string | null>(null);
  const isDragging = useRef(false);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(440);

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
  const { data: savedCharts = [], refetch: refetchCharts } = useQuery({
    queryKey: ['custom-charts'],
    queryFn: () => apiFetchJson('/api/custom'),
    enabled: true,
  });

  useEffect(() => {
    if (savedCharts.length > 0) {
      setOrderedCharts(savedCharts);
      if (!isLoaded) setIsLoaded(true);
    }
  }, [savedCharts, isLoaded]);

  // Handle loading chart from prop (state-based studio navigation)
  useEffect(() => {
    if (initialChartId && savedCharts.length > 0) {
      const target = savedCharts.find((c: any) => c.id === initialChartId);
      if (target && loadedFromPropRef.current !== initialChartId) {
        loadChart(target);
        loadedFromPropRef.current = initialChartId;
      }
    } else if (initialChartId === null && currentChartId !== null) {
      // CREATE clicked — reset to blank state
      setCode(DEFAULT_CODE);
      setName('Untitled Analysis');
      setCategory('Personal');
      setDescription('');
      setTags('');
      setCurrentChartId(null);
      setExportPdf(true);
      setPreviewFigure(null);
      setPreviewError(null);
      setSuccessMsg(null);
      loadedFromPropRef.current = null;
    }
  }, [initialChartId, savedCharts, currentChartId]);

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

  const isFiltering = useMemo(() => {
    return searchQuery.trim() !== '' || categoryFilter !== 'All';
  }, [searchQuery, categoryFilter]);

  // Count of charts flagged for PDF export
  const pdfCount = useMemo(() => orderedCharts.filter((c: any) => c.export_pdf).length, [orderedCharts]);

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
      
      const data = await res.json();
      if (!res.ok) {
         const errorObj = typeof data.detail === 'object' ? data.detail : data;
         throw errorObj;
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

      const data = await res.json();
      if (!res.ok) {
         const errorObj = typeof data.detail === 'object' ? data.detail : data;
         throw errorObj;
      }
      return { data, method };
    },
    onSuccess: ({ data, method }: any) => {
      const savedId = method === 'POST' ? data.id : currentChartId;
      if (method === 'POST') setCurrentChartId(data.id);
      setSuccessMsg(method === 'POST' ? 'Analysis created.' : 'Analysis saved.');
      setPreviewError(null);
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
  }, [token, currentChartId]);

  // --- Handlers ---
  const handlePreview = useCallback(() => {
    setSuccessMsg(null);
    setPreviewError(null);
    previewMutation.mutate();
  }, [previewMutation]);

  const handleSave = useCallback(() => {
    setSuccessMsg(null);
    setPreviewError(null);
    saveMutation.mutate();
  }, [saveMutation]);

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
         const errData = await res.json().catch(() => ({}));
         throw new Error(errData.detail || 'PDF generation failed');
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
    if (refreshingAll || orderedCharts.length === 0) return;
    
    setRefreshingAll(true);
    setSuccessMsg(null);
    setPreviewError(null);
    setRefreshProgress({ current: 0, total: orderedCharts.length, name: '' });

    let errorCount = 0;
    
    for (let i = 0; i < orderedCharts.length; i++) {
      const chart = orderedCharts[i];
      setRefreshProgress(prev => ({ ...prev, current: i + 1, name: chart.name || 'Untitled' }));
      
      try {
        const res = await fetch('/api/custom/preview', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ code: chart.code }),
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

  const loadChart = (chart: any) => {
    setCurrentChartId(chart.id);
    setName(chart.name || 'Untitled Analysis');
    setCode(chart.code);
    setCategory(chart.category || 'Personal');
    setDescription(chart.description || '');
    setTags(chart.tags ? chart.tags.join(', ') : '');
    setExportPdf(chart.export_pdf ?? true);
    setPreviewFigure(chart.figure || null);
    setSuccessMsg(`Loaded "${chart.name || 'Untitled'}".`);
    setPreviewError(null);
    


  };

  const clearEditor = () => {
    setCurrentChartId(null);
    setName('Untitled Analysis');
    setCode(DEFAULT_CODE);
    setCategory('Personal');
    setDescription('');
    setTags('');
    setExportPdf(true);
    setPreviewFigure(null);
    setSuccessMsg(null);
    setPreviewError(null);
  };

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
            <Layout className="w-6 h-6" />
          </button>
          <button 
            onClick={() => { setActiveTab('data'); setLibraryOpen(true); }}
            className={`p-2 rounded-xl transition-all ${activeTab === 'data' && libraryOpen ? 'text-indigo-400 bg-indigo-500/10' : 'text-slate-500 hover:text-slate-300'}`}
            title="Variables & Data"
          >
            <Database className="w-6 h-6" />
          </button>
          <div className="mt-auto flex flex-col gap-4 items-center">
              <button 
                onClick={() => { setActiveTab('settings'); setLibraryOpen(true); }}
                className={`p-2 rounded-xl transition-all ${activeTab === 'settings' && libraryOpen ? 'text-indigo-400 bg-indigo-500/10' : 'text-slate-500 hover:text-slate-300'}`}
                title="Studio Settings"
              >
                <Settings className="w-6 h-6" />
              </button>
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-600 to-sky-600 flex items-center justify-center text-[10px] font-bold text-white mb-4">
                {name.charAt(0)}
              </div>
          </div>
        </aside>
      )}

      {/* ═══════════════ MOBILE TAB BAR ═══════════════ */}
      <div className="lg:hidden fixed bottom-0 left-0 right-0 z-50 h-12 bg-card border-t border-border/50 flex items-center justify-around px-2">
        <button
          onClick={() => setMobilePanel('workspace')}
          className={`flex-1 flex flex-col items-center gap-0.5 py-1.5 rounded-lg transition-colors ${mobilePanel === 'workspace' ? 'text-indigo-400 bg-indigo-500/10' : 'text-slate-500'}`}
        >
          <Eye className="w-4 h-4" />
          <span className="text-[9px] font-medium">Workspace</span>
        </button>
        <button
          onClick={() => setMobilePanel('editor')}
          className={`flex-1 flex flex-col items-center gap-0.5 py-1.5 rounded-lg transition-colors ${mobilePanel === 'editor' ? 'text-indigo-400 bg-indigo-500/10' : 'text-slate-500'}`}
        >
          <Code className="w-4 h-4" />
          <span className="text-[9px] font-medium">Code</span>
        </button>
      </div>

      {/* ═══════════════ SIDEBAR PANEL ═══════════════ */}
      {mode === 'standalone' && (
        <aside className={`
          ${libraryOpen ? 'w-80' : 'w-0'} shrink-0 flex flex-col border-r border-border/50 bg-card/70 backdrop-blur-xl transition-all duration-300 overflow-hidden relative z-10
        `}>
        {/* Sidebar Header */}
        <div className="h-12 shrink-0 flex items-center justify-between px-4 border-b border-white/5 bg-white/[0.02]">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                {activeTab === 'library' ? 'Research Library' : activeTab === 'data' ? 'Data Pipeline' : 'Preferences'}
              </span>
              {activeTab === 'library' && (
                <span className="text-[9px] tabular-nums px-1.5 py-0.5 rounded-full bg-white/[0.06] text-slate-500 font-mono">
                    {orderedCharts.length}
                </span>
              )}
            </div>
            <button
                onClick={() => setLibraryOpen(false)}
                className="p-1 text-slate-500 hover:text-white hover:bg-white/5 rounded transition-colors lg:hidden"
            >
                <PanelLeftClose className="w-4 h-4" />
            </button>
        </div>

        {activeTab === 'library' && (
          <>
            {/* New + Export */}
            <div className="p-3 border-b border-white/5 flex gap-2">
              <button
                onClick={clearEditor}
                className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-xs font-semibold text-white bg-indigo-600/90 hover:bg-indigo-500 rounded-xl shadow-lg shadow-indigo-500/10 transition-all"
              >
                <Plus className="w-4 h-4" /> New Analysis
              </button>
              <button
                onClick={handleRefreshAll}
                disabled={refreshingAll}
                className={`p-2 rounded-xl transition-all border ${
                  refreshingAll 
                    ? 'text-amber-400 bg-amber-500/10 border-amber-500/20' 
                    : 'text-slate-500 hover:text-white bg-white/[0.03] border-white/10'
                }`}
                title="Refresh all data"
              >
                {refreshingAll ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
              </button>
            </div>

            {/* Refresh All Progress Bar */}
            <AnimatePresence>
              {refreshingAll && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="px-3 pb-3 overflow-hidden"
                >
                  <div className="bg-amber-500/5 border border-amber-500/10 rounded-xl p-3">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-[10px] font-mono text-amber-500/80 uppercase tracking-tight truncate max-w-[150px]">
                        {refreshProgress.name}
                      </span>
                      <span className="text-[10px] font-mono text-amber-500/60">
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
            <div className="px-3 py-3 border-b border-white/5 bg-white/[0.01]">
              <div className="relative group">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600 group-focus-within:text-indigo-400 transition-colors" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Filter charts..."
                  className="w-full pl-9 pr-3 py-2 bg-white/[0.03] border border-white/5 rounded-xl text-xs text-white placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-indigo-500/30 transition-all"
                />
              </div>
            </div>

            {/* Chart list */}
            <div className="flex-grow overflow-y-auto custom-scrollbar">
              <Reorder.Group 
                axis="y" 
                values={filteredCharts} 
                onReorder={(newItems) => {
                    // Update the global orderedCharts. 
                    // If filtering is on, reordering is disabled by isFiltering hook anyway,
                    // but we ensure here that we only update the full list.
                    if (!isFiltering) {
                        setOrderedCharts(newItems);
                    }
                }}
                className="py-2 space-y-0.5 px-2"
              >
                {filteredCharts.map((chart: any) => (
                  <Reorder.Item
                    key={chart.id}
                    value={chart}
                    onClick={() => loadChart(chart)}
                    className={`group relative flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all duration-200 ${
                      currentChartId === chart.id
                        ? 'bg-indigo-500/10 border border-indigo-500/20 shadow-inner'
                        : 'border border-transparent hover:bg-white/[0.03] hover:border-white/5'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                        {!isFiltering && (
                            <div className="flex flex-col items-center gap-1">
                                <GripVertical className="w-3 h-3 text-slate-700 opacity-0 group-hover:opacity-100 transition-opacity cursor-grab active:cursor-grabbing" />
                                <button 
                                    onClick={(e) => { e.stopPropagation(); toggleExportPdf(chart.id, !chart.export_pdf); }}
                                    className={`w-3.5 h-3.5 rounded border flex items-center justify-center transition-all ${chart.export_pdf ? 'bg-indigo-500 border-indigo-400 text-white' : 'border-white/10 hover:border-white/30 text-transparent'}`}
                                    title={chart.export_pdf ? "Included in PDF" : "Excluded from PDF"}
                                >
                                    <CheckCircle2 className="w-2.5 h-2.5" />
                                </button>
                            </div>
                        )}
                        <div className={`p-1.5 rounded-lg ${currentChartId === chart.id ? 'bg-indigo-500/20 text-indigo-400' : 'bg-white/5 text-slate-500'} group-hover:scale-110 transition-transform`}>
                          <Activity className="w-3.5 h-3.5" />
                        </div>
                    </div>
                    
                    <div className="flex-grow min-w-0">
                        <div className={`text-[11px] font-semibold truncate ${currentChartId === chart.id ? 'text-indigo-200' : 'text-slate-300 group-hover:text-white'}`}>
                          {chart.name || 'Untitled Analysis'}
                        </div>
                        <div className="text-[9px] text-slate-500 font-mono mt-0.5 flex items-center gap-1.5">
                            <span className="px-1 py-0.5 bg-white/5 rounded uppercase tracking-tighter">{chart.category}</span>
                            {chart.export_pdf && <span className="text-emerald-500/80">• PDF</span>}
                        </div>
                    </div>

                    <div className="flex items-center gap-1">
                        <button
                            onClick={(e) => { e.stopPropagation(); setDeleteConfirm(chart.id); }}
                            className="p-1.5 text-slate-700 hover:text-rose-400 opacity-0 group-hover:opacity-100 transition-all"
                            title="Delete Analysis"
                        >
                            <Trash2 className="w-3 h-3" />
                        </button>
                        {currentChartId === chart.id && (
                          <motion.div layoutId="active-indicator" className="absolute left-0 w-1 h-5 bg-indigo-500 rounded-r-full" />
                        )}
                    </div>
                  </Reorder.Item>
                ))}
              </Reorder.Group>
            </div>
            
            <div className="p-3 bg-white/[0.02] border-t border-white/5">
                <button
                    onClick={handleExportPDF}
                    disabled={exporting || pdfCount === 0}
                    className="w-full flex items-center justify-between px-4 py-2 bg-white/5 hover:bg-white/10 rounded-xl text-xs font-semibold text-slate-300 disabled:opacity-30 transition-all"
                >
                    <div className="flex items-center gap-2">
                        <FileDown className="w-4 h-4" />
                        Generate Report
                    </div>
                <span className="bg-indigo-500/20 text-indigo-400 px-1.5 py-0.5 rounded-md text-[9px] font-mono tabular-nums">{pdfCount}</span>
              </button>
            </div>
          </>
        )}

        {activeTab === 'data' && (
           <div className="flex flex-col h-full bg-[#05070c]/20">
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
                              <span className="text-[11px] font-mono font-bold text-slate-400 group-hover:text-white uppercase">{symbol}</span>
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
           <div className="flex flex-col h-full bg-[#05070c]/20">
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
        <header className="h-12 shrink-0 flex items-center justify-between px-6 border-b border-border/50 bg-card/70 backdrop-blur-md relative z-20">
            <div className="flex items-center gap-3 min-w-0">
                <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400">
                    <Activity className="w-4 h-4" />
                </div>
                <div className="flex flex-col min-w-0">
                    <input
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className="bg-transparent text-[13px] font-bold text-foreground placeholder-muted-foreground focus:outline-none truncate w-full"
                        placeholder="Untitled Analysis"
                    />
                    <div className="flex items-center gap-2 text-[9px] font-mono text-slate-500 uppercase tracking-tighter">
                        <span>{category || 'Uncategorized'}</span>
                        <span>/</span>
                        <span className="truncate">{tags || 'No Tags'}</span>
                    </div>
                </div>
            </div>

            <div className="flex items-center gap-2">
                <button
                    onClick={handlePreview}
                    disabled={loading}
                    className="group relative flex items-center gap-2 px-4 py-2 text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl shadow-lg shadow-indigo-600/20 transition-all active:scale-95 disabled:opacity-50"
                >
                    {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current group-hover:scale-110 transition-transform" />}
                    <span>Run</span>
                </button>
                <div className="w-px h-5 bg-white/10 mx-1" />
                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="flex items-center gap-2 px-4 py-2 text-xs font-bold text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 rounded-xl transition-all active:scale-95 disabled:opacity-30"
                >
                    {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                    <span>Save</span>
                </button>
                <div className="w-px h-5 bg-white/10 mx-1" />
                <button
                    onClick={() => setShowMeta(!showMeta)}
                    className={`flex items-center gap-2 px-3 py-2 rounded-xl transition-all ${showMeta ? 'text-indigo-400 bg-indigo-500/10 border border-indigo-500/20' : 'text-muted-foreground hover:text-foreground bg-card/60 border border-transparent hover:border-border/50'}`}
                >
                    <Settings className={`w-4 h-4 ${showMeta ? 'animate-spin-slow' : ''}`} />
                    <span className="text-xs font-bold">Properties</span>
                </button>
                <button
                    onClick={toggleCodePanel}
                    className={`p-2.5 rounded-xl transition-all ${showCodePanel ? 'text-indigo-400 bg-indigo-500/10 border border-indigo-500/20' : 'text-muted-foreground hover:text-foreground bg-card/60 border border-transparent hover:border-border/50'}`}
                >
                    <Code className="w-4 h-4" />
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
                    <div className="flex flex-col gap-5 px-8 py-6 max-w-7xl mx-auto">
                        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                            <div className="lg:col-span-3 space-y-2">
                                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] flex items-center gap-2">
                                    <Layers className="w-3 h-3 text-indigo-500" /> Category
                                </label>
                                <input
                                    type="text"
                                    value={category}
                                    onChange={(e) => setCategory(e.target.value)}
                                    className="w-full bg-white/[0.03] border border-white/10 rounded-xl px-4 py-2.5 text-xs text-slate-300 outline-none focus:border-indigo-500/50 transition-all font-semibold"
                                    placeholder="Enter category..."
                                />
                            </div>
                            
                            <div className="lg:col-span-4 space-y-2">
                                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] flex items-center gap-2">
                                    <Search className="w-3 h-3 text-indigo-500" /> Metadata Tags
                                </label>
                                <input
                                    type="text"
                                    value={tags}
                                    onChange={(e) => setTags(e.target.value)}
                                    className="w-full bg-white/[0.03] border border-white/10 rounded-xl px-4 py-2.5 text-xs text-slate-300 outline-none focus:border-indigo-500/50 transition-all font-mono placeholder:text-slate-700"
                                    placeholder="Volatility, Strategy, 2025..."
                                />
                            </div>

                            <div className="lg:col-span-5 space-y-2">
                                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] flex items-center gap-2">
                                    <FileText className="w-3 h-3 text-indigo-500" /> Description
                                </label>
                                <textarea
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    rows={1}
                                    className="w-full bg-white/[0.03] border border-white/10 rounded-xl px-4 py-2.5 text-xs text-slate-300 outline-none focus:border-indigo-500/50 transition-all resize-none font-medium custom-scrollbar min-h-[42px]"
                                    placeholder="Briefly describe the analytical protocol..."
                                />
                            </div>
                        </div>

                        {mode === 'standalone' && (
                            <div className="flex items-center justify-between p-3 bg-indigo-500/[0.02] border border-indigo-500/10 rounded-xl">
                                <div className="flex items-center gap-3">
                                    <div className={`w-2 h-2 rounded-full ${exportPdf ? 'bg-emerald-500 animate-pulse' : 'bg-slate-700'}`} />
                                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Global Report Sync</span>
                                </div>
                                <button
                                    onClick={() => currentChartId ? toggleExportPdf(currentChartId, !exportPdf) : setExportPdf(!exportPdf)}
                                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border transition-all text-[10px] font-bold ${exportPdf ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' : 'text-slate-600 border-white/10 bg-white/5'}`}
                                >
                                    <CheckCircle2 className="w-3.5 h-3.5" />
                                    {exportPdf ? 'ACTIVE' : 'DISABLED'}
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
            <div className="flex-grow relative bg-[#010205] flex flex-col min-h-0">
                <div className="flex-grow relative overflow-hidden">
                    {previewFigure ? (
                        <Plot
                        data={previewFigure.data}
                        layout={{ 
                            ...previewFigure.layout, 
                            autosize: true,
                            paper_bgcolor: 'rgba(0,0,0,0)',
                            plot_bgcolor: 'rgba(0,0,0,0)',
                            font: { color: '#94a3b8', family: 'Inter' },
                        }}
                        config={{ responsive: true, displayModeBar: 'hover', displaylogo: false }}
                        style={{ width: '100%', height: '100%' }}
                        useResizeHandler={true}
                        className="w-full h-full"
                        onInitialized={(_: any, gd: any) => setGraphDiv(gd)}
                        />
                    ) : (
                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                            <div className="relative">
                                <div className="absolute inset-0 blur-3xl bg-indigo-500/20 rounded-full" />
                                <div className="relative w-24 h-24 rounded-3xl bg-white/[0.03] border border-white/10 flex items-center justify-center backdrop-blur-sm">
                                    <Activity className="w-10 h-10 text-slate-700" />
                                </div>
                            </div>
                            <h3 className="text-sm font-bold text-slate-400 mt-6 uppercase tracking-[0.2em]">IDE Forge Ready</h3>
                            <p className="text-[10px] text-slate-600 font-mono mt-2">Initialize analysis or select from library</p>
                        </div>
                    )}

                    {/* Quick Floating Actions */}
                    {previewFigure && (
                        <div className="absolute top-4 right-4 flex gap-2">
                            <button
                                onClick={handleCopyChart}
                                className="p-2 rounded-xl bg-black/40 backdrop-blur-xl border border-white/10 text-slate-400 hover:text-white hover:border-white/20 transition-all"
                                title="Copy Image"
                            >
                                {copying ? <Loader2 className="w-4 h-4 animate-spin" /> : <Copy className="w-4 h-4" />}
                            </button>
                        </div>
                    )}
                </div>

                {/* Console Drawer (Bottom) */}
                <div className={`shrink-0 border-t border-white/5 bg-[#05070c]/80 backdrop-blur-xl transition-all duration-300 ${consoleExpanded ? 'h-[250px]' : 'h-10'}`}>
                    <div className="h-10 shrink-0 flex items-center justify-between px-6 cursor-pointer hover:bg-white/[0.02]" onClick={() => {
                        const next = !consoleExpanded;
                        setConsoleExpanded(next);
                        setUserManuallyCollapsed(!next); // If we are closing it, mark as manual collapse
                    }}>
                        <div className="flex items-center gap-3">
                            <Terminal className={`w-4 h-4 ${error ? 'text-rose-400' : 'text-slate-500'}`} />
                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Execution Log</span>
                            {loading && <Loader2 className="w-3 h-3 text-indigo-400 animate-spin" />}
                        </div>
                        <div className="flex items-center gap-2">
                            {error && <span className="text-[9px] font-mono text-rose-500 px-2 py-0.5 rounded-full bg-rose-500/10 border border-rose-500/20">ERROR</span>}
                            {successMsg && !error && <span className="text-[9px] font-mono text-emerald-500 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">SUCCESS</span>}
                            <button className="text-slate-600 hover:text-white">
                                {consoleExpanded ? <ChevronDown className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                            </button>
                        </div>
                    </div>
                    {consoleExpanded && (
                        <div className="flex-grow h-[210px] overflow-y-auto px-6 py-4 font-mono text-[11px] leading-relaxed custom-scrollbar">
                           <AnimatePresence mode="wait">
                                {error ? (
                                    <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-3">
                                        <div className="flex items-center gap-2 text-rose-400">
                                            <AlertCircle className="w-4 h-4" />
                                            <span className="font-bold underline uppercase tracking-tighter">System Interrupt / Fault</span>
                                        </div>
                                        <div className="p-4 bg-rose-500/5 border border-rose-500/10 rounded-xl text-rose-200/90 whitespace-pre-wrap font-mono text-[10px] leading-relaxed">
                                            {typeof error === 'object' ? error.message : String(error)}
                                        </div>
                                        {typeof error === 'object' && error.traceback && (
                                            <pre className="p-4 bg-black/40 rounded-xl border border-white/5 text-[10px] text-slate-500 overflow-x-auto whitespace-pre-wrap">
                                                {error.traceback}
                                            </pre>
                                        )}
                                    </motion.div>
                                ) : successMsg ? (
                                    <motion.div key="success" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-3 text-emerald-400/80">
                                        <CheckCircle2 className="w-4 h-4" />
                                        <span>{successMsg}</span>
                                    </motion.div>
                                ) : (
                                    <div className="text-slate-700 italic">&gt; Kernel idle. Ready for instruction.</div>
                                )}
                           </AnimatePresence>
                        </div>
                    )}
                </div>
            </div>
        </div>
      </main>

      {/* ═══════════════ RESIZE HANDLE ═══════════════ */}
      {showCodePanel && (
        <div
          onMouseDown={startResize}
          className="hidden lg:flex w-1 shrink-0 cursor-col-resize hover:bg-indigo-500/50 transition-colors z-30"
        />
      )}

      {/* ═══════════════ RIGHT — Editor ═══════════════ */}
      <div
        className={`
          flex-col bg-[#0d0f14] relative z-20 border-l border-white/5
          ${mobilePanel === 'editor' ? 'fixed inset-0 pt-16 z-50 flex shadow-2xl' : 'hidden lg:flex'}
          ${showCodePanel ? 'lg:flex' : 'lg:hidden'}
        `}
        style={{ width: isMounted && showCodePanel && window.innerWidth >= 1024 ? editorWidth : '100%' }}
      >
        <div className="h-12 shrink-0 flex items-center justify-between px-4 bg-[#0d0f14] border-b border-white/5">
            <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
                <span className="text-[10px] font-mono text-slate-400 uppercase tracking-widest opacity-50">analysis.py</span>
            </div>
            <div className="flex items-center gap-3">
                <span className="text-[9px] text-slate-600 font-mono">Kernel: Python 3.12</span>
            </div>
        </div>
        
        <div className="flex-grow flex flex-col min-h-0 bg-background">
            <Editor
                height="100%"
                defaultLanguage="python"
                value={code}
                theme={isLight ? 'vs' : 'vs-dark'}
                onChange={(value: string | undefined) => setCode(value || '')}
                options={{
                minimap: { enabled: false },
                fontSize: editorFontSize,
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                padding: { top: 12, bottom: 12 },
                fontFamily: editorFontFamily,
                renderLineHighlight: 'gutter',
                bracketPairColorization: { enabled: true },
                smoothScrolling: true,
                cursorBlinking: 'smooth',
                wordWrap: 'on',
                }}
            />
        </div>
      </div>


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
               className="absolute inset-0 bg-black/60 backdrop-blur-sm"
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
