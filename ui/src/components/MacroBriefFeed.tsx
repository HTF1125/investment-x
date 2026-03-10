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
  Youtube,
  FileText,
  X,
  ZoomIn,
  Calendar,
  Presentation,
  Download,
} from 'lucide-react';

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

export interface ReportData {
  date: string;
  briefing: string | null;
  risk_scorecard: string | null;
  takeaways: string | null;
  sources: {
    selected_videos?: VideoSource[];
    drive_files?: DriveSource[];
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
  const blockRegex = /\*\*([^:*]+):\s*(\d+)\/10\*\*\s*\n\*\*Key Expert[s]?:\*\*\s*(.+?)\n\*\*Why:\*\*\s*([\s\S]*?)(?=\n\n\*\*[A-Z]|\nResumed conversation:|$)/g;
  let match;
  while ((match = blockRegex.exec(md)) !== null) {
    items.push({
      category: match[1].trim(),
      score: parseInt(match[2], 10),
      experts: match[3].trim(),
      description: match[4].trim().replace(/\s*\[\d+[-,\s\d]*\]/g, ''),
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
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [pdfDoc, setPdfDoc] = useState<any>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const renderingRef = useRef(false);

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
  }, [pdfDoc, currentPage]);

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
      <div className="flex items-center justify-center py-16 text-muted-foreground text-sm animate-pulse">
        Loading slide deck...
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
      <div className="relative rounded-[var(--radius)] border border-border/50 overflow-hidden bg-primary/[0.03]">
        <canvas ref={canvasRef} className="w-full block" />

        {/* Left/right click zones */}
        {totalPages > 1 && (
          <>
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="absolute left-0 top-0 bottom-0 w-1/4 cursor-w-resize group"
              aria-label="Previous slide"
            >
              <div className="absolute left-3 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-background/80 backdrop-blur-sm border border-border/50 rounded-lg p-2 shadow-lg">
                <ChevronLeft className="w-5 h-5 text-foreground" />
              </div>
            </button>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="absolute right-0 top-0 bottom-0 w-1/4 cursor-e-resize group"
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

  const toggleBriefingSection = useCallback(
    (i: number) => setExpandedBriefing((prev) => ({ ...prev, [i]: !prev[i] })),
    [],
  );

  /* ── Loading / Error / Empty ──────────────────────────────────────────── */

  if (datesLoading) {
    return (
      <div role="status" aria-live="polite" className="h-32 animate-pulse flex items-center justify-center text-muted-foreground text-sm">
        Loading research reports...
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
          <div className="flex items-center justify-center py-20 text-muted-foreground text-sm animate-pulse">
            Loading report...
          </div>
        ) : reportError ? (
          <div className="flex items-center justify-center py-20 text-muted-foreground text-sm">
            <WifiOff className="w-4 h-4 mr-2 text-rose-400/50" />
            Failed to load report
          </div>
        ) : report ? (
          <div className="px-5 md:px-8 py-6 space-y-10 max-w-[1600px] mx-auto">

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

                    {/* Slide Deck view */}
                    {((report.has_slide_deck && report.has_infographic && mediaView === 'slides') ||
                      (report.has_slide_deck && !report.has_infographic)) && (
                      <SlideDeckViewer pdfUrl={slideDeckUrl} date={report.date} />
                    )}

                    {/* Infographic view */}
                    {((report.has_slide_deck && report.has_infographic && mediaView === 'infographic') ||
                      (!report.has_slide_deck && report.has_infographic)) && (
                      <div
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
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={infographicSrc}
                          alt={`Macro infographic for ${selectedDate}`}
                          className="w-full h-auto"
                          loading="lazy"
                        />
                        <div className="absolute inset-0 flex items-center justify-center bg-foreground/0 group-hover:bg-primary/[0.06] transition-colors">
                          <div className="opacity-0 group-hover:opacity-100 transition-opacity bg-background/80 backdrop-blur-sm border border-border/50 rounded-lg px-3 py-1.5 flex items-center gap-1.5 text-[11px] text-muted-foreground shadow-lg">
                            <ZoomIn className="w-3.5 h-3.5" />
                            Click to enlarge
                          </div>
                        </div>
                      </div>
                    )}
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

                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 mb-5">
                  {riskItems.map((r, i) => (
                    <div key={i} className={`rounded-lg border px-3.5 py-3 ${scoreBgClass(r.score)} ${scoreBorderClass(r.score)}`}>
                      <div className="flex items-center gap-1.5 mb-2">
                        <AlertTriangle className={`w-3 h-3 ${scoreColor(r.score)}`} />
                        <span className="text-[11px] font-semibold text-foreground truncate">{r.category}</span>
                      </div>
                      <ScoreBar score={r.score} />
                    </div>
                  ))}
                </div>

                <div className="space-y-3">
                  {riskItems.map((r, i) => (
                    <div key={i} className="rounded-[var(--radius)] border border-border/40 bg-primary/[0.02] overflow-hidden">
                      <div className="px-4 py-3 border-b border-border/25 flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                          <span className={`text-[13px] font-semibold ${scoreColor(r.score)}`}>{r.category}</span>
                          <span className={`text-[11px] font-mono font-bold tabular-nums ${scoreColor(r.score)}`}>{r.score}/10</span>
                        </div>
                        <span className="text-[10px] text-muted-foreground/50 font-mono">{r.experts}</span>
                      </div>
                      <div className="px-4 py-3">
                        <p className="text-sm text-muted-foreground/80 leading-relaxed">{r.description}</p>
                      </div>
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
            {(videoSources.length > 0 || driveSources.length > 0) && (
              <section className="pt-2 border-t border-border/25">
                <details
                  className="group"
                  open={showSources}
                  onToggle={(e) => setShowSources((e.target as HTMLDetailsElement).open)}
                >
                  <summary className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-muted-foreground/40 font-mono cursor-pointer hover:text-muted-foreground/60 transition-colors list-none select-none py-1">
                    <ExternalLink className="w-3 h-3" />
                    Sources ({videoSources.length + driveSources.length})
                    <span className="ml-auto">
                      {showSources ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                    </span>
                  </summary>

                  <div className="mt-3 space-y-4">
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
