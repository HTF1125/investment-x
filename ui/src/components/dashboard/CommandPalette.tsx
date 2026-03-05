'use client';

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Search, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { ChartMeta } from '@/types/chart';

interface CommandPaletteProps {
  charts: ChartMeta[];
  isOpen: boolean;
  onClose: () => void;
  onSelect: (chartId: string) => void;
}

export default function CommandPalette({ charts, isOpen, onClose, onSelect }: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const results = useMemo(() => {
    if (!query.trim()) return charts.slice(0, 50);
    const q = query.toLowerCase();
    return charts
      .filter(c => `${c.name || ''}|${c.category || ''}|${c.description || ''}`.toLowerCase().includes(q))
      .slice(0, 50);
  }, [charts, query]);

  // Reset state when opening
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIdx(0);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [isOpen]);

  // Keep selectedIdx in range
  useEffect(() => {
    if (selectedIdx >= results.length) setSelectedIdx(Math.max(0, results.length - 1));
  }, [results.length, selectedIdx]);

  // Scroll selected item into view
  useEffect(() => {
    const el = listRef.current?.children[selectedIdx] as HTMLElement | undefined;
    el?.scrollIntoView({ block: 'nearest' });
  }, [selectedIdx]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIdx(i => Math.min(i + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIdx(i => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && results[selectedIdx]) {
      e.preventDefault();
      onSelect(results[selectedIdx].id);
      onClose();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-[300] flex items-start justify-center pt-[15vh] px-4 bg-foreground/40 dark:bg-black/60 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          onClick={onClose}
        >
          <motion.div
            className="w-full max-w-lg bg-popover border border-border/60 rounded-xl shadow-2xl overflow-hidden flex flex-col"
            initial={{ y: -8, scale: 0.97, opacity: 0 }}
            animate={{ y: 0, scale: 1, opacity: 1 }}
            exit={{ y: -8, scale: 0.97, opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={e => e.stopPropagation()}
          >
            {/* Search input */}
            <div className="flex items-center gap-2 px-3 py-2.5 border-b border-border/40">
              <Search className="w-4 h-4 text-muted-foreground/50 shrink-0" />
              <input
                ref={inputRef}
                value={query}
                onChange={e => { setQuery(e.target.value); setSelectedIdx(0); }}
                onKeyDown={handleKeyDown}
                placeholder="Search charts..."
                className="flex-1 bg-transparent text-sm outline-none text-foreground placeholder:text-muted-foreground/40"
              />
              {query && (
                <button onClick={() => { setQuery(''); setSelectedIdx(0); }} className="text-muted-foreground/40 hover:text-muted-foreground">
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Results */}
            <div ref={listRef} className="max-h-[300px] overflow-y-auto py-1">
              {results.length === 0 ? (
                <div className="py-8 text-center text-xs text-muted-foreground/40">No charts found</div>
              ) : (
                results.map((chart, idx) => (
                  <button
                    key={chart.id}
                    onClick={() => { onSelect(chart.id); onClose(); }}
                    onMouseEnter={() => setSelectedIdx(idx)}
                    className={`w-full text-left px-3 py-2 flex items-center gap-3 transition-colors ${
                      idx === selectedIdx
                        ? 'bg-foreground/[0.07] text-foreground'
                        : 'text-muted-foreground hover:bg-foreground/[0.04]'
                    }`}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-medium truncate">{chart.name || 'Untitled'}</div>
                    </div>
                    {chart.category && (
                      <span className="text-[9px] font-mono text-muted-foreground/40 shrink-0">{chart.category}</span>
                    )}
                  </button>
                ))
              )}
            </div>

            {/* Footer hints */}
            <div className="px-3 py-1.5 border-t border-border/40 flex items-center gap-3 text-[9px] text-muted-foreground/40 font-mono">
              <span><kbd className="px-1 py-0.5 rounded border border-border/40 text-[8px]">↑↓</kbd> navigate</span>
              <span><kbd className="px-1 py-0.5 rounded border border-border/40 text-[8px]">↵</kbd> select</span>
              <span><kbd className="px-1 py-0.5 rounded border border-border/40 text-[8px]">esc</kbd> close</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
