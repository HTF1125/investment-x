import React, { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { ChevronLeft, ChevronRight, LineChart, Plus, Search, LayoutGrid, Columns2, Square } from 'lucide-react';
import { useQuery, useQueries, keepPreviousData } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { getApiCode } from '@/lib/buildChartFigure';
import PackChart from './PackChart';
import type { PackDetail } from './types';

type LayoutMode = '1' | '2' | '3';
const LAYOUT_PAGE_SIZE: Record<LayoutMode, number> = { '1': 6, '2': 12, '3': 18 };
const LAYOUT_GRID: Record<LayoutMode, string> = {
  '1': 'grid-cols-1',
  '2': 'grid-cols-1 lg:grid-cols-2',
  '3': 'grid-cols-1 md:grid-cols-2 xl:grid-cols-3',
};
const LAYOUT_HEIGHT: Record<LayoutMode, string> = {
  '1': 'clamp(400px, 50vh, 560px)',
  '2': 'clamp(320px, 38vh, 450px)',
  '3': 'clamp(260px, 30vh, 360px)',
};

interface Props {
  pack: PackDetail;
  isLight: boolean;
  readOnly?: boolean;
  justSavedIndex?: number | null;
  onRemoveChart: (i: number) => void;
  onEditChart: (i: number) => void;
  onMoveChart: (from: number, to: number) => void;
  onCopyMoveChart: (i: number) => void;
  onRefreshChart: (i: number) => void;
  onAddChart?: () => void;
}

export default function PackChartGrid({
  pack, isLight, readOnly, justSavedIndex,
  onRemoveChart, onEditChart, onMoveChart, onCopyMoveChart, onRefreshChart, onAddChart,
}: Props) {
  // ── Layout mode ──
  const [layout, setLayout] = useState<LayoutMode>(() => {
    if (typeof window !== 'undefined') return (localStorage.getItem('ix-pack-layout') as LayoutMode) || '2';
    return '2';
  });
  useEffect(() => { localStorage.setItem('ix-pack-layout', layout); }, [layout]);
  const PAGE_SIZE = LAYOUT_PAGE_SIZE[layout];

  // ── Pagination & search state ──
  const pageKey = `ix-pack-page-${pack.id}`;
  const totalPages = Math.max(1, Math.ceil(pack.charts.length / PAGE_SIZE));
  const [page, setPage] = useState(() => {
    const stored = sessionStorage.getItem(pageKey);
    const p = stored ? parseInt(stored, 10) : 0;
    return Math.min(p, Math.max(0, Math.ceil(pack.charts.length / PAGE_SIZE) - 1));
  });

  useEffect(() => { sessionStorage.setItem(pageKey, String(page)); }, [pageKey, page]);

  useEffect(() => {
    const stored = sessionStorage.getItem(pageKey);
    const p = stored ? parseInt(stored, 10) : 0;
    setPage(Math.min(p, totalPages - 1));
  }, [pack.id, pageKey, totalPages]);

  const [searchQuery, setSearchQuery] = useState('');

  const filteredCharts = useMemo(() => {
    if (!searchQuery.trim()) return pack.charts.map((c, i) => ({ chart: c, origIdx: i }));
    const q = searchQuery.toLowerCase();
    return pack.charts
      .map((c, i) => ({ chart: c, origIdx: i }))
      .filter(({ chart }) =>
        (chart.title || '').toLowerCase().includes(q) ||
        (chart.description || '').toLowerCase().includes(q) ||
        chart.series?.some((s) => (s.name || s.code).toLowerCase().includes(q))
      );
  }, [pack.charts, searchQuery]);

  const visibleOrigIndices = useMemo(() => {
    const filteredTotal = filteredCharts.length;
    const filteredTotalPages = Math.max(1, Math.ceil(filteredTotal / PAGE_SIZE));
    const safePage = Math.min(page, filteredTotalPages - 1);
    const startIdx = safePage * PAGE_SIZE;
    const endIdx = Math.min(startIdx + PAGE_SIZE * 2, filteredTotal);
    const indices = new Set<number>();
    for (let i = startIdx; i < endIdx; i++) {
      indices.add(filteredCharts[i].origIdx);
    }
    return indices;
  }, [filteredCharts, page]);

  const { codeChartIndices, allCodes } = useMemo(() => {
    const codeIdx: number[] = [];
    const codes = new Set<string>();
    pack.charts.forEach((chart, i) => {
      if (!visibleOrigIndices.has(i)) return;
      if (chart.figure || chart.chart_id) return;
      if (chart.code?.trim()) {
        codeIdx.push(i);
      } else {
        chart.series?.forEach((s) => codes.add(getApiCode(s)));
      }
    });
    return { codeChartIndices: codeIdx, allCodes: Array.from(codes) };
  }, [pack.charts, visibleOrigIndices]);

  const { data: batchData, isLoading: batchLoading } = useQuery({
    queryKey: ['pack-batch-data', pack.id, allCodes],
    queryFn: () => apiFetchJson<Record<string, (string | number | null)[]>>('/api/timeseries.custom', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ codes: allCodes }),
    }),
    enabled: allCodes.length > 0,
    staleTime: 120_000,
    placeholderData: keepPreviousData,
    retry: 3,
    retryDelay: (attempt: number) => Math.min(2000 * 2 ** attempt, 15_000),
  });

  const codeQueries = useQueries({
    queries: codeChartIndices.map((i) => ({
      queryKey: ['pack-chart-code', i, pack.charts[i].code],
      queryFn: () => apiFetchJson<Record<string, any>>('/api/timeseries.exec', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: pack.charts[i].code }),
      }),
      staleTime: 120_000,
      retry: 3,
      retryDelay: (attempt: number) => Math.min(2000 * 2 ** attempt, 15_000),
    })),
  });

  const codeDataMap = useMemo(() => {
    const map = new Map<number, Record<string, any[]> | undefined>();
    codeChartIndices.forEach((chartIdx, queryIdx) => {
      const result = codeQueries[queryIdx]?.data;
      if (!result) { map.set(chartIdx, undefined); return; }
      const columns: string[] = result.__columns__ || Object.keys(result).filter((k) => k !== 'Date' && k !== '__columns__');
      const data: Record<string, any[]> = { Date: result.Date };
      for (const col of columns) data[col] = result[col];
      map.set(chartIdx, data);
    });
    return map;
  }, [codeChartIndices, codeQueries]);

  const chartDataList = useMemo(() => {
    return pack.charts.map((chart, i) => {
      if (chart.figure || chart.chart_id) return { rawData: undefined, isLoading: false };
      if (!visibleOrigIndices.has(i)) return { rawData: undefined, isLoading: false };
      if (chart.code?.trim()) {
        const rd = codeDataMap.get(i);
        return { rawData: rd, isLoading: !codeDataMap.has(i) || (rd === undefined && codeQueries[codeChartIndices.indexOf(i)]?.isLoading) };
      }
      if (!batchData) return { rawData: undefined, isLoading: batchLoading };
      const slice: Record<string, (string | number | null)[]> = { Date: batchData.Date };
      chart.series.forEach((s) => {
        const key = getApiCode(s);
        if (batchData[key]) slice[key] = batchData[key];
      });
      return { rawData: slice, isLoading: false };
    });
  }, [pack.charts, batchData, batchLoading, codeDataMap, codeQueries, codeChartIndices, visibleOrigIndices]);

  // ── Empty state ──
  if (pack.charts.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="text-center max-w-[260px]"
        >
          <div className="w-12 h-12 mx-auto rounded-[var(--radius)] border border-border/30 bg-card flex items-center justify-center mb-4">
            <LineChart className="w-5 h-5 text-muted-foreground/20" />
          </div>
          <p className="text-[13px] font-semibold text-foreground/50">Empty pack</p>
          <p className="text-[12.5px] text-muted-foreground/40 mt-2 leading-relaxed">
            {readOnly ? 'This pack has no charts yet.' : 'Add charts from the builder to start monitoring.'}
          </p>
          {!readOnly && onAddChart && (
            <button onClick={onAddChart} className="btn-primary mt-5">
              <Plus className="w-3.5 h-3.5" /> Add chart
            </button>
          )}
        </motion.div>
      </div>
    );
  }

  // ── Grid ──
  const filteredTotal = filteredCharts.length;
  const filteredTotalPages = Math.max(1, Math.ceil(filteredTotal / PAGE_SIZE));
  const safePage = Math.min(page, filteredTotalPages - 1);
  const startIdx = safePage * PAGE_SIZE;
  const chartsToRender = filteredCharts.slice(startIdx, startIdx + PAGE_SIZE);
  const showFrom = filteredTotal > 0 ? startIdx + 1 : 0;
  const showTo = Math.min(startIdx + PAGE_SIZE, filteredTotal);

  return (
    <>
      {/* Toolbar: search + layout toggle */}
      <div className="mb-3 flex items-center gap-2">
        {pack.charts.length > 6 && (
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground/30 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setPage(0); }}
              placeholder="Filter by title or series..."
              className="w-full h-7 pl-7 pr-2.5 text-[12.5px] border border-border/30 rounded-[var(--radius)] bg-transparent text-foreground placeholder:text-muted-foreground/25 focus:outline-none focus:ring-1 focus:ring-primary/25"
            />
          </div>
        )}
        {!pack.charts.length || pack.charts.length <= 6 ? <div className="flex-1" /> : null}
        <div className="flex items-center border border-border/30 rounded-[var(--radius)] overflow-hidden shrink-0">
          <button onClick={() => { setLayout('1'); setPage(0); }} title="1 column"
            className={`p-1.5 transition-colors ${layout === '1' ? 'bg-foreground/10 text-foreground' : 'text-muted-foreground/30 hover:text-foreground'}`}>
            <Square className="w-3.5 h-3.5" />
          </button>
          <button onClick={() => { setLayout('2'); setPage(0); }} title="2 columns"
            className={`p-1.5 transition-colors ${layout === '2' ? 'bg-foreground/10 text-foreground' : 'text-muted-foreground/30 hover:text-foreground'}`}>
            <Columns2 className="w-3.5 h-3.5" />
          </button>
          <button onClick={() => { setLayout('3'); setPage(0); }} title="3 columns"
            className={`p-1.5 transition-colors ${layout === '3' ? 'bg-foreground/10 text-foreground' : 'text-muted-foreground/30 hover:text-foreground'}`}>
            <LayoutGrid className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <div className={`grid ${LAYOUT_GRID[layout]} gap-3`} style={{ gridAutoRows: LAYOUT_HEIGHT[layout] }}>
        {chartsToRender.map(({ chart, origIdx }, localIdx) => (
          <PackChart
            key={`${pack.id}-${origIdx}`}
            config={chart} index={origIdx} isLight={isLight}
            rawData={chartDataList[origIdx]?.rawData as any}
            isLoading={chartDataList[origIdx]?.isLoading ?? false}
            onRemove={() => onRemoveChart(origIdx)}
            onEdit={() => onEditChart(origIdx)}
            onMoveUp={() => onMoveChart(origIdx, origIdx - 1)}
            onMoveDown={() => onMoveChart(origIdx, origIdx + 1)}
            onCopyMove={() => onCopyMoveChart(origIdx)}
            onRefresh={() => onRefreshChart(origIdx)}
            isFirst={origIdx === 0} isLast={origIdx === pack.charts.length - 1}
            readOnly={readOnly}
            pageIndex={localIdx}
            justSaved={justSavedIndex === origIdx}
          />
        ))}
      </div>

      {/* ── Pagination ── */}
      {filteredTotalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-4 pb-2">
          <span className="text-[11.5px] font-mono text-muted-foreground/40 tabular-nums mr-2">
            {showFrom}–{showTo} of {filteredTotal}{searchQuery && ` (${pack.charts.length} total)`}
          </span>
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={safePage === 0}
            className="w-7 h-7 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/40 hover:text-foreground hover:bg-foreground/[0.06] transition-colors disabled:opacity-40 disabled:pointer-events-none"
            aria-label="Previous page"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          {(() => {
            const pages: (number | '...')[] = [];
            if (filteredTotalPages <= 7) {
              for (let i = 0; i < filteredTotalPages; i++) pages.push(i);
            } else {
              pages.push(0);
              if (safePage > 2) pages.push('...');
              for (let i = Math.max(1, safePage - 1); i <= Math.min(filteredTotalPages - 2, safePage + 1); i++) pages.push(i);
              if (safePage < filteredTotalPages - 3) pages.push('...');
              pages.push(filteredTotalPages - 1);
            }
            return pages.map((p, i) =>
              p === '...' ? (
                <span key={`e-${i}`} className="text-[11.5px] text-muted-foreground/20 px-1">...</span>
              ) : (
                <button
                  key={p}
                  onClick={() => setPage(p as number)}
                  className={`w-7 h-7 flex items-center justify-center rounded-[var(--radius)] text-[11.5px] font-mono transition-colors ${
                    p === safePage
                      ? 'bg-foreground text-background font-bold'
                      : 'text-muted-foreground/40 hover:text-foreground hover:bg-foreground/[0.06]'
                  }`}
                >{(p as number) + 1}</button>
              )
            );
          })()}
          <button
            onClick={() => setPage((p) => Math.min(filteredTotalPages - 1, p + 1))}
            disabled={safePage >= filteredTotalPages - 1}
            className="w-7 h-7 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/40 hover:text-foreground hover:bg-foreground/[0.06] transition-colors disabled:opacity-40 disabled:pointer-events-none"
            aria-label="Next page"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </>
  );
}
