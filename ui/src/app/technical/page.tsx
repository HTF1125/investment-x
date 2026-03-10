'use client';

import dynamic from 'next/dynamic';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import AppShell from '@/components/AppShell';
import Modal from '@/components/Modal';
import NavigatorShell from '@/components/NavigatorShell';
import {
  Activity, Loader2, BrainCircuit, BarChart2, Settings2, Plus, X, Search, ChevronRight, Minimize2, Maximize2,
  ChevronUp, ChevronDown, FileText, Presentation as PresentationIcon
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { apiFetchJson, apiFetch } from '@/lib/api';
import { useTheme } from '@/context/ThemeContext';
import { useDebounce } from '@/lib/hooks/useDebounce';
import { useResponsiveSidebar } from '@/lib/hooks/useResponsiveSidebar';
import { useNativeInputStyle } from '@/lib/hooks/useNativeInputStyle';
import ReactMarkdown from 'react-markdown';
import { ChartErrorBoundary } from '@/components/ChartErrorBoundary';

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center bg-background animate-in fade-in duration-500">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-border border-t-foreground rounded-full animate-spin" />
        <span className="text-[11px] text-muted-foreground/60 tracking-[0.12em] font-medium uppercase">Loading</span>
      </div>
    </div>
  ),
}) as React.ComponentType<Record<string, unknown>>;

// ─── Utilities & Constants ───────────────────────────────────────────────────


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
const MA_COLORS = ['#f59e0b', '#38bdf8', '#8b5cf6', '#22c55e', '#f43f5e', '#06b6d4', '#a3e635', '#fb923c', '#e879f9', '#94a3b8', '#14b8a6', '#ec4899'];
const COMMON_PERIODS = [5, 10, 20, 50, 100, 200] as const;

function todayIso() { return new Date().toISOString().slice(0, 10); }
function isoDateYearsAgo(years: number) {
  const d = new Date(); d.setFullYear(d.getFullYear() - years); return d.toISOString().slice(0, 10);
}

// ─── UI Components ───────────────────────────────────────────────────────────

interface ParamRowProps {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
}

function ParamRow({ label, value, onChange, min, max, step }: ParamRowProps) {
  const nativeInputStyle = useNativeInputStyle();
  return (
    <div className="flex items-center justify-between gap-4 group">
      <span className="text-[12px] text-muted-foreground/80 font-medium group-hover:text-foreground/90 transition-colors">{label}</span>
      <input
        type="number" value={value as number} min={min} max={max} step={step ?? 1}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-20 text-right text-[12px] bg-primary/[0.03] border border-border/40 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 text-foreground transition-all"
        style={nativeInputStyle}
      />
    </div>
  );
}

function ParamSelect({ label, value, onChange, options }: {
  label: string; value: string | number; onChange: (v: string) => void;
  options: { value: string | number; label: string }[];
}) {
  const nativeInputStyle = useNativeInputStyle();
  return (
    <div className="flex items-center justify-between gap-4 group">
      <span className="text-[12px] text-muted-foreground/80 font-medium group-hover:text-foreground/90 transition-colors">{label}</span>
      <select
        value={value} onChange={(e) => onChange(e.target.value)}
        className="text-[12px] bg-primary/[0.03] border border-border/40 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 text-foreground cursor-pointer transition-all appearance-none pr-8 relative"
        style={{ ...nativeInputStyle, backgroundImage: 'url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%2371717A%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E")', backgroundRepeat: 'no-repeat', backgroundPosition: 'right 0.7rem top 50%', backgroundSize: '0.65rem auto' }}
      >
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}

interface IndicatorRowProps {
  color: string;
  label: string;
  sublabel?: string;
  checked: boolean;
  onCheck: (v: boolean) => void;
  onSettingsOpen?: () => void;
  settingsOpen?: boolean;
  settingsContent?: React.ReactNode;
  extra?: React.ReactNode;
  onMoveUp?: () => void;
  onMoveDown?: () => void;
  isFirst?: boolean;
  isLast?: boolean;
}

function IndicatorRow({
  color, label, sublabel, checked, onCheck, onSettingsOpen, settingsOpen, settingsContent, extra,
  onMoveUp, onMoveDown, isFirst, isLast
}: IndicatorRowProps) {
  return (
    <div className="relative">
      <div
        className={`flex items-center gap-3 px-3 py-1.5 group hover:bg-primary/10 transition-all cursor-pointer select-none rounded-lg mx-2 ${checked ? 'bg-primary/[0.04]' : ''}`}
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
              <span className="text-[10px] text-primary/40 font-bold tabular-nums truncate">{sublabel}</span>
            )}
          </div>
        </div>

        {/* Reordering Controls (Shown on hover) */}
        {(onMoveUp || onMoveDown) && (
          <div className="flex flex-col opacity-0 group-hover:opacity-100 transition-opacity">
            {onMoveUp && !isFirst && (
              <button 
                onClick={(e) => { e.stopPropagation(); onMoveUp(); }}
                className="p-0.5 hover:text-primary text-muted-foreground/30 transition-colors"
              >
                <ChevronUp className="w-3 h-3" />
              </button>
            )}
            {onMoveDown && !isLast && (
              <button 
                onClick={(e) => { e.stopPropagation(); onMoveDown(); }}
                className="p-0.5 hover:text-primary text-muted-foreground/30 transition-colors"
              >
                <ChevronDown className="w-3 h-3" />
              </button>
            )}
          </div>
        )}

        {extra}

        {/* Settings Gear - Prominent on Hover */}
        <button
          onClick={(e) => { e.stopPropagation(); onSettingsOpen?.(); }}
          className="shrink-0 opacity-0 group-hover:opacity-100 transition-all p-1.5 rounded-md bg-primary/[0.06] hover:bg-primary/10 text-muted-foreground/60 hover:text-foreground shadow-sm"
          title="Settings"
        >
          <Settings2 className="w-4 h-4" />
        </button>
      </div>

      {onSettingsOpen && <Modal open={!!settingsOpen} title={`${label} Settings`} onClose={onSettingsOpen} maxWidth="max-w-[320px]">{settingsContent}</Modal>}
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
  useEffect(() => { document.title = 'Technical Analysis | Investment-X'; }, []);
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
    
    showElliott: true,
    showTD: true,
    showMACD: true,
    showRSI: true,
    showSqz: false,
    showST: false,
    showBB: false,
    showVWAP: false,
    showStoch: false,
    showATR: false,

    setupFrom: 9,
    countdownFrom: 13,
    cooldown: 0,
    macdFast: 12, macdSlow: 26, macdSignal: 9,
    rsiPeriod: 14,
    sqzBbLen: 20, sqzBbMult: 2.0, sqzKcLen: 20, sqzKcMult: 1.5,
    stPeriod: 10, stMult: 3.0,
    bbLen: 20, bbMult: 2.0,
    stochK: 14, stochD: 3, stochSmooth: 3,
    atrPeriod: 14,
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
  const { sidebarOpen, toggleSidebar } = useResponsiveSidebar();
  const [openSettings, setOpenSettings] = useState<string | null>(null);
  const [showAiSummary, setShowAiSummary] = useState(false);
  const [maAdderOpen, setMaAdderOpen] = useState(false);
  const [maAdderType, setMaAdderType] = useState<'SMA' | 'EMA' | 'WMA'>('SMA');
  const [maAdderPeriods, setMaAdderPeriods] = useState<Set<number>>(new Set());
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [exportingFormat, setExportingFormat] = useState<string | null>(null);
  const [toastError, setToastError] = useState<string | null>(null);

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
      setToastError('Failed to generate ' + format.toUpperCase());
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

  // Track user's zoom/pan state to preserve across indicator changes
  const userAxisState = useRef<Record<string, any>>({});
  const lastTicker = useRef(state.ticker);

  // Reset zoom state when ticker changes
  if (state.ticker !== lastTicker.current) {
    userAxisState.current = {};
    lastTicker.current = state.ticker;
  }

  const handleRelayout = useCallback((e: any) => {
    if (!e) return;
    const updated: Record<string, any> = {};
    // Capture any axis range changes from user interaction (zoom/pan/double-click reset)
    for (const key of Object.keys(e)) {
      if (/^[xy]axis\d*\.range\[\d\]$/.test(key) || /^[xy]axis\d*\.autorange$/.test(key)) {
        updated[key] = e[key];
      }
    }
    if (Object.keys(updated).length > 0) {
      // If user resets via double-click (autorange:true), clear saved state for that axis
      for (const key of Object.keys(updated)) {
        if (key.endsWith('.autorange') && updated[key] === true) {
          const axName = key.replace('.autorange', '');
          delete userAxisState.current[`${axName}.range[0]`];
          delete userAxisState.current[`${axName}.range[1]`];
        }
      }
      userAxisState.current = { ...userAxisState.current, ...updated };
    }
  }, []);

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
      showBB: s.technical_show_bb ?? prev.showBB,
      showVWAP: s.technical_show_vwap ?? prev.showVWAP,
      showStoch: s.technical_show_stoch ?? prev.showStoch,
      showATR: s.technical_show_atr ?? prev.showATR,
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
      technical_show_bb: debouncedState.showBB,
      technical_show_vwap: debouncedState.showVWAP,
      technical_show_stoch: debouncedState.showStoch,
      technical_show_atr: debouncedState.showATR,
      technical_ma_configs: debouncedState.maConfigs,
    });
  }, [
    debouncedState.ticker, debouncedState.freq, debouncedState.showSqz, debouncedState.showST,
    debouncedState.showElliott, debouncedState.showTD, debouncedState.showMACD, debouncedState.showRSI,
    debouncedState.showBB, debouncedState.showVWAP, debouncedState.showStoch, debouncedState.showATR,
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
    placeholderData: keepPreviousData,
  });

  const hasOverlays = debouncedState.showSqz || debouncedState.showST || debouncedState.showBB || debouncedState.showVWAP || debouncedState.showStoch || debouncedState.showATR || debouncedState.maConfigs.some(m => m.enabled);
  const masStr = debouncedState.maConfigs.filter(m => m.enabled).map(m => `${m.type}:${m.period}:${m.color}`).join(',');

  const overlayQueryKey = useMemo(() => [
    'technical-overlays', debouncedState.ticker, interval,
    debouncedState.showSqz, debouncedState.sqzBbLen, debouncedState.sqzBbMult, debouncedState.sqzKcLen, debouncedState.sqzKcMult,
    debouncedState.showST, debouncedState.stPeriod, debouncedState.stMult,
    debouncedState.showBB, debouncedState.bbLen, debouncedState.bbMult,
    debouncedState.showVWAP,
    debouncedState.showStoch, debouncedState.stochK, debouncedState.stochD, debouncedState.stochSmooth,
    debouncedState.showATR, debouncedState.atrPeriod,
    masStr
  ], [debouncedState, interval, masStr]);

  const { data: overlayData, isFetching: isFetchingOverlays } = useQuery({
    queryKey: overlayQueryKey,
    queryFn: () => {
      const p = new URLSearchParams({
        ticker: debouncedState.ticker,
        interval,
        sqz: String(debouncedState.showSqz),
        sqz_bb_len: String(debouncedState.sqzBbLen),
        sqz_bb_mult: String(debouncedState.sqzBbMult),
        sqz_kc_len: String(debouncedState.sqzKcLen),
        sqz_kc_mult: String(debouncedState.sqzKcMult),
        st: String(debouncedState.showST),
        st_period: String(debouncedState.stPeriod),
        st_mult: String(debouncedState.stMult),
        bb: String(debouncedState.showBB),
        bb_len: String(debouncedState.bbLen),
        bb_mult: String(debouncedState.bbMult),
        vwap: String(debouncedState.showVWAP),
        stoch: String(debouncedState.showStoch),
        stoch_k: String(debouncedState.stochK),
        stoch_d: String(debouncedState.stochD),
        stoch_smooth: String(debouncedState.stochSmooth),
        atr: String(debouncedState.showATR),
        atr_period: String(debouncedState.atrPeriod),
      });
      if (masStr) p.set('mas', masStr);
      return apiFetchJson(`/api/technical/overlays?${p}`);
    },
    enabled: hasOverlays,
    staleTime: 60_000,
    placeholderData: keepPreviousData,
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
    const cloned = structuredClone(fig);
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
    if (overlayData?.bollinger) {
      const bb = overlayData.bollinger;
      overlayTraces.push({
        type: 'scatter', x: bb.dates, y: bb.upper, mode: 'lines',
        line: { color: 'rgba(33,150,243,0.5)', width: 1 },
        name: 'BB Upper', legendgroup: 'bb', hovertemplate: 'BB Upper: %{y:.2f}<extra></extra>',
      });
      overlayTraces.push({
        type: 'scatter', x: bb.dates, y: bb.lower, mode: 'lines',
        line: { color: 'rgba(33,150,243,0.5)', width: 1 },
        fill: 'tonexty', fillcolor: isLight ? 'rgba(33,150,243,0.06)' : 'rgba(33,150,243,0.08)',
        name: 'BB Lower', legendgroup: 'bb', hovertemplate: 'BB Lower: %{y:.2f}<extra></extra>',
      });
      overlayTraces.push({
        type: 'scatter', x: bb.dates, y: bb.middle, mode: 'lines',
        line: { color: 'rgba(33,150,243,0.7)', width: 1, dash: 'dot' },
        name: 'BB Mid', legendgroup: 'bb', hovertemplate: 'BB Mid: %{y:.2f}<extra></extra>',
      });
    }
    if (overlayData?.vwap) {
      overlayTraces.push({
        type: 'scatter', x: overlayData.vwap.dates, y: overlayData.vwap.vwap, mode: 'lines',
        line: { color: '#ff9800', width: 1.5 }, name: 'VWAP', legendgroup: 'vwap',
        hovertemplate: 'VWAP: %{y:.2f}<extra></extra>',
      });
    }

    if (overlayTraces.length) {
      cloned.data = [cloned.data[0], ...overlayTraces, ...cloned.data.slice(1)];
    }

    // === Sub-chart layout: recalculate domains to add oscillator rows ===
    // Determine how many backend sub-chart rows exist
    const backendSubCount = (debouncedState.showMACD ? 1 : 0) + (debouncedState.showRSI ? 1 : 0);
    // Frontend oscillator sub-charts
    const frontendOscillators: string[] = [];
    if (overlayData?.squeeze && debouncedState.showSqz) frontendOscillators.push('sqz');
    if (overlayData?.stochastic && debouncedState.showStoch) frontendOscillators.push('stoch');
    if (overlayData?.atr && debouncedState.showATR) frontendOscillators.push('atr');

    const totalSubCharts = backendSubCount + frontendOscillators.length;
    const totalRows = 1 + totalSubCharts;

    if (totalSubCharts > 0) {
      const SPACING = 0.035;
      const mainWeight = 3;
      const totalWeight = mainWeight + totalSubCharts;
      const totalSpacingUsed = SPACING * totalSubCharts;
      const available = 1.0 - totalSpacingUsed;

      let top = 1.0;
      const domains: [number, number][] = [];
      const weights = [mainWeight, ...Array(totalSubCharts).fill(1)];
      for (let i = 0; i < totalRows; i++) {
        const height = (weights[i] / totalWeight) * available;
        const bottom = top - height;
        domains.push([Math.max(0, bottom), top]);
        top = bottom - SPACING;
      }

      // Apply domains to main chart
      if (cloned.layout.yaxis) cloned.layout.yaxis.domain = domains[0];

      // Apply domains to backend sub-chart rows (yaxis2, yaxis3, ...)
      for (let i = 0; i < backendSubCount; i++) {
        const axNum = i + 2;
        const yKey = `yaxis${axNum}`;
        if (cloned.layout[yKey]) {
          cloned.layout[yKey].domain = domains[1 + i];
          // Remove any anchoring that conflicts with the new domain
          delete cloned.layout[yKey].overlaying;
        }
      }

      // Create frontend oscillator sub-chart rows
      const nextAxisNum = 1 + backendSubCount + 1; // e.g., 4 if MACD+RSI exist
      for (let i = 0; i < frontendOscillators.length; i++) {
        const axNum = nextAxisNum + i;
        const domain = domains[1 + backendSubCount + i];
        const yRef = `y${axNum}`;
        const xRef = `x${axNum}`;
        const yKey = `yaxis${axNum}`;
        const xKey = `xaxis${axNum}`;

        cloned.layout[yKey] = {
          domain,
          showgrid: true, gridcolor: grid,
          zeroline: true, zerolinecolor: grid,
          linecolor: isLight ? 'rgba(0,0,0,0.15)' : 'rgba(255,255,255,0.1)',
          tickfont: { color: fg, size: 10 },
          showticklabels: true,
          anchor: xRef,
        };
        cloned.layout[xKey] = {
          matches: 'x',
          showticklabels: i === frontendOscillators.length - 1 && !backendSubCount ? true : false,
          anchor: yRef,
        };

        const osc = frontendOscillators[i];
        if (osc === 'sqz') {
          const sqz = overlayData.squeeze;
          const barColors = sqz.bar_color.map((c: string) => SQZ_BAR_COLOR[c] ?? '#64748b');
          const dotColors = sqz.sqz_dot_color.map((c: string) => SQZ_DOT_COLOR[c] ?? '#64748b');
          cloned.data.push({
            type: 'bar', x: overlayData.dates, y: sqz.val, marker: { color: barColors },
            name: 'SQZ Mom', yaxis: yRef, xaxis: xRef, legendgroup: 'squeeze',
            hovertemplate: 'SQZ: %{y:.4f}<extra></extra>',
          });
          cloned.data.push({
            type: 'scatter', x: overlayData.dates, y: overlayData.dates.map(() => 0), mode: 'markers',
            marker: { color: dotColors, size: 4, symbol: 'cross-thin', line: { width: 1.5, color: dotColors } },
            name: 'SQZ State', yaxis: yRef, xaxis: xRef, legendgroup: 'squeeze', showlegend: false,
            hovertemplate: 'SQZ State<extra></extra>',
          });
          cloned.layout[yKey].zeroline = true;
          cloned.layout[yKey].zerolinecolor = isLight ? 'rgba(0,0,0,0.2)' : 'rgba(255,255,255,0.1)';
          cloned.layout[yKey].zerolinewidth = 1;
        } else if (osc === 'stoch') {
          const stoch = overlayData.stochastic;
          cloned.data.push({
            type: 'scatter', x: stoch.dates, y: stoch.k, mode: 'lines',
            line: { color: '#2196f3', width: 1.5 }, name: '%K',
            yaxis: yRef, xaxis: xRef, legendgroup: 'stoch',
            hovertemplate: '%K: %{y:.1f}<extra></extra>',
          });
          cloned.data.push({
            type: 'scatter', x: stoch.dates, y: stoch.d, mode: 'lines',
            line: { color: '#ff5722', width: 1.5, dash: 'dot' }, name: '%D',
            yaxis: yRef, xaxis: xRef, legendgroup: 'stoch',
            hovertemplate: '%D: %{y:.1f}<extra></extra>',
          });
          cloned.layout[yKey].range = [0, 100];
        } else if (osc === 'atr') {
          const atrData = overlayData.atr;
          cloned.data.push({
            type: 'scatter', x: atrData.dates, y: atrData.atr, mode: 'lines',
            line: { color: '#ab47bc', width: 1.5 }, name: 'ATR',
            yaxis: yRef, xaxis: xRef, legendgroup: 'atr',
            hovertemplate: 'ATR: %{y:.4f}<extra></extra>',
          });
        }
      }
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
      uirevision: debouncedState.ticker,
    };

    // Add per-axis uirevision to preserve zoom/pan when sub-charts change
    for (let i = 0; i <= 8; i++) {
      const suffix = i === 0 ? '' : `${i + 1}`;
      const xKey = `xaxis${suffix}`;
      const yKey = `yaxis${suffix}`;
      if (cloned.layout[xKey]) cloned.layout[xKey].uirevision = debouncedState.ticker;
      if (cloned.layout[yKey]) cloned.layout[yKey].uirevision = debouncedState.ticker;
    }

    // Style all axes (main + up to 8 sub-chart axes)
    for (let i = 0; i <= 8; i++) {
      const suffix = i === 0 ? '' : `${i + 1}`;
      for (const prefix of ['xaxis', 'yaxis']) {
        const ax = `${prefix}${suffix}`;
        if (cloned.layout?.[ax]) {
          cloned.layout[ax].gridcolor = grid;
          cloned.layout[ax].zerolinecolor = cloned.layout[ax].zerolinecolor ?? grid;
          cloned.layout[ax].linecolor = isLight ? 'rgba(0,0,0,0.15)' : 'rgba(255,255,255,0.1)';
          cloned.layout[ax].tickfont = { ...(cloned.layout[ax].tickfont || {}), color: fg, size: 10 };
        }
      }
    }

    // Reapply user's zoom/pan state over the computed layout
    const axState = userAxisState.current;
    for (const key of Object.keys(axState)) {
      // key is like "xaxis.range[0]", "xaxis.range[1]", "xaxis.autorange"
      const match = key.match(/^([xy]axis\d*)\.(.+)$/);
      if (match) {
        const [, axName, prop] = match;
        if (!cloned.layout[axName]) continue;
        const rangeMatch = prop.match(/^range\[(\d)\]$/);
        if (rangeMatch) {
          if (!cloned.layout[axName].range) cloned.layout[axName].range = [undefined, undefined];
          cloned.layout[axName].range[Number(rangeMatch[1])] = axState[key];
          cloned.layout[axName].autorange = false;
        } else if (prop === 'autorange') {
          cloned.layout[axName].autorange = axState[key];
          if (axState[key]) delete cloned.layout[axName].range;
        }
      }
    }

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
            <Search className={`w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 transition-colors ${sidebarSearch ? 'text-primary' : 'text-muted-foreground/40'}`} />
            <input 
              value={sidebarSearch}
              onChange={(e) => setSidebarSearch(e.target.value)}
              placeholder="Search indicators..."
              className="w-full bg-primary/[0.04] border border-border/40 rounded-lg pl-8 pr-8 py-1.5 text-[11.5px] focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/15 transition-all placeholder:text-muted-foreground/30"
            />
            {sidebarSearch && (
              <button 
                onClick={() => setSidebarSearch('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 hover:bg-primary/10 rounded text-muted-foreground/40"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar pb-6">
          {/* On Chart group */}
          {(match('Elliott Wave') || match('TD Sequential') || match('Bollinger') || match('VWAP') || match('Supertrend')) && (
            <>
              <SectionLabel>On Chart</SectionLabel>
              {match('Elliott Wave') && (
                <IndicatorRow color="#22c55e" label="Elliott Wave" sublabel="Auto" checked={state.showElliott} onCheck={(v: boolean) => setState(s => ({ ...s, showElliott: v }))} onSettingsOpen={() => toggleSettings('elliott')} settingsOpen={openSettings === 'elliott'} settingsContent={<div className="text-[12px] text-muted-foreground/60 py-2 leading-relaxed">Automatic detection of motive (1–5) and corrective (A–B–C) wave patterns. Calculation is based on fractal swing highs/lows.</div>} />
              )}
              {match('TD Sequential') && (
                <IndicatorRow color="#f59e0b" label="TD Sequential" checked={state.showTD} onCheck={(v: boolean) => setState(s => ({ ...s, showTD: v }))} onSettingsOpen={() => toggleSettings('td')} settingsOpen={openSettings === 'td'} settingsContent={<div className="space-y-4"><ParamSelect label="Setup from" value={state.setupFrom} onChange={(v) => setState(s => ({ ...s, setupFrom: Number(v) }))} options={[1, 5, 7, 9].map((v) => ({ value: v, label: `${v}+` }))} /><ParamSelect label="Countdown from" value={state.countdownFrom} onChange={(v) => setState(s => ({ ...s, countdownFrom: Number(v) }))} options={[9, 10, 11, 12, 13].map((v) => ({ value: v, label: `${v}+` }))} /><ParamSelect label="Cooldown bars" value={state.cooldown} onChange={(v) => setState(s => ({ ...s, cooldown: Number(v) }))} options={[0, 5, 10, 15, 20].map((v) => ({ value: v, label: `${v}` }))} /></div>} />
              )}
              {match('Bollinger') && (
                <IndicatorRow color="#2196f3" label="Bollinger Bands" sublabel={state.showBB ? `${state.bbLen} ${state.bbMult}σ` : undefined} checked={state.showBB} onCheck={(v: boolean) => setState(s => ({ ...s, showBB: v }))} onSettingsOpen={() => toggleSettings('bb')} settingsOpen={openSettings === 'bb'} settingsContent={<div className="space-y-4"><ParamRow label="Length" value={state.bbLen} min={5} max={100} onChange={(v: number) => setState(s => ({ ...s, bbLen: v }))} /><ParamRow label="Multiplier" value={state.bbMult} min={0.5} max={5} step={0.1} onChange={(v: number) => setState(s => ({ ...s, bbMult: v }))} /></div>} />
              )}
              {match('VWAP') && (
                <IndicatorRow color="#ff9800" label="VWAP" checked={state.showVWAP} onCheck={(v: boolean) => setState(s => ({ ...s, showVWAP: v }))} onSettingsOpen={() => toggleSettings('vwap')} settingsOpen={openSettings === 'vwap'} settingsContent={<div className="text-[12px] text-muted-foreground/60 py-2">Volume Weighted Average Price. Cumulative, no adjustable parameters.</div>} />
              )}
              {match('Supertrend') && (
                <IndicatorRow color="#f43f5e" label="Supertrend" sublabel={state.showST ? `ATR ${state.stPeriod} × ${state.stMult}` : undefined} checked={state.showST} onCheck={(v: boolean) => setState(s => ({ ...s, showST: v }))} onSettingsOpen={() => toggleSettings('st')} settingsOpen={openSettings === 'st'} settingsContent={<div className="space-y-4"><ParamRow label="ATR Period" value={state.stPeriod} min={2} max={50} onChange={(v: number) => setState(s => ({ ...s, stPeriod: v }))} /><ParamRow label="Multiplier" value={state.stMult} min={0.5} max={10} step={0.1} onChange={(v: number) => setState(s => ({ ...s, stMult: v }))} /></div>} />
              )}
            </>
          )}

          {/* Moving Averages group */}
          {(match('MA') || match('Moving Average') || match('SMA') || match('EMA') || match('WMA')) ? (
            <>
              <SectionLabel>Moving Averages</SectionLabel>
              {(['SMA', 'EMA', 'WMA'] as const).map((maType) => {
                const typeConfigs = state.maConfigs.filter(c => c.type === maType);
                if (typeConfigs.length === 0) return null;
                const anyEnabled = typeConfigs.some(c => c.enabled);
                const firstColor = typeConfigs.find(c => c.enabled)?.color ?? typeConfigs[0].color;
                return (
                  <IndicatorRow
                    key={maType}
                    color={firstColor}
                    label={maType}
                    sublabel={anyEnabled ? typeConfigs.filter(c => c.enabled).map(c => c.period).sort((a, b) => a - b).join(', ') : undefined}
                    checked={anyEnabled}
                    onCheck={(v: boolean) => setState(s => ({ ...s, maConfigs: s.maConfigs.map(c => c.type === maType ? { ...c, enabled: v } : c) }))}
                    onSettingsOpen={() => toggleSettings(`ma-group-${maType}`)}
                    settingsOpen={openSettings === `ma-group-${maType}`}
                    settingsContent={
                      <div className="space-y-4">
                        {typeConfigs.map((cfg) => {
                          const idx = state.maConfigs.indexOf(cfg);
                          return (
                            <div key={idx} className="flex items-center gap-3 group/ma">
                              <input type="color" value={cfg.color} onChange={(e) => setState(s => ({ ...s, maConfigs: s.maConfigs.map((c, i) => i === idx ? { ...c, color: e.target.value } : c) }))} className="w-6 h-6 rounded cursor-pointer border border-border/40 p-0 bg-transparent shrink-0" />
                              <span className="text-[12px] font-mono font-medium text-foreground/80 w-10">{cfg.period}</span>
                              <button
                                onClick={() => setState(s => ({ ...s, maConfigs: s.maConfigs.map((c, i) => i === idx ? { ...c, enabled: !c.enabled } : c) }))}
                                className={`text-[10px] px-2 py-0.5 rounded-md border transition-all ${cfg.enabled ? 'border-primary/40 bg-primary/10 text-primary' : 'border-border/30 text-muted-foreground/40'}`}
                              >{cfg.enabled ? 'On' : 'Off'}</button>
                              <div className="flex-1" />
                              <button onClick={() => setState(s => ({ ...s, maConfigs: s.maConfigs.filter((_, i) => i !== idx) }))} className="opacity-0 group-hover/ma:opacity-100 transition-opacity p-1 rounded hover:bg-rose-500/10 text-muted-foreground/40 hover:text-rose-500"><X className="w-3 h-3" /></button>
                            </div>
                          );
                        })}
                      </div>
                    }
                  />
                );
              })}
              <div className="px-4 py-2 space-y-2">
                {maAdderOpen ? (
                  <div className="p-3 rounded-[var(--radius)] border border-border/50 bg-primary/[0.03] space-y-3">
                    {/* Type selector */}
                    <div className="flex p-0.5 bg-primary/[0.04] border border-border/40 rounded-lg">
                      {(['SMA', 'EMA', 'WMA'] as const).map((t) => (
                        <button key={t} onClick={() => setMaAdderType(t)}
                          className={`flex-1 px-2 py-1 rounded-md text-[11px] font-semibold transition-all ${maAdderType === t ? 'bg-background shadow-sm text-foreground ring-1 ring-border/50' : 'text-muted-foreground/60 hover:text-foreground'}`}
                        >{t}</button>
                      ))}
                    </div>
                    {/* Period checkboxes */}
                    <div className="grid grid-cols-3 gap-1.5">
                      {COMMON_PERIODS.map((p) => {
                        const checked = maAdderPeriods.has(p);
                        const alreadyExists = state.maConfigs.some(m => m.type === maAdderType && m.period === p);
                        return (
                          <button key={p} disabled={alreadyExists}
                            onClick={() => setMaAdderPeriods(prev => { const n = new Set(prev); if (n.has(p)) n.delete(p); else n.add(p); return n; })}
                            className={`px-2 py-1.5 rounded-md text-[11px] font-mono font-medium border transition-all ${alreadyExists ? 'opacity-30 cursor-not-allowed border-border/30 text-muted-foreground/40' : checked ? 'border-primary/50 bg-primary/10 text-primary' : 'border-border/40 text-muted-foreground/60 hover:border-border hover:text-foreground'}`}
                          >{p}</button>
                        );
                      })}
                    </div>
                    {/* Actions */}
                    <div className="flex gap-2">
                      <button
                        onClick={() => {
                          if (maAdderPeriods.size === 0) return;
                          const usedColors = new Set(state.maConfigs.map(m => m.color));
                          const newMAs: MaConfig[] = [];
                          for (const period of Array.from(maAdderPeriods).sort((a, b) => a - b)) {
                            if (state.maConfigs.some(m => m.type === maAdderType && m.period === period)) continue;
                            const color = MA_COLORS.find(c => !usedColors.has(c)) ?? MA_COLORS[newMAs.length % MA_COLORS.length];
                            usedColors.add(color);
                            newMAs.push({ type: maAdderType, period, color, enabled: true });
                          }
                          if (newMAs.length) setState(s => ({ ...s, maConfigs: [...s.maConfigs, ...newMAs] }));
                          setMaAdderPeriods(new Set());
                          setMaAdderOpen(false);
                        }}
                        disabled={maAdderPeriods.size === 0}
                        className="flex-1 py-1.5 rounded-md text-[11px] font-medium bg-primary/15 text-primary hover:bg-primary/25 disabled:opacity-30 transition-all"
                      >Add {maAdderPeriods.size > 0 ? `${maAdderPeriods.size} ${maAdderType}${maAdderPeriods.size > 1 ? 's' : ''}` : maAdderType}</button>
                      <button onClick={() => { setMaAdderOpen(false); setMaAdderPeriods(new Set()); }} className="px-3 py-1.5 rounded-md text-[11px] font-medium text-muted-foreground/60 hover:text-foreground hover:bg-primary/[0.06] transition-all">Cancel</button>
                    </div>
                  </div>
                ) : (
                  <button onClick={() => setMaAdderOpen(true)} className="flex items-center justify-center gap-1.5 w-full py-1.5 rounded-md text-[11px] font-medium border border-dashed border-border/50 text-muted-foreground/70 hover:text-foreground hover:bg-primary/[0.04] hover:border-border transition-all">
                    <Plus className="w-3 h-3" /> Add MA
                  </button>
                )}
              </div>
            </>
          ) : null}

          {/* Oscillators group */}
          {(match('MACD') || match('RSI') || match('Squeeze Momentum') || match('Stochastic') || match('ATR')) && (
            <>
              <SectionLabel>Oscillators</SectionLabel>
              {match('MACD') && (
                <IndicatorRow color="#38bdf8" label="MACD" sublabel={`${state.macdFast} ${state.macdSlow} ${state.macdSignal}`} checked={state.showMACD} onCheck={(v: boolean) => setState(s => ({ ...s, showMACD: v }))} onSettingsOpen={() => toggleSettings('macd')} settingsOpen={openSettings === 'macd'} settingsContent={<div className="space-y-4"><ParamRow label="Fast Length" value={state.macdFast} min={1} max={100} onChange={(v: number) => setState(s => ({ ...s, macdFast: v }))} /><ParamRow label="Slow Length" value={state.macdSlow} min={1} max={200} onChange={(v: number) => setState(s => ({ ...s, macdSlow: v }))} /><ParamRow label="Signal Smoothing" value={state.macdSignal} min={1} max={50} onChange={(v: number) => setState(s => ({ ...s, macdSignal: v }))} /></div>} />
              )}
              {match('RSI') && (
                <IndicatorRow color="#60a5fa" label="RSI" sublabel={`${state.rsiPeriod}`} checked={state.showRSI} onCheck={(v: boolean) => setState(s => ({ ...s, showRSI: v }))} onSettingsOpen={() => toggleSettings('rsi')} settingsOpen={openSettings === 'rsi'} settingsContent={<div className="space-y-4"><ParamRow label="RSI Length" value={state.rsiPeriod} min={2} max={100} onChange={(v: number) => setState(s => ({ ...s, rsiPeriod: v }))} /></div>} />
              )}
              {match('Stochastic') && (
                <IndicatorRow color="#2196f3" label="Stochastic" sublabel={state.showStoch ? `${state.stochK} ${state.stochD}` : undefined} checked={state.showStoch} onCheck={(v: boolean) => setState(s => ({ ...s, showStoch: v }))} onSettingsOpen={() => toggleSettings('stoch')} settingsOpen={openSettings === 'stoch'} settingsContent={<div className="space-y-4"><ParamRow label="%K Period" value={state.stochK} min={2} max={50} onChange={(v: number) => setState(s => ({ ...s, stochK: v }))} /><ParamRow label="%D Period" value={state.stochD} min={1} max={20} onChange={(v: number) => setState(s => ({ ...s, stochD: v }))} /><ParamRow label="Smoothing" value={state.stochSmooth} min={1} max={10} onChange={(v: number) => setState(s => ({ ...s, stochSmooth: v }))} /></div>} />
              )}
              {match('ATR') && (
                <IndicatorRow color="#ab47bc" label="ATR" sublabel={state.showATR ? `${state.atrPeriod}` : undefined} checked={state.showATR} onCheck={(v: boolean) => setState(s => ({ ...s, showATR: v }))} onSettingsOpen={() => toggleSettings('atr')} settingsOpen={openSettings === 'atr'} settingsContent={<div className="space-y-4"><ParamRow label="ATR Period" value={state.atrPeriod} min={2} max={50} onChange={(v: number) => setState(s => ({ ...s, atrPeriod: v }))} /></div>} />
              )}
              {match('Squeeze Momentum') && (
                <IndicatorRow color="#4ade80" label="Squeeze Momentum" sublabel={state.showSqz ? `${state.sqzBbLen} ${state.sqzKcLen}` : undefined} checked={state.showSqz} onCheck={(v: boolean) => setState(s => ({ ...s, showSqz: v }))} onSettingsOpen={() => toggleSettings('sqz')} settingsOpen={openSettings === 'sqz'} settingsContent={<div className="space-y-4"><ParamRow label="BB Length" value={state.sqzBbLen} min={5} max={50} onChange={(v: number) => setState(s => ({ ...s, sqzBbLen: v }))} /><ParamRow label="BB Mult" value={state.sqzBbMult} min={0.5} max={5} step={0.1} onChange={(v: number) => setState(s => ({ ...s, sqzBbMult: v }))} /><ParamRow label="KC Length" value={state.sqzKcLen} min={5} max={50} onChange={(v: number) => setState(s => ({ ...s, sqzKcLen: v }))} /><ParamRow label="KC Mult" value={state.sqzKcMult} min={0.5} max={5} step={0.1} onChange={(v: number) => setState(s => ({ ...s, sqzKcMult: v }))} /></div>} />
              )}
            </>
          )}
        </div>
      </div>
    );
  }, [sidebarSearch, state, openSettings, maAdderOpen, maAdderType, maAdderPeriods]);

  return (<>
    <AppShell hideFooter>
      <NavigatorShell
        sidebarOpen={sidebarOpen && !isFullscreen}
        onSidebarToggle={toggleSidebar}
        sidebarIcon={<BarChart2 className="w-4 h-4 text-primary" />}
        sidebarLabel="Indicators"
        sidebarContent={sidebarContent}
      >
        <div className={`h-full flex flex-col bg-background relative ${isFullscreen ? 'fixed inset-0 z-50' : ''}`}>

          {/* ── Top Bar ── */}
          <div className="h-12 px-4 border-b border-border/50 flex items-center justify-between shrink-0 bg-background/95 backdrop-blur-md z-10 shadow-sm">
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
                  className="w-28 pl-8 pr-3 py-1.5 bg-primary/[0.03] border border-border/50 rounded-lg text-[13px] font-bold tracking-wide focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 text-foreground transition-all uppercase placeholder:font-normal"
                />
              </div>

              <div className="w-px h-5 bg-border/50" />

              {/* Frequency Segmented Control */}
              <div className="flex p-0.5 bg-primary/[0.03] border border-border/40 rounded-lg">
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
                        : 'text-muted-foreground/70 hover:text-foreground hover:bg-primary/[0.04]'
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
                  <><Loader2 className="w-3.5 h-3.5 animate-spin text-primary" /><span className="text-[11px] font-medium text-primary">Updating</span></>
                ) : (
                  <><span className="relative flex h-2 w-2"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span><span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span></span><span className="text-[11px] font-medium text-muted-foreground">Live</span></>
                )}
              </div>

              <div className="w-px h-5 bg-border/50" />

              <button
                onClick={() => setShowAiSummary(!showAiSummary)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all ${showAiSummary ? 'bg-primary/10 text-primary ring-1 ring-primary/30' : 'bg-primary/[0.03] border border-border/40 text-muted-foreground hover:text-foreground hover:bg-primary/[0.06]'}`}
              >
                <BrainCircuit className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">AI Analysis</span>
              </button>

              <button
                onClick={() => setIsFullscreen(!isFullscreen)}
                className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-primary/10 rounded-lg transition-colors"
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
              <div className="absolute top-4 left-4 z-20 w-[400px] max-h-[85%] flex flex-col bg-background/95 border border-border/50 backdrop-blur-2xl rounded-md shadow-lg overflow-hidden animate-in fade-in slide-in-from-left-4 duration-300 ring-1 ring-foreground/5">
                <div className="px-5 py-3.5 border-b border-border/50 flex items-center justify-between bg-primary/[0.03]">
                  <div className="flex items-center gap-2.5 text-primary">
                    <div className={`p-1 rounded-lg ${isLight ? 'bg-primary/10' : 'bg-primary/10'}`}>
                      <BrainCircuit className="w-4 h-4" />
                    </div>
                    <span className="text-[13px] font-bold uppercase tracking-wider">Intelligence Report</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {summaryQuery.data?.summary && (
                      <div className="flex items-center gap-1 mr-2 border-r border-border/40 pr-2">
                        <button
                          onClick={() => handleExport('pdf')}
                          disabled={!!exportingFormat}
                          className="p-1.5 rounded-md transition-all text-muted-foreground hover:text-primary hover:bg-primary/[0.07]"
                          title="Export to PDF"
                        >
                          {exportingFormat === 'pdf' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}
                        </button>
                        <button
                          onClick={() => handleExport('pptx')}
                          disabled={!!exportingFormat}
                          className="p-1.5 rounded-md transition-all text-muted-foreground hover:text-amber-500 hover:bg-amber-500/[0.07]"
                          title="Export to PowerPoint"
                        >
                          {exportingFormat === 'pptx' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <PresentationIcon className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    )}
                    {summaryQuery.isFetching && !exportingFormat && <Loader2 className="w-3.5 h-3.5 animate-spin text-primary/40" />}
                    <button 
                      onClick={() => setShowAiSummary(false)} 
                      className="text-muted-foreground hover:text-foreground transition-colors p-1.5 hover:bg-primary/10 rounded-md"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <div className="p-4 overflow-y-auto custom-scrollbar">
                  {summaryQuery.data?.summary ? (
                    <div className="prose prose-sm max-w-none dark:prose-invert">
                      <ReactMarkdown
                        components={{
                          h1: ({node, ...props}) => <h1 className="text-primary font-bold text-[15px] mb-4 mt-2 border-b border-primary/20 pb-2" {...props} />,
                          h2: ({node, ...props}) => <h2 className="text-foreground font-bold text-[13px] mb-3 mt-6" {...props} />,
                          h3: ({node, ...props}) => <h3 className="text-foreground/90 font-bold text-[12px] mb-2 mt-4 underline decoration-primary/30 underline-offset-4" {...props} />,
                          p: ({node, ...props}) => <p className="mb-4 text-[12px] leading-[1.6] text-foreground/70" {...props} />,
                          ul: ({node, ...props}) => <ul className="mb-4 space-y-2 list-none pl-0" {...props} />,
                          li: ({node, ...props}) => (
                            <li className="flex gap-2 text-[12px] text-foreground/70 items-start">
                              <span className="text-primary mt-1.5 shrink-0">•</span>
                              <span>{props.children}</span>
                            </li>
                          ),
                          strong: ({node, ...props}) => <strong className="text-primary font-semibold" {...props} />,
                          blockquote: ({node, ...props}) => (
                            <blockquote className="my-4 p-3 rounded-lg border-l-2 border-primary/40 bg-primary/[0.05] italic text-foreground/80" {...props} />
                          ),
                        }}
                      >
                        {summaryQuery.data.summary}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-12 gap-4 text-muted-foreground">
                      <div className="relative">
                        <Activity className="w-8 h-8 animate-pulse text-primary/20" />
                        <Loader2 className="w-8 h-8 animate-spin text-primary absolute inset-0" />
                      </div>
                      <span className="text-[12px] font-medium animate-pulse">Generating Intelligence Report...</span>
                    </div>
                  )}
                </div>
                {summaryQuery.data?.summary && (
                  <div className="px-5 py-3 border-t border-border/40 text-center bg-primary/[0.02]">
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
                <ChartErrorBoundary>
                  <Plot
                    data={cleanedFigure.data}
                    layout={{ ...cleanedFigure.layout, autosize: true }}
                    config={{
                      responsive: true, displaylogo: false, displayModeBar: 'hover',
                      scrollZoom: true,
                      modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d', 'toggleSpikelines'],
                    }}
                    style={{ width: '100%', height: '100%' }}
                    useResizeHandler
                    onInitialized={(_f: any, gd: any) => { plotGraphDivRef.current = gd; }}
                    onRelayout={handleRelayout}
                  />
                </ChartErrorBoundary>
              )}
            </div>
          </div>
        </div>
      </NavigatorShell>
    </AppShell>
    {toastError && <Toast message={toastError} onDismiss={() => setToastError(null)} />}
  </>);
}

function Toast({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  useEffect(() => { const t = setTimeout(onDismiss, 4000); return () => clearTimeout(t); }, [onDismiss]);
  return (
    <div className="fixed bottom-4 right-4 z-[200] bg-rose-500/90 text-white px-4 py-2.5 rounded-lg shadow-lg text-sm font-medium flex items-center gap-2 animate-in slide-in-from-bottom-2 fade-in duration-200">
      {message}
      <button onClick={onDismiss} className="ml-1 opacity-70 hover:opacity-100">&times;</button>
    </div>
  );
}
