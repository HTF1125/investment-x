'use client';

import { useMemo, useState } from 'react';
import AuthGuard from '@/components/AuthGuard';
import TimeseriesManager from '@/components/TimeseriesManager';
import UserManager from '@/components/UserManager';
import AppShell from '@/components/AppShell';
import { useAuth } from '@/context/AuthContext';
import { Database, ShieldAlert, Users } from 'lucide-react';

type AdminTab = 'timeseries' | 'users';

export default function AdminTimeseriesPage() {
  const { user } = useAuth();
  const isAdmin = !!user && (user.role === 'owner' || user.role === 'admin' || user.is_admin);
  const [activeTab, setActiveTab] = useState<AdminTab>('timeseries');

  const tabs = useMemo(
    () => [
      { id: 'timeseries' as const, label: 'Timeseries', icon: Database },
      { id: 'users' as const, label: 'Users', icon: Users },
    ],
    []
  );

  return (
    <AuthGuard>
      <AppShell>
        <div className="p-4 md:p-8 lg:p-12 max-w-[1600px] mx-auto">
          {isAdmin ? (
            <div className="space-y-6">
              <div className="flex flex-wrap items-center gap-2">
                {tabs.map((tab) => {
                  const Icon = tab.icon;
                  const active = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold border transition-colors ${
                        active
                          ? 'bg-indigo-500/15 border-indigo-500/40 text-indigo-700 dark:text-indigo-300'
                          : 'bg-card/60 border-border/70 text-muted-foreground hover:text-foreground hover:bg-accent/30'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      {tab.label}
                    </button>
                  );
                })}
              </div>

              {activeTab === 'timeseries' ? <TimeseriesManager /> : <UserManager />}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-40 text-muted-foreground">
              <ShieldAlert className="w-16 h-16 mb-4 text-rose-500/60" />
              <h2 className="text-xl font-semibold text-foreground mb-2">Access Denied</h2>
              <p className="text-sm text-muted-foreground">This page is restricted to administrators.</p>
            </div>
          )}
        </div>
      </AppShell>
    </AuthGuard>
  );
}
