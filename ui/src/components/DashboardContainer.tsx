'use client';

import React, { useEffect, useMemo, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import DashboardGallery from '@/components/DashboardGallery';
import AppShell from '@/components/AppShell';
import { RefreshCw, WifiOff, Activity } from 'lucide-react';

const INITIAL_DASHBOARD_FIGURE_BATCH_SIZE = 8;

interface DashboardFigureBatchResponse {
  charts: Record<string, { figure?: any; chart_style?: string | null }>;
}

export default function DashboardContainer({ initialData }: { initialData?: any }) {
  const router = useRouter();
  const { token, user } = useAuth();
  const role = String(user?.role || '').toLowerCase();
  const canUseStudio = !!user && (role === 'owner' || (role !== 'admin' && !user.is_admin && role === 'general'));

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => apiFetchJson('/api/v1/dashboard/summary?include_figures=false'),
    initialData: initialData || undefined,
    staleTime: 1000 * 60 * 2,
    refetchOnWindowFocus: false,
  });

  const initialFigureIds = useMemo(() => {
    const chartsByCategory = data?.charts_by_category as Record<string, any[]> | undefined;
    if (!chartsByCategory) return [] as string[];

    const uniqueCharts = new Map<string, any>();
    Object.values(chartsByCategory).forEach((charts) => {
      charts.forEach((chart) => {
        if (chart?.id) uniqueCharts.set(chart.id, chart);
      });
    });

    return Array.from(uniqueCharts.values())
      .sort((a, b) => (a.rank ?? 0) - (b.rank ?? 0))
      .slice(0, INITIAL_DASHBOARD_FIGURE_BATCH_SIZE)
      .map((chart) => String(chart.id));
  }, [data]);

  const initialFigureQuery = useQuery({
    queryKey: ['dashboard-initial-figures', initialFigureIds],
    queryFn: () => {
      const params = new URLSearchParams();
      initialFigureIds.forEach((id) => params.append('ids', id));
      return apiFetchJson<DashboardFigureBatchResponse>(
        `/api/v1/dashboard/charts/figures?${params.toString()}`
      );
    },
    enabled: initialFigureIds.length > 0,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    refetchOnWindowFocus: false,
  });

  const hydratedChartsByCategory = useMemo(() => {
    const chartsByCategory = data?.charts_by_category as Record<string, any[]> | undefined;
    if (!chartsByCategory) return null;

    const prefetchedFigures = initialFigureQuery.data?.charts ?? {};
    if (Object.keys(prefetchedFigures).length === 0) return chartsByCategory;

    return Object.fromEntries(
      Object.entries(chartsByCategory).map(([category, charts]) => [
        category,
        (charts as any[]).map((chart) => {
          const prefetched = prefetchedFigures[String(chart.id)];
          if (!prefetched?.figure) return chart;
          return {
            ...chart,
            figure: prefetched.figure,
            chart_style: prefetched.chart_style ?? chart.chart_style ?? null,
          };
        }),
      ])
    );
  }, [data, initialFigureQuery.data]);

  // Prefetch the dedicated studio route during idle time for fast first navigation.
  const preloadedStudioRoute = useRef(false);
  useEffect(() => {
    if (!canUseStudio || preloadedStudioRoute.current) return;
    preloadedStudioRoute.current = true;

    const preloadStudioRoute = () => {
      router.prefetch('/studio');
    };

    if (typeof requestIdleCallback !== 'undefined') {
      requestIdleCallback(preloadStudioRoute, { timeout: 3000 });
    } else {
      setTimeout(preloadStudioRoute, 1000);
    }
  }, [canUseStudio, router]);

  if (isError) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center min-h-[70vh] space-y-6 px-4">
          <div className="w-16 h-16 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
            <WifiOff className="w-7 h-7 text-rose-400" />
          </div>
          <div className="text-center space-y-2">
            <p className="text-lg font-semibold text-foreground">Connection Failed</p>
            <p className="text-sm text-muted-foreground font-mono max-w-md">
              {error instanceof Error ? error.message : 'Unable to reach the data pipeline.'}
            </p>
          </div>
          <button
            onClick={() => refetch()}
            className="flex items-center gap-2 px-5 py-2.5 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-400 rounded-xl text-sm font-medium transition-all"
          >
            <RefreshCw className="w-4 h-4" />
            Retry Connection
          </button>
        </div>
      </AppShell>
    );
  }

  const waitingForInitialFigures =
    !!data?.charts_by_category &&
    initialFigureIds.length > 0 &&
    initialFigureQuery.isLoading &&
    !initialFigureQuery.isError;
  const showLoading = (!data && isLoading) || waitingForInitialFigures;

  if (showLoading) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center min-h-[75vh] space-y-8 animate-in fade-in duration-500">
            <div className="relative">
              {/* Outer glowing rings */}
              <div className="absolute inset-0 -m-4 border border-sky-500/20 rounded-full animate-[spin_4s_linear_infinite]" />
              <div className="absolute inset-0 -m-2 border border-indigo-500/20 rounded-full animate-[spin_3s_linear_infinite_reverse]" />
              
              {/* Core spinner */}
              <div className="w-16 h-16 border-4 border-sky-500/10 border-t-sky-400 rounded-full animate-spin shadow-[0_0_15px_rgba(56,189,248,0.2)]" />
              
              {/* Center dot */}
              <div className="absolute inset-0 m-auto w-2 h-2 bg-sky-400 rounded-full animate-pulse shadow-[0_0_10px_rgba(56,189,248,0.6)]" />
            </div>
            
            <div className="text-center space-y-3">
              <div className="text-foreground font-bold text-sm tracking-[0.25em] uppercase bg-clip-text text-transparent bg-gradient-to-r from-sky-400 to-indigo-400">
                Initializing Intelligence
              </div>
              <div className="text-muted-foreground/60 font-mono text-[10px] animate-pulse tracking-wider">
                SYNCING DATA PIPELINES...
              </div>
            </div>
            
            {!token && (
              <a 
                href="/login"
                className="mt-4 px-6 py-2 bg-secondary/30 hover:bg-secondary/50 border border-border/50 rounded-full text-[11px] font-medium text-muted-foreground hover:text-foreground transition-all duration-300"
              >
                Return to Login
              </a>
            )}
        </div>
      </AppShell>
    );
  }

  if (!data && !isLoading && !isError) {
    return (
        <AppShell>
          <div className="flex flex-col items-center justify-center min-h-[75vh] space-y-5 animate-in fade-in">
              <div className="w-16 h-16 rounded-2xl bg-secondary/30 border border-border flex items-center justify-center mb-2">
                <Activity className="w-8 h-8 text-muted-foreground/40" />
              </div>
              <p className="text-sm text-muted-foreground font-medium tracking-wide">Kernel handshake timed out.</p>
              <button 
                onClick={() => refetch()}
                className="px-6 py-2.5 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 text-indigo-400 text-xs font-semibold rounded-xl transition-all"
              >
                RE-INITIALIZE
              </button>
          </div>
        </AppShell>
    );
  }

  return (
      <AppShell hideFooter>
      {hydratedChartsByCategory ? (
        <DashboardGallery
          chartsByCategory={hydratedChartsByCategory}
        />
      ) : (
        <div className="text-center py-20 text-muted-foreground">
          Loading Data Dictionary...
        </div>
      )}
    </AppShell>
  );
}
