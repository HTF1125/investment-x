'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import { Loader2 } from 'lucide-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import { useTheme } from '@/context/ThemeContext';
import { applyChartTheme } from '@/lib/chartTheme';

const ChartSkeleton = () => (
  <div className="w-full h-full p-6 flex flex-col gap-4 bg-[#0a0a0a]/40 rounded-xl animate-pulse overflow-hidden relative min-h-[290px]">
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
      <div className="p-4 bg-background/60 backdrop-blur-xl rounded-2xl border border-white/5 shadow-2xl">
        <Loader2 className="w-6 h-6 text-sky-500 animate-spin" />
      </div>
    </div>
  </div>
);

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => <ChartSkeleton />,
}) as any;

import { motion, AnimatePresence } from 'framer-motion';

interface ChartProps {
  id: string;
  initialFigure?: any;
  copySignal?: number;
}

export default function Chart({ id, initialFigure, copySignal = 0 }: ChartProps) {
  const { theme } = useTheme();
  const queryClient = useQueryClient();
  const [graphDiv, setGraphDiv] = React.useState<HTMLElement | null>(null);
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

  // Sync internal cache when initialFigure prop changes
  React.useEffect(() => {
    if (initialFigure && id) {
      queryClient.setQueryData(
        ['chart-figure', id, theme],
        safelyThemeFigure(initialFigure)
      );
    }
  }, [id, initialFigure, queryClient, theme, safelyThemeFigure]);
  
  const { data: figure, isLoading, error } = useQuery({
    queryKey: ['chart-figure', id, theme],
    queryFn: async () => {
      const res = await apiFetch(`/api/v1/dashboard/charts/${id}/figure`);
      
      if (!res.ok) {
        throw new Error('Failed to load chart data');
      }
      
      const data = await res.json();
      return safelyThemeFigure(data);
    },
    initialData: () => safelyThemeFigure(initialFigure),
    staleTime: 1000 * 60 * 10, // 10 minutes cache
    enabled: !!id && isVisible,
  });

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
            <Plot
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
              onInitialized={(_: any, gd: any) => setGraphDiv(gd)}
            />
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
