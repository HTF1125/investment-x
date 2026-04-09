'use client';

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import {
  Search, BarChart3, TrendingUp, Radio,
  Settings, ArrowRight, Activity, PenTool, LineChart,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { useFocusTrap } from '@/hooks/useFocusTrap';
import { useDebounce } from '@/hooks/useDebounce';

interface SearchItem {
  id: string;
  label: string;
  description?: string;
  icon: React.ReactNode;
  href: string;
  section: string;
}

const NAV_ITEMS: SearchItem[] = [
  { id: 'dashboard', label: 'Dashboard', description: 'Chart gallery & analytics', icon: <BarChart3 className="w-3.5 h-3.5" />, href: '/', section: 'Pages' },
  { id: 'chartpack', label: 'ChartPack', description: 'Chart packs & analysis', icon: <LineChart className="w-3.5 h-3.5" />, href: '/chartpack', section: 'Pages' },
  { id: 'research', label: 'Research', description: 'Research files, wartime & stress', icon: <Radio className="w-3.5 h-3.5" />, href: '/research', section: 'Pages' },
  { id: 'macro', label: 'Macro Outlook', description: 'Regime analysis & liquidity', icon: <TrendingUp className="w-3.5 h-3.5" />, href: '/macro', section: 'Pages' },
  { id: 'whiteboard', label: 'Whiteboard', description: 'Diagrams & visual thinking', icon: <PenTool className="w-3.5 h-3.5" />, href: '/whiteboard', section: 'Pages' },
  { id: 'admin', label: 'System Admin', description: 'Timeseries management', icon: <Settings className="w-3.5 h-3.5" />, href: '/admin', section: 'Pages' },
];

interface GlobalSearchPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function GlobalSearchPalette({ isOpen, onClose }: GlobalSearchPaletteProps) {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 150);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const focusTrapRef = useFocusTrap(isOpen, onClose);
  const router = useRouter();

  const chartItems: SearchItem[] = [];

  const items = useMemo(() => {
    const q = debouncedQuery.toLowerCase().trim();
    if (!q) return NAV_ITEMS;
    const allItems = [...NAV_ITEMS, ...chartItems];
    const matched = allItems.filter(item =>
      item.label.toLowerCase().includes(q) ||
      (item.description || '').toLowerCase().includes(q)
    );
    // Pages first, then Charts
    matched.sort((a, b) => {
      if (a.section === b.section) return 0;
      return a.section === 'Pages' ? -1 : 1;
    });
    return matched;
  }, [debouncedQuery, chartItems]);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIdx(0);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [isOpen]);

  useEffect(() => {
    if (selectedIdx >= items.length) setSelectedIdx(Math.max(0, items.length - 1));
  }, [items.length, selectedIdx]);

  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-idx="${selectedIdx}"]`) as HTMLElement | undefined;
    el?.scrollIntoView({ block: 'nearest' });
  }, [selectedIdx]);

  const executeItem = (item: SearchItem) => {
    router.push(item.href);
    onClose();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIdx(i => Math.min(i + 1, items.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIdx(i => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && items[selectedIdx]) {
      e.preventDefault();
      executeItem(items[selectedIdx]);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  // Build grouped sections for rendering
  const sections = useMemo(() => {
    const groups: { section: string; items: { item: SearchItem; globalIdx: number }[] }[] = [];
    let currentSection = '';
    items.forEach((item, idx) => {
      if (item.section !== currentSection) {
        currentSection = item.section;
        groups.push({ section: currentSection, items: [] });
      }
      groups[groups.length - 1].items.push({ item, globalIdx: idx });
    });
    return groups;
  }, [items]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-[300] flex items-start justify-center pt-[15vh] px-4 bg-black/50 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.1 }}
          onClick={onClose}
          role="dialog"
          aria-modal="true"
          aria-label="Search"
        >
          <motion.div
            ref={focusTrapRef}
            className="w-full max-w-md bg-card border border-border/40 rounded-xl shadow-lg shadow-black/20 overflow-hidden flex flex-col"
            initial={{ y: -8, scale: 0.98, opacity: 0 }}
            animate={{ y: 0, scale: 1, opacity: 1 }}
            exit={{ y: -6, scale: 0.98, opacity: 0 }}
            transition={{ duration: 0.12 }}
            onClick={e => e.stopPropagation()}
          >
            {/* Search input */}
            <div className="flex items-center gap-2 px-4 py-3 border-b border-border/25">
              <Search className="w-4 h-4 text-primary/40 shrink-0" />
              <input
                ref={inputRef}
                value={query}
                onChange={e => { setQuery(e.target.value); setSelectedIdx(0); }}
                onKeyDown={handleKeyDown}
                placeholder="Search pages and charts…"
                className="flex-1 bg-transparent text-sm outline-none text-foreground placeholder:text-muted-foreground/35 font-medium"
              />
              <kbd className="hidden sm:inline px-1.5 py-0.5 rounded border border-border/25 text-[9.5px] text-muted-foreground/30 font-mono">
                ESC
              </kbd>
            </div>

            {/* Results */}
            <div ref={listRef} className="max-h-[320px] overflow-y-auto py-1">
              {items.length === 0 ? (
                <div className="py-8 text-center text-xs text-muted-foreground/30 font-medium">No results</div>
              ) : (
                sections.map(group => (
                  <div key={group.section}>
                    {/* Section header — only show when there's a query and mixed sections */}
                    {debouncedQuery.trim() && sections.length > 1 && (
                      <div className="px-4 pt-2.5 pb-1 text-[11px] font-mono font-semibold uppercase tracking-[0.12em] text-muted-foreground/30">
                        {group.section}
                      </div>
                    )}
                    {group.items.map(({ item, globalIdx }) => (
                      <button
                        key={item.id}
                        data-idx={globalIdx}
                        onClick={() => executeItem(item)}
                        onMouseEnter={() => setSelectedIdx(globalIdx)}
                        className={`w-full text-left px-4 py-2.5 flex items-center gap-3 transition-colors duration-75 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/25 focus-visible:ring-inset ${
                          globalIdx === selectedIdx
                            ? 'bg-foreground/[0.08] text-foreground'
                            : 'text-muted-foreground hover:bg-foreground/[0.04]'
                        }`}
                      >
                        <div className={`w-7 h-7 rounded-[var(--radius)] flex items-center justify-center shrink-0 ${
                          globalIdx === selectedIdx ? 'bg-foreground/15 text-foreground' : 'bg-foreground/[0.05] text-muted-foreground/40'
                        }`}>
                          {item.icon}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-[13px] font-semibold truncate">{item.label}</div>
                          {item.description && (
                            <div className="text-[11.5px] text-muted-foreground/40 mt-0.5 truncate">{item.description}</div>
                          )}
                        </div>
                        {globalIdx === selectedIdx && (
                          <ArrowRight className="w-3 h-3 text-foreground/40 shrink-0" />
                        )}
                      </button>
                    ))}
                  </div>
                ))
              )}
            </div>

            {/* Footer */}
            <div className="px-4 py-2 border-t border-border/15 flex items-center gap-3 text-[11.5px] text-muted-foreground/40 font-mono">
              <span><kbd className="px-1 py-0.5 rounded border border-border/15 text-[9.5px]">&#8593;&#8595;</kbd> navigate</span>
              <span><kbd className="px-1 py-0.5 rounded border border-border/15 text-[9.5px]">&#8629;</kbd> go</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
