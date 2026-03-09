'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { apiFetch } from '@/lib/api';

const PDFJS_VERSION = '3.11.174';
const PDFJS_CDN = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${PDFJS_VERSION}/build`;
const SWIPE_THRESHOLD = 50;

const variants = {
  enter: (dir: number) => ({ x: dir > 0 ? '60%' : '-60%', opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (dir: number) => ({ x: dir > 0 ? '-60%' : '60%', opacity: 0 }),
};

// Load pdf.js from CDN (avoids webpack bundling issues)
let pdfjsLoadPromise: Promise<any> | null = null;
function loadPdfJs(): Promise<any> {
  if (pdfjsLoadPromise) return pdfjsLoadPromise;
  pdfjsLoadPromise = new Promise((resolve, reject) => {
    if ((window as any).pdfjsLib) {
      resolve((window as any).pdfjsLib);
      return;
    }
    const legacyScript = document.createElement('script');
    legacyScript.src = `${PDFJS_CDN}/pdf.min.js`;
    legacyScript.onload = () => {
      const lib = (window as any).pdfjsLib;
      if (lib) {
        lib.GlobalWorkerOptions.workerSrc = `${PDFJS_CDN}/pdf.worker.min.js`;
        resolve(lib);
      } else {
        reject(new Error('pdfjsLib not found after script load'));
      }
    };
    legacyScript.onerror = () => reject(new Error('Failed to load pdf.js'));
    document.head.appendChild(legacyScript);
  });
  return pdfjsLoadPromise;
}

interface Props {
  src: string;
}

export default function SlideDeckViewer({ src }: Props) {
  const [pageImages, setPageImages] = useState<string[]>([]);
  const [page, setPage] = useState(0);
  const [direction, setDirection] = useState(0);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState('');
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const touchStartX = useRef(0);
  const touchDeltaX = useRef(0);

  const numPages = pageImages.length;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setPage(0);
    setPageImages([]);
    setProgress('Loading PDF library...');

    (async () => {
      try {
        const pdfjsLib = await loadPdfJs();
        if (cancelled) return;

        setProgress('Fetching slides...');
        const res = await apiFetch(src, { timeoutMs: 60000 });
        if (!res.ok) throw new Error(`Failed to load slides (${res.status})`);
        const data = await res.arrayBuffer();
        if (cancelled) return;

        setProgress('Rendering pages...');
        const pdf = await pdfjsLib.getDocument({ data }).promise;
        if (cancelled) return;

        const images: string[] = [];
        for (let i = 1; i <= pdf.numPages; i++) {
          if (cancelled) return;
          setProgress(`Rendering page ${i}/${pdf.numPages}...`);
          const pg = await pdf.getPage(i);
          const scale = 2;
          const viewport = pg.getViewport({ scale });
          const canvas = document.createElement('canvas');
          canvas.width = viewport.width;
          canvas.height = viewport.height;
          const ctx = canvas.getContext('2d')!;
          await pg.render({ canvasContext: ctx, viewport }).promise;
          images.push(canvas.toDataURL('image/png'));
          pg.cleanup();
        }

        if (!cancelled) {
          setPageImages(images);
        }
      } catch (e: any) {
        if (!cancelled) setError(e.message || 'Failed to load slides');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [src]);

  const goTo = useCallback(
    (p: number) => {
      if (p < 0 || p >= numPages || p === page) return;
      setDirection(p > page ? 1 : -1);
      setPage(p);
    },
    [page, numPages],
  );

  const prev = useCallback(() => goTo(page - 1), [goTo, page]);
  const next = useCallback(() => goTo(page + 1), [goTo, page]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') prev();
      if (e.key === 'ArrowRight') next();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [prev, next]);

  const onTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX;
    touchDeltaX.current = 0;
  };
  const onTouchMove = (e: React.TouchEvent) => {
    touchDeltaX.current = e.touches[0].clientX - touchStartX.current;
  };
  const onTouchEnd = () => {
    if (touchDeltaX.current > SWIPE_THRESHOLD) prev();
    else if (touchDeltaX.current < -SWIPE_THRESHOLD) next();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-muted-foreground/50">
        <Loader2 className="w-5 h-5 animate-spin mr-2" />
        <span className="text-sm">{progress}</span>
      </div>
    );
  }

  if (error || numPages === 0) {
    return (
      <div className="flex items-center justify-center py-20 text-muted-foreground/60 text-sm">
        {error || 'Failed to load slides'}
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="relative select-none group"
      onTouchStart={onTouchStart}
      onTouchMove={onTouchMove}
      onTouchEnd={onTouchEnd}
    >
      <div className="overflow-hidden bg-foreground/[0.02]">
        <AnimatePresence mode="wait" custom={direction}>
          <motion.img
            key={page}
            src={pageImages[page]}
            alt={`Slide ${page + 1} of ${numPages}`}
            custom={direction}
            variants={variants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.25, ease: 'easeInOut' }}
            className="w-full h-auto block"
            draggable={false}
          />
        </AnimatePresence>
      </div>

      {numPages > 1 && (
        <>
          <button
            onClick={prev}
            disabled={page <= 0}
            className="absolute left-2 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-background/80 border border-border/50 backdrop-blur-sm flex items-center justify-center text-muted-foreground/60 hover:text-foreground hover:bg-background transition-all opacity-100 sm:opacity-0 sm:group-hover:opacity-100 disabled:opacity-0 shadow-lg"
            aria-label="Previous slide"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={next}
            disabled={page >= numPages - 1}
            className="absolute right-2 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-background/80 border border-border/50 backdrop-blur-sm flex items-center justify-center text-muted-foreground/60 hover:text-foreground hover:bg-background transition-all opacity-100 sm:opacity-0 sm:group-hover:opacity-100 disabled:opacity-0 shadow-lg"
            aria-label="Next slide"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </>
      )}

      {numPages > 1 && (
        <div className="flex items-center justify-center gap-3 py-2.5 bg-background/80 backdrop-blur-sm border-t border-border/40">
          <div className="flex items-center gap-1">
            {numPages <= 12 ? (
              Array.from({ length: numPages }, (_, i) => (
                <button
                  key={i}
                  onClick={() => goTo(i)}
                  className={`rounded-full transition-all ${
                    page === i
                      ? 'w-5 h-1.5 bg-foreground/70'
                      : 'w-1.5 h-1.5 bg-foreground/15 hover:bg-foreground/30'
                  }`}
                  aria-label={`Go to slide ${i + 1}`}
                />
              ))
            ) : (
              <span className="text-[10px] font-mono text-muted-foreground/50 tabular-nums">
                {page + 1} / {numPages}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
