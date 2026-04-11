'use client';

import React, { Suspense, lazy, useState, useMemo, useRef, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { apiFetch, apiFetchJson } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';
import { useDebounce } from '@/hooks/useDebounce';
import AppShell from '@/components/layout/AppShell';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import {
  Loader2, AlertTriangle, FileText, ExternalLink, Upload, Trash2,
  Search, X, Pencil, Check, Shield, Activity, ChevronRight,
  ChevronLeft, ChevronsLeft, ChevronsRight,
} from 'lucide-react';
import SignInPrompt from '@/components/auth/SignInPrompt';

// ── Lazy tabs ──────────────────────────────────────────────────────────

const WartimeContent = lazy(() =>
  import('@/components/wartime/WartimeContent').then((m) => ({ default: m.WartimeContent })),
);
const StressTestContent = lazy(() =>
  import('@/components/wartime/StressTestContent').then((m) => ({ default: m.StressTestContent })),
);

// ── Types ──────────────────────────────────────────────────────────────

type ResearchTab = 'files' | 'wartime' | 'stress';

interface LibraryItem {
  id: string;
  filename: string;
  title: string;
  size_bytes: number;
  uploaded_by: string | null;
  created_at: string;
  summary: string | null;
}

interface PaginatedResponse {
  items: LibraryItem[];
  total: number;
}

// ── Constants ─────────────────────────────────────────────────────────

const PAGE_SIZE = 25;

// ── Helpers ────────────────────────────────────────────────────────────

function fmtSize(bytes: number): string {
  if (bytes >= 1e6) return (bytes / 1e6).toFixed(1) + ' MB';
  if (bytes >= 1e3) return (bytes / 1e3).toFixed(0) + ' KB';
  return bytes + ' B';
}

function fmtDate(iso: string | null): string {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

const tabTransition = { duration: 0.15, ease: 'easeOut' } as const;
const tabInitial = { opacity: 0 } as const;
const tabAnimate = { opacity: 1 } as const;
const tabExit = { opacity: 0 } as const;

// ── Tabs config ────────────────────────────────────────────────────────

const TABS: { key: ResearchTab; label: string; shortLabel: string; icon: React.ReactNode }[] = [
  { key: 'files', label: 'Research', shortLabel: 'Research', icon: <FileText className="w-3.5 h-3.5" /> },
  { key: 'wartime', label: 'Wartime', shortLabel: 'War', icon: <Shield className="w-3.5 h-3.5" /> },
  { key: 'stress', label: 'Stress Test', shortLabel: 'Stress', icon: <Activity className="w-3.5 h-3.5" /> },
];

// ── Lazy fallback ──────────────────────────────────────────────────────

function LazyFallback({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <LoadingSpinner label={label} size="section" />
    </div>
  );
}

// ── Summary renderer ──────────────────────────────────────────────────

function SummaryPanel({ summary, onOpenPdf }: { summary: string; onOpenPdf: () => void }) {
  const sections = useMemo(() => {
    const result: { thesis: string; takeaways: string[]; topics: string[]; outlook: string; outlookType: 'bullish' | 'bearish' | 'neutral' | 'mixed' | 'na' } = {
      thesis: '', takeaways: [], topics: [], outlook: '', outlookType: 'neutral',
    };
    const lines = summary.split('\n');
    let section = '';
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      if (trimmed.startsWith('THESIS:')) {
        result.thesis = trimmed.slice(7).trim();
        section = 'thesis';
      } else if (trimmed === 'KEY TAKEAWAYS:') {
        section = 'takeaways';
      } else if (trimmed.startsWith('TOPICS:')) {
        result.topics = trimmed.slice(7).trim().split(',').map(t => t.trim()).filter(Boolean);
        section = 'topics';
      } else if (trimmed.startsWith('OUTLOOK:')) {
        result.outlook = trimmed.slice(8).trim();
        const lower = result.outlook.toLowerCase();
        if (lower.startsWith('bullish')) result.outlookType = 'bullish';
        else if (lower.startsWith('bearish')) result.outlookType = 'bearish';
        else if (lower.startsWith('mixed')) result.outlookType = 'mixed';
        else if (lower.includes('n/a')) result.outlookType = 'na';
        section = 'outlook';
      } else if (section === 'takeaways' && trimmed.startsWith('-')) {
        result.takeaways.push(trimmed.slice(1).trim());
      }
    }
    return result;
  }, [summary]);

  const outlookColor = {
    bullish: 'text-success',
    bearish: 'text-destructive',
    neutral: 'text-muted-foreground/60',
    mixed: 'text-warning',
    na: 'text-muted-foreground/40',
  }[sections.outlookType];

  return (
    <div className="pl-7 pr-4 py-3 space-y-2.5">
      {/* Thesis */}
      {sections.thesis && (
        <p className="text-[12.5px] leading-[1.6] text-foreground/70 font-medium">
          {sections.thesis}
        </p>
      )}

      {/* Takeaways */}
      {sections.takeaways.length > 0 && (
        <ul className="space-y-1">
          {sections.takeaways.map((t, i) => (
            <li key={i} className="text-[11.5px] leading-[1.5] text-muted-foreground/60 pl-3 relative before:content-[''] before:absolute before:left-0 before:top-[6px] before:w-1 before:h-1 before:rounded-full before:bg-muted-foreground/20">
              {t}
            </li>
          ))}
        </ul>
      )}

      {/* Topics + Outlook row */}
      <div className="flex items-center gap-2 flex-wrap">
        {sections.topics.map((topic, i) => (
          <span key={i} className="text-[9.5px] font-mono font-semibold uppercase tracking-[0.08em] px-1.5 py-0.5 rounded-[3px] bg-foreground/[0.04] text-muted-foreground/50 border border-border/20">
            {topic}
          </span>
        ))}
        {sections.outlook && (
          <span className={`text-[11px] font-mono font-semibold ${outlookColor} ml-auto`}>
            {sections.outlook}
          </span>
        )}
      </div>

      <button
        onClick={(e) => { e.stopPropagation(); onOpenPdf(); }}
        className="text-[11px] font-mono font-semibold text-primary/60 hover:text-primary uppercase tracking-wider transition-colors"
      >
        Open PDF
      </button>
    </div>
  );
}

// ── Row component ──────────────────────────────────────────────────────

const FileRow = React.memo(function FileRow({
  item, isAdmin, onDelete, onStartRename,
  isConfirmingDelete, onRequestDelete, onCancelDelete,
  isExpanded, onToggleExpand,
}: {
  item: LibraryItem;
  isAdmin: boolean;
  onDelete: (id: string) => void;
  onStartRename: (id: string, title: string) => void;
  isConfirmingDelete: boolean;
  onRequestDelete: (id: string) => void;
  onCancelDelete: () => void;
  isExpanded: boolean;
  onToggleExpand: (id: string) => void;
}) {
  const openPdf = useCallback(() => window.open(`/api/research/library/view/${item.id}`, '_blank'), [item.id]);

  return (
    <>
      <tr
        className={`border-b border-border/10 hover:bg-foreground/[0.02] cursor-pointer transition-colors group ${isExpanded ? 'bg-foreground/[0.015]' : ''}`}
        onClick={() => {
          if (item.summary) onToggleExpand(item.id);
          else openPdf();
        }}
      >
        <td className="px-4 py-2.5">
          <div className="flex items-center gap-2.5">
            <div className="w-4 shrink-0 flex items-center justify-center">
              {item.summary ? (
                <ChevronRight className={`w-3 h-3 text-muted-foreground/25 transition-transform duration-150 ${isExpanded ? 'rotate-90' : ''}`} />
              ) : null}
            </div>
            <div className="w-7 h-8 rounded-[3px] bg-destructive/[0.06] border border-destructive/10 flex items-center justify-center shrink-0">
              <span className="text-[6px] font-mono font-bold text-destructive/40 uppercase tracking-wider">PDF</span>
            </div>
            <div className="min-w-0 flex-1">
              <span className="text-[13px] font-semibold text-foreground/80 line-clamp-1 group-hover:text-foreground transition-colors block">
                {item.title}
              </span>
              <span className="text-[11px] font-mono text-muted-foreground/30 tabular-nums sm:hidden">
                {fmtSize(item.size_bytes)}
              </span>
            </div>
          </div>
        </td>
        <td className="px-3 py-2.5 text-[11.5px] font-mono text-muted-foreground/35 tabular-nums whitespace-nowrap hidden sm:table-cell">
          {fmtSize(item.size_bytes)}
        </td>
        <td className="px-3 py-2.5 text-[11.5px] font-mono text-muted-foreground/35 tabular-nums whitespace-nowrap">
          {fmtDate(item.created_at)}
        </td>
        <td className="px-3 py-2.5 w-20">
          {isConfirmingDelete ? (
            <div className="flex items-center gap-0.5" onClick={(e) => e.stopPropagation()}>
              <button
                onClick={() => onDelete(item.id)}
                className="text-[11px] font-mono font-semibold text-destructive hover:text-destructive/80 px-1.5 py-0.5 rounded bg-destructive/[0.08] hover:bg-destructive/15 transition-colors"
              >
                Delete?
              </button>
              <button
                onClick={() => onCancelDelete()}
                className="w-6 h-6 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/30 hover:text-foreground hover:bg-foreground/[0.06]"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
              <a
                href={`/api/research/library/view/${item.id}`}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="w-6 h-6 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/20 hover:text-foreground hover:bg-foreground/[0.06]"
                title="Open PDF"
              >
                <ExternalLink className="w-3 h-3" />
              </a>
              {isAdmin && (
                <>
                  <button
                    onClick={(e) => { e.stopPropagation(); onStartRename(item.id, item.title); }}
                    className="w-6 h-6 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/20 hover:text-foreground hover:bg-foreground/[0.06]"
                    title="Rename"
                  >
                    <Pencil className="w-3 h-3" />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); onRequestDelete(item.id); }}
                    className="w-6 h-6 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/20 hover:text-destructive hover:bg-destructive/[0.06]"
                    title="Delete"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </>
              )}
            </div>
          )}
        </td>
      </tr>
      <AnimatePresence>
        {isExpanded && item.summary && (
          <motion.tr
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.12 }}
          >
            <td colSpan={4} className="px-4 py-0 border-b border-border/10 bg-foreground/[0.015]">
              <SummaryPanel summary={item.summary} onOpenPdf={openPdf} />
            </td>
          </motion.tr>
        )}
      </AnimatePresence>
    </>
  );
});

// ── Pagination bar ────────────────────────────────────────────────────

function PaginationBar({ page, totalPages, total, onPageChange }: {
  page: number;
  totalPages: number;
  total: number;
  onPageChange: (p: number) => void;
}) {
  if (totalPages <= 1) return null;

  return (
    <div className="shrink-0 flex items-center justify-between px-3 sm:px-5 lg:px-6 py-2 border-t border-border/20">
      <span className="text-[11.5px] font-mono text-muted-foreground/30 tabular-nums">
        {total} file{total !== 1 ? 's' : ''}
      </span>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(0)}
          disabled={page === 0}
          className="w-6 h-6 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/30 hover:text-foreground hover:bg-foreground/[0.06] disabled:opacity-20 disabled:cursor-default disabled:hover:bg-transparent transition-colors"
          title="First page"
        >
          <ChevronsLeft className="w-3 h-3" />
        </button>
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page === 0}
          className="w-6 h-6 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/30 hover:text-foreground hover:bg-foreground/[0.06] disabled:opacity-20 disabled:cursor-default disabled:hover:bg-transparent transition-colors"
          title="Previous"
        >
          <ChevronLeft className="w-3 h-3" />
        </button>
        <span className="text-[11.5px] font-mono text-muted-foreground/40 tabular-nums px-2 select-none">
          {page + 1}<span className="text-muted-foreground/20"> / </span>{totalPages}
        </span>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages - 1}
          className="w-6 h-6 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/30 hover:text-foreground hover:bg-foreground/[0.06] disabled:opacity-20 disabled:cursor-default disabled:hover:bg-transparent transition-colors"
          title="Next"
        >
          <ChevronRight className="w-3 h-3" />
        </button>
        <button
          onClick={() => onPageChange(totalPages - 1)}
          disabled={page >= totalPages - 1}
          className="w-6 h-6 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/30 hover:text-foreground hover:bg-foreground/[0.06] disabled:opacity-20 disabled:cursor-default disabled:hover:bg-transparent transition-colors"
          title="Last page"
        >
          <ChevronsRight className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}

// ── Files tab content ──────────────────────────────────────────────────

function FilesContent() {
  const { user, loading: authLoading } = useAuth();
  const { theme } = useTheme();
  const isAdmin = !!(user?.role === 'owner' || user?.role === 'admin' || user?.is_admin);
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const debouncedSearch = useDebounce(search, 300);
  const [page, setPage] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const tableRef = useRef<HTMLDivElement>(null);

  // Reset page when search changes
  useEffect(() => { setPage(0); }, [debouncedSearch]);

  // Auto-clear error after 4s
  useEffect(() => {
    if (!errorMsg) return;
    const t = setTimeout(() => setErrorMsg(null), 4000);
    return () => clearTimeout(t);
  }, [errorMsg]);

  // Auto-cancel delete confirmation after 3s
  useEffect(() => {
    if (!confirmDeleteId) return;
    const t = setTimeout(() => setConfirmDeleteId(null), 3000);
    return () => clearTimeout(t);
  }, [confirmDeleteId]);

  const buildUrl = useCallback(() => {
    const params = new URLSearchParams();
    if (debouncedSearch) params.set('q', debouncedSearch);
    params.set('limit', String(PAGE_SIZE));
    params.set('offset', String(page * PAGE_SIZE));
    return `/api/research/library?${params.toString()}`;
  }, [debouncedSearch, page]);

  const { data, isLoading, isFetching, isError, refetch } = useQuery<PaginatedResponse>({
    queryKey: ['research-library', debouncedSearch, page],
    queryFn: () => apiFetchJson<PaginatedResponse>(buildUrl()),
    staleTime: 120_000,
    placeholderData: keepPreviousData,
    enabled: !authLoading && !!user,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const handlePageChange = useCallback((p: number) => {
    setPage(p);
    setExpandedId(null);
    tableRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  const handleUpload = useCallback(async (file: globalThis.File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) return;
    setUploading(true);
    setErrorMsg(null);
    const form = new FormData();
    form.append('file', file);
    try {
      const res = await apiFetch('/api/research/library/upload', { method: 'POST', body: form });
      if (!res.ok) {
        const err = await res.text();
        setErrorMsg(`Upload failed: ${err}`);
        setUploading(false);
        return;
      }
      if (fileRef.current) fileRef.current.value = '';
      queryClient.invalidateQueries({ queryKey: ['research-library'] });
    } catch (e: any) {
      setErrorMsg(`Upload error: ${e.message || e}`);
    }
    setUploading(false);
  }, [queryClient]);

  const handleDelete = useCallback(async (id: string) => {
    setConfirmDeleteId(null);
    try {
      await apiFetchJson(`/api/research/library/${id}`, { method: 'DELETE' });
      queryClient.invalidateQueries({ queryKey: ['research-library'] });
    } catch (e: any) {
      setErrorMsg(`Delete failed: ${e.message || 'Unknown error'}`);
    }
  }, [queryClient]);

  const handleRename = useCallback(async (id: string) => {
    const title = editTitle.trim();
    if (!title) { setEditingId(null); return; }
    try {
      await apiFetchJson(`/api/research/library/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      });
      queryClient.invalidateQueries({ queryKey: ['research-library'] });
    } catch (e: any) {
      setErrorMsg(`Rename failed: ${e.message || 'Unknown error'}`);
    }
    setEditingId(null);
  }, [editTitle, queryClient]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const files = e.dataTransfer.files;
    if (files) Array.from(files).forEach(handleUpload);
  }, [handleUpload]);

  // Auth gate — after all hooks
  if (!authLoading && !user) {
    return <SignInPrompt feature="research files" />;
  }

  const showLoading = authLoading || (isLoading && !data);

  return (
    <div className="h-full flex flex-col min-h-0">
      {/* Search + upload bar */}
      <div className="shrink-0 px-3 sm:px-5 lg:px-6 pt-4 pb-2">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/30" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search files and summaries..."
              className="w-full h-9 pl-9 pr-9 text-[13px] border border-border/30 rounded-[var(--radius)] bg-card text-foreground focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/20 transition-all placeholder:text-muted-foreground/30"
              style={{ colorScheme: theme === 'light' ? 'light' : 'dark' }}
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 p-0.5 rounded hover:bg-foreground/[0.06]"
              >
                <X className="w-3 h-3 text-muted-foreground/30 hover:text-foreground transition-colors" />
              </button>
            )}
          </div>
          <>
            <input ref={fileRef} type="file" accept=".pdf" multiple className="hidden"
              onChange={(e) => { const files = e.target.files; if (files) Array.from(files).forEach(handleUpload); }} />
            <button
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
              className="btn-primary h-9 shrink-0"
            >
              {uploading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Upload className="w-3 h-3" />}
              <span className="hidden sm:inline">{uploading ? 'Uploading' : 'Upload'}</span>
            </button>
          </>
        </div>
      </div>

      {/* Status bar */}
      <div className="shrink-0 flex items-center justify-between px-3 sm:px-5 lg:px-6 py-1">
        <span className="text-[11.5px] font-mono text-muted-foreground/25 tabular-nums">
          {!showLoading && total > 0 && (
            <>
              {total} file{total !== 1 ? 's' : ''}
              {debouncedSearch && <span className="text-muted-foreground/15"> matching &ldquo;{debouncedSearch}&rdquo;</span>}
            </>
          )}
        </span>
        {isFetching && !showLoading && (
          <Loader2 className="w-3 h-3 animate-spin text-muted-foreground/20" />
        )}
      </div>

      {/* Inline error message */}
      <AnimatePresence>
        {errorMsg && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="shrink-0 overflow-hidden"
          >
            <div className="flex items-center gap-2 px-3 sm:px-5 lg:px-6 py-2 bg-destructive/[0.06] border-b border-destructive/15">
              <span className="text-[11.5px] font-mono text-destructive/80 flex-1 truncate">{errorMsg}</span>
              <button onClick={() => setErrorMsg(null)} className="text-destructive/40 hover:text-destructive shrink-0">
                <X className="w-3 h-3" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Rename bar */}
      <AnimatePresence>
        {editingId && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="shrink-0 overflow-hidden"
          >
            <div className="h-10 flex items-center gap-2 px-3 sm:px-5 lg:px-6 border-b border-border/20 bg-card">
              <span className="text-[11.5px] font-mono text-muted-foreground/40">Rename:</span>
              <form
                onSubmit={(e) => { e.preventDefault(); handleRename(editingId); }}
                className="flex items-center gap-1.5 flex-1"
              >
                <input
                  autoFocus
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Escape') setEditingId(null); }}
                  className="text-[13px] font-semibold text-foreground bg-background border border-border/50 rounded-[calc(var(--radius)-2px)] px-2.5 py-1 flex-1 max-w-md focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/20"
                  style={{ colorScheme: theme === 'light' ? 'light' : 'dark' }}
                />
                <button type="submit" className="btn-icon text-success hover:text-success/80 hover:bg-success/10">
                  <Check className="w-3.5 h-3.5" />
                </button>
                <button type="button" onClick={() => setEditingId(null)} className="btn-icon text-muted-foreground/30 hover:text-foreground">
                  <X className="w-3.5 h-3.5" />
                </button>
              </form>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* File table */}
      <div className="flex-1 min-h-0 flex flex-col">
        <div
          ref={tableRef}
          className={`flex-1 min-h-0 overflow-y-auto relative transition-all ${dragOver ? 'ring-2 ring-inset ring-primary/30 bg-primary/[0.02]' : ''}`}
          onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); setDragOver(true); }}
          onDragEnter={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const { clientX: x, clientY: y } = e;
            if (x <= rect.left || x >= rect.right || y <= rect.top || y >= rect.bottom) setDragOver(false);
          }}
          onDrop={handleDrop}
        >
          {/* Drag overlay */}
          <AnimatePresence>
            {dragOver && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="absolute inset-0 z-10 flex items-center justify-center bg-background/80"
              >
                <div className="flex flex-col items-center gap-3 text-primary/60">
                  <motion.div
                    animate={{ y: [0, -4, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                    className="w-14 h-14 rounded-[var(--radius)] border-2 border-dashed border-primary/30 flex items-center justify-center"
                  >
                    <Upload className="w-6 h-6" />
                  </motion.div>
                  <span className="text-[13px] font-semibold">Drop PDF to upload</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {showLoading ? (
            <LoadingSpinner label="Loading research files" size="section" />
          ) : isError ? (
            <div className="flex items-center justify-center py-24">
              <div className="flex flex-col items-center gap-3 text-center max-w-xs animate-fade-in">
                <div className="w-10 h-10 rounded-[var(--radius)] bg-destructive/10 border border-destructive/20 flex items-center justify-center">
                  <AlertTriangle className="w-4.5 h-4.5 text-destructive" />
                </div>
                <p className="text-[13px] font-medium text-foreground">Failed to load research files</p>
                <p className="text-[12px] text-muted-foreground">Check your connection and try again.</p>
                <button onClick={() => refetch()} className="mt-1 text-[12px] font-medium text-primary hover:text-primary/80 transition-colors">Retry</button>
              </div>
            </div>
          ) : items.length === 0 ? (
            <div className="flex items-center justify-center py-24">
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
                className="text-center max-w-[280px]"
              >
                <div className="w-14 h-14 mx-auto rounded-[var(--radius)] border border-border/20 bg-card flex items-center justify-center mb-4">
                  <FileText className="w-6 h-6 text-muted-foreground/15" />
                </div>
                <p className="text-[13px] font-semibold text-foreground/50">
                  {debouncedSearch ? 'No matching files' : 'No research files yet'}
                </p>
                <p className="text-[12.5px] text-muted-foreground/35 mt-2 leading-relaxed">
                  {debouncedSearch ? 'Try a different search term.' : 'Upload PDFs to build your research library.'}
                </p>
                {!debouncedSearch && (
                  <button onClick={() => fileRef.current?.click()} className="btn-primary mt-5">
                    <Upload className="w-3.5 h-3.5" /> Upload your first PDF
                  </button>
                )}
              </motion.div>
            </div>
          ) : (
            <table className="w-full">
              <thead className="sticky top-0 z-10 bg-background border-b border-border/20">
                <tr>
                  <th className="text-[11px] font-mono font-semibold uppercase tracking-[0.1em] text-muted-foreground/35 text-left px-4 py-2">Name</th>
                  <th className="text-[11px] font-mono font-semibold uppercase tracking-[0.1em] text-muted-foreground/35 text-left px-3 py-2 hidden sm:table-cell">Size</th>
                  <th className="text-[11px] font-mono font-semibold uppercase tracking-[0.1em] text-muted-foreground/35 text-left px-3 py-2">Date</th>
                  <th className="px-3 py-2 w-20"></th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <FileRow
                    key={item.id}
                    item={item}
                    isAdmin={isAdmin}
                    onDelete={handleDelete}
                    onStartRename={(id, title) => { setEditingId(id); setEditTitle(title); }}
                    isConfirmingDelete={confirmDeleteId === item.id}
                    onRequestDelete={setConfirmDeleteId}
                    onCancelDelete={() => setConfirmDeleteId(null)}
                    isExpanded={expandedId === item.id}
                    onToggleExpand={(id) => setExpandedId((prev) => prev === id ? null : id)}
                  />
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {!showLoading && !isError && items.length > 0 && (
          <PaginationBar
            page={page}
            totalPages={totalPages}
            total={total}
            onPageChange={handlePageChange}
          />
        )}
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────

export default function ResearchPage() {
  useEffect(() => { document.title = 'Research | Investment-X'; }, []);

  const [activeTab, setActiveTab] = useState<ResearchTab>('files');

  return (
    <AppShell hideFooter>
      <div className="page-shell">
        {/* Header */}
        <div className="page-header">
          <h1 className="page-header-title">RESEARCH</h1>
        </div>

        {/* Tab bar */}
        <div className="shrink-0 border-b border-border/40 px-3 sm:px-5 lg:px-6">
          <div className="flex items-center overflow-x-auto no-scrollbar">
            {TABS.map((tab, idx) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`relative flex items-center gap-1.5 whitespace-nowrap px-3 py-2.5 text-[10px] font-mono font-semibold uppercase tracking-[0.10em] transition-colors ${
                  activeTab === tab.key ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
                } ${idx > 0 ? 'border-l border-border/30' : ''}`}
              >
                <span>{tab.icon}</span>
                <span className="hidden sm:inline">{tab.label}</span>
                <span className="sm:hidden">{tab.shortLabel}</span>
                {activeTab === tab.key && (
                  <motion.span
                    layoutId="research-tab"
                    className="absolute left-0 right-0 bottom-0 h-[2px] bg-accent"
                    transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                  />
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Tab content */}
        <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden">
          <AnimatePresence mode="wait">
            {activeTab === 'files' && (
              <motion.div key="files" initial={tabInitial} animate={tabAnimate} exit={tabExit} transition={tabTransition} className="h-full">
                <FilesContent />
              </motion.div>
            )}

            {activeTab === 'wartime' && (
              <motion.div key="wartime" initial={tabInitial} animate={tabAnimate} exit={tabExit} transition={tabTransition} className="h-full">
                <Suspense fallback={<LazyFallback label="Loading wartime analysis" />}>
                  <WartimeContent embedded />
                </Suspense>
              </motion.div>
            )}

            {activeTab === 'stress' && (
              <motion.div key="stress" initial={tabInitial} animate={tabAnimate} exit={tabExit} transition={tabTransition} className="h-full">
                <Suspense fallback={<LazyFallback label="Loading stress analysis" />}>
                  <StressTestContent embedded />
                </Suspense>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </AppShell>
  );
}
