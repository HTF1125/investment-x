'use client';

import React, { Suspense, lazy, useState, useRef, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch, apiFetchJson } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import AppShell from '@/components/layout/AppShell';
import {
  Loader2, WifiOff, FileText, ExternalLink, Upload, Trash2,
  Search, X, Pencil, Check, Shield, Activity,
} from 'lucide-react';

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
}

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
      <div className="flex flex-col items-center gap-2">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground/40" />
        <span className="text-[10px] font-mono text-muted-foreground/50 uppercase tracking-wider">
          {label}
        </span>
      </div>
    </div>
  );
}

// ── Row component ──────────────────────────────────────────────────────

const FileRow = React.memo(function FileRow({
  item,
  isAdmin,
  onDelete,
  onStartRename,
}: {
  item: LibraryItem;
  isAdmin: boolean;
  onDelete: (id: string, title: string) => void;
  onStartRename: (id: string, title: string) => void;
}) {
  return (
    <tr
      className="border-b border-border/10 hover:bg-foreground/[0.02] cursor-pointer transition-colors group"
      onClick={() => window.open(`/api/research/library/view/${item.id}`, '_blank')}
    >
      <td className="px-3 py-2.5">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-8 rounded-[3px] bg-destructive/[0.08] border border-destructive/10 flex items-center justify-center shrink-0">
            <span className="text-[6px] font-mono font-bold text-destructive/50 uppercase">PDF</span>
          </div>
          <span className="text-[11px] font-semibold text-foreground/80 line-clamp-1 group-hover:text-foreground transition-colors">
            {item.title}
          </span>
        </div>
      </td>
      <td className="px-3 py-2.5 text-[9px] font-mono text-muted-foreground/30 tabular-nums whitespace-nowrap hidden sm:table-cell">
        {fmtSize(item.size_bytes)}
      </td>
      <td className="px-3 py-2.5 text-[9px] font-mono text-muted-foreground/30 tabular-nums whitespace-nowrap">
        {fmtDate(item.created_at)}
      </td>
      <td className="px-3 py-2.5 w-20">
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
          <a
            href={`/api/research/library/view/${item.id}`}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="w-6 h-6 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/20 hover:text-foreground hover:bg-foreground/[0.06]"
            title="Open in new tab"
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
                onClick={(e) => { e.stopPropagation(); onDelete(item.id, item.title); }}
                className="w-6 h-6 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/20 hover:text-destructive hover:bg-destructive/[0.06]"
                title="Delete"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </>
          )}
        </div>
      </td>
    </tr>
  );
});

// ── Annotations drop zone ──────────────────────────────────────────────

function AnnotationsZone() {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<{ name: string; status: string; duplicate?: boolean } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleUpload = useCallback(async (file: globalThis.File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      alert('Only PDF files are accepted');
      return;
    }
    setUploading(true);
    setResult(null);
    const form = new FormData();
    form.append('file', file);
    try {
      const res = await apiFetchJson<{ id: string; name: string; status: string; duplicate?: boolean }>(
        '/api/insights/upload',
        { method: 'POST', body: form },
      );
      setResult(res);
    } catch (e: any) {
      alert(`Annotation upload error: ${e.message || e}`);
    }
    setUploading(false);
  }, []);

  return (
    <div className="shrink-0 px-4 sm:px-5 lg:px-6 pb-4 pt-2">
      <div className="border-t border-border/20 pt-3">
        <div className="flex items-center gap-2 mb-2">
          <span className="stat-label">Annotations</span>
          <span className="text-[9px] text-muted-foreground/30 font-mono">
            YYYYMMDD_issuer_name_#tags.pdf
          </span>
        </div>
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragEnter={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const { clientX: x, clientY: y } = e;
            if (x <= rect.left || x >= rect.right || y <= rect.top || y >= rect.bottom)
              setDragOver(false);
          }}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            const files = e.dataTransfer.files;
            if (files?.[0]) handleUpload(files[0]);
          }}
          onClick={() => inputRef.current?.click()}
          className={`flex flex-col items-center justify-center gap-2 py-6 border-2 border-dashed rounded-[var(--radius)] cursor-pointer transition-all ${
            dragOver
              ? 'border-primary/60 bg-primary/[0.04]'
              : 'border-border/30 hover:border-border/50 hover:bg-foreground/[0.02]'
          }`}
        >
          {uploading ? (
            <Loader2 className="w-5 h-5 animate-spin text-primary/60" />
          ) : (
            <>
              <Upload className="w-5 h-5 text-muted-foreground/25" />
              <span className="text-[11px] font-mono text-muted-foreground/40">
                Drop annotation PDF here
              </span>
            </>
          )}
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleUpload(f); e.target.value = ''; }}
        />
        {result && (
          <div className="mt-2 text-[10px] font-mono text-muted-foreground/50">
            {result.duplicate ? 'Updated' : 'Uploaded'}: {result.name}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Files tab content ──────────────────────────────────────────────────

function FilesContent() {
  const { user } = useAuth();
  const isAdmin = !!(user?.role === 'owner' || user?.role === 'admin' || user?.is_admin);
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [uploading, setUploading] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: items = [], isLoading, isError, refetch } = useQuery<LibraryItem[]>({
    queryKey: ['research-library', search],
    queryFn: () => apiFetchJson<LibraryItem[]>(`/api/research/library${search ? `?q=${encodeURIComponent(search)}` : ''}`),
    staleTime: 120_000,
  });

  const handleUpload = useCallback(async (file: globalThis.File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) return;
    setUploading(true);
    const form = new FormData();
    form.append('file', file);
    try {
      const res = await apiFetch('/api/research/library/upload', { method: 'POST', body: form });
      if (!res.ok) {
        const err = await res.text();
        alert(`Upload failed: ${err}`);
        setUploading(false);
        return;
      }
      if (fileRef.current) fileRef.current.value = '';
      queryClient.invalidateQueries({ queryKey: ['research-library'] });
    } catch (e: any) {
      alert(`Upload error: ${e.message || e}`);
    }
    setUploading(false);
  }, [queryClient]);

  const handleDelete = useCallback(async (id: string, title: string) => {
    if (!confirm(`Delete "${title}"?`)) return;
    try {
      await apiFetchJson(`/api/research/library/${id}`, { method: 'DELETE' });
      queryClient.invalidateQueries({ queryKey: ['research-library'] });
    } catch { /* ignore */ }
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
    } catch { /* ignore */ }
    setEditingId(null);
  }, [editTitle, queryClient]);

  const [dragOver, setDragOver] = useState(false);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const files = e.dataTransfer.files;
    if (files) Array.from(files).forEach(handleUpload);
  }, [handleUpload]);

  return (
    <div className="h-full flex flex-col min-h-0">
      {/* Large search bar */}
      <div className="shrink-0 px-4 sm:px-5 lg:px-6 pt-4 pb-2">
        <div className="relative">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/40" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search research files..."
            className="w-full h-11 pl-10 pr-10 text-sm font-medium border border-border/40 rounded-[var(--radius)] bg-background text-foreground focus:outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/25 transition-all placeholder:text-muted-foreground/40"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 rounded hover:bg-foreground/[0.06]"
            >
              <X className="w-3.5 h-3.5 text-muted-foreground/40 hover:text-foreground transition-colors" />
            </button>
          )}
        </div>
      </div>

      {/* Files header */}
      <div className="section-header shrink-0 px-4 sm:px-5 lg:px-6">
        <span className="text-[9px] font-mono text-muted-foreground/25 tabular-nums">
          {!isLoading && `${items.length} files`}
        </span>
        <div className="flex-1" />
        {isAdmin && (
          <>
            <input ref={fileRef} type="file" accept=".pdf" multiple className="hidden"
              onChange={(e) => { const files = e.target.files; if (files) Array.from(files).forEach(handleUpload); }} />
            <button
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
              className="btn-toolbar gap-1"
            >
              {uploading ? <Loader2 className="w-2.5 h-2.5 animate-spin" /> : <Upload className="w-2.5 h-2.5" />}
              <span className="text-[9px] font-semibold hidden sm:inline">{uploading ? 'Uploading' : 'Upload'}</span>
            </button>
          </>
        )}
      </div>

      {/* Rename bar */}
      {editingId && (
        <div className="shrink-0 h-9 flex items-center gap-2 px-4 sm:px-5 lg:px-6 border-b border-border/20 bg-card">
          <span className="text-[10px] font-mono text-muted-foreground/40">Rename:</span>
          <form
            onSubmit={(e) => { e.preventDefault(); handleRename(editingId); }}
            className="flex items-center gap-1 flex-1"
          >
            <input
              autoFocus
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Escape') setEditingId(null); }}
              className="text-[11px] font-semibold text-foreground bg-background border border-border/50 rounded-[calc(var(--radius)-2px)] px-2 py-0.5 flex-1 max-w-md focus:outline-none focus:border-primary/50"
            />
            <button type="submit" className="btn-icon text-primary/60 hover:text-primary">
              <Check className="w-3.5 h-3.5" />
            </button>
            <button type="button" onClick={() => setEditingId(null)} className="btn-icon text-muted-foreground/40 hover:text-foreground">
              <X className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      )}

      {/* File table — full width, single column */}
      <div className="flex-1 min-h-0 flex flex-col">
        <div
          className={`flex-1 min-h-0 overflow-y-auto relative ${dragOver ? 'ring-1 ring-inset ring-primary/30' : ''}`}
          onDragOver={isAdmin ? (e) => { e.preventDefault(); e.stopPropagation(); setDragOver(true); } : undefined}
          onDragEnter={isAdmin ? (e) => { e.preventDefault(); setDragOver(true); } : undefined}
          onDragLeave={isAdmin ? (e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const { clientX: x, clientY: y } = e;
            if (x <= rect.left || x >= rect.right || y <= rect.top || y >= rect.bottom) setDragOver(false);
          } : undefined}
          onDrop={isAdmin ? handleDrop : undefined}
        >
          {dragOver && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-primary/[0.03] backdrop-blur-[1px]">
              <div className="flex flex-col items-center gap-2 text-primary/60">
                <div className="w-12 h-12 rounded-full border-2 border-dashed border-primary/30 flex items-center justify-center">
                  <Upload className="w-5 h-5" />
                </div>
                <span className="text-[11px] font-mono font-semibold">Drop PDF to upload</span>
              </div>
            </div>
          )}

          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <div className="flex flex-col items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-muted-foreground/20" />
                <span className="stat-label">Loading research</span>
              </div>
            </div>
          ) : isError ? (
            <div className="m-6 panel-card p-8 flex flex-col items-center gap-3 text-center">
              <WifiOff className="w-5 h-5 text-muted-foreground/30" />
              <p className="text-[12px] text-muted-foreground/60">Unable to load research files</p>
              <button onClick={() => refetch()} className="btn-toolbar">Retry</button>
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 gap-2">
              <FileText className="w-5 h-5 text-muted-foreground/10" />
              <span className="text-[11px] text-muted-foreground/25 font-mono">
                {search ? 'No matching files' : 'No research files yet'}
              </span>
              {isAdmin && !search && (
                <button onClick={() => fileRef.current?.click()}
                  className="mt-2 text-[10px] font-mono text-primary/50 hover:text-primary transition-colors">
                  Upload your first PDF
                </button>
              )}
            </div>
          ) : (
            <table className="w-full">
              <thead className="sticky top-0 z-10 bg-background">
                <tr className="border-b border-border/20">
                  <th className="stat-label text-left px-3 py-2">Name</th>
                  <th className="stat-label text-left px-3 py-2 hidden sm:table-cell">Size</th>
                  <th className="stat-label text-left px-3 py-2">Date</th>
                  <th className="stat-label px-3 py-2 w-20"></th>
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
                  />
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Annotations drop zone — admin only */}
        {isAdmin && <AnnotationsZone />}
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
      <div className="h-[calc(100vh-48px)] flex flex-col min-h-0 overflow-hidden bg-background">
        {/* Tab bar */}
        <div className="px-4 sm:px-5 lg:px-6 border-b border-border/25 shrink-0">
          <div className="flex gap-0.5 overflow-x-auto no-scrollbar -mb-px">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`tab-link flex items-center gap-1.5 ${activeTab === tab.key ? 'active' : ''}`}
              >
                <span className="opacity-50">{tab.icon}</span>
                <span className="hidden sm:inline">{tab.label}</span>
                <span className="sm:hidden">{tab.shortLabel}</span>
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
