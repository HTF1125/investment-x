'use client';

import React from 'react';
import { useAuth } from '@/context/AuthContext';
import { useQuery } from '@tanstack/react-query';
import { apiFetch, apiFetchJson } from '@/lib/api';
import DashboardGallery from '@/components/DashboardGallery';
import Header from '@/components/Header';
import AppShell from '@/components/AppShell';
import dynamic from 'next/dynamic';
import { RefreshCw, WifiOff, LayoutGrid, Activity, X } from 'lucide-react';
import { useSearchParams, useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';

// Lazy load heavy editor
const CustomChartEditor = dynamic(() => import('@/components/CustomChartEditor'), { 
  ssr: false,
  loading: () => <div className="h-full flex items-center justify-center font-mono text-slate-500 animate-pulse bg-slate-900/50 backdrop-blur-xl">INITIALIZING QUANT STUDIO...</div>
});

export default function DashboardContainer({ initialData }: { initialData?: any }) {
  const { token, user } = useAuth();
  const searchParams = useSearchParams();
  const router = useRouter();
  
  const viewParam = searchParams.get('view') || 'gallery';
  const editingChartId = searchParams.get('id');
  const isAdmin = user?.is_admin;

  const showStudio = viewParam === 'studio';

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => apiFetchJson('/api/v1/dashboard/summary'),
    initialData: initialData || undefined, // Fallback to client-side fetch if SSR returned null
    staleTime: 0, // Always consider stale to ensure fresh data after Studio edits
  });

  // Error and loading states now render *inside* AppShell so the navbar stays accessible
  if (isError) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center min-h-[70vh] space-y-6 px-4">
            <div className="w-16 h-16 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
              <WifiOff className="w-7 h-7 text-rose-400" />
            </div>
            <div className="text-center space-y-2">
              <p className="text-lg font-semibold text-white">Connection Failed</p>
              <p className="text-sm text-slate-500 font-mono max-w-md">
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

  // Determine if we should show the loading screen
  // If we have SSR data, we never show the loading screen
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
              <div className="text-slate-200 font-bold text-sm tracking-[0.2em] uppercase transition-all">
                Establishing Secure Connection
              </div>
              <div className="text-slate-500 font-mono text-[10px] animate-pulse">
                SYNCING AGENTIC RESEARCH NODES...
              </div>
            </div>
            {!token && (
              <button 
                onClick={() => router.push('/login')}
                className="px-6 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-xs text-slate-400 transition-all"
              >
                Return to Login
              </button>
            )}
            {/* Fail-safe button after 5 seconds of loading might be good, but for now we keep it clean */}
        </div>
      </AppShell>
    );
  }

  // If no data and not loading (and no error caught by react-query), it's a silent fail
  if (!data && !isLoading && !isError) {
    return (
        <AppShell>
          <div className="flex flex-col items-center justify-center min-h-[70vh] space-y-4">
              <Activity className="w-8 h-8 text-slate-700 mx-auto mb-2 opacity-20" />
              <p className="text-sm text-slate-500 font-mono">Kernel handshake timed out.</p>
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

  const setView = (v: string, id: string | null = null) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('view', v);
    if (id) params.set('id', id); else params.delete('id');
    router.push(`?${params.toString()}`, { scroll: false });
  };

  const closeStudio = () => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('view', 'gallery');
    params.delete('id');
    router.push(`?${params.toString()}`, { scroll: false });
  };

  return (
    <AppShell>
      <div className="relative min-h-screen">
        {/* 📚 Base Dashboard Layer */}
        <div className={`p-4 md:p-8 lg:p-12 transition-all duration-500 ${showStudio ? 'opacity-30 scale-[0.98] blur-sm pointer-events-none' : 'opacity-100 scale-100'}`}>
          <div className="max-w-[1600px] mx-auto">
             <Header />
             {data.charts_by_category ? (
                <DashboardGallery 
                    categories={data.categories || []} 
                    chartsByCategory={data.charts_by_category} 
                />
            ) : (
                <div className="text-center py-20 text-slate-500">
                    Loading Data Dictionary...
                </div>
            )}
          </div>
          
          <footer className="max-w-[1600px] mx-auto mt-32 py-16 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-6 opacity-40 grayscale hover:grayscale-0 hover:opacity-100 transition-all">
            <div className="text-slate-500 text-xs font-mono tracking-widest uppercase">
            [ End of Intelligence Feed ]
            </div>
            <div className="text-slate-500 text-xs font-light">
            © {new Date().getFullYear()} Investment-X Research Library. Structured data and proprietary models.
            </div>
          </footer>
        </div>

        {/* 🚀 Integrated Studio Workspace (Slide-over) */}
        <AnimatePresence>
          {showStudio && isAdmin && (
            <>
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-black/60 backdrop-blur-md z-[120]"
                onClick={closeStudio}
              />
              <motion.div 
                initial={{ x: '100%' }}
                animate={{ x: 0 }}
                exit={{ x: '100%' }}
                transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                className="fixed inset-y-0 right-0 w-[94vw] bg-black border-l border-white/10 shadow-2xl z-[130] flex flex-col overflow-hidden"
              >
                {/* Studio Control Header */}
                <div className="h-14 shrink-0 flex items-center justify-between px-6 bg-[#05070c] border-b border-white/10">
                   <div className="flex items-center gap-4">
                      <div className="flex items-center gap-2 text-indigo-400">
                         <Activity className="w-5 h-5" />
                         <span className="text-xs font-bold font-mono uppercase tracking-[0.2em]">Quantum Studio Focus</span>
                      </div>
                      <div className="w-px h-4 bg-white/10" />
                      <span className="text-[10px] text-slate-500 font-mono italic">
                        {editingChartId ? `Modifying Instance: ${editingChartId}` : 'Authoring New Research Protocol'}
                      </span>
                   </div>
                   <button 
                     onClick={closeStudio}
                     className="p-2 text-slate-500 hover:text-white hover:bg-white/5 rounded-xl transition-all flex items-center gap-2 group"
                   >
                     <span className="text-[10px] font-bold font-mono opacity-0 group-hover:opacity-100 transition-opacity">CLOSE WORKSPACE</span>
                     <X className="w-5 h-5" />
                   </button>
                </div>

                <div className="flex-grow overflow-hidden relative">
                   <CustomChartEditor mode="integrated" initialChartId={editingChartId} onClose={closeStudio} />
                </div>
              </motion.div>
            </>
          )}
        </AnimatePresence>

        {/* Floating Toggle (Optional shortcut) */}
        {isAdmin && !showStudio && (
          <motion.button
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="fixed bottom-8 right-8 z-[110] p-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-2xl shadow-2xl shadow-indigo-600/30 transition-all flex items-center gap-3 border border-indigo-400/20 group hover:scale-105 active:scale-95"
            onClick={() => setView('studio')}
          >
             <div className="relative">
                <Activity className="w-5 h-5" />
                <div className="absolute -top-1 -right-1 w-2 h-2 bg-emerald-400 rounded-full animate-ping" />
                <div className="absolute -top-1 -right-1 w-2 h-2 bg-emerald-400 rounded-full" />
             </div>
             <span className="text-xs font-bold uppercase tracking-widest hidden group-hover:block transition-all">Research Studio</span>
          </motion.button>
        )}
      </div>
    </AppShell>
  );
}
