'use client';

import { useEffect, useState } from 'react';
import AppShell from '@/components/AppShell';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { useTheme } from '@/context/ThemeContext';
import { LoadingSpinner } from '@/components/macro/SharedComponents';
import { TABS } from '@/components/macro/constants';
import { OverviewTab } from '@/components/macro';
import { StrategyTab } from '@/components/macro';
import { StrategyFactorsTab } from '@/components/macro';
import { MethodologyTab } from '@/components/macro';
import { RegimeStrategyRegimeTab } from '@/components/macro';
import type { Tab, RegimeStrategyBacktest, FactorCategory, CurrentSignalData, SummaryIndex, Snapshot, TimeseriesData } from '@/components/macro/types';

const STATIC_TABS = new Set<Tab>(['methodology', 'overview']);
const DATA_TABS = new Set<Tab>(['strategy', 'factors', 'regime']);

// Map new regime-strategy index names → old outlook target names
const OUTLOOK_NAME_MAP: Record<string, string> = {
  'ACWI': 'MSCI ACWI',
  'Stoxx 50': 'Euro Stoxx 50',
  'Shanghai Comp': 'Shanghai Composite',
};

export default function MacroPage() {
  useEffect(() => { document.title = 'Macro Regime Strategy | Investment-X'; }, []);

  const { theme } = useTheme();
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [strategyIndex, setStrategyIndex] = useState<string>('ACWI');

  const needsData = DATA_TABS.has(activeTab);
  const showIndexSelector = DATA_TABS.has(activeTab);

  // ── Queries ──
  const indicesQuery = useQuery({
    queryKey: ['regime-strategy-indices'],
    queryFn: () => apiFetchJson<{ indices: string[] }>('/api/macro/regime-strategy/indices'),
    staleTime: 300_000,
  });

  const backtestQuery = useQuery({
    queryKey: ['regime-strategy-backtest', strategyIndex],
    queryFn: () => apiFetchJson<{ index_name: string; computed_at: string; backtest: RegimeStrategyBacktest }>(
      `/api/macro/regime-strategy/backtest?index=${encodeURIComponent(strategyIndex)}`
    ),
    enabled: (activeTab === 'strategy' || activeTab === 'factors' || activeTab === 'regime') && !!strategyIndex,
    staleTime: 120_000,
  });

  const factorsQuery = useQuery({
    queryKey: ['regime-strategy-factors', strategyIndex],
    queryFn: () => apiFetchJson<{ index_name: string; computed_at: string; factors: Record<string, FactorCategory> }>(
      `/api/macro/regime-strategy/factors?index=${encodeURIComponent(strategyIndex)}`
    ),
    enabled: activeTab === 'factors' && !!strategyIndex,
    staleTime: 120_000,
  });

  const signalQuery = useQuery({
    queryKey: ['regime-strategy-signal', strategyIndex],
    queryFn: () => apiFetchJson<{ current_signal: CurrentSignalData }>(
      `/api/macro/regime-strategy/signal?index=${encodeURIComponent(strategyIndex)}`
    ),
    enabled: activeTab === 'factors' && !!strategyIndex,
    staleTime: 120_000,
  });

  // Overview: summary for all indices
  const summaryQuery = useQuery({
    queryKey: ['regime-strategy-summary'],
    queryFn: () => apiFetchJson<{ indices: SummaryIndex[] }>('/api/macro/regime-strategy/summary'),
    enabled: activeTab === 'overview',
    staleTime: 120_000,
  });

  // Regime tab: outlook probability data from old macro system
  const outlookTarget = OUTLOOK_NAME_MAP[strategyIndex] ?? strategyIndex;

  const outlookQuery = useQuery({
    queryKey: ['macro-outlook', outlookTarget],
    queryFn: () => apiFetchJson<{ snapshot: Snapshot }>(`/api/macro/outlook?target=${encodeURIComponent(outlookTarget)}`),
    enabled: activeTab === 'regime' && !!strategyIndex,
    staleTime: 120_000,
  });

  const timeseriesQuery = useQuery({
    queryKey: ['macro-timeseries', outlookTarget],
    queryFn: () => apiFetchJson<{ timeseries: TimeseriesData }>(`/api/macro/timeseries?target=${encodeURIComponent(outlookTarget)}`),
    enabled: activeTab === 'regime' && !!strategyIndex,
    staleTime: 120_000,
  });

  const backtest = backtestQuery.data?.backtest ?? null;
  const factors = factorsQuery.data?.factors ?? null;
  const signal = signalQuery.data?.current_signal ?? null;

  return (
    <AppShell>
      <div className="max-w-[1600px] mx-auto px-4 sm:px-5 lg:px-6 py-4">

        {/* Tab bar: selector | tabs | timestamp */}
        <div className="border-b border-border/25 mb-3">
          <div className="flex items-center gap-3 -mb-px">
            {/* Index selector (only on data tabs) */}
            {showIndexSelector && (
              <select
                value={strategyIndex}
                onChange={(e) => setStrategyIndex(e.target.value)}
                className="border border-border/40 rounded-md px-2.5 py-1.5 text-[11px] font-medium focus:outline-none focus:border-primary/40 text-foreground cursor-pointer shrink-0"
                style={{ colorScheme: theme === 'light' ? 'light' : 'dark', backgroundColor: 'rgb(var(--background))', color: 'rgb(var(--foreground))' }}
              >
                {(indicesQuery.data?.indices ?? []).map(idx => (
                  <option key={idx} value={idx}>{idx}</option>
                ))}
              </select>
            )}

            {/* Tabs */}
            <div className="flex gap-0.5 overflow-x-auto no-scrollbar flex-1">
              {TABS.map(tab => (
                <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                  className={`tab-link ${activeTab === tab.key ? 'active' : ''}`}>
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Timestamp */}
            <div className="flex items-center gap-2 shrink-0 pb-2">
              {backtestQuery.data?.computed_at && needsData && (
                <span className="text-[9px] font-mono text-muted-foreground/40">
                  {new Date(backtestQuery.data.computed_at).toLocaleString()}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Tab content */}
        {activeTab === 'overview' ? (
          <OverviewTab summary={summaryQuery.data?.indices ?? null} />
        ) : activeTab === 'methodology' ? (
          <MethodologyTab />
        ) : needsData && backtestQuery.isLoading ? (
          <LoadingSpinner label="Loading strategy data" />
        ) : (
          <>
            {activeTab === 'strategy' && (
              <StrategyTab backtest={backtest} isLoading={backtestQuery.isLoading} target={strategyIndex} />
            )}
            {activeTab === 'regime' && (
              <RegimeStrategyRegimeTab
                backtest={backtest} isLoading={backtestQuery.isLoading} target={strategyIndex}
                snapshot={outlookQuery.data?.snapshot ?? null}
                timeseries={timeseriesQuery.data?.timeseries ?? null}
                tsLoading={timeseriesQuery.isLoading}
              />
            )}
            {activeTab === 'factors' && (
              <StrategyFactorsTab
                factors={factors}
                signal={signal}
                isLoading={factorsQuery.isLoading || signalQuery.isLoading}
                target={strategyIndex}
              />
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
