'use client';

import React from 'react';
import { useAuth } from '@/context/AuthContext';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import DashboardGallery from '@/components/DashboardGallery';
import Header from '@/components/Header';
import AppShell from '@/components/AppShell';
import { RefreshCw, WifiOff } from 'lucide-react';

export default function DashboardContainer() {
  const { token } = useAuth();

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => apiFetchJson('/api/v1/dashboard/summary'),
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

  if (isLoading || !data) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center min-h-[70vh] space-y-4">
            <div className="w-12 h-12 border-4 border-sky-500/30 border-t-sky-500 rounded-full animate-spin" />
            <div className="text-slate-500 font-mono text-sm animate-pulse">
              ESTABLISHING SECURE CONNECTION...
            </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="p-4 md:p-8 lg:p-12 overflow-x-hidden">
        <Header />

        {/* Dynamic Research Gallery */}
        <div className="max-w-[1600px] mx-auto">
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
        
        {/* Footer */}
        <footer className="max-w-[1600px] mx-auto mt-32 py-16 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-6 opacity-40 grayscale hover:grayscale-0 hover:opacity-100 transition-all">
            <div className="text-slate-500 text-xs font-mono tracking-widest uppercase">
            [ End of Intelligence Feed ]
            </div>
            <div className="text-slate-500 text-xs font-light">
            © {new Date().getFullYear()} Investment-X Research Library. Structured data and proprietary models.
            </div>
        </footer>
      </div>
    </AppShell>
  );
}
