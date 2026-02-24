'use client';

import React, { useCallback, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import DashboardGallery from '@/components/DashboardGallery';
import AppShell from '@/components/AppShell';
import { RefreshCw, WifiOff, Activity } from 'lucide-react';

export default function DashboardContainer({ initialData }: { initialData?: any }) {
  const router = useRouter();
  const { token, user } = useAuth();
  const role = String(user?.role || '').toLowerCase();
  const isOwner = !!user && role === 'owner';
  const isAdminRole = !!user && (role === 'admin' || user.is_admin);
  const canUseStudio = !!user && (isOwner || (!isAdminRole && role === 'general'));

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => apiFetchJson('/api/v1/dashboard/summary'),
    initialData: initialData || undefined,
    staleTime: 1000 * 60 * 2,
    refetchOnWindowFocus: false,
  });

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

  const openStudio = useCallback((chartId: string | null = null) => {
    const target = chartId ? `/studio?chartId=${encodeURIComponent(chartId)}` : '/studio';
    router.push(target);
  }, [router]);

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
              className="flex items-center gap-2 px-5 py-2.5 bg-rose-500 hover:bg-rose-400 text-white rounded-xl text-sm font-medium transition-colors shadow-lg shadow-rose-500/20"
            >
              <RefreshCw className="w-4 h-4" />
              Retry Connection
            </button>
        </div>
      </AppShell>
    );
  }

  const showLoading = !data && isLoading;

  if (showLoading) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center min-h-[70vh] space-y-6">
            <div className="relative">
              <div className="absolute inset-0 border-4 border-sky-500/10 rounded-full" />
              <div className="w-16 h-16 border-4 border-sky-500/30 border-t-sky-500 rounded-full animate-spin" />
            </div>
            <div className="text-center space-y-2">
              <div className="text-foreground font-bold text-sm tracking-[0.2em] uppercase transition-all">
                Establishing Secure Connection
              </div>
              <div className="text-muted-foreground font-mono text-[10px] animate-pulse">
                SYNCING AGENTIC RESEARCH NODES...
              </div>
            </div>
            {!token && (
              <a 
                href="/login"
                className="px-6 py-2 bg-secondary/10 hover:bg-secondary/20 border border-border rounded-xl text-xs text-muted-foreground transition-all"
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
          <div className="flex flex-col items-center justify-center min-h-[70vh] space-y-4">
              <Activity className="w-8 h-8 text-muted-foreground mx-auto mb-2 opacity-20" />
              <p className="text-sm text-muted-foreground font-mono">Kernel handshake timed out.</p>
              <button 
                onClick={() => refetch()}
                className="px-4 py-2 bg-indigo-600 text-white text-xs font-bold rounded-lg"
              >
                RE-INITIALIZE
              </button>
          </div>
        </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="relative min-h-screen">
        {/* 📚 Base Dashboard Layer */}
        <div className="px-4 md:px-8 lg:px-12 pb-4 md:pb-8 lg:pb-12 pt-0 md:pt-1 lg:pt-2">
          <div className="w-full max-w-[1400px] mx-auto">
             {data.charts_by_category ? (
                <DashboardGallery 
                    categories={data.categories || []} 
                    chartsByCategory={data.charts_by_category}
                    onOpenStudio={canUseStudio ? openStudio : undefined}
                />
            ) : (
                <div className="text-center py-20 text-muted-foreground">
                    Loading Data Dictionary...
                </div>
            )}
          </div>
        </div>

        {/* Floating Toggle */}
        {canUseStudio && (
          <button
            className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 md:bottom-8 md:right-8 z-[110] p-3 sm:p-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-2xl shadow-2xl shadow-indigo-600/30 transition-all flex items-center gap-2 sm:gap-3 border border-indigo-400/20 group hover:scale-105 active:scale-95"
            onClick={() => openStudio(null)}
          >
             <div className="relative">
                <Activity className="w-4 h-4 sm:w-5 sm:h-5" />
                <div className="absolute -top-1 -right-1 w-2 h-2 bg-emerald-400 rounded-full animate-ping" />
                <div className="absolute -top-1 -right-1 w-2 h-2 bg-emerald-400 rounded-full" />
             </div>
             <span className="text-xs font-bold uppercase tracking-widest hidden lg:group-hover:block transition-all">Research Studio</span>
          </button>
        )}
      </div>
    </AppShell>
  );
}
