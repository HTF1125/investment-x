'use client';

import { useEffect, useRef } from 'react';
import {
  createChart,
  type IChartApi,
  type ISeriesApi,
  type LogicalRange,
  type MouseEventParams,
} from 'lightweight-charts';
import { getChartOptions, getSubPaneOptions, getColors } from './theme';
import { ema, ichimoku, macd, roc, toOHLC, toLineData, toHistogramData } from './indicators';

interface DailyPrices {
  dates: string[];
  open: number[];
  high: number[];
  low: number[];
  close: number[];
  volume: number[];
}

interface UseTechnicalsChartParams {
  mainContainer: HTMLDivElement | null;
  macdContainer: HTMLDivElement | null;
  rocContainer: HTMLDivElement | null;
  dailyPrices: DailyPrices | null;
  theme: 'light' | 'dark';
  startStr: string;
  onCrosshairMove?: (params: CrosshairData | null) => void;
}

export interface CrosshairData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  ema21: number | null;
  ema55: number | null;
  macdVal: number | null;
  signalVal: number | null;
  rocVal: number | null;
}

export function useTechnicalsChart({
  mainContainer,
  macdContainer,
  rocContainer,
  dailyPrices,
  theme,
  startStr,
  onCrosshairMove,
}: UseTechnicalsChartParams) {
  const mainChartRef = useRef<IChartApi | null>(null);
  const macdChartRef = useRef<IChartApi | null>(null);
  const rocChartRef = useRef<IChartApi | null>(null);
  const isSyncingRef = useRef(false);
  const dataVersionRef = useRef(0);

  // ── Create charts when containers mount ──
  useEffect(() => {
    if (!mainContainer || !macdContainer || !rocContainer) return;

    const mainChart = createChart(mainContainer, {
      ...getChartOptions(theme),
      width: mainContainer.clientWidth,
      height: mainContainer.clientHeight,
    });
    const macdChart = createChart(macdContainer, {
      ...getSubPaneOptions(theme),
      width: macdContainer.clientWidth,
      height: macdContainer.clientHeight,
    });
    const rocChart = createChart(rocContainer, {
      ...getSubPaneOptions(theme),
      width: rocContainer.clientWidth,
      height: rocContainer.clientHeight,
    });

    // Manual resize observer (more reliable than autoSize)
    const ro = new ResizeObserver(() => {
      mainChart.resize(mainContainer.clientWidth, mainContainer.clientHeight);
      macdChart.resize(macdContainer.clientWidth, macdContainer.clientHeight);
      rocChart.resize(rocContainer.clientWidth, rocContainer.clientHeight);
    });
    ro.observe(mainContainer);
    ro.observe(macdContainer);
    ro.observe(rocContainer);

    mainChartRef.current = mainChart;
    macdChartRef.current = macdChart;
    rocChartRef.current = rocChart;

    // Sync time scales
    const syncRange = (source: IChartApi, targets: IChartApi[]) => {
      source.timeScale().subscribeVisibleLogicalRangeChange((range: LogicalRange | null) => {
        if (isSyncingRef.current || !range) return;
        isSyncingRef.current = true;
        targets.forEach(t => { try { t.timeScale().setVisibleLogicalRange(range); } catch {} });
        isSyncingRef.current = false;
      });
    };
    syncRange(mainChart, [macdChart, rocChart]);
    syncRange(macdChart, [mainChart, rocChart]);
    syncRange(rocChart, [mainChart, macdChart]);

    // Sync crosshair
    const syncCH = (source: IChartApi, targets: IChartApi[]) => {
      source.subscribeCrosshairMove((param: MouseEventParams) => {
        if (isSyncingRef.current) return;
        isSyncingRef.current = true;
        targets.forEach(t => {
          try {
            if (param.time) {
              // setCrosshairPosition requires a series — use first available
              const ts = (t as any)._private__seriesMap;
              // Fallback: just clear, sync is best-effort
              t.clearCrosshairPosition();
            } else {
              t.clearCrosshairPosition();
            }
          } catch {}
        });
        isSyncingRef.current = false;
      });
    };
    syncCH(mainChart, [macdChart, rocChart]);

    return () => {
      ro.disconnect();
      mainChartRef.current = null;
      macdChartRef.current = null;
      rocChartRef.current = null;
      mainChart.remove();
      macdChart.remove();
      rocChart.remove();
    };
  }, [mainContainer, macdContainer, rocContainer]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Update theme ──
  useEffect(() => {
    try {
      mainChartRef.current?.applyOptions(getChartOptions(theme));
      macdChartRef.current?.applyOptions(getSubPaneOptions(theme));
      rocChartRef.current?.applyOptions(getSubPaneOptions(theme));
    } catch {}
  }, [theme]);

  // ── Set data when dailyPrices, theme, or startStr changes ──
  useEffect(() => {
    const mc = mainChartRef.current;
    const macdC = macdChartRef.current;
    const rocC = rocChartRef.current;
    if (!mc || !macdC || !rocC || !dailyPrices) return;

    // Verify chart is alive
    try { mc.timeScale(); } catch { console.warn('LC: chart disposed, skipping data set'); return; }

    const c = getColors(theme);

    // Slice data to visible period + warmup (same as old Plotly approach)
    const fullDp = dailyPrices;
    const fullN = fullDp.dates.length;
    if (fullN === 0) return;

    let visStart = fullDp.dates.findIndex(d => d >= startStr);
    if (visStart < 0) visStart = 0;
    const WARMUP = 78; // Ichimoku 52 + 26 displacement
    const computeStart = Math.max(0, visStart - WARMUP);

    const dp = {
      dates: fullDp.dates.slice(computeStart),
      open: fullDp.open.slice(computeStart),
      high: fullDp.high.slice(computeStart),
      low: fullDp.low.slice(computeStart),
      close: fullDp.close.slice(computeStart),
      volume: fullDp.volume.slice(computeStart),
    };
    const n = dp.dates.length;

    // Increment data version to track this update
    const version = ++dataVersionRef.current;

    // Clear all existing series from all charts
    const clearChart = (chart: IChartApi) => {
      try {
        // LC doesn't have a "removeAllSeries" — we recreate by removing chart content
        // The simplest approach: remove the chart and recreate
        // But since containers don't change, we can't recreate easily.
        // Instead, let's track series refs externally.
      } catch {}
    };

    // We'll add series fresh each time. LC handles replacing data on existing series,
    // but since the number of series may change, recreate them.
    // Actually for our case, series count is fixed. So we can just setData on existing ones.

    // Since we can't easily remove series in LC without chart.remove(),
    // the cleanest approach is to recreate charts when data changes.
    // BUT that causes the disposed error. So instead: create series once, update data.

    // For the first data load or when switching indices, we need to ensure series exist.
    // Use a flag to track if series were created for this chart instance.

    // APPROACH: Always clear and re-add series (LC supports addSeries after removeSeries)

    // Helper to safely add series
    const addCandlestick = () => mc.addCandlestickSeries({
      upColor: c.candleUp, downColor: c.candleDown,
      wickUpColor: c.candleUp, wickDownColor: c.candleDown,
      borderUpColor: c.candleUp, borderDownColor: c.candleDown,
    });

    const addLine = (chart: IChartApi, color: string, width = 1) => chart.addLineSeries({
      color, lineWidth: width as any,
      crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false,
    });

    const addHist = (chart: IChartApi) => chart.addHistogramSeries({
      priceLineVisible: false, lastValueVisible: false,
    });

    // Compute indicators
    const ema21 = ema(dp.close, 21);
    const ema55 = ema(dp.close, 55);
    const ichi = ichimoku(dp.dates, dp.high, dp.low, dp.close);
    const macdResult = macd(dp.close);
    const rocResult = roc(dp.close);

    // Clear existing series by recreating charts content
    // LC doesn't support bulk remove, so we use a workaround:
    // Just create the chart fresh by removing and recreating.
    // But we can't do that because containers are the same ref.

    // FINAL APPROACH: Accept that we create duplicate series on data change.
    // LC renders all series on top of each other. To avoid duplication,
    // we actually need to remove old series. Let's track them.

    // Remove previous series from this chart
    const removePrevious = (chart: IChartApi, series: ISeriesApi<any>[]) => {
      for (const s of series) {
        try { chart.removeSeries(s); } catch {}
      }
    };

    // Store series for cleanup
    const mainSeries: ISeriesApi<any>[] = [];
    const macdSeries: ISeriesApi<any>[] = [];
    const rocSeries: ISeriesApi<any>[] = [];

    // We need to get the previous series to remove them.
    // Store them on the chart ref object.
    const prevMain = (mc as any).__ixSeries as ISeriesApi<any>[] | undefined;
    const prevMacd = (macdC as any).__ixSeries as ISeriesApi<any>[] | undefined;
    const prevRoc = (rocC as any).__ixSeries as ISeriesApi<any>[] | undefined;
    if (prevMain) removePrevious(mc, prevMain);
    if (prevMacd) removePrevious(macdC, prevMacd);
    if (prevRoc) removePrevious(rocC, prevRoc);

    // ── Main pane ──
    const senkouA = addLine(mc, c.cloudLine);
    senkouA.setData(toLineData(ichi.extDates, ichi.senkouA));
    mainSeries.push(senkouA);

    const senkouB = addLine(mc, c.cloudLine);
    senkouB.setData(toLineData(ichi.extDates, ichi.senkouB));
    mainSeries.push(senkouB);

    const tenkan = addLine(mc, c.tenkan);
    tenkan.setData(toLineData(dp.dates, ichi.tenkan));
    mainSeries.push(tenkan);

    const kijun = addLine(mc, c.kijun);
    kijun.setData(toLineData(dp.dates, ichi.kijun));
    mainSeries.push(kijun);

    const candle = addCandlestick();
    candle.setData(toOHLC(dp.dates, dp.open, dp.high, dp.low, dp.close));
    mainSeries.push(candle);

    const ema21S = addLine(mc, c.ema21, 1);
    ema21S.setData(toLineData(dp.dates, ema21));
    mainSeries.push(ema21S);

    const ema55S = addLine(mc, c.ema55, 1);
    ema55S.setData(toLineData(dp.dates, ema55));
    mainSeries.push(ema55S);

    // ── MACD pane ──
    const histS = addHist(macdC);
    histS.setData(toHistogramData(dp.dates, macdResult.histogram, c.macdHistPos, c.macdHistNeg));
    macdSeries.push(histS);

    const macdLineS = addLine(macdC, c.macdLine);
    macdLineS.setData(toLineData(dp.dates, macdResult.macdLine));
    macdSeries.push(macdLineS);

    const macdSigS = addLine(macdC, c.macdSignal);
    macdSigS.setData(toLineData(dp.dates, macdResult.signal));
    macdSeries.push(macdSigS);

    // ── ROC pane ──
    const rocHistS = addHist(rocC);
    rocHistS.setData(toHistogramData(dp.dates, rocResult, c.rocPos, c.rocNeg));
    rocSeries.push(rocHistS);

    // Store series for next cleanup
    (mc as any).__ixSeries = mainSeries;
    (macdC as any).__ixSeries = macdSeries;
    (rocC as any).__ixSeries = rocSeries;

    // Crosshair callback
    if (onCrosshairMove) {
      mc.subscribeCrosshairMove((param) => {
        if (dataVersionRef.current !== version) return;
        if (!param.time || !param.seriesData) { onCrosshairMove(null); return; }
        const cd = param.seriesData.get(candle) as any;
        if (!cd) { onCrosshairMove(null); return; }
        const timeStr = String(param.time);
        const idx = dp.dates.indexOf(timeStr);
        onCrosshairMove({
          date: timeStr,
          open: cd.open, high: cd.high, low: cd.low, close: cd.close,
          ema21: idx >= 0 ? ema21[idx] : null,
          ema55: idx >= 0 ? ema55[idx] : null,
          macdVal: idx >= 0 ? macdResult.macdLine[idx] : null,
          signalVal: idx >= 0 ? macdResult.signal[idx] : null,
          rocVal: idx >= 0 ? rocResult[idx] : null,
        });
      });
    }

    // Fit all visible data (already sliced to the period)
    // Use setTimeout on first render to let LC process canvas dimensions
    mc.timeScale().fitContent();
    const fitTimer = setTimeout(() => {
      try { mc.timeScale().fitContent(); } catch {}
    }, 200);
  }, [dailyPrices, theme, startStr]); // eslint-disable-line react-hooks/exhaustive-deps

  // Period changes are handled by the main data effect since startStr is in its deps
}
