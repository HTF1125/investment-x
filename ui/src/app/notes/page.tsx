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

function sortNoteSummaries(notes: NoteSummary[]): NoteSummary[] {
  return [...notes].sort((a, b) => {
    if (a.pinned !== b.pinned) {
      return a.pinned ? -1 : 1;
    }
    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
  });
}

function extractLinks(raw: string): string[] {
  const urls = new Set<string>();
  const markdownLinkRegex = /\[[^\]]*]\(([^)\s]+)\)/g;
  const rawUrlRegex = /\bhttps?:\/\/[^\s<>"')]+/gi;

  let match: RegExpExecArray | null = null;

  if (typeof window !== 'undefined' && raw.includes('<a')) {
    try {
      const doc = new DOMParser().parseFromString(raw, 'text/html');
      doc.querySelectorAll('a[href]').forEach((el) => {
        const href = (el.getAttribute('href') || '').trim();
        if (href) {
          urls.add(href);
        }
      });
    } catch {
      // Fallback to regex extraction only.
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

  const notes = notesQuery.data || [];

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

  useEffect(() => {
    const note = noteQuery.data;
    if (!note) return;
    if (hydratedNoteIdRef.current === note.id) return;
    hydratedNoteIdRef.current = note.id;
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
  }, [noteQuery.data]);

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
      setStatus('Note created.');
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
    mutationFn: async (payload: { id: string; title: string; content: string; links: string[]; pinned: boolean }) => {
      return apiFetchJson<NoteDetail>(`/api/notes/${payload.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: payload.title,
          content: payload.content,
          links: payload.links,
          pinned: payload.pinned,
        }),
      });
    },
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
      setStatus('Note deleted.');
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

  const handleImageUpload = useCallback(
    async (file: File): Promise<NoteImageMeta> => {
      if (!selectedNoteId) {
        throw new Error('Create or select a note first.');
      }
      setStatus('Uploading image...');
      const image = await uploadMutation.mutateAsync({ id: selectedNoteId, file });
      const nowIso = new Date().toISOString();
      queryClient.setQueryData<NoteDetail | undefined>(['investment-note', selectedNoteId], (prev) =>
        prev
          ? {
              ...prev,
              images: [...(prev.images || []), image],
              updated_at: nowIso,
            }
          : prev
      );
      queryClient.setQueryData<NoteSummary[] | undefined>(['investment-notes'], (prev) => {
        if (!prev) return prev;
        const next = prev.map((item) =>
          item.id === selectedNoteId
            ? {
                ...item,
                image_count: (item.image_count || 0) + 1,
                updated_at: nowIso,
              }
            : item
        );
        return sortNoteSummaries(next);
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
  }, [
    selectedNoteId,
    uploadMutation.isPending,
    updateMutation.isPending,
    recomputeDirty,
    saveNow,
  ]);

  useEffect(() => {
    if (selectedNoteId && isDirty && !updateMutation.isPending && !uploadMutation.isPending) {
      queueAutoSave();
    }
  }, [
    selectedNoteId,
    isDirty,
    updateMutation.isPending,
    uploadMutation.isPending,
    queueAutoSave,
  ]);

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
    createMutation.mutate({
      title: 'New Investment Note',
      content: '',
      links: [],
      pinned: false,
    });
  };

  const handleDeleteNote = () => {
    if (!selectedNoteId) return;
    if (!confirm('Delete this note?')) return;
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
    if (lastSavedAt) return `Saved ${new Date(lastSavedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    return 'Saved';
  }, [saveState, status, isDirty, lastSavedAt]);

  if (authLoading || (!isAuthenticated && !authLoading)) {
    return (
      <AppShell hideFooter>
        <div className="h-[calc(100vh-3rem)] flex items-center justify-center text-muted-foreground">
          <Loader2 className="w-5 h-5 animate-spin mr-2" />
          Loading notes...
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell hideFooter>
      <div className="h-[calc(100vh-3rem)] grid grid-cols-1 lg:grid-cols-[250px_minmax(0,1fr)]">
        <aside className="border-r border-border/50 bg-card/30 backdrop-blur-sm min-h-0 flex flex-col">
          <div className="h-10 px-3 border-b border-border/50 flex items-center justify-between">
            <div className="text-[12px] font-semibold tracking-wide flex items-center gap-2">
              <FileText className="w-4 h-4 text-sky-400" />
              Notes
            </div>
            <button
              onClick={handleCreateNote}
              disabled={createMutation.isPending}
              className="h-6 px-2 rounded-md border border-border/50 text-[11px] font-semibold text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 disabled:opacity-50"
            >
              {createMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
              New
            </button>
          </div>
          <div className="p-2.5 border-b border-border/40">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search notes..."
                className="w-full h-8 pl-8 pr-2.5 rounded-md border border-border/50 bg-background/50 text-xs outline-none focus:ring-2 focus:ring-sky-500/25"
              />
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto p-1.5 space-y-1 custom-scrollbar">
            {notesQuery.isLoading && (
              <div className="text-xs text-muted-foreground px-2 py-3">Loading notes...</div>
            )}
            {!notesQuery.isLoading && filteredNotes.length === 0 && (
              <div className="text-xs text-muted-foreground px-2 py-3">No notes yet.</div>
            )}
            {filteredNotes.map((note) => {
              const active = note.id === selectedNoteId;
              return (
                <button
                  key={note.id}
                  onClick={() => setSelectedNoteId(note.id)}
                  className={`w-full text-left rounded-md px-2.5 py-2 transition-colors border ${
                    active
                      ? 'border-sky-500/35 bg-sky-500/12'
                      : 'border-transparent hover:border-border/50 hover:bg-accent/15'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="font-medium text-[13px] truncate">{note.title || 'Untitled'}</div>
                    {note.pinned && <Pin className="w-3.5 h-3.5 text-sky-300 shrink-0 mt-0.5" />}
                  </div>
                  <div className="mt-1 text-[11px] text-muted-foreground truncate">
                    {new Date(note.updated_at).toLocaleDateString()}
                  </div>
                </button>
              );
            })}
          </div>
        </aside>

        <section className="min-h-0 flex flex-col bg-background">
          <div className="h-10 px-3 border-b border-border/50 flex items-center justify-between gap-2 shrink-0">
            <div className="text-xs text-muted-foreground">{saveHint}</div>
            <div className="flex items-center gap-1.5">
              <button
                onClick={handlePinnedToggle}
                disabled={!selectedNoteId}
                className="h-6 px-2 rounded-md border border-border/50 text-[11px] font-medium text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 disabled:opacity-40"
              >
                {pinned ? <PinOff className="w-3.5 h-3.5" /> : <Pin className="w-3.5 h-3.5" />}
                {pinned ? 'Unpin' : 'Pin'}
              </button>
              <button
                onClick={saveNow}
                disabled={!selectedNoteId || !isDirty || updateMutation.isPending || uploadMutation.isPending}
                className="h-6 px-2 rounded-md border border-emerald-500/35 bg-emerald-500/12 text-[11px] font-medium text-emerald-300 hover:bg-emerald-500/18 inline-flex items-center gap-1.5 disabled:opacity-40"
              >
                {updateMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                Save
              </button>
              <button
                onClick={handleDeleteNote}
                disabled={!selectedNoteId || deleteMutation.isPending}
                className="h-6 px-2 rounded-md border border-rose-500/35 bg-rose-500/12 text-[11px] font-medium text-rose-300 hover:bg-rose-500/18 inline-flex items-center gap-1.5 disabled:opacity-40"
              >
                {deleteMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                Delete
              </button>
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto custom-scrollbar">
            <div className="w-full px-3 py-3 md:px-4 md:py-4 lg:px-5 lg:py-5">
              {!selectedNoteId && (
                <div className="h-[48vh] rounded-lg border border-border/50 bg-card/25 flex items-center justify-center text-sm text-muted-foreground">
                  Create a note to start writing.
                </div>
              )}

              {selectedNoteId && (
                <>
                  <div className="-mx-3 px-3 py-1.5 md:-mx-4 md:px-4 lg:-mx-5 lg:px-5">
                    <input
                      value={title}
                      onChange={handleTitleChange}
                      placeholder="Note title"
                      disabled={noteLoading}
                      className="w-full bg-transparent text-2xl md:text-3xl font-semibold tracking-tight outline-none placeholder:text-muted-foreground/55 disabled:opacity-50"
                    />

                    <div className="mt-1 text-[11px] text-muted-foreground">
                      Paste links/images directly. Images render inline while editing.
                    </div>
                  </div>

                  <div className="mt-2">
                    {noteLoading ? (
                      <div className="h-[48vh] rounded-lg border border-border/50 bg-card/25 flex items-center justify-center text-sm text-muted-foreground">
                        <Loader2 className="w-4 h-4 animate-spin mr-2" />
                        Loading note...
                      </div>
                    ) : (
                      <NotesRichEditor
                        value={editorValue}
                        onChange={handleEditorChange}
                        onImageUpload={handleImageUpload}
                        disabled={!selectedNoteId}
                        minHeightClassName="min-h-[48vh]"
                        toolbarStickyTopClassName="top-0"
                      />
                    )}
                  </div>
                </>
              )}

              {status && (
                <div
                  className={`mt-2 text-xs ${
                    saveState === 'error' ? 'text-rose-300' : 'text-muted-foreground'
                  }`}
                >
                  {status}
                </div>
              )}
            </div>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
