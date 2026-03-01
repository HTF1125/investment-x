'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { Newspaper, Clock, WifiOff, Sparkles, ChevronDown, Check, Filter } from 'lucide-react';

interface UnifiedNewsItem {
  id: string;
  source: string;
  source_name?: string | null;
  url?: string | null;
  title: string;
  summary?: string | null;
  published_at?: string | null;
  discovered_at: string;
  symbols: string[];
  meta: Record<string, unknown>;
}

const THEME_RULES: Array<{ theme: string; keywords: string[] }> = [
  { theme: 'AI / Tech', keywords: ['ai', 'artificial intelligence', 'semiconductor', 'chip', 'nvidia', 'software', 'cloud'] },
  { theme: 'Rates / Macro', keywords: ['fed', 'fomc', 'rate', 'inflation', 'cpi', 'treasury', 'bond', 'yield'] },
  { theme: 'Treasury Liquidity / TGA', keywords: ['tga', 'treasury general account', 'rpp', 'rrp', 'reverse repo', 'bill issuance', 'net liquidity', 'sofr', 'funding stress', 'repo market'] },
  { theme: 'Space Economy', keywords: ['space', 'satellite', 'spacex', 'nasa', 'launch', 'rocket', 'starlink', 'orbital', 'space force'] },
  { theme: 'Defense Spending', keywords: ['defense', 'defence', 'military', 'pentagon', 'dod', 'army', 'navy', 'air force', 'missile', 'munition', 'defense budget', 'aerospace defense'] },
  { theme: 'Energy / Commodities', keywords: ['oil', 'gas', 'crude', 'commodity', 'gold', 'copper', 'opec'] },
  { theme: 'Financials / Credit', keywords: ['bank', 'credit', 'loan', 'default', 'liquidity', 'financials'] },
  { theme: 'China / EM', keywords: ['china', 'emerging market', 'em ', 'yuan', 'renminbi', 'korea', 'india', 'brazil'] },
  { theme: 'Crypto', keywords: ['bitcoin', 'btc', 'ethereum', 'crypto', 'blockchain', 'etf'] },
];

function detectThemes(item: UnifiedNewsItem): string[] {
  const text = `${item.title || ''} ${item.summary || ''}`.toLowerCase();
  const matched: string[] = [];
  for (const rule of THEME_RULES) {
    if (rule.keywords.some((kw) => text.includes(kw))) matched.push(rule.theme);
  }
  return matched.length ? matched : ['General Market'];
}

export default function NewsFeed({ embedded }: { embedded?: boolean }) {
  const [mounted, setMounted] = useState(false);
  const [selectedThemes, setSelectedThemes] = useState<string[]>([]);
  const [filterOpen, setFilterOpen] = useState(false);
  const filterRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (filterRef.current && !filterRef.current.contains(event.target as Node)) {
        setFilterOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const { data = [], isLoading, isError } = useQuery<UnifiedNewsItem[]>({
    queryKey: ['news-feed', 'items'],
    queryFn: () => apiFetchJson<UnifiedNewsItem[]>('/api/news/items?limit=250'),
    staleTime: 60_000,
  });

  const allThemes = [...THEME_RULES.map((r) => r.theme), 'General Market'];
  const allSelected = selectedThemes.length === allThemes.length;
  
  const toggleTheme = (theme: string) => {
    if (selectedThemes.includes(theme)) {
      if (selectedThemes.length === 1 && !allSelected) return; 
      if (allSelected) {
        setSelectedThemes([theme]);
      } else {
        setSelectedThemes(prev => prev.filter(t => t !== theme));
      }
    } else {
      const next = [...selectedThemes, theme];
      setSelectedThemes(next.length === allThemes.length ? allThemes : next);
    }
  };

  const toggleAll = () => {
    if (allSelected) {
      setSelectedThemes([allThemes[0]]);
    } else {
      setSelectedThemes(allThemes);
    }
  };

  const rows = data
    .map((item) => ({ ...item, __themes: detectThemes(item) }))
    .filter((item) => {
      if (allSelected) return true;
      return item.__themes.some((t) => selectedThemes.includes(t));
    })
    .sort((a, b) => {
      const ad = new Date(a.published_at || a.discovered_at).getTime();
      const bd = new Date(b.published_at || b.discovered_at).getTime();
      return bd - ad;
    });

  useEffect(() => {
    setSelectedThemes(allThemes);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (isLoading) {
    return (
      <div className="h-32 border border-border/60 rounded-xl bg-background animate-pulse flex items-center justify-center text-muted-foreground text-sm">
        Loading intelligence feed…
      </div>
    );
  }

  if (isError) {
    return (
      <div className="border border-rose-500/20 rounded-xl bg-rose-500/[0.04] p-8 flex flex-col items-center gap-3 text-center">
        <WifiOff className="w-6 h-6 text-rose-400/50" />
        <p className="text-sm text-muted-foreground">Unable to load intelligence feed</p>
      </div>
    );
  }

  if (rows.length === 0) return null;

  const outer = embedded
    ? 'h-full flex flex-col min-h-0 overflow-hidden'
    : 'h-full border border-border/60 rounded-xl overflow-hidden bg-background flex flex-col min-h-0';

  return (
    <section className={outer}>
      <div className="px-3 pt-2.5 pb-2 border-b border-border/60 shrink-0 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-20">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Newspaper className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />
            <span className="text-xs font-semibold text-foreground">Intelligence Feed</span>
            <span className="text-muted-foreground/30 text-[11px]">·</span>
            <span className="text-[10px] text-muted-foreground/60">{rows.length} items</span>
          </div>
          <span className="hidden sm:inline-flex text-[10px] text-muted-foreground/50 uppercase tracking-wider font-mono items-center gap-1.5">
            <Sparkles className="w-3 h-3" />
            Chronological
          </span>
        </div>
        
        <div className="flex items-center gap-2 relative" ref={filterRef}>
          <button
            onClick={() => setFilterOpen(!filterOpen)}
            className={`flex items-center gap-1.5 h-7 px-2.5 rounded-md border text-[11px] font-medium transition-all ${
              filterOpen || !allSelected
                ? 'border-sky-500/40 bg-sky-500/5 text-sky-400'
                : 'border-border/60 bg-foreground/[0.03] text-muted-foreground hover:text-foreground hover:bg-foreground/[0.06]'
            }`}
          >
            <Filter className="w-3 h-3" />
            <span>Themes</span>
            <span className="text-muted-foreground/30">|</span>
            <span className="truncate max-w-[120px] sm:max-w-none">
              {allSelected ? 'All Themes' : selectedThemes.join(', ')}
            </span>
            <ChevronDown className={`w-3 h-3 ml-0.5 transition-transform duration-200 ${filterOpen ? 'rotate-180' : ''}`} />
          </button>

          {filterOpen && (
            <div className="absolute top-full left-0 mt-1.5 w-64 max-h-[80vh] overflow-y-auto p-1.5 rounded-xl border border-border bg-background shadow-2xl z-50 custom-scrollbar animate-in fade-in zoom-in duration-150">
              <button
                onClick={toggleAll}
                className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-[11px] font-medium text-foreground hover:bg-foreground/[0.06] transition-colors"
              >
                <span>All Themes</span>
                {allSelected && <Check className="w-3 h-3 text-sky-400" />}
              </button>
              <div className="h-px bg-border/60 my-1 mx-1" />
              {allThemes.map((theme) => {
                const isSelected = selectedThemes.includes(theme) && !allSelected;
                return (
                  <button
                    key={theme}
                    onClick={() => toggleTheme(theme)}
                    className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-[11px] font-medium text-muted-foreground hover:text-foreground hover:bg-foreground/[0.06] transition-colors"
                  >
                    <span className={isSelected ? 'text-sky-400' : ''}>{theme}</span>
                    {isSelected && <Check className="w-3 h-3 text-sky-400" />}
                  </button>
                );
              })}
            </div>
          )}
          
          {!allSelected && (
            <button
              onClick={() => setSelectedThemes(allThemes)}
              className="text-[10px] text-muted-foreground hover:text-foreground underline underline-offset-2 decoration-muted-foreground/30"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden custom-scrollbar">
        <div className="px-2 py-2 grid grid-cols-1 md:grid-cols-2 gap-2">
          {rows.slice(0, 120).map((item) => {
            const dt = item.published_at || item.discovered_at;
            return (
              <article
                key={item.id}
                className="px-3 py-2.5 rounded-lg border border-border/40 hover:bg-foreground/[0.02] transition-colors min-h-[112px]"
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-[10px] uppercase tracking-wider text-muted-foreground/70 font-medium truncate">
                    {item.source_name || item.source}
                  </span>
                  <span className="text-[10px] text-muted-foreground/60 tabular-nums inline-flex items-center gap-1 font-mono shrink-0">
                    <Clock className="w-3 h-3" />
                    {mounted ? new Date(dt).toLocaleString() : '─ ─'}
                  </span>
                </div>
                <div className="mb-1 flex flex-wrap gap-1">
                  {item.__themes.slice(0, 3).map((tag) => (
                    <span key={`${item.id}-${tag}`} className="text-[9px] px-1.5 py-0.5 rounded border border-border/60 text-muted-foreground/80">
                      {tag}
                    </span>
                  ))}
                </div>
                <a
                  href={item.url || '#'}
                  target={item.url ? '_blank' : undefined}
                  rel={item.url ? 'noreferrer' : undefined}
                  className="text-[12px] md:text-[13px] font-semibold text-foreground leading-snug hover:text-sky-300 transition-colors"
                >
                  {item.title}
                </a>
                {item.summary && (
                  <p className="mt-1 text-[11px] md:text-[12px] text-muted-foreground/85 line-clamp-2">
                    {item.summary}
                  </p>
                )}
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
