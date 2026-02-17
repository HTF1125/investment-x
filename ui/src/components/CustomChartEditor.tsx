'use client';

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import dynamic from 'next/dynamic';
import { useAuth } from '@/context/AuthContext';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Loader2, Play, Save, Code, FileText, 
  Download, Copy, Trash2, Plus, Terminal, Search,
  Maximize2, Minimize2, AlertCircle, CheckCircle2,
  Eye, PanelLeftClose, PanelLeft, PanelRightClose, PanelRight, FileDown, ChevronDown,
  GripVertical,
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

export default function CustomChartEditor() {
  const { token } = useAuth();
  const queryClient = useQueryClient();

  // --- State ---
  const [code, setCode] = useState<string>(DEFAULT_CODE);
  const [name, setName] = useState('Untitled Analysis');
  const [category, setCategory] = useState('Personal');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('');
  const [currentChartId, setCurrentChartId] = useState<string | null>(null);
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
  const [consoleExpanded, setConsoleExpanded] = useState(false);

  // Library panel state
  const [libraryOpen, setLibraryOpen] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('All');

  // Mobile: which panel is active
  const [mobilePanel, setMobilePanel] = useState<'editor' | 'workspace'>('workspace');

  const [editorWidth, setEditorWidth] = useState(440);
  const [showCodePanel, setShowCodePanel] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
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
  const { data: savedCharts = [] } = useQuery({
    queryKey: ['custom-charts'],
    queryFn: async () => {
      const res = await fetch('/api/custom', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to load charts');
      return res.json();
    },
    enabled: !!token,
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

  // Count of charts flagged for PDF export
  const pdfCount = useMemo(() => orderedCharts.filter((c: any) => c.export_pdf).length, [orderedCharts]);

  const reorderMutation = useMutation({
    mutationFn: async (items: any[]) => {
      const payload = { items: items.map((c: any) => ({ id: c.id })) };
      const res = await fetch('/api/custom/reorder', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error('Reorder failed');
      return res.json();
    },
  });

  useEffect(() => {
    if (orderedCharts.length === 0 || !isLoaded) return;
    const timer = setTimeout(() => reorderMutation.mutate(orderedCharts), 1500);
    return () => clearTimeout(timer);
  }, [orderedCharts, isLoaded]);

  const previewMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/custom/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ code }),
      });
      
      const contentType = res.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        const data = await res.json();
        if (!res.ok) {
           const errorObj = typeof data.detail === 'object' ? data.detail : data;
           throw errorObj;
        }
        return data;
      } else {
        const text = await res.text();
        if (!res.ok) throw new Error(text || `Server Error: ${res.status}`);
        return text;
      }
    },
    onSuccess: (data: any) => {
      setPreviewFigure(data);
      setPreviewError(null);
      setSuccessMsg('Execution completed.');
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
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(payload),
      });

      const contentType = res.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        const data = await res.json();
        if (!res.ok) {
           const errorObj = typeof data.detail === 'object' ? data.detail : data;
           throw errorObj;
        }
        return { data, method };
      } else {
        const text = await res.text();
        if (!res.ok) throw new Error(text || `Server Error: ${res.status}`);
        return { data: null, method }; // Should not happen
      }
    },
    onSuccess: ({ data, method }: any) => {
      if (method === 'POST') setCurrentChartId(data.id);
      setSuccessMsg(method === 'POST' ? 'Analysis created.' : 'Analysis saved.');
      setPreviewError(null);
      queryClient.invalidateQueries({ queryKey: ['custom-charts'] });
      if (!previewFigure) previewMutation.mutate();
    },
    onError: (err: any) => {
      setPreviewError(err);
      setSuccessMsg(null);
      setConsoleExpanded(true);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (chartId: string) => {
      const res = await fetch(`/api/custom/${chartId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Delete failed');
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
      await fetch('/api/custom/export-pdf', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
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
      const res = await fetch('/api/custom/pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
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
    <div className="flex h-screen w-screen overflow-hidden pt-16 bg-[#0a0c10]">

      {/* ═══════════════ MOBILE TAB BAR ═══════════════ */}
      <div className="lg:hidden fixed bottom-0 left-0 right-0 z-50 h-12 bg-[#0d0f14] border-t border-white/[0.08] flex items-center justify-around px-2">
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

      {/* ═══════════════ LEFT SIDEBAR — Library ═══════════════ */}
      <aside className={`
        ${libraryOpen ? 'w-72' : 'w-12'} shrink-0 flex-col border-r border-white/[0.06] bg-[#0d0f14] transition-all duration-300
        ${libraryOpen ? 'flex' : 'flex'}
        lg:flex
      `}>
        {/* Sidebar Header */}
        <div className="h-11 shrink-0 flex items-center justify-between px-3 border-b border-white/[0.06]">
          {libraryOpen && (
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-widest">Library</span>
              <span className="text-[9px] tabular-nums px-1.5 py-0.5 rounded-full bg-white/[0.06] text-slate-500 font-mono">
                {orderedCharts.length}
              </span>
            </div>
          )}
          <button
            onClick={() => setLibraryOpen(!libraryOpen)}
            className="p-1 text-slate-500 hover:text-white hover:bg-white/5 rounded transition-colors"
            aria-label={libraryOpen ? 'Collapse library' : 'Expand library'}
          >
            {libraryOpen ? <PanelLeftClose className="w-3.5 h-3.5" /> : <PanelLeft className="w-3.5 h-3.5" />}
          </button>
        </div>

        {libraryOpen && (
          <>
            {/* New + Export */}
            <div className="p-2 border-b border-white/[0.04] flex gap-1.5">
              <button
                onClick={clearEditor}
                className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium text-indigo-300 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/20 hover:border-indigo-500/30 rounded-lg transition-all"
              >
                <Plus className="w-3.5 h-3.5" /> New
              </button>
              {pdfCount > 0 && (
                <button
                  onClick={handleExportPDF}
                  disabled={exporting}
                  className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-400 hover:text-white bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] rounded-lg transition-all disabled:opacity-40"
                  aria-label="Export PDF"
                >
                  {exporting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                  <span className="tabular-nums">{pdfCount}</span>
                </button>
              )}
            </div>

            {/* Search */}
            <div className="p-2 border-b border-white/[0.04]">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-600" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search charts..."
                  className="w-full pl-8 pr-3 py-2 bg-white/[0.04] border border-white/[0.06] rounded-lg text-xs text-white placeholder:text-slate-600 focus:outline-none focus:border-indigo-500/40 transition-colors"
                  aria-label="Search charts"
                />
              </div>
              {/* Category filter pills */}
              {categories.length > 2 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {categories.map((cat) => (
                    <button
                      key={cat}
                      onClick={() => setCategoryFilter(cat)}
                      className={`px-2 py-0.5 rounded-md text-[10px] font-medium transition-all ${
                        categoryFilter === cat
                          ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                          : 'text-slate-500 hover:text-slate-300 bg-white/[0.03] border border-transparent hover:border-white/[0.08]'
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Chart list */}
            <div className="flex-grow overflow-y-auto pb-14 lg:pb-0">
              {filteredCharts.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
                  <p className="text-xs text-slate-600">
                    {searchQuery || categoryFilter !== 'All'
                      ? 'No charts match your filter.'
                      : 'No saved analyses yet.'}
                  </p>
                </div>
              ) : (
                <div className="py-1">
                  {categoryFilter === 'All' && !searchQuery.trim() ? (
                    <Reorder.Group axis="y" values={orderedCharts} onReorder={setOrderedCharts}>
                      {orderedCharts.map((chart: any) => (
                        <Reorder.Item
                          key={chart.id}
                          value={chart}
                          className={`group flex items-center gap-2 px-2.5 py-2 mx-1 mb-0.5 rounded-lg cursor-grab active:cursor-grabbing select-none transition-colors duration-150 ${
                            currentChartId === chart.id
                              ? 'bg-indigo-500/15 border border-indigo-500/25'
                              : 'border border-transparent hover:bg-white/[0.04] hover:border-white/[0.06]'
                          }`}
                        >
                          {/* Drag Handle (Visual only, whole item is draggable) */}
                          <div className="shrink-0 text-slate-700 group-hover:text-slate-500 mr-1">
                            <GripVertical className="w-3.5 h-3.5" />
                          </div>

                          {/* PDF toggle */}
                          <button
                            onPointerDown={(e) => e.stopPropagation()}
                            onClick={(e) => { e.stopPropagation(); toggleExportPdf(chart.id, !chart.export_pdf); }}
                            className={`shrink-0 p-0.5 rounded transition-colors ${
                              chart.export_pdf
                                ? 'text-emerald-400 hover:text-emerald-300'
                                : 'text-slate-700 hover:text-slate-500'
                            }`}
                            title={chart.export_pdf ? 'Included in PDF — click to exclude' : 'Excluded from PDF — click to include'}
                            aria-label={chart.export_pdf ? 'Remove from PDF export' : 'Add to PDF export'}
                          >
                            <FileDown className="w-3.5 h-3.5" />
                          </button>

                          {/* Chart info */}
                          <div 
                             onPointerDown={(e) => e.stopPropagation()}
                             onClick={() => loadChart(chart)} 
                             className="flex-grow min-w-0 cursor-pointer pl-1"
                          >
                            <div className={`text-[11px] font-medium truncate leading-tight ${
                              currentChartId === chart.id ? 'text-indigo-200' : 'text-slate-300'
                            }`}>
                              {chart.name || 'Untitled'}
                            </div>
                            <div className="text-[10px] text-slate-600 truncate leading-tight mt-0.5">
                              {chart.category}
                              {chart.tags?.length > 0 && (
                                <span className="text-slate-700"> · {chart.tags.slice(0, 2).join(', ')}</span>
                              )}
                            </div>
                          </div>

                          {/* Delete button */}
                          <div className="opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                            {deleteConfirm === chart.id ? (
                              <button
                                onPointerDown={(e) => e.stopPropagation()}
                                onClick={(e) => { e.stopPropagation(); deleteMutation.mutate(chart.id); }}
                                className="p-1 text-rose-400 hover:bg-rose-500/20 rounded transition-colors"
                                title="Confirm Delete"
                              >
                                <CheckCircle2 className="w-3 h-3" />
                              </button>
                            ) : (
                              <button
                                onPointerDown={(e) => e.stopPropagation()}
                                onClick={(e) => { e.stopPropagation(); setDeleteConfirm(chart.id); setTimeout(() => setDeleteConfirm(null), 3000); }}
                                className="p-1 text-slate-700 hover:text-rose-400 hover:bg-white/5 rounded transition-colors"
                                title="Delete"
                              >
                                <Trash2 className="w-3 h-3" />
                              </button>
                            )}
                          </div>
                        </Reorder.Item>
                      ))}
                    </Reorder.Group>
                  ) : (
                    // Non-reorderable filtered list
                    filteredCharts.map((chart: any) => (
                      <div
                        key={chart.id}
                        className={`group flex items-center gap-2 px-2.5 py-2 mx-1 mb-0.5 rounded-lg cursor-pointer select-none transition-all duration-150 ${
                          currentChartId === chart.id
                            ? 'bg-indigo-500/15 border border-indigo-500/25'
                            : 'border border-transparent hover:bg-white/[0.04] hover:border-white/[0.06]'
                        }`}
                      >
                         {/* Spacer for alignment with drag handle */}
                         <div className="w-4 mr-1"></div>

                        {/* PDF toggle */}
                        <button
                          onClick={(e) => { e.stopPropagation(); toggleExportPdf(chart.id, !chart.export_pdf); }}
                          className={`shrink-0 p-0.5 rounded transition-colors ${
                            chart.export_pdf
                              ? 'text-emerald-400 hover:text-emerald-300'
                              : 'text-slate-700 hover:text-slate-500'
                          }`}
                          title={chart.export_pdf ? 'Included in PDF — click to exclude' : 'Excluded from PDF — click to include'}
                          aria-label={chart.export_pdf ? 'Remove from PDF export' : 'Add to PDF export'}
                        >
                          <FileDown className="w-3.5 h-3.5" />
                        </button>

                        {/* Chart info */}
                        <div onClick={() => loadChart(chart)} className="flex-grow min-w-0 pl-1">
                          <div className={`text-[11px] font-medium truncate leading-tight ${
                            currentChartId === chart.id ? 'text-indigo-200' : 'text-slate-300'
                          }`}>
                            {chart.name || 'Untitled'}
                          </div>
                          <div className="text-[10px] text-slate-600 truncate leading-tight mt-0.5">
                            {chart.category}
                            {chart.tags?.length > 0 && (
                              <span className="text-slate-700"> · {chart.tags.slice(0, 2).join(', ')}</span>
                            )}
                          </div>
                        </div>

                        {/* Delete button */}
                        <div className="opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                          {deleteConfirm === chart.id ? (
                            <button
                              onClick={(e) => { e.stopPropagation(); deleteMutation.mutate(chart.id); }}
                              className="p-1 text-rose-400 hover:bg-rose-500/20 rounded transition-colors"
                              title="Confirm Delete"
                            >
                              <CheckCircle2 className="w-3 h-3" />
                            </button>
                          ) : (
                            <button
                              onClick={(e) => { e.stopPropagation(); setDeleteConfirm(chart.id); setTimeout(() => setDeleteConfirm(null), 3000); }}
                              className="p-1 text-slate-700 hover:text-rose-400 hover:bg-white/5 rounded transition-colors"
                              title="Delete"
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* Summary footer */}
            <div className="shrink-0 px-3 py-2 border-t border-white/[0.06] text-[10px] text-slate-600 font-mono hidden lg:block">
              {filteredCharts.length !== orderedCharts.length
                ? `${filteredCharts.length} of ${orderedCharts.length} shown`
                : `${orderedCharts.length} analyses`
              }
              {pdfCount > 0 && <span className="text-emerald-600"> · {pdfCount} in PDF</span>}
            </div>
          </>
        )}

        {/* Collapsed sidebar — icon-only view */}
        {!libraryOpen && (
          <div className="py-2 space-y-1">
            <button onClick={clearEditor} className="w-full flex items-center justify-center p-2 text-indigo-400 hover:bg-indigo-500/15 rounded-lg transition-colors" title="New Analysis">
              <Plus className="w-4 h-4" />
            </button>
            {pdfCount > 0 && (
              <button onClick={handleExportPDF} disabled={exporting} className="w-full flex items-center justify-center p-2 text-slate-500 hover:text-white hover:bg-white/5 rounded-lg transition-colors disabled:opacity-40" title={`Export PDF (${pdfCount})`}>
                {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
              </button>
            )}
          </div>
        )}
      </aside>

      {/* ═══════════════ CENTER — Chart Preview ═══════════════ */}
      <div className={`
        flex-grow flex-col min-w-0 border-r border-white/[0.06]
        flex lg:flex
      `}>
        {/* Chart Toolbar (Center Panel) */}
        <div className="h-11 shrink-0 flex items-center justify-between px-4 border-b border-white/[0.06] bg-[#0d0f14]/80">
          {/* Left: Name Input */}
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="bg-transparent text-[13px] font-semibold text-white placeholder-slate-600 focus:outline-none flex-grow min-w-0 truncate mr-4"
            placeholder="Untitled Analysis"
            aria-label="Analysis name"
          />

          {/* Right: Actions */}
          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 rounded-md transition-all disabled:opacity-50"
              title="Save Analysis (Ctrl+S)"
            >
              {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
              <span className="hidden sm:inline">Save</span>
            </button>
            <button
              onClick={handlePreview}
              disabled={loading}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded-md shadow-lg shadow-indigo-500/20 transition-all disabled:opacity-50"
              title="Run Analysis (Ctrl+Enter)"
            >
              {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3 fill-current" />}
              Run
            </button>
            {previewFigure && (
              <button
                onClick={handleCopyChart}
                disabled={copying}
                className="p-1.5 text-slate-500 hover:text-white hover:bg-white/5 rounded-md transition-colors"
                title="Copy Chart Image"
              >
                {copying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            )}
            <button
              onClick={toggleCodePanel}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] font-semibold border rounded-md transition-all hidden lg:flex ${
                showCodePanel 
                  ? 'text-indigo-300 bg-indigo-500/10 border-indigo-500/20 shadow-sm shadow-indigo-500/10' 
                  : 'text-slate-500 border-transparent hover:text-indigo-300 hover:bg-white/5'
              }`}
              title={showCodePanel ? 'Close Code Editor' : 'Open Code Editor'}
            >
              <Code className="w-3.5 h-3.5" />
              <span>Edit</span>
            </button>
          </div>
        </div>
        
        {/* Metadata Bar (Category, Tags, PDF) */}
        <div className="shrink-0 flex items-center gap-2 px-4 py-2 border-b border-white/[0.04] bg-[#0d0f14]/40">
           <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-32 bg-white/[0.04] border border-white/[0.08] rounded-md px-2 py-1 text-[11px] text-slate-400 focus:border-indigo-500/40 outline-none transition-colors"
              placeholder="Category"
           />
           <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              className="flex-1 min-w-0 bg-white/[0.04] border border-white/[0.08] rounded-md px-2 py-1 text-[11px] text-slate-400 focus:border-indigo-500/40 outline-none transition-colors"
              placeholder="Tags (comma separated)"
           />
           <button
              onClick={() => currentChartId ? toggleExportPdf(currentChartId, !exportPdf) : setExportPdf(!exportPdf)}
              className={`shrink-0 flex items-center gap-1 px-2 py-1 rounded-md border text-[10px] font-medium transition-all ${
                exportPdf
                  ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                  : 'bg-white/[0.02] border-white/[0.08] text-slate-600'
              }`}
              title={exportPdf ? 'Will be included in PDF export' : 'Will NOT be included in PDF export'}
           >
              <FileDown className="w-3 h-3" />
              PDF
           </button>
        </div>

        {/* Chart Canvas */}
        <div className="flex-grow relative min-h-0 bg-gradient-to-br from-[#0a0c10] to-[#0f1318] pb-12 lg:pb-0">
          {previewFigure ? (
            <Plot
              data={previewFigure.data}
              layout={{ ...previewFigure.layout, autosize: true }}
              config={{ responsive: true, displayModeBar: 'hover', displaylogo: false }}
              style={{ width: '100%', height: '100%' }}
              useResizeHandler={true}
              className="w-full h-full"
              onInitialized={(_: any, gd: any) => setGraphDiv(gd)}
            />
          ) : (
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <div className="w-16 h-16 rounded-2xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center mb-4">
                <Play className="w-7 h-7 text-slate-600 ml-0.5" />
              </div>
              <p className="text-sm font-medium text-slate-600">Ready to run</p>
              <p className="text-[11px] text-slate-700 mt-1">
                Press <kbd className="px-1.5 py-0.5 bg-white/[0.06] rounded text-[10px] font-mono border border-white/[0.08]">Ctrl+Enter</kbd> to execute
              </p>
            </div>
          )}
        </div>
      </div>

      {/* ═══════════════ RESIZE HANDLE ═══════════════ */}
      {showCodePanel && (
        <div
          onMouseDown={startResize}
          className="hidden lg:flex w-2 shrink-0 cursor-col-resize items-center justify-center group hover:bg-white/[0.02] active:bg-indigo-500/20 transition-colors relative z-10 -ml-1 border-l border-white/5"
          title="Drag to resize"
          role="separator"
          aria-orientation="vertical"
        >
          <div className="w-1 h-8 rounded-full bg-white/10 group-hover:bg-indigo-500/50 group-active:bg-indigo-500/80 transition-colors" />
        </div>
      )}

      {/* ═══════════════ RIGHT — Code Editor + Console ═══════════════ */}
      <div
        className={`
          w-full lg:w-[440px] shrink-0 flex-col bg-[#0d0f14]
          lg:static lg:h-auto
          ${mobilePanel === 'editor' ? 'fixed top-16 bottom-12 right-0 w-full md:w-[600px] z-50 flex border-l border-white/10 shadow-2xl' : 'hidden'}
          ${showCodePanel ? 'lg:flex' : 'lg:hidden'}
        `}
        style={{ width: isMounted && showCodePanel && window.innerWidth >= 1024 ? editorWidth : undefined }}
      >
        {/* Code Header (Mobile only) */}
        <div className="h-11 shrink-0 flex items-center justify-between px-3 border-b border-white/[0.06] lg:hidden">
            <button
                onClick={() => setMobilePanel('workspace')}
                className="mr-2 p-1 text-slate-400 hover:text-white"
            >
                <ChevronDown className="w-5 h-5" />
            </button>
            <span className="text-xs font-medium text-slate-500">Code Editor</span>
        </div>

        {/* Monaco Code Editor */}
        <div className="flex-grow flex flex-col min-h-0 relative">
          <div className="h-8 shrink-0 bg-[#1e1e1e] border-b border-[#2a2a2a] flex items-center px-3 justify-between">
            <span className="text-[11px] font-mono text-slate-500 flex items-center gap-1.5">
              <Code className="w-3 h-3" /> analysis.py
            </span>
            <span className="text-[10px] text-slate-700 font-mono">Python</span>
          </div>
          <div className="flex-grow min-h-0 bg-[#1e1e1e]">
            <Editor
              height="100%"
              defaultLanguage="python"
              value={code}
              theme="vs-dark"
              onChange={(value: string | undefined) => setCode(value || '')}
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                padding: { top: 12, bottom: 12 },
                fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
                renderLineHighlight: 'gutter',
                lineDecorationsWidth: 0,
                lineNumbersMinChars: 3,
                glyphMargin: false,
                folding: true,
                bracketPairColorization: { enabled: true },
                guides: { indentation: true, bracketPairs: true },
                smoothScrolling: true,
                cursorBlinking: 'smooth',
                cursorSmoothCaretAnimation: 'on',
                wordWrap: 'on',
              }}
            />
          </div>
        </div>

        {/* Console */}
        <div className={`shrink-0 flex flex-col border-t border-white/[0.06] transition-all duration-300 ${consoleExpanded ? 'h-[200px]' : 'h-[80px]'} mb-12 lg:mb-0`}>
          <div className="h-7 shrink-0 flex items-center justify-between px-3 bg-[#0a0c10]">
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
              <Terminal className="w-3 h-3" /> Console
            </span>
            <button
              onClick={() => setConsoleExpanded(!consoleExpanded)}
              className="p-0.5 text-slate-600 hover:text-white transition-colors"
              aria-label={consoleExpanded ? 'Collapse console' : 'Expand console'}
            >
              {consoleExpanded ? <Minimize2 className="w-3 h-3" /> : <Maximize2 className="w-3 h-3" />}
            </button>
          </div>
          <div className="flex-grow overflow-y-auto px-3 py-2 font-mono text-[11px] leading-relaxed bg-[#0a0c10]">
            <AnimatePresence mode="wait">
              {error ? (
                <motion.div key="error" initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="flex items-start gap-2 text-rose-400">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                  <div className="flex flex-col gap-1 min-w-0 flex-1">
                    <span className="font-bold underline">{typeof error === 'object' && (error as any).error ? (error as any).error : 'Error'}:</span>
                    <pre className="whitespace-pre-wrap break-words text-[10px] bg-rose-500/5 p-1.5 rounded">{typeof error === 'object' && (error as any).message ? (error as any).message : String(error)}</pre>
                    {typeof error === 'object' && (error as any).traceback && (
                      <div className="mt-1">
                        <div className="text-[9px] uppercase tracking-wider text-rose-300/80">Traceback</div>
                        <pre className="mt-1 p-2 bg-black/40 rounded border border-rose-500/10 text-[9px] overflow-x-auto whitespace-pre-wrap">
                          {(error as any).traceback}
                        </pre>
                      </div>
                    )}
                  </div>
                </motion.div>
              ) : successMsg ? (
                <motion.div key="success" initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="flex items-start gap-2 text-emerald-400">
                  <CheckCircle2 className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                  <span>{successMsg}</span>
                </motion.div>
              ) : (
                <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-slate-700 italic">
                  &gt; Waiting for execution...
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* PDF Export Notification */}
      <AnimatePresence>
        {pdfStatus !== 'idle' && (
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 50 }}
            className="fixed bottom-6 right-6 z-[60] flex items-center gap-3 px-4 py-3 bg-zinc-900 border border-white/10 rounded-lg shadow-2xl min-w-[300px]"
          >
            {pdfStatus === 'exporting' && <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />}
            {pdfStatus === 'complete' && <CheckCircle2 className="w-5 h-5 text-emerald-400" />}
            {pdfStatus === 'error' && <AlertCircle className="w-5 h-5 text-rose-400" />}
            
            <div className="flex flex-col">
              <span className="text-sm font-medium text-white">
                {pdfStatus === 'exporting' && 'Generating PDF Report...'}
                {pdfStatus === 'complete' && 'Download Ready'}
                {pdfStatus === 'error' && 'Export Failed'}
              </span>
              <span className="text-xs text-slate-400">
                {pdfStatus === 'exporting' ? `Processing ${pdfCount} charts` : 
                 pdfStatus === 'complete' ? 'Check your downloads folder' : 
                 'Please try again'}
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
