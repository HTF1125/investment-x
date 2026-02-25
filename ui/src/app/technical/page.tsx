'use client';

import dynamic from 'next/dynamic';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import AppShell from '@/components/AppShell';
import { Activity, Loader2, Plus, X } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { useTheme } from '@/context/ThemeContext';

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

// ─── Signal Extraction ───────────────────────────────────────────────────────

interface Signals {
  rsi: number | null;
  rsiLabel: 'Overbought' | 'Neutral' | 'Oversold';
  macdBullish: boolean | null;
  aboveMA200: boolean | null;
}

function lastOf(arr: any): number | undefined {
  if (arr == null || typeof arr.length !== 'number' || arr.length === 0) return undefined;
  return arr[arr.length - 1];
}

function extractSignals(fig: any): Signals {
  const traces: any[] = fig?.data ?? [];
  const candlestick = traces.find((t) => t.type === 'candlestick');
  const ma200 = traces.find((t) => t.name?.includes('200'));
  const rsiTrace = traces.find((t) => {
    const n = t.name?.toLowerCase() ?? '';
    return n.includes('rsi') && !n.includes('mean');
  });
  const macdHist = traces.find((t) => {
    const n = t.name?.toLowerCase() ?? '';
    return n.includes('macd') && n.includes('hist');
  }) ?? traces.find((t) => t.name?.toLowerCase().includes('hist'));

  const lastClose = lastOf(candlestick?.close);
  const lastMA200 = lastOf(ma200?.y);
  const lastRSI = lastOf(rsiTrace?.y);
  const lastMACDHist = lastOf(macdHist?.y);

  const rsi = lastRSI != null ? Math.round(lastRSI * 10) / 10 : null;
  return {
    rsi,
    rsiLabel: rsi == null ? 'Neutral' : rsi > 70 ? 'Overbought' : rsi < 30 ? 'Oversold' : 'Neutral',
    macdBullish: lastMACDHist != null ? lastMACDHist > 0 : null,
    aboveMA200: lastClose != null && lastMA200 != null ? lastClose > lastMA200 : null,
  };
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function SignalCard({ label, value, subLabel, color }: {
  label: string;
  value: string;
  subLabel: string;
  color: 'green' | 'red' | 'sky' | 'muted';
}) {
  const colorMap = {
    green: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/8',
    red: 'text-rose-400 border-rose-500/30 bg-rose-500/8',
    sky: 'text-sky-400 border-sky-500/30 bg-sky-500/8',
    muted: 'text-muted-foreground border-border/50 bg-card/30',
  };
  return (
    <div className={`rounded-lg border px-3 py-2 flex flex-col gap-0.5 ${colorMap[color]}`}>
      <div className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">{label}</div>
      <div className="text-sm font-bold font-mono">{value}</div>
      <div className="text-[10px] text-muted-foreground">{subLabel}</div>
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function TechnicalPage() {
  const { theme } = useTheme();
  const isLight = theme === 'light';
  const today = todayIso();
  const addInputRef = useRef<HTMLInputElement>(null);

  // ── Watchlist (localStorage-persisted) ──────────────────────────────────
  const [watchlist, setWatchlist] = useState<string[]>(() => {
    try {
      const stored = localStorage.getItem(WATCHLIST_KEY);
      if (stored) return JSON.parse(stored);
    } catch {}
    return DEFAULT_WATCHLIST;
  });
  const [addInput, setAddInput] = useState('');

  useEffect(() => {
    try { localStorage.setItem(WATCHLIST_KEY, JSON.stringify(watchlist)); } catch {}
  }, [watchlist]);

  const addTicker = useCallback(() => {
    const t = addInput.trim().toUpperCase();
    if (!t || watchlist.includes(t)) { setAddInput(''); return; }
    setWatchlist((prev) => [...prev, t]);
    setAddInput('');
  }, [addInput, watchlist]);

  const removeTicker = useCallback((ticker: string) => {
    setWatchlist((prev) => prev.filter((t) => t !== ticker));
  }, []);

  // ── Controls state ───────────────────────────────────────────────────────
  const [activeTicker, setActiveTicker] = useState(watchlist[0] ?? 'SPY');
  const [freq, setFreq] = useState<Frequency>('D');
  const [startDate, setStartDate] = useState(() => isoDateYearsAgo(FREQ_CONFIG.D.years));
  const [endDate, setEndDate] = useState(today);
  const [setupFrom, setSetupFrom] = useState(9);
  const [countdownFrom, setCountdownFrom] = useState(13);
  const [cooldown, setCooldown] = useState(0);

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

  // ── Signal cards ─────────────────────────────────────────────────────────
  const signals = useMemo(() => (fig ? extractSignals(fig) : null), [fig]);

  // ── Chart theming ─────────────────────────────────────────────────────────
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
  const formStyle: React.CSSProperties = { colorScheme: isLight ? 'light' : 'dark' };
  const inputCls = 'bg-background border border-border/50 rounded px-2 py-1 text-xs font-mono text-foreground focus:outline-none focus:border-sky-500/60 focus:ring-1 focus:ring-sky-500/30 transition-colors';
  const selectCls = inputCls + ' cursor-pointer';

  return (
    <AppShell hideFooter>
      <section className="h-[calc(100dvh-3rem)] flex overflow-hidden font-mono">

        {/* ── Left Sidebar: Watchlist ───────────────────────────────────── */}
        <aside className="w-44 shrink-0 border-r border-border/40 flex flex-col overflow-hidden bg-card/20">
          <div className="px-3 pt-3 pb-2 border-b border-border/40 shrink-0">
            <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest mb-2">Watchlist</div>
            <div className="flex gap-1">
              <input
                ref={addInputRef}
                value={addInput}
                onChange={(e) => setAddInput(e.target.value.toUpperCase())}
                onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addTicker(); } }}
                placeholder="Add ticker…"
                maxLength={10}
                className="flex-1 min-w-0 bg-transparent border border-border/40 rounded px-2 py-1 text-[11px] font-mono placeholder:text-muted-foreground/50 focus:outline-none focus:border-sky-500/50 transition-colors"
              />
              <button
                onClick={addTicker}
                className="shrink-0 w-6 h-6 flex items-center justify-center rounded border border-border/40 hover:border-sky-500/50 hover:text-sky-400 text-muted-foreground transition-colors"
                title="Add ticker"
              >
                <Plus className="w-3 h-3" />
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto py-1">
            {watchlist.length === 0 && (
              <div className="px-3 py-4 text-[11px] text-muted-foreground/60 text-center">No tickers</div>
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
                      ? 'bg-sky-500/10 border-l-2 border-sky-500 pl-[10px] text-sky-300'
                      : 'border-l-2 border-transparent hover:bg-white/5 text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${isActive ? 'bg-sky-400' : 'bg-border'}`} />
                    <span className={`text-xs font-semibold font-mono truncate ${isActive ? 'text-sky-200' : ''}`}>{ticker}</span>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); removeTicker(ticker); }}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:text-rose-400 text-muted-foreground/70 shrink-0"
                    title="Remove"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              );
            })}
          </div>
        </aside>

        {/* ── Main Content ─────────────────────────────────────────────────── */}
        <div className="flex-1 min-w-0 flex flex-col overflow-hidden p-2.5 gap-2">

          {/* Controls bar */}
          <div className="shrink-0 rounded-lg border border-border/40 bg-card/20 px-3 py-2 flex flex-wrap items-center gap-x-3 gap-y-2">
            {/* Active ticker */}
            <div className="flex items-center gap-2 min-w-fit">
              <span className="text-base font-bold font-mono text-foreground tracking-widest">{params.ticker}</span>
              <span className="text-[10px] text-muted-foreground font-sans">·</span>
              <span className="text-[11px] text-muted-foreground">{FREQ_CONFIG[freq].label}</span>
            </div>

            <div className="h-4 w-px bg-border/50 hidden sm:block" />

            {/* Frequency toggle */}
            <div className="flex items-center gap-0.5">
              {(['D', 'W', 'M'] as Frequency[]).map((f) => (
                <button
                  key={f}
                  onClick={() => changeFreq(f)}
                  className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
                    freq === f
                      ? 'bg-sky-500/20 border border-sky-500/50 text-sky-300'
                      : 'border border-transparent hover:border-border/60 text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>

            <div className="h-4 w-px bg-border/50 hidden sm:block" />

            {/* Date range */}
            <div className="flex items-center gap-1.5 text-[11px]">
              <span className="text-muted-foreground shrink-0">Start</span>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className={inputCls}
                style={formStyle}
              />
              <span className="text-muted-foreground shrink-0">End</span>
              <input
                type="date"
                value={endDate}
                max={today}
                onChange={(e) => setEndDate(e.target.value)}
                className={inputCls}
                style={formStyle}
              />
            </div>

            <div className="h-4 w-px bg-border/50 hidden lg:block" />

            {/* Indicator filters */}
            <div className="flex items-center gap-1.5 text-[11px]">
              <span className="text-muted-foreground shrink-0">Setup</span>
              <select value={setupFrom} onChange={(e) => setSetupFrom(Number(e.target.value))} className={selectCls} style={formStyle}>
                {[1, 5, 7, 9].map((v) => <option key={v} value={v}>{v}+</option>)}
              </select>
              <span className="text-muted-foreground shrink-0">CD</span>
              <select value={countdownFrom} onChange={(e) => setCountdownFrom(Number(e.target.value))} className={selectCls} style={formStyle}>
                {[9, 10, 11, 12, 13].map((v) => <option key={v} value={v}>{v}+</option>)}
              </select>
              <span className="text-muted-foreground shrink-0">Cool</span>
              <select value={cooldown} onChange={(e) => setCooldown(Number(e.target.value))} className={selectCls} style={formStyle}>
                {[0, 5, 10, 15, 20].map((v) => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>

            <div className="ml-auto flex items-center gap-2">
              {isFetching && !isLoading && (
                <span className="flex items-center gap-1 text-[10px] text-emerald-400">
                  <Activity className="w-3 h-3" />
                  Updating
                </span>
              )}
              <button
                onClick={commit}
                className="px-3 py-1 rounded border border-sky-500/40 bg-sky-500/10 hover:bg-sky-500/20 text-sky-300 text-[11px] font-semibold transition-colors"
              >
                Refresh
              </button>
            </div>
          </div>

          {/* Signal cards */}
          <div className="shrink-0 grid grid-cols-3 gap-2">
            <SignalCard
              label="RSI 14"
              value={signals?.rsi != null ? String(signals.rsi) : '─'}
              subLabel={signals ? signals.rsiLabel : 'Loading…'}
              color={
                signals?.rsi == null ? 'muted'
                : signals.rsi > 70 ? 'red'
                : signals.rsi < 30 ? 'green'
                : 'sky'
              }
            />
            <SignalCard
              label="MACD"
              value={signals?.macdBullish == null ? '─' : signals.macdBullish ? 'Bullish' : 'Bearish'}
              subLabel={signals?.macdBullish == null ? 'Loading…' : signals.macdBullish ? 'Histogram above zero' : 'Histogram below zero'}
              color={signals?.macdBullish == null ? 'muted' : signals.macdBullish ? 'green' : 'red'}
            />
            <SignalCard
              label="MA 200"
              value={signals?.aboveMA200 == null ? '─' : signals.aboveMA200 ? 'Above' : 'Below'}
              subLabel={signals?.aboveMA200 == null ? 'Loading…' : signals.aboveMA200 ? 'Price above 200-period MA' : 'Price below 200-period MA'}
              color={signals?.aboveMA200 == null ? 'muted' : signals.aboveMA200 ? 'green' : 'red'}
            />
          </div>

          {/* Chart panel */}
          <div className="flex-1 min-h-0 rounded-lg border border-border/40 bg-card/20 flex flex-col overflow-hidden">
            <div className="px-3 py-1.5 border-b border-border/40 flex items-center justify-between text-[11px] shrink-0">
              <span className="font-semibold text-foreground font-mono">
                {params.ticker} · {FREQ_CONFIG[freq].label} · Elliott + MACD + RSI
              </span>
              {!isFetching && !isLoading && fig && (
                <span className="flex items-center gap-1 text-emerald-400">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Live
                </span>
              )}
            </div>

            <div className="flex-1 min-h-0">
              {isLoading && (
                <div className="h-full w-full flex flex-col items-center justify-center gap-2 text-muted-foreground">
                  <Loader2 className="w-5 h-5 animate-spin text-sky-400" />
                  <span className="text-xs">Loading {params.ticker}…</span>
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
                  No data
                </div>
              )}
            </div>
          </div>
        </div>
      </section>
    </AppShell>
  );
}
