'use client';

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import DashboardGallery from '@/components/DashboardGallery';
import AppShell from '@/components/AppShell';
import dynamic from 'next/dynamic';
import { RefreshCw, WifiOff, Activity, X } from 'lucide-react';

// ─── Eager chunk preload via dynamic import handle ───
// The chunk is fetched during idle time after dashboard mount (see useEffect below).
// By the time the user clicks "open studio", the JS is already parsed & in memory.
const editorImport = () => import('@/components/CustomChartEditor');
const CustomChartEditor = dynamic(editorImport, {
  ssr: false,
  loading: () => (
    <div className="h-full flex items-center justify-center font-mono text-muted-foreground animate-pulse bg-card/50">
      INITIALIZING QUANT STUDIO...
    </div>
  ),
});

export default function DashboardContainer({ initialData }: { initialData?: any }) {
  const { token, user } = useAuth();
  const queryClient = useQueryClient();
  const role = String(user?.role || '').toLowerCase();
  const isOwner = !!user && role === 'owner';
  const isAdminRole = !!user && (role === 'admin' || user.is_admin);
  const canUseStudio = !!user && (isOwner || (!isAdminRole && role === 'general'));

  // Studio state — pure React state, no URL params
  const [studioOpen, setStudioOpen] = useState(false);
  const [studioChartId, setStudioChartId] = useState<string | null>(null);
  // Once true, the editor component stays mounted permanently (hidden off-screen)
  const [editorReady, setEditorReady] = useState(false);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => apiFetchJson('/api/v1/dashboard/summary'),
    initialData: initialData || undefined,
    staleTime: 1000 * 60 * 2,
    refetchOnWindowFocus: false,
  });

  // ─── Preload strategy ───
  // After dashboard renders, use idle callback to:
  //   1. Fetch the CustomChartEditor webpack chunk (Monaco + Plotly)
  //   2. Prefetch the /api/custom chart list into react-query cache
  // This ensures zero JS download delay on first studio click.
  const preloaded = useRef(false);
  useEffect(() => {
    if (!canUseStudio || preloaded.current) return;
    preloaded.current = true;

    const preload = () => {
      // 1. Trigger webpack chunk download + parse
      editorImport().catch(() => {
        // Silently fail preload — will load on-demand as fallback
      });

      // 2. Do not prefetch /api/custom here to avoid background load noise.
    };

    // Use requestIdleCallback if available, otherwise setTimeout
    if (typeof requestIdleCallback !== 'undefined') {
      requestIdleCallback(preload, { timeout: 3000 });
    } else {
      setTimeout(preload, 1000);
    }
  }, [canUseStudio, queryClient]);

  const openStudio = useCallback((chartId: string | null = null) => {
    setStudioChartId(chartId);
    setStudioOpen(true);
    // Fallback: if preload hasn't finished, mount the editor now
    if (!editorReady) setEditorReady(true);
  }, [editorReady]);

  const closeStudio = useCallback(() => {
    setStudioOpen(false);
  }, []);

  // Close studio on Escape key
  useEffect(() => {
    if (!studioOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeStudio();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [studioOpen, closeStudio]);

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
        <div className={`px-4 md:px-8 lg:px-12 pb-4 md:pb-8 lg:pb-12 pt-2 md:pt-4 lg:pt-6 transition-opacity duration-150 ${studioOpen ? 'opacity-20 pointer-events-none' : 'opacity-100'}`}>
          <div className="w-full max-w-[1400px] mx-auto">
             {data.charts_by_category ? (
                <DashboardGallery 
                    categories={data.categories || []} 
                    chartsByCategory={data.charts_by_category}
                    onOpenStudio={openStudio}
                />
            ) : (
                <div className="text-center py-20 text-muted-foreground">
                    Loading Data Dictionary...
                </div>
            )}
          </div>
          

        </div>

        {/* 🚀 Studio Backdrop */}
        {studioOpen && (
          <div 
            className="fixed inset-0 bg-background/60 z-[120] animate-in fade-in duration-150 backdrop-blur-sm"
            onClick={closeStudio}
          />
        )}

        {/* Studio Panel — CSS transform only, no mount/unmount */}
        <div
          className={`fixed inset-y-0 right-0 w-full sm:w-[94vw] md:w-[90vw] lg:w-[80vw] bg-background border-l border-border shadow-2xl z-[130] flex flex-col overflow-hidden transition-transform duration-200 ease-out ${
            studioOpen ? 'translate-x-0' : 'translate-x-full'
          }`}
          style={{ pointerEvents: studioOpen ? 'auto' : 'none' }}
        >
          {/* Studio Control Header */}
          <div className="h-14 sm:h-16 shrink-0 flex items-center justify-between px-3 sm:px-4 md:px-6 bg-card border-b border-border">
             <div className="flex items-center gap-2 sm:gap-4 min-w-0">
                <div className="flex items-center gap-2 text-indigo-400">
                   <Activity className="w-5 h-5" />
                   <span className="text-[10px] sm:text-xs font-bold font-mono uppercase tracking-[0.2em] whitespace-nowrap">Quantum Studio Focus</span>
                </div>
                <div className="hidden sm:block w-px h-4 bg-foreground/10" />
                <span className="hidden md:block text-[10px] text-muted-foreground font-mono italic truncate max-w-[40vw]">
                  {studioChartId ? `Modifying Instance: ${studioChartId}` : 'Authoring New Research Protocol'}
                </span>
             </div>
             <button 
               onClick={closeStudio}
               className="p-2 text-muted-foreground hover:text-foreground hover:bg-foreground/5 rounded-xl transition-all flex items-center gap-1 sm:gap-2 group shrink-0"
             >
               <span className="hidden md:block text-[10px] font-bold font-mono opacity-0 group-hover:opacity-100 transition-opacity">CLOSE WORKSPACE</span>
               <X className="w-5 h-5" />
             </button>
          </div>

          <div className="flex-grow overflow-hidden relative">
            {editorReady && (
              <CustomChartEditor mode="integrated" initialChartId={studioChartId} onClose={closeStudio} />
            )}
          </div>
        </div>

        {/* Floating Toggle */}
        {canUseStudio && !studioOpen && (
          <button
            className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 md:bottom-8 md:right-8 z-[110] p-3 sm:p-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-2xl shadow-2xl shadow-indigo-600/30 transition-all flex items-center gap-2 sm:gap-3 border border-indigo-400/20 group hover:scale-105 active:scale-95"
            onClick={() => openStudio()}
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
