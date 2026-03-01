'use client';

import { type ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  FileText,
  Loader2,
  Pin,
  PinOff,
  Plus,
  Save,
  Search,
  Trash2,
  Presentation as PresentationIcon,
} from 'lucide-react';

import AppShell from '@/components/AppShell';
import NavigatorShell from '@/components/NavigatorShell';
import NotesRichEditor from '@/components/NotesRichEditor';
import { useAuth } from '@/context/AuthContext';
import { apiFetch, apiFetchJson } from '@/lib/api';

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

interface CustomChartListItem {
  id: string;
  name?: string | null;
  category?: string | null;
  description?: string | null;
  updated_at?: string | null;
}

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

function NoteEditorPane({
  notes,
  chartLibrary,
  onFetchChartSnapshot,
}: {
  notes: NoteSummary[];
  chartLibrary: CustomChartListItem[];
  onFetchChartSnapshot: (chartId: string) => Promise<{ figure: any }>;
}) {
  const queryClient = useQueryClient();
  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(
    () => notes[1]?.id ?? notes[0]?.id ?? null
  );
  const [title, setTitle] = useState('');
  const [editorValue, setEditorValue] = useState('');
  const [isDirty, setIsDirty] = useState(false);
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);

  const titleRef = useRef('');
  const contentRef = useRef('');
  const originalRef = useRef<{ title: string; content: string } | null>(null);
  const hydratedRef = useRef<string | null>(null);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => { hydratedRef.current = null; }, [selectedNoteId]);
  useEffect(() => () => { if (saveTimerRef.current) clearTimeout(saveTimerRef.current); }, []);

  const noteQuery = useQuery({
    queryKey: ['investment-note', selectedNoteId],
    enabled: !!selectedNoteId,
    queryFn: () => apiFetchJson<NoteDetail>(`/api/notes/${selectedNoteId}`),
    staleTime: 15_000,
  });

  useEffect(() => {
    const note = noteQuery.data;
    if (!note || hydratedRef.current === note.id) return;
    hydratedRef.current = note.id;
    
    const textBlock = note.body?.find(b => b.type === 'text');
    const content = textBlock?.value || '';
    
    titleRef.current = note.title || '';
    contentRef.current = content;
    setTitle(note.title || '');
    setEditorValue(content);
    setIsDirty(false);
    setLastSavedAt(note.updated_at || null);
    setSaveState('idle');
    originalRef.current = { title: note.title || '', content: content };
  }, [noteQuery.data]);

  const uploadMutation = useMutation({
    mutationFn: async ({ id, file }: { id: string; file: File }) => {
      const formData = new FormData();
      formData.append('file', file);
      const res = await apiFetch(`/api/notes/${id}/images`, { method: 'POST', body: formData });
      if (!res.ok) throw new Error('Upload failed');
      return res.json() as Promise<{ id: string; url: string }>;
    },
  });

  const updateMutation = useMutation({
    mutationFn: async (payload: { id: string; title: string; content: string }) => {
      const currentNote = queryClient.getQueryData<NoteDetail>(['investment-note', payload.id]);
      const existingBlocks = currentNote?.body?.filter(b => b.type !== 'text') || [];
      const updatedBody = [
        { id: crypto.randomUUID(), type: 'text', value: payload.content },
        ...existingBlocks
      ];

      return apiFetchJson<NoteDetail>(`/api/notes/${payload.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: payload.title, body: updatedBody, pinned: false }),
      });
    },
    onSuccess: (note) => {
      setSaveState('saved');
      setLastSavedAt(note.updated_at || null);
      queryClient.setQueryData(['investment-note', note.id], note);
      const textBlock = note.body?.find(b => b.type === 'text');
      const content = textBlock?.value || '';
      originalRef.current = { title: note.title || '', content: content };
      setIsDirty(false);
    },
    onError: () => setSaveState('error'),
  });

  const recomputeDirty = useCallback(() => {
    const original = originalRef.current;
    const dirty = Boolean(
      original && selectedNoteId &&
      (titleRef.current !== original.title || contentRef.current !== original.content)
    );
    setIsDirty((prev) => (prev === dirty ? prev : dirty));
    return dirty;
  }, [selectedNoteId]);

  const saveNow = useCallback(() => {
    if (!selectedNoteId || updateMutation.isPending || !recomputeDirty()) return;
    setSaveState('saving');
    updateMutation.mutate({ id: selectedNoteId, title: titleRef.current || 'Untitled', content: contentRef.current });
  }, [selectedNoteId, updateMutation, recomputeDirty]);

  const queueAutoSave = useCallback(() => {
    if (saveTimerRef.current) { clearTimeout(saveTimerRef.current); saveTimerRef.current = null; }
    if (!selectedNoteId || updateMutation.isPending || !recomputeDirty()) return;
    saveTimerRef.current = setTimeout(saveNow, 1700);
  }, [selectedNoteId, updateMutation.isPending, recomputeDirty, saveNow]);

  const handleTitleChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    titleRef.current = e.target.value;
    setTitle(e.target.value);
    queueAutoSave();
  }, [queueAutoSave]);

  const handleEditorChange = useCallback((html: string) => {
    contentRef.current = html;
    setEditorValue(html);
    queueAutoSave();
  }, [queueAutoSave]);

  const handleImageUpload = useCallback(async (file: File): Promise<NoteImageMeta> => {
    if (!selectedNoteId) throw new Error('Select a note first');
    return uploadMutation.mutateAsync({ id: selectedNoteId, file });
  }, [selectedNoteId, uploadMutation]);

  const saveHint = saveState === 'saving' ? 'Saving...'
    : saveState === 'error' ? 'Error'
    : isDirty ? 'Unsaved'
    : lastSavedAt ? `Saved ${new Date(lastSavedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
    : '';

  const noteLoading = !!selectedNoteId && noteQuery.isLoading;
  const formStyle = { backgroundColor: 'rgb(var(--background))', color: 'rgb(var(--foreground))' };

  return (
    <div className="report-canvas flex-1 min-w-0 min-h-0 h-full flex flex-col">
      <div className="h-10 px-4 border-b border-border/30 flex items-center gap-2 shrink-0 bg-background/65 backdrop-blur-xl">
        <select
          value={selectedNoteId || ''}
          onChange={(e) => setSelectedNoteId(e.target.value || null)}
          className="h-8 flex-1 min-w-0 rounded-lg border border-border/45 bg-background/80 px-3 text-[11px] outline-none text-foreground font-medium cursor-pointer"
          style={formStyle}
        >
          {notes.length === 0 && <option value="">No notes</option>}
          {notes.map((n) => (
            <option key={n.id} value={n.id}>{n.title || 'Untitled'}</option>
          ))}
        </select>
        {saveHint && (
          <span className={`shrink-0 rounded-full border px-2.5 py-1 text-[10px] font-medium ${saveState === 'error' ? 'border-rose-500/30 bg-rose-500/10 text-rose-300' : isDirty ? 'border-amber-500/25 bg-amber-500/10 text-amber-200' : 'border-emerald-500/20 bg-emerald-500/10 text-emerald-200'}`}>
            {saveHint}
          </span>
        )}
        <button
          onClick={saveNow}
          disabled={!isDirty || updateMutation.isPending}
          className="h-8 px-3 rounded-lg border border-emerald-500/30 bg-emerald-500/[0.08] text-[11px] font-medium text-emerald-300 hover:bg-emerald-500/15 disabled:opacity-30 transition-colors shrink-0"
        >
          Save
        </button>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar">
        {!selectedNoteId ? (
          <div className="h-full flex flex-col items-center justify-center text-muted-foreground/50 text-sm">
            <FileText className="w-8 h-8 opacity-20 mb-3" />
            <p>Select a note to edit.</p>
          </div>
        ) : noteLoading ? (
          <div className="h-32 flex items-center justify-center text-muted-foreground/50 text-sm gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading…
          </div>
        ) : (
          <div className="mx-auto max-w-4xl px-6 py-10 md:px-10 md:py-12">
            <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl border border-border/40 bg-background/90 shadow-lg shadow-black/10">
              <FileText className="w-6 h-6 text-sky-400/80" />
            </div>
            <input
              value={title}
              onChange={handleTitleChange}
              placeholder="Untitled"
              className="report-title-input w-full bg-transparent text-4xl md:text-5xl font-bold tracking-tight outline-none placeholder:text-muted-foreground/20 mb-5"
            />
            <div className="report-editor-shell">
              <NotesRichEditor
                value={editorValue}
                onChange={handleEditorChange}
                onImageUpload={handleImageUpload}
                disabled={!selectedNoteId}
                chartLibrary={chartLibrary}
                minHeightClassName="min-h-[56vh] text-lg"
                onFetchChartSnapshot={onFetchChartSnapshot}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function NotesPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isAuthenticated, loading: authLoading } = useAuth();

  const [sidebarOpen, setSidebarOpen] = useState(true);
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const syncSidebarForViewport = () => {
      if (window.innerWidth < 1024) setSidebarOpen(false);
    };
    syncSidebarForViewport();
    window.addEventListener('resize', syncSidebarForViewport);
    return () => window.removeEventListener('resize', syncSidebarForViewport);
  }, []);

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

  const originalRef = useRef<{ title: string; content: string; pinned: boolean } | null>(null);
  const hydratedNoteIdRef = useRef<string | null>(null);
  const lastServerUpdatedAtRef = useRef<string | null>(null);
  const titleRef = useRef('');
  const contentRef = useRef('');
  const pinnedRef = useRef(false);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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
      alert('Failed to generate ' + format.toUpperCase());
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

  useEffect(() => { hydratedNoteIdRef.current = null; }, [selectedNoteId]);

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

  const handleImageUpload = useCallback(async (file: File): Promise<{ id: string; url: string }> => {
    if (!selectedNoteId) throw new Error('Create or select a report first.');
    setStatus('Uploading image...'); const image = await uploadMutation.mutateAsync({ id: selectedNoteId, file }); const nowIso = new Date().toISOString();
    queryClient.setQueryData<NoteDetail | undefined>(['investment-note', selectedNoteId], (prev) => prev ? { ...prev, body: [...(prev.body || []), { id: image.id, type: 'image', data: '', filename: file.name, content_type: file.type }], updated_at: nowIso } : prev);
    queryClient.setQueryData<NoteSummary[] | undefined>(['investment-notes'], (prev) => prev ? sortNoteSummaries(prev.map((item) => item.id === selectedNoteId ? { ...item, image_count: (item.image_count || 0) + 1, updated_at: nowIso } : item)) : prev);
    setStatus('Image uploaded.'); return image;
  }, [selectedNoteId, uploadMutation, queryClient]);

  const saveNow = useCallback(() => {
    if (!selectedNoteId || uploadMutation.isPending || updateMutation.isPending || !recomputeDirty()) return;
    const draftTitle = titleRef.current.trim() || 'Untitled Note'; const draftContent = contentRef.current;
    const currentNote = queryClient.getQueryData<NoteDetail>(['investment-note', selectedNoteId]);
    const existingBlocks = currentNote?.body?.filter(b => b.type !== 'text') || [];
    const updatedBody = [{ id: crypto.randomUUID(), type: 'text', value: draftContent }, ...existingBlocks];
    setSaveState('saving'); updateMutation.mutate({ id: selectedNoteId, title: draftTitle, body: updatedBody, pinned: pinnedRef.current });
  }, [selectedNoteId, uploadMutation.isPending, updateMutation, recomputeDirty, queryClient]);

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

  const saveHint = useMemo(() => { if (saveState === 'saving') return 'Saving...'; if (saveState === 'error') return status || 'Save failed'; if (isDirty) return 'Unsaved changes'; if (lastSavedAt) return `Saved ${new Date(lastSavedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`; return 'Saved'; }, [saveState, status, isDirty, lastSavedAt]);
  const statusToneClass = saveState === 'error'
    ? 'border-rose-500/35 bg-rose-500/12 text-rose-300'
    : isDirty
      ? 'border-amber-500/30 bg-amber-500/12 text-amber-200'
      : 'border-emerald-500/25 bg-emerald-500/12 text-emerald-200';
  const publishToneClass = pinned
    ? 'border-sky-500/30 bg-sky-500/12 text-sky-200 hover:bg-sky-500/18'
    : 'border-border/45 bg-background/75 text-muted-foreground hover:bg-background hover:text-foreground';
  const toolbarIconButtonClass = 'h-7 w-8 rounded-lg border border-border/45 bg-background/70 text-muted-foreground hover:bg-background hover:text-foreground inline-flex items-center justify-center transition-colors disabled:opacity-40 disabled:cursor-not-allowed';

  if (authLoading || (!isAuthenticated && !authLoading)) return (<AppShell hideFooter><div className="h-[calc(100vh-3rem)] flex items-center justify-center text-muted-foreground"><Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading reports...</div></AppShell>);

  const sidebarContent = (
    <>
      <div className="px-3 py-2 shrink-0">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground/55" />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search reports"
            className="w-full h-9 pl-9 pr-3 rounded-xl border border-border/45 bg-background/70 text-[12px] outline-none focus:ring-1 focus:ring-sky-500/20"
          />
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-3 custom-scrollbar">
        <div className="px-2 pb-2 text-[10px] uppercase tracking-[0.22em] text-muted-foreground/40 text-left">
          Documents
        </div>
        {notesQuery.isLoading && <div className="text-[11px] text-muted-foreground px-3 py-2">Loading...</div>}
        {!notesQuery.isLoading && filteredNotes.length === 0 && <div className="text-[11px] text-muted-foreground px-3 py-2">No reports yet.</div>}
        <div className="space-y-1">
          {filteredNotes.map((note) => {
            const active = note.id === selectedNoteId;
            return (
              <button
                key={note.id}
                onClick={() => setSelectedNoteId(note.id)}
                data-active={active ? 'true' : 'false'}
                className="report-sidebar-item group"
              >
                <div className="flex items-start gap-3">
                  <div className={`mt-0.5 flex h-8 w-8 items-center justify-center rounded-xl border transition-colors ${active ? 'border-sky-500/25 bg-sky-500/12 text-sky-200' : 'border-border/40 bg-background/70 text-muted-foreground/70 group-hover:text-foreground'}`}>
                    {note.pinned ? <Pin className="w-3.5 h-3.5" /> : <FileText className="w-3.5 h-3.5" />}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-3">
                      <div className="truncate text-[12px] font-medium leading-tight text-foreground/90 text-left">{note.title || 'Untitled'}</div>
                      <span className="shrink-0 text-[10px] text-muted-foreground/65">{new Date(note.updated_at).toLocaleDateString([], { month: 'short', day: 'numeric' })}</span>
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

  return (
    <AppShell hideFooter>
      <NavigatorShell
        sidebarOpen={sidebarOpen}
        onSidebarToggle={() => setSidebarOpen((o) => !o)}
        shellClassName="report-shell"
        sidebarClassName="report-sidebar"
        sidebarOpenWidthClassName="w-[260px] xl:w-[280px]"
        sidebarHeaderClassName="bg-background/55 backdrop-blur-xl"
        topBarClassName="report-topbar"
        mainSectionClassName="report-shell"
        mainClassName="report-main-scroll"
        sidebarIcon={<FileText className="w-3.5 h-3.5 text-sky-400/80" />}
        sidebarLabel="Private"
        sidebarHeaderActions={<button onClick={handleCreateNote} disabled={createMutation.isPending} className="w-6 h-6 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-foreground/8 transition-colors disabled:opacity-50" title="New report">{createMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}</button>}
        sidebarContent={sidebarContent}
        topBarLeft={<div className="min-w-0 flex items-center gap-2 text-[11px] text-muted-foreground/70"><span className="font-semibold text-foreground/85">Reports</span>{selectedNoteId && <><span className="text-muted-foreground/35">/</span><span className="truncate max-w-[220px]">{title.trim() || selectedNote?.title || 'Untitled'}</span></>}{selectedNoteId && noteQuery.isFetching && <Loader2 className="w-3 h-3 animate-spin text-sky-400" />}</div>}
        topBarRight={
          <>
            {selectedNoteId && <div className={`hidden md:inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${statusToneClass}`}>{saveHint}</div>}
            <div className="flex items-center gap-1 mr-1">
              <button onClick={() => handleExport('pdf')} disabled={!selectedNoteId || !!exportingFormat} className={toolbarIconButtonClass} title="Export to PDF">{exportingFormat === 'pdf' ? <Loader2 className="w-3 h-3 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}</button>
              <button onClick={() => handleExport('pptx')} disabled={!selectedNoteId || !!exportingFormat} className={toolbarIconButtonClass} title="Export to PowerPoint">{exportingFormat === 'pptx' ? <Loader2 className="w-3 h-3 animate-spin" /> : <PresentationIcon className="w-3.5 h-3.5" />}</button>
            </div>
            <button onClick={saveNow} disabled={!selectedNoteId || !isDirty || updateMutation.isPending || uploadMutation.isPending} className="h-7 rounded-lg border border-emerald-500/35 bg-emerald-500/10 px-2.5 text-[11px] font-medium text-emerald-200 hover:bg-emerald-500/18 inline-flex items-center gap-1.5 disabled:opacity-40 transition-colors">{updateMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}Save</button>
            <button onClick={handleDeleteNote} disabled={!selectedNoteId || deleteMutation.isPending} className="h-7 rounded-lg border border-rose-500/35 bg-rose-500/10 px-2.5 text-[11px] font-medium text-rose-200 hover:bg-rose-500/18 inline-flex items-center gap-1.5 disabled:opacity-40 transition-colors">{deleteMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3" />}Delete</button>
          </>
        }
      >
        <div className="h-full min-h-0 px-3 py-3 md:px-4 md:py-4 overflow-hidden max-w-[1600px] mx-auto w-full">
          <div className="h-full min-h-0 rounded-[28px] border border-border/40 bg-background/55 overflow-hidden shadow-[0_28px_90px_rgba(0,0,0,0.22)]">
            <div className="h-full min-h-0">
              <section className="report-canvas min-h-0 h-full overflow-y-auto custom-scrollbar">
                {!selectedNoteId && (
                  <div className="report-empty-state h-full flex flex-col items-center justify-center px-6 text-center">
                    <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-[1.4rem] border border-border/40 bg-background/90 shadow-xl shadow-black/10">
                      <FileText className="w-7 h-7 text-sky-400/80" />
                    </div>
                    <h2 className="text-2xl font-semibold tracking-tight text-foreground">Create your next report</h2>
                    <p className="mt-3 max-w-md text-sm leading-6 text-muted-foreground/70">This workspace keeps the document front and center with the same block editor, export flow, and autosave behavior you already had.</p>
                    <button onClick={handleCreateNote} disabled={createMutation.isPending} className="mt-6 h-10 px-4 rounded-xl border border-border/45 bg-background/85 hover:bg-background text-[12px] font-medium transition-colors disabled:opacity-40 inline-flex items-center shadow-sm"><Plus className="w-4 h-4 mr-2" />New Report</button>
                  </div>
                )}
                {selectedNoteId && (
                  <div className="min-h-full">
                    <div className="report-cover h-28 md:h-36" />
                    <div className="relative mx-auto max-w-4xl px-6 pb-16 -mt-10 md:px-12 md:-mt-12">
                      <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-[1.4rem] border border-border/40 bg-background/90 shadow-xl shadow-black/10">
                        <FileText className="w-7 h-7 text-sky-400/80" />
                      </div>
                      <div className="mb-4 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground/70">
                        <button onClick={handlePinnedToggle} disabled={!selectedNoteId} className={`rounded-full border px-3 py-1 font-medium transition-colors disabled:opacity-50 ${publishToneClass}`}>{pinned ? <PinOff className="w-3.5 h-3.5 inline mr-1.5 align-[-2px]" /> : <Pin className="w-3.5 h-3.5 inline mr-1.5 align-[-2px]" />}{pinned ? 'Published' : 'Draft'}</button>
                        <span className={`rounded-full border px-3 py-1 font-medium ${statusToneClass}`}>{saveHint}</span>
                      </div>
                      <div className="flex items-start justify-between gap-4">
                        <input value={title} onChange={handleTitleChange} placeholder="Untitled" disabled={noteLoading} className="report-title-input min-w-0 flex-1 bg-transparent text-3xl md:text-4xl font-bold tracking-tight outline-none placeholder:text-muted-foreground/20 disabled:opacity-50" />
                        <div className="shrink-0 pt-1 text-right text-[12px] text-muted-foreground/60">
                          {updatedLabel || createdLabel || ''}
                        </div>
                      </div>
                      <div className="mt-4 mb-8 flex flex-wrap items-center gap-3 text-[12px] text-muted-foreground/70">
                        <span>{wordCount.toLocaleString()} words</span>
                        <span>{readingMinutes} min read</span>
                        {chartCount > 0 && <span>{chartCount} charts</span>}
                        {imageCount > 0 && <span>{imageCount} images</span>}
                      </div>
                      {noteLoading
                        ? <div className="mt-12 flex items-center justify-center text-sm text-muted-foreground gap-2"><Loader2 className="w-4 h-4 animate-spin" />Loading blocks...</div>
                        : <div className="report-editor-shell"><NotesRichEditor value={editorValue} onChange={handleEditorChange} onImageUpload={handleImageUpload} disabled={!selectedNoteId} chartLibrary={chartLibrary} minHeightClassName="min-h-[56vh] text-lg" onFetchChartSnapshot={handleFetchChartSnapshot} /></div>}
                      {status && <div className={`mt-8 text-[12px] font-medium transition-opacity ${saveState === 'error' ? 'text-rose-400' : 'text-muted-foreground/50'}`}>{status}</div>}
                    </div>
                  </div>
                )}
              </section>
            </div>
          </div>
        </div>
      </NavigatorShell>
    </AppShell>
  );
}
