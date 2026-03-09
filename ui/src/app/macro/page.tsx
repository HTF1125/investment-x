'use client';

import { useEffect, useState } from 'react';
import AppShell from '@/components/AppShell';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { useTheme } from '@/context/ThemeContext';
import { LoadingSpinner, ErrorBox } from '@/components/macro/SharedComponents';
import { REGIME_COLORS, TABS } from '@/components/macro/constants';
import { OverviewTab } from '@/components/macro';
import { RegimeTab } from '@/components/macro';
import { LiquidityTab } from '@/components/macro';
import { TacticalTab } from '@/components/macro';
import type { Target, Snapshot, TimeseriesData, BacktestData, Tab } from '@/components/macro/types';

export default function MacroPage() {
  useEffect(() => { document.title = 'Macro Outlook | Investment-X'; }, []);

  const { theme } = useTheme();
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [selectedTarget, setSelectedTarget] = useState<string>('');

  const targetsQuery = useQuery({
    queryKey: ['macro-targets'],
    queryFn: () => apiFetchJson<{ targets: Target[] }>('/api/macro/targets'),
    staleTime: 300_000,
  });

  useEffect(() => {
    if (targetsQuery.data?.targets?.length && !selectedTarget) {
      const acwi = targetsQuery.data.targets.find(t => t.name === 'MSCI ACWI');
      setSelectedTarget(acwi ? acwi.name : targetsQuery.data.targets[0].name);
    }
  }, [targetsQuery.data, selectedTarget]);

  const outlookQuery = useQuery({
    queryKey: ['macro-outlook', selectedTarget],
    queryFn: () => apiFetchJson<{ target_name: string; computed_at: string; snapshot: Snapshot }>(
      `/api/macro/outlook?target=${encodeURIComponent(selectedTarget)}`
    ),
    enabled: !!selectedTarget,
    staleTime: 120_000,
  });

  const timeseriesQuery = useQuery({
    queryKey: ['macro-timeseries', selectedTarget],
    queryFn: () => apiFetchJson<{ target_name: string; timeseries: TimeseriesData }>(
      `/api/macro/timeseries?target=${encodeURIComponent(selectedTarget)}`
    ),
    enabled: !!selectedTarget,
    staleTime: 120_000,
  });

  const backtestQuery = useQuery({
    queryKey: ['macro-backtest', selectedTarget],
    queryFn: () => apiFetchJson<{ target_name: string; backtest: BacktestData }>(
      `/api/macro/backtest?target=${encodeURIComponent(selectedTarget)}`
    ),
    enabled: !!selectedTarget,
    staleTime: 120_000,
  });

  const snapshot = outlookQuery.data?.snapshot ?? null;
  const timeseries = timeseriesQuery.data?.timeseries ?? null;
  const backtest = backtestQuery.data?.backtest ?? null;

  const isInitialLoading =
    targetsQuery.isLoading ||
    (!selectedTarget && !targetsQuery.isError) ||
    (!!selectedTarget && outlookQuery.isLoading);

  return (
    <AppShell>
      <div className="max-w-[1600px] mx-auto px-3 sm:px-4 lg:px-6 py-3">

        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2 mb-3">
          <h1 className="text-[16px] font-semibold text-foreground tracking-tight">Macro Outlook</h1>
          <div className="flex items-center gap-2 flex-wrap">
            <select
              value={selectedTarget}
              onChange={(e) => setSelectedTarget(e.target.value)}
              className="border border-border/50 rounded-lg px-2.5 py-1 text-[11px] focus:outline-none focus:border-sky-500/40 text-foreground cursor-pointer"
              style={{ colorScheme: theme === 'light' ? 'light' : 'dark', backgroundColor: 'rgb(var(--background))', color: 'rgb(var(--foreground))' }}
            >
              {(targetsQuery.data?.targets ?? []).map(t => (
                <option key={t.name} value={t.name}>{t.name} - {t.region}</option>
              ))}
            </select>

            {snapshot && (
              <>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold border"
                  style={{
                    backgroundColor: (REGIME_COLORS[snapshot.current.regime] ?? '#888') + '18',
                    borderColor: (REGIME_COLORS[snapshot.current.regime] ?? '#888') + '40',
                    color: REGIME_COLORS[snapshot.current.regime] ?? '#888',
                  }}>
                  <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: REGIME_COLORS[snapshot.current.regime] }} />
                  {snapshot.current.regime}
                </span>
                {snapshot.current.trend_bullish != null && (
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold border ${
                    snapshot.current.trend_bullish
                      ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-500'
                      : 'bg-rose-500/10 border-rose-500/40 text-rose-500'
                  }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${snapshot.current.trend_bullish ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                    {snapshot.current.trend_bullish ? 'Uptrend' : 'Downtrend'}
                  </span>
                )}
              </>
            )}

            {outlookQuery.data?.computed_at && (
              <span className="text-[9px] font-mono text-muted-foreground/50">
                {new Date(outlookQuery.data.computed_at).toLocaleString()}
              </span>
            )}
          </div>
        </div>

        {/* Tab navigation */}
        <div className="border-b border-border/40 mb-3">
          <div className="flex gap-0.5 overflow-x-auto no-scrollbar -mb-px">
            {TABS.map(tab => (
              <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                className={`whitespace-nowrap px-2.5 py-1.5 text-[11px] font-medium border-b-2 transition-all ${
                  activeTab === tab.key
                    ? 'text-foreground border-sky-500'
                    : 'text-muted-foreground border-transparent hover:text-foreground hover:border-foreground/20'
                }`}>
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tab content */}
        {isInitialLoading ? (
          <LoadingSpinner label="Loading macro data" />
        ) : targetsQuery.isError ? (
          <ErrorBox message="Failed to load targets." />
        ) : outlookQuery.isError ? (
          <ErrorBox message={`Failed to load data for ${selectedTarget}. ${(outlookQuery.error as any)?.message || ''}`} />
        ) : !snapshot ? (
          <ErrorBox message="No macro data available for this target." />
        ) : (
          <>
            {activeTab === 'overview' && <OverviewTab snapshot={snapshot} timeseries={timeseries} tsLoading={timeseriesQuery.isLoading} backtest={backtest} btLoading={backtestQuery.isLoading} target={selectedTarget} />}
            {activeTab === 'regime' && <RegimeTab snapshot={snapshot} timeseries={timeseries} tsLoading={timeseriesQuery.isLoading} backtest={backtest} btLoading={backtestQuery.isLoading} target={selectedTarget} />}
            {activeTab === 'liquidity' && <LiquidityTab snapshot={snapshot} timeseries={timeseries} tsLoading={timeseriesQuery.isLoading} backtest={backtest} btLoading={backtestQuery.isLoading} target={selectedTarget} />}
            {activeTab === 'tactical' && <TacticalTab snapshot={snapshot} timeseries={timeseries} tsLoading={timeseriesQuery.isLoading} backtest={backtest} btLoading={backtestQuery.isLoading} target={selectedTarget} />}
          </>
        )}
      </div>
    </AppShell>
  );
}
