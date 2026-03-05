/** Metadata for a custom chart as returned by the dashboard API. */
export interface ChartMeta {
  id: string;
  name: string;
  category: string | null;
  description: string | null;
  updated_at: string | null;
  rank: number;
  public?: boolean;
  created_by_user_id?: string | null;
  created_by_email?: string | null;
  created_by_name?: string | null;
  code?: string;
  figure?: Record<string, unknown>;
  chart_style?: string | null;
}

/** Chart list item as returned by /api/custom/charts. */
export interface CustomChartListItem {
  id: string;
  name?: string | null;
  category?: string | null;
  description?: string | null;
  tags?: string[];
  public?: boolean;
  rank?: number;
  created_by_user_id?: string | null;
  created_by_email?: string | null;
  created_by_name?: string | null;
  code?: string | null;
  figure?: Record<string, unknown>;
}
