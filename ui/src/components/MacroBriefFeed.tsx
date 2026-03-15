'use client';

import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import {
  BookOpen,
  WifiOff,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Youtube,
  FileText,
  Calendar,
  Loader2,
  MessageSquare,
  Rss,
  Building2,
  BarChart3,
  Globe,
} from 'lucide-react';

/* ═══════════════════════════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════════════════════════ */

interface ReportDate {
  date: string;
  has_briefing: boolean;
}

interface VideoSource {
  id: string;
  title: string;
  channel: string;
  url: string;
  views?: number;
  duration?: string;
}

interface DriveSource {
  title: string;
  url: string;
  file_id: string;
}

export interface SourceCounts {
  youtube?: number;
  drive?: number;
  central_banks?: number;
  news?: number;
  telegram?: number;
  macro_data?: number;
  reports?: number;
}

export interface ReportData {
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

/* ═══════════════════════════════════════════════════════════════════════════
   Parsers
   ═══════════════════════════════════════════════════════════════════════════ */

export interface MdSection {
  title: string;
  body: string;
}

export function parseBriefingSections(md: string): MdSection[] {
  const sections: MdSection[] = [];
  const lines = md.split('\n');
  const cleaned = lines
    .filter(
      (l) =>
        !l.startsWith('# Macro Intelligence Briefing') &&
        !l.startsWith('Continuing conversation') &&
        !l.startsWith('Resumed conversation'),
    )
    .join('\n')
    .trim();

  const parts = cleaned.split(/\*\*\d+\)\s*/);
  for (const part of parts) {
    if (!part.trim()) continue;
    const endOfTitle = part.indexOf('**');
    if (endOfTitle === -1) continue;
    const title = part.substring(0, endOfTitle).trim();
    const body = part
      .substring(endOfTitle + 2)
      .trim()
      .replace(/\s*\[\d+[-,\s\d]*\]/g, '');
    if (title && body) {
      sections.push({ title, body });
    }
  }
  return sections;
}

/** Parse `## Heading\nbody` blocks from translation text */
function parseTranslationSections(md: string): MdSection[] {
  const blocks = md.split(/\n(?=##\s)/);
  return blocks
    .map((block) => {
      const lines = block.trim().split('\n');
      const heading = lines[0]?.replace(/^##\s*/, '').trim();
      const body = lines.slice(1).join('\n').trim();
      return { title: heading ?? '', body };
    })
    .filter((s) => s.title && s.body);
}

function formatReportDate(dateStr: string): string {
  try {
    const [y, m, d] = dateStr.split('-').map(Number);
    const date = new Date(y, m - 1, d);
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   BriefingDocument — continuous research note renderer
   ═══════════════════════════════════════════════════════════════════════════ */

/** Renders a single paragraph, bolding inline **text** and detecting numeric tokens */
function BriefingParagraph({ text }: { text: string }) {
  // Split on **bold** markers and numeric tokens (e.g. "-2.3%", "$1.2T", "3.4x")
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <p className="text-[13.5px] leading-[1.85] text-foreground/75 mb-3 last:mb-0">
      {parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          const inner = part.slice(2, -2);
          return (
            <strong key={i} className="font-semibold text-foreground/90">
              {inner}
            </strong>
          );
        }
        // Highlight numeric tokens inline with monospace
        const tokens = part.split(/(\b[\-+]?\d[\d,.]*%?[xX]?|\$[\d,.]+[BMTKbmtk]?\b)/g);
        return (
          <React.Fragment key={i}>
            {tokens.map((tok, j) =>
              /^[\-+]?\d|^\$/.test(tok) ? (
                <span key={j} className="font-mono text-[12.5px] text-foreground/85">
                  {tok}
                </span>
              ) : (
                tok
              ),
            )}
          </React.Fragment>
        );
      })}
    </p>
  );
}

/** Renders a full section with a left-border accent divider */
function BriefingSection({
  section,
  index,
  isLast,
}: {
  section: MdSection;
  index: number;
  isLast: boolean;
}) {
  const paragraphs = section.body
    .split(/\n{2,}/)
    .map((p) => p.replace(/\n/g, ' ').trim())
    .filter(Boolean);

  return (
    <article className={`relative pl-4 ${isLast ? '' : 'pb-7'}`}>
      {/* Left accent bar */}
      <div className="absolute left-0 top-1 bottom-0 w-px bg-border/40" />

      {/* Section number + title */}
      <div className="flex items-baseline gap-2.5 mb-3">
        <span className="text-[10px] font-mono text-muted-foreground/35 tabular-nums shrink-0 select-none">
          {String(index + 1).padStart(2, '0')}
        </span>
        <h3 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/60">
          {section.title}
        </h3>
      </div>

      {/* Body paragraphs */}
      <div className="space-y-0">
        {paragraphs.map((para, i) => (
          <BriefingParagraph key={i} text={para} />
        ))}
      </div>
    </article>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   Source footer
   ═══════════════════════════════════════════════════════════════════════════ */

const SOURCE_BADGES = [
  { key: 'youtube', icon: Youtube, label: 'videos', color: 'text-rose-400/50' },
  { key: 'drive', icon: FileText, label: 'PDFs', color: 'text-primary/50' },
  { key: 'news', icon: Rss, label: 'news feeds', color: 'text-amber-400/50' },
  { key: 'telegram', icon: MessageSquare, label: 'messages', color: 'text-sky-400/50' },
  { key: 'central_banks', icon: Building2, label: 'central bank docs', color: 'text-emerald-400/50' },
  { key: 'macro_data', icon: BarChart3, label: 'indicators', color: 'text-violet-400/50' },
  { key: 'reports', icon: Globe, label: 'research reports', color: 'text-primary/50' },
] as const;

function SourcesFooter({
  sourceCounts,
  videoSources,
  driveSources,
}: {
  sourceCounts: SourceCounts;
  videoSources: VideoSource[];
  driveSources: DriveSource[];
}) {
  const [open, setOpen] = useState(false);
  const hasAny =
    videoSources.length > 0 ||
    driveSources.length > 0 ||
    Object.values(sourceCounts).some((v) => v && v > 0);

  if (!hasAny) return null;

  return (
    <div className="mt-8 pt-5 border-t border-border/20">
      {/* Summary row — always visible */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-3 text-left group"
        aria-expanded={open}
      >
        <span className="text-[10px] font-mono uppercase tracking-[0.1em] text-muted-foreground/35 group-hover:text-muted-foreground/55 transition-colors">
          Sources
        </span>
        <div className="flex items-center gap-1.5 flex-wrap flex-1">
          {SOURCE_BADGES.map(({ key, icon: Icon, label, color }) => {
            const count = sourceCounts[key as keyof SourceCounts];
            if (!count) return null;
            return (
              <span
                key={key}
                className="inline-flex items-center gap-1 text-[10px] font-mono text-muted-foreground/45 bg-card border border-border/25 rounded px-1.5 py-0.5"
              >
                <Icon className={`w-2.5 h-2.5 ${color}`} />
                {count} {label}
              </span>
            );
          })}
        </div>
        <span className="text-muted-foreground/30 group-hover:text-muted-foreground/50 transition-colors shrink-0">
          {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </span>
      </button>

      {/* Expanded source lists */}
      {open && (
        <div className="mt-4 space-y-5">
          {videoSources.length > 0 && (
            <div>
              <p className="stat-label mb-2">YouTube ({videoSources.length})</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-px border border-border/20 rounded-[var(--radius)] overflow-hidden bg-border/10">
                {videoSources.map((v) => (
                  <a
                    key={v.id}
                    href={v.url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-start gap-2.5 px-3 py-2.5 bg-background hover:bg-card transition-colors group/link"
                  >
                    <Youtube className="w-3 h-3 mt-0.5 text-rose-400/40 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="text-[11.5px] text-foreground/80 leading-snug truncate group-hover/link:text-foreground transition-colors">
                        {v.title}
                      </p>
                      <p className="text-[10px] font-mono text-muted-foreground/40 mt-0.5">
                        {v.channel}
                        {v.duration ? ` · ${v.duration}` : ''}
                        {v.views ? ` · ${v.views.toLocaleString()} views` : ''}
                      </p>
                    </div>
                    <ExternalLink className="w-3 h-3 text-muted-foreground/20 group-hover/link:text-muted-foreground/50 transition-colors shrink-0 mt-0.5" />
                  </a>
                ))}
              </div>
            </div>
          )}

          {driveSources.length > 0 && (
            <div>
              <p className="stat-label mb-2">Research Papers ({driveSources.length})</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-px border border-border/20 rounded-[var(--radius)] overflow-hidden bg-border/10">
                {driveSources.map((d, i) => (
                  <a
                    key={i}
                    href={d.url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-start gap-2.5 px-3 py-2.5 bg-background hover:bg-card transition-colors group/link"
                  >
                    <FileText className="w-3 h-3 mt-0.5 text-primary/40 shrink-0" />
                    <p className="text-[11.5px] text-foreground/80 leading-snug truncate flex-1 group-hover/link:text-foreground transition-colors">
                      {d.title}
                    </p>
                    <ExternalLink className="w-3 h-3 text-muted-foreground/20 group-hover/link:text-muted-foreground/50 transition-colors shrink-0 mt-0.5" />
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   Language selector bar
   ═══════════════════════════════════════════════════════════════════════════ */

const LANG_LABELS: Record<string, string> = {
  en: 'EN',
  cn: '中文',
  kr: '한국어',
  jp: '日本語',
};

function LangBar({
  active,
  available,
  onChange,
  updatedAt,
}: {
  active: string;
  available: string[];
  onChange: (lang: string) => void;
  updatedAt?: string | null;
}) {
  return (
    <div className="flex items-center justify-between gap-4 mb-6 pb-4 border-b border-border/20">
      <div className="flex items-center gap-0.5">
        {available.map((lang) => (
          <button
            key={lang}
            onClick={() => onChange(lang)}
            className={`px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.06em] rounded-[var(--radius)] transition-colors ${
              active === lang
                ? 'bg-foreground text-background'
                : 'text-muted-foreground/50 hover:text-foreground hover:bg-border/30'
            }`}
          >
            {LANG_LABELS[lang] ?? lang.toUpperCase()}
          </button>
        ))}
      </div>
      {updatedAt && (
        <span className="text-[10px] font-mono text-muted-foreground/30 tabular-nums shrink-0">
          {new Date(updatedAt).toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            timeZoneName: 'short',
          })}
        </span>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   Main Component
   ═══════════════════════════════════════════════════════════════════════════ */

export default function MacroBriefFeed({
  embedded,
  hideHeader,
  externalDateIdx,
  onDateIdxChange,
}: {
  embedded?: boolean;
  hideHeader?: boolean;
  externalDateIdx?: number;
  onDateIdxChange?: (idx: number) => void;
}) {
  const {
    data: reportDates = [],
    isLoading: datesLoading,
    isError: datesError,
  } = useQuery<ReportDate[]>({
    queryKey: ['research-reports'],
    queryFn: () => apiFetchJson<ReportDate[]>('/api/news/reports'),
    staleTime: 120_000,
  });

  const [internalDateIdx, setInternalDateIdx] = useState(0);
  const dateIdx = externalDateIdx ?? internalDateIdx;
  const setDateIdx = onDateIdxChange ?? setInternalDateIdx;
  const selectedDate = reportDates[dateIdx]?.date ?? null;

  const {
    data: report,
    isLoading: reportLoading,
    isError: reportError,
  } = useQuery<ReportData>({
    queryKey: ['research-report', selectedDate],
    queryFn: () => apiFetchJson<ReportData>(`/api/news/reports/${selectedDate}`),
    enabled: !!selectedDate,
    staleTime: 300_000,
  });

  const hasPrev = dateIdx < reportDates.length - 1;
  const hasNext = dateIdx > 0;

  const [briefingLang, setBriefingLang] = useState<string>('en');

  const briefingSections = useMemo(
    () => (report?.briefing ? parseBriefingSections(report.briefing) : []),
    [report?.briefing],
  );

  const translations = useMemo(
    () => report?.sources?.translations ?? {},
    [report?.sources?.translations],
  );

  const availableLangs = useMemo(() => {
    const langs = ['en'];
    for (const lang of ['cn', 'kr', 'jp']) {
      if (translations[lang]) langs.push(lang);
    }
    return langs;
  }, [translations]);

  const activeSections = useMemo(() => {
    if (briefingLang === 'en') return briefingSections;
    const raw = translations[briefingLang];
    if (!raw) return [];
    return parseTranslationSections(raw);
  }, [briefingLang, briefingSections, translations]);

  const videoSources = useMemo(
    () => report?.sources?.selected_videos ?? [],
    [report?.sources?.selected_videos],
  );
  const driveSources = useMemo(
    () => report?.sources?.drive_files ?? [],
    [report?.sources?.drive_files],
  );
  const sourceCounts = useMemo(
    () => report?.sources?.counts ?? {},
    [report?.sources?.counts],
  );

  /* ── Loading / Error / Empty ──────────────────────────────────────────── */

  if (datesLoading) {
    return (
      <div
        role="status"
        aria-busy="true"
        aria-label="Loading research reports"
        className="h-32 flex items-center justify-center"
      >
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground/30" />
      </div>
    );
  }

  if (datesError) {
    return (
      <div
        role="alert"
        className="m-6 border border-border/30 rounded-[var(--radius)] bg-card p-8 flex flex-col items-center gap-3 text-center"
      >
        <WifiOff className="w-5 h-5 text-muted-foreground/30" />
        <p className="text-[12px] text-muted-foreground/60">Unable to load research reports</p>
      </div>
    );
  }

  if (reportDates.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <BookOpen className="w-6 h-6 mx-auto mb-2 text-muted-foreground/20" />
          <p className="text-[12px] text-muted-foreground/50">No research reports yet</p>
          <p className="text-[11px] mt-1 text-muted-foreground/30 font-mono">
            Run the research pipeline to generate one
          </p>
        </div>
      </div>
    );
  }

  return (
    <section className="h-full flex flex-col min-h-0 overflow-hidden">
      {/* ── Standalone header (shown when not controlled externally) ──── */}
      {!hideHeader && (
        <div className="h-9 px-4 sm:px-5 border-b border-border/25 flex items-center justify-between shrink-0 bg-background">
          <div className="flex items-center gap-2">
            <BookOpen className="w-3.5 h-3.5 text-primary shrink-0" />
            <span className="text-[11px] font-semibold text-foreground uppercase tracking-wide">
              Macro Research
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setDateIdx(dateIdx + 1)}
              disabled={!hasPrev}
              className="btn-icon"
              aria-label="Previous report"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <div className="flex items-center gap-1.5 min-w-[130px] justify-center">
              <Calendar className="w-3 h-3 text-muted-foreground/40" />
              <span className="text-[11px] font-mono text-muted-foreground/60 tabular-nums">
                {selectedDate ? formatReportDate(selectedDate) : '---'}
              </span>
            </div>
            <button
              onClick={() => setDateIdx(dateIdx - 1)}
              disabled={!hasNext}
              className="btn-icon"
              aria-label="Next report"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* ── Scrollable content ────────────────────────────────────────── */}
      <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden">
        {reportLoading ? (
          /* ── Skeleton ──────────────────────────────────────────────── */
          <div
            className="max-w-3xl mx-auto px-6 md:px-10 py-8 space-y-8"
            role="status"
            aria-busy="true"
            aria-label="Loading report"
          >
            {/* Lang bar skeleton */}
            <div className="flex gap-2 pb-4 border-b border-border/20">
              {[40, 52, 60, 56].map((w, i) => (
                <div key={i} className="h-6 rounded bg-border/20" style={{ width: w }} />
              ))}
            </div>
            {/* Section skeletons */}
            {[...Array(5)].map((_, i) => (
              <div key={i} className="pl-4 relative space-y-2.5">
                <div className="absolute left-0 top-1 bottom-0 w-px bg-border/25" />
                <div className="flex gap-2 mb-3">
                  <div className="h-2.5 w-5 rounded bg-border/20" />
                  <div className="h-2.5 w-40 rounded bg-border/20" />
                </div>
                <div className="h-3 w-full rounded bg-border/[0.12]" />
                <div className="h-3 w-5/6 rounded bg-border/[0.12]" />
                <div className="h-3 w-4/5 rounded bg-border/[0.12]" />
                <div className="h-3 w-full rounded bg-border/[0.12]" />
                <div className="h-3 w-2/3 rounded bg-border/[0.12]" />
              </div>
            ))}
          </div>
        ) : reportError ? (
          <div className="flex items-center justify-center py-20 text-muted-foreground/50 text-[12px] gap-2">
            <WifiOff className="w-3.5 h-3.5" />
            Failed to load report
          </div>
        ) : report ? (
          /* ── Research document ─────────────────────────────────────── */
          <div
            key={selectedDate}
            className="max-w-3xl mx-auto px-6 md:px-10 py-8 animate-fade-in"
          >
            {/* Document header */}
            <header className="mb-6">
              <div className="flex items-baseline justify-between gap-4 mb-1">
                <h1 className="text-[11px] font-mono uppercase tracking-[0.12em] text-muted-foreground/40">
                  Macro Intelligence Briefing
                </h1>
                <span className="text-[10px] font-mono text-muted-foreground/30 tabular-nums shrink-0">
                  {selectedDate ? formatReportDate(selectedDate) : ''}
                </span>
              </div>
              <div className="h-px bg-border/30 mt-2" />
            </header>

            {/* Lang selector + update time */}
            {(briefingSections.length > 0 || availableLangs.length > 1) && (
              <LangBar
                active={briefingLang}
                available={availableLangs}
                onChange={setBriefingLang}
                updatedAt={report.updated_at}
              />
            )}

            {/* Section flow */}
            {activeSections.length > 0 ? (
              <div>
                {activeSections.map((section, i) => (
                  <BriefingSection
                    key={`${briefingLang}-${i}`}
                    section={section}
                    index={i}
                    isLast={i === activeSections.length - 1}
                  />
                ))}
              </div>
            ) : (
              <div className="py-12 text-center">
                <p className="text-[12px] text-muted-foreground/40">No content for this language</p>
              </div>
            )}

            {/* Sources footer */}
            <SourcesFooter
              sourceCounts={sourceCounts}
              videoSources={videoSources}
              driveSources={driveSources}
            />
          </div>
        ) : null}
      </div>
    </section>
  );
}
