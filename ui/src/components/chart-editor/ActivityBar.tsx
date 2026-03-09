'use client';

import React from 'react';
import { Layout, Database, Settings } from 'lucide-react';
import type { ActiveTab } from '@/hooks/useChartEditor';

interface ActivityBarProps {
  activeTab: ActiveTab;
  libraryOpen: boolean;
  name: string;
  setActiveTab: (tab: ActiveTab) => void;
  setLibraryOpen: (open: boolean) => void;
}

export default function ActivityBar({
  activeTab,
  libraryOpen,
  name,
  setActiveTab,
  setLibraryOpen,
}: ActivityBarProps) {
  return (
    <aside className="hidden lg:flex w-12 shrink-0 flex-col items-center py-3 gap-1 bg-background border-r border-border/60 z-20">
      <button
        onClick={() => { setActiveTab('library'); setLibraryOpen(true); }}
        className={`p-2 rounded-md transition-all ${activeTab === 'library' && libraryOpen ? 'text-foreground bg-foreground/[0.08]' : 'text-muted-foreground/40 hover:text-muted-foreground hover:bg-foreground/[0.06]'}`}
        title="Library"
      >
        <Layout className="w-4 h-4" />
      </button>
      <button
        onClick={() => { setActiveTab('data'); setLibraryOpen(true); }}
        className={`p-2 rounded-md transition-all ${activeTab === 'data' && libraryOpen ? 'text-foreground bg-foreground/[0.08]' : 'text-muted-foreground/40 hover:text-muted-foreground hover:bg-foreground/[0.06]'}`}
        title="Variables & Data"
      >
        <Database className="w-4 h-4" />
      </button>
      <div className="mt-auto flex flex-col gap-1 items-center">
        <button
          onClick={() => { setActiveTab('settings'); setLibraryOpen(true); }}
          className={`p-2 rounded-md transition-all ${activeTab === 'settings' && libraryOpen ? 'text-foreground bg-foreground/[0.08]' : 'text-muted-foreground/40 hover:text-muted-foreground hover:bg-foreground/[0.06]'}`}
          title="Studio Settings"
        >
          <Settings className="w-4 h-4" />
        </button>
        <div className="w-7 h-7 rounded-md bg-foreground text-background flex items-center justify-center text-[10px] font-bold mb-2">
          {name.charAt(0)}
        </div>
      </div>
    </aside>
  );
}
