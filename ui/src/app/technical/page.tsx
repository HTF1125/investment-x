'use client';

import dynamic from 'next/dynamic';
import { useMemo, useState } from 'react';
import AppShell from '@/components/AppShell';
import { Activity, CandlestickChart, Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { useTheme } from '@/context/ThemeContext';

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center">
      <Loader2 className="w-6 h-6 animate-spin text-sky-400" />
    </div>
  ),
}) as any;

type Frequency = 'D' | 'W' | 'M';

const RANGE_BY_FREQ: Record<Frequency, { years: number; interval: string }> = {
  D: { years: 1, interval: '1d' },
  W: { years: 3, interval: '1wk' },
  M: { years: 10, interval: '1mo' },
};

function isoDateYearsAgo(years: number): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() - years);
  return d.toISOString().slice(0, 10);
}

export default function TechnicalPage() {
  const today = new Date();
  const todayStr = today.toISOString().slice(0, 10);
  const { theme } = useTheme();
  const [tickerInput, setTickerInput] = useState('SPY');
  const [params, setParams] = useState({
    ticker: 'SPY',
    freq: 'D' as Frequency,
    startDate: isoDateYearsAgo(1),
    endDate: todayStr,
    setupFrom: 9,
    countdownFrom: 13,
  });

  const interval = RANGE_BY_FREQ[params.freq].interval;

  const onFreqChange = (next: Frequency) => {
    setParams((prev) => ({
      ...prev,
      freq: next,
      startDate: isoDateYearsAgo(RANGE_BY_FREQ[next].years),
      endDate: todayStr,
    }));
  };

  const commitTicker = () => {
    const nextTicker = (tickerInput || 'SPY').trim().toUpperCase();
    setTickerInput(nextTicker);
    setParams((prev) => ({ ...prev, ticker: nextTicker || 'SPY' }));
  };

  const queryKey = useMemo(
    () => [
      'technical-elliott',
      params.ticker,
      interval,
      params.startDate,
      params.endDate,
      params.setupFrom,
      params.countdownFrom,
    ],
    [params, interval]
  );

  const { data: fig, isLoading, isFetching, error } = useQuery({
    queryKey,
    queryFn: () =>
      apiFetchJson(
        `/api/technical/elliott?ticker=${encodeURIComponent(params.ticker || 'SPY')}&period=10y&interval=${encodeURIComponent(interval)}&start=${encodeURIComponent(params.startDate)}&end=${encodeURIComponent(params.endDate)}&setup_from=${params.setupFrom}&countdown_from=${params.countdownFrom}&label_cooldown=0`
      ),
    staleTime: 60_000,
  });

  const isLight = theme === 'light';
  const cleanedFigure = useMemo(() => {
    if (!fig) return null;
    const cloned = JSON.parse(JSON.stringify(fig));
    const fg = isLight ? '#0f172a' : '#dbeafe';
    const grid = isLight ? 'rgba(0,0,0,0.08)' : 'rgba(148,163,184,0.12)';
    cloned.layout = {
      ...cloned.layout,
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { ...(cloned.layout?.font || {}), color: fg, family: 'Ubuntu, Inter, Roboto, sans-serif' },
    };
    const axes = ['xaxis', 'yaxis', 'xaxis2', 'yaxis2'];
    axes.forEach((ax) => {
      if (cloned.layout?.[ax]) {
        cloned.layout[ax].gridcolor = grid;
        cloned.layout[ax].linecolor = isLight ? 'rgba(0,0,0,0.25)' : 'rgba(226,232,240,0.65)';
        cloned.layout[ax].tickfont = { ...(cloned.layout[ax].tickfont || {}), color: fg };
      }
    });
    return cloned;
  }, [fig, isLight]);

  return (
    <AppShell hideFooter>
      <section className="h-[calc(100vh-3rem)] w-full overflow-hidden">
        <div className="h-full max-w-[1800px] mx-auto px-4 md:px-6 lg:px-8 pt-3 pb-3 flex flex-col gap-2 overflow-hidden">
          <div className="rounded-2xl border border-border/50 bg-gradient-to-r from-indigo-500/10 to-sky-500/10 px-4 py-3 shrink-0">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center">
                  <CandlestickChart className="w-4 h-4 text-indigo-300" />
                </div>
                <div>
                  <div className="text-base font-semibold text-foreground">Technical</div>
                  <div className="text-xs text-muted-foreground">Press Enter on ticker to refresh instantly</div>
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <span className="rounded-lg border border-emerald-400/30 bg-emerald-500/10 px-2 py-1 text-emerald-200 flex items-center gap-1">
                  <Activity className="w-3.5 h-3.5" />
                  {isFetching ? 'Updating' : 'Live'}
                </span>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-border/50 bg-card/20 backdrop-blur-sm p-3 md:p-4 shrink-0">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
              <div className="col-span-2 md:col-span-1">
                <label className="block text-[11px] text-muted-foreground mb-1.5">Ticker</label>
                <input
                  value={tickerInput}
                  onChange={(e) => setTickerInput(e.target.value.toUpperCase())}
                  onBlur={commitTicker}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      commitTicker();
                    }
                  }}
                  className="w-full px-3 py-2.5 rounded-xl border border-border/60 bg-background/40 text-sm font-semibold tracking-wide focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                  placeholder="SPY"
                />
              </div>

              <div className="col-span-1">
                <label className="block text-[11px] text-muted-foreground mb-1.5">Frequency</label>
                <select
                  value={params.freq}
                  onChange={(e) => onFreqChange(e.target.value as Frequency)}
                  className="w-full px-3 py-2.5 rounded-xl border border-border/60 bg-background/40 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                >
                  <option value="D">Daily (D)</option>
                  <option value="W">Weekly (W)</option>
                  <option value="M">Monthly (M)</option>
                </select>
              </div>

              <div className="col-span-1">
                <label className="block text-[11px] text-muted-foreground mb-1.5">Setup Filter</label>
                <select
                  value={params.setupFrom}
                  onChange={(e) =>
                    setParams((prev) => ({ ...prev, setupFrom: Number(e.target.value) }))
                  }
                  className="w-full px-3 py-2.5 rounded-xl border border-border/60 bg-background/40 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                >
                  {[1, 5, 7, 9].map((v) => (
                    <option key={v} value={v}>
                      Setup {v}+
                    </option>
                  ))}
                </select>
              </div>

              <div className="col-span-1">
                <label className="block text-[11px] text-muted-foreground mb-1.5">Countdown Filter</label>
                <select
                  value={params.countdownFrom}
                  onChange={(e) =>
                    setParams((prev) => ({ ...prev, countdownFrom: Number(e.target.value) }))
                  }
                  className="w-full px-3 py-2.5 rounded-xl border border-border/60 bg-background/40 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                >
                  {[9, 10, 11, 12, 13].map((v) => (
                    <option key={v} value={v}>
                      CD {v}+
                    </option>
                  ))}
                </select>
              </div>

            </div>
          </div>

          <div className="rounded-xl border border-border/60 bg-black/20 overflow-hidden w-full flex-1 min-h-0">
            {isLoading && (
              <div className="h-full w-full flex items-center justify-center">
                <Loader2 className="w-6 h-6 animate-spin text-sky-400" />
              </div>
            )}
            {!isLoading && error && (
              <div className="h-full w-full flex items-center justify-center text-rose-400 text-sm">
                {(error as Error)?.message || 'Failed to load chart'}
              </div>
            )}
            {!isLoading && cleanedFigure && (
              <Plot
                data={cleanedFigure.data}
                layout={{ ...cleanedFigure.layout, autosize: true }}
                config={{
                  responsive: true,
                  displaylogo: false,
                  displayModeBar: true,
                  scrollZoom: false,
                }}
                style={{ width: '100%', height: '100%' }}
                useResizeHandler
              />
            )}
            {!isLoading && !cleanedFigure && !error && (
              <div className="h-full w-full flex items-center justify-center text-muted-foreground text-sm">
                No chart data
              </div>
            )}
          </div>
        </div>
      </section>
    </AppShell>
  );
}
