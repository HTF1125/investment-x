'use client';

import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { Loader2, TrendingUp, TrendingDown, Minus, RefreshCw } from 'lucide-react';

interface PositioningItem {
  name: string;
  source: string;
  category: string;
  latest_value: number | null;
  last_date: string | null;
  num_data: number | null;
}

interface PositioningResponse {
  positioning: Record<string, PositioningItem>;
}

interface CollectorStatus {
  name: string;
  display_name: string;
  category: string;
  schedule: string;
  last_fetch_at: string | null;
  last_success_at: string | null;
  last_error: string | null;
  last_data_date: string | null;
  fetch_count: number;
  error_count: number;
}

interface StatusResponse {
  collectors: CollectorStatus[];
}

function formatValue(value: number | null, category: string): string {
  if (value === null || value === undefined) return '—';
  if (category === 'Sentiment') {
    if (Math.abs(value) < 1) return (value * 100).toFixed(1) + '%';
    return value.toFixed(1) + '%';
  }
  if (category === 'Volatility') return value.toFixed(2);
  if (Math.abs(value) > 1_000_000) return (value / 1_000_000).toFixed(1) + 'M';
  if (Math.abs(value) > 1_000) return (value / 1_000).toFixed(1) + 'K';
  return value.toFixed(2);
}

function SentimentGauge({ value, label }: { value: number | null; label: string }) {
  const pct = value !== null ? Math.min(100, Math.max(0, value)) : 50;
  const color = pct > 60 ? 'text-emerald-400' : pct < 40 ? 'text-rose-400' : 'text-amber-400';
  return (
    <div className="flex flex-col gap-1">
      <span className="stat-label">{label}</span>
      <div className="h-1.5 bg-border/20 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${pct > 60 ? 'bg-emerald-500' : pct < 40 ? 'bg-rose-500' : 'bg-amber-500'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-sm font-mono font-semibold ${color}`}>
        {value !== null ? value.toFixed(1) + '%' : '—'}
      </span>
    </div>
  );
}

function IndicatorCard({
  code,
  item,
}: {
  code: string;
  item: PositioningItem;
}) {
  const val = item.latest_value;
  const isPositive = val !== null && val > 0;
  const isNegative = val !== null && val < 0;
  const Icon = isPositive ? TrendingUp : isNegative ? TrendingDown : Minus;
  const color = isPositive ? 'text-emerald-400' : isNegative ? 'text-rose-400' : 'text-muted-foreground';

  return (
    <div className="panel-card p-3 flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <span className="stat-label truncate" title={item.name}>{item.name}</span>
        <Icon className={`w-3 h-3 shrink-0 ${color}`} />
      </div>
      <span className={`text-lg font-mono font-bold ${color}`}>
        {formatValue(val, item.category)}
      </span>
      <div className="flex items-center justify-between">
        <span className="text-[9px] font-mono text-muted-foreground/40 uppercase">{item.source}</span>
        <span className="text-[9px] font-mono text-muted-foreground/30">{item.last_date || ''}</span>
      </div>
    </div>
  );
}

export default function PositioningTab() {
  const { data: posData, isLoading: posLoading } = useQuery<PositioningResponse>({
    queryKey: ['positioning-overview'],
    queryFn: () => apiFetchJson<PositioningResponse>('/api/collectors/positioning'),
    staleTime: 60_000,
  });

  const { data: statusData, isLoading: statusLoading } = useQuery<StatusResponse>({
    queryKey: ['collector-statuses'],
    queryFn: () => apiFetchJson<StatusResponse>('/api/collectors/status'),
    staleTime: 60_000,
  });

  if (posLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground/40" />
      </div>
    );
  }

  const positioning = posData?.positioning || {};
  const collectors = statusData?.collectors || [];

  // Group by category
  const categories: Record<string, [string, PositioningItem][]> = {};
  for (const [code, item] of Object.entries(positioning)) {
    const cat = item.category || 'Other';
    if (!categories[cat]) categories[cat] = [];
    categories[cat].push([code, item]);
  }

  // Sort categories
  const categoryOrder = ['Positioning', 'Sentiment', 'Volatility', 'Dark Pool'];
  const sortedCategories = Object.entries(categories).sort(
    ([a], [b]) => (categoryOrder.indexOf(a) === -1 ? 99 : categoryOrder.indexOf(a)) -
      (categoryOrder.indexOf(b) === -1 ? 99 : categoryOrder.indexOf(b)),
  );

  // Extract AAII for sentiment gauge
  const aaiBull = positioning['AAII_BULL']?.latest_value ?? null;
  const aaiBear = positioning['AAII_BEAR']?.latest_value ?? null;
  const totalPC = positioning['CBOE_TOTAL_PC']?.latest_value ?? null;
  const vixContango = positioning['VIX_CONTANGO_RATIO']?.latest_value ?? null;

  return (
    <div className="px-5 md:px-8 py-5 max-w-[1600px] mx-auto space-y-6">
      {/* Summary Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="panel-card p-4">
          <SentimentGauge value={aaiBull} label="AAII Bullish %" />
        </div>
        <div className="panel-card p-4">
          <SentimentGauge value={aaiBear} label="AAII Bearish %" />
        </div>
        <div className="panel-card p-4">
          <div className="flex flex-col gap-1">
            <span className="stat-label">Put/Call Ratio</span>
            <span className={`text-lg font-mono font-bold ${totalPC && totalPC > 1 ? 'text-rose-400' : 'text-emerald-400'}`}>
              {totalPC !== null ? totalPC.toFixed(2) : '—'}
            </span>
            <span className="text-[9px] font-mono text-muted-foreground/40">
              {totalPC && totalPC > 1 ? 'BEARISH' : totalPC && totalPC < 0.7 ? 'BULLISH' : 'NEUTRAL'}
            </span>
          </div>
        </div>
        <div className="panel-card p-4">
          <div className="flex flex-col gap-1">
            <span className="stat-label">VIX Contango</span>
            <span className={`text-lg font-mono font-bold ${vixContango && vixContango > 1 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {vixContango !== null ? vixContango.toFixed(2) : '—'}
            </span>
            <span className="text-[9px] font-mono text-muted-foreground/40">
              {vixContango && vixContango > 1 ? 'CONTANGO' : 'BACKWARDATION'}
            </span>
          </div>
        </div>
      </div>

      {/* Category Grids */}
      {sortedCategories.map(([category, items]) => (
        <div key={category}>
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.06em] text-muted-foreground/60 mb-3">
            {category}
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
            {items.map(([code, item]) => (
              <IndicatorCard key={code} code={code} item={item} />
            ))}
          </div>
        </div>
      ))}

      {/* Collector Status */}
      {collectors.length > 0 && (
        <div>
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.06em] text-muted-foreground/60 mb-3">
            Collector Status
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {collectors.map((c) => (
              <div key={c.name} className="panel-card p-3 flex items-center justify-between">
                <div className="flex flex-col gap-0.5 min-w-0">
                  <span className="text-xs font-semibold text-foreground/80 truncate">{c.display_name}</span>
                  <span className="text-[9px] font-mono text-muted-foreground/40">
                    {c.last_data_date ? `Last: ${c.last_data_date}` : 'No data yet'}
                    {c.fetch_count > 0 ? ` · ${c.fetch_count} runs` : ''}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  {c.last_error ? (
                    <span className="w-2 h-2 rounded-full bg-destructive" title={c.last_error} />
                  ) : c.last_success_at ? (
                    <span className="w-2 h-2 rounded-full bg-success" />
                  ) : (
                    <span className="w-2 h-2 rounded-full bg-border/40" />
                  )}
                  <span className="text-[9px] font-mono text-muted-foreground/30 uppercase">{c.schedule}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {Object.keys(positioning).length === 0 && !posLoading && (
        <div className="flex flex-col items-center justify-center min-h-[40vh] gap-3">
          <RefreshCw className="w-8 h-8 text-muted-foreground/20" />
          <p className="text-sm text-muted-foreground/50 font-mono">
            No positioning data yet. Run collectors to populate.
          </p>
        </div>
      )}
    </div>
  );
}
