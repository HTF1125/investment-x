'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { useAuth } from '@/context/AuthContext';
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search, Plus, Trash2, Edit3, Save, X, ChevronLeft, ChevronRight,
  Database, RefreshCw, Loader2, AlertTriangle, Check, Star, Mail,
  LineChart, Download, Upload, ChevronDown
} from 'lucide-react';
import dynamic from 'next/dynamic';
import { apiFetch, apiFetchJson } from '@/lib/api';
import { useTasks } from './TaskProvider';

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full w-full">
      <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
    </div>
  ),
}) as any;

// ────────────────────────────────────────────────── Types
interface Timeseries {
  id: string;
  code: string;
  name: string | null;
  provider: string | null;
  asset_class: string | null;
  category: string | null;
  start: string | null;
  end: string | null;
  num_data: number | null;
  source: string | null;
  source_code: string | null;
  frequency: string | null;
  unit: string | null;
  scale: number | null;
  currency: string | null;
  country: string | null;
  remark: string | null;
  favorite: boolean;
}

interface ProcessInfo {
  id: string;
  name: string;
  status: 'running' | 'completed' | 'failed';
  start_time: string;
  end_time?: string;
  message?: string;
  progress?: string;
}

const EMPTY_FORM: Omit<Timeseries, 'id' | 'start' | 'end' | 'num_data'> = {
  code: '', name: '', provider: '', asset_class: '', category: '',
  source: '', source_code: '', frequency: '', unit: '', scale: 1,
  currency: '', country: '', remark: '', favorite: false,
};

const PAGE_SIZE = 30;

// ────────────────────────────────────────────────── Component
export default function TimeseriesManager() {
  const { token } = useAuth();
  const queryClient = useQueryClient();

  // State
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [page, setPage] = useState(0);

  // Modals
  const [showCreate, setShowCreate] = useState(false);
  const [editItem, setEditItem] = useState<Timeseries | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Timeseries | null>(null);
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error'; sticky?: boolean } | null>(null);

  // Form state
  const [form, setForm] = useState(EMPTY_FORM);

  // Update Task State
  const [updating, setUpdating] = useState(false);
  const [emailing, setEmailing] = useState(false);
  const [updateMsg, setUpdateMsg] = useState('');

  // Chart Viewer State
  const [viewChartItem, setViewChartItem] = useState<Timeseries | null>(null);

  // Download State
  const [downloading, setDownloading] = useState(false);
  const [showActionsMenu, setShowActionsMenu] = useState(false);
  const [showDownloadMenu, setShowDownloadMenu] = useState(false);
  const [actionsMenuPos, setActionsMenuPos] = useState<{ top: number; left: number }>({ top: 0, left: 0 });
  const [availableSources, setAvailableSources] = useState<string[]>([]);
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const downloadMenuRef = useRef<HTMLDivElement>(null);
  const actionsBtnRef = useRef<HTMLButtonElement>(null);
  const lastDailyProcessIdRef = useRef<string | null>(null);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (toastTimerRef.current) {
        clearTimeout(toastTimerRef.current);
      }
    };
  }, []);

  // Close download menu on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (downloadMenuRef.current && !downloadMenuRef.current.contains(e.target as Node)) {
        if (actionsBtnRef.current && actionsBtnRef.current.contains(e.target as Node)) return;
        setShowActionsMenu(false);
        setShowDownloadMenu(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Fetch available sources when menu opens
  useEffect(() => {
    if (!showDownloadMenu || availableSources.length > 0) return;
    (async () => {
      try {
        const res = await apiFetch('/api/timeseries/sources');
        if (res.ok) {
          const data = await res.json();
          setAvailableSources(data);
        }
      } catch { /* silent */ }
    })();
  }, [showDownloadMenu, availableSources.length]);

  const positionActionsMenu = useCallback(() => {
    const btn = actionsBtnRef.current;
    if (!btn) return;
    const rect = btn.getBoundingClientRect();
    const menuWidth = 288; // w-72
    const left = Math.max(8, Math.min(window.innerWidth - menuWidth - 8, rect.right - menuWidth));
    setActionsMenuPos({ top: rect.bottom + 8, left });
  }, []);

  useEffect(() => {
    if (!showActionsMenu) return;
    positionActionsMenu();
    const onWindowChange = () => positionActionsMenu();
    window.addEventListener('resize', onWindowChange);
    window.addEventListener('scroll', onWindowChange, true);
    return () => {
      window.removeEventListener('resize', onWindowChange);
      window.removeEventListener('scroll', onWindowChange, true);
    };
  }, [showActionsMenu, positionActionsMenu]);

  // ───── Toast helper
  const flash = useCallback((
    msg: string,
    type: 'success' | 'error',
    opts?: { sticky?: boolean; durationMs?: number }
  ) => {
    if (toastTimerRef.current) {
      clearTimeout(toastTimerRef.current);
      toastTimerRef.current = null;
    }
    const sticky = !!opts?.sticky;
    setToast({ msg, type, sticky });
    if (!sticky) {
      const durationMs = opts?.durationMs ?? 3500;
      toastTimerRef.current = setTimeout(() => setToast(null), durationMs);
    }
  }, []);

  // ───── Debounce search
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(0);
    }, 350);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [search]);

  // ───── Fetch Query
  const fetchTimeseries = async ({ page, search }: { page: number; search: string }) => {
    const params = new URLSearchParams();
    params.set('limit', String(PAGE_SIZE));
    params.set('offset', String(page * PAGE_SIZE));
    if (search) params.set('search', search);

    const res = await apiFetch(`/api/timeseries?${params}`);
    if (!res.ok) throw new Error('Failed to fetch');
    return res.json() as Promise<Timeseries[]>;
  };

  const { data: items = [], isLoading, isPlaceholderData } = useQuery({
    queryKey: ['timeseries', { page, search: debouncedSearch }],
    queryFn: () => fetchTimeseries({ page, search: debouncedSearch }),
    placeholderData: keepPreviousData,
    enabled: true,
  });

  const loading = isLoading; // Alias for UI compatibility

  const { processes: allProcesses } = useTasks();

  const latestDaily = allProcesses.find((p) => p.name.startsWith('Daily Data Update'));

  useEffect(() => {
    if (!latestDaily) return;

    setUpdateMsg(latestDaily.message || (latestDaily.status === 'running' ? 'Running...' : 'Idle'));
    setUpdating(latestDaily.status === 'running');

    if (
      latestDaily.id !== lastDailyProcessIdRef.current &&
      latestDaily.status !== 'running'
    ) {
      if (latestDaily.status === 'completed') {
        flash('Daily update completed!', 'success', { sticky: true });
        queryClient.invalidateQueries({ queryKey: ['timeseries'] });
      } else if (latestDaily.status === 'failed') {
        flash(latestDaily.message || 'Daily update failed', 'error', { sticky: true });
      }
    }
    lastDailyProcessIdRef.current = latestDaily.id;
  }, [latestDaily, flash, queryClient]);

  // ───── Fetch Chart Data
  const { data: chartData, isLoading: chartLoading } = useQuery({
    queryKey: ['series-data', viewChartItem?.code],
    queryFn: async () => {
      if (!viewChartItem?.code) return null;
      // Fetch using the advanced series API to get processed data
      const params = new URLSearchParams();
      // Use Series('CODE') to fetch
      params.set('series', `Series('${viewChartItem.code}')`);
      
      const res = await apiFetch(`/api/series?${params}`);
      if (!res.ok) throw new Error('Failed to fetch data');
      return res.json();
    },
    enabled: !!viewChartItem,
  });

  const plotData = React.useMemo(() => {
    if (!chartData || !viewChartItem) return [];
    return [
      {
        x: chartData.Date || [],
        y: chartData[Object.keys(chartData).find(k => k !== 'Date') || ''] || [],
        type: 'scatter',
        mode: 'lines',
        line: { color: '#6366f1', width: 2.5 },
        fill: 'tozeroy',
        fillcolor: 'rgba(99, 102, 241, 0.1)',
        name: viewChartItem.code
      }
    ];
  }, [chartData, viewChartItem]);

  const plotLayout = React.useMemo(() => ({
    autosize: true,
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: '#94a3b8', family: 'Inter, sans-serif' },
    margin: { l: 60, r: 30, t: 40, b: 50 },
    xaxis: {
      gridcolor: 'rgba(255,255,255,0.05)',
      zerolinecolor: 'rgba(255,255,255,0.1)',
      showgrid: true,
      tickfont: { size: 11 },
    },
    yaxis: {
      gridcolor: 'rgba(255,255,255,0.05)',
      zerolinecolor: 'rgba(255,255,255,0.1)',
      showgrid: true,
      tickfont: { size: 11 },
    },
    hovermode: 'x' as const,
    hoverdistance: 20,
    showlegend: false,
    dragmode: 'pan' as const
  }), []);

  const plotConfig = React.useMemo(() => ({ responsive: true, displayModeBar: true, displaylogo: false, scrollZoom: true }), []);
  const plotStyle = React.useMemo(() => ({ width: '100%', height: '100%' }), []);

  // ───── Mutations
  const createMutation = useMutation({
    mutationFn: async (newItem: typeof form) => {
        const res = await fetch(`/api/timeseries/${encodeURIComponent(newItem.code.trim())}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
            body: JSON.stringify(newItem),
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Create failed');
        }
        return res.json();
    },
    onSuccess: (data) => {
        flash(`Created "${data.code}"`, 'success');
        setShowCreate(false);
        setForm({ ...EMPTY_FORM });
        queryClient.invalidateQueries({ queryKey: ['timeseries'] });
    },
    onError: (err: any) => flash(err.message, 'error'),
  });

  const updateMutation = useMutation({
    mutationFn: async ({ code, data }: { code: string; data: typeof form }) => {
        const res = await fetch(`/api/timeseries/${encodeURIComponent(code)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
            body: JSON.stringify(data),
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Update failed');
        }
        return res.json();
    },
    onSuccess: (data) => {
        flash(`Updated "${data.code}"`, 'success');
        setEditItem(null);
        setForm({ ...EMPTY_FORM });
        queryClient.invalidateQueries({ queryKey: ['timeseries'] });
    },
    onError: (err: any) => flash(err.message, 'error'),
  });

  const deleteMutation = useMutation({
    mutationFn: async (code: string) => {
        const res = await fetch(`/api/timeseries/${encodeURIComponent(code)}`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok && res.status !== 204) {
            const err = await res.json();
            throw new Error(err.detail || 'Delete failed');
        }
    },
    onSuccess: (_, code) => {
        flash(`Deleted "${code}"`, 'success');
        setDeleteTarget(null);
        queryClient.invalidateQueries({ queryKey: ['timeseries'] });
    },
    onError: (err: any) => flash(err.message, 'error'),
  });

  // ───── Update Trigger
  const handleTriggerUpdate = async () => {
    if (updating) return;
    try {
        setUpdating(true);
        setUpdateMsg('Starting update...');
        const res = await apiFetch('/api/task/daily', { method: 'POST' });
        
        if (!res.ok) {
            const err = await res.json();
            if (res.status === 400 && err.detail === "Daily task is already running") {
                // Should just start polling
            } else {
                throw new Error(err.detail || 'Failed to start');
            }
        }
        queryClient.invalidateQueries({ queryKey: ['task-processes'] });
    } catch (e: any) {
        flash(e.message, 'error');
        setUpdating(false);
    }
  };

  const handleSendEmail = async () => {
    if (emailing) return;
    try {
        setEmailing(true);
        flash('Triggering email report...', 'success');
        const res = await apiFetch('/api/task/report', { method: 'POST' });
        
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Failed to send email');
        }
        flash('Email report task started!', 'success');
    } catch (e: any) {
        flash(e.message, 'error');
    } finally {
        setTimeout(() => setEmailing(false), 2000);
    }
  };

  // ───── Handlers
  const handleCreate = () => {
      if (!form.code.trim()) { flash('Code is required', 'error'); return; }
      createMutation.mutate(form);
  };

  const handleUpdate = () => {
      if (!editItem) return;
      updateMutation.mutate({ code: editItem.code, data: form });
  };

  const handleDelete = () => {
      if (!deleteTarget) return;
      deleteMutation.mutate(deleteTarget.code);
  };
  
  const saving = createMutation.isPending || updateMutation.isPending;
  const deleting = deleteMutation.isPending;
  const hasMore = items.length === PAGE_SIZE; // Approximation

  // ───── Upload
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    const isDev = window.location.port === '3000';
    const base = isDev ? `${window.location.protocol}//${window.location.hostname}:8000` : '';
    const url = `${base}/api/timeseries/upload_template_data`;

    try {
      flash('Initializing background upload...', 'success');
      
      const res = await fetch(url, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Upload request failed' }));
        throw new Error(err.detail);
      }

      const data = await res.json();
      flash(`Task started: ${file.name}. Monitor progress in the task center.`, 'success', { sticky: true });
      
    } catch (err: any) {
      flash(err.message, 'error');
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // ───── Download Template (multi-source)
  const handleDownloadTemplate = (sources: string[]) => {
    if (downloading || sources.length === 0) return;
    setDownloading(true);
    setShowDownloadMenu(false);
    const label = sources.length === 1 ? sources[0] : `${sources.length} sources`;
    flash(`Downloading ${label} template...`, 'success', { sticky: true });
    
    // Build URL — bypass Next.js proxy (can't handle large binary).
    // In dev, hit backend directly on :8000. In prod, same origin serves both.
    const params = new URLSearchParams();
    sources.forEach((s) => params.append('source', s));
    const isDev = window.location.port === '3000';
    const base = isDev ? `${window.location.protocol}//${window.location.hostname}:8000` : '';
    const url = `${base}/api/timeseries/download_template?${params}`;
    
    // Hidden anchor for clean download (no new tab)
    const a = document.createElement('a');
    a.href = url;
    a.download = '';
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    a.remove();
    
    setTimeout(() => {
      setDownloading(false);
      flash(`Download request sent for ${label}. Check your browser downloads.`, 'success', { sticky: true });
    }, 500);
  };

  const toggleSource = (src: string) => {
    setSelectedSources((prev) =>
      prev.includes(src) ? prev.filter((s) => s !== src) : [...prev, src]
    );
  };


  // ───── Open edit
  const openEdit = (ts: Timeseries) => {
    setEditItem(ts);
    setForm({
      code: ts.code, name: ts.name || '', provider: ts.provider || '',
      asset_class: ts.asset_class || '', category: ts.category || '',
      source: ts.source || '', source_code: ts.source_code || '',
      frequency: ts.frequency || '', unit: ts.unit || '',
      scale: ts.scale ?? 1, currency: ts.currency || '',
      country: ts.country || '', remark: ts.remark || '', favorite: ts.favorite,
    });
  };

  // ───── Render
  return (
    <div className="space-y-6">
      {/* ── Header ── */}
      <div className="rounded-3xl border border-border/50 bg-gradient-to-br from-card/80 via-card/60 to-card/40 backdrop-blur-xl p-6 md:p-8 shadow-xl">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-500 to-fuchsia-600 flex items-center justify-center shadow-lg shadow-violet-500/30">
              <Database className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-foreground tracking-tight">Timeseries Data</h2>
              <p className="text-xs text-muted-foreground font-mono tracking-wider uppercase">Search • Create • Edit • Delete</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 sm:gap-3 w-full md:w-auto">
            {updating && (
                <div className="flex items-center gap-2 px-4 py-2 bg-sky-500/10 text-sky-400 rounded-xl border border-sky-500/20 text-xs font-mono animate-pulse">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    {updateMsg || 'Updating...'}
                </div>
            )}

            {/* Actions Dropdown */}
            <div className="relative" ref={downloadMenuRef}>
              <button
                ref={actionsBtnRef}
                onClick={() => {
                  positionActionsMenu();
                  setShowActionsMenu((p) => !p);
                  if (showActionsMenu) setShowDownloadMenu(false);
                }}
                className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-indigo-500/10 to-violet-500/10 hover:from-indigo-500/20 hover:to-violet-500/20 text-foreground rounded-xl text-sm font-semibold transition-all border border-border/50 shadow-md"
              >
                <Database className="w-4 h-4" />
                Actions
                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showActionsMenu ? 'rotate-180' : ''}`} />
              </button>

              {showActionsMenu && createPortal(
                <div
                  className="fixed w-72 bg-[#0d0f14] dark:bg-[#0d0f14] bg-card border border-border/50 rounded-2xl shadow-2xl shadow-black/60 overflow-hidden z-[120] backdrop-blur-xl"
                  style={{ top: actionsMenuPos.top, left: actionsMenuPos.left }}
                >
                  <div className="p-2">
                    <button
                      onClick={handleTriggerUpdate}
                      disabled={updating}
                      className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-foreground hover:bg-accent/50 transition-all ${updating ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      <RefreshCw className={`w-4 h-4 ${updating ? 'animate-spin' : ''}`} />
                      {updating ? 'Running...' : 'Update Data'}
                    </button>
                    <button
                      onClick={handleSendEmail}
                      disabled={emailing}
                      className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-foreground hover:bg-accent/50 transition-all ${emailing ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      {emailing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mail className="w-4 h-4" />}
                      {emailing ? 'Sending...' : 'Email Report'}
                    </button>
                    <button
                      onClick={() => setShowDownloadMenu((p) => !p)}
                      disabled={downloading}
                      className={`w-full flex items-center justify-between gap-3 px-4 py-3 rounded-xl text-sm font-medium text-foreground hover:bg-accent/50 transition-all ${downloading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      <span className="flex items-center gap-3">
                        {downloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                        {downloading ? 'Preparing...' : 'Download Data'}
                      </span>
                      <ChevronRight className={`w-3.5 h-3.5 transition-transform ${showDownloadMenu ? 'rotate-90' : ''}`} />
                    </button>
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-foreground hover:bg-accent/50 transition-all"
                    >
                      <Upload className="w-4 h-4" /> Upload Data
                    </button>
                    <div className="my-2 h-px bg-border/50" />
                    <button
                      onClick={() => { setShowActionsMenu(false); setShowCreate(true); setForm({ ...EMPTY_FORM }); }}
                      className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold text-indigo-300 hover:text-indigo-200 hover:bg-indigo-500/10 transition-all"
                    >
                      <Plus className="w-4 h-4" /> New Timeseries
                    </button>
                  </div>

                  {showDownloadMenu && (
                    <div className="border-t border-border/50">
                      <div className="px-4 py-3 border-b border-border/50 flex items-center justify-between bg-muted/20">
                        <span className="text-[10px] font-bold tracking-[2px] text-muted-foreground uppercase">Select Sources</span>
                        {availableSources.length > 0 && (
                          <button
                            onClick={() =>
                              setSelectedSources((prev) =>
                                prev.length === availableSources.length ? [] : [...availableSources]
                              )
                            }
                            className="text-[10px] text-indigo-400 hover:text-indigo-300 font-semibold uppercase tracking-wider transition-colors"
                          >
                            {selectedSources.length === availableSources.length ? 'None' : 'All'}
                          </button>
                        )}
                      </div>
                      {availableSources.length === 0 ? (
                        <div className="px-4 py-6 flex items-center justify-center">
                          <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                        </div>
                      ) : (
                        <>
                          <div className="py-1 max-h-64 overflow-y-auto">
                            {availableSources.map((src) => (
                              <label
                                key={src}
                                onClick={() => toggleSource(src)}
                                className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-foreground hover:bg-accent/30 transition-colors cursor-pointer select-none"
                              >
                                <div className={`w-5 h-5 rounded-lg border flex items-center justify-center transition-all ${
                                  selectedSources.includes(src)
                                    ? 'bg-indigo-500 border-indigo-500'
                                    : 'border-border bg-background/40'
                                }`}>
                                  {selectedSources.includes(src) && <Check className="w-3.5 h-3.5 text-white" />}
                                </div>
                                <span className="font-medium">{src}</span>
                              </label>
                            ))}
                          </div>
                          <div className="px-3 py-3 border-t border-border/50 bg-muted/10">
                            <button
                              onClick={() => handleDownloadTemplate(selectedSources)}
                              disabled={selectedSources.length === 0}
                              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-indigo-500 to-violet-500 hover:from-indigo-400 hover:to-violet-400 text-white rounded-xl text-sm font-semibold transition-all shadow-lg shadow-indigo-500/20 disabled:opacity-30 disabled:cursor-not-allowed"
                            >
                              <Download className="w-4 h-4" />
                              Download {selectedSources.length > 0 ? `(${selectedSources.length})` : ''}
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>,
                document.body
              )}
            </div>

            {/* Upload input (triggered by dropdown action) */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleUpload}
              accept=".xlsx"
              className="hidden"
            />
          </div>
        </div>

      {/* ── Search Bar ── */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by code, name, source, category..."
          aria-label="Search timeseries"
          className="w-full pl-12 pr-4 py-3.5 bg-background/60 border border-border/50 rounded-2xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-indigo-500/50 focus:ring-2 focus:ring-indigo-500/20 transition-all text-sm backdrop-blur-sm"
        />
        {search && (
          <button onClick={() => setSearch('')} className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
      </div>

      {/* ── Table ── */}
      <div className="overflow-hidden rounded-3xl border border-border/50 bg-gradient-to-br from-card/80 via-card/60 to-card/40 backdrop-blur-xl shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border/50 bg-gradient-to-r from-muted/30 to-muted/20">
                {['Code', 'Name', 'Provider', 'Asset Class', 'Category', 'Source', 'Source Code', 'Freq', 'Start', 'End', '#', ''].map((h) => (
                  <th key={h} className="px-4 py-3.5 text-left text-[10px] font-bold tracking-[2px] text-muted-foreground uppercase whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className={isPlaceholderData ? 'opacity-50 pointer-events-none transition-opacity' : 'transition-opacity'}>
              {loading && items.length === 0 ? (
                <tr>
                  <td colSpan={12} className="px-4 py-24 text-center">
                    <Loader2 className="w-8 h-8 animate-spin text-indigo-500 mx-auto mb-3" />
                    <p className="text-sm text-muted-foreground">Loading timeseries data...</p>
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={12} className="px-4 py-24 text-center">
                    <Database className="w-12 h-12 text-muted-foreground/30 mx-auto mb-3" />
                    <p className="text-sm text-muted-foreground">No timeseries found.</p>
                  </td>
                </tr>
              ) : (
                items.map((ts) => (
                  <tr
                    key={ts.id}
                    className="border-b border-border/30 hover:bg-accent/10 transition-colors group"
                  >
                    <td className="px-4 py-3.5 font-mono text-indigo-400 text-xs whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        {ts.favorite && <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />}
                        <span className="font-semibold">{ts.code}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3.5 text-foreground text-xs min-w-[200px] whitespace-normal font-medium">{ts.name || '—'}</td>
                    <td className="px-4 py-3.5 text-muted-foreground text-xs">{ts.provider || '—'}</td>
                    <td className="px-4 py-3.5">
                      {ts.asset_class ? (
                        <span className="px-2.5 py-1 text-[10px] font-semibold rounded-lg bg-gradient-to-r from-indigo-500/15 to-violet-500/15 text-indigo-300 border border-indigo-500/20">
                          {ts.asset_class}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="px-4 py-3.5 text-muted-foreground text-xs">{ts.category || '—'}</td>
                    <td className="px-4 py-3.5 text-muted-foreground text-xs max-w-[120px] truncate">{ts.source || '—'}</td>
                    <td className="px-4 py-3.5 text-muted-foreground text-xs font-mono">{ts.source_code || '—'}</td>
                    <td className="px-4 py-3.5 text-muted-foreground text-xs font-mono">{ts.frequency || '—'}</td>
                    <td className="px-4 py-3.5 text-muted-foreground text-xs font-mono whitespace-nowrap">{ts.start || '—'}</td>
                    <td className="px-4 py-3.5 text-muted-foreground text-xs font-mono whitespace-nowrap">{ts.end || '—'}</td>
                    <td className="px-4 py-3.5 text-muted-foreground text-xs font-mono">{ts.num_data?.toLocaleString() ?? '—'}</td>
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-1.5 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => setViewChartItem(ts)}
                          className="p-2 text-muted-foreground hover:text-emerald-400 hover:bg-emerald-500/10 rounded-lg transition-all"
                          title="View Chart"
                        >
                          <LineChart className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => openEdit(ts)}
                          className="p-2 text-muted-foreground hover:text-sky-400 hover:bg-sky-500/10 rounded-lg transition-all"
                          title="Edit"
                        >
                          <Edit3 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setDeleteTarget(ts)}
                          className="p-2 text-muted-foreground hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-all"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 px-6 py-4 border-t border-border/50 bg-gradient-to-r from-muted/20 to-muted/10">
          <span className="text-xs text-muted-foreground font-mono">
            Page {page + 1} • {items.length} items
          </span>
          <div className="flex items-center gap-2">
            <button
              disabled={page === 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent/30 disabled:opacity-30 disabled:cursor-not-allowed transition-all rounded-lg"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <button
              disabled={!hasMore}
              onClick={() => setPage((p) => p + 1)}
              className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent/30 disabled:opacity-30 disabled:cursor-not-allowed transition-all rounded-lg"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* ═══════════════ Create / Edit Modal ═══════════════ */}
      {(showCreate || editItem) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 dark:bg-black/70 backdrop-blur-md" role="dialog" aria-modal="true" aria-label={editItem ? `Edit ${editItem.code}` : 'Create new timeseries'} onClick={() => { setShowCreate(false); setEditItem(null); }}>
          <div
            className="bg-gradient-to-br from-card/95 via-card/90 to-card/85 border border-border/50 rounded-3xl w-full max-w-3xl max-h-[90vh] overflow-y-auto shadow-2xl shadow-black/60 mx-4 backdrop-blur-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sticky top-0 bg-gradient-to-r from-card/95 to-card/90 border-b border-border/50 px-6 py-5 flex items-center justify-between z-10 backdrop-blur-xl">
              <div>
                <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                  {editItem ? <Edit3 className="w-5 h-5 text-indigo-400" /> : <Plus className="w-5 h-5 text-indigo-400" />}
                  {editItem ? `Edit: ${editItem.code}` : 'Create New Timeseries'}
                </h2>
                <p className="text-xs text-muted-foreground font-mono mt-1">
                  {editItem ? 'Update timeseries metadata' : 'Add a new data series to the system'}
                </p>
              </div>
              <button
                onClick={() => { setShowCreate(false); setEditItem(null); }}
                className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent/30 rounded-xl transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Code — required */}
              <FormField label="Code *" value={form.code} onChange={(v) => setForm({ ...form, code: v })} mono disabled={!!editItem} />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField label="Name" value={form.name || ''} onChange={(v) => setForm({ ...form, name: v })} />
                <FormField label="Provider" value={form.provider || ''} onChange={(v) => setForm({ ...form, provider: v })} />
                <FormField label="Asset Class" value={form.asset_class || ''} onChange={(v) => setForm({ ...form, asset_class: v })} />
                <FormField label="Category" value={form.category || ''} onChange={(v) => setForm({ ...form, category: v })} />
                <FormField label="Source" value={form.source || ''} onChange={(v) => setForm({ ...form, source: v })} />
                <FormField label="Source Code" value={form.source_code || ''} onChange={(v) => setForm({ ...form, source_code: v })} mono />
                <FormField label="Frequency" value={form.frequency || ''} onChange={(v) => setForm({ ...form, frequency: v })} placeholder="e.g. D, W, M, Q" />
                <FormField label="Unit" value={form.unit || ''} onChange={(v) => setForm({ ...form, unit: v })} />
                <FormField label="Scale" value={String(form.scale ?? 1)} onChange={(v) => setForm({ ...form, scale: Number(v) || 1 })} type="number" />
                <FormField label="Currency" value={form.currency || ''} onChange={(v) => setForm({ ...form, currency: v })} placeholder="e.g. USD, KRW" />
                <FormField label="Country" value={form.country || ''} onChange={(v) => setForm({ ...form, country: v })} />
              </div>

              <FormField label="Remark" value={form.remark || ''} onChange={(v) => setForm({ ...form, remark: v })} multiline />

              {/* Favorite toggle */}
              <label className="flex items-center gap-3 cursor-pointer group">
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={form.favorite}
                    onChange={(e) => setForm({ ...form, favorite: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-muted rounded-full peer peer-checked:bg-amber-500 transition-colors" />
                  <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
                </div>
                <span className="text-sm text-muted-foreground group-hover:text-foreground transition-colors font-medium flex items-center gap-2">
                  <Star className="w-4 h-4" />
                  Mark as Favorite
                </span>
              </label>
            </div>

            {/* Footer */}
            <div className="sticky bottom-0 bg-gradient-to-r from-card/95 to-card/90 border-t border-border/50 px-6 py-5 flex items-center justify-end gap-3 backdrop-blur-xl">
              <button
                onClick={() => { setShowCreate(false); setEditItem(null); }}
                className="px-6 py-2.5 text-sm font-semibold text-muted-foreground hover:text-foreground bg-background/60 hover:bg-accent/40 rounded-xl transition-all border border-border/50"
              >
                Cancel
              </button>
              <button
                onClick={editItem ? handleUpdate : handleCreate}
                disabled={saving}
                className="flex items-center gap-2 px-6 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-indigo-500 to-violet-500 hover:from-indigo-400 hover:to-violet-400 rounded-xl transition-all shadow-lg shadow-indigo-500/30 disabled:opacity-50"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                {editItem ? 'Update' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════ Delete Confirmation ═══════════════ */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 dark:bg-black/70 backdrop-blur-md" role="dialog" aria-modal="true" aria-label="Delete confirmation" onClick={() => setDeleteTarget(null)}>
          <div
            className="bg-gradient-to-br from-card/95 via-card/90 to-card/85 border border-rose-500/30 rounded-3xl w-full max-w-md shadow-2xl shadow-black/60 p-8 mx-4 backdrop-blur-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-4 mb-6">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-rose-500/20 to-red-500/20 flex items-center justify-center border border-rose-500/30">
                <AlertTriangle className="w-7 h-7 text-rose-400" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-foreground">Delete Timeseries</h3>
                <p className="text-xs text-muted-foreground mt-1">This action cannot be undone.</p>
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-8 leading-relaxed">
              Are you sure you want to delete <span className="font-mono text-rose-300 font-semibold">{deleteTarget.code}</span>
              {deleteTarget.name ? ` (${deleteTarget.name})` : ''}? All associated data will be permanently removed.
            </p>
            <div className="flex items-center justify-end gap-3">
              <button
                onClick={() => setDeleteTarget(null)}
                className="px-6 py-2.5 text-sm font-semibold text-muted-foreground hover:text-foreground bg-background/60 hover:bg-accent/40 rounded-xl transition-all border border-border/50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="flex items-center gap-2 px-6 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-500 hover:to-red-500 rounded-xl transition-all shadow-lg shadow-rose-500/30 disabled:opacity-50"
              >
                {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════ Toast ═══════════════ */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className={`fixed bottom-6 left-6 right-6 sm:left-auto sm:right-6 sm:max-w-md z-[60] flex items-start sm:items-center gap-3 px-5 py-4 rounded-2xl shadow-2xl backdrop-blur-xl border ${
              toast.type === 'success'
                ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300'
                : 'bg-rose-500/15 border-rose-500/30 text-rose-300'
            }`}
            role="alert"
          >
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
              toast.type === 'success' ? 'bg-emerald-500/20' : 'bg-rose-500/20'
            }`}>
              {toast.type === 'success' ? <Check className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
            </div>
            <div className="flex-1 flex items-start sm:items-center gap-3 min-w-0">
              <span className="text-sm font-medium break-words">{toast.msg}</span>
              {toast.sticky && (
                <button
                  onClick={() => setToast(null)}
                  className="px-3 py-1.5 rounded-lg border border-current/30 text-xs font-semibold hover:bg-foreground/[0.08] transition-colors shrink-0"
                >
                  OK
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ═══════════════ Chart Modal ═══════════════ */}
      {viewChartItem && (
        <div
          className="fixed inset-0 z-[70] flex items-center justify-center bg-foreground/40 dark:bg-black/80 backdrop-blur-md p-4"
          role="dialog"
          onClick={() => setViewChartItem(null)}
        >
          <div
             className="bg-gradient-to-br from-card/95 via-card/90 to-card/85 border border-border/50 rounded-3xl w-full max-w-6xl h-[85dvh] sm:h-[85vh] flex flex-col shadow-2xl overflow-hidden backdrop-blur-xl"
             onClick={(e) => e.stopPropagation()}
          >
            <div className="shrink-0 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 px-6 py-5 border-b border-border/50 bg-gradient-to-r from-card/95 to-card/90 backdrop-blur-xl">
              <div>
                <h2 className="text-xl font-bold text-foreground flex items-center gap-3">
                   <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                     <LineChart className="w-5 h-5 text-white" />
                   </div>
                   {viewChartItem.name || viewChartItem.code}
                </h2>
                <p className="text-xs text-muted-foreground font-mono mt-1.5 tracking-wide">
                  {viewChartItem.code} • {viewChartItem.frequency || 'N/A'} • {viewChartItem.provider || 'Unknown Provider'}
                </p>
              </div>
              <button
                onClick={() => setViewChartItem(null)}
                className="p-2.5 text-muted-foreground hover:text-foreground hover:bg-accent/30 rounded-xl transition-all"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="flex-grow relative bg-gradient-to-br from-background/60 to-background/40">
               {/* Loading State */}
               {chartLoading && (
                 <div className="absolute inset-0 z-10 flex items-center justify-center flex-col gap-4 bg-background/80 backdrop-blur-sm">
                   <Loader2 className="w-12 h-12 text-indigo-500 animate-spin" />
                   <p className="text-sm text-muted-foreground font-medium">Loading timeseries data...</p>
                 </div>
               )}

               {/* Chart */}
               {chartData && (
                 <div className="w-full h-full p-6">
                  <Plot
                      data={plotData}
                      layout={plotLayout}
                      config={plotConfig}
                      style={plotStyle}
                  />
                 </div>
               )}

               {/* Empty State */}
               {!chartLoading && (!chartData || Object.keys(chartData).length <= 1) && (
                 <div className="absolute inset-0 flex items-center justify-center text-muted-foreground flex-col gap-3">
                    <div className="w-16 h-16 rounded-2xl bg-muted/20 flex items-center justify-center">
                      <AlertTriangle className="w-8 h-8 opacity-50" />
                    </div>
                    <p className="text-sm font-medium">No data available for this series.</p>
                 </div>
               )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────── Form Field Component
function FormField({
  label, value, onChange, mono, disabled, multiline, placeholder, type = 'text'
}: {
  label: string; value: string; onChange: (v: string) => void;
  mono?: boolean; disabled?: boolean; multiline?: boolean; placeholder?: string; type?: string;
}) {
  const cls = `w-full px-4 py-3 bg-background/60 border border-border/50 rounded-xl text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-indigo-500/50 focus:ring-2 focus:ring-indigo-500/20 transition-all disabled:opacity-40 disabled:cursor-not-allowed backdrop-blur-sm ${mono ? 'font-mono' : ''}`;

  return (
    <div>
      <label className="block text-[11px] font-bold tracking-wider text-muted-foreground uppercase mb-2">{label}</label>
      {multiline ? (
        <textarea value={value} onChange={(e) => onChange(e.target.value)} className={`${cls} min-h-[100px] resize-y`} disabled={disabled} placeholder={placeholder} />
      ) : (
        <input type={type} value={value} onChange={(e) => onChange(e.target.value)} className={cls} disabled={disabled} placeholder={placeholder} />
      )}
    </div>
  );
}
