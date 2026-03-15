'use client';

import React, { Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch, apiFetchJson } from '@/lib/api';
import AppShell from '@/components/AppShell';
import ExcalidrawEditor from '@/components/ExcalidrawEditor';
import {
  Plus, ArrowLeft, Loader2, Trash2, PenTool, Clock, LayoutTemplate,
} from 'lucide-react';
import { WELCOME_TEMPLATE, MACRO_RESEARCH_TEMPLATE } from '@/lib/whiteboardTemplates';

// ── Types ──

interface WhiteboardSummary {
  id: string;
  title: string;
  thumbnail: string | null;
  created_at: string;
  updated_at: string;
}

interface WhiteboardDetail {
  id: string;
  user_id: string;
  title: string;
  scene_data: Record<string, any>;
  thumbnail: string | null;
  created_at: string;
  updated_at: string;
}

// ── Helpers ──

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

// ── Gallery View ──

function WhiteboardGallery() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: boards = [], isLoading } = useQuery<WhiteboardSummary[]>({
    queryKey: ['whiteboards'],
    queryFn: () => apiFetchJson('/api/whiteboards'),
    retry: 1,
    staleTime: 1000 * 60,
  });

  const createMut = useMutation({
    mutationFn: () =>
      apiFetchJson<WhiteboardDetail>('/api/whiteboards', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'Untitled' }),
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['whiteboards'] });
      router.push(`/whiteboard?id=${data.id}`);
    },
  });

  const createFromTemplateMut = useMutation({
    mutationFn: (tmpl: { title: string; scene_data: any }) =>
      apiFetchJson<WhiteboardDetail>('/api/whiteboards', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tmpl),
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['whiteboards'] });
      router.push(`/whiteboard?id=${data.id}`);
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/api/whiteboards/${id}`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['whiteboards'] }),
  });

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (confirm('Delete this diagram?')) {
      deleteMut.mutate(id);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-5 h-5 text-muted-foreground animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-[1440px] mx-auto px-4 sm:px-5 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-[15px] font-semibold text-foreground">Whiteboard</h1>
          <p className="text-[11px] text-muted-foreground/50 mt-0.5">
            {boards.length} diagram{boards.length !== 1 ? 's' : ''}
          </p>
        </div>
        <button
          onClick={() => createMut.mutate()}
          disabled={createMut.isPending}
          className="h-8 px-3 bg-foreground text-background rounded-[var(--radius)] text-[11px] font-semibold inline-flex items-center gap-1.5 hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {createMut.isPending ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Plus className="w-3.5 h-3.5" />
          )}
          New Diagram
        </button>
      </div>

      {/* Empty state */}
      {boards.length === 0 && (
        <div className="flex flex-col items-center justify-center h-64 text-center">
          <PenTool className="w-8 h-8 text-muted-foreground/20 mb-3" />
          <p className="text-[12px] text-muted-foreground/50">No diagrams yet</p>
          <p className="text-[11px] text-muted-foreground/30 mt-1 mb-4">
            Create a blank canvas or start from a pre-built template
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => createFromTemplateMut.mutate({ title: 'Investment Thesis Framework', scene_data: WELCOME_TEMPLATE })}
              disabled={createFromTemplateMut.isPending}
              className="h-8 px-3.5 rounded-[var(--radius)] border border-border/50 text-[11px] font-medium text-muted-foreground hover:text-foreground hover:border-border transition-all inline-flex items-center gap-1.5 disabled:opacity-50"
            >
              {createFromTemplateMut.isPending ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <LayoutTemplate className="w-3.5 h-3.5" />
              )}
              Thesis Template
            </button>
            <button
              onClick={() => createFromTemplateMut.mutate({ title: 'Macro Research Pipeline', scene_data: MACRO_RESEARCH_TEMPLATE })}
              disabled={createFromTemplateMut.isPending}
              className="h-8 px-3.5 rounded-[var(--radius)] border border-border/50 text-[11px] font-medium text-muted-foreground hover:text-foreground hover:border-border transition-all inline-flex items-center gap-1.5 disabled:opacity-50"
            >
              {createFromTemplateMut.isPending ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <LayoutTemplate className="w-3.5 h-3.5" />
              )}
              Macro Research
            </button>
          </div>
        </div>
      )}

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {boards.map((board) => (
          <div
            key={board.id}
            role="button"
            tabIndex={0}
            onClick={() => router.push(`/whiteboard?id=${board.id}`)}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); router.push(`/whiteboard?id=${board.id}`); } }}
            className="group rounded-[var(--radius)] border border-border/30 bg-card hover:border-border/60 transition-all duration-150 cursor-pointer overflow-hidden focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/25"
          >
            {/* Thumbnail */}
            <div className="aspect-[16/10] bg-background/50 flex items-center justify-center overflow-hidden">
              {board.thumbnail ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={`data:image/png;base64,${board.thumbnail}`}
                  alt={board.title}
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="flex flex-col items-center justify-center gap-2 px-4">
                  <PenTool className="w-5 h-5 text-muted-foreground/20" />
                  <span className="text-[10px] font-mono text-muted-foreground/25 text-center leading-tight truncate max-w-full">
                    {board.title}
                  </span>
                </div>
              )}
            </div>

            {/* Info */}
            <div className="px-3 py-2.5 border-t border-border/20 flex items-center justify-between">
              <div className="min-w-0 flex-1">
                <p className="text-[12px] font-medium text-foreground truncate">
                  {board.title}
                </p>
                <p className="text-[10px] text-muted-foreground/40 flex items-center gap-1 mt-0.5">
                  <Clock className="w-2.5 h-2.5" />
                  {timeAgo(board.updated_at)}
                </p>
              </div>
              <button
                onClick={(e) => handleDelete(e, board.id)}
                className="opacity-0 group-hover:opacity-100 p-1.5 rounded-[var(--radius)] text-muted-foreground/40 hover:text-destructive hover:bg-destructive/10 transition-all"
                title="Delete"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Editor View ──

function WhiteboardEditorView({ whiteboardId }: { whiteboardId: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState('');
  const [saveStatus, setSaveStatus] = useState<'saved' | 'saving' | 'unsaved'>('saved');
  const saveTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const excalidrawAPIRef = useRef<any>(null);
  const latestSceneRef = useRef<{ elements: any; appState: any; files: any } | null>(null);

  const { data: wb, isLoading, error } = useQuery<WhiteboardDetail>({
    queryKey: ['whiteboard', whiteboardId],
    queryFn: () => apiFetchJson(`/api/whiteboards/${whiteboardId}`),
  });

  const updateMut = useMutation({
    mutationFn: (payload: { title?: string; scene_data?: any; thumbnail?: string }) =>
      apiFetchJson(`/api/whiteboards/${whiteboardId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      setSaveStatus('saved');
      queryClient.invalidateQueries({ queryKey: ['whiteboards'] });
    },
    onError: () => setSaveStatus('unsaved'),
  });

  useEffect(() => {
    if (wb) setTitle(wb.title);
  }, [wb]);

  // Generate thumbnail and save
  const flushSave = useCallback(async () => {
    const scene = latestSceneRef.current;
    if (!scene) return;

    setSaveStatus('saving');

    let thumbnailBase64: string | undefined;
    try {
      const { exportToBlob } = await import('@excalidraw/excalidraw');
      const visibleElements = scene.elements.filter(
        (el: any) => !el.isDeleted,
      );
      if (visibleElements.length > 0) {
        const blob = await exportToBlob({
          elements: visibleElements,
          appState: {
            ...scene.appState,
            exportWithDarkMode: false,
            exportBackground: true,
          },
          files: scene.files || {},
          maxWidthOrHeight: 400,
          mimeType: 'image/png',
        });
        if (blob && blob.size > 0) {
          // Use FileReader for reliable base64 conversion (btoa+reduce is fragile)
          thumbnailBase64 = await new Promise<string>((resolve, reject) => {
            const reader = new FileReader();
            reader.onloadend = () => {
              const dataUrl = reader.result as string;
              // Strip "data:image/png;base64," prefix
              const b64 = dataUrl.split(',')[1];
              if (b64) resolve(b64);
              else reject(new Error('Empty base64'));
            };
            reader.onerror = reject;
            reader.readAsDataURL(blob);
          });
        }
      }
    } catch (e) {
      console.warn('Thumbnail generation failed:', e);
    }

    updateMut.mutate({
      scene_data: {
        elements: scene.elements,
        appState: {
          viewBackgroundColor: scene.appState?.viewBackgroundColor,
          currentItemFontFamily: scene.appState?.currentItemFontFamily,
          gridSize: scene.appState?.gridSize,
        },
        files: scene.files || {},
      },
      ...(thumbnailBase64 ? { thumbnail: thumbnailBase64 } : {}),
    });
  }, [updateMut]);

  const handleChange = useCallback(
    (elements: readonly any[], appState: any, files: any) => {
      latestSceneRef.current = { elements, appState, files };
      setSaveStatus('unsaved');

      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
      saveTimerRef.current = setTimeout(() => {
        flushSave();
      }, 2000);
    },
    [flushSave],
  );

  // Flush on unmount
  useEffect(() => {
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    };
  }, []);

  const handleTitleBlur = () => {
    if (wb && title !== wb.title) {
      updateMut.mutate({ title });
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-5 h-5 text-muted-foreground animate-spin" />
      </div>
    );
  }

  if (error || !wb) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3">
        <p className="text-[12px] text-muted-foreground/50">Diagram not found</p>
        <button
          onClick={() => router.push('/whiteboard')}
          className="text-[11px] text-primary hover:underline"
        >
          Back to gallery
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header bar */}
      <div className="h-10 shrink-0 border-b border-border/20 bg-background/80 backdrop-blur-sm flex items-center gap-3 px-3">
        <button
          onClick={() => router.push('/whiteboard')}
          className="btn-icon shrink-0"
          title="Back to gallery"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
        </button>

        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={handleTitleBlur}
          onKeyDown={(e) => {
            if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
          }}
          className="flex-1 min-w-0 text-[12px] font-medium text-foreground bg-transparent border-none outline-none placeholder:text-muted-foreground/30"
          placeholder="Untitled"
        />

        <span
          className={`text-[9px] font-mono uppercase tracking-wider shrink-0 ${
            saveStatus === 'saved'
              ? 'text-muted-foreground/30'
              : saveStatus === 'saving'
                ? 'text-primary/60'
                : 'text-warning/60'
          }`}
        >
          {saveStatus === 'saved' ? 'Saved' : saveStatus === 'saving' ? 'Saving...' : 'Unsaved'}
        </span>
      </div>

      {/* Excalidraw canvas */}
      <div className="flex-1 min-h-0">
        <ExcalidrawEditor
          initialData={{
            elements: wb.scene_data?.elements || [],
            appState: wb.scene_data?.appState || {},
            files: wb.scene_data?.files || {},
          }}
          onChange={handleChange}
          excalidrawAPI={(api: any) => {
            excalidrawAPIRef.current = api;
          }}
        />
      </div>
    </div>
  );
}

// ── Page Router ──

function WhiteboardContent() {
  const searchParams = useSearchParams();
  const whiteboardId = searchParams.get('id');

  if (whiteboardId) {
    // Editor mode: full viewport, no AppShell constraints
    return (
      <div className="fixed inset-0 z-[60] bg-background flex flex-col">
        <WhiteboardEditorView whiteboardId={whiteboardId} />
      </div>
    );
  }

  // Gallery mode: inside AppShell with normal layout
  return (
    <AppShell hideFooter>
      <div className="h-[calc(100vh-48px)] min-h-0 overflow-auto">
        <WhiteboardGallery />
      </div>
    </AppShell>
  );
}

export default function WhiteboardPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-screen bg-background">
          <Loader2 className="w-5 h-5 text-muted-foreground animate-spin" />
        </div>
      }
    >
      <WhiteboardContent />
    </Suspense>
  );
}
