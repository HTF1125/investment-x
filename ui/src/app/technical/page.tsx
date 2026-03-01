'use client';

import dynamic from 'next/dynamic';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import AppShell from '@/components/AppShell';
import NavigatorShell from '@/components/NavigatorShell';
import {
  Activity, Loader2, BrainCircuit, BarChart2, Settings2, Plus, X, Search, ChevronRight, Minimize2, Maximize2,
  ChevronUp, ChevronDown, FileText, Presentation as PresentationIcon
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetchJson, apiFetch } from '@/lib/api';
import { useTheme } from '@/context/ThemeContext';
import ReactMarkdown from 'react-markdown';

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-3">
        <Loader2 className="w-6 h-6 animate-spin text-sky-500/50" />
        <span className="text-[11px] text-muted-foreground/50 tracking-widest uppercase">Initializing Chart</span>
      </div>
    </div>
  ),
}) as any;

// ─── Utilities & Constants ───────────────────────────────────────────────────

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);
  return debouncedValue;
}

type Frequency = 'D' | 'W' | 'M';
const FREQ_CONFIG: Record<Frequency, { years: number; interval: string; label: string }> = {
  D: { years: 1, interval: '1d', label: '1D' },
  W: { years: 3, interval: '1wk', label: '1W' },
  M: { years: 10, interval: '1mo', label: '1M' },
};

const SQZ_BAR_COLOR: Record<string, string> = {
  lime: '#4ade80', green: '#16a34a', red: '#f87171', maroon: '#991b1b', gray: '#64748b',
};
const SQZ_DOT_COLOR: Record<string, string> = {
  blue: '#38bdf8', black: '#1e293b', gray: '#64748b',
};

const DEFAULT_MA_CONFIGS = [
  { type: 'SMA', period: 20, color: '#f59e0b', enabled: true },
  { type: 'EMA', period: 50, color: '#38bdf8', enabled: true },
  { type: 'SMA', period: 200, color: '#8b5cf6', enabled: true },
];
type MaConfig = { type: string; period: number; color: string; enabled: boolean };

function todayIso() { return new Date().toISOString().slice(0, 10); }
function isoDateYearsAgo(years: number) {
  const d = new Date(); d.setFullYear(d.getFullYear() - years); return d.toISOString().slice(0, 10);
}

// ─── UI Components ───────────────────────────────────────────────────────────

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-background/80 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-[320px] overflow-hidden rounded-xl border border-border/60 bg-background/95 shadow-2xl animate-in fade-in zoom-in-95 duration-150 backdrop-blur-xl">
        <div className="flex items-center justify-between border-b border-border/50 px-4 py-3 bg-foreground/[0.02]">
          <h3 className="text-[13px] font-semibold tracking-tight text-foreground/90">{title}</h3>
          <button onClick={onClose} className="rounded-md p-1.5 text-muted-foreground/60 hover:bg-foreground/10 hover:text-foreground transition-colors">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
        <div className="p-5 space-y-5 max-h-[60vh] overflow-y-auto custom-scrollbar">
          {children}
        </div>
      </div>
    </div>
  );
}

function ParamRow({ label, value, onChange, min, max, step }: any) {
  return (
    <div className="flex items-center justify-between gap-4 group">
      <span className="text-[12px] text-muted-foreground/80 font-medium group-hover:text-foreground/90 transition-colors">{label}</span>
      <input
        type="number" value={value as number} min={min} max={max} step={step ?? 1}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-20 text-right text-[12px] bg-foreground/[0.02] border border-border/40 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-sky-500/50 focus:ring-1 focus:ring-sky-500/20 text-foreground transition-all"
        style={{ colorScheme: 'dark' }}
      />
    </div>
  );
}

function ParamSelect({ label, value, onChange, options }: any) {
  return (
    <div className="flex items-center justify-between gap-4 group">
      <span className="text-[12px] text-muted-foreground/80 font-medium group-hover:text-foreground/90 transition-colors">{label}</span>
      <select
        value={value as any} onChange={(e) => onChange(e.target.value)}
        className="text-[12px] bg-foreground/[0.02] border border-border/40 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-sky-500/50 focus:ring-1 focus:ring-sky-500/20 text-foreground cursor-pointer transition-all appearance-none pr-8 relative"
        style={{ colorScheme: 'dark', backgroundImage: 'url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%2371717A%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E")', backgroundRepeat: 'no-repeat', backgroundPosition: 'right 0.7rem top 50%', backgroundSize: '0.65rem auto' }}
      >
        {options.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}

function IndicatorRow({ 
  color, label, sublabel, checked, onCheck, onSettingsOpen, settingsOpen, settingsContent, extra,
  onMoveUp, onMoveDown, isFirst, isLast 
}: any) {
  return (
    <div className="relative">
      <div
        className={`flex items-center gap-3 px-3 py-1.5 group hover:bg-foreground/[0.06] transition-all cursor-pointer select-none rounded-lg mx-2 ${checked ? 'bg-foreground/[0.03]' : ''}`}
        onClick={() => onCheck(!checked)}
      >
        {/* TradingView Style Checkbox */}
        <button
          onClick={(e) => { e.stopPropagation(); onCheck(!checked); }}
          className={`shrink-0 w-4 h-4 rounded-[4px] border-2 transition-all flex items-center justify-center shadow-sm ${
            checked 
              ? 'border-transparent scale-110' 
              : 'border-muted-foreground/30 bg-transparent hover:border-muted-foreground/60'
          }`}
          style={{ backgroundColor: checked ? color : undefined }}
          role="checkbox" aria-checked={checked}
        >
          {checked && (
            <svg width="10" height="10" viewBox="0 0 12 10" fill="none" className="drop-shadow-sm">
              <path d="M1.5 5L4.5 8.5L10.5 1.5" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          )}
        </button>

        {/* Label and Sublabel */}
        <div className="flex-1 min-w-0 flex flex-col justify-center">
          <div className="flex items-baseline gap-2 overflow-hidden">
            <span className={`text-[12px] font-bold tracking-tight transition-colors truncate ${checked ? 'text-foreground' : 'text-muted-foreground/40'}`}>
              {label}
            </span>
            {sublabel && checked && (
              <span className="text-[10px] text-sky-500/50 font-bold tabular-nums truncate">{sublabel}</span>
            )}
          </div>
        </div>

        {/* Reordering Controls (Shown on hover) */}
        {(onMoveUp || onMoveDown) && (
          <div className="flex flex-col opacity-0 group-hover:opacity-100 transition-opacity">
            {onMoveUp && !isFirst && (
              <button 
                onClick={(e) => { e.stopPropagation(); onMoveUp(); }}
                className="p-0.5 hover:text-sky-400 text-muted-foreground/30 transition-colors"
              >
                <ChevronUp className="w-3 h-3" />
              </button>
            )}
            {onMoveDown && !isLast && (
              <button 
                onClick={(e) => { e.stopPropagation(); onMoveDown(); }}
                className="p-0.5 hover:text-sky-400 text-muted-foreground/30 transition-colors"
              >
                <ChevronDown className="w-3 h-3" />
              </button>
            )}
          </div>
        )}

        {extra}

        {/* Settings Gear - Prominent on Hover */}
        <button
          onClick={(e) => { e.stopPropagation(); onSettingsOpen(); }}
          className="shrink-0 opacity-0 group-hover:opacity-100 transition-all p-1.5 rounded-md bg-foreground/5 hover:bg-foreground/10 text-muted-foreground/60 hover:text-foreground shadow-sm"
          title="Settings"
        >
          <Settings2 className="w-4 h-4" />
        </button>
      </div>

      {settingsOpen && <Modal title={`${label} Settings`} onClose={onSettingsOpen}>{settingsContent}</Modal>}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="px-4 pt-5 pb-2.5 flex items-center gap-2">
      <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">{children}</span>
      <div className="h-px flex-1 bg-gradient-to-r from-border/50 to-transparent" />
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function TechnicalPage() {
  const { theme } = useTheme();
  const isLight = theme === 'light';
  const queryClient = useQueryClient();
  const today = todayIso();

  // ── Sidebar Search ──
  const [sidebarSearch, setSidebarSearch] = useState('');

  // ── Unified State ─────────────────────────────────────────────────────────
  const [state, setState] = useState({
    ticker: 'SPY',
    freq: 'D' as Frequency,
    startDate: isoDateYearsAgo(FREQ_CONFIG.D.years),
    endDate: today,
    
    showCandle: true,
    showElliott: true,
    showTD: true,
    showMACD: true,
    showRSI: true,
    showSqz: false,
    showST: false,

    setupFrom: 9,
    countdownFrom: 13,
    cooldown: 0,
    macdFast: 12, macdSlow: 26, macdSignal: 9,
    rsiPeriod: 14,
    sqzBbLen: 20, sqzBbMult: 2.0, sqzKcLen: 20, sqzKcMult: 1.5,
    stPeriod: 10, stMult: 3.0,
    maConfigs: DEFAULT_MA_CONFIGS,
  });

  const debouncedState = useDebounce(state, 600);

  // Local ticker input for immediate typing feedback
  const [tickerInput, setTickerInput] = useState(state.ticker);

  const applyTicker = useCallback(() => {
    const t = tickerInput.trim().toUpperCase();
    if (t && t !== state.ticker) setState(s => ({ ...s, ticker: t }));
  }, [tickerInput, state.ticker]);

  // ── Layout & UI State ─────────────────────────────────────────────────────
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [openSettings, setOpenSettings] = useState<string | null>(null);
  const [showAiSummary, setShowAiSummary] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [exportingFormat, setExportingFormat] = useState<string | null>(null);

  // ── Export Logic ──
  const handleExport = async (format: 'pdf' | 'pptx') => {
    if (!summaryQuery.data?.summary) return;
    setExportingFormat(format);
    try {
      const interval = FREQ_CONFIG[debouncedState.freq].interval;
      const params = new URLSearchParams({
        ticker: debouncedState.ticker,
        format,
        interval,
        setup_from: debouncedState.setupFrom.toString(),
        countdown_from: debouncedState.countdownFrom.toString(),
        label_cooldown: debouncedState.cooldown.toString(),
        show_macd: debouncedState.showMACD.toString(),
        show_rsi: debouncedState.showRSI.toString(),
      });

      const res = await apiFetch(`/api/technical/export?${params.toString()}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ summary: summaryQuery.data.summary }),
      });

      if (!res.ok) throw new Error('Export failed');

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `InvestmentX_${debouncedState.ticker}_Report_${new Date().toISOString().slice(0, 10)}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Export error:', err);
      alert('Failed to generate ' + format.toUpperCase());
    } finally {
      setExportingFormat(null);
    }
  };

  // ── Reordering logic ──
  const moveMA = (idx: number, direction: 'up' | 'down') => {
    const newMAs = [...state.maConfigs];
    const targetIdx = direction === 'up' ? idx - 1 : idx + 1;
    if (targetIdx >= 0 && targetIdx < newMAs.length) {
      [newMAs[idx], newMAs[targetIdx]] = [newMAs[targetIdx], newMAs[idx]];
      setState(s => ({ ...s, maConfigs: newMAs }));
    }
  };

  const plotContainerRef = useRef<HTMLDivElement>(null);
  const plotGraphDivRef = useRef<HTMLElement | null>(null);

  function toggleSettings(key: string) {
    setOpenSettings((prev) => (prev === key ? null : key));
  }

  // Handle resizing
  useEffect(() => {
    const el = plotContainerRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(() => {
      const gd = plotGraphDivRef.current;
      if (!gd || !gd.isConnected) return;
      import('plotly.js-dist-min').then(({ default: Plotly }) => { (Plotly as any).Plots.resize(gd); }).catch(() => {});
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // ── Preferences ───────────────────────────────────────────────────────────
  const prefQuery = useQuery({
    queryKey: ['user-preferences'],
    queryFn: () => apiFetchJson('/api/user/preferences'),
    staleTime: Infinity,
  });

  const prefMutation = useMutation({
    mutationFn: (settings: any) =>
      apiFetch('/api/user/preferences', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings }),
      }),
  });

  // Load preferences once
  const loadedPref = useRef(false);
  useEffect(() => {
    if (!prefQuery.data?.settings || loadedPref.current) return;
    const s = prefQuery.data.settings;
    setState(prev => ({
      ...prev,
      ticker: s.technical_ticker || prev.ticker,
      freq: (s.technical_freq as Frequency) || prev.freq,
      showSqz: s.technical_show_sqz ?? prev.showSqz,
      showST: s.technical_show_st ?? prev.showST,
      showElliott: s.technical_show_elliott ?? prev.showElliott,
      showTD: s.technical_show_td ?? prev.showTD,
      showMACD: s.technical_show_macd ?? prev.showMACD,
      showRSI: s.technical_show_rsi ?? prev.showRSI,
      maConfigs: s.technical_ma_configs || prev.maConfigs,
    }));
    setTickerInput(s.technical_ticker || 'SPY');
    loadedPref.current = true;
  }, [prefQuery.data]);

  // Save preferences on debounce change
  useEffect(() => {
    if (!loadedPref.current) return;
    prefMutation.mutate({
      technical_ticker: debouncedState.ticker,
      technical_freq: debouncedState.freq,
      technical_show_sqz: debouncedState.showSqz,
      technical_show_st: debouncedState.showST,
      technical_show_elliott: debouncedState.showElliott,
      technical_show_td: debouncedState.showTD,
      technical_show_macd: debouncedState.showMACD,
      technical_show_rsi: debouncedState.showRSI,
      technical_ma_configs: debouncedState.maConfigs,
    });
  }, [
    debouncedState.ticker, debouncedState.freq, debouncedState.showSqz, debouncedState.showST,
    debouncedState.showElliott, debouncedState.showTD, debouncedState.showMACD, debouncedState.showRSI,
    debouncedState.maConfigs
  ]);

  // ── Queries (Powered by debouncedState) ───────────────────────────────────
  const interval = FREQ_CONFIG[debouncedState.freq].interval;

  const elliottQueryKey = useMemo(() => [
    'technical-elliott', debouncedState.ticker, interval, debouncedState.startDate, debouncedState.endDate,
    debouncedState.setupFrom, debouncedState.countdownFrom, debouncedState.cooldown,
    debouncedState.showMACD, debouncedState.showRSI
  ], [debouncedState, interval]);

  const { data: fig, isLoading, isFetching: isFetchingElliott, error } = useQuery({
    queryKey: elliottQueryKey,
    queryFn: () => apiFetchJson(
      `/api/technical/elliott?ticker=${encodeURIComponent(debouncedState.ticker)}&period=10y&interval=${encodeURIComponent(interval)}&start=${encodeURIComponent(debouncedState.startDate)}&end=${encodeURIComponent(debouncedState.endDate)}&setup_from=${debouncedState.setupFrom}&countdown_from=${debouncedState.countdownFrom}&label_cooldown=${debouncedState.cooldown}&show_macd=${debouncedState.showMACD}&show_rsi=${debouncedState.showRSI}`
    ),
    staleTime: 60_000,
  });

  const hasOverlays = debouncedState.showSqz || debouncedState.showST || debouncedState.maConfigs.some(m => m.enabled);
  const masStr = debouncedState.maConfigs.filter(m => m.enabled).map(m => `${m.type}:${m.period}:${m.color}`).join(',');

  const overlayQueryKey = useMemo(() => [
    'technical-overlays', debouncedState.ticker, interval,
    debouncedState.showSqz, debouncedState.sqzBbLen, debouncedState.sqzBbMult, debouncedState.sqzKcLen, debouncedState.sqzKcMult,
    debouncedState.showST, debouncedState.stPeriod, debouncedState.stMult, masStr
  ], [debouncedState, interval, masStr]);

  const { data: overlayData, isFetching: isFetchingOverlays } = useQuery({
    queryKey: overlayQueryKey,
    queryFn: () => apiFetchJson(
      `/api/technical/overlays?ticker=${encodeURIComponent(debouncedState.ticker)}&interval=${encodeURIComponent(interval)}&sqz=${debouncedState.showSqz}&sqz_bb_len=${debouncedState.sqzBbLen}&sqz_bb_mult=${debouncedState.sqzBbMult}&sqz_kc_len=${debouncedState.sqzKcLen}&sqz_kc_mult=${debouncedState.sqzKcMult}&st=${debouncedState.showST}&st_period=${debouncedState.stPeriod}&st_mult=${debouncedState.stMult}${masStr ? `&mas=${encodeURIComponent(masStr)}` : ''}`
    ),
    enabled: hasOverlays,
    staleTime: 60_000,
  });

  const summaryQuery = useQuery({
    queryKey: ['technical-summary', debouncedState.ticker, interval],
    queryFn: () => apiFetchJson(`/api/technical/summary?ticker=${debouncedState.ticker}&interval=${interval}`),
    enabled: !!debouncedState.ticker && showAiSummary,
    staleTime: 300_000,
  });

  const isFetching = isFetchingElliott || isFetchingOverlays;

  // ── Chart Assembly ────────────────────────────────────────────────────────
  const cleanedFigure = useMemo(() => {
    if (!fig) return null;
    const cloned = JSON.parse(JSON.stringify(fig));
    const fg = isLight ? '#020617' : '#dbeafe';
    const grid = isLight ? 'rgba(0,0,0,0.08)' : 'rgba(148,163,184,0.06)';

    // Strip built-in MAs
    cloned.data = (cloned.data as any[]).filter((t: any) => !['MA 5', 'MA 20', 'MA 200'].includes(t.name));

    if (!debouncedState.showElliott) {
      cloned.data = cloned.data.filter((t: any) => !['Elliott 1-5', 'Elliott A-B-C', 'Wave Backbone'].includes(t.name) && t.legendgroup !== 'elliott');
    }
    if (!debouncedState.showTD) {
      cloned.data = cloned.data.filter((t: any) => !(t.mode === 'text' && t.showlegend === false && t.hoverinfo === 'skip'));
    }

    const overlayTraces: any[] = [];
    if (overlayData?.moving_averages) {
      for (const ma of overlayData.moving_averages) {
        overlayTraces.push({
          type: 'scatter', x: ma.x, y: ma.y, mode: 'lines',
          line: { color: ma.color, width: 1.5 }, name: ma.name, legendgroup: 'ma',
          hovertemplate: `${ma.name}: %{y:.2f}<extra></extra>`,
        });
      }
    }
    if (overlayData?.supertrend) {
      const st = overlayData.supertrend;
      overlayTraces.push({
        type: 'scatter', x: overlayData.dates, y: st.up, mode: 'lines', line: { color: isLight ? '#16a34a' : '#22c55e', width: 1.5 }, name: 'ST ↑', legendgroup: 'supertrend', connectgaps: false, hovertemplate: 'ST Up: %{y:.2f}<extra></extra>',
      });
      overlayTraces.push({
        type: 'scatter', x: overlayData.dates, y: st.dn, mode: 'lines', line: { color: isLight ? '#dc2626' : '#f43f5e', width: 1.5 }, name: 'ST ↓', legendgroup: 'supertrend', connectgaps: false, hovertemplate: 'ST Down: %{y:.2f}<extra></extra>',
      });
    }

    if (overlayTraces.length) {
      cloned.data = [cloned.data[0], ...overlayTraces, ...cloned.data.slice(1)];
    }

    if (overlayData?.squeeze) {
      const sqz = overlayData.squeeze;
      const barColors = sqz.bar_color.map((c: string) => SQZ_BAR_COLOR[c] ?? '#64748b');
      const dotColors = sqz.sqz_dot_color.map((c: string) => SQZ_DOT_COLOR[c] ?? '#64748b');
      
      const lastAxisIndex = (debouncedState.showMACD && debouncedState.showRSI) ? '3' : ((debouncedState.showMACD || debouncedState.showRSI) ? '2' : '');
      const yaxisKey = `yaxis${lastAxisIndex ? (parseInt(lastAxisIndex) + 1) : '2'}`;
      const overlayingY = `y${lastAxisIndex || '1'}`;
      const xaxisKey = lastAxisIndex ? `x${lastAxisIndex}` : 'x';

      cloned.data.push({
        type: 'bar', x: overlayData.dates, y: sqz.val, marker: { color: barColors }, name: 'SQZ Mom', yaxis: yaxisKey.replace('axis', ''), xaxis: xaxisKey.replace('axis', ''), legendgroup: 'squeeze', hovertemplate: 'SQZ: %{y:.4f}<extra></extra>',
      });
      cloned.data.push({
        type: 'scatter', x: overlayData.dates, y: overlayData.dates.map(() => 0), mode: 'markers', marker: { color: dotColors, size: 4, symbol: 'cross-thin', line: { width: 1.5, color: dotColors } }, name: 'SQZ State', yaxis: yaxisKey.replace('axis', ''), xaxis: xaxisKey.replace('axis', ''), legendgroup: 'squeeze', showlegend: false, hovertemplate: 'SQZ State<extra></extra>',
      });
      cloned.layout[yaxisKey] = {
        overlaying: overlayingY, side: 'right', showgrid: false, showticklabels: false, zeroline: true, zerolinecolor: isLight ? 'rgba(0,0,0,0.2)' : 'rgba(255,255,255,0.1)', zerolinewidth: 1,
      };
    }

    if (!debouncedState.showCandle && cloned.data.length > 0) {
      cloned.data[0] = { ...cloned.data[0], visible: false };
    }

    cloned.layout = {
      ...cloned.layout,
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { ...(cloned.layout?.font || {}), color: fg, family: 'Inter, sans-serif' },
      margin: { l: 50, r: 15, t: 15, b: 30 },
      legend: {
        orientation: 'h', x: 0.01, xanchor: 'left', y: 0.99, yanchor: 'bottom',
        itemsizing: 'constant', traceorder: 'normal', bgcolor: 'rgba(0,0,0,0)', borderwidth: 0,
        font: { color: fg, family: 'Inter, sans-serif', size: 10 },
      },
      hoverlabel: {
        bgcolor: isLight ? 'rgba(255,255,255,0.98)' : 'rgba(15,23,42,0.98)',
        bordercolor: isLight ? 'rgba(15,23,42,0.1)' : 'rgba(148,163,184,0.2)',
        font: { color: fg, family: 'Inter, sans-serif', size: 12 },
      },
      hovermode: 'x',
      hoverdistance: 20,
      spikedistance: -1,
      dragmode: 'pan',
    };

    ['xaxis', 'yaxis', 'xaxis2', 'yaxis2', 'xaxis3', 'yaxis3'].forEach((ax) => {
      if (cloned.layout?.[ax]) {
        cloned.layout[ax].gridcolor = grid;
        cloned.layout[ax].zerolinecolor = grid;
        cloned.layout[ax].linecolor = isLight ? 'rgba(0,0,0,0.15)' : 'rgba(255,255,255,0.1)';
        cloned.layout[ax].tickfont = { ...(cloned.layout[ax].tickfont || {}), color: fg, size: 10 };
      }
    });
    return cloned;
  }, [fig, overlayData, isLight, debouncedState]);

  // ── Sidebar Content ───────────────────────────────────────────────────────
  const sidebarContent = useMemo(() => {
    const s = sidebarSearch.toLowerCase();
    const match = (label: string) => !s || label.toLowerCase().includes(s);

    return (
      <div className="flex flex-col h-full overflow-hidden bg-card/10">
        {/* Search Bar at the top of sidebar */}
        <div className="px-3.5 py-3 shrink-0 border-b border-border/20">
          <div className="relative group">
            <Search className={`w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 transition-colors ${sidebarSearch ? 'text-sky-500' : 'text-muted-foreground/40'}`} />
            <input 
              value={sidebarSearch}
              onChange={(e) => setSidebarSearch(e.target.value)}
              placeholder="Search indicators..."
              className="w-full bg-foreground/[0.03] border border-border/40 rounded-lg pl-8 pr-8 py-1.5 text-[11.5px] focus:outline-none focus:border-sky-500/40 focus:ring-1 focus:ring-sky-500/10 transition-all placeholder:text-muted-foreground/30"
            />
            {sidebarSearch && (
              <button 
                onClick={() => setSidebarSearch('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 hover:bg-foreground/5 rounded text-muted-foreground/40"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar pb-6">
          {/* On Chart group */}
          {(match('Candles') || match('Elliott Wave') || match('TD Sequential')) && (
            <>
              <SectionLabel>On Chart</SectionLabel>
              {match('Candles') && (
                <IndicatorRow color="#64748b" label="Candles" checked={state.showCandle} onCheck={(v: boolean) => setState(s => ({ ...s, showCandle: v }))} onSettingsOpen={() => toggleSettings('candle')} settingsOpen={openSettings === 'candle'} settingsContent={<div className="text-[12px] text-muted-foreground/60 py-2">No adjustable parameters for candles.</div>} />
              )}
              {match('Elliott Wave') && (
                <IndicatorRow color="#22c55e" label="Elliott Wave" sublabel="Auto" checked={state.showElliott} onCheck={(v: boolean) => setState(s => ({ ...s, showElliott: v }))} onSettingsOpen={() => toggleSettings('elliott')} settingsOpen={openSettings === 'elliott'} settingsContent={<div className="text-[12px] text-muted-foreground/60 py-2 leading-relaxed">Automatic detection of motive (1–5) and corrective (A–B–C) wave patterns. Calculation is based on fractal swing highs/lows.</div>} />
              )}
              {match('TD Sequential') && (
                <IndicatorRow color="#f59e0b" label="TD Sequential" checked={state.showTD} onCheck={(v: boolean) => setState(s => ({ ...s, showTD: v }))} onSettingsOpen={() => toggleSettings('td')} settingsOpen={openSettings === 'td'} settingsContent={<div className="space-y-4"><ParamSelect label="Setup from" value={state.setupFrom} onChange={(v: number) => setState(s => ({ ...s, setupFrom: v }))} options={[1, 5, 7, 9].map((v) => ({ value: v, label: `${v}+` }))} /><ParamSelect label="Countdown from" value={state.countdownFrom} onChange={(v: number) => setState(s => ({ ...s, countdownFrom: v }))} options={[9, 10, 11, 12, 13].map((v) => ({ value: v, label: `${v}+` }))} /><ParamSelect label="Cooldown bars" value={state.cooldown} onChange={(v: number) => setState(s => ({ ...s, cooldown: v }))} options={[0, 5, 10, 15, 20].map((v) => ({ value: v, label: `${v}` }))} /></div>} />
              )}
            </>
          )}

          {/* Moving Averages group */}
          {(match('MA') || match('Moving Average') || match('SMA') || match('EMA') || match('WMA')) ? (
            <>
              <SectionLabel>Moving Averages</SectionLabel>
              {state.maConfigs.map((cfg, idx) => (
                <IndicatorRow 
                  key={`${cfg.type}-${cfg.period}-${idx}`} 
                  color={cfg.color} 
                  label={`${cfg.type} ${cfg.period}`} 
                  checked={cfg.enabled} 
                  onCheck={(v: boolean) => setState(s => ({ ...s, maConfigs: s.maConfigs.map((c, i) => i === idx ? { ...c, enabled: v } : c) }))} 
                  onSettingsOpen={() => toggleSettings(`ma-${idx}`)} 
                  settingsOpen={openSettings === `ma-${idx}`} 
                  onMoveUp={() => moveMA(idx, 'up')}
                  onMoveDown={() => moveMA(idx, 'down')}
                  isFirst={idx === 0}
                  isLast={idx === state.maConfigs.length - 1}
                  extra={<button onClick={(e) => { e.stopPropagation(); setState(s => ({ ...s, maConfigs: s.maConfigs.filter((_, i) => i !== idx) })); }} className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-rose-500/10 text-muted-foreground/40 hover:text-rose-500"><X className="w-3 h-3" /></button>} 
                  settingsContent={<div className="space-y-4"><div className="flex items-center justify-between gap-4"><span className="text-[12px] text-muted-foreground/80 font-medium">Color</span><input type="color" value={cfg.color} onChange={(e) => setState(s => ({ ...s, maConfigs: s.maConfigs.map((c, i) => i === idx ? { ...c, color: e.target.value } : c) }))} className="w-12 h-7 rounded-md cursor-pointer border border-border/40 p-0.5 bg-foreground/[0.02]" /></div><ParamSelect label="Type" value={cfg.type} onChange={(v: string) => setState(s => ({ ...s, maConfigs: s.maConfigs.map((c, i) => i === idx ? { ...c, type: v } : c) }))} options={['SMA', 'EMA', 'WMA'].map((v) => ({ value: v, label: v }))} /><ParamRow label="Period" value={cfg.period} min={2} max={500} onChange={(v: number) => setState(s => ({ ...s, maConfigs: s.maConfigs.map((c, i) => i === idx ? { ...c, period: v } : c) }))} /></div>} 
                />
              ))}
              <div className="px-4 py-2">
                <button onClick={() => setState(s => ({ ...s, maConfigs: [...s.maConfigs, { type: 'SMA', period: 100, color: '#94a3b8', enabled: true }] }))} className="flex items-center justify-center gap-1.5 w-full py-1.5 rounded-md text-[11px] font-medium border border-dashed border-border/50 text-muted-foreground/70 hover:text-foreground hover:bg-foreground/[0.02] hover:border-border transition-all">
                  <Plus className="w-3 h-3" /> Add MA
                </button>
              </div>
            </>
          ) : null}

          {/* Oscillators group */}
          {(match('MACD') || match('RSI') || match('Squeeze Momentum') || match('Supertrend')) && (
            <>
              <SectionLabel>Oscillators</SectionLabel>
              {match('MACD') && (
                <IndicatorRow color="#38bdf8" label="MACD" sublabel={`${state.macdFast} ${state.macdSlow} ${state.macdSignal}`} checked={state.showMACD} onCheck={(v: boolean) => setState(s => ({ ...s, showMACD: v }))} onSettingsOpen={() => toggleSettings('macd')} settingsOpen={openSettings === 'macd'} settingsContent={<div className="space-y-4"><ParamRow label="Fast Length" value={state.macdFast} min={1} max={100} onChange={(v: number) => setState(s => ({ ...s, macdFast: v }))} /><ParamRow label="Slow Length" value={state.macdSlow} min={1} max={200} onChange={(v: number) => setState(s => ({ ...s, macdSlow: v }))} /><ParamRow label="Signal Smoothing" value={state.macdSignal} min={1} max={50} onChange={(v: number) => setState(s => ({ ...s, macdSignal: v }))} /></div>} />
              )}
              {match('RSI') && (
                <IndicatorRow color="#60a5fa" label="RSI" sublabel={`${state.rsiPeriod}`} checked={state.showRSI} onCheck={(v: boolean) => setState(s => ({ ...s, showRSI: v }))} onSettingsOpen={() => toggleSettings('rsi')} settingsOpen={openSettings === 'rsi'} settingsContent={<div className="space-y-4"><ParamRow label="RSI Length" value={state.rsiPeriod} min={2} max={100} onChange={(v: number) => setState(s => ({ ...s, rsiPeriod: v }))} /></div>} />
              )}
              {match('Squeeze Momentum') && (
                <IndicatorRow color="#4ade80" label="Squeeze Momentum" sublabel={state.showSqz ? `${state.sqzBbLen} ${state.sqzKcLen}` : undefined} checked={state.showSqz} onCheck={(v: boolean) => setState(s => ({ ...s, showSqz: v }))} onSettingsOpen={() => toggleSettings('sqz')} settingsOpen={openSettings === 'sqz'} settingsContent={<div className="space-y-4"><ParamRow label="BB Length" value={state.sqzBbLen} min={5} max={50} onChange={(v: number) => setState(s => ({ ...s, sqzBbLen: v }))} /><ParamRow label="BB Mult" value={state.sqzBbMult} min={0.5} max={5} step={0.1} onChange={(v: number) => setState(s => ({ ...s, sqzBbMult: v }))} /><ParamRow label="KC Length" value={state.sqzKcLen} min={5} max={50} onChange={(v: number) => setState(s => ({ ...s, sqzKcLen: v }))} /><ParamRow label="KC Mult" value={state.sqzKcMult} min={0.5} max={5} step={0.1} onChange={(v: number) => setState(s => ({ ...s, sqzKcMult: v }))} /></div>} />
              )}
              {match('Supertrend') && (
                <IndicatorRow color="#f43f5e" label="Supertrend" sublabel={state.showST ? `ATR ${state.stPeriod} × ${state.stMult}` : undefined} checked={state.showST} onCheck={(v: boolean) => setState(s => ({ ...s, showST: v }))} onSettingsOpen={() => toggleSettings('st')} settingsOpen={openSettings === 'st'} settingsContent={<div className="space-y-4"><ParamRow label="ATR Period" value={state.stPeriod} min={2} max={50} onChange={(v: number) => setState(s => ({ ...s, stPeriod: v }))} /><ParamRow label="Multiplier" value={state.stMult} min={0.5} max={10} step={0.1} onChange={(v: number) => setState(s => ({ ...s, stMult: v }))} /></div>} />
              )}
            </>
          )}
        </div>
      </div>
    );
  }, [sidebarSearch, state, openSettings]);

  return (
    <AppShell hideFooter>
      <NavigatorShell
        sidebarOpen={sidebarOpen && !isFullscreen}
        onSidebarToggle={() => setSidebarOpen((o) => !o)}
        sidebarIcon={<BarChart2 className="w-4 h-4 text-sky-500" />}
        sidebarLabel="Indicators"
        sidebarContent={sidebarContent}
      >
        <div className={`h-full flex flex-col bg-background relative ${isFullscreen ? 'fixed inset-0 z-50' : ''}`}>
          
          {/* ── Top Bar ── */}
          <div className="h-12 px-4 border-b border-border/40 flex items-center justify-between shrink-0 bg-background/95 backdrop-blur z-10 shadow-sm">
            <div className="flex items-center gap-4">
              {/* Ticker Input */}
              <div className="relative flex items-center">
                <Search className="w-3.5 h-3.5 absolute left-2.5 text-muted-foreground/50" />
                <input
                  value={tickerInput}
                  onChange={(e) => setTickerInput(e.target.value.toUpperCase())}
                  onKeyDown={(e) => { if (e.key === 'Enter') applyTicker(); }}
                  onBlur={applyTicker}
                  maxLength={10}
                  placeholder="Symbol"
                  className="w-28 pl-8 pr-3 py-1.5 bg-foreground/[0.02] border border-border/50 rounded-lg text-[13px] font-bold tracking-wide focus:outline-none focus:border-sky-500/50 focus:ring-1 focus:ring-sky-500/20 text-foreground transition-all uppercase placeholder:font-normal"
                />
              </div>

              <div className="w-px h-5 bg-border/50" />

              {/* Frequency Segmented Control */}
              <div className="flex p-0.5 bg-foreground/[0.02] border border-border/40 rounded-lg">
                {(['D', 'W', 'M'] as Frequency[]).map((f) => (
                  <button
                    key={f}
                    onClick={() => {
                      const newStart = isoDateYearsAgo(FREQ_CONFIG[f].years);
                      setState(s => ({ ...s, freq: f, startDate: newStart }));
                    }}
                    className={`px-3 py-1 rounded-md text-[11px] font-semibold transition-all ${
                      state.freq === f 
                        ? 'bg-background shadow-sm text-foreground ring-1 ring-border/50' 
                        : 'text-muted-foreground/70 hover:text-foreground hover:bg-foreground/[0.02]'
                    }`}
                  >
                    {FREQ_CONFIG[f].label}
                  </button>
                ))}
              </div>

              <div className="w-px h-5 bg-border/50 hidden sm:block" />

              {/* Date Range */}
              <div className="hidden sm:flex items-center gap-2">
                <input type="date" value={state.startDate} onChange={(e) => setState(s => ({ ...s, startDate: e.target.value }))} className="bg-transparent text-[12px] text-muted-foreground hover:text-foreground focus:outline-none cursor-pointer" style={{ colorScheme: isLight ? 'light' : 'dark' }} />
                <ChevronRight className="w-3 h-3 text-muted-foreground/30" />
                <input type="date" value={state.endDate} max={today} onChange={(e) => setState(s => ({ ...s, endDate: e.target.value }))} className="bg-transparent text-[12px] text-muted-foreground hover:text-foreground focus:outline-none cursor-pointer" style={{ colorScheme: isLight ? 'light' : 'dark' }} />
              </div>
            </div>

            <div className="flex items-center gap-3">
              {/* Status Indicator */}
              <div className="flex items-center gap-1.5 px-2">
                {isFetching ? (
                  <><Loader2 className="w-3.5 h-3.5 animate-spin text-sky-500" /><span className="text-[11px] font-medium text-sky-500">Updating</span></>
                ) : (
                  <><span className="relative flex h-2 w-2"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span><span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span></span><span className="text-[11px] font-medium text-muted-foreground">Live</span></>
                )}
              </div>

              <div className="w-px h-5 bg-border/50" />

              <button
                onClick={() => setShowAiSummary(!showAiSummary)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all ${showAiSummary ? 'bg-sky-500/10 text-sky-500 ring-1 ring-sky-500/30' : 'bg-foreground/[0.02] border border-border/40 text-muted-foreground hover:text-foreground hover:bg-foreground/[0.04]'}`}
              >
                <BrainCircuit className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">AI Analysis</span>
              </button>

              <button
                onClick={() => setIsFullscreen(!isFullscreen)}
                className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-foreground/5 rounded-lg transition-colors"
                title="Toggle Fullscreen"
              >
                {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* ── Chart Area ── */}
          <div className="flex-1 relative min-h-0 bg-background">
            {/* Floating AI Panel */}
            {showAiSummary && (
              <div className={`absolute top-4 left-4 z-20 w-[400px] max-h-[85%] flex flex-col ${isLight ? 'bg-white/95 border-sky-200' : 'bg-[#0a0f1d]/95 border-sky-500/20'} backdrop-blur-2xl border rounded-2xl shadow-2xl overflow-hidden animate-in fade-in slide-in-from-left-4 duration-300 ring-1 ${isLight ? 'ring-black/5' : 'ring-white/5'}`}>
                <div className={`px-5 py-3.5 border-b flex items-center justify-between ${isLight ? 'border-sky-100 bg-sky-50/50' : 'border-white/5 bg-sky-500/5'}`}>
                  <div className="flex items-center gap-2.5 text-sky-500">
                    <div className={`p-1 rounded-lg ${isLight ? 'bg-sky-500/10' : 'bg-sky-500/10'}`}>
                      <BrainCircuit className="w-4 h-4" />
                    </div>
                    <span className="text-[13px] font-bold uppercase tracking-wider">Intelligence Report</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {summaryQuery.data?.summary && (
                      <div className={`flex items-center gap-1 mr-2 border-r pr-2 ${isLight ? 'border-sky-100' : 'border-white/10'}`}>
                        <button
                          onClick={() => handleExport('pdf')}
                          disabled={!!exportingFormat}
                          className={`p-1.5 rounded-md transition-all ${isLight ? 'hover:bg-sky-500/5 text-muted-foreground hover:text-sky-600' : 'hover:bg-white/5 text-muted-foreground hover:text-sky-400'}`}
                          title="Export to PDF"
                        >
                          {exportingFormat === 'pdf' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}
                        </button>
                        <button
                          onClick={() => handleExport('pptx')}
                          disabled={!!exportingFormat}
                          className={`p-1.5 rounded-md transition-all ${isLight ? 'hover:bg-amber-500/5 text-muted-foreground hover:text-amber-600' : 'hover:bg-white/5 text-muted-foreground hover:text-amber-400'}`}
                          title="Export to PowerPoint"
                        >
                          {exportingFormat === 'pptx' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <PresentationIcon className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    )}
                    {summaryQuery.isFetching && !exportingFormat && <Loader2 className="w-3.5 h-3.5 animate-spin text-sky-500/50" />}
                    <button 
                      onClick={() => setShowAiSummary(false)} 
                      className="text-muted-foreground hover:text-foreground transition-colors p-1.5 hover:bg-foreground/5 rounded-md"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <div className="p-4 overflow-y-auto custom-scrollbar">
                  {summaryQuery.data?.summary ? (
                    <div className={`prose ${isLight ? 'prose-slate' : 'prose-invert'} prose-xs max-w-none`}>
                      <ReactMarkdown
                        components={{
                          h1: ({node, ...props}) => <h1 className="text-sky-500 font-bold text-[15px] mb-4 mt-2 border-b border-sky-500/20 pb-2 flex items-center gap-2" {...props} />,
                          h2: ({node, ...props}) => <h2 className="text-foreground font-bold text-[13px] mb-3 mt-6 flex items-center gap-2 before:w-1 before:h-3.5 before:bg-sky-500 before:rounded-full" {...props} />,
                          h3: ({node, ...props}) => <h3 className="text-foreground/90 font-bold text-[12px] mb-2 mt-4 underline decoration-sky-500/30 underline-offset-4" {...props} />,
                          p: ({node, ...props}) => <p className="mb-4 text-[12px] leading-[1.6] text-foreground/70" {...props} />,
                          ul: ({node, ...props}) => <ul className="mb-4 space-y-2 list-none pl-0" {...props} />,
                          li: ({node, ...props}) => (
                            <li className="flex gap-2 text-[12px] text-foreground/70 items-start">
                              <span className="text-sky-500 mt-1.5 shrink-0">•</span>
                              <span>{props.children}</span>
                            </li>
                          ),
                          strong: ({node, ...props}) => <strong className={`${isLight ? 'text-sky-700' : 'text-sky-200/90'} font-semibold`} {...props} />,
                          blockquote: ({node, ...props}) => (
                            <blockquote className={`my-4 p-3 rounded-xl border-l-2 italic ${isLight ? 'bg-sky-50 border-sky-200 text-sky-800' : 'bg-sky-500/5 border-sky-500/40 text-foreground/80'}`} {...props} />
                          ),
                        }}
                      >
                        {summaryQuery.data.summary}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-12 gap-4 text-muted-foreground">
                      <div className="relative">
                        <Activity className="w-8 h-8 animate-pulse text-sky-500/20" />
                        <Loader2 className="w-8 h-8 animate-spin text-sky-500 absolute inset-0" />
                      </div>
                      <span className="text-[12px] font-medium animate-pulse">Generating Intelligence Report...</span>
                    </div>
                  )}
                </div>
                {summaryQuery.data?.summary && (
                  <div className={`px-5 py-3 border-t text-center ${isLight ? 'border-sky-100 bg-sky-50/30' : 'border-white/5 bg-black/20'}`}>
                    <span className="text-[10px] text-muted-foreground/40 uppercase tracking-[0.2em]">End of Analysis</span>
                  </div>
                )}
              </div>
            )}

            {/* Error State */}
            {!isLoading && error && (
              <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/50 backdrop-blur-sm">
                <div className="bg-rose-500/10 text-rose-500 px-4 py-2 rounded-lg border border-rose-500/20 text-sm font-medium">
                  {(error as Error)?.message || 'Failed to load chart'}
                </div>
              </div>
            )}

            {/* Plotly Chart */}
            <div ref={plotContainerRef} className="w-full h-full">
              {cleanedFigure && (
                <Plot
                  data={cleanedFigure.data}
                  layout={{ ...cleanedFigure.layout, autosize: true }}
                  config={{
                    responsive: true, displaylogo: false, displayModeBar: 'hover',
                    scrollZoom: true,
                    modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d', 'toggleSpikelines'],
                  }}
                  style={{ width: '100%', height: '100%' }}
                  onInitialized={(_f: any, gd: any) => { plotGraphDivRef.current = gd; }}
                />
              )}
            </div>
          </div>
        </div>
      </NavigatorShell>
    </AppShell>
  );
}
