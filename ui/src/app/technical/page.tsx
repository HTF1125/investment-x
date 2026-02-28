'use client';

import dynamic from 'next/dynamic';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import AppShell from '@/components/AppShell';
import NavigatorShell from '@/components/NavigatorShell';
import { Activity, Loader2, Plus, X, BrainCircuit, RefreshCw } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetchJson, apiFetch } from '@/lib/api';
import { useTheme } from '@/context/ThemeContext';
import ReactMarkdown from 'react-markdown';

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center">
      <Loader2 className="w-5 h-5 animate-spin text-sky-400" />
    </div>
  ),
}) as any;

// ─── Types & Constants ────────────────────────────────────────────────────────

type Frequency = 'D' | 'W' | 'M';

const FREQ_CONFIG: Record<Frequency, { years: number; interval: string; label: string }> = {
  D: { years: 1, interval: '1d', label: 'Daily' },
  W: { years: 3, interval: '1wk', label: 'Weekly' },
  M: { years: 10, interval: '1mo', label: 'Monthly' },
};

const DEFAULT_WATCHLIST = ['SPY', 'QQQ', 'GLD', 'TLT'];
const WATCHLIST_KEY = 'technical-watchlist';

function isoDateYearsAgo(years: number): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() - years);
  return d.toISOString().slice(0, 10);
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function TechnicalPage() {
  const { theme } = useTheme();
  const isLight = theme === 'light';
  const today = todayIso();
  const addInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  // ── Preferences Persistence ─────────────────────────────────────────────
  const prefQuery = useQuery({
    queryKey: ['user-preferences'],
    queryFn: () => apiFetchJson('/api/user/preferences'),
  });

  const prefMutation = useMutation({
    mutationFn: (settings: any) => 
      apiFetch('/api/user/preferences', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['user-preferences'] }),
  });

  const [watchlist, setWatchlist] = useState<string[]>(DEFAULT_WATCHLIST);
  const [addInput, setAddInput] = useState('');

  useEffect(() => {
    if (prefQuery.data?.settings?.technical_watchlist) {
      setWatchlist(prefQuery.data.settings.technical_watchlist);
    }
  }, [prefQuery.data]);

  const updateWatchlist = useCallback((newList: string[]) => {
    setWatchlist(newList);
    const currentSettings = prefQuery.data?.settings || {};
    prefMutation.mutate({ ...currentSettings, technical_watchlist: newList });
  }, [prefQuery.data, prefMutation]);

  const addTicker = useCallback(() => {
    const t = addInput.trim().toUpperCase();
    if (!t || watchlist.includes(t)) { setAddInput(''); return; }
    updateWatchlist([...watchlist, t]);
    setAddInput('');
  }, [addInput, watchlist, updateWatchlist]);

  const removeTicker = useCallback((ticker: string) => {
    updateWatchlist(watchlist.filter((t) => t !== ticker));
  }, [watchlist, updateWatchlist]);

  // ── Controls state ───────────────────────────────────────────────────────
  const [activeTicker, setActiveTicker] = useState(watchlist[0] ?? 'SPY');
  const [freq, setFreq] = useState<Frequency>('D');
  const [startDate, setStartDate] = useState(() => isoDateYearsAgo(FREQ_CONFIG.D.years));
  const [endDate, setEndDate] = useState(today);
  const [setupFrom, setSetupFrom] = useState(9);
  const [countdownFrom, setCountdownFrom] = useState(13);
  const [cooldown, setCooldown] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const plotContainerRef = useRef<HTMLDivElement>(null);
  const plotGraphDivRef = useRef<HTMLElement | null>(null);

  // Resize Plotly when the container changes size (sidebar toggle, etc.)
  useEffect(() => {
    const el = plotContainerRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(() => {
      const gd = plotGraphDivRef.current;
      if (!gd || !gd.isConnected) return;
      import('plotly.js-dist-min')
        .then(({ default: Plotly }) => { (Plotly as any).Plots.resize(gd); })
        .catch(() => {});
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Committed params — only update on Refresh
  const [params, setParams] = useState({
    ticker: activeTicker,
    interval: FREQ_CONFIG.D.interval,
    startDate: isoDateYearsAgo(FREQ_CONFIG.D.years),
    endDate: today,
    setupFrom: 9,
    countdownFrom: 13,
    cooldown: 0,
  });

  const summaryQuery = useQuery({
    queryKey: ['technical-summary', params.ticker, params.interval],
    queryFn: () => apiFetchJson(`/api/technical/summary?ticker=${params.ticker}&interval=${params.interval}`),
    enabled: !!params.ticker,
    staleTime: 300_000,
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const syncSidebarForViewport = () => {
      if (window.innerWidth < 1024) setSidebarOpen(false);
    };

    syncSidebarForViewport();
    window.addEventListener('resize', syncSidebarForViewport);
    return () => window.removeEventListener('resize', syncSidebarForViewport);
  }, []);

  useEffect(() => {
    if (!watchlist.includes(activeTicker)) {
      const nextTicker = watchlist[0] ?? 'SPY';
      setActiveTicker(nextTicker);
      setParams((prev) => ({ ...prev, ticker: nextTicker }));
    }
  }, [watchlist, activeTicker]);

  const commit = useCallback(() => {
    setParams({
      ticker: activeTicker,
      interval: FREQ_CONFIG[freq].interval,
      startDate,
      endDate,
      setupFrom,
      countdownFrom,
      cooldown,
    });
  }, [activeTicker, freq, startDate, endDate, setupFrom, countdownFrom, cooldown]);

  // Auto-commit when ticker or frequency changes
  const selectTicker = useCallback((ticker: string) => {
    setActiveTicker(ticker);
    setParams((prev) => ({ ...prev, ticker }));
  }, []);

  const changeFreq = useCallback((next: Frequency) => {
    const newStart = isoDateYearsAgo(FREQ_CONFIG[next].years);
    setFreq(next);
    setStartDate(newStart);
    setParams((prev) => ({
      ...prev,
      interval: FREQ_CONFIG[next].interval,
      startDate: newStart,
    }));
  }, []);

  // ── Query ────────────────────────────────────────────────────────────────
  const queryKey = useMemo(
    () => ['technical-elliott', params.ticker, params.interval, params.startDate, params.endDate, params.setupFrom, params.countdownFrom, params.cooldown],
    [params]
  );

  const { data: fig, isLoading, isFetching, error } = useQuery({
    queryKey,
    queryFn: () =>
      apiFetchJson(
        `/api/technical/elliott?ticker=${encodeURIComponent(params.ticker)}&period=10y&interval=${encodeURIComponent(params.interval)}&start=${encodeURIComponent(params.startDate)}&end=${encodeURIComponent(params.endDate)}&setup_from=${params.setupFrom}&countdown_from=${params.countdownFrom}&label_cooldown=${params.cooldown}`
      ),
    staleTime: 60_000,
  });

  // ── Chart theming ─────────────────────────────────────────────────────────
  const cleanedFigure = useMemo(() => {
    if (!fig) return null;
    const cloned = JSON.parse(JSON.stringify(fig));
    const fg = isLight ? '#0f172a' : '#dbeafe';
    const grid = isLight ? 'rgba(0,0,0,0.08)' : 'rgba(148,163,184,0.12)';
    cloned.layout = {
      ...cloned.layout,
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { ...(cloned.layout?.font || {}), color: fg, family: 'Inter, sans-serif' },
      margin: {
        ...(cloned.layout?.margin || {}),
        b: Math.max((cloned.layout?.margin?.b ?? 0), 48),
      },
      legend: {
        ...(cloned.layout?.legend || {}),
        orientation: 'h',
        x: 0,
        xanchor: 'left',
        y: 1.05,
        yanchor: 'bottom',
        itemsizing: 'constant',
        traceorder: 'normal',
        bgcolor: 'rgba(0,0,0,0)',
        borderwidth: 0,
        font: { ...(cloned.layout?.legend?.font || {}), color: fg, family: 'Inter, sans-serif', size: 11 },
      },
      hoverlabel: {
        ...(cloned.layout?.hoverlabel || {}),
        bgcolor: isLight ? 'rgba(255,255,255,0.96)' : 'rgba(15,23,42,0.92)',
        bordercolor: isLight ? 'rgba(15,23,42,0.18)' : 'rgba(148,163,184,0.35)',
        font: { ...(cloned.layout?.hoverlabel?.font || {}), color: fg, family: 'Inter, sans-serif' },
      },
    };
    ['xaxis', 'yaxis', 'xaxis2', 'yaxis2', 'xaxis3', 'yaxis3'].forEach((ax) => {
      if (cloned.layout?.[ax]) {
        cloned.layout[ax].gridcolor = grid;
        cloned.layout[ax].linecolor = isLight ? 'rgba(0,0,0,0.25)' : 'rgba(226,232,240,0.65)';
        cloned.layout[ax].tickfont = { ...(cloned.layout[ax].tickfont || {}), color: fg };
      }
    });
    return cloned;
  }, [fig, isLight]);

  // ── Render ───────────────────────────────────────────────────────────────
  const formStyle: React.CSSProperties = {
    colorScheme: isLight ? 'light' : 'dark',
    backgroundColor: 'rgb(var(--background))',
    color: 'rgb(var(--foreground))',
  };
  const inputCls = 'border border-border/50 rounded-md px-2 py-1 text-[11px] focus:outline-none focus:border-border transition-colors';
  const selectCls = inputCls + ' cursor-pointer';

  const sidebarContent = (
    <>
      <div className="px-2 py-2 border-b border-border/60 shrink-0">
        <div className="flex gap-1">
          <input
            ref={addInputRef}
            value={addInput}
            onChange={(e) => setAddInput(e.target.value.toUpperCase())}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addTicker(); } }}
            placeholder="Add ticker…"
            maxLength={10}
            className="flex-1 min-w-0 bg-transparent border border-border/50 rounded-md px-2 py-1.5 text-[11px] placeholder:text-muted-foreground/40 focus:outline-none focus:border-border transition-colors"
          />
          <button
            onClick={addTicker}
            className="shrink-0 w-7 h-7 flex items-center justify-center rounded-md border border-border/50 text-muted-foreground/40 hover:text-muted-foreground hover:border-border transition-colors"
            title="Add ticker"
          >
            <Plus className="w-3 h-3" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto py-1">
        {watchlist.length === 0 && (
          <div className="px-3 py-4 text-[11px] text-muted-foreground/50 text-center">No tickers</div>
        )}
        {watchlist.map((ticker) => {
          const isActive = ticker === params.ticker;
          return (
            <div
              key={ticker}
              role="button"
              tabIndex={0}
              onClick={() => selectTicker(ticker)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') selectTicker(ticker); }}
              className={`group w-full flex items-center justify-between px-3 py-1.5 text-left cursor-pointer transition-colors ${
                isActive
                  ? 'bg-foreground/[0.06] text-foreground'
                  : 'text-muted-foreground hover:text-foreground hover:bg-foreground/[0.03]'
              }`}
            >
              <div className="flex items-center gap-1.5 min-w-0">
                <span className={`w-1 h-1 rounded-full shrink-0 ${isActive ? 'bg-foreground' : 'bg-border/60'}`} />
                <span className="text-xs truncate">{ticker}</span>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); removeTicker(ticker); }}
                className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:text-rose-400 text-muted-foreground/50 shrink-0"
                title="Remove"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          );
        })}
      </div>
    </>
  );

  return (
    <AppShell hideFooter>
      <NavigatorShell
        sidebarOpen={sidebarOpen}
        onSidebarToggle={() => setSidebarOpen((o) => !o)}
        sidebarIcon={<Activity className="w-3.5 h-3.5 text-sky-400" />}
        sidebarLabel="Watchlist"
        sidebarContent={sidebarContent}
      >
        <div className="h-full min-h-0 p-3 flex gap-2 max-w-screen-xl mx-auto w-full">

          {/* ── Chart (dominant area) ── */}
          <div className="flex-1 min-w-0 min-h-0 rounded-xl border border-border/60 bg-background flex flex-col overflow-hidden">
            <div className="h-9 px-3 border-b border-border/60 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-semibold text-foreground">{params.ticker}</span>
                <span className="text-muted-foreground/30 text-[11px]">·</span>
                <span className="text-[11px] text-muted-foreground">{FREQ_CONFIG[freq].label}</span>
                <span className="text-muted-foreground/30 text-[11px]">·</span>
                <span className="text-[11px] text-muted-foreground">Elliott · MACD · RSI</span>
              </div>
              <div className="flex items-center gap-2">
                {isFetching && !isLoading && (
                  <span className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                    <Activity className="w-3 h-3" />
                    Updating
                  </span>
                )}
                {!isFetching && !isLoading && fig && (
                  <span className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    Live
                  </span>
                )}
              </div>
            </div>

            <div ref={plotContainerRef} className="flex-1 min-h-0">
              {isLoading && (
                <div className="h-full w-full flex flex-col items-center justify-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">Loading {params.ticker}…</span>
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
                  onInitialized={(_fig: any, gd: any) => { plotGraphDivRef.current = gd; }}
                />
              )}
              {!isLoading && !cleanedFigure && !error && (
                <div className="h-full w-full flex items-center justify-center text-muted-foreground text-sm">
                  No data
                </div>
              )}
            </div>
          </div>

          {/* ── Controls panel ── */}
          <div className="w-[196px] shrink-0 overflow-y-auto custom-scrollbar flex flex-col gap-2">

            {/* Frequency */}
            <div className="rounded-xl border border-border/60 bg-background p-3 flex flex-col gap-2 shrink-0">
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground/50 font-mono">Frequency</div>
              <div className="flex items-center gap-0.5">
                {(['D', 'W', 'M'] as Frequency[]).map((f) => (
                  <button
                    key={f}
                    onClick={() => changeFreq(f)}
                    className={`flex-1 py-1 rounded-md text-[11px] font-medium transition-colors ${
                      freq === f
                        ? 'bg-foreground/[0.07] text-foreground'
                        : 'text-muted-foreground hover:text-foreground hover:bg-foreground/[0.04]'
                    }`}
                  >
                    {f}
                  </button>
                ))}
              </div>
            </div>

            {/* Date range */}
            <div className="rounded-xl border border-border/60 bg-background p-3 flex flex-col gap-2 shrink-0">
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground/50 font-mono">Date Range</div>
              <div className="flex flex-col gap-1.5 text-[11px]">
                <div className="flex flex-col gap-0.5">
                  <span className="text-muted-foreground/60">Start</span>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className={inputCls + ' w-full'}
                    style={formStyle}
                  />
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-muted-foreground/60">End</span>
                  <input
                    type="date"
                    value={endDate}
                    max={today}
                    onChange={(e) => setEndDate(e.target.value)}
                    className={inputCls + ' w-full'}
                    style={formStyle}
                  />
                </div>
              </div>
            </div>

            {/* Signals */}
            <div className="rounded-xl border border-border/60 bg-background p-3 flex flex-col gap-2 shrink-0">
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground/50 font-mono">Signals</div>
              <div className="flex flex-col gap-1.5 text-[11px]">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-muted-foreground/60">Setup</span>
                  <select value={setupFrom} onChange={(e) => setSetupFrom(Number(e.target.value))} className={selectCls} style={formStyle}>
                    {[1, 5, 7, 9].map((v) => <option key={v} value={v}>{v}+</option>)}
                  </select>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-muted-foreground/60">Countdown</span>
                  <select value={countdownFrom} onChange={(e) => setCountdownFrom(Number(e.target.value))} className={selectCls} style={formStyle}>
                    {[9, 10, 11, 12, 13].map((v) => <option key={v} value={v}>{v}+</option>)}
                  </select>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-muted-foreground/60">Cooldown</span>
                  <select value={cooldown} onChange={(e) => setCooldown(Number(e.target.value))} className={selectCls} style={formStyle}>
                    {[0, 5, 10, 15, 20].map((v) => <option key={v} value={v}>{v}</option>)}
                  </select>
                </div>
              </div>
            </div>

            {/* AI Summary */}
            <div className="rounded-xl border border-border/60 bg-background p-3 flex flex-col gap-2 shrink-0">
              <div className="flex items-center justify-between">
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground/50 font-mono flex items-center gap-1.5">
                  <BrainCircuit className="w-3 h-3 text-sky-400" />
                  AI Summary
                </div>
                <button 
                  onClick={() => queryClient.invalidateQueries({ queryKey: ['technical-summary'] })}
                  className="text-muted-foreground/30 hover:text-foreground transition-colors"
                  title="Refresh AI Analysis"
                >
                  <RefreshCw className={`w-2.5 h-2.5 ${summaryQuery.isFetching ? 'animate-spin' : ''}`} />
                </button>
              </div>
              <div className="min-h-[120px] max-h-[320px] overflow-y-auto no-scrollbar">
                {summaryQuery.isLoading ? (
                  <div className="h-24 flex items-center justify-center">
                    <Loader2 className="w-4 h-4 animate-spin text-muted-foreground/20" />
                  </div>
                ) : (
                  <div className="text-[11px] leading-relaxed text-muted-foreground/80 prose prose-invert prose-xs max-w-none">
                    <ReactMarkdown>{summaryQuery.data?.summary || 'No analysis available.'}</ReactMarkdown>
                  </div>
                )}
              </div>
            </div>

            {/* Refresh */}
            <button
              onClick={commit}
              className="w-full h-8 bg-foreground text-background rounded-xl text-[11px] font-medium hover:opacity-80 transition-opacity shrink-0"
            >
              Refresh
            </button>
          </div>
        </div>
      </NavigatorShell>
    </AppShell>
  );
}

