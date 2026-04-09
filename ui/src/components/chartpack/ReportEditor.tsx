import React, { useState, useCallback, useRef, useEffect } from 'react';
import { motion, AnimatePresence, Reorder } from 'framer-motion';
import dynamic from 'next/dynamic';
import {
  X, Loader2, FileText, Presentation, Trash2, GripVertical,
  ChevronLeft, Download,
} from 'lucide-react';
import { applyChartTheme } from '@/lib/chartTheme';
// Export uses relative URLs through Next.js proxy
import type { FlashMessage } from './types';

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center">
      <Loader2 className="w-4 h-4 animate-spin text-primary/30" />
    </div>
  ),
}) as any;

// ── Types ──

export interface Slide {
  id: string;
  title: string;
  narrative: string;
  figure: any;
  packName: string;
}

interface Props {
  initialSlides: Slide[];
  isLight: boolean;
  onClose: () => void;
  onFlash: (msg: FlashMessage) => void;
}

// ── Auto-resize textarea hook ──

function useAutoResize(value: string) {
  const ref = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  }, [value]);
  return ref;
}

// ── Slide thumbnail ──

function SlideThumbnail({ slide, index, isActive, onClick }: {
  slide: Slide;
  index: number;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <Reorder.Item
      key={slide.id}
      value={slide}
      as="div"
      className={`relative rounded-[var(--radius)] border cursor-pointer transition-all group ${
        isActive
          ? 'border-primary/40 bg-primary/[0.06] ring-1 ring-primary/20'
          : 'border-border/30 bg-card hover:border-border/50'
      }`}
      onClick={onClick}
      whileDrag={{ scale: 1.02, boxShadow: '0 4px 12px rgba(0,0,0,0.15)' }}
    >
      {/* Drag handle */}
      <div className="absolute top-1 left-1 opacity-0 group-hover:opacity-100 transition-opacity z-10">
        <GripVertical className="w-3 h-3 text-muted-foreground/30" />
      </div>

      {/* Slide number */}
      <div className="absolute top-1 right-1.5 z-10">
        <span className="text-[11px] font-mono font-bold text-muted-foreground/40 tabular-nums">
          {index + 1}
        </span>
      </div>

      {/* Mini preview */}
      <div className="h-[72px] overflow-hidden rounded-t-[calc(var(--radius)-1px)] bg-background/50">
        <div className="w-full h-full flex items-center justify-center">
          <FileText className="w-5 h-5 text-muted-foreground/10" />
        </div>
      </div>

      {/* Title */}
      <div className="px-2 py-1.5 border-t border-border/20">
        <p className="text-[11px] font-medium text-foreground truncate leading-tight">
          {slide.title || `Slide ${index + 1}`}
        </p>
        <p className="text-[9.5px] text-muted-foreground/30 truncate mt-0.5">
          {slide.packName}
        </p>
      </div>
    </Reorder.Item>
  );
}

// ── Main editor ──

export default function ReportEditor({ initialSlides, isLight, onClose, onFlash }: Props) {
  const [slides, setSlides] = useState<Slide[]>(initialSlides);
  const [activeIndex, setActiveIndex] = useState(0);
  const [exporting, setExporting] = useState<'pptx' | 'pdf' | null>(null);
  const [reportTitle, setReportTitle] = useState('Investment-X Report');

  const activeSlide = slides[activeIndex] ?? null;
  const uiTheme = isLight ? 'light' : 'dark';

  const updateSlide = useCallback((index: number, updates: Partial<Slide>) => {
    setSlides(prev => prev.map((s, i) => i === index ? { ...s, ...updates } : s));
  }, []);

  const removeSlide = useCallback((index: number) => {
    setSlides(prev => {
      const next = prev.filter((_, i) => i !== index);
      if (next.length === 0) return next;
      return next;
    });
    setActiveIndex(prev => Math.min(prev, Math.max(0, slides.length - 2)));
  }, [slides.length]);

  const handleReorder = useCallback((newOrder: Slide[]) => {
    const activeId = slides[activeIndex]?.id;
    setSlides(newOrder);
    if (activeId) {
      const newIdx = newOrder.findIndex(s => s.id === activeId);
      if (newIdx >= 0) setActiveIndex(newIdx);
    }
  }, [slides, activeIndex]);

  // ── Export handlers ──

  const handleExport = async (format: 'pptx' | 'pdf') => {
    if (exporting || slides.length === 0) return;
    setExporting(format);
    try {
      const url = format === 'pptx'
        ? '/api/chart-packs/report/pptx'
        : '/api/chart-packs/report/pdf';

      const body = JSON.stringify({
        slides: slides.map(s => ({
          title: s.title,
          narrative: s.narrative,
          figure: s.figure,
        })),
        theme: 'light',
        report_title: reportTitle,
      });

      const res = await fetch(url, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail || `${format.toUpperCase()} export failed`);
      }
      const blob = await res.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      const ext = format === 'pptx' ? 'pptx' : 'pdf';
      a.download = `InvestmentX_Report_${new Date().toISOString().slice(0, 10)}.${ext}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(blobUrl);
      onFlash({ type: 'success', text: `${format.toUpperCase()} downloaded` });
    } catch (err: any) {
      onFlash({ type: 'error', text: err?.message || 'Export failed' });
    } finally {
      setExporting(null);
    }
  };

  // ── Chart figure with theme ──
  const themedFigure = activeSlide?.figure
    ? applyChartTheme(activeSlide.figure, uiTheme, { transparentBackground: false })
    : null;

  const narrativeRef = useAutoResize(activeSlide?.narrative || '');

  const formStyle = {
    colorScheme: isLight ? 'light' as const : 'dark' as const,
    backgroundColor: 'rgb(var(--background))',
    color: 'rgb(var(--foreground))',
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-background flex flex-col"
    >
      {/* ── Top bar ── */}
      <div className="shrink-0 h-11 flex items-center px-4 gap-3 border-b border-border/30">
        <button
          onClick={onClose}
          className="flex items-center gap-1 text-[12.5px] font-medium text-muted-foreground/40 hover:text-foreground transition-colors -ml-1"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
          <span>Back</span>
        </button>

        <div className="w-px h-5 bg-border/20" />

        {/* Report title (editable) */}
        <input
          type="text"
          value={reportTitle}
          onChange={e => setReportTitle(e.target.value)}
          className="text-[13px] font-semibold text-foreground bg-transparent border-none outline-none flex-1 min-w-0 placeholder:text-muted-foreground/20"
          placeholder="Report title..."
          style={formStyle}
        />

        <div className="flex items-center gap-1.5 shrink-0">
          {/* Slide count */}
          <span className="text-[11.5px] font-mono text-muted-foreground/30 tabular-nums">
            {slides.length} slides
          </span>

          <div className="w-px h-4 bg-border/15" />

          {/* Export buttons */}
          <button
            onClick={() => handleExport('pdf')}
            disabled={!!exporting || slides.length === 0}
            className="btn-toolbar"
            title="Export as PDF"
          >
            {exporting === 'pdf' ? <Loader2 className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />}
            <span>PDF</span>
          </button>
          <button
            onClick={() => handleExport('pptx')}
            disabled={!!exporting || slides.length === 0}
            className="btn-primary"
            title="Export as PowerPoint"
          >
            {exporting === 'pptx' ? <Loader2 className="w-3 h-3 animate-spin" /> : <Presentation className="w-3 h-3" />}
            <span>PPTX</span>
          </button>
        </div>
      </div>

      {/* ── Main area ── */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar — slide thumbnails */}
        <div className="w-[140px] shrink-0 border-r border-border/20 overflow-y-auto no-scrollbar p-2 space-y-1.5 bg-card/50">
          <Reorder.Group
            axis="y"
            values={slides}
            onReorder={handleReorder}
            as="div"
            className="space-y-1.5"
          >
            {slides.map((slide, i) => (
              <SlideThumbnail
                key={slide.id}
                slide={slide}
                index={i}
                isActive={i === activeIndex}
                onClick={() => setActiveIndex(i)}
              />
            ))}
          </Reorder.Group>

          {slides.length === 0 && (
            <div className="text-center py-8">
              <p className="text-[11.5px] text-muted-foreground/30">No slides</p>
            </div>
          )}
        </div>

        {/* Main content — active slide */}
        <div className="flex-1 overflow-y-auto no-scrollbar">
          {activeSlide ? (
            <div className="p-4 space-y-4 max-w-[1400px] mx-auto">
              {/* Chart preview */}
              <div className="rounded-[var(--radius)] border border-border/30 bg-card overflow-hidden">
                <div className="aspect-[16/9] relative">
                  {themedFigure ? (
                    <Plot
                      data={themedFigure.data || []}
                      layout={{
                        ...(themedFigure.layout || {}),
                        autosize: true,
                        margin: { l: 60, r: 40, t: 40, b: 50 },
                      }}
                      config={{
                        responsive: true,
                        displayModeBar: false,
                        staticPlot: false,
                      }}
                      style={{ width: '100%', height: '100%' }}
                      useResizeHandler
                    />
                  ) : (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <FileText className="w-8 h-8 text-muted-foreground/10" />
                    </div>
                  )}
                </div>
              </div>

              {/* Slide metadata */}
              <div className="flex items-start gap-4">
                <div className="flex-1 space-y-3">
                  {/* Title */}
                  <div>
                    <label className="stat-label block mb-1">Slide Title</label>
                    <input
                      type="text"
                      value={activeSlide.title}
                      onChange={e => updateSlide(activeIndex, { title: e.target.value })}
                      className="w-full h-9 px-3 text-[14px] font-semibold border border-border/50 rounded-[var(--radius)] focus:outline-none focus:ring-2 focus:ring-primary/25 text-foreground bg-transparent"
                      placeholder="Chart title..."
                      style={formStyle}
                    />
                  </div>

                  {/* Narrative */}
                  <div>
                    <label className="stat-label block mb-1">Commentary</label>
                    <textarea
                      ref={narrativeRef}
                      value={activeSlide.narrative}
                      onChange={e => updateSlide(activeIndex, { narrative: e.target.value })}
                      className="w-full px-3 py-2.5 text-[13px] font-mono leading-relaxed border border-border/50 rounded-[var(--radius)] focus:outline-none focus:ring-2 focus:ring-primary/25 resize-none text-foreground bg-transparent min-h-[80px]"
                      placeholder="Add commentary for this slide..."
                      style={formStyle}
                    />
                  </div>

                  {/* Pack origin */}
                  <div className="flex items-center gap-2">
                    <span className="text-[11.5px] font-mono text-muted-foreground/25">
                      Source: {activeSlide.packName}
                    </span>
                    <span className="text-[11.5px] font-mono text-muted-foreground/20 tabular-nums">
                      Slide {activeIndex + 1} of {slides.length}
                    </span>
                  </div>
                </div>

                {/* Delete slide */}
                <button
                  onClick={() => removeSlide(activeIndex)}
                  className="btn-icon text-muted-foreground/20 hover:text-destructive hover:bg-destructive/10 mt-5"
                  title="Remove slide"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center h-full">
              <div className="text-center">
                <Presentation className="w-10 h-10 text-muted-foreground/10 mx-auto mb-3" />
                <p className="text-[13px] text-muted-foreground/30">No slides in this report</p>
                <button onClick={onClose} className="btn-toolbar mt-4">
                  Back to packs
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Exporting overlay */}
      <AnimatePresence>
        {exporting && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[60] bg-black/40 flex items-center justify-center"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="rounded-[var(--radius)] border border-border/40 bg-card shadow-lg px-8 py-6 text-center"
            >
              <Loader2 className="w-6 h-6 animate-spin text-primary mx-auto mb-3" />
              <p className="text-[13px] font-medium text-foreground">
                Generating {exporting.toUpperCase()}...
              </p>
              <p className="text-[12.5px] text-muted-foreground/40 mt-1">
                Rendering {slides.length} charts may take a minute
              </p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
