'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { ExternalLink, Youtube, AlertTriangle, Save, Trash2, PlusCircle, FileText, RefreshCw, Play, Square } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useAuth } from '@/context/AuthContext';

interface YouTubeVideoIntel {
  video_id: string;
  channel: string;
  title: string;
  published_at: string;
  updated_at?: string | null;
  created_at?: string | null;
  is_new: boolean;
  url: string;
  summary?: string | null;
}

interface YouTubeIntelResponse {
  generated_at: string;
  videos: YouTubeVideoIntel[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  note?: string;
}

export default function YouTubeIntelFeed() {
  const { user } = useAuth();
  const isAdmin = !!user && (user.role === 'owner' || user.role === 'admin' || user.is_admin);
  const [manualUrl, setManualUrl] = useState('');
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<'unsummarized' | 'published_desc'>('unsummarized');
  const [search, setSearch] = useState('');
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [expandedByVideo, setExpandedByVideo] = useState<Record<string, boolean>>({});
  const [adminError, setAdminError] = useState<string | null>(null);
  const [speakingVideoId, setSpeakingVideoId] = useState<string | null>(null);
  const [speakingSentenceIndex, setSpeakingSentenceIndex] = useState<number | null>(null);
  const [ttsSupported, setTtsSupported] = useState(false);
  const [ttsError, setTtsError] = useState<string | null>(null);
  const ttsSessionRef = useRef<{ videoId: string; cancelled: boolean } | null>(null);
  const pageSize = 4;
  const queryClient = useQueryClient();

  useEffect(() => {
    if (typeof window === 'undefined') return;
    setTtsSupported('speechSynthesis' in window && 'SpeechSynthesisUtterance' in window);
    return () => {
      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
      ttsSessionRef.current = null;
    };
  }, []);

  const toSpeechText = (input?: string | null) => {
    const s = (input || '').trim();
    if (!s) return '';
    return s
      .replace(/`([^`]+)`/g, '$1')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1')
      .replace(/[*_>#~-]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  };

  const splitSentences = (input?: string | null): string[] => {
    const plain = toSpeechText(input);
    if (!plain) return [];
    const out = plain
      .split(/(?<=[.!?])\s+/)
      .map((x) => x.trim())
      .filter(Boolean);
    return out.length > 0 ? out : [plain];
  };

  const normalizeDisplayText = (input?: string | null): string => {
    const s = (input || '').trim();
    if (!s) return '';
    return s
      .replace(/\r/g, '')
      .replace(/```[\s\S]*?```/g, '')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1')
      .replace(/^#{1,6}\s+/gm, '')
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/\*([^*]+)\*/g, '$1')
      .trim();
  };

  const summaryBlocks = (input?: string | null): string[] => {
    const n = normalizeDisplayText(input);
    if (!n) return [];
    return n
      .split(/\n{2,}/)
      .map((b) => b.trim())
      .filter(Boolean);
  };

  const pickSmoothVoice = (): SpeechSynthesisVoice | null => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return null;
    const voices = window.speechSynthesis.getVoices();
    if (!voices || voices.length === 0) return null;
    const preferred = voices.find((v) => /en-us/i.test(v.lang) && /natural|neural|samantha|google/i.test(v.name));
    if (preferred) return preferred;
    const en = voices.find((v) => /^en/i.test(v.lang));
    return en || voices[0] || null;
  };

  const handleSpeak = (videoId: string, summary?: string | null) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;
    const speech = window.speechSynthesis;
    const sentences = splitSentences(summary);
    if (!sentences.length) return;
    setTtsError(null);
    speech.cancel();
    speech.resume();
    const session = { videoId, cancelled: false };
    ttsSessionRef.current = session;
    setSpeakingVideoId(videoId);
    setSpeakingSentenceIndex(0);

    const speakSentence = (idx: number) => {
      if (!ttsSessionRef.current || ttsSessionRef.current !== session || session.cancelled) return;
      if (idx >= sentences.length) {
        setSpeakingVideoId((curr) => (curr === videoId ? null : curr));
        setSpeakingSentenceIndex(null);
        return;
      }

      setSpeakingSentenceIndex(idx);
      const utterance = new SpeechSynthesisUtterance(sentences[idx]);
      const voice = pickSmoothVoice();
      if (voice) utterance.voice = voice;
      utterance.rate = 1.15;
      utterance.pitch = 0.96;
      utterance.volume = 1;

      let started = false;
      utterance.onstart = () => {
        started = true;
      };
      utterance.onend = () => {
        if (!ttsSessionRef.current || ttsSessionRef.current !== session || session.cancelled) return;
        setTimeout(() => speakSentence(idx + 1), 40);
      };
      utterance.onerror = () => {
        if (!ttsSessionRef.current || ttsSessionRef.current !== session || session.cancelled) return;
        setTtsError('Text-to-speech failed to play in this browser.');
        setSpeakingVideoId((curr) => (curr === videoId ? null : curr));
        setSpeakingSentenceIndex(null);
      };

      speech.speak(utterance);

      // Guard: some browser/voice combos get stuck without firing start/end.
      setTimeout(() => {
        if (!started && !session.cancelled && ttsSessionRef.current === session) {
          speech.cancel();
          setTtsError('Audio playback did not start. Try again or use a different browser voice.');
          setSpeakingVideoId((curr) => (curr === videoId ? null : curr));
          setSpeakingSentenceIndex(null);
        }
      }, 2500);
    };

    speakSentence(0);
  };

  const handleStopSpeak = (videoId: string) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;
    if (ttsSessionRef.current && ttsSessionRef.current.videoId === videoId) {
      ttsSessionRef.current.cancelled = true;
      ttsSessionRef.current = null;
    }
    window.speechSynthesis.cancel();
    setSpeakingVideoId((curr) => (curr === videoId ? null : curr));
    setSpeakingSentenceIndex(null);
  };

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery<YouTubeIntelResponse>({
    queryKey: ['youtube-intel', { hours: 24, page, pageSize, sort, search }],
    queryFn: () =>
      apiFetchJson<YouTubeIntelResponse>(
        `/api/news/youtube?hours=24&limit=50&page=${page}&page_size=${pageSize}&sort=${encodeURIComponent(sort)}&q=${encodeURIComponent(search)}`
      ),
    staleTime: 1000 * 60 * 5,
    refetchInterval: 1000 * 60 * 10,
    refetchIntervalInBackground: false,
  });

  const addVideoMutation = useMutation({
    mutationFn: (url: string) =>
      apiFetchJson<YouTubeVideoIntel>('/api/news/youtube/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      }),
    onSuccess: () => {
      setAdminError(null);
      setManualUrl('');
      setPage(1);
      queryClient.invalidateQueries({ queryKey: ['youtube-intel'] });
    },
    onError: (e: unknown) => {
      setAdminError((e as Error)?.message || 'Failed to add video.');
    },
  });

  const updateSummaryMutation = useMutation({
    mutationFn: ({ videoId, summary }: { videoId: string; summary: string }) =>
      apiFetchJson<YouTubeVideoIntel>(`/api/news/youtube/${encodeURIComponent(videoId)}/summary`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ summary }),
      }),
    onSuccess: () => {
      setAdminError(null);
      queryClient.invalidateQueries({ queryKey: ['youtube-intel'] });
    },
    onError: (e: unknown) => {
      setAdminError((e as Error)?.message || 'Failed to save summary.');
    },
  });

  const deleteVideoMutation = useMutation({
    mutationFn: (videoId: string) =>
      apiFetchJson<{ ok: boolean; video_id: string }>(`/api/news/youtube/${encodeURIComponent(videoId)}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      setAdminError(null);
      queryClient.invalidateQueries({ queryKey: ['youtube-intel'] });
    },
    onError: (e: unknown) => {
      setAdminError((e as Error)?.message || 'Failed to delete video.');
    },
  });

  if (isLoading) {
    return (
      <div className="h-32 border border-border/60 rounded-xl bg-background animate-pulse flex items-center justify-center text-muted-foreground text-sm">
        Loading YouTube intelligence…
      </div>
    );
  }

  if (isError) {
    return (
      <div className="border border-rose-500/20 rounded-xl bg-rose-500/[0.04] p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-2 text-rose-400 text-sm">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {(error as Error)?.message || 'Failed to load YouTube intelligence'}
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="inline-flex items-center gap-1.5 h-7 px-3 rounded-md border border-border/60 text-[11px] text-muted-foreground hover:text-foreground hover:bg-foreground/[0.06] disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} />
          Retry
        </button>
      </div>
    );
  }

  const videos = data?.videos || [];
  if (videos.length === 0) {
    return (
      <div className="border border-border/60 rounded-xl bg-background p-6 text-sm text-muted-foreground">
        {data?.note || 'No videos available.'}
      </div>
    );
  }

  return (
    <section className="border border-border/60 rounded-xl overflow-hidden bg-background">
      <div className="h-11 flex items-center justify-between px-4 border-b border-border/60">
        <div className="flex items-center gap-2">
          <Youtube className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />
          <span className="text-sm font-semibold text-foreground">YouTube Intelligence</span>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-muted-foreground/60">
          <span className="px-2 h-5 rounded border border-border/60 inline-flex items-center font-mono">
            {data?.total || 0} videos
          </span>
        </div>
      </div>

      {isAdmin && (
        <div className="px-4 py-3 border-b border-border/60">
          <div className="flex flex-col md:flex-row gap-2">
            <input
              value={manualUrl}
              onChange={(e) => setManualUrl(e.target.value)}
              placeholder="Paste YouTube URL or video ID"
              className="flex-1 h-8 px-3 rounded-md border border-border/50 bg-transparent text-[12px] focus:outline-none focus:border-border transition-colors"
            />
            <button
              onClick={() => {
                if (!manualUrl.trim()) return;
                setAdminError(null);
                addVideoMutation.mutate(manualUrl.trim());
              }}
              disabled={addVideoMutation.isPending}
              className="h-8 px-3 bg-foreground text-background rounded-md text-[11px] font-medium hover:opacity-80 disabled:opacity-50 transition-opacity w-full md:w-auto inline-flex items-center justify-center gap-1.5"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              Add Video
            </button>
          </div>
          <div className="mt-1.5 text-[11px] text-muted-foreground/50">
            Minimum video length is 5 minutes.
          </div>
          {adminError && (
            <div className="mt-2 rounded-md border border-rose-500/30 bg-rose-500/[0.06] px-3 py-2 text-[12px] text-rose-400">
              {adminError}
            </div>
          )}
        </div>
      )}

      <div className="px-4 py-2.5 border-b border-border/60">
        <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-2">
          <select
            value={sort}
            onChange={(e) => {
              setSort(e.target.value as 'unsummarized' | 'published_desc');
              setPage(1);
            }}
            className="h-8 px-3 rounded-md border border-border/50 bg-transparent text-[12px] focus:outline-none transition-colors"
          >
            <option value="unsummarized">Sort: Unsummarized First</option>
            <option value="published_desc">Sort: Publish Date (Newest)</option>
          </select>
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search by title, channel, or summary"
            className="h-8 px-3 rounded-md border border-border/50 bg-transparent text-[12px] focus:outline-none transition-colors"
          />
        </div>
        {ttsError && (
          <div className="mt-2 rounded-md border border-amber-500/30 bg-amber-500/[0.06] px-3 py-2 text-[12px] text-amber-400">
            {ttsError}
          </div>
        )}
      </div>

      <div className="max-h-[780px] overflow-y-auto custom-scrollbar divide-y divide-border/40">
        {videos.map((v) => {
          const draft = drafts[v.video_id] ?? (v.summary || '');
          const sentences = splitSentences(draft);
          const isSpeakingThisVideo = speakingVideoId === v.video_id;
          const blocks = summaryBlocks(draft);
          const wordCount = normalizeDisplayText(draft).split(/\s+/).filter(Boolean).length;
          const estimatedMin = Math.max(1, Math.round(wordCount / 180));
          const isExpanded = !!expandedByVideo[v.video_id];
          const collapseAt = 14;
          return (
            <article key={v.video_id} className="px-4 py-4 hover:bg-foreground/[0.02] transition-colors">
              <div className="grid grid-cols-1 lg:grid-cols-[180px_1fr] xl:grid-cols-[200px_1fr] gap-4 items-start">
                <a
                  href={v.url}
                  target="_blank"
                  rel="noreferrer"
                  className="group relative rounded-xl overflow-hidden border border-border/60 bg-background w-full max-w-full sm:max-w-[200px]"
                >
                  <img
                    src={`https://i.ytimg.com/vi/${v.video_id}/hqdefault.jpg`}
                    alt={v.title}
                    className="w-full h-[102px] md:h-[112px] object-cover opacity-85 group-hover:opacity-100 transition-opacity"
                    loading="lazy"
                  />
                  <div className="absolute bottom-2 left-2 text-[10px] font-mono px-1.5 py-0.5 rounded-md bg-background/90 text-muted-foreground border border-border/60">
                    Watch
                  </div>
                </a>

                <div className="min-w-0">
                  <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 sm:gap-3 mb-2">
                    <div className="min-w-0">
                      <a
                        href={v.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-sm font-semibold text-foreground hover:text-foreground/70 transition-colors inline-flex items-center gap-1"
                      >
                        <span className="break-words">{v.title}</span>
                        <ExternalLink className="w-3 h-3 shrink-0 text-muted-foreground/50" />
                      </a>
                      <div className="text-[11px] text-muted-foreground/60 font-mono mt-1 flex flex-wrap items-center gap-1.5">
                        <span>{v.channel}</span>
                        <span className="text-border/60">·</span>
                        <span>{new Date(v.published_at).toLocaleDateString()}</span>
                        {v.is_new && (
                          <span className="px-1.5 py-0.5 rounded border border-emerald-500/30 bg-emerald-500/[0.08] text-emerald-400 text-[10px]">
                            New
                          </span>
                        )}
                      </div>
                    </div>
                    {isAdmin && (
                      <button
                        onClick={() => {
                          if (!confirm(`Delete video "${v.title}"?`)) return;
                          deleteVideoMutation.mutate(v.video_id);
                        }}
                        disabled={deleteVideoMutation.isPending}
                        className="inline-flex items-center gap-1.5 h-7 px-2.5 rounded-md border border-rose-500/30 bg-rose-500/[0.06] text-[11px] text-rose-400 hover:bg-rose-500/[0.12] disabled:opacity-50 shrink-0 transition-colors"
                        title="Delete video"
                      >
                        <Trash2 className="w-3 h-3" />
                        Delete
                      </button>
                    )}
                  </div>

                  <div className="rounded-xl border border-border/60 p-3">
                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                      <div className="text-[10px] font-medium text-muted-foreground/50 uppercase tracking-wider inline-flex items-center gap-1.5">
                        <FileText className="w-3 h-3" />
                        Summary
                      </div>
                      {ttsSupported && (
                        isSpeakingThisVideo ? (
                          <button
                            onClick={() => handleStopSpeak(v.video_id)}
                            className="inline-flex items-center gap-1.5 h-6 px-2.5 rounded-md border border-amber-500/30 bg-amber-500/[0.08] text-[10px] text-amber-400 hover:bg-amber-500/[0.14] transition-colors"
                            title="Stop audio summary"
                          >
                            <Square className="w-3 h-3" />
                            Stop
                          </button>
                        ) : (
                          <button
                            onClick={() => handleSpeak(v.video_id, draft)}
                            disabled={!sentences.length}
                            className="inline-flex items-center gap-1.5 h-6 px-2.5 rounded-md border border-emerald-500/30 bg-emerald-500/[0.08] text-[10px] text-emerald-400 hover:bg-emerald-500/[0.14] disabled:opacity-40 transition-colors"
                            title="Play audio summary"
                          >
                            <Play className="w-3 h-3" />
                            Play
                          </button>
                        )
                      )}
                    </div>
                    {isAdmin ? (
                      <div className="space-y-2">
                        <textarea
                          value={draft}
                          onChange={(e) => setDrafts((prev) => ({ ...prev, [v.video_id]: e.target.value }))}
                          placeholder="Add or edit summary manually..."
                          className="w-full min-h-[116px] px-3 py-2 rounded-md border border-border/50 bg-transparent text-sm focus:outline-none focus:border-border transition-colors"
                        />
                        <button
                          onClick={() =>
                            updateSummaryMutation.mutate({
                              videoId: v.video_id,
                              summary: draft,
                            })
                          }
                          disabled={updateSummaryMutation.isPending}
                          className="h-7 px-3 bg-foreground text-background rounded-md text-[11px] font-medium hover:opacity-80 disabled:opacity-50 transition-opacity inline-flex items-center gap-1.5"
                        >
                          <Save className="w-3 h-3" />
                          Save
                        </button>
                      </div>
                    ) : (
                      <div>
                        {blocks.length ? (
                          <div className="space-y-3">
                            <div className="flex items-center justify-between gap-2 pb-2 border-b border-border/40">
                              <div className="text-[10px] text-muted-foreground/50">
                                {wordCount} words · ~{estimatedMin} min read
                              </div>
                              {sentences.length > collapseAt && (
                                <button
                                  onClick={() =>
                                    setExpandedByVideo((prev) => ({ ...prev, [v.video_id]: !isExpanded }))
                                  }
                                  className="text-[10px] px-2 py-0.5 rounded-md border border-border/60 text-muted-foreground hover:text-foreground transition-colors"
                                >
                                  {isExpanded ? 'Show Less' : 'Show More'}
                                </button>
                              )}
                            </div>

                            <div className="space-y-2.5">
                              {(() => {
                                const rows: React.ReactNode[] = [];
                                let globalIdx = 0;
                                for (let b = 0; b < blocks.length; b += 1) {
                                  const blockSentences = splitSentences(blocks[b]);
                                  if (!blockSentences.length) continue;
                                  const rendered: React.ReactNode[] = [];

                                  for (let i = 0; i < blockSentences.length; i += 1) {
                                    const hidden = !isExpanded && globalIdx >= collapseAt;
                                    const active = isSpeakingThisVideo && speakingSentenceIndex === globalIdx;
                                    if (!hidden) {
                                      rendered.push(
                                        <span
                                          key={`${v.video_id}-s-${globalIdx}`}
                                          className={`transition-colors rounded-sm ${
                                            active
                                              ? 'bg-emerald-500/[0.12] text-emerald-400 px-1 py-0.5'
                                              : 'text-foreground/85'
                                          }`}
                                        >
                                          {blockSentences[i]}{' '}
                                        </span>
                                      );
                                    }
                                    globalIdx += 1;
                                  }

                                  if (rendered.length) {
                                    rows.push(
                                      <p
                                        key={`${v.video_id}-b-${b}`}
                                        className="text-[13px] leading-6 text-foreground/85"
                                      >
                                        {rendered}
                                      </p>
                                    );
                                  }
                                }
                                if (!rows.length) {
                                  return (
                                    <span className="text-muted-foreground/50 text-[13px]">No summary yet.</span>
                                  );
                                }
                                return rows;
                              })()}
                            </div>
                          </div>
                        ) : (
                          <span className="text-muted-foreground/50 text-[13px]">No summary yet.</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </article>
          );
        })}
      </div>

      <div className="px-4 py-2.5 border-t border-border/60 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div className="text-[11px] font-mono text-muted-foreground/50">
          {data?.total
            ? `${(data.page - 1) * data.page_size + 1}–${Math.min(data.page * data.page_size, data.total)} of ${data.total}`
            : '0'}
        </div>
        <div className="flex items-center gap-1.5 self-end sm:self-auto">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={!data || data.page <= 1}
            className="h-7 px-2.5 rounded-md border border-border/60 text-[11px] text-muted-foreground hover:text-foreground hover:bg-foreground/[0.06] disabled:opacity-40 transition-colors"
          >
            Prev
          </button>
          <span className="text-[11px] text-muted-foreground/50 px-1">
            {data?.page || 1} / {data?.total_pages || 1}
          </span>
          <button
            onClick={() => setPage((p) => (!data ? p : Math.min(data.total_pages || 1, p + 1)))}
            disabled={!data || data.page >= (data.total_pages || 1)}
            className="h-7 px-2.5 rounded-md border border-border/60 text-[11px] text-muted-foreground hover:text-foreground hover:bg-foreground/[0.06] disabled:opacity-40 transition-colors"
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}
