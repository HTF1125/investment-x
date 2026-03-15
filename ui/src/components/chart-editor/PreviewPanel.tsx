'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import { Loader2, Copy, Activity } from 'lucide-react';

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full w-full">
      <Loader2 className="w-8 h-8 text-muted-foreground animate-spin" />
    </div>
  ),
}) as React.ComponentType<Record<string, unknown>>;

interface PreviewPanelProps {
  currentChartId: string | null;
  theme: string;
  themedPreviewFigure: any;
  previewFigure: any;
  plotRenderError: string | null;
  setPlotRenderError: (v: string | null) => void;
  plotRetryNonce: number;
  setPlotRetryNonce: (fn: (n: number) => number) => void;
  loadingChartId: string | null;
  copying: boolean;
  handleCopyChart: () => void;
  handlePlotError: (err: any) => void;
}

export default function PreviewPanel({
  currentChartId,
  theme,
  themedPreviewFigure,
  previewFigure,
  plotRenderError,
  setPlotRenderError,
  plotRetryNonce,
  setPlotRetryNonce,
  loadingChartId,
  copying,
  handleCopyChart,
  handlePlotError,
}: PreviewPanelProps) {
  return (
    <div className="flex-grow relative flex flex-col min-h-0 p-3 items-center justify-center">
      <div className="relative overflow-hidden rounded-lg border border-border/50 bg-background w-full h-full max-w-[1200px] max-h-[700px]">
        {loadingChartId ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm z-10">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            <p className="text-[11px] text-muted-foreground mt-3">Loading chart...</p>
          </div>
        ) : themedPreviewFigure && !plotRenderError ? (
          <Plot
            key={`${currentChartId || 'draft'}-${theme}-${plotRetryNonce}`}
            data={themedPreviewFigure.data}
            layout={{
              ...themedPreviewFigure.layout,
              autosize: true,
              dragmode: 'zoom'
            }}
            config={{ responsive: true, displayModeBar: 'hover' as any, displaylogo: false, scrollZoom: true, modeBarButtonsToRemove: ['select2d', 'lasso2d', 'sendDataToCloud'] as any[] }}
            style={{ width: '100%', height: '100%' }}
            className="w-full h-full"
            onError={handlePlotError}
          />
        ) : plotRenderError ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 px-6 text-center">
            <div className="text-xs font-semibold text-destructive">Chart Render Error</div>
            <div className="text-[11px] text-muted-foreground">
              {plotRenderError}
            </div>
            <button
              type="button"
              onClick={() => {
                setPlotRenderError(null);
                setPlotRetryNonce((n) => n + 1);
              }}
              className="h-8 px-3 rounded-md border border-border/50 text-xs text-muted-foreground hover:text-foreground"
            >
              Retry Render
            </button>
          </div>
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <Activity className="w-8 h-8 text-muted-foreground/20" />
            <p className="text-[12px] font-medium text-muted-foreground mt-3">Run code to preview chart</p>
            <p className="text-[11px] text-muted-foreground/50 mt-1">or select from library</p>
          </div>
        )}

        {/* Quick Floating Actions */}
        {previewFigure && (
          <div className="absolute top-3 right-3">
            <button
              onClick={handleCopyChart}
              className="p-1.5 rounded-md bg-background border border-border/50 text-muted-foreground/40 hover:text-muted-foreground hover:border-border transition-all"
              title="Copy Image"
            >
              {copying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
