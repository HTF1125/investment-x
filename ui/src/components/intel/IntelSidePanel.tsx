'use client';

import { useState } from 'react';
import { X, Newspaper, MessageSquare } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import NewsFeed from '@/components/NewsFeed';
import TelegramFeed from '@/components/TelegramFeed';
import type { IntelState } from '@/hooks/useIntelState';

interface IntelSidePanelProps {
  state: IntelState;
}

function PanelTabs({
  activeTab,
  setActiveTab,
}: {
  activeTab: 'news' | 'signals';
  setActiveTab: (tab: 'news' | 'signals') => void;
}) {
  return (
    <div className="flex items-center gap-1">
      <button
        onClick={() => setActiveTab('news')}
        className={`flex items-center gap-1 text-[11px] font-medium px-2 py-1 rounded-md transition-colors ${
          activeTab === 'news'
            ? 'bg-primary/10 text-primary'
            : 'text-muted-foreground hover:text-foreground hover:bg-primary/[0.06]'
        }`}
      >
        <Newspaper className="w-3 h-3" />
        News
      </button>
      <button
        onClick={() => setActiveTab('signals')}
        className={`flex items-center gap-1 text-[11px] font-medium px-2 py-1 rounded-md transition-colors ${
          activeTab === 'signals'
            ? 'bg-primary/10 text-primary'
            : 'text-muted-foreground hover:text-foreground hover:bg-primary/[0.06]'
        }`}
      >
        <MessageSquare className="w-3 h-3" />
        Signals
      </button>
    </div>
  );
}

function PanelContent({ tab }: { tab: 'news' | 'signals' }) {
  return tab === 'news' ? <NewsFeed embedded /> : <TelegramFeed embedded />;
}

export default function IntelSidePanel({ state }: IntelSidePanelProps) {
  const { sidePanelOpen, toggleSidePanel, sidePanelTab, setSidePanelTab } = state;

  return (
    <>
      {/* Desktop side panel */}
      <aside
        className={`
          hidden md:flex flex-col shrink-0
          border-l border-border/30 bg-card/40
          transition-all duration-200 ease-out overflow-hidden
          ${sidePanelOpen ? 'w-[360px]' : 'w-0'}
        `}
      >
        {sidePanelOpen && (
          <>
            {/* Panel header */}
            <div className="h-9 px-3 border-b border-border/25 flex items-center justify-between shrink-0">
              <PanelTabs activeTab={sidePanelTab} setActiveTab={setSidePanelTab} />
              <button
                onClick={toggleSidePanel}
                className="btn-icon"
                aria-label="Close panel"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Panel body */}
            <div className="flex-1 min-h-0 overflow-hidden">
              <PanelContent tab={sidePanelTab} />
            </div>
          </>
        )}
      </aside>

      {/* Mobile bottom sheet */}
      <AnimatePresence>
        {sidePanelOpen && (
          <div className="md:hidden fixed inset-0 z-[80]">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="absolute inset-0 bg-black/30"
              onClick={toggleSidePanel}
            />

            {/* Sheet */}
            <motion.div
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ type: 'spring', damping: 28, stiffness: 300 }}
              className="absolute bottom-0 left-0 right-0 max-h-[70vh] bg-card rounded-t-xl border-t border-border/40 flex flex-col overflow-hidden"
            >
              {/* Drag handle */}
              <div className="flex justify-center py-2 shrink-0">
                <div className="w-8 h-1 rounded-full bg-muted-foreground/20" />
              </div>

              {/* Sheet header */}
              <div className="px-3 pb-2 flex items-center justify-between shrink-0">
                <PanelTabs activeTab={sidePanelTab} setActiveTab={setSidePanelTab} />
                <button
                  onClick={toggleSidePanel}
                  className="btn-icon"
                  aria-label="Close panel"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Sheet body */}
              <div className="flex-1 min-h-0 overflow-hidden border-t border-border/25">
                <PanelContent tab={sidePanelTab} />
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}
