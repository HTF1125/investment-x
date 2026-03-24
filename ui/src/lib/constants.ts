/** Default boilerplate code for the chart editor. */
export const DEFAULT_CHART_CODE = `# Investment-X Analysis Studio
# Available: pd, px, go, np, Series, MultiSeries, apply_theme(fig)
# MUST define a variable 'fig' at the end

import pandas as pd
import plotly.express as px

data = {
    'Year': [2020, 2021, 2022, 2023, 2024],
    'Value': [100, 120, 110, 135, 150]
}
df = pd.DataFrame(data)

fig = px.bar(df, x='Year', y='Value', title='New Analysis')
apply_theme(fig)
`;

// ── Date range presets (shared across chart pages) ──

export const RANGE_MAP: Record<string, number> = {
  '1M': 1, '3M': 3, '6M': 6, 'YTD': -1, '1Y': 12, '2Y': 24, '3Y': 36, '5Y': 60, '10Y': 120, '20Y': 240, '30Y': 360, '50Y': 600, 'MAX': 0,
};

export const RANGE_PRESETS = Object.entries(RANGE_MAP).map(([label, months]) => ({ label, months }));

export function getPresetStartDate(months: number): string {
  if (months === 0) return '';
  const now = new Date();
  if (months === -1) return `${now.getFullYear()}-01-01`;
  const d = new Date(now);
  d.setMonth(d.getMonth() - months);
  return d.toISOString().slice(0, 10);
}

/** TanStack Query key factories for consistent cache management. */
export const queryKeys = {
  dashboard: {
    summary: () => ['dashboard-summary'] as const,
  },
  charts: {
    all: () => ['charts'] as const,
    detail: (id: string) => ['charts', id] as const,
    figure: (id: string) => ['chart-figure', id] as const,
  },
  timeseries: {
    list: (params: Record<string, unknown>) => ['timeseries', params] as const,
  },
  admin: {
    users: (search: string) => ['admin-users', search] as const,
    logs: (...args: unknown[]) => ['admin-logs', ...args] as const,
  },
} as const;
