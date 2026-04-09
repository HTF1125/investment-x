'use client';

import { Loader2 } from 'lucide-react';
import type { TimeseriesMeta } from './types';

interface SearchDropdownProps {
  searchResults: TimeseriesMeta[] | undefined;
  searchLoading: boolean;
  searchQuery: string;
  selectedCodes: Set<string>;
  searchHighlight: number;
  onAddSeries: (code: string, name: string) => void;
}

export default function SearchDropdown({
  searchResults,
  searchLoading,
  searchQuery,
  selectedCodes,
  searchHighlight,
  onAddSeries,
}: SearchDropdownProps) {
  return (
    <div className="absolute left-1/2 -translate-x-1/2 top-full mt-1 bg-card border border-border/50 rounded-[var(--radius)] shadow-lg z-50 w-[500px] max-h-[340px] overflow-y-auto no-scrollbar">
      {/* Header */}
      <div className="flex items-center gap-0 px-3 py-1.5 border-b border-border/20 bg-foreground/[0.02] sticky top-0">
        <span className="flex-1 text-[9.5px] font-mono uppercase tracking-[0.1em] text-muted-foreground/40 font-semibold">Code</span>
        <span className="w-[140px] text-[9.5px] font-mono uppercase tracking-[0.1em] text-muted-foreground/40 font-semibold shrink-0">Name</span>
        <span className="w-[70px] text-[9.5px] font-mono uppercase tracking-[0.1em] text-muted-foreground/40 font-semibold shrink-0">Class</span>
        <span className="w-[50px] text-[9.5px] font-mono uppercase tracking-[0.1em] text-muted-foreground/40 font-semibold shrink-0">Source</span>
      </div>
      {searchLoading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-4 h-4 animate-spin text-primary/40" />
        </div>
      ) : searchResults && searchResults.length > 0 ? (
        (() => {
          let availIdx = -1;
          return searchResults.map((ts) => {
            const isAdded = selectedCodes.has(ts.code);
            if (!isAdded) availIdx++;
            const isHighlighted = !isAdded && availIdx === searchHighlight;
            return (
              <button
                key={ts.id}
                onClick={() => !isAdded && onAddSeries(ts.code, ts.name || ts.code)}
                className={`w-full text-left px-3 h-7 flex items-center transition-colors border-b border-border/8 last:border-0 ${
                  isAdded ? 'opacity-30 cursor-default' : 'cursor-pointer'
                } ${isHighlighted ? 'bg-primary/[0.08]' : isAdded ? '' : 'hover:bg-foreground/[0.03]'}`}
              >
                <div className="flex items-center gap-0 min-w-0 w-full">
                  <div className="flex-1 min-w-0 flex items-center gap-1">
                    {isAdded && <span className="text-[11px] text-success shrink-0">{'\u2713'}</span>}
                    <span className="text-[11.5px] font-mono font-medium text-foreground truncate">{ts.code}</span>
                  </div>
                  <span className="w-[140px] text-[11px] text-muted-foreground/40 truncate shrink-0">{ts.name && ts.name !== ts.code ? ts.name : ''}</span>
                  <span className="w-[70px] text-[11px] font-mono text-muted-foreground/40 truncate shrink-0">{ts.asset_class || ts.category || ''}</span>
                  <span className="w-[50px] text-[11px] font-mono text-muted-foreground/40 truncate shrink-0">{ts.source || ''}</span>
                </div>
              </button>
            );
          });
        })()
      ) : searchQuery.length >= 1 ? (
        <div className="py-6 text-center text-[12.5px] text-muted-foreground/40">No series found</div>
      ) : null}
    </div>
  );
}
