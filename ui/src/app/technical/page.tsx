'use client';

import dynamic from 'next/dynamic';
import { useMemo, useState } from 'react';
import AppShell from '@/components/AppShell';
import { Activity, CandlestickChart, Loader2, Sparkles } from 'lucide-react';
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
const FREQ_LABEL: Record<Frequency, string> = {
  D: 'Daily',
  W: 'Weekly',
  M: 'Monthly',
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
    const panelBg = isLight ? 'rgba(255,255,255,0.95)' : 'rgba(2,6,23,0.72)';
    cloned.layout = {
      ...cloned.layout,
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { ...(cloned.layout?.font || {}), color: fg, family: 'Ubuntu, Inter, Roboto, sans-serif' },
      legend: {
        ...(cloned.layout?.legend || {}),
        bgcolor: panelBg,
        bordercolor: isLight ? 'rgba(15,23,42,0.14)' : 'rgba(148,163,184,0.35)',
        font: { ...(cloned.layout?.legend?.font || {}), color: fg },
      },
      hoverlabel: {
        ...(cloned.layout?.hoverlabel || {}),
        bgcolor: isLight ? 'rgba(255,255,255,0.96)' : 'rgba(15,23,42,0.92)',
        bordercolor: isLight ? 'rgba(15,23,42,0.18)' : 'rgba(148,163,184,0.35)',
        font: { ...(cloned.layout?.hoverlabel?.font || {}), color: fg },
      },
    };
    const axes = ['xaxis', 'yaxis', 'xaxis2', 'yaxis2', 'xaxis3', 'yaxis3'];
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
      <section className="h-[calc(100dvh-3rem)] min-h-[calc(100vh-3rem)] w-full overflow-hidden">
        <div className="h-full max-w-[1800px] mx-auto px-4 md:px-6 lg:px-8 pt-3 pb-3 flex flex-col gap-3 overflow-x-hidden overflow-y-auto md:overflow-hidden">
          <div className="rounded-2xl border border-border/60 bg-gradient-to-r from-sky-500/10 via-indigo-500/10 to-cyan-500/10 px-4 py-3 md:px-5 md:py-4 shrink-0">
            <div className="flex flex-wrap md:flex-nowrap items-start md:items-center justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-10 h-10 rounded-xl bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center shrink-0">
                  <CandlestickChart className="w-5 h-5 text-indigo-300" />
                </div>
                <div className="min-w-0">
                  <div className="text-base md:text-lg font-semibold text-foreground">Technical Workbench</div>
                  <div className="text-xs text-muted-foreground truncate">TradingView-style structure: Price + Elliott + MACD + RSI Mean</div>
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs flex-wrap justify-end">
                <span className="rounded-lg border border-emerald-400/30 bg-emerald-500/10 px-2.5 py-1 text-emerald-200 flex items-center gap-1">
                  <Activity className="w-3.5 h-3.5" />
                  {isFetching ? 'Updating' : 'Live'}
                </span>
                <span className="rounded-lg border border-sky-400/30 bg-sky-500/10 px-2.5 py-1 text-sky-200 flex items-center gap-1">
                  <Sparkles className="w-3.5 h-3.5" />
                  MA 5/20/200 · MACD · RSI Mean
                </span>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-border/60 bg-card/25 backdrop-blur-sm p-2.5 md:p-3 shrink-0">
            <div className="flex flex-wrap xl:flex-nowrap items-end gap-2">
              <div className="min-w-[170px] flex-1 xl:flex-none xl:w-[220px]">
                <label className="block text-[10px] text-muted-foreground mb-1">Ticker</label>
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
                  className="w-full px-2.5 py-2 rounded-lg border border-border/60 bg-background/40 text-xs font-semibold tracking-wide focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                  placeholder="SPY"
                />
              </div>

              <div className="min-w-[160px] flex-1 xl:flex-none xl:w-[190px]">
                <label className="block text-[10px] text-muted-foreground mb-1">Frequency</label>
                <select
                  value={params.freq}
                  onChange={(e) => onFreqChange(e.target.value as Frequency)}
                  className="w-full px-2.5 py-2 rounded-lg border border-border/60 bg-background/40 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                >
                  <option value="D">Daily (D)</option>
                  <option value="W">Weekly (W)</option>
                  <option value="M">Monthly (M)</option>
                </select>
              </div>

              <div className="min-w-[160px] flex-1 xl:flex-none xl:w-[180px]">
                <label className="block text-[10px] text-muted-foreground mb-1">Setup Filter</label>
                <select
                  value={params.setupFrom}
                  onChange={(e) =>
                    setParams((prev) => ({ ...prev, setupFrom: Number(e.target.value) }))
                  }
                  className="w-full px-2.5 py-2 rounded-lg border border-border/60 bg-background/40 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                >
                  {[1, 5, 7, 9].map((v) => (
                    <option key={v} value={v}>
                      Setup {v}+
                    </option>
                  ))}
                </select>
              </div>

              <div className="min-w-[160px] flex-1 xl:flex-none xl:w-[190px]">
                <label className="block text-[10px] text-muted-foreground mb-1">Countdown Filter</label>
                <select
                  value={params.countdownFrom}
                  onChange={(e) =>
                    setParams((prev) => ({ ...prev, countdownFrom: Number(e.target.value) }))
                  }
                  className="w-full px-2.5 py-2 rounded-lg border border-border/60 bg-background/40 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                >
                  {[9, 10, 11, 12, 13].map((v) => (
                    <option key={v} value={v}>
                      CD {v}+
                    </option>
                  ))}
                </select>
              </div>

              <button
                onClick={commitTicker}
                className="px-3 py-2 rounded-lg text-xs font-semibold border border-sky-500/40 bg-sky-500/15 hover:bg-sky-500/25 text-sky-200 transition-colors"
                title="Refresh chart"
              >
                Refresh
              </button>
            </div>
          </div>

          <div className="rounded-2xl border border-border/60 bg-black/20 overflow-hidden w-full flex-1 min-h-0 flex flex-col">
            <div className="px-3 md:px-4 py-2 border-b border-border/50 bg-card/30 flex items-center justify-between gap-2 text-[11px]">
              <div className="font-semibold text-foreground truncate">
                {params.ticker} · {FREQ_LABEL[params.freq]} · Elliott + MACD + RSI
              </div>
              <div className="text-muted-foreground shrink-0">Legend cleaned and grouped</div>
            </div>
            <div className="flex-1 min-h-0">
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
                    modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d', 'toggleSpikelines'],
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
        </div>
      </section>
    </AppShell>
  );
}
