'use client';

import { useMemo, useState } from 'react';
import AuthGuard from '@/components/AuthGuard';
import TimeseriesManager from '@/components/TimeseriesManager';
import UserManager from '@/components/UserManager';
import AppShell from '@/components/AppShell';
import { useAuth } from '@/context/AuthContext';
import { Database, ShieldAlert, Users, Activity, Server, BarChart3 } from 'lucide-react';
import { motion } from 'framer-motion';

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
        <div className="min-h-screen bg-background">
          {isAdmin ? (
            <div className="max-w-[1800px] mx-auto p-3 md:p-4 lg:p-5 space-y-3">
              {/* Header Section */}
              <div className="rounded-xl border border-border/60 bg-background p-4 md:p-5">
                <div>
                  <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1.5">
                        <div className="w-9 h-9 rounded-lg bg-foreground/[0.08] border border-border/60 flex items-center justify-center">
                          <Server className="w-4 h-4 text-foreground" />
                        </div>
                        <div>
                          <h1 className="text-xl md:text-2xl font-semibold text-foreground tracking-tight">
                            System Control
                          </h1>
                          <p className="text-xs text-muted-foreground">
                            Admin Dashboard · {user?.email}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Quick Stats */}
                    <div className="flex flex-wrap gap-2">
                      <div className="px-3 py-2 rounded-lg bg-background border border-border/60">
                        <div className="flex items-center gap-2">
                          <Activity className="w-3.5 h-3.5 text-emerald-400" />
                          <div>
                            <div className="text-[10px] text-muted-foreground uppercase tracking-wider">Status</div>
                            <div className="text-xs font-semibold text-foreground">Online</div>
                          </div>
                        </div>
                      </div>
                      <div className="px-3 py-2 rounded-lg bg-background border border-border/60">
                        <div className="flex items-center gap-2">
                          <BarChart3 className="w-3.5 h-3.5 text-sky-400" />
                          <div>
                            <div className="text-[10px] text-muted-foreground uppercase tracking-wider">Role</div>
                            <div className="text-xs font-semibold text-foreground capitalize">{user?.role || 'Admin'}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Tab Navigation */}
                  <div className="flex flex-wrap items-center gap-1 p-1 rounded-lg border border-border/60 bg-background w-fit">
                    {tabs.map((tab) => {
                      const Icon = tab.icon;
                      const active = activeTab === tab.id;
                      return (
                        <button
                          key={tab.id}
                          onClick={() => setActiveTab(tab.id)}
                          className={`relative group px-3 py-1.5 rounded-md text-xs font-medium border transition-all duration-200 ${
                            active
                              ? 'bg-foreground/[0.08] border-border text-foreground'
                              : 'bg-transparent border-transparent text-muted-foreground hover:text-foreground hover:bg-foreground/[0.04]'
                          }`}
                        >
                          <div className="flex items-center gap-1.5">
                            <Icon className="w-3.5 h-3.5" />
                            <div className="text-left leading-none">
                              <div>{tab.label}</div>
                            </div>
                          </div>
                          {active && (
                            <motion.div
                              layoutId="activeTab"
                              className="absolute inset-0 rounded-md bg-foreground/[0.05] -z-10"
                              transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
                            />
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Content Section */}
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                {activeTab === 'timeseries' ? <TimeseriesManager /> : <UserManager />}
              </motion.div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center min-h-[80vh] text-muted-foreground px-4">
              <div className="max-w-md w-full rounded-xl border border-border/60 bg-background p-10 text-center">
                <ShieldAlert className="w-16 h-16 mb-5 text-rose-500/70 mx-auto" />
                <h2 className="text-xl font-semibold text-foreground mb-2">Access Denied</h2>
                <p className="text-sm text-muted-foreground mb-6">
                  This page is restricted to administrators only. Please contact your system administrator if you believe you should have access.
                </p>
                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md bg-rose-500/10 border border-rose-500/30 text-xs text-rose-400">
                  <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
                  Unauthorized Access Attempt
                </div>
              </div>
            </div>
          )}
        </div>
      </AppShell>
    </AuthGuard>
  );
}
