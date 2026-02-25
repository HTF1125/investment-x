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
      { id: 'timeseries' as const, label: 'Timeseries', icon: Database, description: 'Manage data sources' },
      { id: 'users' as const, label: 'Users', icon: Users, description: 'User management' },
    ],
    []
  );

  return (
    <AuthGuard>
      <AppShell>
        <div className="min-h-screen bg-gradient-to-br from-background via-background to-indigo-950/5">
          {isAdmin ? (
            <div className="max-w-[1800px] mx-auto p-4 md:p-6 lg:p-8 space-y-6">
              {/* Header Section */}
              <div className="relative overflow-hidden rounded-3xl border border-border/50 bg-gradient-to-br from-card/80 via-card/60 to-card/40 backdrop-blur-xl p-6 md:p-8 shadow-2xl">
                <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 via-transparent to-violet-500/5 pointer-events-none" />
                <div className="absolute -top-24 -right-24 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
                <div className="absolute -bottom-24 -left-24 w-64 h-64 bg-violet-500/10 rounded-full blur-3xl pointer-events-none" />

                <div className="relative z-10">
                  <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
                    <div>
                      <div className="flex items-center gap-3 mb-2">
                        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                          <Server className="w-6 h-6 text-white" />
                        </div>
                        <div>
                          <h1 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight">
                            System Control
                          </h1>
                          <p className="text-sm text-muted-foreground font-mono tracking-wider">
                            Admin Dashboard • {user?.email}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Quick Stats */}
                    <div className="flex flex-wrap gap-3">
                      <div className="px-4 py-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 backdrop-blur-sm">
                        <div className="flex items-center gap-2">
                          <Activity className="w-4 h-4 text-emerald-500" />
                          <div>
                            <div className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">Status</div>
                            <div className="text-sm font-bold text-emerald-700 dark:text-emerald-300">Online</div>
                          </div>
                        </div>
                      </div>
                      <div className="px-4 py-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 backdrop-blur-sm">
                        <div className="flex items-center gap-2">
                          <BarChart3 className="w-4 h-4 text-indigo-500" />
                          <div>
                            <div className="text-[10px] font-mono text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">Role</div>
                            <div className="text-sm font-bold text-indigo-700 dark:text-indigo-300 capitalize">{user?.role || 'Admin'}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Tab Navigation */}
                  <div className="flex flex-wrap items-center gap-2">
                    {tabs.map((tab) => {
                      const Icon = tab.icon;
                      const active = activeTab === tab.id;
                      return (
                        <button
                          key={tab.id}
                          onClick={() => setActiveTab(tab.id)}
                          className={`relative group px-5 py-3 rounded-xl text-sm font-semibold border transition-all duration-200 ${
                            active
                              ? 'bg-gradient-to-br from-indigo-500/20 to-violet-500/20 border-indigo-500/40 text-indigo-700 dark:text-indigo-300 shadow-lg shadow-indigo-500/10'
                              : 'bg-card/40 border-border/60 text-muted-foreground hover:text-foreground hover:bg-card/60 hover:border-border hover:shadow-md'
                          }`}
                        >
                          <div className="flex items-center gap-2.5">
                            <Icon className={`w-4 h-4 transition-transform ${active ? 'scale-110' : 'group-hover:scale-105'}`} />
                            <div className="text-left">
                              <div className="font-bold">{tab.label}</div>
                              <div className={`text-[10px] font-normal ${active ? 'text-indigo-600 dark:text-indigo-400' : 'text-muted-foreground'}`}>
                                {tab.description}
                              </div>
                            </div>
                          </div>
                          {active && (
                            <motion.div
                              layoutId="activeTab"
                              className="absolute inset-0 rounded-xl bg-gradient-to-br from-indigo-500/10 to-violet-500/10 -z-10"
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
              <div className="max-w-md w-full rounded-3xl border border-rose-500/20 bg-rose-500/5 backdrop-blur-sm p-12 text-center">
                <ShieldAlert className="w-20 h-20 mb-6 text-rose-500/60 mx-auto" />
                <h2 className="text-2xl font-bold text-foreground mb-3">Access Denied</h2>
                <p className="text-sm text-muted-foreground mb-6">
                  This page is restricted to administrators only. Please contact your system administrator if you believe you should have access.
                </p>
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs font-mono text-rose-600 dark:text-rose-400">
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
