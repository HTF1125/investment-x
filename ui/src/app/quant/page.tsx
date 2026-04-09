'use client';

import dynamic from 'next/dynamic';
import { useCallback, useMemo, useRef, useState, useEffect } from 'react';
import AppShell from '@/components/layout/AppShell';
import NavigatorShell from '@/components/layout/NavigatorShell';
import { AlertTriangle, BarChart3, Loader2, TrendingUp, GitBranch, Shield, Sigma } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { useTheme } from '@/context/ThemeContext';
import { applyChartTheme } from '@/lib/chartTheme';
import { useDebounce } from '@/hooks/useDebounce';
import { useResponsiveSidebar } from '@/hooks/useResponsiveSidebar';
import { ChartErrorBoundary } from '@/components/shared/ChartErrorBoundary';

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-3">
        <Loader2 className="w-6 h-6 animate-spin text-primary/40" />
        <span className="text-[12.5px] text-muted-foreground/50 tracking-widest uppercase">Loading Chart</span>
      </div>
    </div>
  ),
}) as any;

// ─── Types & Constants ────────────────────────────────────────────────────────

type Tab = 'correlation' | 'regression' | 'pca' | 'var';

const TABS: { key: Tab; label: string; icon: React.ReactNode; title?: string }[] = [
  { key: 'correlation', label: 'Correlation', icon: <GitBranch className="w-3.5 h-3.5" /> },
  { key: 'regression', label: 'Regression', icon: <TrendingUp className="w-3.5 h-3.5" /> },
  { key: 'pca', label: 'PCA', icon: <Sigma className="w-3.5 h-3.5" />, title: 'Principal Component Analysis' },
  { key: 'var', label: 'VaR', icon: <Shield className="w-3.5 h-3.5" />, title: 'Value at Risk — maximum expected loss at a given confidence level' },
];

const DEFAULT_CODES = 'SPY,TLT,GLD,EEM,DXY Index';

// ─── Reusable Controls ────────────────────────────────────────────────────────

function ControlInput({ label, value, onChange, placeholder, type = 'text', min, max, step }: {
  label: string; value: string | number; onChange: (v: string) => void;
  placeholder?: string; type?: string; min?: number; max?: number; step?: number;
}) {
  const { theme } = useTheme();
  return (
    <div className="space-y-1">
      <label className="stat-label block">{label}</label>
      <input
        type={type} value={value} placeholder={placeholder}
        min={min} max={max} step={step}
        onChange={(e) => onChange(e.target.value)}
        className="w-full border border-border/50 rounded-[var(--radius)] px-2.5 h-7 text-[13px] focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/20 text-foreground transition-all placeholder:text-muted-foreground/35"
        style={{ colorScheme: theme === 'light' ? 'light' : 'dark', backgroundColor: 'rgb(var(--background))', color: 'rgb(var(--foreground))' }}
      />
    </div>
  );
}

function ControlSelect({ label, value, onChange, options }: {
  label: string; value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  const { theme } = useTheme();
  return (
    <div className="space-y-1">
      <label className="stat-label block">{label}</label>
      <select
        value={value} onChange={(e) => onChange(e.target.value)}
        className="w-full border border-border/50 rounded-[var(--radius)] px-2.5 h-7 text-[13px] focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/20 text-foreground cursor-pointer transition-all"
        style={{ colorScheme: theme === 'light' ? 'light' : 'dark', backgroundColor: 'rgb(var(--background))', color: 'rgb(var(--foreground))' }}
      >
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="pt-4 pb-1.5 flex items-center gap-2">
      <span className="stat-label">{children}</span>
      <div className="h-px flex-1 bg-border/30" />
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function QuantPage() {
  useEffect(() => { document.title = 'Quantitative Analysis | Investment-X'; }, []);
  const { theme } = useTheme();
  const isLight = theme === 'light';

  // ── Tab State ──
  const [activeTab, setActiveTab] = useState<Tab>('correlation');
  const { sidebarOpen, toggleSidebar } = useResponsiveSidebar();

  // ── Correlation State ──
  const [corrCodes, setCorrCodes] = useState(DEFAULT_CODES);
  const [corrWindow, setCorrWindow] = useState('');
  const [corrMethod, setCorrMethod] = useState('pearson');
  const [corrMode, setCorrMode] = useState<'matrix' | 'rolling'>('matrix');
  const [corrCode1, setCorrCode1] = useState('SPY');
  const [corrCode2, setCorrCode2] = useState('TLT');
  const [corrRollingWindow, setCorrRollingWindow] = useState('60');

  // ── Regression State ──
  const [regY, setRegY] = useState('SPY');
  const [regX, setRegX] = useState('TLT,GLD');
  const [regMode, setRegMode] = useState<'ols' | 'rolling-beta'>('ols');
  const [regBetaX, setRegBetaX] = useState('TLT');
  const [regBetaWindow, setRegBetaWindow] = useState('60');

  // ── PCA State ──
  const [pcaCodes, setPcaCodes] = useState(DEFAULT_CODES);
  const [pcaComponents, setPcaComponents] = useState('3');

  // ── VaR State ──
  const [varCode, setVarCode] = useState('SPY');
  const [varConfidence, setVarConfidence] = useState('0.95');
  const [varWindow, setVarWindow] = useState('252');
  const [varMethod, setVarMethod] = useState('historical');
  const [varMode, setVarMode] = useState<'snapshot' | 'rolling'>('snapshot');

  // Debounce all state
  const dCorrCodes = useDebounce(corrCodes, 500);
  const dCorrWindow = useDebounce(corrWindow, 500);
  const dCorrCode1 = useDebounce(corrCode1, 500);
  const dCorrCode2 = useDebounce(corrCode2, 500);
  const dCorrRollingWindow = useDebounce(corrRollingWindow, 500);
  const dRegY = useDebounce(regY, 500);
  const dRegX = useDebounce(regX, 500);
  const dRegBetaX = useDebounce(regBetaX, 500);
  const dRegBetaWindow = useDebounce(regBetaWindow, 500);
  const dPcaCodes = useDebounce(pcaCodes, 500);
  const dPcaComponents = useDebounce(pcaComponents, 500);
  const dVarCode = useDebounce(varCode, 500);
  const dVarConfidence = useDebounce(varConfidence, 500);
  const dVarWindow = useDebounce(varWindow, 500);

  // ── Queries ──

  // Correlation matrix
  const corrMatrixQuery = useQuery({
    queryKey: ['quant-corr-matrix', dCorrCodes, dCorrWindow, corrMethod],
    queryFn: () => {
      const params = new URLSearchParams({ codes: dCorrCodes, method: corrMethod });
      if (dCorrWindow) params.set('window', dCorrWindow);
      return apiFetchJson(`/api/quant/correlation/matrix?${params}`);
    },
    enabled: activeTab === 'correlation' && corrMode === 'matrix' && dCorrCodes.split(',').filter(s => s.trim()).length >= 2,
    staleTime: 60_000,
  });

  // Rolling correlation
  const corrRollingQuery = useQuery({
    queryKey: ['quant-corr-rolling', dCorrCode1, dCorrCode2, dCorrRollingWindow],
    queryFn: () => apiFetchJson(
      `/api/quant/correlation/rolling?code1=${encodeURIComponent(dCorrCode1)}&code2=${encodeURIComponent(dCorrCode2)}&window=${dCorrRollingWindow}`
    ),
    enabled: activeTab === 'correlation' && corrMode === 'rolling' && !!dCorrCode1 && !!dCorrCode2,
    staleTime: 60_000,
  });

  // OLS Regression
  const regOlsQuery = useQuery({
    queryKey: ['quant-reg-ols', dRegY, dRegX],
    queryFn: () => apiFetchJson(
      `/api/quant/regression/ols?y=${encodeURIComponent(dRegY)}&x=${encodeURIComponent(dRegX)}`
    ),
    enabled: activeTab === 'regression' && regMode === 'ols' && !!dRegY && !!dRegX,
    staleTime: 60_000,
  });

  // Rolling Beta
  const regBetaQuery = useQuery({
    queryKey: ['quant-reg-beta', dRegY, dRegBetaX, dRegBetaWindow],
    queryFn: () => apiFetchJson(
      `/api/quant/regression/rolling-beta?y=${encodeURIComponent(dRegY)}&x=${encodeURIComponent(dRegBetaX)}&window=${dRegBetaWindow}`
    ),
    enabled: activeTab === 'regression' && regMode === 'rolling-beta' && !!dRegY && !!dRegBetaX,
    staleTime: 60_000,
  });

  // PCA
  const pcaQuery = useQuery({
    queryKey: ['quant-pca', dPcaCodes, dPcaComponents],
    queryFn: () => apiFetchJson(
      `/api/quant/pca?codes=${encodeURIComponent(dPcaCodes)}&n_components=${dPcaComponents}`
    ),
    enabled: activeTab === 'pca' && dPcaCodes.split(',').filter(s => s.trim()).length >= 2,
    staleTime: 60_000,
  });

  // VaR snapshot
  const varSnapshotQuery = useQuery({
    queryKey: ['quant-var', dVarCode, dVarConfidence, dVarWindow, varMethod],
    queryFn: () => {
      const params = new URLSearchParams({ code: dVarCode, confidence: dVarConfidence, method: varMethod });
      if (dVarWindow) params.set('window', dVarWindow);
      return apiFetchJson(`/api/quant/var?${params}`);
    },
    enabled: activeTab === 'var' && varMode === 'snapshot' && !!dVarCode,
    staleTime: 60_000,
  });

  // VaR rolling
  const varRollingQuery = useQuery({
    queryKey: ['quant-var-rolling', dVarCode, dVarConfidence, dVarWindow],
    queryFn: () => apiFetchJson(
      `/api/quant/var/rolling?code=${encodeURIComponent(dVarCode)}&confidence=${dVarConfidence}&window=${dVarWindow}`
    ),
    enabled: activeTab === 'var' && varMode === 'rolling' && !!dVarCode,
    staleTime: 60_000,
  });

  // ── Active figure ──
  const { figData, isLoading, isFetching, isError } = useMemo(() => {
    if (activeTab === 'correlation') {
      const q = corrMode === 'matrix' ? corrMatrixQuery : corrRollingQuery;
      return { figData: q.data, isLoading: q.isLoading, isFetching: q.isFetching, isError: q.isError };
    }
    if (activeTab === 'regression') {
      const q = regMode === 'ols' ? regOlsQuery : regBetaQuery;
      return { figData: q.data, isLoading: q.isLoading, isFetching: q.isFetching, isError: q.isError };
    }
    if (activeTab === 'pca') {
      return { figData: pcaQuery.data, isLoading: pcaQuery.isLoading, isFetching: pcaQuery.isFetching, isError: pcaQuery.isError };
    }
    // var
    const q = varMode === 'snapshot' ? varSnapshotQuery : varRollingQuery;
    return { figData: q.data, isLoading: q.isLoading, isFetching: q.isFetching, isError: q.isError };
  }, [activeTab, corrMode, regMode, varMode, corrMatrixQuery, corrRollingQuery, regOlsQuery, regBetaQuery, pcaQuery, varSnapshotQuery, varRollingQuery]);

  // ── Theme the figure ──
  const themedFig = useMemo(() => {
    if (!figData) return null;
    return applyChartTheme(figData, isLight ? 'light' : 'dark', { transparentBackground: true });
  }, [figData, isLight]);

  // ── Plot resize ──
  const plotContainerRef = useRef<HTMLDivElement>(null);
  const plotGraphDivRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const el = plotContainerRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(() => {
      const gd = plotGraphDivRef.current;
      if (!gd || !gd.isConnected) return;
      import('plotly.js-dist-min').then(({ default: Plotly }) => {
        (Plotly as any).Plots.resize(gd);
      }).catch((err) => console.warn('[Chart] resize failed:', err));
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // ─── Sidebar content per tab ──────────────────────────────────────────────

  const sidebarContent = useMemo(() => {
    return (
      <div className="flex flex-col h-full overflow-y-auto px-3 pb-6">
        {/* Tab selector */}
        <SectionLabel>Analysis Type</SectionLabel>
        <div className="grid grid-cols-2 gap-1">
          {TABS.map(t => (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key)}
              title={t.title}
              className={`flex items-center gap-1.5 px-2 py-1.5 rounded-[var(--radius)] text-[12.5px] font-semibold transition-all ${
                activeTab === t.key
                  ? 'bg-foreground text-background'
                  : 'text-muted-foreground/60 hover:text-foreground hover:bg-foreground/[0.06] border border-border/30'
              }`}
            >
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>

        {/* Tab-specific controls */}
        {activeTab === 'correlation' && (
          <>
            <SectionLabel>Mode</SectionLabel>
            <div className="flex p-0.5 bg-background border border-border/40 rounded-[var(--radius)]">
              {(['matrix', 'rolling'] as const).map(m => (
                <button
                  key={m}
                  onClick={() => setCorrMode(m)}
                  className={`flex-1 h-6 rounded text-[11.5px] font-bold tracking-wider transition-all ${
                    corrMode === m
                      ? 'bg-foreground text-background shadow-sm'
                      : 'text-muted-foreground/60 hover:text-foreground'
                  }`}
                >
                  {m === 'matrix' ? 'Matrix' : 'Rolling'}
                </button>
              ))}
            </div>

            {corrMode === 'matrix' ? (
              <>
                <SectionLabel>Parameters</SectionLabel>
                <div className="space-y-3">
                  <ControlInput label="Series Codes (comma-separated)" value={corrCodes} onChange={setCorrCodes} placeholder="SPY,TLT,GLD" />
                  <ControlInput label="Trailing Window (blank = full sample)" value={corrWindow} onChange={setCorrWindow} type="number" min={20} placeholder="e.g. 120" />
                  <ControlSelect label="Method" value={corrMethod} onChange={setCorrMethod} options={[
                    { value: 'pearson', label: 'Pearson' },
                    { value: 'spearman', label: 'Spearman' },
                    { value: 'kendall', label: 'Kendall' },
                  ]} />
                </div>
              </>
            ) : (
              <>
                <SectionLabel>Parameters</SectionLabel>
                <div className="space-y-3">
                  <ControlInput label="Series 1" value={corrCode1} onChange={setCorrCode1} placeholder="SPY" />
                  <ControlInput label="Series 2" value={corrCode2} onChange={setCorrCode2} placeholder="TLT" />
                  <ControlInput label="Window" value={corrRollingWindow} onChange={setCorrRollingWindow} type="number" min={10} />
                </div>
              </>
            )}
          </>
        )}

        {activeTab === 'regression' && (
          <>
            <SectionLabel>Mode</SectionLabel>
            <div className="flex p-0.5 bg-background border border-border/40 rounded-[var(--radius)]">
              {(['ols', 'rolling-beta'] as const).map(m => (
                <button
                  key={m}
                  onClick={() => setRegMode(m)}
                  className={`flex-1 h-6 rounded text-[11.5px] font-bold tracking-wider transition-all ${
                    regMode === m
                      ? 'bg-foreground text-background shadow-sm'
                      : 'text-muted-foreground/60 hover:text-foreground'
                  }`}
                >
                  {m === 'ols' ? 'OLS' : 'Rolling β'}
                </button>
              ))}
            </div>

            <SectionLabel>Parameters</SectionLabel>
            <div className="space-y-3">
              <ControlInput label="Dependent (Y)" value={regY} onChange={setRegY} placeholder="SPY" />
              {regMode === 'ols' ? (
                <ControlInput label="Factors (X, comma-separated)" value={regX} onChange={setRegX} placeholder="TLT,GLD" />
              ) : (
                <>
                  <ControlInput label="Independent (X)" value={regBetaX} onChange={setRegBetaX} placeholder="TLT" />
                  <ControlInput label="Window" value={regBetaWindow} onChange={setRegBetaWindow} type="number" min={10} />
                </>
              )}
            </div>
          </>
        )}

        {activeTab === 'pca' && (
          <>
            <SectionLabel>Parameters</SectionLabel>
            <div className="space-y-3">
              <ControlInput label="Series Codes (comma-separated)" value={pcaCodes} onChange={setPcaCodes} placeholder="SPY,TLT,GLD,EEM" />
              <ControlInput label="Components" value={pcaComponents} onChange={setPcaComponents} type="number" min={1} max={10} />
            </div>
          </>
        )}

        {activeTab === 'var' && (
          <>
            <SectionLabel>Mode</SectionLabel>
            <div className="flex p-0.5 bg-background border border-border/40 rounded-[var(--radius)]">
              {(['snapshot', 'rolling'] as const).map(m => (
                <button
                  key={m}
                  onClick={() => setVarMode(m)}
                  className={`flex-1 h-6 rounded text-[11.5px] font-bold tracking-wider transition-all ${
                    varMode === m
                      ? 'bg-foreground text-background shadow-sm'
                      : 'text-muted-foreground/60 hover:text-foreground'
                  }`}
                >
                  {m === 'snapshot' ? 'Snapshot' : 'Rolling'}
                </button>
              ))}
            </div>

            <SectionLabel>Parameters</SectionLabel>
            <div className="space-y-3">
              <ControlInput label="Series Code" value={varCode} onChange={setVarCode} placeholder="SPY" />
              <ControlInput label="Confidence" value={varConfidence} onChange={setVarConfidence} type="number" min={0.9} max={0.999} step={0.01} />
              <ControlInput label="Window (days)" value={varWindow} onChange={setVarWindow} type="number" min={20} />
              {varMode === 'snapshot' && (
                <ControlSelect label="Method" value={varMethod} onChange={setVarMethod} options={[
                  { value: 'historical', label: 'Historical' },
                  { value: 'parametric', label: 'Parametric' },
                ]} />
              )}
            </div>
          </>
        )}
      </div>
    );
  }, [activeTab, corrMode, corrCodes, corrWindow, corrMethod, corrCode1, corrCode2, corrRollingWindow, regMode, regY, regX, regBetaX, regBetaWindow, pcaCodes, pcaComponents, varMode, varCode, varConfidence, varWindow, varMethod]);

  // ─── Render ───────────────────────────────────────────────────────────────

  const activeLabel = TABS.find(t => t.key === activeTab)?.label ?? 'Quant';

  return (
    <AppShell>
      <NavigatorShell
        sidebarOpen={sidebarOpen}
        onSidebarToggle={toggleSidebar}
        sidebarIcon={<BarChart3 className="w-4 h-4" />}
        sidebarLabel="Quant Analytics"
        sidebarContent={sidebarContent}
        sidebarOpenWidthClassName="w-[220px]"
        topBarLeft={
          <div className="flex items-center gap-2.5">
            <span className="text-[12.5px] font-bold uppercase tracking-[0.08em] text-foreground/80">{activeLabel}</span>
            {isFetching && (
              <div className="flex items-center gap-1.5">
                <Loader2 className="w-3 h-3 animate-spin text-primary" />
                <span className="text-[11.5px] font-mono text-primary/70 tracking-wider">Loading...</span>
              </div>
            )}
          </div>
        }
      >
        <div ref={plotContainerRef} className="h-full w-full">
          {isLoading ? (
            <div className="h-full flex items-center justify-center">
              <div className="flex flex-col items-center gap-2.5">
                <Loader2 className="w-5 h-5 animate-spin text-primary/50" />
                <span className="stat-label">Running analysis...</span>
              </div>
            </div>
          ) : isError ? (
            <div className="h-full flex items-center justify-center">
              <div className="flex flex-col items-center gap-3 text-center max-w-xs animate-fade-in">
                <div className="w-10 h-10 rounded-[var(--radius)] bg-destructive/10 border border-destructive/20 flex items-center justify-center">
                  <AlertTriangle className="w-4.5 h-4.5 text-destructive" />
                </div>
                <p className="text-[13px] font-medium text-foreground">Failed to load {activeLabel.toLowerCase()} analysis</p>
                <p className="text-[12px] text-muted-foreground">Check that the series codes are valid and try again</p>
              </div>
            </div>
          ) : themedFig ? (
            <ChartErrorBoundary>
              <Plot
                data={themedFig.data}
                layout={{ ...themedFig.layout, autosize: true }}
                config={{ responsive: true, displaylogo: false, modeBarButtonsToRemove: ['lasso2d', 'select2d'] }}
                useResizeHandler
                style={{ width: '100%', height: '100%' }}
                onInitialized={(_: any, gd: HTMLElement) => { plotGraphDivRef.current = gd; }}
                onUpdate={(_: any, gd: HTMLElement) => { plotGraphDivRef.current = gd; }}
              />
            </ChartErrorBoundary>
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="text-center space-y-3">
                <div className="w-10 h-10 rounded-[var(--radius)] bg-foreground/[0.04] flex items-center justify-center mx-auto border border-border/30">
                  <BarChart3 className="w-5 h-5 text-muted-foreground/30" />
                </div>
                <div className="space-y-1">
                  <p className="text-[13px] font-medium text-foreground/50">No analysis selected</p>
                  <p className="stat-label">Configure parameters in the sidebar</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </NavigatorShell>
    </AppShell>
  );
}
