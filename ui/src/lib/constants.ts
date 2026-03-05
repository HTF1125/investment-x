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
  technical: {
    elliott: (...args: unknown[]) => ['technical-elliott', ...args] as const,
    overlays: (...args: unknown[]) => ['technical-overlays', ...args] as const,
    summary: (...args: unknown[]) => ['technical-summary', ...args] as const,
  },
  admin: {
    users: (search: string) => ['admin-users', search] as const,
    logs: (...args: unknown[]) => ['admin-logs', ...args] as const,
  },
} as const;
