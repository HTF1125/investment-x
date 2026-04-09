'use client';

import React, { useRef, useEffect, useImperativeHandle, forwardRef } from 'react';
import { createChart, type IChartApi, type DeepPartial, type ChartOptions } from 'lightweight-charts';

export interface LightweightChartHandle {
  chart: IChartApi | null;
}

interface Props {
  options: DeepPartial<ChartOptions>;
  className?: string;
  style?: React.CSSProperties;
}

/**
 * Thin React wrapper around TradingView Lightweight Charts.
 * Creates a chart instance on mount, handles resize, cleans up on unmount.
 * Exposes the IChartApi via ref for imperative series management.
 */
const LightweightChart = forwardRef<LightweightChartHandle, Props>(
  ({ options, className = '', style }, ref) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);

    useImperativeHandle(ref, () => ({
      get chart() { return chartRef.current; },
    }));

    // Create chart on mount
    useEffect(() => {
      if (!containerRef.current) return;

      const chart = createChart(containerRef.current, {
        ...options,
        width: containerRef.current.clientWidth,
        height: containerRef.current.clientHeight,
        autoSize: true,
      });
      chartRef.current = chart;

      return () => {
        chart.remove();
        chartRef.current = null;
      };
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    // Update options (theme changes)
    useEffect(() => {
      chartRef.current?.applyOptions(options);
    }, [options]);

    return (
      <div
        ref={containerRef}
        className={className}
        style={{ width: '100%', height: '100%', ...style }}
      />
    );
  }
);

LightweightChart.displayName = 'LightweightChart';
export default LightweightChart;
