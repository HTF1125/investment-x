import React from 'react';
import { LineChart, BarChart3, AreaChart, ScatterChart, Layers } from 'lucide-react';
import type { TransformType, LineStyle, ChartType } from './types';

export const TRANSFORMS: { key: TransformType; label: string; hasParam?: boolean; defaultParam?: number }[] = [
  { key: 'none', label: 'None' },
  { key: 'pctchg', label: '%Chg', hasParam: true, defaultParam: 1 },
  { key: 'yoy', label: 'YoY%' },
  { key: 'ma', label: 'MA', hasParam: true, defaultParam: 20 },
  { key: 'zscore', label: 'Z-Score', hasParam: true, defaultParam: 252 },
  { key: 'diff', label: 'Diff', hasParam: true, defaultParam: 1 },
  { key: 'drawdown', label: 'Drawdown' },
  { key: 'rebase', label: 'Rebase' },
  { key: 'log', label: 'Log' },
];

export const LINE_STYLES: { key: LineStyle; label: string; preview: string }[] = [
  { key: 'solid', label: 'Solid', preview: '\u2500\u2500\u2500' },
  { key: 'dash', label: 'Dash', preview: '\u2504\u2504\u2504' },
  { key: 'dot', label: 'Dot', preview: '\u00B7\u00B7\u00B7\u00B7' },
  { key: 'dashdot', label: 'DashDot', preview: '\u2504\u00B7\u2504' },
];

export const LINE_WIDTHS = [1, 1.5, 2.5];

export const CHART_TYPES: { key: ChartType; label: string; icon: React.ReactNode }[] = [
  { key: 'line', label: 'Line', icon: React.createElement(LineChart, { className: 'w-3.5 h-3.5' }) },
  { key: 'bar', label: 'Bar', icon: React.createElement(BarChart3, { className: 'w-3.5 h-3.5' }) },
  { key: 'area', label: 'Area', icon: React.createElement(AreaChart, { className: 'w-3.5 h-3.5' }) },
  { key: 'scatter', label: 'Scatter', icon: React.createElement(ScatterChart, { className: 'w-3.5 h-3.5' }) },
  { key: 'stackedbar', label: 'Stk Bar', icon: React.createElement(Layers, { className: 'w-3.5 h-3.5' }) },
  { key: 'stackedarea', label: 'Stk Area', icon: React.createElement(Layers, { className: 'w-3.5 h-3.5' }) },
];
