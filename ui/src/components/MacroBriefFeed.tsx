'use client';

import React, { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson, apiFetch } from '@/lib/api';
import {
  BookOpen,
  WifiOff,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Image as ImageIcon,
  AlertTriangle,
  Shield,
  Zap,
  ExternalLink,
  Info,
  Youtube,
  FileText,
  X,
  ZoomIn,
  Calendar,
  Presentation,
  Download,
  Loader2,
  MessageSquare,
  Rss,
  Building2,
  BarChart3,
  Globe,
} from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';

/* ═══════════════════════════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════════════════════════ */

interface ReportDate {
  date: string;
  has_briefing: boolean;
  has_risk_scorecard: boolean;
  has_takeaways: boolean;
  has_infographic: boolean;
  has_slide_deck: boolean;
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
  risk_scorecard: string | null;
  takeaways: string | null;
  sources: {
    selected_videos?: VideoSource[];
    drive_files?: DriveSource[];
    counts?: SourceCounts;
  };
  has_infographic: boolean;
  has_slide_deck: boolean;
}

/* ═══════════════════════════════════════════════════════════════════════════
   Parsers
   ═══════════════════════════════════════════════════════════════════════════ */

export interface RiskItem {
  category: string;
  score: number;
  experts: string;
  description: string;
}

export function parseRiskScorecard(md: string): RiskItem[] {
  const items: RiskItem[] = [];
  // Split on risk category headers: **Category: N/10**
  const headerRegex = /\*\*([^:*]+):\s*(\d+)\/10\*\*/g;
  const headers: { category: string; score: number; start: number; end: number }[] = [];
  let match;
  while ((match = headerRegex.exec(md)) !== null) {
    headers.push({
      category: match[1].trim(),
      score: parseInt(match[2], 10),
      start: match.index,
      end: match.index + match[0].length,
    });
  }

  for (let i = 0; i < headers.length; i++) {
    const blockEnd = i + 1 < headers.length ? headers[i + 1].start : md.length;
    const block = md.substring(headers[i].end, blockEnd).trim();

    // Try to extract experts from various formats:
    //   **Key Expert[s]:** Name      or   * **Key Expert[s]:** Name
    let experts = '';
    const expertMatch = block.match(/\*\*Key\s+Expert[s]?:\*\*\s*(.+)/i);
    if (expertMatch) {
      experts = expertMatch[1].trim();
    }

    // Extract description from various formats:
    //   **Why:** text     or  **Key Evidence & Explanation:** text  or  just bullet body
    let description = '';
    const whyMatch = block.match(/\*\*Why:\*\*\s*([\s\S]*?)(?=\n\*\s+\*\*|\n\n|$)/i);
    const evidenceMatch = block.match(
      /\*\*Key Evidence[^*]*:\*\*\s*([\s\S]*?)(?=\n\*\s+\*\*[A-Z]|\n\n\*\*[A-Z]|$)/i,
    );
    if (whyMatch) {
      description = whyMatch[1].trim();
    } else if (evidenceMatch) {
      description = evidenceMatch[1].trim();
    } else {
      // Fallback: use the whole block minus any **Label:** prefixes
      description = block.replace(/\*\s+\*\*[^*]+\*\*\s*/g, '').trim();
    }

    // Clean citation references [1, 2] etc.
    description = description.replace(/\s*\[\d+[-,\s\d]*\]/g, '');

    items.push({
      category: headers[i].category,
      score: headers[i].score,
      experts,
      description: description.substring(0, 2000),
    });
  }
  return items;
}

function scoreColor(score: number): string {
  if (score >= 8) return 'text-rose-400';
  if (score >= 6) return 'text-amber-400';
  return 'text-emerald-400';
}

function scoreLabel(score: number): string {
  if (score >= 8) return 'High Risk';
  if (score >= 6) return 'Elevated';
  return 'Low Risk';
}

function scoreBgClass(score: number): string {
  if (score >= 8) return 'bg-rose-500/10';
  if (score >= 6) return 'bg-amber-500/10';
  return 'bg-emerald-500/10';
}

function scoreBarColor(score: number): string {
  if (score >= 8) return 'bg-rose-400';
  if (score >= 6) return 'bg-amber-400';
  return 'bg-emerald-400';
}

function scoreBorderClass(score: number): string {
  if (score >= 8) return 'border-rose-500/25';
  if (score >= 6) return 'border-amber-500/25';
  return 'border-emerald-500/25';
}

export interface MdSection {
  title: string;
  body: string;
}

export function parseBriefingSections(md: string): MdSection[] {
  const sections: MdSection[] = [];
  const lines = md.split('\n');
  const cleaned = lines
    .filter(l => !l.startsWith('# Macro Intelligence Briefing') && !l.startsWith('Continuing conversation') && !l.startsWith('Resumed conversation'))
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

export interface Takeaway {
  title: string;
  body: string;
}

export function parseTakeaways(md: string): Takeaway[] {
  const items: Takeaway[] = [];
  const regex = /\*\s+\*\*([^*]+)\*\*\s*([\s\S]*?)(?=\n\*\s+\*\*|Resumed conversation:|$)/g;
  let match;
  while ((match = regex.exec(md)) !== null) {
    items.push({
      title: match[1].trim().replace(/:$/, ''),
      body: match[2].trim().replace(/\s*\[\d+[-,\s\d]*\]/g, ''),
    });
  }
  return items;
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
   Sub-components
   ═══════════════════════════════════════════════════════════════════════════ */

function SectionHeading({
  icon,
  children,
  className = '',
}: {
  icon: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <h3
      className={`flex items-center gap-2 text-[11px] uppercase tracking-widest text-muted-foreground/60 font-mono font-medium select-none ${className}`}
    >
      {icon}
      {children}
    </h3>
  );
}

function ScoreBar({ score }: { score: number }) {
  return (
    <div className="flex items-center gap-2 w-full" role="meter" aria-valuenow={score} aria-valuemin={0} aria-valuemax={10} aria-label={`Risk score: ${score} out of 10, ${scoreLabel(score)}`}>
      <div className="flex-1 h-1.5 rounded-full bg-primary/10 overflow-hidden" aria-hidden="true">
        <div
          className={`h-full rounded-full transition-all duration-500 ${scoreBarColor(score)}`}
          style={{ width: `${score * 10}%` }}
        />
      </div>
      <span className={`text-xs font-mono font-bold tabular-nums min-w-[32px] text-right ${scoreColor(score)}`}>
        {score}/10
      </span>
    </div>
  );
}

/* ── PDF Slide Viewer ──────────────────────────────────────────────────── */

function SlideDeckViewer({ pdfUrl, date }: { pdfUrl: string; date: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [pdfDoc, setPdfDoc] = useState<any>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const renderingRef = useRef(false);
  const [resizeNonce, setResizeNonce] = useState(0);

  // Load PDF
  useEffect(() => {
    let cancelled = false;

    async function loadPdf() {
      setLoading(true);
      setError(null);
      setPdfDoc(null);
      setCurrentPage(1);
      setTotalPages(0);

      try {
        const res = await apiFetch(pdfUrl);
        if (!res.ok) throw new Error('Failed to fetch slide deck');
        const arrayBuffer = await res.arrayBuffer();

        // Load pdf.js from CDN (UMD build) to avoid webpack/SSR bundling issues
        const PDFJS_CDN = 'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build';
        let pdfjs = (window as any).pdfjsLib;
        if (!pdfjs) {
          await new Promise<void>((resolve, reject) => {
            const s = document.createElement('script');
            s.src = `${PDFJS_CDN}/pdf.min.js`;
            s.onload = () => resolve();
            s.onerror = () => reject(new Error('Failed to load PDF.js'));
            document.head.appendChild(s);
          });
          pdfjs = (window as any).pdfjsLib;
          if (!pdfjs) throw new Error('PDF.js library not available');
          pdfjs.GlobalWorkerOptions.workerSrc = `${PDFJS_CDN}/pdf.worker.min.js`;
        }

        const doc = await pdfjs.getDocument({ data: arrayBuffer }).promise;
        if (cancelled) return;

        setPdfDoc(doc);
        setTotalPages(doc.numPages);
        setCurrentPage(1);
      } catch (err: any) {
        if (!cancelled) setError(err.message || 'Failed to load PDF');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadPdf();
    return () => { cancelled = true; };
  }, [pdfUrl]);

  // Render current page
  useEffect(() => {
    if (!pdfDoc || !canvasRef.current || renderingRef.current) return;

    let cancelled = false;
    renderingRef.current = true;

    async function renderPage() {
      try {
        const page = await pdfDoc.getPage(currentPage);
        if (cancelled) return;

        const canvas = canvasRef.current;
        if (!canvas) return;

        const containerWidth = canvas.parentElement?.clientWidth || 800;
        const viewport = page.getViewport({ scale: 1 });
        const scale = (containerWidth * window.devicePixelRatio) / viewport.width;
        const scaledViewport = page.getViewport({ scale });

        canvas.width = scaledViewport.width;
        canvas.height = scaledViewport.height;
        canvas.style.width = `${scaledViewport.width / window.devicePixelRatio}px`;
        canvas.style.height = `${scaledViewport.height / window.devicePixelRatio}px`;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        await page.render({ canvasContext: ctx, viewport: scaledViewport }).promise;
      } catch {
        // Render error — ignore silently
      } finally {
        renderingRef.current = false;
      }
    }

    renderPage();
    return () => { cancelled = true; };
  }, [pdfDoc, currentPage, resizeNonce]);

  // Re-render canvas when container resizes
  useEffect(() => {
    const el = containerRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    let timeoutId: ReturnType<typeof setTimeout>;
    const observer = new ResizeObserver(() => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => setResizeNonce((n) => n + 1), 150);
    });
    observer.observe(el);
    return () => {
      observer.disconnect();
      clearTimeout(timeoutId);
    };
  }, []);

  // Keyboard navigation
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault();
        setCurrentPage((p) => Math.max(1, p - 1));
      } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault();
        setCurrentPage((p) => Math.min(totalPages, p + 1));
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [totalPages]);

  if (loading) {
    return (
      <div className="space-y-3" role="status" aria-busy="true" aria-label="Loading slide deck">
        <div className="relative rounded-[var(--radius)] border border-border/50 overflow-hidden bg-primary/[0.03]" style={{ paddingBottom: '56.25%' }}>
          <div className="absolute inset-0 -translate-x-full animate-[shimmer_1.6s_ease-in-out_infinite] bg-gradient-to-r from-transparent via-foreground/[0.04] to-transparent" />
          <div className="absolute inset-0 flex items-center justify-center">
            <Presentation className="w-8 h-8 text-muted-foreground/15" />
          </div>
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="w-2 h-2 rounded-full bg-primary/10" />
            ))}
          </div>
          <div className="h-3 w-12 rounded bg-primary/[0.06]" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground/60 text-sm gap-2">
        <AlertTriangle className="w-4 h-4 text-rose-400/50" />
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Slide canvas */}
      <div ref={containerRef} className="relative rounded-[var(--radius)] border border-border/50 overflow-hidden bg-primary/[0.03]">
        <canvas ref={canvasRef} className="w-full block" />

        {/* Left/right click zones */}
        {totalPages > 1 && (
          <>
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="absolute left-0 top-0 bottom-0 w-1/4 cursor-pointer group"
              aria-label="Previous slide"
            >
              <div className="absolute left-3 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-background/80 backdrop-blur-sm border border-border/50 rounded-lg p-2 shadow-lg">
                <ChevronLeft className="w-5 h-5 text-foreground" />
              </div>
            </button>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="absolute right-0 top-0 bottom-0 w-1/4 cursor-pointer group"
              aria-label="Next slide"
            >
              <div className="absolute right-3 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-background/80 backdrop-blur-sm border border-border/50 rounded-lg p-2 shadow-lg">
                <ChevronRight className="w-5 h-5 text-foreground" />
              </div>
            </button>
          </>
        )}
      </div>

      {/* Page controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="p-1.5 rounded-md text-muted-foreground/40 hover:text-muted-foreground hover:bg-primary/10 transition-colors disabled:opacity-20"
            aria-label="Previous slide"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          {/* Page dots for quick nav */}
          <div className="flex items-center gap-1">
            {Array.from({ length: totalPages }, (_, i) => (
              <button
                key={i}
                onClick={() => setCurrentPage(i + 1)}
                className={`w-2 h-2 rounded-full transition-all ${
                  i + 1 === currentPage
                    ? 'bg-primary scale-125'
                    : 'bg-primary/15 hover:bg-primary/20'
                }`}
                aria-label={`Go to slide ${i + 1}`}
              />
            ))}
          </div>

          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="p-1.5 rounded-md text-muted-foreground/40 hover:text-muted-foreground hover:bg-primary/10 transition-colors disabled:opacity-20"
            aria-label="Next slide"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-[11px] font-mono text-muted-foreground/50 tabular-nums">
            {currentPage} / {totalPages}
          </span>
          <a
            href={pdfUrl}
            download={`macro-slides-${date}.pdf`}
            className="p-1.5 rounded-md text-muted-foreground/40 hover:text-muted-foreground hover:bg-primary/10 transition-colors"
            title="Download PDF"
          >
            <Download className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>
    </div>
  );
}

/* ── Infographic Lightbox ──────────────────────────────────────────────── */

function InfographicLightbox({
  src,
  alt,
  onClose,
}: {
  src: string;
  alt: string;
  onClose: () => void;
}) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 md:p-8" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative max-w-5xl w-full max-h-[90vh] overflow-auto rounded-lg border border-border/50 bg-background shadow-lg">
        <button
          onClick={onClose}
          className="absolute top-3 right-3 z-10 rounded-md p-1.5 bg-background/80 border border-border/50 text-muted-foreground/60 hover:bg-primary/10 hover:text-foreground transition-colors backdrop-blur-sm"
          aria-label="Close"
        >
          <X className="w-4 h-4" />
        </button>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={src} alt={alt} className="w-full h-auto" />
      </div>
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
  const selectedMeta = reportDates[dateIdx] ?? null;

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

  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [expandedBriefing, setExpandedBriefing] = useState<Record<number, boolean>>({});
  const [showSources, setShowSources] = useState(false);
  const [mediaView, setMediaView] = useState<'slides' | 'infographic'>('slides');
  const [infographicLoaded, setInfographicLoaded] = useState(false);

  useEffect(() => { setInfographicLoaded(false); }, [selectedDate, mediaView]);

  const riskItems = useMemo(
    () => (report?.risk_scorecard ? parseRiskScorecard(report.risk_scorecard) : []),
    [report?.risk_scorecard],
  );

  const briefingSections = useMemo(
    () => (report?.briefing ? parseBriefingSections(report.briefing) : []),
    [report?.briefing],
  );

  const takeaways = useMemo(
    () => (report?.takeaways ? parseTakeaways(report.takeaways) : []),
    [report?.takeaways],
  );

  const videoSources = useMemo(() => report?.sources?.selected_videos ?? [], [report?.sources?.selected_videos]);
  const driveSources = useMemo(() => report?.sources?.drive_files ?? [], [report?.sources?.drive_files]);
  const sourceCounts = useMemo(() => report?.sources?.counts ?? {}, [report?.sources?.counts]);

  const toggleBriefingSection = useCallback(
    (i: number) => setExpandedBriefing((prev) => ({ ...prev, [i]: !prev[i] })),
    [],
  );

  /* ── Loading / Error / Empty ──────────────────────────────────────────── */

  if (datesLoading) {
    return (
      <div role="status" aria-busy="true" aria-label="Loading research reports" className="h-32 flex flex-col items-center justify-center gap-3">
        <Loader2 className="w-5 h-5 animate-spin text-primary/40" />
        <div className="flex items-center gap-2">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-2 w-16 rounded bg-primary/[0.06]" />
          ))}
        </div>
      </div>
    );
  }

  if (datesError) {
    return (
      <div role="alert" className="border border-rose-500/20 rounded-lg bg-rose-500/[0.04] p-8 flex flex-col items-center gap-3 text-center">
        <WifiOff className="w-6 h-6 text-rose-400/50" />
        <p className="text-sm text-muted-foreground">Unable to load research reports</p>
      </div>
    );
  }

  if (reportDates.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground/60 text-sm">
        <div className="text-center">
          <BookOpen className="w-8 h-8 mx-auto mb-2 opacity-30" />
          <p>No research reports yet</p>
          <p className="text-[11px] mt-1 text-muted-foreground/40">
            Run the research pipeline to generate one
          </p>
        </div>
      </div>
    );
  }

  const infographicSrc = `/api/news/reports/${selectedDate}/infographic`;
  const slideDeckUrl = `/api/news/reports/${selectedDate}/slide-deck`;

  return (
    <section className="h-full flex flex-col min-h-0 overflow-hidden">
      {/* ── Header bar (hidden when externally controlled) ─────────────── */}
      {!hideHeader && (
        <div className="px-4 py-2.5 border-b border-border/25 shrink-0 bg-background/95 supports-[backdrop-filter]:bg-background sticky top-0 z-20">
          <div className="flex items-center justify-between max-w-[1600px] mx-auto">
            <div className="flex items-center gap-2.5">
              <BookOpen className="w-3.5 h-3.5 text-primary shrink-0" />
              <span className="text-xs font-semibold text-foreground tracking-tight">
                Macro Research
              </span>
              {selectedDate && (
                <>
                  <span className="text-muted-foreground/20 text-xs">/</span>
                  <span className="text-[10px] text-muted-foreground/50 font-mono">
                    {[
                      riskItems.length > 0 && `${riskItems.length} risks`,
                      briefingSections.length > 0 && `${briefingSections.length} sections`,
                      takeaways.length > 0 && `${takeaways.length} takeaways`,
                    ]
                      .filter(Boolean)
                      .join(' / ')}
                  </span>
                </>
              )}
            </div>

            {/* Date navigator */}
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setDateIdx(dateIdx + 1)}
                disabled={!hasPrev}
                className="p-1 rounded-md text-muted-foreground/40 hover:text-muted-foreground hover:bg-primary/10 transition-colors disabled:opacity-20 disabled:cursor-default"
                aria-label="Previous report"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>
              <div className="flex items-center gap-1.5 min-w-[140px] justify-center">
                <Calendar className="w-3 h-3 text-muted-foreground/40" />
                <span className="text-[11px] font-mono text-muted-foreground/70">
                  {selectedDate ? formatReportDate(selectedDate) : '---'}
                </span>
              </div>
              <button
                onClick={() => setDateIdx(dateIdx - 1)}
                disabled={!hasNext}
                className="p-1 rounded-md text-muted-foreground/40 hover:text-muted-foreground hover:bg-primary/10 transition-colors disabled:opacity-20 disabled:cursor-default"
                aria-label="Next report"
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Content ──────────────────────────────────────────────────────── */}
      <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden custom-scrollbar">
        {reportLoading ? (
          <div className="px-5 md:px-8 py-6 space-y-10 max-w-[1600px] mx-auto" role="status" aria-busy="true" aria-label="Loading report">
            {/* Media + takeaways skeleton */}
            <div className="flex flex-col lg:flex-row gap-6">
              <div className="flex-1 min-w-0 lg:max-w-[60%]">
                <div className="relative rounded-[var(--radius)] border border-border/50 overflow-hidden bg-primary/[0.03]" style={{ paddingBottom: '56.25%' }}>
                  <div className="absolute inset-0 -translate-x-full animate-[shimmer_1.6s_ease-in-out_infinite] bg-gradient-to-r from-transparent via-foreground/[0.04] to-transparent" />
                </div>
              </div>
              <div className="lg:w-[40%] shrink-0 space-y-2.5">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="rounded-lg border border-primary/20 bg-primary/[0.03] p-3 space-y-2">
                    <div className="h-3 w-3/4 rounded bg-primary/[0.06]" />
                    <div className="h-2 w-full rounded bg-primary/[0.04]" />
                    <div className="h-2 w-5/6 rounded bg-primary/[0.04]" />
                  </div>
                ))}
              </div>
            </div>
            {/* Risk cards skeleton */}
            <div>
              <div className="h-3 w-28 rounded bg-primary/[0.06] mb-4" />
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="rounded-lg border border-border/40 bg-primary/[0.02] px-3.5 py-3 space-y-2">
                    <div className="h-2.5 w-20 rounded bg-primary/[0.06]" />
                    <div className="h-1.5 rounded-full bg-primary/10" />
                  </div>
                ))}
              </div>
            </div>
            {/* Briefing skeleton */}
            <div>
              <div className="h-3 w-24 rounded bg-primary/[0.06] mb-4" />
              <div className="space-y-3">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="rounded-[var(--radius)] border border-border/40 bg-primary/[0.02] px-4 py-3 space-y-2">
                    <div className="h-3 w-2/3 rounded bg-primary/[0.06]" />
                    <div className="h-2 w-full rounded bg-primary/[0.04]" />
                    <div className="h-2 w-4/5 rounded bg-primary/[0.04]" />
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : reportError ? (
          <div className="flex items-center justify-center py-20 text-muted-foreground text-sm">
            <WifiOff className="w-4 h-4 mr-2 text-rose-400/50" />
            Failed to load report
          </div>
        ) : report ? (
          <div key={selectedDate} className="px-5 md:px-8 py-6 space-y-10 max-w-[1600px] mx-auto animate-fade-in">

            {/* ── Media + Takeaways (side-by-side on lg) ────────────────── */}
            {(report.has_slide_deck || report.has_infographic || takeaways.length > 0) && (
              <section className="flex flex-col lg:flex-row gap-6">
                {/* Left: Slide Deck / Infographic toggle */}
                {(report.has_slide_deck || report.has_infographic) && (
                  <div className="flex-1 min-w-0 lg:max-w-[60%]">
                    {/* Toggle tabs (only when both exist) */}
                    {report.has_slide_deck && report.has_infographic && (
                      <div className="flex items-center gap-1 mb-4">
                        <button
                          onClick={() => setMediaView('slides')}
                          className={`flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1.5 rounded-md transition-colors ${
                            mediaView === 'slides'
                              ? 'bg-primary/10 text-primary'
                              : 'text-muted-foreground hover:text-foreground hover:bg-primary/[0.06]'
                          }`}
                        >
                          <Presentation className="w-3.5 h-3.5" />
                          Slide Deck
                        </button>
                        <button
                          onClick={() => setMediaView('infographic')}
                          className={`flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1.5 rounded-md transition-colors ${
                            mediaView === 'infographic'
                              ? 'bg-primary/10 text-primary'
                              : 'text-muted-foreground hover:text-foreground hover:bg-primary/[0.06]'
                          }`}
                        >
                          <ImageIcon className="w-3.5 h-3.5" />
                          Infographic
                        </button>
                      </div>
                    )}

                    {/* Single heading when only one exists */}
                    {report.has_slide_deck && !report.has_infographic && (
                      <SectionHeading icon={<Presentation className="w-3.5 h-3.5" />} className="mb-4">
                        Strategy Slide Deck
                      </SectionHeading>
                    )}
                    {!report.has_slide_deck && report.has_infographic && (
                      <SectionHeading icon={<ImageIcon className="w-3.5 h-3.5" />} className="mb-4">
                        Market Analysis Infographic
                      </SectionHeading>
                    )}

                    {/* Media content with crossfade on view toggle */}
                    <AnimatePresence mode="wait">
                    {/* Slide Deck view */}
                    {((report.has_slide_deck && report.has_infographic && mediaView === 'slides') ||
                      (report.has_slide_deck && !report.has_infographic)) && (
                      <motion.div
                        key="slides"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2 }}
                      >
                        <SlideDeckViewer pdfUrl={slideDeckUrl} date={report.date} />
                      </motion.div>
                    )}

                    {/* Infographic view */}
                    {((report.has_slide_deck && report.has_infographic && mediaView === 'infographic') ||
                      (!report.has_slide_deck && report.has_infographic)) && (
                      <motion.div
                        key="infographic"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="group relative rounded-[var(--radius)] border border-border/50 overflow-hidden bg-primary/[0.03] cursor-zoom-in"
                        onClick={() => setLightboxOpen(true)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            setLightboxOpen(true);
                          }
                        }}
                        aria-label="Click to enlarge infographic"
                      >
                        {/* Skeleton shown while image loads */}
                        {!infographicLoaded && (
                          <div className="absolute inset-0 z-[1] bg-primary/[0.03] overflow-hidden">
                            <div className="absolute inset-0 -translate-x-full animate-[shimmer_1.6s_ease-in-out_infinite] bg-gradient-to-r from-transparent via-foreground/[0.04] to-transparent" />
                            <div className="flex items-center justify-center h-full min-h-[200px]">
                              <ImageIcon className="w-8 h-8 text-muted-foreground/15" />
                            </div>
                          </div>
                        )}
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={infographicSrc}
                          alt={`Macro infographic for ${selectedDate}`}
                          className={`w-full h-auto transition-opacity duration-300 ${infographicLoaded ? 'opacity-100' : 'opacity-0'}`}
                          loading="lazy"
                          onLoad={() => setInfographicLoaded(true)}
                        />
                        <div className="absolute inset-0 flex items-center justify-center bg-foreground/0 group-hover:bg-primary/[0.06] transition-colors">
                          <div className="opacity-0 group-hover:opacity-100 transition-opacity bg-background/80 backdrop-blur-sm border border-border/50 rounded-lg px-3 py-1.5 flex items-center gap-1.5 text-[11px] text-muted-foreground shadow-lg">
                            <ZoomIn className="w-3.5 h-3.5" />
                            Click to enlarge
                          </div>
                        </div>
                      </motion.div>
                    )}
                    </AnimatePresence>
                  </div>
                )}

                {/* Right: Executive Takeaways */}
                {takeaways.length > 0 && (
                  <div className="lg:w-[40%] shrink-0 flex flex-col">
                    <SectionHeading icon={<Zap className="w-3.5 h-3.5" />} className="mb-4">
                      Executive Takeaways
                      <span className="ml-1.5 text-[9px] font-mono text-muted-foreground/40">{takeaways.length}</span>
                    </SectionHeading>
                    <div className="space-y-2.5 lg:max-h-[480px] lg:overflow-y-auto no-scrollbar">
                      {takeaways.map((t, i) => (
                        <div key={i} className="relative rounded-lg border border-primary/20 bg-primary/[0.03] overflow-hidden">
                          <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary/60 rounded-l-xl" />
                          <div className="pl-4 pr-3 py-3">
                            <h4 className="text-[12px] font-semibold text-foreground leading-snug mb-1">
                              {t.title}
                            </h4>
                            <p className="text-[11px] text-muted-foreground/80 leading-relaxed">{t.body}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </section>
            )}

            {/* ── Risk Scorecard ─────────────────────────────────────────── */}
            {riskItems.length > 0 && (
              <section>
                <SectionHeading icon={<Shield className="w-3.5 h-3.5" />} className="mb-4">
                  Risk Scorecard
                </SectionHeading>

                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                  {riskItems.map((r, i) => (
                    <div key={i} className={`group relative rounded-lg border px-3.5 py-3 ${scoreBgClass(r.score)} ${scoreBorderClass(r.score)}`}>
                      <div className="flex items-center gap-1.5 mb-2">
                        <AlertTriangle className={`w-3 h-3 ${scoreColor(r.score)}`} />
                        <span className="text-[11px] font-semibold text-foreground truncate flex-1">{r.category}</span>
                        {r.description && (
                          <span className="relative shrink-0">
                            <Info className="w-3 h-3 text-muted-foreground/40 hover:text-muted-foreground/80 transition-colors cursor-help" />
                            <span className="pointer-events-none opacity-0 group-hover:pointer-events-auto group-hover:opacity-100 transition-opacity duration-150 absolute right-0 top-full mt-1.5 z-50 w-[280px] max-h-[200px] overflow-y-auto rounded-md border border-border/60 bg-card shadow-lg px-3 py-2.5">
                              <span className="block text-[11px] text-muted-foreground/80 leading-relaxed whitespace-normal">{r.description}</span>
                              {r.experts && (
                                <span className="block mt-1.5 text-[10px] font-mono text-muted-foreground/40">{r.experts}</span>
                              )}
                            </span>
                          </span>
                        )}
                      </div>
                      <ScoreBar score={r.score} />
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* ── Full Briefing ──────────────────────────────────────────── */}
            {briefingSections.length > 0 && (
              <section>
                <SectionHeading icon={<FileText className="w-3.5 h-3.5" />} className="mb-4">
                  Full Briefing
                </SectionHeading>
                <div className="space-y-3">
                  {briefingSections.map((s, i) => {
                    const isExpanded = expandedBriefing[i] ?? false;
                    const preview = s.body.substring(0, 400);
                    const needsTruncate = s.body.length > 400;
                    return (
                      <article key={i} className="rounded-[var(--radius)] border border-border/40 bg-primary/[0.02] overflow-hidden">
                        <button
                          onClick={() => toggleBriefingSection(i)}
                          className="flex items-center justify-between w-full text-left gap-3 px-4 py-3 hover:bg-primary/[0.04] transition-colors"
                        >
                          <h4 className="text-[13px] font-semibold text-foreground leading-snug">{s.title}</h4>
                          {needsTruncate && (
                            <span className="shrink-0 text-muted-foreground/40">
                              {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                            </span>
                          )}
                        </button>
                        <div className="px-4 pb-4">
                          <p className="text-sm text-muted-foreground/80 leading-[1.75]">
                            {isExpanded || !needsTruncate ? s.body : `${preview}...`}
                          </p>
                          {needsTruncate && !isExpanded && (
                            <button
                              onClick={() => toggleBriefingSection(i)}
                              className="mt-2 text-[11px] font-medium text-muted-foreground/50 hover:text-muted-foreground transition-colors"
                            >
                              Read more
                            </button>
                          )}
                        </div>
                      </article>
                    );
                  })}
                </div>
              </section>
            )}

            {/* ── Sources ────────────────────────────────────────────────── */}
            {(videoSources.length > 0 || driveSources.length > 0 || Object.values(sourceCounts).some(v => v && v > 0)) && (
              <section className="pt-2 border-t border-border/25">
                <details
                  className="group"
                  open={showSources}
                  onToggle={(e) => setShowSources((e.target as HTMLDetailsElement).open)}
                >
                  <summary className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-muted-foreground/40 font-mono cursor-pointer hover:text-muted-foreground/60 transition-colors list-none select-none py-1">
                    <ExternalLink className="w-3 h-3" />
                    Sources
                    <span className="ml-auto">
                      {showSources ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                    </span>
                  </summary>

                  <div className="mt-3 space-y-4">
                    {/* Source counts summary */}
                    {Object.values(sourceCounts).some(v => v && v > 0) && (
                      <div className="flex flex-wrap gap-2">
                        {(sourceCounts.youtube ?? 0) > 0 && (
                          <span className="inline-flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground/60 bg-primary/[0.04] border border-border/30 rounded-md px-2 py-1">
                            <Youtube className="w-3 h-3 text-rose-400/50" />
                            {sourceCounts.youtube} videos
                          </span>
                        )}
                        {(sourceCounts.drive ?? 0) > 0 && (
                          <span className="inline-flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground/60 bg-primary/[0.04] border border-border/30 rounded-md px-2 py-1">
                            <FileText className="w-3 h-3 text-primary/50" />
                            {sourceCounts.drive} PDFs
                          </span>
                        )}
                        {(sourceCounts.news ?? 0) > 0 && (
                          <span className="inline-flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground/60 bg-primary/[0.04] border border-border/30 rounded-md px-2 py-1">
                            <Rss className="w-3 h-3 text-amber-400/50" />
                            {sourceCounts.news} news feeds
                          </span>
                        )}
                        {(sourceCounts.telegram ?? 0) > 0 && (
                          <span className="inline-flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground/60 bg-primary/[0.04] border border-border/30 rounded-md px-2 py-1">
                            <MessageSquare className="w-3 h-3 text-sky-400/50" />
                            {sourceCounts.telegram} messages
                          </span>
                        )}
                        {(sourceCounts.central_banks ?? 0) > 0 && (
                          <span className="inline-flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground/60 bg-primary/[0.04] border border-border/30 rounded-md px-2 py-1">
                            <Building2 className="w-3 h-3 text-emerald-400/50" />
                            {sourceCounts.central_banks} central bank docs
                          </span>
                        )}
                        {(sourceCounts.macro_data ?? 0) > 0 && (
                          <span className="inline-flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground/60 bg-primary/[0.04] border border-border/30 rounded-md px-2 py-1">
                            <BarChart3 className="w-3 h-3 text-violet-400/50" />
                            {sourceCounts.macro_data} indicators
                          </span>
                        )}
                        {(sourceCounts.reports ?? 0) > 0 && (
                          <span className="inline-flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground/60 bg-primary/[0.04] border border-border/30 rounded-md px-2 py-1">
                            <Globe className="w-3 h-3 text-primary/50" />
                            {sourceCounts.reports} research reports
                          </span>
                        )}
                      </div>
                    )}

                    {videoSources.length > 0 && (
                      <div>
                        <h4 className="text-[10px] uppercase tracking-wider text-muted-foreground/50 font-mono mb-2">
                          YouTube ({videoSources.length})
                        </h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5">
                          {videoSources.map((v) => (
                            <a
                              key={v.id}
                              href={v.url}
                              target="_blank"
                              rel="noreferrer"
                              className="flex items-start gap-2.5 px-3 py-2 rounded-lg hover:bg-primary/[0.04] transition-colors group/link"
                            >
                              <Youtube className="w-3.5 h-3.5 mt-0.5 text-rose-400/40 shrink-0" />
                              <div className="min-w-0 flex-1">
                                <p className="text-[12px] text-foreground leading-snug truncate group-hover/link:text-primary transition-colors">
                                  {v.title}
                                </p>
                                <p className="text-[10px] text-muted-foreground/45 font-mono mt-0.5">
                                  {v.channel}
                                  {v.duration ? ` \u00B7 ${v.duration}` : ''}
                                  {v.views ? ` \u00B7 ${v.views.toLocaleString()} views` : ''}
                                </p>
                              </div>
                            </a>
                          ))}
                        </div>
                      </div>
                    )}

                    {driveSources.length > 0 && (
                      <div>
                        <h4 className="text-[10px] uppercase tracking-wider text-muted-foreground/50 font-mono mb-2">
                          Research Papers ({driveSources.length})
                        </h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5">
                          {driveSources.map((d, i) => (
                            <a
                              key={i}
                              href={d.url}
                              target="_blank"
                              rel="noreferrer"
                              className="flex items-start gap-2.5 px-3 py-2 rounded-lg hover:bg-primary/[0.04] transition-colors group/link"
                            >
                              <FileText className="w-3.5 h-3.5 mt-0.5 text-primary/40 shrink-0" />
                              <p className="text-[12px] text-foreground leading-snug truncate group-hover/link:text-primary transition-colors">
                                {d.title}
                              </p>
                            </a>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </details>
              </section>
            )}
          </div>
        ) : null}
      </div>

      {/* ── Infographic lightbox ──────────────────────────────────────────── */}
      {lightboxOpen && selectedDate && (
        <InfographicLightbox
          src={infographicSrc}
          alt={`Macro infographic for ${selectedDate}`}
          onClose={() => setLightboxOpen(false)}
        />
      )}
    </section>
  );
}
