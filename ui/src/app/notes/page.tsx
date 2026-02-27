'use client';

import { type ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  FileText,
  Loader2,
  PanelLeftClose,
  PanelLeftOpen,
  Pin,
  PinOff,
  Plus,
  Save,
  Search,
  Trash2,
} from 'lucide-react';

import AppShell from '@/components/AppShell';
import NotesRichEditor from '@/components/NotesRichEditor';
import { useAuth } from '@/context/AuthContext';
import { apiFetch, apiFetchJson } from '@/lib/api';

interface NoteSummary {
  id: string;
  title: string;
  links: string[];
  pinned: boolean;
  image_count: number;
  created_at: string;
  updated_at: string;
}

interface NoteImageMeta {
  id: string;
  filename?: string | null;
  content_type: string;
  created_at: string;
  url: string;
}

interface NoteDetail {
  id: string;
  user_id: string;
  title: string;
  content: string;
  links: string[];
  pinned: boolean;
  created_at: string;
  updated_at: string;
  images: NoteImageMeta[];
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
      // Chart block references embedded by the editor
      doc.querySelectorAll('[data-chart-block]').forEach((el) => {
        const chartId = el.getAttribute('data-chart-id');
        if (chartId) urls.add(`chart://${chartId}`);
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
    .filter((url) => !url.startsWith('/api/notes/images/'))
    .slice(0, 40);
}

async function parseErrorMessage(res: Response): Promise<string> {
  const body = await res.json().catch(() => ({}));
  return body?.detail || body?.message || `Request failed (${res.status})`;
}

export default function NotesPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isAuthenticated, loading: authLoading } = useAuth();

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [title, setTitle] = useState('');
  const [editorValue, setEditorValue] = useState('');
  const [pinned, setPinned] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);

  const originalRef = useRef<{ title: string; content: string; pinned: boolean } | null>(null);
  const hydratedNoteIdRef = useRef<string | null>(null);
  const lastServerUpdatedAtRef = useRef<string | null>(null);
  const titleRef = useRef('');
  const contentRef = useRef('');
  const pinnedRef = useRef(false);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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
    const nextContent = note.content || '';
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

  const createMutation = useMutation({
    mutationFn: (payload: { title: string; content: string; links: string[]; pinned: boolean }) =>
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
        const summary: NoteSummary = {
          id: note.id,
          title: note.title || 'Untitled Note',
          links: Array.isArray(note.links) ? note.links : [],
          pinned: !!note.pinned,
          image_count: Array.isArray(note.images) ? note.images.length : 0,
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
    mutationFn: async (payload: { id: string; title: string; content: string; links: string[]; pinned: boolean }) =>
      apiFetchJson<NoteDetail>(`/api/notes/${payload.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: payload.title,
          content: payload.content,
          links: payload.links,
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
                links: Array.isArray(note.links) ? note.links : [],
                pinned: !!note.pinned,
                updated_at: note.updated_at,
                image_count: Array.isArray(note.images) ? note.images.length : item.image_count,
              }
            : item
        );
        return sortNoteSummaries(next);
      });
      originalRef.current = {
        title: variables.title || '',
        content: variables.content || '',
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
    return apiFetchJson<{ figure: any; name?: string | null; updated_at?: string | null }>(
      `/api/custom/${chartId}`
    );
  }, []);

  const handleImageUpload = useCallback(
    async (file: File): Promise<NoteImageMeta> => {
      if (!selectedNoteId) {
        throw new Error('Create or select a report first.');
      }
      setStatus('Uploading image...');
      const image = await uploadMutation.mutateAsync({ id: selectedNoteId, file });
      const nowIso = new Date().toISOString();
      queryClient.setQueryData<NoteDetail | undefined>(['investment-note', selectedNoteId], (prev) =>
        prev ? { ...prev, images: [...(prev.images || []), image], updated_at: nowIso } : prev
      );
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
    setSaveState('saving');
    updateMutation.mutate({
      id: selectedNoteId,
      title: draftTitle,
      content: draftContent,
      links: extractLinks(draftContent),
      pinned: pinnedRef.current,
    });
  }, [selectedNoteId, uploadMutation.isPending, updateMutation, recomputeDirty]);

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

  return (
    <AppShell hideFooter>
      <div className="h-[calc(100vh-40px)] flex">
        {/* ── Sidebar ── */}
        <aside className={`shrink-0 transition-all duration-200 overflow-hidden border-r border-border/50 bg-card/20 backdrop-blur-sm flex flex-col ${sidebarOpen ? 'w-[190px]' : 'w-0'}`}>
          {/* Sidebar header */}
          <div className="h-8 px-2.5 border-b border-border/50 flex items-center justify-between shrink-0">
            <div className="text-[11px] font-semibold tracking-wide flex items-center gap-1.5 text-muted-foreground">
              <FileText className="w-3.5 h-3.5 text-sky-400" />
              Reports
            </div>
            <div className="flex items-center gap-0.5">
              <button
                onClick={handleCreateNote}
                disabled={createMutation.isPending}
                className="w-5 h-5 rounded flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-foreground/8 transition-colors disabled:opacity-50"
                title="New report"
              >
                {createMutation.isPending ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Plus className="w-3 h-3" />
                )}
              </button>
              <button
                onClick={() => setSidebarOpen(false)}
                className="w-5 h-5 rounded flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-foreground/8 transition-colors"
                title="Collapse sidebar"
              >
                <PanelLeftClose className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Search */}
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

          {/* Note list */}
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
        </aside>

        {/* ── Editor area ── */}
        <section className="min-h-0 flex-1 flex flex-col bg-background overflow-hidden">
          {/* Top bar */}
          <div className="h-8 px-2.5 border-b border-border/50 flex items-center justify-between gap-2 shrink-0">
            <div className="flex items-center gap-1.5">
              {!sidebarOpen && (
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="w-6 h-6 rounded flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-foreground/8 transition-colors"
                  title="Open sidebar"
                >
                  <PanelLeftOpen className="w-3.5 h-3.5" />
                </button>
              )}
              <div className="text-[11px] text-muted-foreground inline-flex items-center gap-1.5">
                {selectedNoteId && noteQuery.isFetching && (
                  <Loader2 className="w-3 h-3 animate-spin text-sky-400" />
                )}
                {saveHint}
              </div>
            </div>
            <div className="flex items-center gap-1">
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
                {updateMutation.isPending ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Save className="w-3 h-3" />
                )}
                Save
              </button>
              <button
                onClick={handleDeleteNote}
                disabled={!selectedNoteId || deleteMutation.isPending}
                className="h-6 px-2 rounded border border-rose-500/35 bg-rose-500/10 text-[11px] font-medium text-rose-300 hover:bg-rose-500/18 inline-flex items-center gap-1.5 disabled:opacity-40 transition-colors"
              >
                {deleteMutation.isPending ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Trash2 className="w-3 h-3" />
                )}
                Delete
              </button>
            </div>
          </div>

          {/* Document area */}
          <div className="min-h-0 flex-1 overflow-y-auto custom-scrollbar">
            <div className="max-w-2xl mx-auto px-4 py-6">
              {!selectedNoteId && (
                <div className="h-[40vh] rounded-lg border border-border/50 bg-card/25 flex flex-col items-center justify-center gap-3 text-muted-foreground">
                  <FileText className="w-6 h-6 opacity-30" />
                  <p className="text-sm">Select or create a report.</p>
                  <button
                    onClick={handleCreateNote}
                    disabled={createMutation.isPending}
                    className="h-7 px-3 rounded border border-border/50 text-[12px] font-medium hover:bg-accent/10 transition-colors disabled:opacity-40"
                  >
                    <Plus className="w-3 h-3 inline mr-1" />
                    New Report
                  </button>
                </div>
              )}

              {selectedNoteId && (
                <>
                  <input
                    value={title}
                    onChange={handleTitleChange}
                    placeholder="Untitled Report"
                    disabled={noteLoading}
                    className="w-full bg-transparent text-2xl md:text-3xl font-bold tracking-tight outline-none placeholder:text-muted-foreground/30 disabled:opacity-50 mb-1"
                  />
                  <div className="text-[10px] text-muted-foreground/40 mb-4 font-mono">
                    <kbd className="px-1 rounded border border-border/40 bg-background text-[9px]">/</kbd>
                    {' '}blocks &middot;{' '}
                    <kbd className="px-1 rounded border border-border/40 bg-background text-[9px]">/chart</kbd>
                    {' '}snapshot
                  </div>

                  {noteLoading ? (
                    <div className="h-[40vh] rounded-lg border border-border/50 bg-card/25 flex items-center justify-center text-sm text-muted-foreground">
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                      Loading...
                    </div>
                  ) : (
                    <NotesRichEditor
                      value={editorValue}
                      onChange={handleEditorChange}
                      onImageUpload={handleImageUpload}
                      disabled={!selectedNoteId}
                      chartLibrary={chartLibrary}
                      minHeightClassName="min-h-[50vh]"
                      onFetchChartSnapshot={handleFetchChartSnapshot}
                    />
                  )}

                  {status && (
                    <div className={`mt-3 text-[11px] ${saveState === 'error' ? 'text-rose-300' : 'text-muted-foreground/60'}`}>
                      {status}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
