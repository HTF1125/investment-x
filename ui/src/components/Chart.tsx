'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import { Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-[450px] w-full bg-white/5 rounded-xl animate-pulse">
      <Loader2 className="w-8 h-8 text-sky-500 animate-spin" />
    </div>
  ),
});

interface ChartProps {
  code: string;
}

export default function Chart({ code }: ChartProps) {
  const { data: figure, isLoading, error } = useQuery({
    queryKey: ['chart-figure', code],
    queryFn: async () => {
      // Optional token for public access - sanitize
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
        
      // Clean up layout for nextjs container
      if (data.layout) {
        data.layout.autosize = true;
        data.layout.width = undefined;
        data.layout.height = undefined;
        data.layout.paper_bgcolor = 'rgba(0,0,0,0)';
        data.layout.plot_bgcolor = 'rgba(0,0,0,0)';
      }
      return data;
    },
    staleTime: 1000 * 60 * 10, // 10 minutes cache
    enabled: !!code,
  });

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
    <div className="w-full min-h-[450px]">
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
        />
      )}
    </div>
  );
}
