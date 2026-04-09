'use client';

import React, { useState, useRef, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search, Plus, Trash2, Edit3, Save, X, ChevronLeft, ChevronRight,
  Loader2, AlertTriangle, Check, Eye, EyeOff,
} from 'lucide-react';
import { apiFetch } from '@/lib/api';

// ────────────────────────────────────────────────── Types

interface WatchlistItem {
  id: string;
  entity: string;
  entity_type: string | null;
  sector: string | null;
  region: string | null;
  current_rating: string | null;
  watch_reason: string | null;
  risk_level: string;
  signal_count: number;
  last_signal: string | null;
  cra_summary: string | null;
  added_by: string | null;
  active: boolean;
  notes: any[] | null;
  created_at: string | null;
  updated_at: string | null;
}

interface WatchlistForm {
  entity: string;
  entity_type: string;
  sector: string;
  region: string;
  current_rating: string;
  watch_reason: string;
  cra_summary: string;
  risk_level: string;
  added_by: string;
}

const EMPTY_FORM: WatchlistForm = {
  entity: '',
  entity_type: 'corporate',
  sector: '',
  region: '',
  current_rating: '',
  watch_reason: '',
  cra_summary: '',
  risk_level: 'medium',
  added_by: 'manual',
};

const PAGE_SIZE = 30;

const ENTITY_TYPES = ['corporate', 'sovereign', 'financial', 'municipal', 'structured'];
const RISK_LEVELS = ['low', 'medium', 'high', 'critical'];
const REGIONS = ['US', 'KR', 'EU', 'CN', 'JP', 'EM', 'UK', 'AU', 'Other'];

const RISK_COLORS: Record<string, string> = {
  critical: 'bg-destructive/[0.08] border-destructive/20 text-destructive',
  high: 'bg-warning/[0.08] border-warning/20 text-warning',
  medium: 'bg-primary/[0.06] border-primary/15 text-primary/70',
  low: 'bg-success/[0.06] border-success/15 text-success/70',
};

// ────────────────────────────────────────────────── Component

export default function CreditWatchlistTab() {
  const queryClient = useQueryClient();

  // State
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [page, setPage] = useState(0);
  const [showCreate, setShowCreate] = useState(false);
  const [editItem, setEditItem] = useState<WatchlistItem | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<WatchlistItem | null>(null);
  const [showInactive, setShowInactive] = useState(false);
  const [form, setForm] = useState<WatchlistForm>({ ...EMPTY_FORM });
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error'; sticky?: boolean } | null>(null);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounced search
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const handleSearchChange = (val: string) => {
    setSearch(val);
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => {
      setDebouncedSearch(val);
      setPage(0);
    }, 350);
  };

  // Toast
  const flash = useCallback((msg: string, type: 'success' | 'error') => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    setToast({ msg, type });
    toastTimerRef.current = setTimeout(() => setToast(null), 3500);
  }, []);

  // ── Data fetching ──
  const fetchWatchlist = async ({ page, search }: { page: number; search: string }) => {
    const params = new URLSearchParams();
    params.set('limit', String(PAGE_SIZE));
    params.set('offset', String(page * PAGE_SIZE));
    params.set('active_only', String(!showInactive));
    if (search) params.set('search', search);
    const res = await apiFetch(`/api/credit-watchlist?${params}`);
    if (!res.ok) throw new Error('Failed to fetch watchlist');
    return res.json() as Promise<WatchlistItem[]>;
  };

  const { data: items = [], isLoading } = useQuery({
    queryKey: ['credit-watchlist', { page, search: debouncedSearch, showInactive }],
    queryFn: () => fetchWatchlist({ page, search: debouncedSearch }),
    placeholderData: keepPreviousData,
  });

  const hasMore = items.length === PAGE_SIZE;

  // ── Mutations ──
  const createMutation = useMutation({
    mutationFn: async (data: WatchlistForm) => {
      const res = await apiFetch('/api/credit-watchlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Create failed');
      }
      return res.json();
    },
    onSuccess: (data) => {
      flash(`Added "${data.entity}" to watchlist`, 'success');
      setShowCreate(false);
      setForm({ ...EMPTY_FORM });
      queryClient.invalidateQueries({ queryKey: ['credit-watchlist'] });
    },
    onError: (err: any) => flash(err.message, 'error'),
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<WatchlistForm> }) => {
      const res = await apiFetch(`/api/credit-watchlist/${id}`, {
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
      flash(`Updated "${data.entity}"`, 'success');
      setEditItem(null);
      setForm({ ...EMPTY_FORM });
      queryClient.invalidateQueries({ queryKey: ['credit-watchlist'] });
    },
    onError: (err: any) => flash(err.message, 'error'),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await apiFetch(`/api/credit-watchlist/${id}`, { method: 'DELETE' });
      if (!res.ok && res.status !== 204) {
        const err = await res.json();
        throw new Error(err.detail || 'Delete failed');
      }
    },
    onSuccess: () => {
      flash('Removed from watchlist', 'success');
      setDeleteTarget(null);
      queryClient.invalidateQueries({ queryKey: ['credit-watchlist'] });
    },
    onError: (err: any) => flash(err.message, 'error'),
  });

  // ── Handlers ──
  const handleCreate = () => {
    if (!form.entity.trim()) { flash('Entity name is required', 'error'); return; }
    createMutation.mutate(form);
  };
  const handleUpdate = () => {
    if (!editItem) return;
    updateMutation.mutate({ id: editItem.id, data: form });
  };
  const handleDelete = () => {
    if (!deleteTarget) return;
    deleteMutation.mutate(deleteTarget.id);
  };
  const openEdit = (item: WatchlistItem) => {
    setForm({
      entity: item.entity,
      entity_type: item.entity_type || 'corporate',
      sector: item.sector || '',
      region: item.region || '',
      current_rating: item.current_rating || '',
      watch_reason: item.watch_reason || '',
      cra_summary: item.cra_summary || '',
      risk_level: item.risk_level || 'medium',
      added_by: item.added_by || 'manual',
    });
    setEditItem(item);
  };

  const saving = createMutation.isPending || updateMutation.isPending;
  const deleting = deleteMutation.isPending;

  return (
    <div className="space-y-3">
      {/* ── Toolbar ── */}
      <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
        <span className="text-[11.5px] font-mono text-muted-foreground/40 tabular-nums shrink-0">
          {items.length} entities
        </span>

        <div className="relative flex-1 min-w-[160px] max-w-xs">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground/30 pointer-events-none" />
          <input
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Search entity, sector, region..."
            className="w-full h-7 pl-7 pr-2 text-[12.5px] bg-background border border-border/50 rounded-[var(--radius)] text-foreground placeholder:text-muted-foreground/30 focus:outline-none focus:border-primary/50 transition-colors"
          />
        </div>

        <button
          onClick={() => setShowInactive(!showInactive)}
          className={`btn-toolbar flex items-center gap-1.5 text-[11.5px] ${showInactive ? 'text-muted-foreground' : 'text-muted-foreground/40'}`}
          title={showInactive ? 'Showing inactive' : 'Hiding inactive'}
        >
          {showInactive ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
          <span className="hidden sm:inline">{showInactive ? 'All' : 'Active'}</span>
        </button>

        <div className="flex-1" />

        <button
          onClick={() => { setForm({ ...EMPTY_FORM }); setShowCreate(true); }}
          className="btn-toolbar flex items-center gap-1.5 text-[11.5px] text-primary"
        >
          <Plus className="w-3 h-3" />
          <span className="hidden sm:inline">Add Entity</span>
        </button>
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

      {/* ── Loading ── */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-5 h-5 animate-spin text-primary/40" />
        </div>
      )}

      {/* ── Desktop Table ── */}
      {!isLoading && (
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border/30">
                {['Entity', 'Type', 'Sector', 'Region', 'Rating', 'Risk', 'Signals', 'Last Signal', 'CRA Summary', ''].map(h => (
                  <th key={h} className="stat-label text-left px-3 py-2 whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && (
                <tr>
                  <td colSpan={10} className="text-center py-8 text-[12.5px] text-muted-foreground/30">
                    No watchlist entities found
                  </td>
                </tr>
              )}
              {items.map(item => (
                <tr
                  key={item.id}
                  className={`border-b border-border/10 hover:bg-foreground/[0.02] transition-colors group ${!item.active ? 'opacity-40' : ''}`}
                >
                  <td className="px-3 py-2">
                    <span className="text-[12.5px] font-semibold text-foreground">{item.entity}</span>
                  </td>
                  <td className="px-3 py-2">
                    <span className="text-[11.5px] font-mono text-muted-foreground/50">{item.entity_type || '—'}</span>
                  </td>
                  <td className="px-3 py-2">
                    <span className="text-[11.5px] text-muted-foreground/60">{item.sector || '—'}</span>
                  </td>
                  <td className="px-3 py-2">
                    {item.region && (
                      <span className="px-1.5 py-0.5 text-[11px] font-mono font-semibold rounded-[calc(var(--radius)-2px)] bg-primary/[0.06] text-primary/70 border border-primary/15">
                        {item.region}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <span className="text-[11.5px] font-mono text-muted-foreground/60">{item.current_rating || '—'}</span>
                  </td>
                  <td className="px-3 py-2">
                    <span className={`inline-flex px-1.5 py-0.5 text-[11px] font-mono font-semibold uppercase rounded-[calc(var(--radius)-2px)] border ${RISK_COLORS[item.risk_level] || RISK_COLORS.medium}`}>
                      {item.risk_level}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <span className="text-[11.5px] font-mono text-muted-foreground/40 tabular-nums">{item.signal_count}</span>
                  </td>
                  <td className="px-3 py-2">
                    <span className="text-[11.5px] text-muted-foreground/40 truncate max-w-[200px] block">{item.last_signal || '—'}</span>
                  </td>
                  <td className="px-3 py-2">
                    {item.cra_summary ? (
                      <span className="text-[11.5px] text-muted-foreground/60 line-clamp-2 max-w-[260px] block" title={item.cra_summary}>
                        {item.cra_summary}
                      </span>
                    ) : (
                      <span className="text-[11.5px] text-muted-foreground/20">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button onClick={() => openEdit(item)} className="btn-icon text-muted-foreground/40 hover:text-foreground">
                        <Edit3 className="w-3 h-3" />
                      </button>
                      <button onClick={() => setDeleteTarget(item)} className="btn-icon text-muted-foreground/40 hover:text-destructive">
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Mobile Cards ── */}
      {!isLoading && (
        <div className="md:hidden space-y-2">
          {items.map(item => (
            <div key={item.id} className={`panel-card p-3 ${!item.active ? 'opacity-40' : ''}`}>
              <div className="flex items-start justify-between gap-2 mb-2">
                <div>
                  <span className="text-[12.5px] font-semibold text-foreground block">{item.entity}</span>
                  <span className="text-[11px] font-mono text-muted-foreground/40">
                    {item.entity_type} · {item.region || '—'} · {item.sector || '—'}
                  </span>
                </div>
                <span className={`shrink-0 px-1.5 py-0.5 text-[11px] font-mono font-semibold uppercase rounded-[calc(var(--radius)-2px)] border ${RISK_COLORS[item.risk_level] || RISK_COLORS.medium}`}>
                  {item.risk_level}
                </span>
              </div>
              {item.current_rating && (
                <div className="text-[11.5px] font-mono text-muted-foreground/50 mb-1">{item.current_rating}</div>
              )}
              {item.cra_summary && (
                <div className="text-[11.5px] text-muted-foreground/60 mb-1 line-clamp-2">{item.cra_summary}</div>
              )}
              <div className="flex items-center justify-between mt-2">
                <span className="text-[11px] text-muted-foreground/30">
                  Signals: {item.signal_count} · {item.last_signal || 'No signals'}
                </span>
                <div className="flex items-center gap-1">
                  <button onClick={() => openEdit(item)} className="btn-icon"><Edit3 className="w-3 h-3" /></button>
                  <button onClick={() => setDeleteTarget(item)} className="btn-icon text-destructive/50"><Trash2 className="w-3 h-3" /></button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Pagination ── */}
      {!isLoading && items.length > 0 && (
        <div className="flex items-center justify-between">
          <span className="text-[11.5px] font-mono text-muted-foreground/30 tabular-nums">
            Page {page + 1} · {items.length} items
          </span>
          <div className="flex items-center gap-1">
            <button disabled={page === 0} onClick={() => setPage(p => Math.max(0, p - 1))} className="btn-icon disabled:opacity-30">
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <button disabled={!hasMore} onClick={() => setPage(p => p + 1)} className="btn-icon disabled:opacity-30">
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* ── Create / Edit Modal ── */}
      {(showCreate || editItem) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => { setShowCreate(false); setEditItem(null); }}>
          <div className="bg-card border border-border/40 rounded-[var(--radius)] w-full max-w-2xl max-h-[85vh] overflow-y-auto shadow-lg mx-4" onClick={e => e.stopPropagation()}>
            {/* Header */}
            <div className="sticky top-0 bg-card border-b border-border/30 px-4 py-3 flex items-center justify-between z-10">
              <span className="text-[13px] font-semibold text-foreground">
                {editItem ? `Edit: ${editItem.entity}` : 'Add to Watchlist'}
              </span>
              <button onClick={() => { setShowCreate(false); setEditItem(null); }} className="btn-icon"><X className="w-3.5 h-3.5" /></button>
            </div>

            {/* Form */}
            <div className="p-4 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                <FormField label="Entity Name" value={form.entity} onChange={v => setForm({ ...form, entity: v })} placeholder="e.g., Boeing Co." />

                <div>
                  <label className="stat-label block mb-1">Entity Type</label>
                  <select
                    value={form.entity_type}
                    onChange={e => setForm({ ...form, entity_type: e.target.value })}
                    className="w-full h-7 px-2.5 text-[12.5px] bg-background border border-border/50 rounded-[var(--radius)] text-foreground focus:outline-none focus:border-primary/50 transition-colors"
                  >
                    {ENTITY_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>

                <FormField label="Sector" value={form.sector} onChange={v => setForm({ ...form, sector: v })} placeholder="e.g., Aerospace" />

                <div>
                  <label className="stat-label block mb-1">Region</label>
                  <select
                    value={form.region}
                    onChange={e => setForm({ ...form, region: e.target.value })}
                    className="w-full h-7 px-2.5 text-[12.5px] bg-background border border-border/50 rounded-[var(--radius)] text-foreground focus:outline-none focus:border-primary/50 transition-colors"
                  >
                    <option value="">—</option>
                    {REGIONS.map(r => <option key={r} value={r}>{r}</option>)}
                  </select>
                </div>

                <div className="sm:col-span-2">
                  <FormField label="Current Rating" value={form.current_rating} onChange={v => setForm({ ...form, current_rating: v })} mono placeholder="e.g., BBB- (S&P, neg) / Baa3 (Moody's)" />
                </div>

                <div>
                  <label className="stat-label block mb-1">Risk Level</label>
                  <select
                    value={form.risk_level}
                    onChange={e => setForm({ ...form, risk_level: e.target.value })}
                    className="w-full h-7 px-2.5 text-[12.5px] bg-background border border-border/50 rounded-[var(--radius)] text-foreground focus:outline-none focus:border-primary/50 transition-colors"
                  >
                    {RISK_LEVELS.map(r => <option key={r} value={r}>{r}</option>)}
                  </select>
                </div>

                <div className="sm:col-span-2 md:col-span-3">
                  <FormField label="Watch Reason" value={form.watch_reason} onChange={v => setForm({ ...form, watch_reason: v })} multiline placeholder="Why is this entity on the watchlist?" />
                </div>
                <div className="sm:col-span-2 md:col-span-3">
                  <FormField label="CRA Summary" value={form.cra_summary} onChange={v => setForm({ ...form, cra_summary: v })} multiline placeholder="1-2 sentence key point from rating agency commentaries" />
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="sticky bottom-0 bg-card border-t border-border/30 px-4 py-3 flex items-center justify-end gap-2">
              <button onClick={() => { setShowCreate(false); setEditItem(null); setForm({ ...EMPTY_FORM }); }} className="btn-toolbar text-[12.5px]">Cancel</button>
              <button
                onClick={editItem ? handleUpdate : handleCreate}
                disabled={saving}
                className="h-7 px-3 text-[12.5px] font-semibold bg-foreground text-background hover:bg-foreground/90 rounded-[var(--radius)] transition-all disabled:opacity-50 flex items-center gap-1.5"
              >
                {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                {editItem ? 'Update' : 'Add'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Delete Confirmation ── */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setDeleteTarget(null)}>
          <div className="bg-card border border-destructive/20 rounded-[var(--radius)] w-full max-w-sm shadow-lg p-5 mx-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 rounded-[var(--radius)] bg-destructive/[0.08] flex items-center justify-center shrink-0">
                <AlertTriangle className="w-4 h-4 text-destructive" />
              </div>
              <div>
                <h3 className="text-[13px] font-semibold text-foreground">Remove from Watchlist</h3>
                <p className="text-[11.5px] text-muted-foreground/50">Entity will be deactivated (soft-delete).</p>
              </div>
            </div>
            <p className="text-[12.5px] text-muted-foreground/60 mb-5">
              Remove <span className="font-semibold text-destructive">{deleteTarget.entity}</span> from the watchlist?
            </p>
            <div className="flex items-center justify-end gap-2">
              <button onClick={() => setDeleteTarget(null)} className="btn-toolbar text-[12.5px]">Cancel</button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="h-7 px-3 text-[12.5px] font-semibold bg-destructive hover:bg-destructive/90 text-destructive-foreground rounded-[var(--radius)] transition-all disabled:opacity-50 flex items-center gap-1.5"
              >
                {deleting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3" />}
                Remove
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


// ────────────────────────────────────────────────── FormField

function FormField({
  label, value, onChange, mono, disabled, multiline, placeholder,
}: {
  label: string; value: string; onChange: (v: string) => void;
  mono?: boolean; disabled?: boolean; multiline?: boolean; placeholder?: string;
}) {
  const cls = `w-full h-7 px-2.5 text-[12.5px] bg-background border border-border/50 rounded-[var(--radius)] text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-primary/50 transition-colors disabled:opacity-40 ${mono ? 'font-mono' : ''}`;
  return (
    <div>
      <label className="stat-label block mb-1">{label}</label>
      {multiline ? (
        <textarea value={value} onChange={e => onChange(e.target.value)} className={`${cls} h-auto min-h-[60px] py-1.5 resize-y`} disabled={disabled} placeholder={placeholder} />
      ) : (
        <input type="text" value={value} onChange={e => onChange(e.target.value)} className={cls} disabled={disabled} placeholder={placeholder} />
      )}
    </div>
  );
}
