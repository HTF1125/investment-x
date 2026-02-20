'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import { Loader2, Copy, Check } from 'lucide-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import { useTheme } from '@/context/ThemeContext';

const ChartSkeleton = () => (
  <div className="w-full h-full p-6 flex flex-col gap-4 bg-[#0a0a0a]/40 rounded-xl animate-pulse overflow-hidden relative min-h-[350px]">
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

const cleanFigure = (data: any, theme: string) => {
    if (!data) return data;
    const cleaned = JSON.parse(JSON.stringify(data)); // Deep clone
    const isLight = theme === 'light';
    const textColor = isLight ? 'rgb(15 23 42)' : 'rgb(248 250 252)';
    const gridColor = isLight ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.06)';

    if (cleaned.layout) {
      cleaned.layout.autosize = true;
      cleaned.layout.width = undefined;
      cleaned.layout.height = undefined;
      cleaned.layout.paper_bgcolor = 'rgba(0,0,0,0)';
      cleaned.layout.plot_bgcolor = 'rgba(0,0,0,0)';
      
      const legendBg = isLight ? 'rgba(255,255,255,0.85)' : 'rgba(0,0,0,0.7)';
      const borderColor = isLight ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)';
      
      // Theme-aware typography
      cleaned.layout.font = { ...cleaned.layout.font, color: textColor, family: 'Inter, sans-serif' };
      
      const axes = ['xaxis', 'yaxis', 'xaxis2', 'yaxis2', 'xaxis3', 'yaxis3', 'xaxis4', 'yaxis4'];
      axes.forEach(ax => {
        if (cleaned.layout[ax]) {
          cleaned.layout[ax].gridcolor = gridColor;
          cleaned.layout[ax].zerolinecolor = gridColor;
          cleaned.layout[ax].tickfont = { color: textColor, size: 10 };
          cleaned.layout[ax].title = { 
            ...cleaned.layout[ax].title, 
            font: { color: textColor, size: 11, weight: 600 } 
          };
        }
      });

      if (cleaned.layout.legend) {
        cleaned.layout.legend.font = { color: textColor, size: 10 };
        cleaned.layout.legend.bgcolor = legendBg;
        cleaned.layout.legend.bordercolor = borderColor;
        cleaned.layout.legend.borderwidth = 1;
      }

      // Tooltip/Hover Styling
      cleaned.layout.hoverlabel = {
        bgcolor: isLight ? 'white' : 'rgb(15 23 42)',
        bordercolor: borderColor,
        font: { color: textColor, family: 'Inter, sans-serif', size: 12 },
        align: 'left'
      };

      // Preserve the chart's intended margins but cap them for card display
      const orig = cleaned.layout.margin || {};
      cleaned.layout.margin = {
        l: Math.min(orig.l ?? 50, 120),
        r: Math.min(orig.r ?? 20, 50),
        t: Math.min(orig.t ?? 40, 80),
        b: Math.min(orig.b ?? 30, 50),
      };
    }
    return cleaned;
};

interface ChartProps {
  id: string;
  initialFigure?: any;
}

export default function Chart({ id, initialFigure }: ChartProps) {
  const { theme } = useTheme();
  const queryClient = useQueryClient();
  const [graphDiv, setGraphDiv] = React.useState<HTMLElement | null>(null);
  const [copyState, setCopyState] = React.useState<'idle' | 'copying' | 'done'>('idle');
  const [isVisible, setIsVisible] = React.useState(true);
  const containerRef = React.useRef<HTMLDivElement>(null);

  // Sync internal cache when initialFigure prop changes
  React.useEffect(() => {
    if (initialFigure && id) {
      queryClient.setQueryData(['chart-figure', id, theme], cleanFigure(initialFigure, theme));
    }
  }, [id, initialFigure, queryClient, theme]);
  
  const { data: figure, isLoading, error } = useQuery({
    queryKey: ['chart-figure', id, theme],
    queryFn: async () => {
      const res = await apiFetch(`/api/v1/dashboard/charts/${id}/figure`);
      
      if (!res.ok) {
        throw new Error('Failed to load chart data');
      }
      
      const data = await res.json();
      return cleanFigure(data, theme);
    },
    initialData: () => cleanFigure(initialFigure, theme),
    staleTime: 1000 * 60 * 10, // 10 minutes cache
    enabled: !!id && isVisible,
  });

  const handleCopy = async () => {
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
  };

  if (!isVisible) {
    return (
      <div ref={containerRef} className="h-[350px] w-full">
        <ChartSkeleton />
      </div>
    );
  }

  return (
    <div ref={containerRef} className="w-full h-full min-h-[350px] relative group flex flex-col">
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
            <button
              onClick={handleCopy}
              disabled={copyState !== 'idle'}
              className="absolute top-2 right-2 z-10 p-2 bg-background/60 hover:bg-background/80 text-muted-foreground hover:text-foreground rounded-lg opacity-0 group-hover:opacity-100 transition-all shadow-lg border border-border"
              title="Copy Chart to Clipboard"
            >
              {copyState === 'copying' ? (
                <Loader2 className="w-4 h-4 animate-spin text-sky-400" />
              ) : copyState === 'done' ? (
                <Check className="w-4 h-4 text-emerald-400" />
              ) : (
                <Copy className="w-4 h-4" />
              )}
            </button>
            
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
