'use client';

import { type ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  BookOpen,
  Check,
  Clock,
  FileText,
  ImageIcon,
  Loader2,
  Pin,
  PinOff,
  Plus,
  Save,
  Search,
  Trash2,
  BarChart2,
  Presentation as PresentationIcon,
  AlignLeft,
} from 'lucide-react';

import dynamic from 'next/dynamic';
import AppShell from '@/components/AppShell';
import NavigatorShell from '@/components/NavigatorShell';

const NotesRichEditor = dynamic(() => import('@/components/NotesRichEditor'), {
  ssr: false,
  loading: () => (
    <div className="flex-1 flex items-center justify-center text-muted-foreground/40 min-h-[200px]">
      <Loader2 className="w-5 h-5 animate-spin" />
    </div>
  ),
});
import { useAuth } from '@/context/AuthContext';
import { apiFetch, apiFetchJson } from '@/lib/api';
import { useResponsiveSidebar } from '@/lib/hooks/useResponsiveSidebar';
import { useTheme } from '@/context/ThemeContext';

interface NoteSummary {
  id: string;
  title: string;
  pinned: boolean;
  image_count: number;
  created_at: string;
  updated_at: string;
}

interface NoteBlock {
  id: string;
  type: string;
  value?: string;
  data?: string;
  filename?: string;
  content_type?: string;
  url?: string;
  chart_id?: string;
  metadata?: Record<string, any>;
}

interface NoteDetail {
  id: string;
  user_id: string;
  title: string;
  body: NoteBlock[];
  pinned: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

// Re-use the shared chart type (superset of what we need here)
import type { CustomChartListItem } from '@/types/chart';

interface NoteImageMeta {
  id: string;
  url: string;
  filename?: string | null;
}

function sortNoteSummaries(notes: NoteSummary[]): NoteSummary[] {
  return [...notes].sort((a, b) => {
    if (a.pinned !== b.pinned) return a.pinned ? -1 : 1;
    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
  });
}

function extractLinks(raw: string): string[] {
  const urls = new Set<string>();
  const markdownLinkRegex = /\[[^\]]*]\(([^)\s]+)\)/g;
  const rawUrlRegex = /\bhttps?:\/\/[^\s<>"')]+/gi;

  let match: RegExpExecArray | null = null;

  if (typeof window !== 'undefined' && raw.includes('<')) {
    try {
      const doc = new DOMParser().parseFromString(raw, 'text/html');
      doc.querySelectorAll('a[href]').forEach((el) => {
        const href = (el.getAttribute('href') || '').trim();
        if (href) urls.add(href);
      });
    } catch { }
  }

  while ((match = markdownLinkRegex.exec(raw)) !== null) {
    const url = (match[1] || '').trim();
    if (url) urls.add(url);
  }
  while ((match = rawUrlRegex.exec(raw)) !== null) {
    const url = (match[0] || '').trim();
    if (url) urls.add(url);
  }

  return Array.from(urls)
    .filter((url) => !url.startsWith('chart://'))
    .filter((url) => !url.startsWith('/api/notes/images/'))
    .slice(0, 40);
}

async function parseErrorMessage(res: Response): Promise<string> {
  const body = await res.json().catch(() => ({}));
  return body?.detail || body?.message || `Request failed (${res.status})`;
}

function extractHeadings(html: string): { level: number; text: string; key: number }[] {
  if (typeof window === 'undefined') return [];
  try {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    return Array.from(doc.querySelectorAll('h1, h2, h3')).map((el, key) => ({
      level: parseInt(el.tagName[1], 10),
      text: el.textContent?.trim() || '',
      key,
    })).filter((h) => h.text);
  } catch {
    return [];
  }
}

function countWords(html: string): number {
  if (typeof window === 'undefined') return 0;
  try {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const text = doc.body.textContent?.trim() || '';
    return text ? text.split(/\s+/).filter(Boolean).length : 0;
  } catch {
    return 0;
  }
}

function formatRelativeDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

export default function NotesPage() {
  useEffect(() => { document.title = 'Research Notes | Investment-X'; }, []);
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isAuthenticated, loading: authLoading } = useAuth();
  const { theme } = useTheme();
  const isLight = theme === 'light';

  const { sidebarOpen, toggleSidebar } = useResponsiveSidebar();

  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [title, setTitle] = useState('');
  const [editorValue, setEditorValue] = useState('');
  const [pinned, setPinned] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);
  const [exportingFormat, setExportingFormat] = useState<string | null>(null);
  const [toastError, setToastError] = useState<string | null>(null);

  const originalRef = useRef<{ title: string; content: string; pinned: boolean } | null>(null);
  const hydratedNoteIdRef = useRef<string | null>(null);
  const lastServerUpdatedAtRef = useRef<string | null>(null);
  const titleRef = useRef('');
  const contentRef = useRef('');
  const pinnedRef = useRef(false);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Native form element style — must use inline styles for CSS var references
  const inputStyle = {
    colorScheme: isLight ? 'light' : 'dark',
    backgroundColor: 'rgb(var(--background))',
    color: 'rgb(var(--foreground))',
  } as React.CSSProperties;

  const handleExport = async (format: 'pdf' | 'pptx') => {
    if (!selectedNoteId) return;
    setExportingFormat(format);
    try {
      const res = await apiFetch(`/api/notes/${selectedNoteId}/export?format=${format}`);
      if (!res.ok) throw new Error('Export failed');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const date = new Date().toISOString().slice(0, 10);
      a.download = `InvestmentX_Report_${date}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Export error:', err);
      setToastError('Failed to generate ' + format.toUpperCase());
    } finally {
      setExportingFormat(null);
    }
  };

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  const notesQuery = useQuery({
    queryKey: ['investment-notes'],
    enabled: isAuthenticated,
    queryFn: () => apiFetchJson<NoteSummary[]>('/api/notes'),
    staleTime: 120_000,
  });

  const chartLibraryQuery = useQuery({
    queryKey: ['report-chart-library'],
    enabled: isAuthenticated,
    queryFn: () => apiFetchJson<CustomChartListItem[]>('/api/custom?include_code=false&include_figure=false'),
    staleTime: 120_000,
  });

  const notes = notesQuery.data || [];
  const chartLibrary = chartLibraryQuery.data || [];

  useEffect(() => {
    if (!notes.length) {
      setSelectedNoteId(null); setTitle(''); setEditorValue(''); setPinned(false); setIsDirty(false); setLastSavedAt(null); setSaveState('idle'); titleRef.current = ''; contentRef.current = ''; pinnedRef.current = false; hydratedNoteIdRef.current = null; lastServerUpdatedAtRef.current = null; originalRef.current = null; return;
    }
    if (!selectedNoteId || !notes.some((n) => n.id === selectedNoteId)) {
      setSelectedNoteId(notes[0].id);
    }
  }, [notes, selectedNoteId]);

  useEffect(() => {
    hydratedNoteIdRef.current = null;
    if (saveTimerRef.current) { clearTimeout(saveTimerRef.current); saveTimerRef.current = null; }
  }, [selectedNoteId]);

  const filteredNotes = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return notes;
    return notes.filter((n) => (n.title || '').toLowerCase().includes(q));
  }, [notes, searchQuery]);

  const noteQuery = useQuery({
    queryKey: ['investment-note', selectedNoteId],
    enabled: isAuthenticated && !!selectedNoteId,
    queryFn: () => apiFetchJson<NoteDetail>(`/api/notes/${selectedNoteId}`),
    staleTime: 15_000,
    refetchInterval: selectedNoteId ? 30_000 : false,
    refetchOnWindowFocus: true,
  });
  const noteLoading = Boolean(selectedNoteId) && noteQuery.isLoading;

  const headings = useMemo(() => extractHeadings(editorValue), [editorValue]);
  const wordCount = useMemo(() => countWords(editorValue), [editorValue]);
  const readingMinutes = useMemo(() => Math.max(1, Math.round(wordCount / 200)), [wordCount]);
  const chartCount = useMemo(() => (editorValue.match(/data-chart-block/g) || []).length, [editorValue]);
  const imageCount = noteQuery.data?.body?.filter(b => b.type === 'image').length ?? 0;
  const currentLinks = useMemo(() => extractLinks(editorValue), [editorValue]);
  const selectedNote = useMemo(
    () => notes.find((note) => note.id === selectedNoteId) ?? null,
    [notes, selectedNoteId]
  );
  const createdLabel = useMemo(
    () => noteQuery.data?.created_at
      ? new Date(noteQuery.data.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })
      : null,
    [noteQuery.data?.created_at]
  );
  const updatedLabel = useMemo(
    () => lastSavedAt
      ? new Date(lastSavedAt).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
      : null,
    [lastSavedAt]
  );

  const recomputeDirty = useCallback(() => {
    const original = originalRef.current;
    const dirty = Boolean(original && selectedNoteId && (titleRef.current !== original.title || contentRef.current !== original.content || pinnedRef.current !== original.pinned));
    setIsDirty((prev) => (prev === dirty ? prev : dirty));
    return dirty;
  }, [selectedNoteId]);

  const hydrateFromNote = useCallback((note: NoteDetail) => {
    const nextTitle = note.title || '';
    const textBlock = note.body?.find(b => b.type === 'text');
    const nextContent = textBlock?.value || '';
    const nextPinned = !!note.pinned;
    titleRef.current = nextTitle; contentRef.current = nextContent; pinnedRef.current = nextPinned; setTitle(nextTitle); setEditorValue(nextContent); setPinned(nextPinned); setIsDirty(false); setLastSavedAt(note.updated_at || null); setSaveState('idle');
    if (saveTimerRef.current) { clearTimeout(saveTimerRef.current); saveTimerRef.current = null; }
    originalRef.current = { title: nextTitle, content: nextContent, pinned: nextPinned };
  }, []);

  useEffect(() => {
    const note = noteQuery.data; if (!note) return;
    const incomingUpdatedAt = note.updated_at || null;
    const isFirstHydrationForNote = hydratedNoteIdRef.current !== note.id;
    if (isFirstHydrationForNote) { hydratedNoteIdRef.current = note.id; lastServerUpdatedAtRef.current = incomingUpdatedAt; hydrateFromNote(note); return; }
    if (!incomingUpdatedAt || incomingUpdatedAt === lastServerUpdatedAtRef.current) return;
    lastServerUpdatedAtRef.current = incomingUpdatedAt;
    if (incomingUpdatedAt === lastSavedAt) return;
    if (recomputeDirty()) { setStatus('This report changed on another session. Save to overwrite, or refresh to sync.'); return; }
    hydrateFromNote(note); setStatus('Synced latest updates.');
  }, [noteQuery.data, hydrateFromNote, recomputeDirty, lastSavedAt]);

  useEffect(() => () => { if (saveTimerRef.current) clearTimeout(saveTimerRef.current); }, []);

  const createMutation = useMutation({
    mutationFn: (payload: { title: string; body: NoteBlock[]; pinned: boolean }) => apiFetchJson<NoteDetail>('/api/notes', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }),
    onSuccess: (note) => {
      setStatus('Report created.'); setSaveState('saved'); setLastSavedAt(note.updated_at || null); queryClient.setQueryData(['investment-note', note.id], note);
      queryClient.setQueryData<NoteSummary[] | undefined>(['investment-notes'], (prev) => {
        const imgCount = note.body?.filter(b => b.type === 'image').length || 0;
        const summary: NoteSummary = { id: note.id, title: note.title || 'Untitled Note', pinned: !!note.pinned, image_count: imgCount, created_at: note.created_at, updated_at: note.updated_at };
        const base = prev ? prev.filter((item) => item.id !== note.id) : []; return sortNoteSummaries([summary, ...base]);
      });
      setSelectedNoteId(note.id);
    },
  });

  const updateMutation = useMutation({
    mutationFn: async (payload: { id: string; title: string; body: NoteBlock[]; pinned: boolean }) => apiFetchJson<NoteDetail>(`/api/notes/${payload.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: payload.title, body: payload.body, pinned: payload.pinned }) }),
    onSuccess: (note, variables) => {
      setStatus(null); setSaveState('saved'); setLastSavedAt(note.updated_at || null); queryClient.setQueryData(['investment-note', note.id], note);
      queryClient.setQueryData<NoteSummary[]>(['investment-notes'], (prev) => {
        if (!prev) return prev;
        return sortNoteSummaries(prev.map((item) => item.id === note.id ? { ...item, title: note.title || 'Untitled Note', pinned: !!note.pinned, updated_at: note.updated_at, image_count: note.body?.filter(b => b.type === 'image').length || item.image_count } : item));
      });
      const textBlock = variables.body?.find(b => b.type === 'text');
      originalRef.current = { title: variables.title || '', content: textBlock?.value || '', pinned: !!variables.pinned }; recomputeDirty();
    },
    onError: (err: any) => { setSaveState('error'); setStatus(err?.message || 'Save failed.'); },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => { const res = await apiFetch(`/api/notes/${id}`, { method: 'DELETE' }); if (!res.ok) throw new Error(await parseErrorMessage(res)); },
    onSuccess: (_data, deletedId) => { setStatus('Report deleted.'); queryClient.removeQueries({ queryKey: ['investment-note', deletedId], exact: true }); queryClient.setQueryData<NoteSummary[] | undefined>(['investment-notes'], (prev) => prev ? prev.filter((item) => item.id !== deletedId) : prev); },
  });

  const uploadMutation = useMutation({
    mutationFn: async ({ id, file }: { id: string; file: File }) => { const formData = new FormData(); formData.append('file', file); const res = await apiFetch(`/api/notes/${id}/images`, { method: 'POST', body: formData }); if (!res.ok) throw new Error(await parseErrorMessage(res)); return (await res.json()) as NoteImageMeta; },
    onError: (err: any) => { setSaveState('error'); setStatus(err?.message || 'Image upload failed.'); },
  });

  const handleFetchChartSnapshot = useCallback(async (chartId: string) => {
    try { const res = await apiFetch(`/api/v1/dashboard/charts/${chartId}/figure`); if (res.ok) { const data = await res.json(); if (data?.figure && typeof data.figure === 'object') return { figure: data.figure }; } } catch { }
    try { const res = await apiFetch(`/api/custom/${chartId}`); if (res.ok) { const data = await res.json(); if (data?.figure) return { figure: data.figure }; } } catch { }
    try { const res = await apiFetch(`/api/custom/${chartId}/refresh`, { method: 'POST' }); if (res.ok) { const data = await res.json(); if (data?.figure) return { figure: data.figure }; } } catch { }
    return { figure: null };
  }, []);

  const selectedNoteIdRef = useRef(selectedNoteId);
  selectedNoteIdRef.current = selectedNoteId;

  const uploadMutateRef = useRef(uploadMutation.mutateAsync);
  uploadMutateRef.current = uploadMutation.mutateAsync;

  const handleImageUpload = useCallback(async (file: File): Promise<{ id: string; url: string }> => {
    const noteId = selectedNoteIdRef.current;
    if (!noteId) throw new Error('Create or select a report first.');
    const MAX_SIZE = 10 * 1024 * 1024; // 10MB
    if (file.size > MAX_SIZE) throw new Error('Image must be under 10MB.');
    if (!file.type.startsWith('image/')) throw new Error('Only image files are allowed.');
    setStatus('Uploading image...'); const image = await uploadMutateRef.current({ id: noteId, file }); const nowIso = new Date().toISOString();
    queryClient.setQueryData<NoteDetail | undefined>(['investment-note', noteId], (prev) => prev ? { ...prev, body: [...(prev.body || []), { id: image.id, type: 'image', data: '', filename: file.name, content_type: file.type }], updated_at: nowIso } : prev);
    queryClient.setQueryData<NoteSummary[] | undefined>(['investment-notes'], (prev) => prev ? sortNoteSummaries(prev.map((item) => item.id === noteId ? { ...item, image_count: (item.image_count || 0) + 1, updated_at: nowIso } : item)) : prev);
    setStatus('Image uploaded.'); return image;
  }, [queryClient]);

  const saveNow = useCallback(() => {
    const noteId = selectedNoteIdRef.current;
    if (!noteId || uploadMutation.isPending || updateMutation.isPending || !recomputeDirty()) return;
    const draftTitle = titleRef.current.trim() || 'Untitled Note'; const draftContent = contentRef.current;
    const currentNote = queryClient.getQueryData<NoteDetail>(['investment-note', noteId]);
    const existingBlocks = currentNote?.body?.filter(b => b.type !== 'text') || [];
    const updatedBody = [{ id: crypto.randomUUID(), type: 'text', value: draftContent }, ...existingBlocks];
    setSaveState('saving'); updateMutation.mutate({ id: noteId, title: draftTitle, body: updatedBody, pinned: pinnedRef.current });
  }, [uploadMutation.isPending, updateMutation, recomputeDirty, queryClient]);

  const queueAutoSave = useCallback(() => {
    if (saveTimerRef.current) { clearTimeout(saveTimerRef.current); saveTimerRef.current = null; }
    if (!selectedNoteId || uploadMutation.isPending || updateMutation.isPending || !recomputeDirty()) return;
    setSaveState((prev) => (prev === 'saving' ? prev : 'idle')); saveTimerRef.current = setTimeout(() => { saveNow(); }, 1700);
  }, [selectedNoteId, uploadMutation.isPending, updateMutation.isPending, recomputeDirty, saveNow]);

  useEffect(() => { if (selectedNoteId && isDirty && !updateMutation.isPending && !uploadMutation.isPending) queueAutoSave(); }, [selectedNoteId, isDirty, updateMutation.isPending, uploadMutation.isPending, queueAutoSave]);

  const handleTitleChange = useCallback((event: ChangeEvent<HTMLInputElement>) => { const nextTitle = event.target.value; titleRef.current = nextTitle; setTitle(nextTitle); queueAutoSave(); }, [queueAutoSave]);
  const handlePinnedToggle = useCallback(() => { const nextPinned = !pinnedRef.current; pinnedRef.current = nextPinned; setPinned(nextPinned); queueAutoSave(); }, [queueAutoSave]);
  const handleEditorChange = useCallback((html: string) => { contentRef.current = html; setEditorValue(html); queueAutoSave(); }, [queueAutoSave]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') { e.preventDefault(); if (saveTimerRef.current) { clearTimeout(saveTimerRef.current); saveTimerRef.current = null; } saveNow(); } };
    window.addEventListener('keydown', onKeyDown); return () => window.removeEventListener('keydown', onKeyDown);
  }, [saveNow]);

  useEffect(() => { if (!isDirty) return; const handler = (e: BeforeUnloadEvent) => { e.preventDefault(); }; window.addEventListener('beforeunload', handler); return () => window.removeEventListener('beforeunload', handler); }, [isDirty]);

  const handleCreateNote = () => { setStatus(null); createMutation.mutate({ title: 'New Report Draft', body: [{ id: crypto.randomUUID(), type: 'text', value: '' }], pinned: false }); };
  const handleDeleteNote = () => { if (!selectedNoteId || !confirm('Delete this report?')) return; if (saveTimerRef.current) { clearTimeout(saveTimerRef.current); saveTimerRef.current = null; } deleteMutation.mutate(selectedNoteId); };

  // ── Save state derived values ──────────────────────────────────────────────
  const saveHint = useMemo(() => {
    if (saveState === 'saving') return 'Saving...';
    if (saveState === 'error') return status || 'Save failed';
    if (isDirty) return 'Unsaved';
    if (saveState === 'saved' && lastSavedAt) return 'Saved';
    if (lastSavedAt) return 'Saved';
    return 'Saved';
  }, [saveState, status, isDirty, lastSavedAt]);

  const saveTimeHint = useMemo(() => {
    if (!lastSavedAt || saveState === 'saving' || isDirty) return null;
    return new Date(lastSavedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }, [lastSavedAt, saveState, isDirty]);

  const statusToneClass = saveState === 'error'
    ? 'border-rose-500/35 bg-rose-500/[0.07] text-rose-400 dark:text-rose-300'
    : isDirty || saveState === 'saving'
      ? 'border-amber-500/30 bg-amber-500/[0.07] text-amber-500 dark:text-amber-300'
      : 'border-emerald-500/25 bg-emerald-500/[0.07] text-emerald-600 dark:text-emerald-400';

  const publishToneClass = pinned
    ? 'border-sky-500/30 bg-sky-500/[0.08] text-sky-500 dark:text-sky-400 hover:bg-sky-500/[0.14]'
    : 'border-border/50 bg-background/80 text-muted-foreground hover:bg-foreground/[0.04] hover:text-foreground';

  if (authLoading || (!isAuthenticated && !authLoading)) return (
    <AppShell hideFooter>
      <div className="h-[calc(100vh-3rem)] flex items-center justify-center text-muted-foreground">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading reports...
      </div>
    </AppShell>
  );

  // ── Sidebar ────────────────────────────────────────────────────────────────
  const sidebarContent = (
    <>
      {/* Search */}
      <div className="px-3 pt-2.5 pb-2 shrink-0">
        <div className="relative">
          <Search className="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground/45 pointer-events-none" />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search reports..."
            style={inputStyle}
            className="w-full h-8 pl-8 pr-3 rounded-lg border border-border/40 text-[11.5px] outline-none transition-colors focus:border-border/70 placeholder:text-muted-foreground/35"
          />
        </div>
      </div>

      {/* List */}
      <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-3 no-scrollbar">
        <div className="px-2 pb-1.5 pt-0.5 text-[9.5px] font-mono uppercase tracking-[0.2em] text-muted-foreground/35 select-none">
          {filteredNotes.length > 0 ? `${filteredNotes.length} document${filteredNotes.length !== 1 ? 's' : ''}` : 'Documents'}
        </div>

        {notesQuery.isLoading && (
          <div className="flex items-center gap-2 px-3 py-3 text-[11px] text-muted-foreground/50">
            <Loader2 className="w-3 h-3 animate-spin" /> Loading...
          </div>
        )}

        {!notesQuery.isLoading && filteredNotes.length === 0 && (
          <div className="px-3 py-8 text-center">
            <FileText className="w-5 h-5 text-muted-foreground/25 mx-auto mb-2" />
            <p className="text-[11px] text-muted-foreground/40">
              {searchQuery ? 'No results' : 'No reports yet'}
            </p>
          </div>
        )}

        <div className="space-y-0.5">
          {filteredNotes.map((note) => {
            const active = note.id === selectedNoteId;
            const dateStr = formatRelativeDate(note.updated_at);
            return (
              <button
                key={note.id}
                onClick={() => setSelectedNoteId(note.id)}
                data-active={active ? 'true' : 'false'}
                className="report-sidebar-item group w-full text-left"
              >
                {/* Active indicator strip */}
                {active && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-sky-400/70" />
                )}
                <div className="flex items-start gap-2.5 min-w-0">
                  {/* Icon */}
                  <div className={`mt-0.5 shrink-0 flex h-7 w-7 items-center justify-center rounded-lg border transition-colors ${
                    active
                      ? 'border-sky-500/30 bg-sky-500/[0.1] text-sky-400'
                      : 'border-border/35 bg-foreground/[0.03] text-muted-foreground/50 group-hover:text-muted-foreground group-hover:border-border/55'
                  }`}>
                    {note.pinned
                      ? <Pin className="w-3 h-3" />
                      : <FileText className="w-3 h-3" />}
                  </div>

                  {/* Text */}
                  <div className="min-w-0 flex-1">
                    <div className={`truncate text-[12px] font-medium leading-snug transition-colors ${
                      active ? 'text-foreground' : 'text-foreground/75 group-hover:text-foreground/90'
                    }`}>
                      {note.title || 'Untitled'}
                    </div>
                    <div className="mt-0.5 text-[10px] text-muted-foreground/40 tabular-nums">
                      {dateStr}
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </>
  );

  // ── Top bar left ───────────────────────────────────────────────────────────
  const topBarLeft = (
    <div className="min-w-0 flex items-center gap-1.5 text-[11px]">
      <span className="font-semibold text-foreground/80 tracking-tight">Reports</span>
      {selectedNoteId && (
        <>
          <span className="text-muted-foreground/30">/</span>
          <span className="truncate max-w-[180px] text-muted-foreground/60">
            {title.trim() || selectedNote?.title || 'Untitled'}
          </span>
          {noteQuery.isFetching && (
            <Loader2 className="w-3 h-3 animate-spin text-muted-foreground/40 shrink-0" />
          )}
        </>
      )}
    </div>
  );

  // ── Top bar right ──────────────────────────────────────────────────────────
  const topBarRight = (
    <>
      {/* Save status badge */}
      {selectedNoteId && (
        <div className={`hidden sm:inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.16em] transition-colors ${statusToneClass}`}>
          {saveState === 'saving'
            ? <Loader2 className="w-2.5 h-2.5 animate-spin" />
            : saveState === 'error'
              ? null
              : isDirty
                ? null
                : <Check className="w-2.5 h-2.5" />}
          {saveHint}
          {saveTimeHint && <span className="opacity-60 font-mono normal-case tracking-normal">{saveTimeHint}</span>}
        </div>
      )}

      {/* Export buttons */}
      <div className="flex items-center gap-0.5 mx-0.5">
        <button
          onClick={() => handleExport('pdf')}
          disabled={!selectedNoteId || !!exportingFormat}
          className="btn-icon"
          title="Export to PDF"
        >
          {exportingFormat === 'pdf'
            ? <Loader2 className="w-3 h-3 animate-spin" />
            : <FileText className="w-3.5 h-3.5" />}
        </button>
        <button
          onClick={() => handleExport('pptx')}
          disabled={!selectedNoteId || !!exportingFormat}
          className="btn-icon"
          title="Export to PowerPoint"
        >
          {exportingFormat === 'pptx'
            ? <Loader2 className="w-3 h-3 animate-spin" />
            : <PresentationIcon className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Save */}
      <button
        onClick={saveNow}
        disabled={!selectedNoteId || !isDirty || updateMutation.isPending || uploadMutation.isPending}
        className="h-6 rounded-md border border-emerald-500/30 bg-emerald-500/[0.07] px-2 text-[10.5px] font-semibold text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/[0.13] inline-flex items-center gap-1.5 disabled:opacity-35 transition-colors"
      >
        {updateMutation.isPending ? <Loader2 className="w-2.5 h-2.5 animate-spin" /> : <Save className="w-2.5 h-2.5" />}
        Save
      </button>

      {/* Delete */}
      <button
        onClick={handleDeleteNote}
        disabled={!selectedNoteId || deleteMutation.isPending}
        className="h-6 rounded-md border border-rose-500/30 bg-rose-500/[0.07] px-2 text-[10.5px] font-semibold text-rose-500 dark:text-rose-400 hover:bg-rose-500/[0.13] inline-flex items-center gap-1.5 disabled:opacity-35 transition-colors"
      >
        {deleteMutation.isPending ? <Loader2 className="w-2.5 h-2.5 animate-spin" /> : <Trash2 className="w-2.5 h-2.5" />}
        Delete
      </button>
    </>
  );

  return (
    <>
      <AppShell hideFooter>
        <NavigatorShell
          sidebarOpen={sidebarOpen}
          onSidebarToggle={toggleSidebar}
          shellClassName="report-shell"
          sidebarClassName="report-sidebar"
          sidebarOpenWidthClassName="w-[260px] xl:w-[280px]"
          sidebarHeaderClassName="report-sidebar-header"
          topBarClassName="report-topbar"
          mainSectionClassName="report-shell"
          mainClassName="report-main-scroll"
          sidebarIcon={<BookOpen className="w-3 h-3 text-sky-400/70" />}
          sidebarLabel="Reports"
          sidebarHeaderActions={
            <button
              onClick={handleCreateNote}
              disabled={createMutation.isPending}
              className="w-5 h-5 rounded-md flex items-center justify-center text-muted-foreground/60 hover:text-foreground hover:bg-foreground/[0.06] transition-colors disabled:opacity-50"
              title="New report"
            >
              {createMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
            </button>
          }
          sidebarContent={sidebarContent}
          topBarLeft={topBarLeft}
          topBarRight={topBarRight}
        >
          {/* ── Canvas ──────────────────────────────────────────────────────── */}
          <div className="h-full min-h-0 overflow-hidden max-w-[1600px] mx-auto w-full">
            <div className="h-full min-h-0 bg-background overflow-hidden">
              <section className="report-canvas min-h-0 h-full overflow-y-auto custom-scrollbar">

                {/* Empty state */}
                {!selectedNoteId && (
                  <div className="h-full flex flex-col items-center justify-center px-6 text-center select-none">
                    <div className="mb-6 relative">
                      {/* Glow ring */}
                      <div className="absolute inset-0 rounded-2xl bg-sky-400/10 blur-xl scale-150" />
                      <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl border border-border/40 bg-card/60 backdrop-blur-sm shadow-sm">
                        <BookOpen className="w-7 h-7 text-muted-foreground/40" />
                      </div>
                    </div>
                    <h2 className="text-[15px] font-semibold tracking-tight text-foreground/80">
                      No document open
                    </h2>
                    <p className="mt-2 max-w-[260px] text-[12px] leading-relaxed text-muted-foreground/50">
                      Select a report from the sidebar, or start a new one.
                    </p>
                    <div className="mt-6 flex items-center gap-2">
                      <button
                        onClick={handleCreateNote}
                        disabled={createMutation.isPending}
                        className="h-8 px-4 rounded-lg border border-sky-500/30 bg-sky-500/[0.07] text-[12px] font-medium text-sky-500 dark:text-sky-400 hover:bg-sky-500/[0.13] transition-colors disabled:opacity-40 inline-flex items-center gap-1.5"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        New report
                      </button>
                    </div>
                  </div>
                )}

                {/* Editor view */}
                {selectedNoteId && (
                  <div className="min-h-full">
                    <div className="relative mx-auto max-w-[720px] px-6 pt-10 pb-24 md:px-10 md:pt-14">

                      {/* Document meta row */}
                      <div className="mb-5 flex items-center gap-2 flex-wrap">
                        {/* Published / Draft pill */}
                        <button
                          onClick={handlePinnedToggle}
                          disabled={!selectedNoteId}
                          className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[10.5px] font-semibold tracking-wide transition-colors disabled:opacity-50 ${publishToneClass}`}
                        >
                          {pinned
                            ? <><PinOff className="w-2.5 h-2.5" />Published</>
                            : <><AlignLeft className="w-2.5 h-2.5" />Draft</>}
                        </button>

                        {/* Date */}
                        {(updatedLabel || createdLabel) && (
                          <span className="text-[10.5px] text-muted-foreground/35 tabular-nums">
                            {updatedLabel ? `Edited ${updatedLabel}` : `Created ${createdLabel}`}
                          </span>
                        )}
                      </div>

                      {/* Title */}
                      <input
                        value={title}
                        onChange={handleTitleChange}
                        placeholder="Untitled"
                        disabled={noteLoading}
                        style={{ background: 'transparent', color: 'rgb(var(--foreground))' }}
                        className="report-title-input w-full text-[38px] md:text-[42px] font-bold tracking-[-0.035em] leading-[1.12] outline-none placeholder:text-muted-foreground/15 disabled:opacity-50"
                      />

                      {/* Stats row */}
                      <div className="mt-3 mb-1 flex flex-wrap items-center gap-x-3 gap-y-1">
                        <StatChip icon={<AlignLeft className="w-2.5 h-2.5" />} label={`${wordCount.toLocaleString()} words`} />
                        <StatChip icon={<Clock className="w-2.5 h-2.5" />} label={`${readingMinutes} min read`} />
                        {chartCount > 0 && <StatChip icon={<BarChart2 className="w-2.5 h-2.5" />} label={`${chartCount} charts`} />}
                        {imageCount > 0 && <StatChip icon={<ImageIcon className="w-2.5 h-2.5" />} label={`${imageCount} images`} />}
                      </div>

                      {/* Divider */}
                      <div className="mt-7 mb-6 h-px bg-border/20" />

                      {/* Editor */}
                      {noteQuery.isError ? (
                        <div className="mt-12 flex flex-col items-center justify-center text-sm text-muted-foreground gap-3">
                          <p className="text-rose-400 text-[13px]">Failed to load note.</p>
                          <button
                            onClick={() => noteQuery.refetch()}
                            className="h-7 px-3 rounded-lg border border-border/40 bg-foreground/[0.03] text-[11px] font-medium hover:bg-foreground/[0.06] transition-colors"
                          >
                            Retry
                          </button>
                        </div>
                      ) : noteLoading ? (
                        <div className="mt-12 flex items-center justify-center text-sm text-muted-foreground gap-2">
                          <Loader2 className="w-4 h-4 animate-spin" /> Loading...
                        </div>
                      ) : (
                        <div className="report-editor-shell">
                          <NotesRichEditor
                            value={editorValue}
                            onChange={handleEditorChange}
                            onImageUpload={handleImageUpload}
                            disabled={!selectedNoteId}
                            chartLibrary={chartLibrary}
                            minHeightClassName="min-h-[56vh] text-[16px] leading-[1.72]"
                            onFetchChartSnapshot={handleFetchChartSnapshot}
                          />
                        </div>
                      )}

                      {/* Status message */}
                      {status && (
                        <div className={`mt-6 text-[11px] font-medium transition-opacity ${
                          saveState === 'error' ? 'text-rose-400' : 'text-muted-foreground/35'
                        }`}>
                          {status}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </section>
            </div>
          </div>
        </NavigatorShell>
      </AppShell>

      {toastError && <Toast message={toastError} onDismiss={() => setToastError(null)} />}
    </>
  );
}

// ── Small helpers ──────────────────────────────────────────────────────────────

function StatChip({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <span className="inline-flex items-center gap-1 text-[10.5px] text-muted-foreground/40 tabular-nums">
      {icon}
      {label}
    </span>
  );
}

function Toast({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  useEffect(() => { const t = setTimeout(onDismiss, 4000); return () => clearTimeout(t); }, [onDismiss]);
  return (
    <div className="fixed bottom-5 right-5 z-[200] flex items-center gap-2.5 rounded-xl border border-rose-500/30 bg-rose-500/[0.12] backdrop-blur-md px-4 py-2.5 text-[12px] font-medium text-rose-400 shadow-lg animate-in slide-in-from-bottom-2 fade-in duration-200">
      {message}
      <button onClick={onDismiss} className="opacity-60 hover:opacity-100 transition-opacity leading-none text-base">&times;</button>
    </div>
  );
}
