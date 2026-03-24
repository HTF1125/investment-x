'use client';

import { useState } from 'react';
import AuthGuard from '@/components/auth/AuthGuard';
import TimeseriesManager from '@/components/admin/TimeseriesManager';
import UserManager from '@/components/admin/UserManager';
import AdminLogViewer from '@/components/admin/AdminLogViewer';
import ProjectStructure from '@/components/admin/ProjectStructure';
import AppShell from '@/components/layout/AppShell';
import { useAuth } from '@/context/AuthContext';
import { Activity, Database, ShieldAlert, Users, ScrollText, Terminal, FolderTree } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

type AdminTab = 'timeseries' | 'users' | 'logs' | 'system';

const TABS: { id: AdminTab; label: string; icon: typeof Database; shortcut: string }[] = [
  { id: 'timeseries', label: 'Timeseries', icon: Database,    shortcut: '1' },
  { id: 'users',      label: 'Users',      icon: Users,       shortcut: '2' },
  { id: 'logs',       label: 'Logs',       icon: ScrollText,  shortcut: '3' },
  { id: 'system',     label: 'System',     icon: FolderTree,  shortcut: '4' },
];

export default function AdminTimeseriesPage() {
  const { user } = useAuth();
  const isAdmin = !!user && (user.role === 'owner' || user.role === 'admin' || user.is_admin);
  const [activeTab, setActiveTab] = useState<AdminTab>('timeseries');

  return (
    <AuthGuard>
      <AppShell>
        {!isAdmin ? (
          <div className="flex flex-col items-center justify-center min-h-[80vh] px-4">
            <div className="max-w-sm w-full panel-card p-10 text-center">
              <div className="w-12 h-12 mx-auto mb-5 rounded-full bg-destructive/[0.08] border border-destructive/15 flex items-center justify-center">
                <ShieldAlert className="w-5 h-5 text-destructive/60" />
              </div>
              <h2 className="text-[15px] font-semibold text-foreground mb-2 tracking-tight">Access Denied</h2>
              <p className="text-[12px] text-muted-foreground/60 leading-relaxed mb-6">
                This area is restricted to administrators only.
              </p>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-[var(--radius)] bg-destructive/[0.08] border border-destructive/20 text-[10px] font-mono uppercase tracking-[0.08em] text-destructive/80">
                <span className="w-1.5 h-1.5 rounded-full bg-destructive/80 animate-pulse" />
                Unauthorized
              </div>
            </div>
          </div>
        ) : (
          <div className="max-w-6xl mx-auto px-3 md:px-5 pt-3 pb-8">
            {/* ── Header row: title + status ─────────────────────────── */}
            <div className="flex items-center gap-3 mb-3">
              <div className="flex items-center gap-2">
                <Terminal className="w-3.5 h-3.5 text-primary/70" />
                <h1 className="text-[13px] font-semibold text-foreground tracking-tight">Admin</h1>
              </div>

              <div className="w-px h-3 bg-border/30" />
              <span className="text-[10px] font-mono text-muted-foreground/40 truncate max-w-[200px]">{user?.email}</span>

              <div className="flex-1" />

              {/* Status badges */}
              <div className="hidden sm:flex items-center gap-1.5">
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-[var(--radius)] border border-border/30 text-[9px] font-mono text-muted-foreground/40">
                  <Activity className="w-2 h-2 text-success/70" />
                  Online
                </span>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-[var(--radius)] border border-border/30 bg-foreground/[0.02] text-[9px] font-mono uppercase tracking-wider text-primary/60">
                  {user?.role || 'admin'}
                </span>
              </div>
            </div>

            {/* ── Tab bar ────────────────────────────────────────────── */}
            <div className="flex items-center gap-0.5 mb-4 border-b border-border/20 pb-px">
              {TABS.map((tab) => {
                const Icon = tab.icon;
                const active = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`
                      relative flex items-center gap-1.5 px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.06em]
                      transition-colors duration-150
                      ${active
                        ? 'text-primary'
                        : 'text-muted-foreground/40 hover:text-muted-foreground/70'
                      }
                    `}
                  >
                    <Icon className="w-3 h-3" />
                    <span>{tab.label}</span>
                    <span className="hidden sm:inline text-[8px] font-mono text-muted-foreground/20 ml-0.5 tabular-nums">{tab.shortcut}</span>

                    {/* Active underline */}
                    {active && (
                      <motion.div
                        layoutId="admin-tab-underline"
                        className="absolute bottom-0 left-0 right-0 h-[2px] bg-primary rounded-full"
                        transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                      />
                    )}
                  </button>
                );
              })}
            </div>

            {/* ── Tab content ────────────────────────────────────────── */}
            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.2, ease: 'easeOut' }}
              >
                {activeTab === 'timeseries' && <TimeseriesManager />}
                {activeTab === 'users' && <UserManager />}
                {activeTab === 'logs' && <AdminLogViewer />}
                {activeTab === 'system' && <ProjectStructure />}
              </motion.div>
            </AnimatePresence>
          </div>
        )}
      </AppShell>
    </AuthGuard>
  );
}
