'use client';

import AuthGuard from '@/components/AuthGuard';
import TimeseriesManager from '@/components/TimeseriesManager';
import AppShell from '@/components/AppShell';
import { useAuth } from '@/context/AuthContext';
import { ShieldAlert } from 'lucide-react';

export default function AdminTimeseriesPage() {
  const { user } = useAuth();

  return (
    <AuthGuard>
      <AppShell>
        <div className="p-4 md:p-8 lg:p-12 max-w-[1600px] mx-auto">
          {user?.is_admin ? (
            <TimeseriesManager />
          ) : (
            <div className="flex flex-col items-center justify-center py-40 text-slate-500">
              <ShieldAlert className="w-16 h-16 mb-4 text-rose-500/50" />
              <h2 className="text-xl font-semibold text-slate-300 mb-2">Access Denied</h2>
              <p className="text-sm text-slate-500">This page is restricted to administrators.</p>
            </div>
          )}
        </div>
      </AppShell>
    </AuthGuard>
  );
}
