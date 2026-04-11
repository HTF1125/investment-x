'use client';

import React, { useEffect, useMemo, useState, useRef, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Shield, Search, Plus, Edit3, Trash2, X, Save, Loader2,
  AlertTriangle, Check, TrendingDown, Activity, Eye, EyeOff,
} from 'lucide-react';
import AppShell from '@/components/layout/AppShell';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import { apiFetch } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';

// ─────────────────────────────────────────────────────────── Types

interface WatchlistItem {
  id: string;
  entity: string;
  entity_type: string | null;
  sector: string | null;
  region: string | null;
  current_rating: string | null;
  watch_reason: string | null;
  risk_level: string; // critical | high | medium | low
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
  cra_summary: '',
  risk_level: 'low',
  added_by: 'manual',
};

const ENTITY_TYPES = ['corporate', 'sovereign', 'financial', 'municipal', 'structured'];
const RISK_LEVELS = ['low', 'medium', 'high', 'critical'] as const;
const REGIONS = ['US', 'KR', 'EU', 'CN', 'JP', 'EM', 'UK', 'AU', 'CA', 'Other'];

type RiskLevel = typeof RISK_LEVELS[number];

// Downgrade-risk semantics — not rating level.
// critical: imminent downgrade (IG→HY cliff, active CreditWatch Negative)
// high:     negative outlook from ≥2 agencies, or sector contagion
// medium:   single-agency negative outlook, peer deterioration
// low:      stable/positive, no active negative signal
const RISK_META: Record<RiskLevel, {
  label: string;
  desc: string;
  dot: string;
  badge: string;
  row: string;
  accent: string;
}> = {
  critical: {
    label: 'CRITICAL',
    desc: 'Imminent downgrade · IG→HY cliff · CreditWatch Neg',
    dot: 'bg-destructive',
    badge: 'bg-destructive/[0.12] border-destructive/30 text-destructive',
    row: 'bg-destructive/[0.03]',
    accent: 'border-l-destructive',
  },
  high: {
    label: 'HIGH',
    desc: 'Negative outlook ≥2 agencies · sector contagion',
    dot: 'bg-warning',
    badge: 'bg-warning/[0.12] border-warning/30 text-warning',
    row: 'bg-warning/[0.02]',
    accent: 'border-l-warning',
  },
  medium: {
    label: 'MEDIUM',
    desc: 'Single-agency neg outlook · peer pressure',
    dot: 'bg-accent',
    badge: 'bg-accent/[0.12] border-accent/30 text-accent',
    row: '',
    accent: 'border-l-accent/60',
  },
  low: {
    label: 'LOW',
    desc: 'Stable · no active negative signal',
    dot: 'bg-success/70',
    badge: 'bg-success/[0.08] border-success/20 text-success/80',
    row: '',
    accent: 'border-l-transparent',
  },
};

const PAGE_SIZE = 50;

// ─────────────────────────────────────────────────────────── Utilities

function formatRelative(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  const diff = Date.now() - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.floor(months / 12)}y ago`;
}

function riskRank(r: string): number {
  return { critical: 0, high: 1, medium: 2, low: 3 }[r as RiskLevel] ?? 4;
}

// ─────────────────────────────────────────────────────────── Page

export default function CreditPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const canEdit = !!user && (user.role === 'owner' || user.role === 'admin' || user.is_admin);

  useEffect(() => { document.title = 'Credit Watchlist | Investment-X'; }, []);

  // Filters & UI state
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState<RiskLevel | 'all'>('all');
  const [regionFilter, setRegionFilter] = useState<string>('');
  const [showInactive, setShowInactive] = useState(false);
  const [page, setPage] = useState(0);

  // Modals
  const [showCreate, setShowCreate] = useState(false);
  const [editItem, setEditItem] = useState<WatchlistItem | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<WatchlistItem | null>(null);
  const [form, setForm] = useState<WatchlistForm>({ ...EMPTY_FORM });
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const flash = useCallback((msg: string, type: 'success' | 'error') => {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast({ msg, type });
    toastTimer.current = setTimeout(() => setToast(null), 3500);
  }, []);

  const handleSearch = (v: string) => {
    setSearch(v);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => { setDebouncedSearch(v); setPage(0); }, 300);
  };

  // ── Data fetch ──
  const fetchList = async (): Promise<WatchlistItem[]> => {
    const params = new URLSearchParams();
    params.set('limit', '500');
    params.set('offset', '0');
    params.set('active_only', String(!showInactive));
    if (debouncedSearch) params.set('search', debouncedSearch);
    const res = await apiFetch(`/api/credit-watchlist?${params}`);
    if (!res.ok) throw new Error('Failed to fetch watchlist');
    return res.json();
  };

  const { data: all = [], isLoading, isError } = useQuery({
    queryKey: ['credit-watchlist-page', { search: debouncedSearch, showInactive }],
    queryFn: fetchList,
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  });

  // ── Client-side filters + sort ──
  // Sort: risk level → book size DESC → updated_at DESC
  const filtered = useMemo(() => {
    let rows = all;
    if (riskFilter !== 'all') rows = rows.filter(r => r.risk_level === riskFilter);
    if (regionFilter) rows = rows.filter(r => r.region === regionFilter);
    return [...rows].sort((a, b) => {
      const r = riskRank(a.risk_level) - riskRank(b.risk_level);
      if (r !== 0) return r;
      const au = a.updated_at ? new Date(a.updated_at).getTime() : 0;
      const bu = b.updated_at ? new Date(b.updated_at).getTime() : 0;
      return bu - au;
    });
  }, [all, riskFilter, regionFilter]);

  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));

  // ── Stats ──
  const stats = useMemo(() => {
    const counts: Record<RiskLevel, number> = { critical: 0, high: 0, medium: 0, low: 0 };
    for (const r of all) {
      if (r.risk_level in counts) {
        counts[r.risk_level as RiskLevel]++;
      }
    }
    return { total: all.length, ...counts };
  }, [all]);

  const uniqueRegions = useMemo(
    () => Array.from(new Set(all.map(r => r.region).filter(Boolean))).sort() as string[],
    [all]
  );

  // ── Mutations ──
  const createMut = useMutation({
    mutationFn: async (data: WatchlistForm) => {
      const res = await apiFetch('/api/credit-watchlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Create failed');
      return res.json();
    },
    onSuccess: (data) => {
      flash(`Added "${data.entity}"`, 'success');
      setShowCreate(false); setForm({ ...EMPTY_FORM });
      queryClient.invalidateQueries({ queryKey: ['credit-watchlist-page'] });
    },
    onError: (e: any) => flash(e.message, 'error'),
  });

  const updateMut = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<WatchlistForm> }) => {
      const res = await apiFetch(`/api/credit-watchlist/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Update failed');
      return res.json();
    },
    onSuccess: (data) => {
      flash(`Updated "${data.entity}"`, 'success');
      setEditItem(null); setForm({ ...EMPTY_FORM });
      queryClient.invalidateQueries({ queryKey: ['credit-watchlist-page'] });
    },
    onError: (e: any) => flash(e.message, 'error'),
  });

  const deleteMut = useMutation({
    mutationFn: async (id: string) => {
      const res = await apiFetch(`/api/credit-watchlist/${id}`, { method: 'DELETE' });
      if (!res.ok && res.status !== 204) throw new Error((await res.json()).detail || 'Delete failed');
    },
    onSuccess: () => {
      flash('Removed from watchlist', 'success');
      setDeleteTarget(null);
      queryClient.invalidateQueries({ queryKey: ['credit-watchlist-page'] });
    },
    onError: (e: any) => flash(e.message, 'error'),
  });

  const openEdit = (it: WatchlistItem) => {
    setForm({
      entity: it.entity,
      entity_type: it.entity_type || 'corporate',
      sector: it.sector || '',
      region: it.region || '',
      current_rating: it.current_rating || '',
      cra_summary: it.cra_summary || '',
      risk_level: it.risk_level || 'low',
      added_by: it.added_by || 'manual',
    });
    setEditItem(it);
  };

  const saving = createMut.isPending || updateMut.isPending;
  const deleting = deleteMut.isPending;

  // ──────────────────────────────────────────────── Render

  return (
    <AppShell hideFooter>
      <div className="page-shell">
        {/* ── Header ── */}
        <div className="page-header">
          <Shield className="w-3 h-3 text-muted-foreground" />
          <h1 className="page-header-title">CREDIT WATCHLIST</h1>
          <div className="page-header-divider" aria-hidden />
          <span className="text-[11px] font-mono text-muted-foreground truncate">
            Downgrade-risk surveillance · HTM portfolio
          </span>
          <div className="flex-1" />
          <span className="hidden md:inline-flex items-center gap-3 text-[10px] font-mono uppercase tracking-[0.08em] text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">
              <Activity className="w-3 h-3" />
              {stats.total} entities
            </span>
          </span>
        </div>

        {/* ── Risk-level tab bar ── */}
        <div className="page-tabs">
          <RiskTab label="ALL" count={stats.total} active={riskFilter === 'all'} onClick={() => { setRiskFilter('all'); setPage(0); }} />
          {(['critical', 'high', 'medium', 'low'] as RiskLevel[]).map(lvl => (
            <RiskTab
              key={lvl}
              label={RISK_META[lvl].label}
              count={stats[lvl]}
              dot={RISK_META[lvl].dot}
              active={riskFilter === lvl}
              onClick={() => { setRiskFilter(lvl); setPage(0); }}
            />
          ))}
        </div>

        {/* ── Content ── */}
        <div className="page-content">
          <div className="page-container space-y-4">

            {/* Toolbar */}
            <div className="flex items-center gap-2 flex-wrap">
              <div className="relative flex-1 min-w-[180px] max-w-sm">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground/40 pointer-events-none" />
                <input
                  value={search}
                  onChange={(e) => handleSearch(e.target.value)}
                  placeholder="Search entity, sector, rating..."
                  className="w-full h-7 pl-7 pr-2 text-[12.5px] bg-background border border-border/50 rounded-[var(--radius)] text-foreground placeholder:text-muted-foreground/30 focus:outline-none focus:border-primary/50 transition-colors"
                />
              </div>

              <select
                value={regionFilter}
                onChange={(e) => { setRegionFilter(e.target.value); setPage(0); }}
                className="h-7 px-2 text-[11.5px] font-mono bg-background border border-border/50 rounded-[var(--radius)] text-foreground focus:outline-none focus:border-primary/50"
              >
                <option value="">ALL REGIONS</option>
                {uniqueRegions.map(r => <option key={r} value={r}>{r}</option>)}
              </select>

              <button
                onClick={() => setShowInactive(!showInactive)}
                className={`btn-toolbar flex items-center gap-1.5 text-[11.5px] ${showInactive ? 'text-foreground' : 'text-muted-foreground/50'}`}
                title={showInactive ? 'Showing inactive' : 'Active only'}
              >
                {showInactive ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
                <span className="hidden sm:inline">{showInactive ? 'All' : 'Active'}</span>
              </button>

              <div className="flex-1" />

              <span className="text-[11px] font-mono text-muted-foreground/40 tabular-nums">
                {filtered.length} shown
              </span>

              {canEdit && (
                <button
                  onClick={() => { setForm({ ...EMPTY_FORM }); setShowCreate(true); }}
                  className="h-7 px-3 flex items-center gap-1.5 text-[11.5px] font-semibold bg-foreground text-background hover:bg-foreground/90 rounded-[var(--radius)] transition-colors"
                >
                  <Plus className="w-3 h-3" />
                  <span className="hidden sm:inline">Add</span>
                </button>
              )}
            </div>

            {/* Flash toast */}
            <AnimatePresence>
              {toast && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-[var(--radius)] text-[12.5px] font-medium border ${
                    toast.type === 'success'
                      ? 'bg-success/[0.06] border-success/20 text-success'
                      : 'bg-destructive/[0.06] border-destructive/20 text-destructive'
                  }`}
                >
                  {toast.type === 'success' ? <Check className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                  <span className="flex-1 truncate">{toast.msg}</span>
                  <button onClick={() => setToast(null)} className="opacity-60 hover:opacity-100"><X className="w-3 h-3" /></button>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Loading / error */}
            {isLoading && <LoadingSpinner size="section" />}
            {isError && (
              <div className="panel-card p-6 text-center text-[12.5px] text-destructive">
                Failed to load watchlist.
              </div>
            )}

            {/* ── Table (desktop) ── */}
            {!isLoading && !isError && (
              <div className="panel-card overflow-hidden">
                <div className="hidden md:block overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-border/40 bg-surface/40">
                        <th className="stat-label text-left px-3 py-2 w-10">#</th>
                        <th className="stat-label text-left px-3 py-2">Entity</th>
                        <th className="stat-label text-left px-3 py-2">Region</th>
                        <th className="stat-label text-left px-3 py-2">Rating</th>
                        <th className="stat-label text-left px-3 py-2">Risk</th>
                        <th className="stat-label text-right px-3 py-2">Signals</th>
                        <th className="stat-label text-left px-3 py-2">Last Signal</th>
                        <th className="stat-label text-right px-3 py-2 whitespace-nowrap">Updated</th>
                        <th className="px-3 py-2 w-12"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {paged.length === 0 && (
                        <tr>
                          <td colSpan={9} className="text-center py-12 text-[12.5px] text-muted-foreground/40">
                            No entities match the current filter.
                          </td>
                        </tr>
                      )}
                      {paged.map((it, idx) => {
                        const meta = RISK_META[it.risk_level as RiskLevel] ?? RISK_META.low;
                        return (
                          <tr
                            key={it.id}
                            className={`border-b border-border/15 hover:bg-foreground/[0.025] transition-colors group border-l-2 ${meta.accent} ${meta.row} ${!it.active ? 'opacity-40' : ''}`}
                          >
                            <td className="px-3 py-2 text-[11px] font-mono text-muted-foreground/40 tabular-nums">
                              {page * PAGE_SIZE + idx + 1}
                            </td>
                            <td className="px-3 py-2 max-w-[280px]">
                              <div className="text-[12.5px] font-semibold text-foreground truncate" title={it.entity}>
                                {it.entity}
                              </div>
                              {(it.sector || it.entity_type) && (
                                <div className="text-[10.5px] font-mono text-muted-foreground/45 truncate">
                                  {[it.entity_type, it.sector].filter(Boolean).join(' · ')}
                                </div>
                              )}
                            </td>
                            <td className="px-3 py-2">
                              {it.region ? (
                                <span className="px-1.5 py-0.5 text-[10px] font-mono font-semibold tracking-wider rounded-[calc(var(--radius)-3px)] bg-foreground/[0.04] text-muted-foreground border border-border/40">
                                  {it.region}
                                </span>
                              ) : <span className="text-muted-foreground/20">—</span>}
                            </td>
                            <td className="px-3 py-2 max-w-[180px]">
                              <span className="text-[11px] font-mono text-muted-foreground/70 truncate block" title={it.current_rating || ''}>
                                {it.current_rating || '—'}
                              </span>
                            </td>
                            <td className="px-3 py-2">
                              <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-mono font-semibold tracking-wider rounded-[calc(var(--radius)-3px)] border ${meta.badge}`}>
                                <span className={`w-1 h-1 rounded-full ${meta.dot}`} />
                                {meta.label}
                              </span>
                            </td>
                            <td className="px-3 py-2 text-right">
                              <span className={`text-[11.5px] font-mono tabular-nums ${it.signal_count > 0 ? 'text-foreground' : 'text-muted-foreground/25'}`}>
                                {it.signal_count}
                              </span>
                            </td>
                            <td className="px-3 py-2 max-w-[220px]">
                              {it.last_signal ? (
                                <span className="text-[11px] text-muted-foreground/70 truncate block" title={it.last_signal}>
                                  {it.last_signal}
                                </span>
                              ) : (
                                <span className="text-[11px] text-muted-foreground/20">no signal</span>
                              )}
                            </td>
                            <td className="px-3 py-2 text-right whitespace-nowrap">
                              <span className="text-[10.5px] font-mono text-muted-foreground/40 tabular-nums">
                                {formatRelative(it.updated_at)}
                              </span>
                            </td>
                            <td className="px-3 py-2 text-right">
                              {canEdit && (
                                <div className="flex items-center justify-end gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                                  <button onClick={() => openEdit(it)} className="btn-icon text-muted-foreground/50 hover:text-foreground" title="Edit">
                                    <Edit3 className="w-3 h-3" />
                                  </button>
                                  <button onClick={() => setDeleteTarget(it)} className="btn-icon text-muted-foreground/50 hover:text-destructive" title="Remove">
                                    <Trash2 className="w-3 h-3" />
                                  </button>
                                </div>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* ── Mobile cards ── */}
                <div className="md:hidden divide-y divide-border/20">
                  {paged.length === 0 && (
                    <div className="text-center py-12 text-[12.5px] text-muted-foreground/40">
                      No entities match the current filter.
                    </div>
                  )}
                  {paged.map((it, idx) => {
                    const meta = RISK_META[it.risk_level as RiskLevel] ?? RISK_META.low;
                    return (
                      <div key={it.id} className={`p-3 border-l-2 ${meta.accent} ${meta.row} ${!it.active ? 'opacity-40' : ''}`}>
                        <div className="flex items-start justify-between gap-2 mb-1.5">
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <span className="text-[10px] font-mono text-muted-foreground/30 tabular-nums">{page * PAGE_SIZE + idx + 1}</span>
                              <span className="text-[13px] font-semibold text-foreground truncate">{it.entity}</span>
                            </div>
                            <div className="text-[10.5px] font-mono text-muted-foreground/45 mt-0.5 truncate">
                              {[it.entity_type, it.sector, it.region].filter(Boolean).join(' · ')}
                            </div>
                          </div>
                          <span className={`shrink-0 inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-mono font-semibold tracking-wider rounded-[calc(var(--radius)-3px)] border ${meta.badge}`}>
                            <span className={`w-1 h-1 rounded-full ${meta.dot}`} />
                            {meta.label}
                          </span>
                        </div>
                        {it.current_rating && (
                          <div className="text-[11px] font-mono text-muted-foreground/60 mb-1 truncate">{it.current_rating}</div>
                        )}
                        {it.last_signal && (
                          <div className="text-[11px] text-muted-foreground/70 line-clamp-2 mb-1">
                            <TrendingDown className="w-2.5 h-2.5 inline mr-1 text-warning/60" />
                            {it.last_signal}
                          </div>
                        )}
                        <div className="flex items-center justify-between mt-1.5">
                          <span className="text-[10px] font-mono text-muted-foreground/30">
                            {it.signal_count} signals · {formatRelative(it.updated_at)}
                          </span>
                          {canEdit && (
                            <div className="flex items-center gap-0.5">
                              <button onClick={() => openEdit(it)} className="btn-icon text-muted-foreground/50"><Edit3 className="w-3 h-3" /></button>
                              <button onClick={() => setDeleteTarget(it)} className="btn-icon text-destructive/50"><Trash2 className="w-3 h-3" /></button>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Pagination */}
            {!isLoading && filtered.length > PAGE_SIZE && (
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono text-muted-foreground/40 tabular-nums">
                  Page {page + 1} / {totalPages} · {paged.length} of {filtered.length}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    disabled={page === 0}
                    onClick={() => setPage(p => Math.max(0, p - 1))}
                    className="h-7 px-3 text-[11.5px] font-mono border border-border/50 rounded-[var(--radius)] text-muted-foreground hover:text-foreground hover:bg-foreground/[0.03] disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
                  >
                    ← Prev
                  </button>
                  <button
                    disabled={page >= totalPages - 1}
                    onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                    className="h-7 px-3 text-[11.5px] font-mono border border-border/50 rounded-[var(--radius)] text-muted-foreground hover:text-foreground hover:bg-foreground/[0.03] disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
                  >
                    Next →
                  </button>
                </div>
              </div>
            )}

          </div>
        </div>
      </div>

      {/* ── Create / Edit Modal ── */}
      {(showCreate || editItem) && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => { setShowCreate(false); setEditItem(null); }}
        >
          <div
            className="bg-card border border-border/50 rounded-[var(--radius)] w-full max-w-2xl max-h-[85vh] overflow-y-auto shadow-2xl"
            onClick={e => e.stopPropagation()}
          >
            <div className="sticky top-0 bg-card border-b border-border/30 px-4 py-3 flex items-center justify-between z-10">
              <span className="text-[13px] font-semibold text-foreground">
                {editItem ? `Edit: ${editItem.entity}` : 'Add to Watchlist'}
              </span>
              <button onClick={() => { setShowCreate(false); setEditItem(null); }} className="btn-icon"><X className="w-3.5 h-3.5" /></button>
            </div>
            <div className="p-4 space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <FormField label="Entity Name" value={form.entity} onChange={v => setForm({ ...form, entity: v })} placeholder="e.g., Boeing Co." />
                <SelectField label="Type" value={form.entity_type} onChange={v => setForm({ ...form, entity_type: v })} options={ENTITY_TYPES} />
                <FormField label="Sector" value={form.sector} onChange={v => setForm({ ...form, sector: v })} placeholder="e.g., Aerospace" />
                <SelectField label="Region" value={form.region} onChange={v => setForm({ ...form, region: v })} options={['', ...REGIONS]} />
                <div className="sm:col-span-2">
                  <FormField label="Current Rating" mono value={form.current_rating} onChange={v => setForm({ ...form, current_rating: v })} placeholder="e.g., BBB- (S&P, neg) / Baa3 (Moody's, stable)" />
                </div>
                <div className="sm:col-span-2">
                  <label className="stat-label block mb-1">Downgrade Risk</label>
                  <div className="flex gap-1.5 flex-wrap">
                    {RISK_LEVELS.map(r => {
                      const m = RISK_META[r];
                      const active = form.risk_level === r;
                      return (
                        <button
                          key={r}
                          type="button"
                          onClick={() => setForm({ ...form, risk_level: r })}
                          className={`px-2.5 py-1 text-[11px] font-mono font-semibold uppercase tracking-wider rounded-[calc(var(--radius)-2px)] border transition-colors flex items-center gap-1.5 ${
                            active ? m.badge : 'border-border/40 text-muted-foreground/60 hover:text-foreground'
                          }`}
                        >
                          <span className={`w-1 h-1 rounded-full ${m.dot}`} />
                          {m.label}
                        </button>
                      );
                    })}
                  </div>
                  <p className="mt-1.5 text-[10.5px] text-muted-foreground/50 leading-tight">
                    Risk of <em>downgrade</em>, not rating level. A AAA with negative outlook outranks a stable BBB.
                  </p>
                </div>
                <div className="sm:col-span-2">
                  <label className="stat-label block mb-1">CRA Summary</label>
                  <textarea
                    value={form.cra_summary}
                    onChange={e => setForm({ ...form, cra_summary: e.target.value })}
                    placeholder="Rating agency commentary, outlook, and key downgrade drivers"
                    rows={10}
                    className="w-full min-h-[220px] px-2.5 py-2 text-[12.5px] bg-background border border-border/50 rounded-[var(--radius)] text-foreground placeholder:text-muted-foreground/35 focus:outline-none focus:border-primary/50 transition-colors resize-y leading-relaxed"
                  />
                </div>
              </div>
            </div>
            <div className="sticky bottom-0 bg-card border-t border-border/30 px-4 py-3 flex items-center justify-end gap-2">
              <button
                onClick={() => { setShowCreate(false); setEditItem(null); setForm({ ...EMPTY_FORM }); }}
                className="btn-toolbar text-[12.5px]"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (!form.entity.trim()) { flash('Entity name is required', 'error'); return; }
                  if (editItem) updateMut.mutate({ id: editItem.id, data: form });
                  else createMut.mutate(form);
                }}
                disabled={saving}
                className="h-7 px-3 text-[12.5px] font-semibold bg-foreground text-background hover:bg-foreground/90 rounded-[var(--radius)] disabled:opacity-50 flex items-center gap-1.5 transition-colors"
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => setDeleteTarget(null)}>
          <div className="bg-card border border-destructive/30 rounded-[var(--radius)] w-full max-w-sm shadow-2xl p-5" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 rounded-[var(--radius)] bg-destructive/[0.1] flex items-center justify-center">
                <AlertTriangle className="w-4 h-4 text-destructive" />
              </div>
              <div>
                <h3 className="text-[13px] font-semibold text-foreground">Remove from Watchlist</h3>
                <p className="text-[11px] text-muted-foreground/60">Soft-delete (entity will be deactivated).</p>
              </div>
            </div>
            <p className="text-[12.5px] text-muted-foreground/70 mb-5">
              Remove <span className="font-semibold text-destructive">{deleteTarget.entity}</span>?
            </p>
            <div className="flex items-center justify-end gap-2">
              <button onClick={() => setDeleteTarget(null)} className="btn-toolbar text-[12.5px]">Cancel</button>
              <button
                onClick={() => deleteMut.mutate(deleteTarget.id)}
                disabled={deleting}
                className="h-7 px-3 text-[12.5px] font-semibold bg-destructive hover:bg-destructive/90 text-destructive-foreground rounded-[var(--radius)] disabled:opacity-50 flex items-center gap-1.5"
              >
                {deleting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3" />}
                Remove
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}

// ─────────────────────────────────────────────────────────── Sub-components

function RiskTab({
  label, count, active, onClick, dot,
}: {
  label: string; count: number; active: boolean; onClick: () => void; dot?: string;
}) {
  return (
    <button onClick={onClick} className={`page-tab ${active ? 'page-tab-active' : ''}`}>
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />}
      <span>{label}</span>
      <span className="text-muted-foreground/40 tabular-nums">{count}</span>
    </button>
  );
}

function FormField({
  label, value, onChange, mono, multiline, placeholder,
}: {
  label: string; value: string; onChange: (v: string) => void;
  mono?: boolean; multiline?: boolean; placeholder?: string;
}) {
  const cls = `w-full h-7 px-2.5 text-[12.5px] bg-background border border-border/50 rounded-[var(--radius)] text-foreground placeholder:text-muted-foreground/35 focus:outline-none focus:border-primary/50 transition-colors ${mono ? 'font-mono' : ''}`;
  return (
    <div>
      <label className="stat-label block mb-1">{label}</label>
      {multiline ? (
        <textarea value={value} onChange={e => onChange(e.target.value)} className={`${cls} h-auto min-h-[60px] py-1.5 resize-y`} placeholder={placeholder} />
      ) : (
        <input type="text" value={value} onChange={e => onChange(e.target.value)} className={cls} placeholder={placeholder} />
      )}
    </div>
  );
}

function SelectField({
  label, value, onChange, options,
}: {
  label: string; value: string; onChange: (v: string) => void; options: string[];
}) {
  return (
    <div>
      <label className="stat-label block mb-1">{label}</label>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full h-7 px-2.5 text-[12.5px] bg-background border border-border/50 rounded-[var(--radius)] text-foreground focus:outline-none focus:border-primary/50 transition-colors"
      >
        {options.map(o => <option key={o} value={o}>{o || '—'}</option>)}
      </select>
    </div>
  );
}
