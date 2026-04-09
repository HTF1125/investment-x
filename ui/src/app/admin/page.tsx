'use client';

import { useState, useEffect } from 'react';
import AuthGuard from '@/components/auth/AuthGuard';
import TimeseriesManager from '@/components/admin/TimeseriesManager';
import UserManager from '@/components/admin/UserManager';
import AdminLogViewer from '@/components/admin/AdminLogViewer';
import ProjectStructure from '@/components/admin/ProjectStructure';
import DataToolsTab from '@/components/admin/DataToolsTab';
import CreditWatchlistTab from '@/components/admin/CreditWatchlistTab';
import AppShell from '@/components/layout/AppShell';
import { useAuth } from '@/context/AuthContext';
import { Database, ShieldAlert, Users, ScrollText, Terminal, FolderTree, FileSpreadsheet, Shield } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

type AdminTab = 'timeseries' | 'users' | 'logs' | 'data' | 'watchlist' | 'system';

const TABS: { id: AdminTab; label: string; icon: typeof Database; shortcut: string }[] = [
  { id: 'timeseries', label: 'Timeseries', icon: Database,        shortcut: '1' },
  { id: 'users',      label: 'Users',      icon: Users,           shortcut: '2' },
  { id: 'logs',       label: 'Logs',       icon: ScrollText,      shortcut: '3' },
  { id: 'data',       label: 'Data Tools',  icon: FileSpreadsheet, shortcut: '4' },
  { id: 'watchlist',  label: 'Watchlist',  icon: Shield,          shortcut: '5' },
  { id: 'system',     label: 'System',     icon: FolderTree,      shortcut: '6' },
];

export default function AdminPage() {
  const { user } = useAuth();
  const isAdmin = !!user && (user.role === 'owner' || user.role === 'admin' || user.is_admin);
  const [activeTab, setActiveTab] = useState<AdminTab>('timeseries');

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLSelectElement) return;
      const idx = parseInt(e.key, 10);
      if (idx >= 1 && idx <= TABS.length) {
        setActiveTab(TABS[idx - 1].id);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  return (
    <AuthGuard>
      <AppShell hideFooter>
        <div className="page-shell">
        {!isAdmin ? (
          <div className="flex-1 flex flex-col items-center justify-center px-4">
            <div className="max-w-sm w-full panel-card p-10 text-center">
              <div className="w-12 h-12 mx-auto mb-5 rounded-full bg-destructive/[0.08] border border-destructive/15 flex items-center justify-center">
                <ShieldAlert className="w-5 h-5 text-destructive/60" />
              </div>
              <h2 className="text-[15px] font-semibold text-foreground mb-2 tracking-tight">Access Denied</h2>
              <p className="text-[13px] text-muted-foreground/60 leading-relaxed mb-6">
                This area is restricted to administrators only.
              </p>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-[var(--radius)] bg-destructive/[0.08] border border-destructive/20 text-[11.5px] font-mono uppercase tracking-[0.08em] text-destructive/80">
                <span className="w-1.5 h-1.5 rounded-full bg-destructive/80 animate-pulse" />
                Unauthorized
              </div>
            </div>
          </div>
        ) : (
          <>
            {/* ── Header bar ── */}
            <div className="page-header">
              <Terminal className="w-3 h-3 text-muted-foreground" />
              <h1 className="page-header-title">ADMIN</h1>
              <div className="w-px h-3 bg-border/60" aria-hidden />
              <span className="text-[11px] font-mono text-muted-foreground truncate max-w-[240px]">{user?.email}</span>
              <div className="flex-1" />
              <span className="hidden sm:inline-flex h-5 items-center px-2 border border-border/60 text-[9.5px] font-mono uppercase tracking-[0.08em] text-muted-foreground">
                {user?.role || 'admin'}
              </span>
            </div>

            {/* ── Tab bar ── */}
            <div className="shrink-0 border-b border-border/40 px-3 sm:px-5 lg:px-6">
              <div className="flex items-center overflow-x-auto no-scrollbar">
                {TABS.map((tab, idx) => {
                  const Icon = tab.icon;
                  const active = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`relative flex items-center gap-1.5 whitespace-nowrap px-3 py-2.5 text-[10px] font-mono font-semibold uppercase tracking-[0.10em] transition-colors ${
                        active ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
                      } ${idx > 0 ? 'border-l border-border/30' : ''}`}
                    >
                      <Icon className="w-3 h-3" />
                      <span className="hidden sm:inline">{tab.label}</span>
                      <span className="sm:hidden">{tab.shortcut}</span>
                      {active && (
                        <motion.div
                          layoutId="admin-tab-underline"
                          className="absolute left-0 right-0 bottom-0 h-[2px] bg-accent"
                          transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                        />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* ── Tab content (scrollable) ── */}
            <div className="page-content">
              <div className="page-container">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={activeTab}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -4 }}
                    transition={{ duration: 0.15, ease: 'easeOut' }}
                  >
                    {activeTab === 'timeseries' && <TimeseriesManager />}
                    {activeTab === 'users' && <UserManager />}
                    {activeTab === 'logs' && <AdminLogViewer />}
                    {activeTab === 'data' && <DataToolsTab />}
                    {activeTab === 'watchlist' && <CreditWatchlistTab />}
                    {activeTab === 'system' && <ProjectStructure />}
                  </motion.div>
                </AnimatePresence>
              </div>
            </div>
          </>
        )}
        </div>
      </AppShell>
    </AuthGuard>
  );
}
