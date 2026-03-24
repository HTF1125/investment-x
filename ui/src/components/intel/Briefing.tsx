'use client';

import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiFetch, apiFetchJson } from '@/lib/api';
import {
  BookOpen, WifiOff, ChevronLeft, ChevronRight, Calendar, Loader2,
  Youtube, FileText, Rss, MessageSquare, Building2, BarChart3, Globe,
  Volume2, VolumeX, Clock, ChevronDown,
} from 'lucide-react';

// ── Types ────────────────────────────────────────────────────────────────────

interface ReportDate {
  date: string;
  has_briefing: boolean;
}

interface VideoSource { id: string; title: string; channel: string; url: string; }
interface DriveSource { title: string; url: string; file_id: string; }

interface SourceCounts {
  youtube?: number; drive?: number; central_banks?: number;
  news?: number; telegram?: number; macro_data?: number; reports?: number;
}

interface ReportData {
  date: string;
  briefing: string | null;
  sources: {
    selected_videos?: VideoSource[];
    drive_files?: DriveSource[];
    counts?: SourceCounts;
    translations?: Record<string, string>;
  };
  updated_at?: string | null;
}

export interface MdSection { title: string; body: string; }

// ── Parsers ──────────────────────────────────────────────────────────────────

export function parseBriefingSections(md: string): MdSection[] {
  const sections: MdSection[] = [];
  const cleaned = md.split('\n')
    .filter(l => !l.startsWith('# Macro Intelligence Briefing') && !l.startsWith('Continuing conversation') && !l.startsWith('Resumed conversation'))
    .join('\n').trim();
  const parts = cleaned.split(/\*\*\d+\)\s*/);
  for (const part of parts) {
    if (!part.trim()) continue;
    const endOfTitle = part.indexOf('**');
    if (endOfTitle === -1) continue;
    const title = part.substring(0, endOfTitle).trim();
    const body = part.substring(endOfTitle + 2).trim().replace(/\s*\[\d+[-,\s\d]*\]/g, '');
    if (title && body) sections.push({ title, body });
  }
  return sections;
}

export function parseTranslationSections(md: string): MdSection[] {
  return md.split(/\n(?=##\s)/)
    .map(block => {
      const lines = block.trim().split('\n');
      const raw = lines[0]?.replace(/^##\s*/, '').trim() ?? '';
      // Strip leading "0) " or "1) " number prefix (baked into translation headings)
      const title = raw.replace(/^\d+\)\s*/, '');
      return { title, body: lines.slice(1).join('\n').trim() };
    })
    .filter(s => s.title && s.body);
}

function formatDate(dateStr: string): string {
  try {
    const [y, m, d] = dateStr.split('-').map(Number);
    return new Date(y, m - 1, d).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
  } catch { return dateStr; }
}

function compactDate(dateStr: string): string {
  try {
    const [y, m, d] = dateStr.split('-').map(Number);
    return new Date(y, m - 1, d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch { return dateStr; }
}

// ── Inline markdown renderer ─────────────────────────────────────────────────

export function renderInline(text: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  const re = /\*\*([^*]+)\*\*/g;
  let last = 0, match: RegExpExecArray | null;
  while ((match = re.exec(text)) !== null) {
    if (match.index > last) nodes.push(text.slice(last, match.index));
    nodes.push(<strong key={match.index} className="text-foreground font-semibold">{match[1]}</strong>);
    last = re.lastIndex;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

// ── Section renderer ─────────────────────────────────────────────────────────

export function SectionBlock({ section, index, compact, isActive }: { section: MdSection; index: number; compact?: boolean; isActive?: boolean }) {
  const paragraphs = section.body.split(/\n{2,}/).filter(p => p.trim());

  return (
    <article className={`relative pl-4 transition-all duration-300 rounded-r-[var(--radius)] ${compact ? 'pb-4' : 'pb-6'} ${isActive ? 'bg-primary/[0.04]' : ''}`}>
      <div className={`absolute left-0 top-0 bottom-0 transition-all duration-300 rounded-l ${isActive ? 'w-[3px] bg-primary' : 'w-px bg-border/30'}`} />
      <div className="flex items-baseline gap-2.5 mb-2">
        <span className="text-[10px] font-mono text-muted-foreground/35 tabular-nums shrink-0 select-none">
          {String(index + 1).padStart(2, '0')}
        </span>
        <h3 className={`font-semibold uppercase tracking-[0.08em] text-muted-foreground/60 ${compact ? 'text-[10px]' : 'text-[11px]'}`}>
          {section.title}
        </h3>
      </div>
      <div className="space-y-2">
        {paragraphs.map((p, i) => {
          const trimmed = p.trim();
          // Table detection
          if (trimmed.includes('|') && /\|[\s-:]+\|/.test(trimmed)) {
            const rows = trimmed.split('\n').filter(r => r.includes('|'));
            const header = rows[0]?.split('|').map(c => c.trim()).filter(Boolean) ?? [];
            const dataRows = rows.slice(2).map(r => r.split('|').map(c => c.trim()).filter(Boolean));
            return (
              <div key={i} className="overflow-x-auto my-1">
                <table className="w-full text-[10px] font-mono">
                  <thead><tr className="border-b border-border/30">
                    {header.map((h, j) => <th key={j} className="px-2 py-1 text-left text-muted-foreground/40 font-medium">{h}</th>)}
                  </tr></thead>
                  <tbody>{dataRows.map((row, ri) => (
                    <tr key={ri} className="border-b border-border/10">
                      {row.map((cell, ci) => <td key={ci} className="px-2 py-0.5 text-foreground/70">{renderInline(cell)}</td>)}
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            );
          }
          // List detection
          if (trimmed.match(/^[-*]\s/m)) {
            const items = trimmed.split('\n').filter(l => l.trim().startsWith('-') || l.trim().startsWith('*'));
            return (
              <ul key={i} className={`space-y-0.5 ${compact ? 'text-[10px]' : 'text-[11px]'} text-foreground/70 leading-relaxed`}>
                {items.map((item, j) => (
                  <li key={j} className="flex gap-1.5">
                    <span className="text-muted-foreground/30 mt-[3px] shrink-0">-</span>
                    <span>{renderInline(item.replace(/^[-*]\s+/, ''))}</span>
                  </li>
                ))}
              </ul>
            );
          }
          // Paragraph
          return (
            <p key={i} className={`${compact ? 'text-[10px]' : 'text-[11px]'} text-foreground/70 leading-relaxed`}>
              {renderInline(trimmed.replace(/\n/g, ' '))}
            </p>
          );
        })}
      </div>
    </article>
  );
}

// ── Source badges ─────────────────────────────────────────────────────────────

const SOURCE_BADGES = [
  { key: 'youtube', icon: Youtube, label: 'videos', color: 'text-rose-400/50' },
  { key: 'drive', icon: FileText, label: 'PDFs', color: 'text-primary/50' },
  { key: 'news', icon: Rss, label: 'feeds', color: 'text-amber-400/50' },
  { key: 'telegram', icon: MessageSquare, label: 'msgs', color: 'text-sky-400/50' },
  { key: 'central_banks', icon: Building2, label: 'CBs', color: 'text-emerald-400/50' },
  { key: 'macro_data', icon: BarChart3, label: 'data', color: 'text-violet-400/50' },
  { key: 'reports', icon: Globe, label: 'reports', color: 'text-primary/50' },
] as const;

export function SourceBadges({ counts, compact }: { counts: Record<string, number | undefined>; compact?: boolean }) {
  const active = SOURCE_BADGES.filter(b => (counts as any)[b.key] > 0);
  if (!active.length) return null;
  return (
    <div className={`flex flex-wrap gap-2 ${compact ? 'pt-3' : 'pt-5 mt-5 border-t border-border/20'}`}>
      {active.map(b => {
        const Icon = b.icon;
        const n = (counts as any)[b.key];
        return (
          <span key={b.key} className="inline-flex items-center gap-1 text-[9px] font-mono text-muted-foreground/40">
            <Icon className={`w-2.5 h-2.5 ${b.color}`} />
            {n} {b.label}
          </span>
        );
      })}
    </div>
  );
}

// ── Language selector ────────────────────────────────────────────────────────

// ── TTS hook (backend neural voices via edge-tts) ────────────────────────────

export function cleanForSpeech(text: string): string {
  return text
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\|[^\n]+\|/g, '')
    .replace(/\|[-:\s|]+\|/g, '')
    .replace(/^#{1,4}\s+/gm, '')
    .replace(/^[-*]\s+/gm, '')
    .replace(/https?:\/\/\S+/g, '')
    .replace(/\[\d+[-,\s\d]*\]/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

async function fetchTTSAudio(text: string, lang: string, signal?: AbortSignal): Promise<string> {
  const res = await apiFetch('/api/tts/speak', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, lang }),
    signal,
    timeoutMs: 60_000,
  });
  if (!res.ok) throw new Error(`TTS failed (${res.status})`);
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

function sectionText(sections: MdSection[], idx: number): string {
  if (idx < 0 || idx >= sections.length) return '';
  return cleanForSpeech(`${sections[idx].title}. ${sections[idx].body}`);
}

export function useTTS(sections: MdSection[], lang: string) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [activeIdx, setActiveIdx] = useState<number | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const urlsRef = useRef<string[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const cancelledRef = useRef(false);
  const prefetchRef = useRef<{ idx: number; promise: Promise<string> } | null>(null);

  const cleanup = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    prefetchRef.current = null;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = '';
      audioRef.current = null;
    }
    urlsRef.current.forEach(u => URL.revokeObjectURL(u));
    urlsRef.current = [];
  }, []);

  // Cleanup on unmount
  useEffect(() => cleanup, [cleanup]);

  // Reset when sections/lang change
  useEffect(() => {
    cleanup();
    setIsPlaying(false);
    setIsLoading(false);
    setActiveIdx(null);
  }, [sections, lang, cleanup]);

  const playFrom = useCallback(async (idx: number) => {
    if (cancelledRef.current || idx >= sections.length) {
      setIsPlaying(false);
      setIsLoading(false);
      setActiveIdx(null);
      return;
    }

    const text = sectionText(sections, idx);
    if (!text) { playFrom(idx + 1); return; }

    setActiveIdx(idx);

    try {
      const controller = new AbortController();
      abortRef.current = controller;

      // Use prefetched audio if available, otherwise fetch now
      let url: string;
      if (prefetchRef.current?.idx === idx) {
        setIsLoading(false);
        url = await prefetchRef.current.promise;
        prefetchRef.current = null;
      } else {
        if (idx === 0) setIsLoading(true);
        url = await fetchTTSAudio(text, lang, controller.signal);
      }

      if (cancelledRef.current) { URL.revokeObjectURL(url); return; }
      urlsRef.current.push(url);
      setIsLoading(false);

      // Start prefetching next section while current plays
      const nextText = sectionText(sections, idx + 1);
      if (nextText && !cancelledRef.current) {
        prefetchRef.current = {
          idx: idx + 1,
          promise: fetchTTSAudio(nextText, lang, controller.signal),
        };
      }

      // Play current section
      const audio = new Audio(url);
      audioRef.current = audio;

      await new Promise<void>((resolve, reject) => {
        audio.onended = () => resolve();
        audio.onerror = () => reject(new Error('Audio playback error'));
        audio.play().catch(reject);
      });

      if (!cancelledRef.current) playFrom(idx + 1);
    } catch (err: any) {
      if (err?.name === 'AbortError' || cancelledRef.current) return;
      // Skip section on error, try next
      if (!cancelledRef.current) playFrom(idx + 1);
    }
  }, [sections, lang]);

  const toggle = useCallback(() => {
    if (isPlaying) {
      cancelledRef.current = true;
      cleanup();
      setIsPlaying(false);
      setIsLoading(false);
      setActiveIdx(null);
    } else {
      cancelledRef.current = false;
      setIsPlaying(true);
      playFrom(0);
    }
  }, [isPlaying, playFrom, cleanup]);

  return { isPlaying, isLoading, activeIdx, toggle };
}

// ── Language selector ────────────────────────────────────────────────────────

const LANG_LABELS: Record<string, string> = { en: 'EN', cn: 'CN', kr: 'KR', jp: 'JP' };

export function LangBar({ active, available, onChange, compact }: {
  active: string; available: string[]; onChange: (l: string) => void; compact?: boolean;
}) {
  if (available.length <= 1) return null;
  return (
    <div className={`flex gap-1.5 ${compact ? 'mb-3' : 'mb-5 pb-4 border-b border-border/20'}`}>
      {available.map(l => (
        <button
          key={l}
          onClick={() => onChange(l)}
          className={`px-2 py-0.5 rounded text-[10px] font-mono transition-all ${
            l === active
              ? 'bg-foreground text-background font-bold'
              : 'text-muted-foreground/40 hover:text-foreground hover:bg-foreground/[0.05]'
          }`}
        >
          {LANG_LABELS[l] ?? l.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

// ── Navigation header ────────────────────────────────────────────────────────

function DateNav({ date, hasPrev, hasNext, onPrev, onNext, compact, isPlaying, isLoading, onToggleTTS }: {
  date: string | null; hasPrev: boolean; hasNext: boolean;
  onPrev: () => void; onNext: () => void; compact?: boolean;
  isPlaying?: boolean; isLoading?: boolean; onToggleTTS?: () => void;
}) {
  return (
    <div className={`flex items-center ${compact ? 'gap-1 px-2 py-1 border-b border-border/15' : 'gap-1 px-4 py-1.5 border-b border-border/25'}`}>
      <button onClick={onPrev} disabled={!hasPrev} className="btn-icon"><ChevronLeft className="w-3 h-3" /></button>
      <div className="flex items-center gap-1.5 min-w-[100px] justify-center">
        <Calendar className="w-2.5 h-2.5 text-muted-foreground/40" />
        <span className="text-[10px] font-mono text-muted-foreground/60 tabular-nums">
          {date ? (compact ? compactDate(date) : formatDate(date)) : '---'}
        </span>
      </div>
      <button onClick={onNext} disabled={!hasNext} className="btn-icon"><ChevronRight className="w-3 h-3" /></button>
      {onToggleTTS && (
        <>
          <div className="flex-1" />
          <button
            onClick={onToggleTTS}
            disabled={isLoading}
            className={`btn-icon transition-colors ${isPlaying ? 'text-primary' : 'text-muted-foreground/40 hover:text-foreground'}`}
            title={isLoading ? 'Generating...' : isPlaying ? 'Stop reading' : 'Read aloud'}
          >
            {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : isPlaying ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
          </button>
        </>
      )}
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

export default function Briefing({
  embedded, hideHeader, externalDateIdx, onDateIdxChange, collapsed, onToggleCollapse,
}: {
  embedded?: boolean;
  hideHeader?: boolean;
  externalDateIdx?: number;
  onDateIdxChange?: (idx: number) => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}) {
  const { data: reportDates = [], isLoading: datesLoading, isError: datesError } = useQuery<ReportDate[]>({
    queryKey: ['research-reports'],
    queryFn: () => apiFetchJson<ReportDate[]>('/api/news/reports'),
    staleTime: 120_000,
  });

  const [internalDateIdx, setInternalDateIdx] = useState(0);
  const dateIdx = externalDateIdx ?? internalDateIdx;
  const setDateIdx = onDateIdxChange ?? setInternalDateIdx;
  const selectedDate = reportDates[dateIdx]?.date ?? null;

  const { data: report, isLoading: reportLoading, isError: reportError } = useQuery<ReportData>({
    queryKey: ['research-report', selectedDate],
    queryFn: () => apiFetchJson<ReportData>(`/api/news/reports/${selectedDate}`),
    enabled: !!selectedDate,
    staleTime: 300_000,
  });

  const hasPrev = dateIdx < reportDates.length - 1;
  const hasNext = dateIdx > 0;
  const goPrev = useCallback(() => setDateIdx(dateIdx + 1), [setDateIdx, dateIdx]);
  const goNext = useCallback(() => setDateIdx(dateIdx - 1), [setDateIdx, dateIdx]);

  const [lang, setLang] = useState('en');

  const briefingSections = useMemo(
    () => (report?.briefing ? parseBriefingSections(report.briefing) : []),
    [report?.briefing],
  );

  const translations = useMemo(() => report?.sources?.translations ?? {}, [report?.sources?.translations]);

  const availableLangs = useMemo(() => {
    const langs = ['en'];
    for (const l of ['cn', 'kr', 'jp']) { if (translations[l]) langs.push(l); }
    return langs;
  }, [translations]);

  const activeSections = useMemo(() => {
    if (lang === 'en') return briefingSections;
    const raw = translations[lang];
    return raw ? parseTranslationSections(raw) : [];
  }, [lang, briefingSections, translations]);

  const sourceCounts = report?.sources?.counts ?? {};
  const tts = useTTS(activeSections, lang);

  // ── Loading / Error / Empty ────────────────────────────────────────────

  if (datesLoading) {
    return <div className="h-32 flex items-center justify-center"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground/30" /></div>;
  }

  if (datesError) {
    return (
      <div className="m-6 border border-border/30 rounded-[var(--radius)] bg-card p-8 flex flex-col items-center gap-3 text-center">
        <WifiOff className="w-5 h-5 text-muted-foreground/30" />
        <p className="text-[12px] text-muted-foreground/60">Unable to load research reports</p>
      </div>
    );
  }

  if (!reportDates.length) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <BookOpen className="w-6 h-6 mx-auto mb-2 text-muted-foreground/20" />
          <p className="text-[12px] text-muted-foreground/50">No research reports yet</p>
        </div>
      </div>
    );
  }

  // ── Render ─────────────────────────────────────────────────────────────

  return (
    <section className="h-full flex flex-col min-h-0 overflow-hidden">
      {/* Section header with inline controls */}
      {embedded ? (
        <div className="section-header shrink-0">
          <span className="section-title">Briefing</span>
          {onToggleCollapse && (
            <button onClick={onToggleCollapse} className="w-5 h-5 flex items-center justify-center rounded-full text-muted-foreground/25 hover:text-foreground/50 hover:bg-foreground/[0.06] transition-all" title={collapsed ? 'Expand' : 'Collapse'}>
              <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${collapsed ? '-rotate-90' : ''}`} />
            </button>
          )}
          <div className="flex-1" />
          {/* Lang pills */}
          {availableLangs.length > 1 && (
            <div className="flex items-center gap-0.5 mr-1">
              {availableLangs.map(l => (
                <button key={l} onClick={() => setLang(l)}
                  className={`px-1.5 py-0.5 rounded text-[9px] font-mono transition-all ${
                    l === lang ? 'bg-foreground text-background font-bold' : 'text-muted-foreground/40 hover:text-foreground'
                  }`}>
                  {LANG_LABELS[l] ?? l.toUpperCase()}
                </button>
              ))}
            </div>
          )}
          {/* Date nav */}
          <button onClick={goPrev} disabled={!hasPrev} className="btn-icon"><ChevronLeft className="w-3 h-3" /></button>
          <span className="text-[10px] font-mono text-muted-foreground/60 tabular-nums min-w-[56px] text-center">
            {selectedDate ? compactDate(selectedDate) : '---'}
          </span>
          <button onClick={goNext} disabled={!hasNext} className="btn-icon"><ChevronRight className="w-3 h-3" /></button>
          {/* Updated time */}
          {report?.updated_at && (
            <span className="inline-flex items-center gap-1 text-muted-foreground/30 font-mono text-[10px] ml-1">
              <Clock className="w-2.5 h-2.5" />
              {new Date(report.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
          {/* TTS */}
          <button onClick={tts.toggle} disabled={tts.isLoading} className={`btn-icon ml-0.5 ${tts.isPlaying ? 'text-primary' : ''}`} title={tts.isLoading ? 'Generating...' : tts.isPlaying ? 'Stop' : 'Read aloud'}>
            {tts.isLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : tts.isPlaying ? <VolumeX className="w-3 h-3" /> : <Volume2 className="w-3 h-3" />}
          </button>
        </div>
      ) : !hideHeader ? (
        <DateNav date={selectedDate} hasPrev={hasPrev} hasNext={hasNext} onPrev={goPrev} onNext={goNext} isPlaying={tts.isPlaying} isLoading={tts.isLoading} onToggleTTS={tts.toggle} />
      ) : null}

      {!collapsed ? (<div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden">
        {reportLoading ? (
          <div className={`mx-auto space-y-6 ${embedded ? 'px-3 py-4' : 'px-6 md:px-10 py-8 max-w-3xl'}`}>
            {[...Array(embedded ? 3 : 5)].map((_, i) => (
              <div key={i} className="pl-4 relative space-y-2">
                <div className="absolute left-0 top-1 bottom-0 w-px bg-border/25" />
                <div className="flex gap-2 mb-2"><div className="h-2.5 w-5 rounded bg-border/20 animate-pulse" /><div className="h-2.5 w-40 rounded bg-border/20 animate-pulse" /></div>
                <div className="h-3 w-full rounded bg-border/[0.12] animate-pulse" />
                <div className="h-3 w-5/6 rounded bg-border/[0.12] animate-pulse" />
                <div className="h-3 w-4/5 rounded bg-border/[0.12] animate-pulse" />
              </div>
            ))}
          </div>
        ) : reportError ? (
          <div className="flex items-center justify-center py-20 text-muted-foreground/50 text-[12px] gap-2">
            <WifiOff className="w-3.5 h-3.5" /> Failed to load report
          </div>
        ) : report ? (
          <div key={selectedDate} className={`mx-auto animate-fade-in ${embedded ? 'px-3 py-3' : 'px-6 md:px-10 py-8 max-w-3xl'}`}>
            {!embedded && (
              <header className="mb-6">
                <div className="flex items-baseline justify-between gap-4 mb-1">
                  <h1 className="text-[11px] font-mono uppercase tracking-[0.12em] text-muted-foreground/40">Macro Intelligence Briefing</h1>
                  <span className="text-[10px] font-mono text-muted-foreground/30 tabular-nums shrink-0">{selectedDate ? formatDate(selectedDate) : ''}</span>
                </div>
                <div className="h-px bg-border/30 mt-2" />
              </header>
            )}

            {!embedded && <LangBar active={lang} available={availableLangs} onChange={setLang} />}

            {activeSections.length > 0 ? (
              <div>
                {activeSections.map((s, i) => (
                  <SectionBlock key={`${lang}-${i}`} section={s} index={i} compact={embedded} isActive={tts.activeIdx === i} />
                ))}
              </div>
            ) : (
              <div className="py-12 text-center"><p className="text-[12px] text-muted-foreground/40">No content for this language</p></div>
            )}

            <SourceBadges counts={sourceCounts as Record<string, number | undefined>} compact={embedded} />
          </div>
        ) : null}
      </div>) : null}
    </section>
  );
}
