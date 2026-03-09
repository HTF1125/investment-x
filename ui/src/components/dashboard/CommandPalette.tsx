'use client';

import React, { useState, useRef, useEffect, useMemo } from 'react';
import {
  Search, X, BarChart3, Zap, Plus, FileDown,
  RefreshCw, FileCode,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useFocusTrap } from '@/hooks/useFocusTrap';
import type { ChartMeta } from '@/types/chart';

interface ActionItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  onExecute: () => void;
  requiresOwner?: boolean;
}

interface CommandPaletteProps {
  charts: ChartMeta[];
  isOpen: boolean;
  onClose: () => void;
  onSelectChart: (chartId: string) => void;
  actions?: ActionItem[];
}

export default function CommandPalette({
  charts,
  isOpen,
  onClose,
  onSelectChart,
  actions = [],
}: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const focusTrapRef = useFocusTrap(isOpen, onClose);

  // Build combined results: charts + actions
  const items = useMemo(() => {
    const q = query.toLowerCase().trim();
    const matchingCharts = (q
      ? charts.filter(c =>
          `${c.name || ''}|${c.category || ''}|${c.description || ''}`.toLowerCase().includes(q)
        )
      : charts
    ).slice(0, 30).map(c => ({
      type: 'chart' as const,
      id: c.id,
      label: c.name || 'Untitled',
      sublabel: c.category || undefined,
      chart: c,
    }));

    const matchingActions = (q
      ? actions.filter(a => a.label.toLowerCase().includes(q))
      : actions
    ).map(a => ({
      type: 'action' as const,
      id: `action-${a.id}`,
      label: a.label,
      sublabel: undefined,
      action: a,
    }));

    // If searching, mix results. If not, show charts then actions.
    if (q) {
      return [...matchingCharts, ...matchingActions];
    }
    return [
      ...matchingActions.map(a => ({ ...a, section: 'Actions' })),
      ...matchingCharts.map(c => ({ ...c, section: 'Charts' })),
    ];
  }, [charts, actions, query]);

  // Reset state when opening
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

  const executeItem = (item: typeof items[0]) => {
    if (item.type === 'chart') {
      onSelectChart(item.chart!.id);
    } else if (item.type === 'action') {
      item.action!.onExecute();
    }
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

  // Global Cmd+K listener
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
        // Opening is handled by parent
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-[300] flex items-start justify-center pt-[12vh] px-4 bg-foreground/30 dark:bg-black/60 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.12 }}
          onClick={onClose}
          role="dialog"
          aria-modal="true"
          aria-labelledby="command-palette-title"
        >
          <motion.div
            ref={focusTrapRef}
            className="w-full max-w-lg bg-popover border border-border/60 rounded-xl shadow-2xl overflow-hidden flex flex-col"
            initial={{ y: -12, scale: 0.97, opacity: 0 }}
            animate={{ y: 0, scale: 1, opacity: 1 }}
            exit={{ y: -8, scale: 0.97, opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={e => e.stopPropagation()}
          >
            {/* Search input */}
<<<<<<< Updated upstream
            <h2 id="command-palette-title" className="sr-only">Search Charts</h2>
            <div className="flex items-center gap-2 px-3 py-2.5 border-b border-border/40">
              <Search className="w-4 h-4 text-muted-foreground/50 shrink-0" aria-hidden="true" />
=======
            <div className="flex items-center gap-2 px-3.5 py-3 border-b border-border/40">
              <Search className="w-4 h-4 text-muted-foreground/50 shrink-0" />
>>>>>>> Stashed changes
              <input
                ref={inputRef}
                value={query}
                onChange={e => { setQuery(e.target.value); setSelectedIdx(0); }}
                onKeyDown={handleKeyDown}
<<<<<<< Updated upstream
                placeholder="Search charts..."
                aria-label="Search charts"
=======
                placeholder="Search charts, actions..."
>>>>>>> Stashed changes
                className="flex-1 bg-transparent text-sm outline-none text-foreground placeholder:text-muted-foreground/40"
              />
              {query && (
                <button onClick={() => { setQuery(''); setSelectedIdx(0); }} className="text-muted-foreground/40 hover:text-muted-foreground" aria-label="Clear search">
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
              <kbd className="hidden sm:inline px-1.5 py-0.5 rounded border border-border/40 text-[9px] text-muted-foreground/40 font-mono">
                ESC
              </kbd>
            </div>

            {/* Results */}
<<<<<<< Updated upstream
            <div ref={listRef} className="max-h-[300px] overflow-y-auto py-1" role="listbox" aria-label="Chart results">
              {results.length === 0 ? (
                <div className="py-8 text-center text-xs text-muted-foreground/40" role="status">No charts found</div>
=======
            <div ref={listRef} className="max-h-[340px] overflow-y-auto py-1">
              {items.length === 0 ? (
                <div className="py-10 text-center text-xs text-muted-foreground/40">No results found</div>
>>>>>>> Stashed changes
              ) : (
                items.map((item, idx) => (
                  <button
<<<<<<< Updated upstream
                    key={chart.id}
                    role="option"
                    aria-selected={idx === selectedIdx}
                    onClick={() => { onSelect(chart.id); onClose(); }}
=======
                    key={item.id}
                    data-idx={idx}
                    onClick={() => executeItem(item)}
>>>>>>> Stashed changes
                    onMouseEnter={() => setSelectedIdx(idx)}
                    className={`w-full text-left px-3.5 py-2 flex items-center gap-3 transition-colors ${
                      idx === selectedIdx
                        ? 'bg-foreground/[0.07] text-foreground'
                        : 'text-muted-foreground hover:bg-foreground/[0.03]'
                    }`}
                  >
                    <div className="w-5 h-5 rounded flex items-center justify-center shrink-0 text-muted-foreground/40">
                      {item.type === 'chart' ? (
                        <BarChart3 className="w-3.5 h-3.5" />
                      ) : (
                        item.action?.icon || <Zap className="w-3.5 h-3.5" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-medium truncate">{item.label}</div>
                    </div>
                    {item.sublabel && (
                      <span className="text-[9px] font-mono text-muted-foreground/30 shrink-0">{item.sublabel}</span>
                    )}
                  </button>
                ))
              )}
            </div>

            {/* Footer */}
            <div className="px-3.5 py-1.5 border-t border-border/40 flex items-center gap-3 text-[9px] text-muted-foreground/30 font-mono">
              <span><kbd className="px-1 py-0.5 rounded border border-border/30 text-[8px]">↑↓</kbd> navigate</span>
              <span><kbd className="px-1 py-0.5 rounded border border-border/30 text-[8px]">↵</kbd> open</span>
              <span className="ml-auto">{items.length} results</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
