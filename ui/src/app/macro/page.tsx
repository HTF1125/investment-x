'use client';

import { useEffect, useMemo, useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { AlertTriangle, Info, Sparkles } from 'lucide-react';
import {
  AxisDock,
  CurrentStateTab,
  HistoryTab,
  AssetPerformanceTab,
  StrategyTab,
  EnsembleView,
  ModelTab,
  LoadingSpinner,
  COMPOSITION_PRESETS,
} from '@/components/regimes';
import type {
  RegimeModel,
  ModelsResponse,
  CurrentStateResponse,
  TimeseriesResponse,
  AssetAnalyticsResponse,
  StrategyResponse,
  EnsembleResponse,
  MetaResponse,
  ComposeResponse,
} from '@/components/regimes/types';

export default function MacroRegimePage() {
  useEffect(() => {
    document.title = 'Macro Regime | Investment-X';
  }, []);

  // ── No default selection ── user picks from the AxisDock.
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(
    () => new Set(),
  );

  // ── Models list ──
  const modelsQuery = useQuery({
    queryKey: ['regime-models'],
    queryFn: () => apiFetchJson<ModelsResponse>('/api/regimes/models'),
    staleTime: 600_000,
  });

  const allModels = modelsQuery.data?.models ?? [];

  // Only 1D (single-metric) regimes are selectable.
  const selectableModels = allModels.filter(
    (m) => m.category === 'axis' || m.category === 'phase',
  );

  // ── Mode resolution ──
  const selectedKeyList = useMemo(
    () => Array.from(selectedKeys).sort(),
    [selectedKeys],
  );
  const composeQueryKey = selectedKeyList.join(',');

  const mode: 'empty' | 'single' | 'composite' =
    selectedKeys.size === 0
      ? 'empty'
      : selectedKeys.size === 1
      ? 'single'
      : 'composite';

  const singleKey = mode === 'single' ? selectedKeyList[0] : '';

  // ── Compose query (composite mode only) ──
  const composeQuery = useQuery({
    queryKey: ['regime-compose', composeQueryKey],
    queryFn: () =>
      apiFetchJson<ComposeResponse>(
        `/api/regimes/compose?keys=${encodeURIComponent(composeQueryKey)}`,
      ),
    enabled: mode === 'composite',
    staleTime: 600_000,
  });

  // ── Single-mode queries (all sections render at once, no tab gating) ──
  const currentQuery = useQuery({
    queryKey: ['regime-current', singleKey],
    queryFn: () =>
      apiFetchJson<CurrentStateResponse>(`/api/regimes/${singleKey}/current`),
    enabled: mode === 'single',
    staleTime: 120_000,
  });

  const tsQuery = useQuery({
    queryKey: ['regime-timeseries', singleKey],
    queryFn: () =>
      apiFetchJson<TimeseriesResponse>(`/api/regimes/${singleKey}/timeseries`),
    enabled: mode === 'single',
    staleTime: 120_000,
  });

  const assetsQuery = useQuery({
    queryKey: ['regime-assets', singleKey],
    queryFn: () =>
      apiFetchJson<AssetAnalyticsResponse>(`/api/regimes/${singleKey}/assets`),
    enabled: mode === 'single',
    staleTime: 120_000,
  });

  const strategyQuery = useQuery({
    queryKey: ['regime-strategy', singleKey],
    queryFn: () =>
      apiFetchJson<StrategyResponse>(`/api/regimes/${singleKey}/strategy`),
    enabled: mode === 'single',
    staleTime: 120_000,
    retry: false,
  });

  const [ensembleUniverse, setEnsembleUniverse] = useState<'broad' | 'equity'>('broad');

  const ensembleQuery = useQuery({
    queryKey: ['regime-ensemble', ensembleUniverse],
    queryFn: () =>
      apiFetchJson<EnsembleResponse>(`/api/regimes/ensemble?universe=${ensembleUniverse}`),
    enabled: mode === 'empty',
    staleTime: 600_000,
    retry: false,
  });

  // Methodology popover toggle (must be declared before metaQuery so it
  // can be used in the `enabled` predicate without TDZ issues — React
  // hook order is preserved because both calls are unconditional).
  const [methodologyOpen, setMethodologyOpen] = useState(false);

  const metaQuery = useQuery({
    queryKey: ['regime-meta', singleKey],
    queryFn: () => apiFetchJson<MetaResponse>(`/api/regimes/${singleKey}/meta`),
    enabled: mode === 'single' && methodologyOpen,
    staleTime: 600_000,
  });

  // Primary query for top-level loading/error state. In single mode, the
  // current-state endpoint is the cheapest and arrives first.
  const activeQuery =
    mode === 'composite' ? composeQuery : currentQuery;

  // Methodology query — always uses the active mode's metadata
  const methodologyMeta =
    mode === 'composite'
      ? composeQuery.data?.meta
      : metaQuery.data?.meta;

  // ── Effective model ──
  const singleModel = mode === 'single'
    ? allModels.find((m) => m.key === singleKey)
    : undefined;
  const composedModel = mode === 'composite' ? composeQuery.data?.model : undefined;
  const effectiveModel = mode === 'composite' ? composedModel : singleModel;

  // Per-axis input models for the composite Robustness strip — preserves
  // the full quality snapshot (tier, overlaps, t14 flag) that the
  // synthesized composedModel does not carry.
  const inputModels: RegimeModel[] = useMemo(() => {
    if (mode !== 'composite') return [];
    return selectedKeyList
      .map((k) => allModels.find((m) => m.key === k))
      .filter((m): m is RegimeModel => Boolean(m));
  }, [mode, selectedKeyList, allModels]);

  // ── Hero state extraction (works for both modes) — used for the
  // "as of" timestamp in the header. Regime colors are applied inside
  // sub-components, not in the shell. ──
  const heroState =
    mode === 'composite'
      ? composeQuery.data?.current_state
      : currentQuery.data?.current_state;

  // ── Selection handler ──
  const toggleKey = (key: string) => {
    setSelectedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  // Selectable regime keys for preset filtering
  const selectableKeySet = useMemo(
    () => new Set(selectableModels.map((m) => m.key)),
    [selectableModels],
  );

  return (
    <AppShell hideFooter>
      <div className="page-shell">
        {/* ── Header strip: dense terminal toolbar ── */}
        <div className="shrink-0 border-b border-border/40 bg-[rgb(var(--surface))]/30">
          {/* Row 1: title | model | presets | meta — single dense line on md+ */}
          <div className="page-header">
            <h1 className="page-header-title">MACRO REGIME</h1>
            <div className="h-4 w-px bg-border/60" aria-hidden />
            {effectiveModel && (
              <span
                className="text-[11px] font-semibold text-foreground whitespace-nowrap truncate min-w-0 max-w-[40%] sm:max-w-none"
                title={effectiveModel.display_name}
              >
                {effectiveModel.display_name}
              </span>
            )}
            {effectiveModel && (
              <button
                type="button"
                onClick={() => setMethodologyOpen((v) => !v)}
                className="shrink-0 inline-flex items-center justify-center w-5 h-5 text-muted-foreground hover:text-foreground transition-colors"
                title="Methodology"
                aria-label="Open methodology"
              >
                <Info className="w-3 h-3" />
              </button>
            )}

            {/* Presets — inline on md+, inherit scroll on mobile */}
            {selectableModels.length > 0 && (() => {
              const validPresets = COMPOSITION_PRESETS.filter((p) =>
                p.keys.every((k) => selectableKeySet.has(k)),
              );
              if (validPresets.length === 0) return null;
              return (
                <div className="hidden md:flex items-center gap-0 ml-2 overflow-x-auto no-scrollbar">
                  <span className="stat-label mr-2">Preset</span>
                  {validPresets.map((preset, idx) => {
                    const presetKey = preset.keys.slice().sort().join(',');
                    const isActive = presetKey === composeQueryKey;
                    return (
                      <button
                        key={preset.label}
                        type="button"
                        onClick={() => setSelectedKeys(new Set(preset.keys))}
                        title={preset.description}
                        className={`relative shrink-0 h-6 px-2 text-[9.5px] font-mono uppercase tracking-[0.06em] transition-colors whitespace-nowrap ${
                          isActive
                            ? 'text-foreground'
                            : 'text-muted-foreground hover:text-foreground'
                        } ${idx > 0 ? 'border-l border-border/40' : ''}`}
                      >
                        {preset.label}
                        {isActive && (
                          <span
                            className="absolute left-2 right-2 bottom-0 h-[2px] bg-accent"
                            aria-hidden
                          />
                        )}
                      </button>
                    );
                  })}
                </div>
              );
            })()}

            {/* Right meta cluster */}
            <div className="ml-auto flex items-center gap-3 shrink-0">
              {mode === 'composite' && (
                <div className="flex items-center gap-1 text-[9.5px] font-mono uppercase tracking-[0.08em] text-muted-foreground whitespace-nowrap">
                  <Sparkles className="w-2.5 h-2.5 text-accent" />
                  {selectedKeyList.length}-AXIS
                </div>
              )}
              {heroState?.date && (
                <div className="hidden sm:flex items-baseline gap-1.5">
                  <span className="stat-label">AS OF</span>
                  <span className="text-[10.5px] font-mono tabular-nums text-foreground">
                    {heroState.date}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Mobile preset row — only shown below md */}
          {selectableModels.length > 0 && (() => {
            const validPresets = COMPOSITION_PRESETS.filter((p) =>
              p.keys.every((k) => selectableKeySet.has(k)),
            );
            if (validPresets.length === 0) return null;
            return (
              <div className="md:hidden flex items-center gap-0 overflow-x-auto no-scrollbar border-t border-border/30 px-3">
                {validPresets.map((preset, idx) => {
                  const presetKey = preset.keys.slice().sort().join(',');
                  const isActive = presetKey === composeQueryKey;
                  return (
                    <button
                      key={preset.label}
                      type="button"
                      onClick={() => setSelectedKeys(new Set(preset.keys))}
                      className={`relative shrink-0 h-7 px-2 text-[9.5px] font-mono uppercase tracking-[0.06em] whitespace-nowrap ${
                        isActive ? 'text-foreground' : 'text-muted-foreground'
                      } ${idx > 0 ? 'border-l border-border/40' : ''}`}
                    >
                      {preset.label}
                      {isActive && (
                        <span className="absolute left-2 right-2 bottom-0 h-[2px] bg-accent" aria-hidden />
                      )}
                    </button>
                  );
                })}
              </div>
            );
          })()}

        </div>

        {/* ── Main split: AxisDock sidebar (left) + content column (right) ── */}
        <div className="flex-1 min-h-0 flex flex-col md:flex-row">
          {/* Left sidebar — AxisDock */}
          {selectableModels.length > 0 && (
            <aside className="md:w-[260px] lg:w-[280px] md:shrink-0 md:h-full md:min-h-0 md:border-r md:border-border/40 border-b border-border/40 md:border-b-0 bg-[rgb(var(--surface))]/40">
              <AxisDock
                models={selectableModels}
                selectedKeys={selectedKeys}
                onToggle={toggleKey}
                overrides={
                  mode === 'composite'
                    ? composeQuery.data?.current_state?.input_states
                    : undefined
                }
              />
            </aside>
          )}

          {/* Right main column — all sections stacked (no tabs) */}
          <div className="flex-1 min-h-0 flex flex-col">
        <div className="md:flex-1 md:min-h-0 md:overflow-y-auto">
          <div className="max-w-[1600px] mx-auto px-3 sm:px-5 lg:px-6 py-3 sm:py-4">
            {mode === 'empty' ? (
              ensembleQuery.isLoading ? (
                <div className="h-full flex items-center justify-center py-20">
                  <LoadingSpinner label="Computing IC-weighted ensemble" />
                </div>
              ) : ensembleQuery.data ? (
                <EnsembleView
                  data={ensembleQuery.data}
                  universe={ensembleUniverse}
                  onUniverseChange={setEnsembleUniverse}
                />
              ) : (
                <div className="h-full flex items-center justify-center py-20">
                  <div className="flex flex-col items-center gap-3 text-center max-w-md">
                    <Sparkles className="w-6 h-6 text-muted-foreground/40" />
                    <p className="text-[13px] font-medium text-foreground">
                      Pick one or more regimes
                    </p>
                    <p className="text-[12px] text-muted-foreground">
                      Click any tile in the dock to view that single 1D regime,
                      or pick 2+ to compose them on the fly.
                    </p>
                  </div>
                </div>
              )
            ) : activeQuery.isError ? (
              <div className="h-full flex items-center justify-center py-20">
                <div className="flex flex-col items-center gap-3 text-center max-w-xs">
                  <div className="w-10 h-10 rounded-[var(--radius)] bg-destructive/10 border border-destructive/20 flex items-center justify-center">
                    <AlertTriangle className="w-4.5 h-4.5 text-destructive" />
                  </div>
                  <p className="text-[13px] font-medium text-foreground">
                    {mode === 'composite' ? 'Composition failed' : 'Failed to load regime data'}
                  </p>
                  <p className="text-[12px] text-muted-foreground">
                    {(activeQuery.error as Error)?.message ??
                      'Check your connection or trigger a refresh.'}
                  </p>
                </div>
              </div>
            ) : activeQuery.isLoading ? (
              <LoadingSpinner
                label={
                  mode === 'composite'
                    ? `Composing ${selectedKeyList.join(' × ')}`
                    : 'Loading regime'
                }
              />
            ) : mode === 'composite' && composeQuery.data ? (
              <div className="flex flex-col gap-6">
                <CurrentStateTab
                  state={composeQuery.data.current_state}
                  model={composedModel}
                  expectedReturns={
                    composeQuery.data.asset_analytics?.expected_returns
                  }
                  inputModels={inputModels}
                />
                <HistoryTab
                  ts={composeQuery.data.timeseries}
                  model={composedModel}
                />
                {composeQuery.data.asset_analytics && (
                  <AssetPerformanceTab
                    analytics={composeQuery.data.asset_analytics}
                    model={composedModel}
                  />
                )}
                {composeQuery.data.strategy && (
                  <StrategyTab
                    strategy={composeQuery.data.strategy}
                    model={composedModel}
                  />
                )}
              </div>
            ) : (
              <div className="flex flex-col gap-6">
                {currentQuery.data && (
                  <CurrentStateTab
                    state={currentQuery.data.current_state}
                    model={singleModel}
                    expectedReturns={
                      assetsQuery.data?.asset_analytics?.expected_returns
                    }
                  />
                )}
                {tsQuery.data && (
                  <HistoryTab ts={tsQuery.data.timeseries} model={singleModel} />
                )}
                {assetsQuery.data && (
                  <AssetPerformanceTab
                    analytics={assetsQuery.data.asset_analytics}
                    model={singleModel}
                  />
                )}
                {strategyQuery.data?.strategy && (
                  <StrategyTab
                    strategy={strategyQuery.data.strategy}
                    model={singleModel}
                  />
                )}
              </div>
            )}
          </div>
        </div>
          </div>
        </div>

        {/* ── Methodology modal ── */}
        {methodologyOpen && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            style={{ background: 'rgb(var(--background) / 0.92)' }}
            onClick={() => setMethodologyOpen(false)}
          >
            <div
              className="relative w-full max-w-3xl max-h-[85vh] bg-card border border-border/60 rounded-[var(--radius)] overflow-hidden flex flex-col"
              style={{ boxShadow: '0 20px 60px -15px rgba(0,0,0,0.8)' }}
              onClick={(e) => e.stopPropagation()}
            >
              <div
                className="flex items-center justify-between px-5 h-11"
                style={{ borderBottom: '1.5px solid rgb(var(--border))' }}
              >
                <div className="flex items-baseline gap-3">
                  <h2 className="stat-label">Methodology</h2>
                  {effectiveModel && (
                    <span className="text-[11px] font-semibold text-foreground">
                      {effectiveModel.display_name}
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => setMethodologyOpen(false)}
                  className="font-mono text-[14px] leading-none text-muted-foreground hover:text-foreground transition-colors px-2 py-1"
                  aria-label="Close methodology"
                >
                  [×]
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-5">
                {methodologyMeta ? (
                  <ModelTab meta={methodologyMeta} model={effectiveModel} />
                ) : (
                  <LoadingSpinner label="Loading methodology" />
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
