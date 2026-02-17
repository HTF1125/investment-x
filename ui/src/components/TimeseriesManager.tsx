'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search, Plus, Trash2, Edit3, Save, X, ChevronLeft, ChevronRight,
  Database, RefreshCw, Loader2, AlertTriangle, Check, Star, Mail,
  LineChart
} from 'lucide-react';
import dynamic from 'next/dynamic';

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
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null);

  // Form state
  const [form, setForm] = useState(EMPTY_FORM);

  // Update Task State
  const [updating, setUpdating] = useState(false);
  const [emailing, setEmailing] = useState(false);
  const [updateMsg, setUpdateMsg] = useState('');

  // Chart Viewer State
  const [viewChartItem, setViewChartItem] = useState<Timeseries | null>(null);

  // ───── Toast helper
  const flash = (msg: string, type: 'success' | 'error') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

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
    if (!token) return [];
    const params = new URLSearchParams();
    params.set('limit', String(PAGE_SIZE));
    params.set('offset', String(page * PAGE_SIZE));
    if (search) params.set('search', search);

    const res = await fetch(`/api/timeseries?${params}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Failed to fetch');
    return res.json() as Promise<Timeseries[]>;
  };

  const { data: items = [], isLoading, isPlaceholderData } = useQuery({
    queryKey: ['timeseries', { page, search: debouncedSearch }],
    queryFn: () => fetchTimeseries({ page, search: debouncedSearch }),
    placeholderData: keepPreviousData,
    enabled: !!token,
  });

  const loading = isLoading; // Alias for UI compatibility

  // ───── Fetch Chart Data
  const { data: chartData, isLoading: chartLoading } = useQuery({
    queryKey: ['series-data', viewChartItem?.code],
    queryFn: async () => {
      if (!viewChartItem?.code || !token) return null;
      // Fetch using the advanced series API to get processed data
      const params = new URLSearchParams();
      // Use Series('CODE') to fetch
      params.set('series', `Series('${viewChartItem.code}')`);
      
      const res = await fetch(`/api/series?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to fetch data');
      return res.json();
    },
    enabled: !!viewChartItem && !!token,
  });

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
    if (updating || !token) return;
    try {
        setUpdating(true);
        setUpdateMsg('Starting update...');
        const res = await fetch('/api/task/daily', { 
            method: 'POST', 
            headers: { Authorization: `Bearer ${token}` } 
        });
        
        if (!res.ok) {
            const err = await res.json();
            if (res.status === 400 && err.detail === "Daily task is already running") {
                // Should just start polling
            } else {
                throw new Error(err.detail || 'Failed to start');
            }
        }
        
        // Start polling
        const poll = setInterval(async () => {
             try {
                 const sRes = await fetch('/api/task/status');
                 if (!sRes.ok) return;
                 const status = await sRes.json();
                 
                 if (status.daily) {
                     if (status.daily.running) {
                         setUpdateMsg(status.daily.message || 'Running...');
                     } else {
                         setUpdateMsg(status.daily.message || 'Idle');
                         if (status.daily.message?.includes('Completed')) {
                             flash('Daily update completed!', 'success');
                             queryClient.invalidateQueries({ queryKey: ['timeseries'] });
                         } else if (status.daily.message?.startsWith('Failed')) {
                             flash(status.daily.message, 'error');
                         }
                         setUpdating(false);
                         clearInterval(poll);
                     }
                 }
             } catch (e) {
                 // Silently handled
                 // Don't stop polling on transient network error
             }
        }, 2000);
    } catch (e: any) {
        flash(e.message, 'error');
        setUpdating(false);
    }
  };

  const handleSendEmail = async () => {
    if (emailing || !token) return;
    try {
        setEmailing(true);
        flash('Triggering email report...', 'success');
        const res = await fetch('/api/task/report', { 
            method: 'POST', 
            headers: { Authorization: `Bearer ${token}` } 
        });
        
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
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
            <Database className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Timeseries Manager</h1>
            <p className="text-xs text-slate-500 font-mono tracking-wider uppercase">Admin Panel • Search, Create, Edit, Delete</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {updating && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-sky-500/10 text-sky-400 rounded-lg border border-sky-500/20 text-xs font-mono animate-pulse">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  {updateMsg || 'Updating...'}
              </div>
          )}
          <button
            onClick={handleTriggerUpdate}
            disabled={updating}
            className={`flex items-center gap-2 px-4 py-2.5 bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white rounded-xl text-sm font-semibold transition-all border border-white/10 ${updating ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            <RefreshCw className={`w-4 h-4 ${updating ? 'animate-spin' : ''}`} />
            {updating ? 'Running...' : 'Update Data'}
          </button>

          <button
            onClick={handleSendEmail}
            disabled={emailing}
            className={`flex items-center gap-2 px-4 py-2.5 bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white rounded-xl text-sm font-semibold transition-all border border-white/10 ${emailing ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {emailing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mail className="w-4 h-4" />}
            {emailing ? 'Sending...' : 'Email Report'}
          </button>
          
          
          <div className="w-px h-8 bg-white/10 mx-1" />

          <button
            onClick={() => { setShowCreate(true); setForm({ ...EMPTY_FORM }); }}
            className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-sky-500 to-indigo-500 hover:from-sky-400 hover:to-indigo-400 text-white rounded-xl text-sm font-semibold transition-all shadow-lg shadow-sky-500/20 hover:shadow-sky-500/30"
          >
            <Plus className="w-4 h-4" /> New Timeseries
          </button>
          <button
            onClick={() => queryClient.invalidateQueries({ queryKey: ['timeseries'] })}
            disabled={loading}
            className="p-2.5 bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 rounded-xl border border-white/5 transition-all"
            aria-label="Refresh timeseries list"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* ── Search Bar ── */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by code, name, source, category..."
          aria-label="Search timeseries"
          className="w-full pl-12 pr-4 py-3.5 bg-white/5 border border-white/10 rounded-2xl text-white placeholder:text-slate-600 focus:outline-none focus:border-sky-500/50 focus:ring-1 focus:ring-sky-500/20 transition-all text-sm"
        />
        {search && (
          <button onClick={() => setSearch('')} className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* ── Table ── */}
      <div className="overflow-hidden rounded-2xl border border-white/8 bg-white/[0.02]">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/8 bg-white/[0.03]">
                {['Code', 'Name', 'Provider', 'Asset Class', 'Category', 'Source', 'Source Code', 'Freq', 'Start', 'End', '#', ''].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-[10px] font-bold tracking-[2px] text-slate-500 uppercase whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className={isPlaceholderData ? 'opacity-50 pointer-events-none transition-opacity' : 'transition-opacity'}>
              {loading && items.length === 0 ? (
                <tr>
                  <td colSpan={12} className="px-4 py-20 text-center">
                    <Loader2 className="w-6 h-6 animate-spin text-sky-500 mx-auto" />
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={12} className="px-4 py-20 text-center text-slate-600 text-sm">
                    No timeseries found.
                  </td>
                </tr>
              ) : (
                items.map((ts) => (
                  <tr
                    key={ts.id}
                    className="border-b border-white/5 hover:bg-white/[0.03] transition-colors group"
                  >
                    <td className="px-4 py-3 font-mono text-sky-400 text-xs whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        {ts.favorite && <Star className="w-3 h-3 text-amber-400 fill-amber-400" />}
                        {ts.code}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-300 text-xs min-w-[200px] whitespace-normal">{ts.name || '—'}</td>
                    <td className="px-4 py-3 text-slate-400 text-xs">{ts.provider || '—'}</td>
                    <td className="px-4 py-3">
                      {ts.asset_class ? (
                        <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-indigo-500/15 text-indigo-300 border border-indigo-500/20">
                          {ts.asset_class}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-xs">{ts.category || '—'}</td>
                    <td className="px-4 py-3 text-slate-500 text-xs max-w-[120px] truncate">{ts.source || '—'}</td>
                    <td className="px-4 py-3 text-slate-500 text-xs font-mono">{ts.source_code || '—'}</td>
                    <td className="px-4 py-3 text-slate-500 text-xs font-mono">{ts.frequency || '—'}</td>
                    <td className="px-4 py-3 text-slate-500 text-xs font-mono whitespace-nowrap">{ts.start || '—'}</td>
                    <td className="px-4 py-3 text-slate-500 text-xs font-mono whitespace-nowrap">{ts.end || '—'}</td>
                    <td className="px-4 py-3 text-slate-500 text-xs font-mono">{ts.num_data?.toLocaleString() ?? '—'}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => setViewChartItem(ts)}
                          className="p-1.5 text-slate-500 hover:text-emerald-400 hover:bg-emerald-500/10 rounded-lg transition-colors"
                          title="View Chart"
                        >
                          <LineChart className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => openEdit(ts)}
                          className="p-1.5 text-slate-500 hover:text-sky-400 hover:bg-sky-500/10 rounded-lg transition-colors"
                          title="Edit"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => setDeleteTarget(ts)}
                          className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
                          title="Delete"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
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
        <div className="flex items-center justify-between px-4 py-3 border-t border-white/5 bg-white/[0.02]">
          <span className="text-xs text-slate-500 font-mono">
            Page {page + 1}
          </span>
          <div className="flex items-center gap-2">
            <button
              disabled={page === 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              className="p-1.5 text-slate-500 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              disabled={!hasMore}
              onClick={() => setPage((p) => p + 1)}
              className="p-1.5 text-slate-500 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* ═══════════════ Create / Edit Modal ═══════════════ */}
      {(showCreate || editItem) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label={editItem ? `Edit ${editItem.code}` : 'Create new timeseries'} onClick={() => { setShowCreate(false); setEditItem(null); }}>
          <div
            className="bg-[#0d0f14] border border-white/10 rounded-3xl w-full max-w-2xl max-h-[85vh] overflow-y-auto shadow-2xl shadow-black/50 mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sticky top-0 bg-[#0d0f14] border-b border-white/8 px-6 py-4 flex items-center justify-between z-10">
              <h2 className="text-lg font-bold text-white">
                {editItem ? `Edit: ${editItem.code}` : 'Create New Timeseries'}
              </h2>
              <button
                onClick={() => { setShowCreate(false); setEditItem(null); }}
                className="p-2 text-slate-500 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-5">
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
                <div
                  className={`w-10 h-6 rounded-full relative transition-colors ${form.favorite ? 'bg-amber-500' : 'bg-white/10'}`}
                  onClick={() => setForm({ ...form, favorite: !form.favorite })}
                >
                  <div className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-all ${form.favorite ? 'left-[18px]' : 'left-0.5'}`} />
                </div>
                <span className="text-sm text-slate-400 group-hover:text-slate-200 transition-colors">Favorite</span>
              </label>
            </div>

            {/* Footer */}
            <div className="sticky bottom-0 bg-[#0d0f14] border-t border-white/8 px-6 py-4 flex items-center justify-end gap-3">
              <button
                onClick={() => { setShowCreate(false); setEditItem(null); }}
                className="px-5 py-2.5 text-sm text-slate-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-xl transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={editItem ? handleUpdate : handleCreate}
                disabled={saving}
                className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-sky-500 to-indigo-500 hover:from-sky-400 hover:to-indigo-400 rounded-xl transition-all shadow-lg shadow-sky-500/20 disabled:opacity-50"
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="Delete confirmation" onClick={() => setDeleteTarget(null)}>
          <div
            className="bg-[#0d0f14] border border-rose-500/20 rounded-2xl w-full max-w-md shadow-2xl shadow-black/50 p-6 mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-rose-500/10 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-rose-400" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Delete Timeseries</h3>
                <p className="text-xs text-slate-500">This action cannot be undone.</p>
              </div>
            </div>
            <p className="text-sm text-slate-400 mb-6">
              Are you sure you want to delete <span className="font-mono text-rose-300">{deleteTarget.code}</span>
              {deleteTarget.name ? ` (${deleteTarget.name})` : ''}?
            </p>
            <div className="flex items-center justify-end gap-3">
              <button
                onClick={() => setDeleteTarget(null)}
                className="px-5 py-2.5 text-sm text-slate-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-xl transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-500 hover:to-red-500 rounded-xl transition-all shadow-lg shadow-rose-500/20 disabled:opacity-50"
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
            className={`fixed bottom-6 right-6 z-[60] flex items-center gap-3 px-5 py-3 rounded-2xl shadow-2xl backdrop-blur-md border ${
              toast.type === 'success'
                ? 'bg-emerald-500/15 border-emerald-500/20 text-emerald-300'
                : 'bg-rose-500/15 border-rose-500/20 text-rose-300'
            }`}
            role="alert"
          >
            {toast.type === 'success' ? <Check className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
            <span className="text-sm font-medium">{toast.msg}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ═══════════════ Chart Modal ═══════════════ */}
      {viewChartItem && (
        <div 
          className="fixed inset-0 z-[70] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4" 
          role="dialog" 
          onClick={() => setViewChartItem(null)}
        >
          <div 
             className="bg-[#0d0f14] border border-white/10 rounded-3xl w-full max-w-5xl h-[80vh] flex flex-col shadow-2xl overflow-hidden"
             onClick={(e) => e.stopPropagation()}
          >
            <div className="shrink-0 flex items-center justify-between px-6 py-4 border-b border-white/10 bg-[#12141a]">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                   <LineChart className="w-5 h-5 text-indigo-400" />
                   {viewChartItem.name || viewChartItem.code}
                </h2>
                <p className="text-xs text-slate-500 font-mono mt-0.5 tracking-wide">
                  {viewChartItem.code} • {viewChartItem.frequency || 'N/A'} • {viewChartItem.provider || 'Unknown Provider'}
                </p>
              </div>
              <button 
                onClick={() => setViewChartItem(null)} 
                className="p-2 text-slate-400 hover:text-white hover:bg-white/5 rounded-full transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
            
            <div className="flex-grow relative bg-[#0a0c10]">
               {/* Loading State */}
               {chartLoading && (
                 <div className="absolute inset-0 z-10 flex items-center justify-center flex-col gap-3 bg-[#0a0c10]/80">
                   <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
                   <p className="text-sm text-slate-500 font-medium">Loading timeseries data...</p>
                 </div>
               )}

               {/* Chart */}
               {chartData && (
                 <div className="w-full h-full p-4">
                  <Plot
                      data={[
                        {
                          x: chartData.Date || [],
                          y: chartData[Object.keys(chartData).find(k => k !== 'Date') || ''] || [],
                          type: 'scatter',
                          mode: 'lines',
                          line: { color: '#6366f1', width: 2 },
                          fill: 'tozeroy',
                          fillcolor: 'rgba(99, 102, 241, 0.1)',
                          name: viewChartItem.code
                        }
                      ]}
                      layout={{
                        autosize: true,
                        paper_bgcolor: 'rgba(0,0,0,0)',
                        plot_bgcolor: 'rgba(0,0,0,0)',
                        font: { color: '#94a3b8', family: 'Inter, sans-serif' },
                        margin: { l: 50, r: 20, t: 30, b: 40 },
                        xaxis: { 
                          gridcolor: 'rgba(255,255,255,0.05)', 
                          zerolinecolor: 'rgba(255,255,255,0.1)',
                          showgrid: true,
                          tickfont: { size: 11 }
                        },
                        yaxis: { 
                          gridcolor: 'rgba(255,255,255,0.05)', 
                          zerolinecolor: 'rgba(255,255,255,0.1)',
                          showgrid: true,
                          tickfont: { size: 11 }
                        },
                        hovermode: 'x unified',
                        showlegend: false
                      }}
                      config={{ responsive: true, displayModeBar: true, displaylogo: false }}
                      style={{ width: '100%', height: '100%' }}
                      useResizeHandler={true}
                  />
                 </div>
               )}
               
               {/* Empty State */}
               {!chartLoading && (!chartData || Object.keys(chartData).length <= 1) && (
                 <div className="absolute inset-0 flex items-center justify-center text-slate-500 flex-col gap-2">
                    <AlertTriangle className="w-8 h-8 opacity-50" />
                    <p>No data available for this series.</p>
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
  const cls = `w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-sky-500/50 focus:ring-1 focus:ring-sky-500/20 transition-all disabled:opacity-40 disabled:cursor-not-allowed ${mono ? 'font-mono' : ''}`;

  return (
    <div>
      <label className="block text-[11px] font-semibold tracking-wider text-slate-500 uppercase mb-1.5">{label}</label>
      {multiline ? (
        <textarea value={value} onChange={(e) => onChange(e.target.value)} className={`${cls} min-h-[80px] resize-y`} disabled={disabled} placeholder={placeholder} />
      ) : (
        <input type={type} value={value} onChange={(e) => onChange(e.target.value)} className={cls} disabled={disabled} placeholder={placeholder} />
      )}
    </div>
  );
}
