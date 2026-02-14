'use client';

import React from 'react';
import CustomChartEditor from '@/components/CustomChartEditor';
import AuthGuard from '@/components/AuthGuard';
import AppShell from '@/components/AppShell';
import { Layers } from 'lucide-react';

export default function CustomChartPage() {
  return (
    <AuthGuard>
      <AppShell>
        <div className="px-4 md:px-8 lg:px-12 pb-20 max-w-[1600px] mx-auto">
          
          {/* Header */}
          <div className="flex items-center gap-4 mb-8 pt-4">
            <div className="p-3 bg-indigo-500/10 rounded-xl border border-indigo-500/20">
              <Layers className="w-8 h-8 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-sky-400">
                Custom Analytics Studio
              </h1>
              <p className="text-slate-500 text-sm mt-1">
                Define bespoke indicators using Python &amp; Plotly Express.
              </p>
            </div>
          </div>

          {/* Editor Container */}
          <div className="h-[calc(100vh-200px)] min-h-[600px] glass-card p-6 rounded-2xl border border-white/5 bg-slate-900/50 backdrop-blur-3xl shadow-2xl">
            <CustomChartEditor />
          </div>

        </div>
      </AppShell>
    </AuthGuard>
  );
}
