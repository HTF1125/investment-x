'use client';

import React, { Suspense, useState, useEffect, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { AnimatePresence, motion } from 'framer-motion';
import { Loader2, Plus, Play, ArrowRight, AlertTriangle } from 'lucide-react';
import { apiFetchJson } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import PresentationSlideRenderer from '@/components/reports/PresentationSlideRenderer';
import { SAMPLE_SLIDES } from '@/components/reports/sampleSlides';
import { migrateSlide } from '@/components/reports/slideTypes';
import type { TemplateSlide } from '@/components/reports/slideTypes';

// ── Presentation content ──

function PresentationContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const reportId = searchParams.get('report');
  const { user } = useAuth();

  const [currentIndex, setCurrentIndex] = useState(0);
  const [dims, setDims] = useState({ w: 1280, h: 720 });
  const [creating, setCreating] = useState(false);

  const handleCreateReport = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!user) { router.push('/login'); return; }
    setCreating(true);
    try {
      const report = await apiFetchJson<{ id: string }>('/api/reports', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'Untitled Report', slides: [] }),
      });
      router.push(`/reports?report=${report.id}`);
    } catch {
      router.push('/reports');
    }
  };

  // Fetch report if ID provided
  const { data: report, isLoading: reportLoading, isError: reportError } = useQuery({
    queryKey: ['report', reportId],
    queryFn: () => apiFetchJson<{ slides: any[] }>(`/api/reports/${reportId}`),
    enabled: !!reportId,
    staleTime: 60_000,
  });

  // Resolve slides: from report or sample
  const slides: TemplateSlide[] = reportId && report?.slides
    ? report.slides.map(migrateSlide)
    : SAMPLE_SLIDES;

  // 16:9 aspect ratio from viewport
  useEffect(() => {
    const update = () => {
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const ratio = 16 / 9;
      if (vw / vh > ratio) {
        setDims({ w: vh * ratio, h: vh });
      } else {
        setDims({ w: vw, h: vw / ratio });
      }
    };
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);

  // Keyboard navigation
  const next = useCallback(() => {
    setCurrentIndex(i => Math.min(i + 1, slides.length - 1));
  }, [slides.length]);

  const prev = useCallback(() => {
    setCurrentIndex(i => Math.max(i - 1, 0));
  }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowRight':
        case 'ArrowDown':
        case ' ':
          e.preventDefault();
          next();
          break;
        case 'ArrowLeft':
        case 'ArrowUp':
          e.preventDefault();
          prev();
          break;
        case 'Escape':
          e.preventDefault();
          router.back();
          break;
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [next, prev, router]);

  // Reset index when slides change
  useEffect(() => {
    setCurrentIndex(0);
  }, [reportId]);

  // Loading state for report fetch
  if (reportId && reportLoading) {
    return (
      <div className="fixed inset-0 bg-background flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 animate-fade-in">
          <Loader2 className="w-5 h-5 animate-spin text-primary/40" />
          <span className="stat-label text-muted-foreground/40">Loading presentation</span>
        </div>
      </div>
    );
  }

  // Error state for report fetch
  if (reportId && reportError) {
    return (
      <div className="fixed inset-0 bg-background flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-center max-w-xs animate-fade-in">
          <div className="w-10 h-10 rounded-[var(--radius)] bg-destructive/10 border border-destructive/20 flex items-center justify-center">
            <AlertTriangle className="w-4.5 h-4.5 text-destructive" />
          </div>
          <p className="text-[13px] font-medium text-foreground">Failed to load presentation</p>
          <p className="text-[12px] text-muted-foreground">This report may not exist or you may not have access.</p>
        </div>
      </div>
    );
  }

  if (slides.length === 0) {
    return (
      <div className="fixed inset-0 bg-background flex items-center justify-center">
        <p className="text-foreground/20 font-mono text-[13px]">No slides</p>
      </div>
    );
  }

  const progress = ((currentIndex + 1) / slides.length) * 100;

  return (
    <div
      className="fixed inset-0 bg-background overflow-hidden cursor-pointer select-none"
      onClick={next}
    >
      {/* Slide viewport — centered 16:9 */}
      <div className="w-screen h-screen flex items-center justify-center">
        <div
          style={{ width: dims.w, height: dims.h }}
          className="relative overflow-hidden"
        >
          <AnimatePresence mode="wait">
            <motion.div
              key={currentIndex}
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -30 }}
              transition={{ duration: 0.22, ease: 'easeInOut' }}
              className="absolute inset-0"
            >
              <PresentationSlideRenderer slide={slides[currentIndex]} />
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      {/* Progress bar */}
      <div
        data-testid="progress-bar"
        className="fixed bottom-0 left-0 right-0 h-[3px] bg-foreground/5"
      >
        <div
          className="h-full bg-primary transition-all duration-300 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Slide counter */}
      <div className="fixed bottom-3 right-4 font-mono text-[12.5px] text-foreground/20 pointer-events-none">
        {currentIndex + 1} / {slides.length}
      </div>

      {/* Keyboard hint (first slide only, fades out) */}
      {currentIndex === 0 && !reportId && (
        <motion.div
          initial={{ opacity: 0.6 }}
          animate={{ opacity: 0 }}
          transition={{ delay: 4, duration: 1.5 }}
          className="fixed bottom-3 left-4 font-mono text-[11.5px] text-foreground/15 pointer-events-none"
        >
          Arrow keys or click to navigate &middot; ESC to exit
        </motion.div>
      )}

      {/* Demo badge — top right corner */}
      {!reportId && (
        <div className="fixed top-4 right-4 flex items-center gap-3 pointer-events-auto z-10">
          <span className="text-[11.5px] font-mono text-foreground/15 uppercase tracking-wider">Demo</span>
          <button
            onClick={handleCreateReport}
            disabled={creating}
            className="text-[11.5px] font-medium text-primary/60 hover:text-primary bg-foreground/[0.04] hover:bg-foreground/[0.08] border border-foreground/[0.06] rounded-[var(--radius)] px-2.5 py-1 transition-all flex items-center gap-1.5"
          >
            {creating ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
            Create your own
          </button>
        </div>
      )}

      {/* End-of-deck CTA — shown on last slide of demo */}
      {!reportId && currentIndex === slides.length - 1 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1, duration: 0.4 }}
          className="fixed bottom-12 left-1/2 -translate-x-1/2 pointer-events-auto z-10"
        >
          <button
            onClick={handleCreateReport}
            disabled={creating}
            className="flex items-center gap-2 px-5 py-2.5 rounded-[var(--radius)] bg-primary hover:bg-primary/90 text-primary-foreground text-[13px] font-semibold transition-all shadow-lg shadow-primary/20"
          >
            {creating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            Create your own report
            <ArrowRight className="w-3.5 h-3.5 ml-1 opacity-60" />
          </button>
        </motion.div>
      )}
    </div>
  );
}

// ── Page wrapper ──

export default function PresentPage() {
  return (
    <Suspense
      fallback={
        <div className="fixed inset-0 bg-background flex items-center justify-center">
          <div className="flex flex-col items-center gap-3 animate-fade-in">
            <Loader2 className="w-5 h-5 animate-spin text-primary/40" />
            <span className="stat-label text-muted-foreground/40">Loading presentation</span>
          </div>
        </div>
      }
    >
      <PresentationContent />
    </Suspense>
  );
}
