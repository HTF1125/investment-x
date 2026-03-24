'use client';

import { useEffect, useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { TABS } from '@/components/screener/constants';
import { RankingsTab, FlowsTab, MethodologyTab } from '@/components/screener';
import type { ScreenerTab, ScreenerResponse, FlowsResponse } from '@/components/screener/types';

export default function ScreenerPage() {
  useEffect(() => { document.title = 'VOMO Screener | Investment-X'; }, []);

  const [activeTab, setActiveTab] = useState<ScreenerTab>('rankings');

  const rankingsQuery = useQuery({
    queryKey: ['screener-rankings'],
    queryFn: () => apiFetchJson<ScreenerResponse>('/api/screener/rankings'),
    enabled: activeTab === 'rankings',
    staleTime: 300_000,
    retry: 1,
  });

  const flowsQuery = useQuery({
    queryKey: ['screener-flows'],
    queryFn: () => apiFetchJson<FlowsResponse>('/api/screener/flows'),
    enabled: activeTab === 'flows',
    staleTime: 300_000,
    retry: 1,
  });

  const computedAt = rankingsQuery.data?.computed_at || flowsQuery.data?.computed_at;

  return (
    <AppShell>
      <div className="max-w-[1600px] mx-auto px-4 sm:px-5 lg:px-6 py-4">

        {/* Page header */}
        <div className="flex items-center justify-between mb-3">
          <div>
            <h1 className="page-title">VOMO Screener</h1>
            <p className="text-[10px] text-muted-foreground/50 font-mono mt-0.5 uppercase tracking-wider">
              Institutional flows + risk-adjusted momentum scoring
            </p>
          </div>
          {computedAt && (
            <span className="text-[9px] font-mono text-muted-foreground/35 shrink-0">
              computed {new Date(computedAt).toLocaleString()}
            </span>
          )}
        </div>

        {/* Tab bar */}
        <div className="border-b border-border/25 mb-3">
          <div className="flex gap-0 overflow-x-auto no-scrollbar -mb-px">
            {TABS.map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`tab-link ${activeTab === tab.key ? 'active' : ''}`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tab content */}
        {activeTab === 'rankings' && (
          <RankingsTab
            stocks={rankingsQuery.data?.stocks ?? []}
            isLoading={rankingsQuery.isLoading}
            error={rankingsQuery.error ? String((rankingsQuery.error as any)?.message || rankingsQuery.error) : undefined}
          />
        )}
        {activeTab === 'flows' && (
          <FlowsTab
            flows={flowsQuery.data?.flows ?? []}
            isLoading={flowsQuery.isLoading}
            error={flowsQuery.error ? String((flowsQuery.error as any)?.message || flowsQuery.error) : undefined}
          />
        )}
        {activeTab === 'methodology' && (
          <MethodologyTab />
        )}
      </div>
    </AppShell>
  );
}
