'use client';

import React from 'react';
import { useAuth } from '@/context/AuthContext';
import { useQuery } from '@tanstack/react-query';
import DashboardGallery from '@/components/DashboardGallery';
import Header from '@/components/Header';
import AppShell from '@/components/AppShell';

export default function DashboardContainer() {
  const { user, isAuthenticated, loading: authLoading, token } = useAuth(); // Assuming useAuth exposes token or get token inside queryFn

  const { data, isLoading: dataLoading, isError, error } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: async () => {
      const headers: Record<string, string> = {};
      const authToken = token || (typeof window !== 'undefined' ? localStorage.getItem('token') : null);
      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
      }

      const res = await fetch('/api/v1/dashboard/summary', { headers });
      if (!res.ok) {
         throw new Error('Failed to fetch dashboard data');
      }
      return res.json();
    },
  });

  if (isError) {
    return (
        <div className="min-h-screen flex flex-col items-center justify-center space-y-4">
             <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-center">
                <p className="font-bold mb-2">Connection Failed</p>
                <p className="text-sm font-mono mb-4">{error instanceof Error ? error.message : 'Unknown error'}</p>
                <button 
                  onClick={() => window.location.reload()}
                  className="px-4 py-2 bg-rose-500 hover:bg-rose-600 text-white rounded-lg text-sm transition-colors"
                >
                  Retry Connection
                </button>
             </div>
        </div>
    );
  }

  if (!data) {
    return (
        <div className="min-h-screen flex flex-col items-center justify-center space-y-4">
             <div className="w-12 h-12 border-4 border-sky-500/30 border-t-sky-500 rounded-full animate-spin" />
             <div className="text-slate-500 font-mono text-sm animate-pulse">
                ESTABLISHING SECURE CONNECTION...
             </div>
        </div>
    );
  }

  return (
    <AppShell>
      <div className="p-4 md:p-8 lg:p-12 overflow-x-hidden">
        <Header />

        {/* 🖼️ Dynamic Research Gallery */}
        <div className="max-w-[1600px] mx-auto">
            {data && data.charts_by_category ? (
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
        
        {/* 🏁 Footer */}
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
