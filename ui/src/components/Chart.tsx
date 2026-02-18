'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import { Loader2, Copy, Check } from 'lucide-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-[450px] w-full bg-white/5 rounded-xl animate-pulse">
      <Loader2 className="w-8 h-8 text-sky-500 animate-spin" />
    </div>
  ),
}) as any;

const cleanFigure = (data: any) => {
    if (!data) return data;
    const cleaned = { ...data };
    if (cleaned.layout) {
      cleaned.layout.autosize = true;
      cleaned.layout.width = undefined;
      cleaned.layout.height = undefined;
      cleaned.layout.paper_bgcolor = 'rgba(0,0,0,0)';
      cleaned.layout.plot_bgcolor = 'rgba(0,0,0,0)';
      cleaned.layout.margin = {l: 40, r: 20, t: 30, b: 40};
    }
    return cleaned;
};

interface ChartProps {
  id: string;
  initialFigure?: any;
}

export default function Chart({ id, initialFigure }: ChartProps) {
  const queryClient = useQueryClient();
  const [graphDiv, setGraphDiv] = React.useState<HTMLElement | null>(null);
  const [copyState, setCopyState] = React.useState<'idle' | 'copying' | 'done'>('idle');
  const [isVisible, setIsVisible] = React.useState(true);
  const containerRef = React.useRef<HTMLDivElement>(null);

  // Sync internal cache when initialFigure prop changes
  React.useEffect(() => {
    if (initialFigure && id) {
      queryClient.setQueryData(['chart-figure', id], cleanFigure(initialFigure));
    }
  }, [id, initialFigure, queryClient]);
  
  const { data: figure, isLoading, error } = useQuery({
    queryKey: ['chart-figure', id],
    queryFn: async () => {
      const res = await apiFetch(`/api/v1/dashboard/charts/${id}/figure`);
      
      if (!res.ok) {
        throw new Error('Failed to load chart data');
      }
      
      const data = await res.json();
      return cleanFigure(data);
    },
    initialData: () => cleanFigure(initialFigure),
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
      <div ref={containerRef} className="flex items-center justify-center h-[350px] w-full bg-white/5 rounded-xl animate-pulse">
        <Loader2 className="w-8 h-8 text-sky-400/10 animate-spin" />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[350px] w-full bg-white/5 rounded-xl animate-pulse">
        <Loader2 className="w-8 h-8 text-sky-400/20 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-[350px] w-full bg-rose-500/5 rounded-xl border border-rose-500/10 text-rose-500 text-xs font-mono">
        EXECUTION_ERROR: {id}
      </div>
    );
  }

  return (
    <div ref={containerRef} className="w-full h-full min-h-0 relative group">
      <button
        onClick={handleCopy}
        disabled={copyState !== 'idle'}
        className="absolute top-2 right-2 z-10 p-2 bg-black/60 hover:bg-black/80 text-slate-300 hover:text-white rounded-lg opacity-0 group-hover:opacity-100 transition-all shadow-lg border border-white/10"
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
      
      {figure && isVisible && (
        <Plot
          data={figure.data}
          layout={{
            ...figure.layout,
            autosize: true
          }}
          config={{
            responsive: true,
            displayModeBar: false, // Cleaner display
            displaylogo: false,
          }}
          style={{ width: '100%', height: '100%' }}
          useResizeHandler={true}
          onInitialized={(_: any, gd: any) => setGraphDiv(gd)}
        />
      )}
    </div>
  );
}
