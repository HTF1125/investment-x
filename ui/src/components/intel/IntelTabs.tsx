'use client';

import { BookOpen, Newspaper, MessageSquare, Shield, Activity, TrendingUp } from 'lucide-react';
import type { IntelTab } from '@/hooks/useIntelState';

const TABS: { key: IntelTab; label: string; shortLabel: string; icon: React.ReactNode }[] = [
  { key: 'research', label: 'Research', shortLabel: 'Research', icon: <BookOpen className="w-3.5 h-3.5" /> },
  { key: 'news', label: 'News Feed', shortLabel: 'News', icon: <Newspaper className="w-3.5 h-3.5" /> },
  { key: 'signals', label: 'Signals', shortLabel: 'Signals', icon: <MessageSquare className="w-3.5 h-3.5" /> },
  { key: 'positioning', label: 'Positioning', shortLabel: 'Pos', icon: <TrendingUp className="w-3.5 h-3.5" /> },
  { key: 'wartime', label: 'Wartime', shortLabel: 'War', icon: <Shield className="w-3.5 h-3.5" /> },
  { key: 'stress', label: 'Stress Test', shortLabel: 'Stress', icon: <Activity className="w-3.5 h-3.5" /> },
];

interface IntelTabsProps {
  activeTab: IntelTab;
  setActiveTab: (tab: IntelTab) => void;
}

export default function IntelTabs({ activeTab, setActiveTab }: IntelTabsProps) {
  return (
    <div className="px-4 sm:px-5 lg:px-6 border-b border-border/25 shrink-0">
      <div className="flex gap-0.5 overflow-x-auto no-scrollbar -mb-px">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`tab-link flex items-center gap-1.5 ${activeTab === tab.key ? 'active' : ''}`}
          >
            <span className="opacity-50">{tab.icon}</span>
            <span className="hidden sm:inline">{tab.label}</span>
            <span className="sm:hidden">{tab.shortLabel}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
