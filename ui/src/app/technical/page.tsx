'use client';

import dynamic from 'next/dynamic';
import { useMemo, useState } from 'react';
import AppShell from '@/components/AppShell';
import { CandlestickChart, Loader2 } from 'lucide-react';
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

export default function TechnicalPage() {
  const today = new Date();
  const todayStr = today.toISOString().slice(0, 10);
  const minusYears = (years: number) => {
    const d = new Date();
    d.setFullYear(d.getFullYear() - years);
    return d.toISOString().slice(0, 10);
  };

  const { theme } = useTheme();
  const [tickerInput, setTickerInput] = useState('SPY');
  const [freqInput, setFreqInput] = useState<'D' | 'W' | 'M'>('D');
  const [startInput, setStartInput] = useState(minusYears(1));
  const [endInput, setEndInput] = useState(todayStr);
  const [setupFromInput, setSetupFromInput] = useState(9);
  const [countdownFromInput, setCountdownFromInput] = useState(13);
  const [cooldownInput, setCooldownInput] = useState(0);

  const [applied, setApplied] = useState({
    ticker: 'SPY',
    freq: 'D' as 'D' | 'W' | 'M',
    startDate: minusYears(1),
    endDate: todayStr,
    setupFrom: 9,
    countdownFrom: 13,
    cooldown: 0,
  });

  const interval = applied.freq === 'D' ? '1d' : applied.freq === 'W' ? '1wk' : '1mo';

  const onFreqChange = (next: 'D' | 'W' | 'M') => {
    setFreqInput(next);
    if (next === 'D') setStartInput(minusYears(1));
    if (next === 'W') setStartInput(minusYears(3));
    if (next === 'M') setStartInput(minusYears(10));
    setEndInput(todayStr);
  };

  const queryKey = useMemo(
    () => ['technical-elliott', applied.ticker, interval, applied.setupFrom, applied.countdownFrom, applied.cooldown],
    [applied, interval]
  );

  const { data: fig, isLoading, error, refetch } = useQuery({
    queryKey,
    queryFn: () =>
      apiFetchJson(
        `/api/technical/elliott?ticker=${encodeURIComponent(applied.ticker || 'SPY')}&period=10y&interval=${encodeURIComponent(interval)}&start=${encodeURIComponent(applied.startDate)}&end=${encodeURIComponent(applied.endDate)}&setup_from=${applied.setupFrom}&countdown_from=${applied.countdownFrom}&label_cooldown=${applied.cooldown}`
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

  const hasChanges =
    tickerInput !== applied.ticker ||
    freqInput !== applied.freq ||
    startInput !== applied.startDate ||
    endInput !== applied.endDate ||
    setupFromInput !== applied.setupFrom ||
    countdownFromInput !== applied.countdownFrom ||
    cooldownInput !== applied.cooldown;

  const applyChanges = () => {
    setApplied({
      ticker: tickerInput || 'SPY',
      freq: freqInput,
      startDate: startInput,
      endDate: endInput,
      setupFrom: setupFromInput,
      countdownFrom: countdownFromInput,
      cooldown: cooldownInput,
    });
  };

  const handleSubmit = () => {
    if (hasChanges) {
      applyChanges();
    } else {
      refetch();
    }
  };

  return (
    <AppShell>
      <div className="h-[calc(100vh-3rem)] w-full overflow-hidden">
        <div className="h-full max-w-[1800px] mx-auto px-4 md:px-6 lg:px-8 pt-3 pb-3 flex flex-col overflow-hidden">
        <div className="mb-2 flex items-center gap-2 shrink-0">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center">
            <CandlestickChart className="w-4 h-4 text-indigo-300" />
          </div>
          <span className="text-sm font-semibold text-foreground">Technical</span>
        </div>

        <form
          className="mb-2 rounded-2xl border border-border/50 bg-card/20 backdrop-blur-sm p-3 md:p-4 shrink-0"
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit();
          }}
          onKeyDown={(e) => {
            if (e.key !== 'Enter') return;
            const target = e.target as HTMLElement;
            if (target && target.tagName === 'TEXTAREA') return;
            e.preventDefault();
            handleSubmit();
          }}
        >
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2.5">
            <input
              value={tickerInput}
              onChange={(e) => setTickerInput(e.target.value.toUpperCase())}
              className="px-3 py-2.5 rounded-xl border border-border/60 bg-background/40 text-sm font-semibold tracking-wide"
              placeholder="Ticker (SPY)"
            />
            <select
              value={freqInput}
              onChange={(e) => onFreqChange(e.target.value as 'D' | 'W' | 'M')}
              className="px-3 py-2.5 rounded-xl border border-border/60 bg-background/40 text-sm font-semibold"
            >
              <option value="D">D</option><option value="W">W</option><option value="M">M</option>
            </select>
            <select
              value={setupFromInput}
              onChange={(e) => setSetupFromInput(Number(e.target.value))}
              className="px-3 py-2.5 rounded-xl border border-border/60 bg-background/40 text-sm"
            >
              {[1,5,7,9].map((v) => <option key={v} value={v}>Setup {v}+</option>)}
            </select>
            <select
              value={countdownFromInput}
              onChange={(e) => setCountdownFromInput(Number(e.target.value))}
              className="px-3 py-2.5 rounded-xl border border-border/60 bg-background/40 text-sm"
            >
              {[9,10,11,12,13].map((v) => <option key={v} value={v}>CD {v}+</option>)}
            </select>
            <input
              type="number"
              min={0}
              max={20}
              value={cooldownInput}
              onChange={(e) => setCooldownInput(Number(e.target.value || 0))}
              className="px-3 py-2.5 rounded-xl border border-border/60 bg-background/40 text-sm"
              placeholder="Cooldown"
            />
            <button type="submit" className="hidden" aria-hidden="true" tabIndex={-1}>
              submit
            </button>
          </div>
        </form>

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
              config={{ responsive: true, displaylogo: false, displayModeBar: true }}
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
    </AppShell>
  );
}
