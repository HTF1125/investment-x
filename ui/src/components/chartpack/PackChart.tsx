import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import { motion } from 'framer-motion';
import { Loader2, LineChart, Edit3, Check, Clock } from 'lucide-react';
import { ChartErrorBoundary } from '@/components/shared/ChartErrorBoundary';
import { apiFetchJson } from '@/lib/api';
import { getApiCode, buildChartFigure } from '@/lib/buildChartFigure';
import { applyChartTheme, COLORWAY } from '@/lib/chartTheme';
import { RANGE_MAP, getPresetStartDate } from '@/lib/constants';
import { useQuery } from '@tanstack/react-query';
import ChartMenu from './ChartMenu';
import ConfirmDialog from './ConfirmDialog';
import type { ChartConfig } from './types';

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center">
      <Loader2 className="w-4 h-4 animate-spin text-primary/30" />
    </div>
  ),
}) as any;

interface Props {
  config: ChartConfig;
  index: number;
  isLight: boolean;
  rawData: Record<string, (string | number | null)[]> | undefined;
  isLoading: boolean;
  onRemove: () => void;
  onEdit: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onCopyMove: () => void;
  onRefresh: () => void;
  isFirst: boolean;
  isLast: boolean;
  readOnly?: boolean;
  pageIndex?: number;
  justSaved?: boolean;
}

const MAX_TAGS = 4;

const PackChart = React.memo(function PackChart({
  config, index, isLight, rawData, isLoading,
  onRemove, onEdit, onMoveUp, onMoveDown, onCopyMove, onRefresh,
  isFirst, isLast, readOnly, pageIndex, justSaved,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const plotRef = useRef<HTMLElement | null>(null);
  const [urlCopied, setUrlCopied] = useState(false);
  const [containerSize, setContainerSize] = useState<{ w: number; h: number }>({ w: 400, h: 300 });

  // Track container dimensions for dynamic font scaling
  useEffect(() => {
    const el = containerRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      if (width > 0 && height > 0) setContainerSize({ w: Math.round(width), h: Math.round(height) });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const handleCopyImageUrl = useCallback(() => {
    // Copy chart title to clipboard as a fallback
    if (config.title) {
      navigator.clipboard.writeText(config.title).then(() => {
        setUrlCopied(true);
        setTimeout(() => setUrlCopied(false), 2000);
      });
    }
  }, [config.title]);

  const lazyFigure: any = undefined;
  const figLoading = false;

  const seriesList = useMemo(() => {
    const hasCode = !!config.code?.trim();
    if (hasCode && rawData) {
      const columns = Object.keys(rawData).filter((k) => k !== 'Date');
      const byCode = new Map(config.series.map((s) => [s.code, s]));
      return columns.map((col) => byCode.get(col) || {
        code: col, name: col, chartType: 'line', yAxis: 'left', yAxisIndex: 0, visible: true, transform: 'none',
      });
    }
    return config.series;
  }, [config.code, rawData, config.series]);

  const startDate = useMemo(() => {
    if (config.startDate) return config.startDate;
    const months = RANGE_MAP[config.activeRange || 'MAX'];
    return months != null ? getPresetStartDate(months) : '';
  }, [config.startDate, config.activeRange]);
  const endDate = config.endDate || '';

  const logAxesSet = useMemo(() => new Set((config.logAxes || []).map((v: any) => {
    const s = String(v);
    return s.includes('-') ? s : `0-${s}`;
  })), [config.logAxes]);

  const figure = useMemo(() => {
    // Dynamic font scale for cached figures too
    const scale = Math.max(0.7, Math.min(1.3, containerSize.w / 600));
    const sf = (base: number) => Math.round(base * scale * 10) / 10;

    const sourceFig = config.figure || lazyFigure?.figure;
    if (sourceFig) {
      const themed = applyChartTheme(sourceFig, isLight ? 'light' : 'dark') as any;
      if (!themed) return null;
      if (themed.layout) {
        const fg = isLight ? '#0f1118' : '#e1e6f0';
        const L = themed.layout;
        L.title = { text: '' };
        L.margin = { t: Math.round(8 * scale), l: Math.round(16 * scale), r: Math.round(45 * scale), b: Math.round(28 * scale) };
        L.font = { ...L.font, size: sf(10), color: fg };
        L.modebar = { bgcolor: 'rgba(0,0,0,0)', color: 'transparent', activecolor: 'transparent' };
        L.datarevision = config.figureCachedAt || Date.now();
        const tickStyle = { size: sf(9), color: fg, family: '"Space Mono", monospace' };
        for (const key of Object.keys(L)) {
          if (key.startsWith('yaxis')) {
            const ax = L[key];
            if (!ax) continue;
            if (ax.title) ax.title = { text: '' };
            ax.tickfont = tickStyle;
            ax.automargin = true;
            ax.exponentformat = 'SI';
            ax.separatethousands = true;
            ax.minexponent = 3;
            if (ax.overlaying || ax.anchor === 'free') {
              ax.autoshift = true;
              ax.shift = 0;
            }
          }
          if (key.startsWith('xaxis')) {
            const ax = L[key];
            if (!ax) continue;
            ax.tickfont = tickStyle;
            ax.automargin = true;
            if (ax.type === 'date') delete ax.tickformat;
          }
        }
        if (L.legend) {
          L.legend = { ...L.legend, font: { ...L.legend.font, size: sf(9), color: fg }, tracegroupgap: 2 };
        }
        if (L.hoverlabel) {
          L.hoverlabel = { ...L.hoverlabel, font: { ...L.hoverlabel.font, size: sf(10) } };
        }
      }
      return themed;
    }
    if (!rawData) return null;
    return buildChartFigure({
      rawData, series: seriesList, panes: config.panes,
      annotations: config.annotations as any, logAxes: logAxesSet,
      yAxisBases: config.yAxisBases || {},
      yAxisRanges: config.yAxisRanges || {},
      invertedAxes: new Set(config.invertedAxes || []),
      isLight, title: undefined, startDate, endDate, compact: true,
      containerWidth: containerSize.w, containerHeight: containerSize.h,
      showLegend: config.showLegend,
      legendPosition: config.legendPosition as any,
      showGridlines: config.showGridlines,
      gridlineStyle: config.gridlineStyle,
      axisTitles: config.axisTitles,
      titleFontSize: config.titleFontSize,
      showZeroline: config.showZeroline,
      bargap: config.bargap,
      drawnShapes: config.drawnShapes,
    });
  }, [config.figure, lazyFigure, rawData, seriesList, config.panes, config.annotations, logAxesSet, isLight, config.figureCachedAt, startDate, endDate, config.yAxisBases, config.yAxisRanges, config.invertedAxes, config.showLegend, config.legendPosition, config.showGridlines, config.gridlineStyle, config.axisTitles, config.titleFontSize, config.showZeroline, config.bargap, config.drawnShapes, containerSize.w, containerSize.h]);

  // Debounced resize
  const plotlyRef = useRef<any>(null);
  useEffect(() => {
    const el = containerRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    let timer: ReturnType<typeof setTimeout>;
    const observer = new ResizeObserver(() => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        const gd = plotRef.current;
        if (!gd?.isConnected || !gd.clientHeight || !gd.clientWidth) return;
        if (plotlyRef.current) {
          plotlyRef.current.Plots.resize(gd);
        } else {
          import('plotly.js-dist-min').then(({ default: Plotly }) => {
            plotlyRef.current = Plotly;
            if (gd?.isConnected && gd.clientHeight > 0 && gd.clientWidth > 0) (Plotly as any).Plots.resize(gd);
          }).catch(() => {});
        }
      }, 150);
    });
    observer.observe(el);
    return () => { clearTimeout(timer); observer.disconnect(); };
  }, []);

  const handlePlotInit = useCallback((_: any, gd: HTMLElement) => { plotRef.current = gd; }, []);

  const seriesCount = config.series?.length || 0;
  const stagger = typeof pageIndex === 'number' ? Math.min(pageIndex, 8) : 0;
  const [confirmRemove, setConfirmRemove] = useState(false);

  const seriesTags = (config.series || []).map((s, idx) => ({
    name: s.name || s.code,
    color: s.color || COLORWAY[idx % COLORWAY.length],
  }));
  const visibleTags = seriesTags.slice(0, MAX_TAGS);
  const extraCount = seriesTags.length - MAX_TAGS;

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: stagger * 0.04 }}
        className={`rounded-[var(--radius)] border bg-card hover:border-primary/25 relative group/chart overflow-hidden flex flex-col transition-all duration-300 ${
          justSaved ? 'border-success/60 shadow-[0_0_12px_-3px_rgb(var(--success)/0.25)]' : 'border-border/30'
        }`}
      >
        {/* Save success indicator */}
        {justSaved && (
          <div className="absolute inset-0 z-20 pointer-events-none flex items-center justify-center animate-save-flash">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-success/10 border border-success/20">
              <Check className="w-3 h-3 text-success" />
              <span className="text-[11.5px] font-mono font-medium text-success">Saved</span>
            </div>
          </div>
        )}

        {/* URL copied indicator */}
        {urlCopied && (
          <div className="absolute inset-0 z-20 pointer-events-none flex items-center justify-center">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-primary/10 border border-primary/20">
              <Check className="w-3 h-3 text-primary" />
              <span className="text-[11.5px] font-mono font-medium text-primary">URL copied</span>
            </div>
          </div>
        )}

        {/* Edit button — bottom-right corner on hover */}
        {!readOnly && (
          <button
            onClick={(e) => { e.stopPropagation(); onEdit(); }}
            className="absolute bottom-2 right-2 z-10 opacity-0 group-hover/chart:opacity-100 transition-opacity duration-150 cursor-pointer"
            aria-label="Edit chart"
          >
            <div className="w-7 h-7 flex items-center justify-center rounded-[var(--radius)] bg-card/95 border border-border/40 hover:bg-foreground/[0.06] hover:border-border/60 transition-colors shadow-sm">
              <Edit3 className="w-3 h-3 text-muted-foreground/50" />
            </div>
          </button>
        )}

        {/* ── Card header ── */}
        <div className="shrink-0 px-3 pt-2.5 pb-2 border-b border-border/15">
          <div className="flex items-center gap-1.5">
            <button
              onClick={(e) => { e.stopPropagation(); onEdit(); }}
              className="text-[13px] font-semibold text-foreground/80 truncate flex-1 min-w-0 text-left hover:text-primary transition-colors"
              title={config.title || `Chart ${index + 1}`}
            >
              {config.title || `Chart ${index + 1}`}
            </button>

            {seriesCount > 0 && (
              <span className="shrink-0 px-1.5 py-0.5 rounded-[4px] bg-foreground/[0.04] text-[11px] font-mono text-muted-foreground/40 tabular-nums">
                {seriesCount}
              </span>
            )}

            {config.figureCachedAt && (
              <span
                className="shrink-0 flex items-center gap-0.5 text-[9.5px] font-mono text-muted-foreground/20"
                title={`Cached ${new Date(config.figureCachedAt).toLocaleString()}`}
              >
                <Clock className="w-2.5 h-2.5" />
              </span>
            )}

            {!readOnly && (
              <div className="shrink-0 opacity-0 group-hover/chart:opacity-100 transition-opacity duration-150">
                <ChartMenu
                  onEdit={onEdit} onMoveUp={onMoveUp} onMoveDown={onMoveDown}
                  onCopyMove={onCopyMove} onRemove={() => setConfirmRemove(true)}
                  onRefresh={onRefresh} hasCachedFigure={!!config.figure}
                  onCopyImageUrl={config.chart_id ? handleCopyImageUrl : undefined}
                  isFirst={isFirst} isLast={isLast}
                />
              </div>
            )}
          </div>

          {config.description && (
            <p className="text-[11.5px] leading-snug text-muted-foreground/40 mt-1 line-clamp-2">{config.description}</p>
          )}

          {visibleTags.length > 0 && (
            <div className="flex items-center gap-1 mt-1.5 overflow-hidden">
              {visibleTags.map(({ name, color }) => (
                <span key={name} className="shrink-0 max-w-[100px] truncate inline-flex items-center gap-1 px-1.5 py-0.5 rounded-[4px] bg-foreground/[0.03] text-[11px] font-mono text-muted-foreground/50">
                  <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
                  {name}
                </span>
              ))}
              {extraCount > 0 && (
                <span className="shrink-0 text-[11px] font-mono text-muted-foreground/25">
                  +{extraCount}
                </span>
              )}
            </div>
          )}
        </div>

        {/* ── Chart area ── */}
        <div ref={containerRef} className="flex-1 min-h-0">
          {isLoading || figLoading ? (
            <div className="h-full w-full animate-pulse bg-foreground/[0.02] rounded-b-[var(--radius)]" />
          ) : figure ? (
            <ChartErrorBoundary>
              <Plot data={figure.data} layout={{ ...figure.layout, dragmode: false }}
                config={{ responsive: true, displayModeBar: false, displaylogo: false, scrollZoom: false }}
                style={{ width: '100%', height: '100%' }}
                onInitialized={handlePlotInit} />
            </ChartErrorBoundary>
          ) : (
            <div className="h-full flex flex-col items-center justify-center gap-2">
              <LineChart className="w-5 h-5 text-muted-foreground/10" />
              <span className="text-[12.5px] text-muted-foreground/25">No data</span>
            </div>
          )}
        </div>
      </motion.div>

      {confirmRemove && (
        <ConfirmDialog
          title="Remove chart"
          message={<>Remove <span className="font-semibold text-foreground">{config.title || `Chart ${index + 1}`}</span> from this pack?</>}
          confirmLabel="Remove"
          onConfirm={() => { setConfirmRemove(false); onRemove(); }}
          onCancel={() => setConfirmRemove(false)}
        />
      )}
    </>
  );
});

export default PackChart;
