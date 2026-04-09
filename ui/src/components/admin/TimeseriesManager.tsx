'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search, Plus, Trash2, Edit3, Save, X, ChevronLeft, ChevronRight,
  Database, RefreshCw, Loader2, AlertTriangle, Check, Star, Mail,
  LineChart, Download, Upload, ChevronDown, FileSpreadsheet
} from 'lucide-react';
import dynamic from 'next/dynamic';
import { apiFetch, apiFetchJson, getDirectApiBase } from '@/lib/api';

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full w-full">
      <Loader2 className="w-8 h-8 text-primary animate-spin" />
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
        line: { color: 'rgb(99,130,255)', width: 2 },
        fill: 'tozeroy',
        fillcolor: 'rgba(99,130,255,0.06)',
        name: viewChartItem.code
      }
    ];
  }, [chartData, viewChartItem]);

  const plotLayout = React.useMemo(() => {
    const isDark = typeof document !== 'undefined' && document.documentElement.classList.contains('dark');
    const fg = isDark ? 'rgb(205,215,230)' : 'rgb(18,20,28)';
    const muted = isDark ? 'rgba(100,110,135,0.9)' : 'rgba(95,92,85,0.9)';
    const grid = isDark ? 'rgba(99,130,255,0.04)' : 'rgba(50,80,210,0.06)';
    return {
      autosize: true,
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { color: fg, family: 'var(--font-mono), "Space Mono", monospace', size: 12 },
      margin: { l: 50, r: 20, t: 30, b: 40 },
      xaxis: { gridcolor: grid, zerolinecolor: grid, showgrid: false, tickfont: { size: 11, color: muted } },
      yaxis: { gridcolor: grid, zerolinecolor: grid, showgrid: false, tickfont: { size: 11, color: muted } },
      hovermode: 'x unified' as const,
      hoverdistance: 20,
      showlegend: false,
      dragmode: 'zoom' as const,
    };
  }, []);

  const plotConfig = React.useMemo(() => ({ responsive: true, displayModeBar: false, displaylogo: false, scrollZoom: true }), []);
  const plotStyle = React.useMemo(() => ({ width: '100%', height: '100%' }), []);

  // ───── Mutations
  const createMutation = useMutation({
    mutationFn: async (newItem: typeof form) => {
        const res = await apiFetch(`/api/timeseries/${encodeURIComponent(newItem.code.trim())}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
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
        const res = await apiFetch(`/api/timeseries/${encodeURIComponent(code)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
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
        const res = await apiFetch(`/api/timeseries/${encodeURIComponent(code)}`, {
            method: 'DELETE',
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
            // 401 is handled by SessionExpiredModal — don't double-flash
            if (res.status === 401) { setUpdating(false); return; }
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
            // 401 is handled by SessionExpiredModal — don't double-flash
            if (res.status === 401) { setEmailing(false); return; }
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

    try {
      flash('Initializing background upload...', 'success');

      const res = await apiFetch('/api/timeseries/upload_template_data', {
        method: 'POST',
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

  // ───── Bulk Create Template
  const bulkCreateInputRef = useRef<HTMLInputElement>(null);

  const handleDownloadCreateTemplate = () => {
    setShowActionsMenu(false);
    flash('Downloading create template...', 'success');
    apiFetch('/api/timeseries/create_template')
      .then(async (res) => {
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: 'Download failed' }));
          throw new Error(err.detail);
        }
        return res.blob();
      })
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'timeseries_create_template.xlsx';
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      })
      .catch((err: any) => {
        flash(err.message || 'Download failed', 'error');
      });
  };

  const [exportingAll, setExportingAll] = useState(false);

  const handleExportAll = () => {
    if (exportingAll) return;
    setExportingAll(true);
    flash('Exporting all timeseries...', 'success');
    apiFetch('/api/timeseries/export_all')
      .then(async (res) => {
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: 'Export failed' }));
          throw new Error(err.detail);
        }
        return res.blob();
      })
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `timeseries_all_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}.xlsx`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        flash('Export complete — edit and re-upload via the create template.', 'success');
      })
      .catch((err: any) => {
        flash(err.message || 'Export failed', 'error');
      })
      .finally(() => setExportingAll(false));
  };

  const handleBulkCreateUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      flash('Uploading timeseries...', 'success');

      const res = await apiFetch('/api/timeseries/create_from_template', {
        method: 'POST',
        body: formData,
        timeoutMs: 120_000,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(err.detail);
      }

      const data = await res.json();
      const parts: string[] = [];
      if (data.created?.length) parts.push(`${data.created.length} created`);
      if (data.updated?.length) parts.push(`${data.updated.length} updated`);
      if (data.data_merged) parts.push(`${data.data_merged} data points merged`);
      if (data.errors?.length) parts.push(`${data.errors.length} errors`);
      flash(parts.join(', ') || data.message, data.errors?.length ? 'error' : 'success', { sticky: true });
      queryClient.invalidateQueries({ queryKey: ['timeseries'] });
    } catch (err: any) {
      flash(err.message, 'error');
    } finally {
      if (bulkCreateInputRef.current) bulkCreateInputRef.current.value = '';
    }
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
  const actionBtn = "h-6 px-2 text-[11px] font-mono font-semibold rounded-[calc(var(--radius)-2px)] disabled:opacity-30 transition-all";

  return (
    <div className="space-y-3">
      {/* ── Toolbar ── */}
      <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
        <span className="text-[11.5px] font-mono text-muted-foreground/40 tabular-nums">
          {!loading && `${items.length}${hasMore ? '+' : ''} series`}
        </span>
        <span className="text-[11.5px] font-mono text-muted-foreground/30">pg {page + 1}</span>

        <div className="flex-1 min-w-[8px]" />

        {/* Search */}
        <div className="relative order-last sm:order-none w-full sm:w-auto">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground/40" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search code, name, source..."
            className="h-7 w-full sm:w-56 pl-7 pr-2.5 text-[12.5px] border border-border/40 rounded-[var(--radius)] bg-background text-foreground placeholder:text-muted-foreground/30 focus:outline-none focus:border-primary/50 transition-colors"
          />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground/30 hover:text-foreground">
              <X className="w-3 h-3" />
            </button>
          )}
        </div>

        {/* Action buttons */}
        <button onClick={handleExportAll} disabled={exportingAll} className="btn-toolbar gap-1" title="Download all timeseries metadata as Excel">
          {exportingAll ? <Loader2 className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />}
          <span className="text-[11.5px] font-semibold hidden sm:inline">Export All</span>
        </button>
        <button onClick={() => { setShowCreate(true); setForm({ ...EMPTY_FORM }); }} className="btn-toolbar gap-1">
          <Plus className="w-3 h-3" /><span className="text-[11.5px] font-semibold hidden sm:inline">New</span>
        </button>

        {/* Hidden file inputs */}
        <input type="file" ref={fileInputRef} onChange={handleUpload} accept=".xlsx" className="hidden" />
        <input type="file" ref={bulkCreateInputRef} onChange={handleBulkCreateUpload} accept=".xlsx" className="hidden" />
      </div>

      {/* ── Flash toast ── */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-[var(--radius)] text-[12.5px] font-medium overflow-hidden ${
              toast.type === 'success'
                ? 'bg-success/[0.06] border border-success/20 text-success'
                : 'bg-destructive/[0.06] border border-destructive/20 text-destructive'
            }`}
          >
            {toast.type === 'success' ? <Check className="w-3 h-3 shrink-0" /> : <AlertTriangle className="w-3 h-3 shrink-0" />}
            <span className="flex-1 truncate">{toast.msg}</span>
            <button onClick={() => setToast(null)} className="opacity-50 hover:opacity-100 shrink-0"><X className="w-3 h-3" /></button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Table (desktop) ── */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border/30">
              {['Code', 'Name', 'Source', 'Class', 'Freq', 'Start', 'End', '#', ''].map(h => (
                <th key={h} className="stat-label text-left px-3 py-2 whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className={isPlaceholderData ? 'opacity-50 pointer-events-none' : ''}>
            {loading && items.length === 0 ? (
              <tr><td colSpan={9} className="py-16 text-center"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground/30 mx-auto" /></td></tr>
            ) : items.length === 0 ? (
              <tr><td colSpan={9} className="py-16 text-center text-[12.5px] text-muted-foreground/30 font-mono">No timeseries found</td></tr>
            ) : items.map(ts => (
              <tr key={ts.id} className="border-b border-border/10 hover:bg-foreground/[0.02] transition-colors group">
                <td className="px-3 py-2 font-mono text-[12.5px] text-primary whitespace-nowrap">
                  <div className="flex items-center gap-1.5">
                    {ts.favorite && <Star className="w-3 h-3 text-warning fill-warning" />}
                    <span className="font-semibold">{ts.code}</span>
                  </div>
                </td>
                <td className="px-3 py-2 text-[12.5px] text-foreground/80 max-w-[200px] truncate">{ts.name || '—'}</td>
                <td className="px-3 py-2 text-[11.5px] text-muted-foreground/50 font-mono truncate max-w-[100px]">{ts.source || '—'}</td>
                <td className="px-3 py-2">
                  {ts.asset_class ? (
                    <span className="px-1.5 py-0.5 text-[11px] font-mono font-semibold rounded-[calc(var(--radius)-2px)] bg-primary/[0.06] text-primary/70 border border-primary/15">
                      {ts.asset_class}
                    </span>
                  ) : <span className="text-[11.5px] text-muted-foreground/30">—</span>}
                </td>
                <td className="px-3 py-2 text-[11.5px] font-mono text-muted-foreground/40">{ts.frequency || '—'}</td>
                <td className="px-3 py-2 text-[11.5px] font-mono text-muted-foreground/40 whitespace-nowrap">{ts.start || '—'}</td>
                <td className="px-3 py-2 text-[11.5px] font-mono text-muted-foreground/40 whitespace-nowrap">{ts.end || '—'}</td>
                <td className="px-3 py-2 text-[11.5px] font-mono text-muted-foreground/40 tabular-nums">{ts.num_data?.toLocaleString() ?? '—'}</td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button onClick={() => setViewChartItem(ts)} className={`${actionBtn} border border-success/20 text-success/60 hover:text-success hover:bg-success/[0.06]`} title="Chart">
                      <LineChart className="w-3 h-3" />
                    </button>
                    <button onClick={() => openEdit(ts)} className={`${actionBtn} border border-primary/20 text-primary/60 hover:text-primary hover:bg-primary/[0.06]`} title="Edit">
                      <Edit3 className="w-3 h-3" />
                    </button>
                    <button onClick={() => setDeleteTarget(ts)} className={`${actionBtn} border border-destructive/20 text-destructive/60 hover:text-destructive hover:bg-destructive/[0.06]`} title="Delete">
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── Card list (mobile) ── */}
      <div className="md:hidden space-y-2">
        {loading && items.length === 0 ? (
          <div className="flex items-center justify-center py-16"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground/30" /></div>
        ) : items.length === 0 ? (
          <div className="py-16 text-center text-[12.5px] text-muted-foreground/30 font-mono">No timeseries found</div>
        ) : items.map(ts => (
          <div key={ts.id} className="panel-card p-3">
            <div className="flex items-start justify-between gap-2 mb-1.5">
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  {ts.favorite && <Star className="w-3 h-3 text-warning fill-warning shrink-0" />}
                  <span className="text-[13px] font-mono font-semibold text-primary truncate">{ts.code}</span>
                </div>
                <div className="text-[12.5px] text-foreground/70 truncate">{ts.name || '—'}</div>
              </div>
              {ts.asset_class && (
                <span className="px-1.5 py-0.5 text-[11px] font-mono font-semibold rounded-[calc(var(--radius)-2px)] bg-primary/[0.06] text-primary/70 border border-primary/15 shrink-0">
                  {ts.asset_class}
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 text-[11.5px] font-mono text-muted-foreground/40 mb-2">
              <span>{ts.source || '—'}</span>
              <span>{ts.frequency || '—'}</span>
              <span>{ts.num_data?.toLocaleString() ?? '—'} pts</span>
            </div>
            <div className="flex items-center gap-0.5">
              <button onClick={() => setViewChartItem(ts)} className={`${actionBtn} border border-success/20 text-success/60 hover:text-success hover:bg-success/[0.06]`}><LineChart className="w-3 h-3" /></button>
              <button onClick={() => openEdit(ts)} className={`${actionBtn} border border-primary/20 text-primary/60 hover:text-primary hover:bg-primary/[0.06]`}><Edit3 className="w-3 h-3" /></button>
              <button onClick={() => setDeleteTarget(ts)} className={`${actionBtn} border border-destructive/20 text-destructive/60 hover:text-destructive hover:bg-destructive/[0.06]`}><Trash2 className="w-3 h-3" /></button>
            </div>
          </div>
        ))}
      </div>

      {/* ── Pagination ── */}
      <div className="flex items-center justify-between">
        <span className="text-[11.5px] font-mono text-muted-foreground/30 tabular-nums">
          Page {page + 1} {items.length > 0 && `· ${items.length} items`}
        </span>
        <div className="flex items-center gap-1">
          <button disabled={page === 0} onClick={() => setPage(p => Math.max(0, p - 1))}
            className="btn-icon disabled:opacity-30"><ChevronLeft className="w-3.5 h-3.5" /></button>
          <button disabled={!hasMore} onClick={() => setPage(p => p + 1)}
            className="btn-icon disabled:opacity-30"><ChevronRight className="w-3.5 h-3.5" /></button>
        </div>
      </div>

      {/* ═══ Create / Edit Modal ═══ */}
      {(showCreate || editItem) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => { setShowCreate(false); setEditItem(null); }}>
          <div className="bg-card border border-border/40 rounded-[var(--radius)] w-full max-w-2xl max-h-[85vh] overflow-y-auto shadow-lg mx-4" onClick={e => e.stopPropagation()}>
            <div className="sticky top-0 bg-card border-b border-border/30 px-4 py-3 flex items-center justify-between z-10">
              <div className="flex items-center gap-2">
                {editItem ? <Edit3 className="w-3.5 h-3.5 text-primary" /> : <Plus className="w-3.5 h-3.5 text-primary" />}
                <span className="text-[13px] font-semibold text-foreground">{editItem ? `Edit: ${editItem.code}` : 'New Timeseries'}</span>
              </div>
              <button onClick={() => { setShowCreate(false); setEditItem(null); }} className="btn-icon"><X className="w-3.5 h-3.5" /></button>
            </div>
            <div className="p-4 space-y-4">
              <FormField label="Code *" value={form.code} onChange={v => setForm({ ...form, code: v })} mono disabled={!!editItem} />
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <FormField label="Name" value={form.name || ''} onChange={v => setForm({ ...form, name: v })} />
                <FormField label="Provider" value={form.provider || ''} onChange={v => setForm({ ...form, provider: v })} />
                <FormField label="Asset Class" value={form.asset_class || ''} onChange={v => setForm({ ...form, asset_class: v })} />
                <FormField label="Category" value={form.category || ''} onChange={v => setForm({ ...form, category: v })} />
                <FormField label="Source" value={form.source || ''} onChange={v => setForm({ ...form, source: v })} />
                <FormField label="Source Code" value={form.source_code || ''} onChange={v => setForm({ ...form, source_code: v })} mono />
                <FormField label="Frequency" value={form.frequency || ''} onChange={v => setForm({ ...form, frequency: v })} placeholder="D, W, M, Q" />
                <FormField label="Unit" value={form.unit || ''} onChange={v => setForm({ ...form, unit: v })} />
                <FormField label="Scale" value={String(form.scale ?? 1)} onChange={v => setForm({ ...form, scale: Number(v) || 1 })} type="number" />
                <FormField label="Currency" value={form.currency || ''} onChange={v => setForm({ ...form, currency: v })} placeholder="USD, KRW" />
                <FormField label="Country" value={form.country || ''} onChange={v => setForm({ ...form, country: v })} />
              </div>
              <FormField label="Remark" value={form.remark || ''} onChange={v => setForm({ ...form, remark: v })} multiline />
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.favorite} onChange={e => setForm({ ...form, favorite: e.target.checked })} className="accent-primary w-3.5 h-3.5" />
                <span className="text-[12.5px] text-muted-foreground/60 flex items-center gap-1.5"><Star className="w-3 h-3" /> Favorite</span>
              </label>
            </div>
            <div className="sticky bottom-0 bg-card border-t border-border/30 px-4 py-3 flex items-center justify-end gap-2">
              <button onClick={() => { setShowCreate(false); setEditItem(null); }} className="btn-toolbar">Cancel</button>
              <button onClick={editItem ? handleUpdate : handleCreate} disabled={saving} className="btn-primary">
                {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                {editItem ? 'Update' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ Delete Confirmation ═══ */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setDeleteTarget(null)}>
          <div className="bg-card border border-destructive/20 rounded-[var(--radius)] w-full max-w-sm shadow-lg p-5 mx-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 rounded-[var(--radius)] bg-destructive/[0.08] flex items-center justify-center shrink-0">
                <AlertTriangle className="w-4 h-4 text-destructive" />
              </div>
              <div>
                <h3 className="text-[13px] font-semibold text-foreground">Delete Timeseries</h3>
                <p className="text-[11.5px] text-muted-foreground/50">This cannot be undone.</p>
              </div>
            </div>
            <p className="text-[12.5px] text-muted-foreground/60 mb-5">
              Delete <span className="font-mono text-destructive font-semibold">{deleteTarget.code}</span>{deleteTarget.name ? ` (${deleteTarget.name})` : ''}?
            </p>
            <div className="flex items-center justify-end gap-2">
              <button onClick={() => setDeleteTarget(null)} className="btn-toolbar">Cancel</button>
              <button onClick={handleDelete} disabled={deleting}
                className="h-7 px-3 text-[12.5px] font-semibold bg-destructive hover:bg-destructive/90 text-destructive-foreground rounded-[var(--radius)] transition-all disabled:opacity-50 flex items-center gap-1.5">
                {deleting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3" />}
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ Chart Modal ═══ */}
      {viewChartItem && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/50 p-4" onClick={() => setViewChartItem(null)}>
          <div className="bg-card border border-border/40 rounded-[var(--radius)] w-full max-w-5xl h-[80vh] flex flex-col shadow-lg overflow-hidden" onClick={e => e.stopPropagation()}>
            <div className="shrink-0 flex items-center justify-between px-4 py-2.5 border-b border-border/30">
              <div className="min-w-0">
                <span className="text-[13px] font-semibold text-foreground truncate">{viewChartItem.name || viewChartItem.code}</span>
                <span className="text-[11.5px] font-mono text-muted-foreground/40 ml-2">{viewChartItem.code} · {viewChartItem.frequency || '—'} · {viewChartItem.provider || '—'}</span>
              </div>
              <button onClick={() => setViewChartItem(null)} className="btn-icon"><X className="w-3.5 h-3.5" /></button>
            </div>
            <div className="flex-1 min-h-0 relative">
              {chartLoading && (
                <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/80">
                  <Loader2 className="w-5 h-5 text-primary animate-spin" />
                </div>
              )}
              {chartData && (
                <div className="w-full h-full p-3">
                  <Plot data={plotData} layout={plotLayout} config={plotConfig} style={plotStyle} />
                </div>
              )}
              {!chartLoading && (!chartData || Object.keys(chartData).length <= 1) && (
                <div className="absolute inset-0 flex items-center justify-center text-muted-foreground/40 flex-col gap-2">
                  <AlertTriangle className="w-5 h-5" />
                  <span className="text-[12.5px] font-mono">No data available</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Form Field ──
function FormField({
  label, value, onChange, mono, disabled, multiline, placeholder, type = 'text'
}: {
  label: string; value: string; onChange: (v: string) => void;
  mono?: boolean; disabled?: boolean; multiline?: boolean; placeholder?: string; type?: string;
}) {
  const cls = `w-full h-7 px-2.5 text-[12.5px] bg-background border border-border/50 rounded-[var(--radius)] text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-primary/50 transition-colors disabled:opacity-40 ${mono ? 'font-mono' : ''}`;
  return (
    <div>
      <label className="stat-label block mb-1">{label}</label>
      {multiline ? (
        <textarea value={value} onChange={e => onChange(e.target.value)} className={`${cls} h-auto min-h-[60px] py-1.5 resize-y`} disabled={disabled} placeholder={placeholder} />
      ) : (
        <input type={type} value={value} onChange={e => onChange(e.target.value)} className={cls} disabled={disabled} placeholder={placeholder} />
      )}
    </div>
  );
}
