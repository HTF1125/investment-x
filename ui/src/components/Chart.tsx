'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import { Loader2, Copy, Check } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-[450px] w-full bg-white/5 rounded-xl animate-pulse">
      <Loader2 className="w-8 h-8 text-sky-500 animate-spin" />
    </div>
  ),
}) as any;

interface ChartProps {
  code: string;
}

export default function Chart({ code }: ChartProps) {
  const [graphDiv, setGraphDiv] = React.useState<HTMLElement | null>(null);
  const [copyState, setCopyState] = React.useState<'idle' | 'copying' | 'done'>('idle');
  
  const { data: figure, isLoading, error } = useQuery({
    queryKey: ['chart-figure', code],
    queryFn: async () => {
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
      const headers: Record<string, string> = {};
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetch(`/api/v1/dashboard/charts/${code}/figure`, { headers });
      
      if (!res.ok) {
        throw new Error('Failed to load chart data');
      }
      
      const data = await res.json();
        
      // Clean up layout for Next.js container
      if (data.layout) {
        data.layout.autosize = true;
        data.layout.width = undefined;
        data.layout.height = undefined;
        data.layout.paper_bgcolor = 'rgba(0,0,0,0)';
        data.layout.plot_bgcolor = 'rgba(0,0,0,0)';
        data.layout.margin = {l: 40, r: 20, t: 30, b: 40};
      }
      return data;
    },
    staleTime: 1000 * 60 * 10, // 10 minutes cache
    enabled: !!code,
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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[450px] w-full bg-white/5 rounded-xl animate-pulse">
        <Loader2 className="w-8 h-8 text-sky-500 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-[450px] text-rose-500 bg-rose-500/10 rounded-xl p-4 text-center">
        <p>Error: {(error as Error).message}</p>
      </div>
    );
  }

  return (
    <div className="w-full min-h-[450px] relative group">
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
      
      {figure && (
        <Plot
          data={figure.data}
          layout={figure.layout}
          config={{
            responsive: true,
            displayModeBar: 'hover',
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
