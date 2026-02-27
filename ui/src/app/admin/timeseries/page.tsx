'use client';

import { useEffect, useMemo, useState } from 'react';
import AuthGuard from '@/components/AuthGuard';
import TimeseriesManager from '@/components/TimeseriesManager';
import UserManager from '@/components/UserManager';
import RolePermissionsManager from '@/components/RolePermissionsManager';
import AppShell from '@/components/AppShell';
import NavigatorShell from '@/components/NavigatorShell';
import { useAuth } from '@/context/AuthContext';
import { Database, ShieldAlert, Users, Activity, Server, BarChart3, ShieldCheck } from 'lucide-react';
import { motion } from 'framer-motion';

type AdminTab = 'timeseries' | 'users' | 'permissions';

export default function AdminTimeseriesPage() {
  const { user } = useAuth();
  const isAdmin = !!user && (user.role === 'owner' || user.role === 'admin' || user.is_admin);
  const [activeTab, setActiveTab] = useState<AdminTab>('timeseries');
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const syncSidebarForViewport = () => {
      if (window.innerWidth < 1024) setSidebarOpen(false);
    };
    syncSidebarForViewport();
    window.addEventListener('resize', syncSidebarForViewport);
    return () => window.removeEventListener('resize', syncSidebarForViewport);
  }, []);

  const tabs = useMemo(
    () => [
      { id: 'timeseries' as const,  label: 'Timeseries',  icon: Database },
      { id: 'users' as const,       label: 'Users',        icon: Users },
      { id: 'permissions' as const, label: 'Permissions',  icon: ShieldCheck },
    ],
    []
  );

  return (
    <AuthGuard>
      <AppShell>
        {!isAdmin ? (
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
        ) : (
          <NavigatorShell
            sidebarOpen={sidebarOpen}
            onSidebarToggle={() => setSidebarOpen((o) => !o)}
            sidebarIcon={<Server className="w-3.5 h-3.5 text-sky-400" />}
            sidebarLabel="Admin"
            sidebarContent={
              <div className="min-h-0 flex-1 overflow-y-auto py-1 custom-scrollbar">
                {tabs.map((tab) => {
                  const Icon = tab.icon;
                  const active = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`w-full text-left px-2.5 py-1.5 transition-colors border-l-2 ${
                        active
                          ? 'border-l-sky-500/70 bg-sky-500/8 text-foreground'
                          : 'border-l-transparent hover:bg-foreground/5 text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        <Icon className="w-3.5 h-3.5" />
                        <span className="font-medium text-[12px] leading-tight">{tab.label}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            }
            topBarLeft={
              <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                <span className="text-sm font-semibold text-foreground">System Control</span>
                <span className="text-muted-foreground/30">·</span>
                <span>{user?.email}</span>
              </div>
            }
            topBarRight={
              <>
                <div className="px-2 py-1 rounded-md border border-border/60 text-[10px] text-muted-foreground inline-flex items-center gap-1.5">
                  <Activity className="w-3 h-3 text-emerald-400" />
                  <span>Online</span>
                </div>
                <div className="px-2 py-1 rounded-md border border-border/60 text-[10px] text-muted-foreground inline-flex items-center gap-1.5">
                  <BarChart3 className="w-3 h-3 text-sky-400" />
                  <span className="capitalize">{user?.role || 'Admin'}</span>
                </div>
              </>
            }
            mainClassName="p-3 md:p-4 lg:p-5"
          >
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              {activeTab === 'timeseries' && <TimeseriesManager />}
              {activeTab === 'users' && <UserManager />}
              {activeTab === 'permissions' && <RolePermissionsManager />}
            </motion.div>
          </NavigatorShell>
        )}
      </AppShell>
    </AuthGuard>
  );
}
