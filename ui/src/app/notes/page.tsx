'use client';

import { type ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlignLeft,
  Columns2,
  ExternalLink,
  FileText,
  Loader2,
  Maximize2,
  Minimize2,
  Pin,
  PinOff,
  Plus,
  Save,
  Search,
  Trash2,
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
      // Regular links
      doc.querySelectorAll('a[href]').forEach((el) => {
        const href = (el.getAttribute('href') || '').trim();
        if (href) urls.add(href);
      });
    } catch {
      // Fallback to regex extraction.
    }
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

// ─────────────────────────────────────────────────────────────────────────────
// Self-contained second note pane for split view
// ─────────────────────────────────────────────────────────────────────────────

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
      // Reconstruct body preserving non-text blocks
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
    <div className="flex-1 min-w-0 min-h-0 h-full flex flex-col">
      {/* Pane header — note picker + save state */}
      <div className="h-8 px-2.5 border-b border-border/40 flex items-center gap-2 shrink-0">
        <select
          value={selectedNoteId || ''}
          onChange={(e) => setSelectedNoteId(e.target.value || null)}
          className="flex-1 min-w-0 text-[11px] bg-transparent border-none outline-none text-foreground font-medium cursor-pointer"
          style={formStyle}
        >
          {notes.length === 0 && <option value="">No notes</option>}
          {notes.map((n) => (
            <option key={n.id} value={n.id}>{n.title || 'Untitled'}</option>
          ))}
        </select>
        {saveHint && (
          <span className={`text-[10px] shrink-0 ${saveState === 'error' ? 'text-rose-400' : isDirty ? 'text-amber-400/70' : 'text-muted-foreground/40'}`}>
            {saveHint}
          </span>
        )}
        <button
          onClick={saveNow}
          disabled={!isDirty || updateMutation.isPending}
          className="h-5 px-1.5 rounded border border-emerald-500/30 bg-emerald-500/[0.08] text-[10px] font-medium text-emerald-400 hover:bg-emerald-500/15 disabled:opacity-30 transition-colors shrink-0"
        >
          Save
        </button>
      </div>

      {/* Editor area */}
      <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar px-6 py-8 md:px-10 bg-background">
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
          <div className="max-w-3xl mx-auto">
            <input
              value={title}
              onChange={handleTitleChange}
              placeholder="Untitled"
              className="w-full bg-transparent text-3xl md:text-4xl font-bold tracking-tight outline-none placeholder:text-muted-foreground/20 mb-4"
            />
            <NotesRichEditor
              value={editorValue}
              onChange={handleEditorChange}
              onImageUpload={handleImageUpload}
              disabled={!selectedNoteId}
              chartLibrary={chartLibrary}
              minHeightClassName="min-h-[60vh] text-lg"
              onFetchChartSnapshot={onFetchChartSnapshot}
            />
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
  const [focusMode, setFocusMode] = useState(false);
  const [dualPane, setDualPane] = useState(false);
  const [splitRatio, setSplitRatio] = useState(68);

  const originalRef = useRef<{ title: string; content: string; pinned: boolean } | null>(null);
  const hydratedNoteIdRef = useRef<string | null>(null);
  const lastServerUpdatedAtRef = useRef<string | null>(null);
  const titleRef = useRef('');
  const contentRef = useRef('');
  const pinnedRef = useRef(false);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const splitDraggingRef = useRef(false);
  const splitResizeRafRef = useRef(0);

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
      setSelectedNoteId(null);
      setTitle('');
      setEditorValue('');
      setPinned(false);
      setIsDirty(false);
      setLastSavedAt(null);
      setSaveState('idle');
      titleRef.current = '';
      contentRef.current = '';
      pinnedRef.current = false;
      hydratedNoteIdRef.current = null;
      lastServerUpdatedAtRef.current = null;
      originalRef.current = null;
      return;
    }
    if (!selectedNoteId || !notes.some((n) => n.id === selectedNoteId)) {
      setSelectedNoteId(notes[0].id);
    }
  }, [notes, selectedNoteId]);

  useEffect(() => {
    hydratedNoteIdRef.current = null;
  }, [selectedNoteId]);

  const filteredNotes = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return notes;
    return notes.filter(
      (n) =>
        (n.title || '').toLowerCase().includes(q) ||
        (n.links || []).some((l) => l.toLowerCase().includes(q))
    );
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
  const chartCount = useMemo(() => (editorValue.match(/data-chart-block/g) || []).length, [editorValue]);
  const imageCount = noteQuery.data?.images?.length ?? 0;
  const currentLinks = useMemo(() => extractLinks(editorValue), [editorValue]);

  const recomputeDirty = useCallback(() => {
    const original = originalRef.current;
    const dirty = Boolean(
      original &&
        selectedNoteId &&
        (titleRef.current !== original.title ||
          contentRef.current !== original.content ||
          pinnedRef.current !== original.pinned)
    );
    setIsDirty((prev) => (prev === dirty ? prev : dirty));
    return dirty;
  }, [selectedNoteId]);

  const hydrateFromNote = useCallback((note: NoteDetail) => {
    const nextTitle = note.title || '';
    const textBlock = note.body?.find(b => b.type === 'text');
    const nextContent = textBlock?.value || '';
    const nextPinned = !!note.pinned;

    titleRef.current = nextTitle;
    contentRef.current = nextContent;
    pinnedRef.current = nextPinned;
    setTitle(nextTitle);
    setEditorValue(nextContent);
    setPinned(nextPinned);
    setIsDirty(false);
    setLastSavedAt(note.updated_at || null);
    setSaveState('idle');
    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current);
      saveTimerRef.current = null;
    }
    originalRef.current = {
      title: nextTitle,
      content: nextContent,
      pinned: nextPinned,
    };
  }, []);

  useEffect(() => {
    const note = noteQuery.data;
    if (!note) return;

    const incomingUpdatedAt = note.updated_at || null;
    const isFirstHydrationForNote = hydratedNoteIdRef.current !== note.id;

    if (isFirstHydrationForNote) {
      hydratedNoteIdRef.current = note.id;
      lastServerUpdatedAtRef.current = incomingUpdatedAt;
      hydrateFromNote(note);
      return;
    }

    if (!incomingUpdatedAt || incomingUpdatedAt === lastServerUpdatedAtRef.current) return;
    lastServerUpdatedAtRef.current = incomingUpdatedAt;
    if (incomingUpdatedAt === lastSavedAt) return;

    if (recomputeDirty()) {
      setStatus('This report changed on another session. Save to overwrite, or refresh to sync.');
      return;
    }

    hydrateFromNote(note);
    setStatus('Synced latest updates.');
  }, [noteQuery.data, hydrateFromNote, recomputeDirty, lastSavedAt]);

  useEffect(
    () => () => {
      if (saveTimerRef.current) {
        clearTimeout(saveTimerRef.current);
      }
    },
    []
  );

  useEffect(() => {
    const onPointerMove = (event: PointerEvent) => {
      if (!splitDraggingRef.current) return;
      const width = window.innerWidth || 1;
      const ratio = Math.max(46, Math.min(82, (event.clientX / width) * 100));
      setSplitRatio(ratio);
      // Notify Plotly (and any other responsive elements) of the container resize
      if (!splitResizeRafRef.current) {
        splitResizeRafRef.current = window.requestAnimationFrame(() => {
          splitResizeRafRef.current = 0;
          window.dispatchEvent(new Event('resize'));
        });
      }
    };
    const onPointerUp = () => {
      splitDraggingRef.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      if (splitResizeRafRef.current) {
        window.cancelAnimationFrame(splitResizeRafRef.current);
        splitResizeRafRef.current = 0;
      }
      window.dispatchEvent(new Event('resize'));
    };
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
    return () => {
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
    };
  }, []);

  const createMutation = useMutation({
    mutationFn: (payload: { title: string; body: NoteBlock[]; pinned: boolean }) =>
      apiFetchJson<NoteDetail>('/api/notes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }),
    onSuccess: (note) => {
      setStatus('Report created.');
      setSaveState('saved');
      setLastSavedAt(note.updated_at || null);
      queryClient.setQueryData(['investment-note', note.id], note);
      queryClient.setQueryData<NoteSummary[] | undefined>(['investment-notes'], (prev) => {
        const imgCount = note.body?.filter(b => b.type === 'image').length || 0;
        const summary: NoteSummary = {
          id: note.id,
          title: note.title || 'Untitled Note',
          pinned: !!note.pinned,
          image_count: imgCount,
          created_at: note.created_at,
          updated_at: note.updated_at,
        };
        const base = prev ? prev.filter((item) => item.id !== note.id) : [];
        return sortNoteSummaries([summary, ...base]);
      });
      setSelectedNoteId(note.id);
    },
  });

  const updateMutation = useMutation({
    mutationFn: async (payload: { id: string; title: string; body: NoteBlock[]; pinned: boolean }) =>
      apiFetchJson<NoteDetail>(`/api/notes/${payload.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: payload.title,
          body: payload.body,
          pinned: payload.pinned,
        }),
      }),
    onSuccess: (note, variables) => {
      setStatus(null);
      setSaveState('saved');
      setLastSavedAt(note.updated_at || null);
      queryClient.setQueryData(['investment-note', note.id], note);
      queryClient.setQueryData<NoteSummary[]>(['investment-notes'], (prev) => {
        if (!prev) return prev;
        const next = prev.map((item) =>
          item.id === note.id
            ? {
                ...item,
                title: note.title || 'Untitled Note',
                pinned: !!note.pinned,
                updated_at: note.updated_at,
                image_count: note.body?.filter(b => b.type === 'image').length || item.image_count,
              }
            : item
        );
        return sortNoteSummaries(next);
      });
      
      const textBlock = variables.body?.find(b => b.type === 'text');
      originalRef.current = {
        title: variables.title || '',
        content: textBlock?.value || '',
        pinned: !!variables.pinned,
      };
      recomputeDirty();
    },
    onError: (err: any) => {
      setSaveState('error');
      setStatus(err?.message || 'Save failed.');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await apiFetch(`/api/notes/${id}`, { method: 'DELETE' });
      if (!res.ok) {
        throw new Error(await parseErrorMessage(res));
      }
    },
    onSuccess: (_data, deletedId) => {
      setStatus('Report deleted.');
      queryClient.removeQueries({ queryKey: ['investment-note', deletedId], exact: true });
      queryClient.setQueryData<NoteSummary[] | undefined>(['investment-notes'], (prev) => {
        if (!prev) return prev;
        return prev.filter((item) => item.id !== deletedId);
      });
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async ({ id, file }: { id: string; file: File }) => {
      const formData = new FormData();
      formData.append('file', file);
      const res = await apiFetch(`/api/notes/${id}/images`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        throw new Error(await parseErrorMessage(res));
      }
      return (await res.json()) as NoteImageMeta;
    },
    onError: (err: any) => {
      setSaveState('error');
      setStatus(err?.message || 'Image upload failed.');
    },
  });

  const handleFetchChartSnapshot = useCallback(async (chartId: string) => {
    // 1. Try dedicated figure endpoint
    try {
      const res = await apiFetch(`/api/v1/dashboard/charts/${chartId}/figure`);
      if (res.ok) {
        const data = await res.json();
        if (data?.figure && typeof data.figure === 'object') return { figure: data.figure };
      }
    } catch { /* fall through */ }
    // 2. Try full chart record
    try {
      const res = await apiFetch(`/api/custom/${chartId}`);
      if (res.ok) {
        const data = await res.json();
        if (data?.figure) return { figure: data.figure };
      }
    } catch { /* fall through */ }
    // 3. Re-execute chart code server-side if no figure stored
    try {
      const res = await apiFetch(`/api/custom/${chartId}/refresh`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data?.figure) return { figure: data.figure };
      }
    } catch { /* fall through */ }
    return { figure: null };
  }, []);

  const handleImageUpload = useCallback(
    async (file: File): Promise<{ id: string; url: string }> => {
      if (!selectedNoteId) {
        throw new Error('Create or select a report first.');
      }
      setStatus('Uploading image...');
      const image = await uploadMutation.mutateAsync({ id: selectedNoteId, file });
      const nowIso = new Date().toISOString();
      queryClient.setQueryData<NoteDetail | undefined>(['investment-note', selectedNoteId], (prev) => {
        if (!prev) return prev;
        const newBlock = {
          id: image.id,
          type: 'image',
          data: '', // Base64 is managed via the endpoint response, we just push the block structure roughly
          filename: file.name,
          content_type: file.type
        };
        // The backend handles pushing the block, but we reflect it optimistically
        return { ...prev, body: [...(prev.body || []), newBlock], updated_at: nowIso };
      });
      queryClient.setQueryData<NoteSummary[] | undefined>(['investment-notes'], (prev) => {
        if (!prev) return prev;
        return sortNoteSummaries(
          prev.map((item) =>
            item.id === selectedNoteId
              ? { ...item, image_count: (item.image_count || 0) + 1, updated_at: nowIso }
              : item
          )
        );
      });
      setStatus('Image uploaded.');
      return image;
    },
    [selectedNoteId, uploadMutation, queryClient]
  );

  const saveNow = useCallback(() => {
    if (!selectedNoteId) return;
    if (uploadMutation.isPending || updateMutation.isPending) return;
    if (!recomputeDirty()) return;
    
    const draftTitle = titleRef.current.trim() || 'Untitled Note';
    const draftContent = contentRef.current;
    
    // Construct the updated body with the new text block and existing non-text blocks
    const currentNote = queryClient.getQueryData<NoteDetail>(['investment-note', selectedNoteId]);
    const existingBlocks = currentNote?.body?.filter(b => b.type !== 'text') || [];
    
    // Generate UUID locally or just assume backend manages text block
    const updatedBody = [
      { id: crypto.randomUUID(), type: 'text', value: draftContent },
      ...existingBlocks
    ];

    setSaveState('saving');
    updateMutation.mutate({
      id: selectedNoteId,
      title: draftTitle,
      body: updatedBody,
      pinned: pinnedRef.current,
    });
  }, [selectedNoteId, uploadMutation.isPending, updateMutation, recomputeDirty, queryClient]);

  const queueAutoSave = useCallback(() => {
    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current);
      saveTimerRef.current = null;
    }
    if (!selectedNoteId) return;
    if (uploadMutation.isPending || updateMutation.isPending) return;
    if (!recomputeDirty()) return;
    setSaveState((prev) => (prev === 'saving' ? prev : 'idle'));
    saveTimerRef.current = setTimeout(() => {
      saveNow();
    }, 1700);
  }, [selectedNoteId, uploadMutation.isPending, updateMutation.isPending, recomputeDirty, saveNow]);

  useEffect(() => {
    if (selectedNoteId && isDirty && !updateMutation.isPending && !uploadMutation.isPending) {
      queueAutoSave();
    }
  }, [selectedNoteId, isDirty, updateMutation.isPending, uploadMutation.isPending, queueAutoSave]);

  const handleTitleChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      const nextTitle = event.target.value;
      titleRef.current = nextTitle;
      setTitle(nextTitle);
      queueAutoSave();
    },
    [queueAutoSave]
  );

  const handlePinnedToggle = useCallback(() => {
    const nextPinned = !pinnedRef.current;
    pinnedRef.current = nextPinned;
    setPinned(nextPinned);
    queueAutoSave();
  }, [queueAutoSave]);

  const handleEditorChange = useCallback(
    (html: string) => {
      contentRef.current = html;
      setEditorValue(html);
      queueAutoSave();
    },
    [queueAutoSave]
  );

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        if (saveTimerRef.current) {
          clearTimeout(saveTimerRef.current);
          saveTimerRef.current = null;
        }
        saveNow();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [saveNow]);

  useEffect(() => {
    if (!isDirty) return;
    const handler = (e: BeforeUnloadEvent) => { e.preventDefault(); };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [isDirty]);

  const handleCreateNote = () => {
    setStatus(null);
    createMutation.mutate({ title: 'New Report Draft', content: '', links: [], pinned: false });
  };

  const handleDeleteNote = () => {
    if (!selectedNoteId) return;
    if (!confirm('Delete this report?')) return;
    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current);
      saveTimerRef.current = null;
    }
    deleteMutation.mutate(selectedNoteId);
  };

  const saveHint = useMemo(() => {
    if (saveState === 'saving') return 'Saving...';
    if (saveState === 'error') return status || 'Save failed';
    if (isDirty) return 'Unsaved changes';
    if (lastSavedAt)
      return `Saved ${new Date(lastSavedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    return 'Saved';
  }, [saveState, status, isDirty, lastSavedAt]);

  if (authLoading || (!isAuthenticated && !authLoading)) {
    return (
      <AppShell hideFooter>
        <div className="h-[calc(100vh-3rem)] flex items-center justify-center text-muted-foreground">
          <Loader2 className="w-5 h-5 animate-spin mr-2" />
          Loading reports...
        </div>
      </AppShell>
    );
  }

  const sidebarContent = (
    <>
      <div className="px-2 py-1.5 border-b border-border/40 shrink-0">
        <div className="relative">
          <Search className="w-3 h-3 absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground/60" />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search..."
            className="w-full h-6 pl-6 pr-2 rounded border border-border/50 bg-background/50 text-[11px] outline-none focus:ring-1 focus:ring-sky-500/25"
          />
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto py-1 custom-scrollbar">
        {notesQuery.isLoading && (
          <div className="text-[11px] text-muted-foreground px-2.5 py-2">Loading...</div>
        )}
        {!notesQuery.isLoading && filteredNotes.length === 0 && (
          <div className="text-[11px] text-muted-foreground px-2.5 py-2">No reports yet.</div>
        )}
        {filteredNotes.map((note) => {
          const active = note.id === selectedNoteId;
          return (
            <button
              key={note.id}
              onClick={() => setSelectedNoteId(note.id)}
              className={`w-full text-left px-2.5 py-1.5 transition-colors border-l-2 ${
                active
                  ? 'border-l-sky-500/70 bg-sky-500/8 text-foreground'
                  : 'border-l-transparent hover:bg-foreground/5 text-muted-foreground hover:text-foreground'
              }`}
            >
              <div className="flex items-start justify-between gap-1">
                <div className="font-medium text-[12px] truncate leading-tight">{note.title || 'Untitled'}</div>
                {note.pinned && <Pin className="w-2.5 h-2.5 text-sky-400 shrink-0 mt-0.5" />}
              </div>
              <div className="mt-0.5 text-[10px] text-muted-foreground/60 truncate">
                {new Date(note.updated_at).toLocaleDateString()}
              </div>
            </button>
          );
        })}
      </div>
    </>
  );

  return (
    <AppShell hideFooter>
      <NavigatorShell
        sidebarOpen={sidebarOpen}
        onSidebarToggle={() => setSidebarOpen((o) => !o)}
        sidebarIcon={<FileText className="w-3.5 h-3.5 text-sky-400" />}
        sidebarLabel="Reports"
        sidebarHeaderActions={
          <>
            <button
              onClick={handleCreateNote}
              disabled={createMutation.isPending}
              className="w-5 h-5 rounded flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-foreground/8 transition-colors disabled:opacity-50"
              title="New report"
            >
              {createMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
            </button>
          </>
        }
        sidebarContent={sidebarContent}
        topBarLeft={
          <div className="text-[11px] text-muted-foreground inline-flex items-center gap-1.5">
            {selectedNoteId && noteQuery.isFetching && (
              <Loader2 className="w-3 h-3 animate-spin text-sky-400" />
            )}
            {saveHint}
          </div>
        }
        topBarRight={
          <>
            <button
              onClick={() => {
                setDualPane((v) => {
                  if (!v) { setSplitRatio(50); setFocusMode(false); }
                  return !v;
                });
              }}
              className={`h-6 px-2 rounded border text-[11px] font-medium inline-flex items-center gap-1.5 transition-colors ${
                dualPane
                  ? 'border-sky-500/40 bg-sky-500/[0.08] text-sky-400'
                  : 'border-border/50 text-muted-foreground hover:text-foreground'
              }`}
              title={dualPane ? 'Close split view' : 'Open split view'}
            >
              <Columns2 className="w-3 h-3" />
              {dualPane ? 'Exit Split' : 'Split'}
            </button>
            <button
              onClick={() => { setFocusMode((v) => !v); if (!focusMode) setDualPane(false); }}
              className="h-6 px-2 rounded border border-border/50 text-[11px] font-medium text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 transition-colors"
              title={focusMode ? 'Exit focus mode' : 'Focus mode'}
            >
              {focusMode ? <Minimize2 className="w-3 h-3" /> : <Maximize2 className="w-3 h-3" />}
              {focusMode ? 'Exit Focus' : 'Focus'}
            </button>
            <button
              onClick={handlePinnedToggle}
              disabled={!selectedNoteId}
              className="h-6 px-2 rounded border border-border/50 text-[11px] font-medium text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 disabled:opacity-40 transition-colors"
            >
              {pinned ? <PinOff className="w-3 h-3" /> : <Pin className="w-3 h-3" />}
              {pinned ? 'Unpublish' : 'Publish'}
            </button>
            <button
              onClick={saveNow}
              disabled={!selectedNoteId || !isDirty || updateMutation.isPending || uploadMutation.isPending}
              className="h-6 px-2 rounded border border-emerald-500/35 bg-emerald-500/10 text-[11px] font-medium text-emerald-300 hover:bg-emerald-500/18 inline-flex items-center gap-1.5 disabled:opacity-40 transition-colors"
            >
              {updateMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
              Save
            </button>
            <button
              onClick={handleDeleteNote}
              disabled={!selectedNoteId || deleteMutation.isPending}
              className="h-6 px-2 rounded border border-rose-500/35 bg-rose-500/10 text-[11px] font-medium text-rose-300 hover:bg-rose-500/18 inline-flex items-center gap-1.5 disabled:opacity-40 transition-colors"
            >
              {deleteMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3" />}
              Delete
            </button>
          </>
        }
      >
        <div className="h-full min-h-0 p-3 md:p-4 overflow-hidden">
          <div className="h-full min-h-0 rounded-xl border border-border/50 bg-background/70 overflow-hidden">
            <div className="h-full min-h-0 flex">
              <section
                className="min-h-0 h-full overflow-y-auto custom-scrollbar bg-background"
                style={{ width: focusMode ? '100%' : `${splitRatio}%` }}
              >
                {!selectedNoteId && (
                  <div className="h-full flex flex-col items-center justify-center gap-4 text-muted-foreground/60">
                    <FileText className="w-12 h-12 opacity-20" />
                    <p className="text-sm font-medium">Select a note or create a new one.</p>
                    <button
                      onClick={handleCreateNote}
                      disabled={createMutation.isPending}
                      className="mt-2 h-9 px-4 rounded-md border border-border/50 bg-card hover:bg-accent/20 transition-colors disabled:opacity-40 flex items-center shadow-sm"
                    >
                      <Plus className="w-4 h-4 mr-2" />
                      New Note
                    </button>
                  </div>
                )}

                {selectedNoteId && (
                  <div className="max-w-3xl mx-auto px-6 py-12 md:px-12 md:py-16">
                    <input
                      value={title}
                      onChange={handleTitleChange}
                      placeholder="Untitled"
                      disabled={noteLoading}
                      className="w-full bg-transparent text-4xl md:text-5xl font-bold tracking-tight outline-none placeholder:text-muted-foreground/20 disabled:opacity-50 mb-4"
                    />
                    
                    {noteLoading ? (
                      <div className="mt-12 flex items-center justify-center text-sm text-muted-foreground gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Loading blocks...
                      </div>
                    ) : (
                      <NotesRichEditor
                        value={editorValue}
                        onChange={handleEditorChange}
                        onImageUpload={handleImageUpload}
                        disabled={!selectedNoteId}
                        chartLibrary={chartLibrary}
                        minHeightClassName="min-h-[60vh] text-lg"
                        onFetchChartSnapshot={handleFetchChartSnapshot}
                      />
                    )}

                    {status && (
                      <div className={`mt-8 text-[12px] font-medium transition-opacity ${saveState === 'error' ? 'text-rose-400' : 'text-muted-foreground/40'}`}>
                        {status}
                      </div>
                    )}
                  </div>
                )}
              </section>

              {!focusMode && (
                <>
                  <div
                    className="w-1.5 shrink-0 cursor-col-resize border-l border-r border-border/40 bg-foreground/[0.02] hover:bg-foreground/[0.08] transition-colors"
                    onPointerDown={() => {
                      splitDraggingRef.current = true;
                      document.body.style.cursor = 'col-resize';
                      document.body.style.userSelect = 'none';
                    }}
                    title="Drag to resize panels"
                  />
                  {dualPane ? (
                    <NoteEditorPane
                      notes={notes}
                      chartLibrary={chartLibrary}
                      onFetchChartSnapshot={handleFetchChartSnapshot}
                    />
                  ) : (
                  <aside className="min-h-0 h-full flex-1 overflow-y-auto custom-scrollbar border-l border-border/30 bg-card/20">
                    {selectedNoteId && !noteLoading ? (
                      <div className="p-3 space-y-4">

                        {/* Outline */}
                        {headings.length > 0 && (
                          <section>
                            <div className="flex items-center gap-1 text-[9px] font-semibold uppercase tracking-widest text-muted-foreground/40 mb-1.5">
                              <AlignLeft className="w-2.5 h-2.5" />
                              Outline
                            </div>
                            <div className="space-y-0.5">
                              {headings.map((h) => (
                                <div
                                  key={h.key}
                                  className="text-[11px] text-muted-foreground truncate leading-snug py-px"
                                  style={{ paddingLeft: `${(h.level - 1) * 12}px` }}
                                  title={h.text}
                                >
                                  {h.level === 1 ? (
                                    <span className="font-medium text-foreground/70">{h.text}</span>
                                  ) : (
                                    <span>{h.text}</span>
                                  )}
                                </div>
                              ))}
                            </div>
                          </section>
                        )}

                        {/* Document stats */}
                        <section>
                          <div className="text-[9px] font-semibold uppercase tracking-widest text-muted-foreground/40 mb-1.5">Document</div>
                          <div className="grid grid-cols-2 gap-1.5">
                            <div className="rounded-lg border border-border/40 bg-background/40 p-2 text-center">
                              <div className="text-sm font-mono font-semibold text-foreground/80 leading-none tabular-nums">{wordCount}</div>
                              <div className="text-[8px] text-muted-foreground/50 uppercase tracking-wider mt-0.5">words</div>
                            </div>
                            <div className="rounded-lg border border-border/40 bg-background/40 p-2 text-center">
                              <div className="text-sm font-mono font-semibold text-foreground/80 leading-none">{Math.max(1, Math.round(wordCount / 200))}<span className="text-[9px] font-normal text-muted-foreground/50">m</span></div>
                              <div className="text-[8px] text-muted-foreground/50 uppercase tracking-wider mt-0.5">read</div>
                            </div>
                            {chartCount > 0 && (
                              <div className="rounded-lg border border-border/40 bg-background/40 p-2 text-center">
                                <div className="text-sm font-mono font-semibold text-sky-400/80 leading-none">{chartCount}</div>
                                <div className="text-[8px] text-muted-foreground/50 uppercase tracking-wider mt-0.5">charts</div>
                              </div>
                            )}
                            {imageCount > 0 && (
                              <div className="rounded-lg border border-border/40 bg-background/40 p-2 text-center">
                                <div className="text-sm font-mono font-semibold text-foreground/80 leading-none">{imageCount}</div>
                                <div className="text-[8px] text-muted-foreground/50 uppercase tracking-wider mt-0.5">images</div>
                              </div>
                            )}
                          </div>
                        </section>

                        {/* References */}
                        {currentLinks.length > 0 && (
                          <section>
                            <div className="text-[9px] font-semibold uppercase tracking-widest text-muted-foreground/40 mb-1.5">
                              References ({currentLinks.length})
                            </div>
                            <div className="space-y-0.5">
                              {currentLinks.slice(0, 8).map((link, i) => {
                                let display = link;
                                try { display = new URL(link).hostname.replace(/^www\./, ''); } catch { /* keep raw */ }
                                return (
                                  <a
                                    key={i}
                                    href={link}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-1 text-[10px] text-sky-400/70 hover:text-sky-300 py-px group"
                                    title={link}
                                  >
                                    <ExternalLink className="w-2.5 h-2.5 shrink-0 opacity-40 group-hover:opacity-100 transition-opacity" />
                                    <span className="truncate">{display}</span>
                                  </a>
                                );
                              })}
                              {currentLinks.length > 8 && (
                                <div className="text-[9px] text-muted-foreground/40 pl-3.5">+{currentLinks.length - 8} more</div>
                              )}
                            </div>
                          </section>
                        )}

                        {/* Properties */}
                        <section>
                          <div className="text-[9px] font-semibold uppercase tracking-widest text-muted-foreground/40 mb-1.5">Properties</div>
                          <div className="space-y-1.5">
                            <div className="flex items-center justify-between text-[10px]">
                              <span className="text-muted-foreground/60">Status</span>
                              <span className={saveState === 'error' ? 'text-rose-400' : isDirty ? 'text-amber-400/80' : 'text-emerald-400/80'}>
                                {saveHint}
                              </span>
                            </div>
                            <div className="flex items-center justify-between text-[10px]">
                              <span className="text-muted-foreground/60">Pinned</span>
                              <span className={pinned ? 'text-sky-400' : 'text-muted-foreground/40'}>{pinned ? 'Yes' : 'No'}</span>
                            </div>
                            {lastSavedAt && (
                              <div className="flex items-baseline justify-between text-[10px] gap-2">
                                <span className="text-muted-foreground/60 shrink-0">Updated</span>
                                <span className="text-muted-foreground/60 font-mono text-[9px] text-right">
                                  {new Date(lastSavedAt).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                                </span>
                              </div>
                            )}
                            {noteQuery.data?.created_at && (
                              <div className="flex items-baseline justify-between text-[10px] gap-2">
                                <span className="text-muted-foreground/60 shrink-0">Created</span>
                                <span className="text-muted-foreground/60 font-mono text-[9px] text-right">
                                  {new Date(noteQuery.data.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}
                                </span>
                              </div>
                            )}
                          </div>
                        </section>

                      </div>
                    ) : (
                      <div className="p-4 text-[11px] text-muted-foreground/40">Select a report to view details.</div>
                    )}
                  </aside>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </NavigatorShell>
    </AppShell>
  );
}

