'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import { Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import { useTheme } from '@/context/ThemeContext';
import { applyChartTheme } from '@/lib/chartTheme';

const ChartSkeleton = () => (
  <div className="w-full h-full p-6 flex flex-col gap-4 bg-background/80 rounded-xl animate-pulse overflow-hidden relative min-h-[290px]">
    {/* Grid Lines Pattern */}
    <div className="absolute inset-x-8 inset-y-12 flex flex-col justify-between opacity-10">
      {[...Array(8)].map((_, i) => (
        <div key={i} className="h-px bg-sky-500/30 w-full" />
      ))}
    </div>
    
    {/* Body skeleton - Dynamic Bars */}
    <div className="flex-1 flex items-end gap-3 px-8 pb-12 relative z-10 transition-all duration-1000">
      {[40, 70, 45, 90, 65, 30, 85, 50, 60, 40].map((h, i) => (
        <div 
          key={i} 
          className="flex-1 rounded-t-md bg-sky-500/5 border border-sky-500/10"
          style={{ height: `${h}%`, animationDelay: `${i * 100}ms` }} 
        />
      ))}
    </div>

    {/* Center Glow */}
    <div className="absolute inset-0 flex items-center justify-center z-20">
      <div className="p-4 bg-background/60 backdrop-blur-xl rounded-2xl border border-border/20 shadow-2xl">
        <Loader2 className="w-6 h-6 text-sky-500 animate-spin" />
      </div>
    </div>
  </div>
);

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => <ChartSkeleton />,
}) as React.ComponentType<Record<string, unknown>>;

import { motion, AnimatePresence } from 'framer-motion';

interface ChartProps {
  id: string;
  initialFigure?: any;
  copySignal?: number;
}

export default function Chart({ id, initialFigure, copySignal = 0 }: ChartProps) {
  const { theme } = useTheme();
  const [graphDiv, setGraphDiv] = React.useState<HTMLElement | null>(null);
  const [plotRenderError, setPlotRenderError] = React.useState<string | null>(null);
  const [plotRetryNonce, setPlotRetryNonce] = React.useState(0);
  const [copyState, setCopyState] = React.useState<'idle' | 'copying' | 'done'>('idle');
  const [isVisible, setIsVisible] = React.useState(true);
  const containerRef = React.useRef<HTMLDivElement>(null);
  const safelyThemeFigure = React.useCallback(
    (figure: any) => {
      try {
        return applyChartTheme(figure, theme, { transparentBackground: true });
      } catch {
        return figure;
      }
    },
    [theme]
  );

  const { data: rawFigure, isLoading, error } = useQuery({
    queryKey: ['chart-figure', id],
    queryFn: async () => {
      const res = await apiFetch(`/api/v1/dashboard/charts/${id}/figure`);
      
      if (!res.ok) {
        throw new Error('Failed to load chart data');
      }
      
      return res.json();
    },
    initialData: initialFigure ?? undefined,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    enabled: !!id && isVisible,
  });

  const figure = React.useMemo(
    () => safelyThemeFigure(rawFigure),
    [rawFigure, safelyThemeFigure]
  );

  React.useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    if (typeof IntersectionObserver === 'undefined') {
      setIsVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsVisible(entry.isIntersecting);
      },
      { rootMargin: '500px 0px 500px 0px', threshold: 0 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [id]);

  React.useEffect(() => {
    if (!isVisible) {
      setGraphDiv(null);
      setPlotRenderError(null);
    }
  }, [isVisible]);

  React.useEffect(() => {
    setPlotRenderError(null);
  }, [id, theme, rawFigure]);

  const handleCopy = React.useCallback(async () => {
    if (!graphDiv || copyState !== 'idle') return;
    setCopyState('copying');
    try {
        const Plotly = (await import('plotly.js-dist-min')).default;
        const url = await Plotly.toImage(graphDiv as any, { format: 'png', width: 1200, height: 800, scale: 2 });
        
        const res = await fetch(url);
        const blob = await res.blob();
        
        await navigator.clipboard.write([
            new ClipboardItem({ 'image/png': blob })
        ]);
        
        setCopyState('done');
        setTimeout(() => setCopyState('idle'), 1500);
    } catch {
        // Clipboard write may fail in insecure contexts — degrade silently
        setCopyState('idle');
    }
  }, [graphDiv, copyState]);

  const lastCopySignalRef = React.useRef(copySignal);
  React.useEffect(() => {
    if (copySignal !== lastCopySignalRef.current) {
      lastCopySignalRef.current = copySignal;
      handleCopy();
    }
  }, [copySignal, handleCopy]);

  if (!isVisible) {
    return (
      <div ref={containerRef} className="h-[290px] w-full">
        <ChartSkeleton />
      </div>
    );
  }

  return (
    <div ref={containerRef} className="w-full h-full min-h-[290px] relative group flex flex-col">
      <AnimatePresence mode="wait">
        {isLoading || !figure ? (
          <motion.div
            key="skeleton"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="h-full w-full"
          >
            <ChartSkeleton />
          </motion.div>
        ) : (
          <motion.div
            key="chart"
            initial={{ opacity: 0, scale: 0.99, filter: 'blur(4px)' }}
            animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
            className="w-full h-full"
          >
            {!plotRenderError ? (
              <Plot
                key={`${id}-${theme}-${plotRetryNonce}`}
                data={figure.data}
                layout={{
                  ...figure.layout,
                  autosize: true
                }}
                config={{
                  responsive: true,
                  displayModeBar: false,
                  displaylogo: false,
                }}
                style={{ width: '100%', height: '100%' }}
                useResizeHandler={true}
                onInitialized={(_figure: Readonly<{data: any[]; layout: any; frames: any}>, gd: Readonly<HTMLElement>) => setGraphDiv(gd as HTMLElement)}
                onError={(err: any) => setPlotRenderError(err?.message || 'Chart render failed.')}
              />
            ) : (
              <div className="h-full w-full flex flex-col items-center justify-center gap-2 p-4 text-center">
                <div className="text-xs text-rose-400 font-semibold">Chart Render Error</div>
                <div className="text-[11px] text-muted-foreground">{plotRenderError}</div>
                <button
                  type="button"
                  onClick={() => {
                    setPlotRenderError(null);
                    setPlotRetryNonce((n) => n + 1);
                  }}
                  className="h-7 px-3 rounded-md border border-border/60 text-xs text-muted-foreground hover:text-foreground"
                >
                  Retry
                </button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-rose-500/5 rounded-xl border border-rose-500/10 text-rose-500 text-xs font-mono">
          EXECUTION_ERROR: {id}
        </div>
      )}
    </div>
  );
}
