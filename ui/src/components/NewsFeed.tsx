'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { Newspaper, Clock, WifiOff, Sparkles, ChevronDown } from 'lucide-react';

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

export default function NewsFeed() {
  const [mounted, setMounted] = useState(false);
  const [themeDropdownOpen, setThemeDropdownOpen] = useState(false);
  const [selectedThemes, setSelectedThemes] = useState<string[]>([]);
  const dropdownRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  const { data = [], isLoading, isError } = useQuery<UnifiedNewsItem[]>({
    queryKey: ['news-feed', 'items'],
    queryFn: () => apiFetchJson<UnifiedNewsItem[]>('/api/news/items?limit=250'),
    staleTime: 60_000,
  });
  const allThemes = [...THEME_RULES.map((r) => r.theme), 'General Market'];
  const allSelected = selectedThemes.length === allThemes.length;
  const filterLabel = allSelected ? 'All' : `${selectedThemes.length}/${allThemes.length}`;
  const rows = data
    .map((item) => ({ ...item, __themes: detectThemes(item) }))
    .filter((item) => {
      if (allSelected || !selectedThemes.length) return true;
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

  useEffect(() => {
    const onPointerDown = (event: MouseEvent) => {
      if (!dropdownRef.current) return;
      if (!dropdownRef.current.contains(event.target as Node)) {
        setThemeDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
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

  return (
    <section className="h-full border border-border/60 rounded-xl overflow-hidden bg-background flex flex-col min-h-0">
      <div className="h-10 flex items-center justify-between px-3 border-b border-border/60 shrink-0">
        <div className="flex items-center gap-2">
          <Newspaper className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setThemeDropdownOpen((v) => !v)}
              className="h-6 px-2 rounded-md border border-border/60 inline-flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground hover:bg-foreground/[0.05]"
            >
              Themes {filterLabel}
              <ChevronDown className="w-3 h-3" />
            </button>
            {themeDropdownOpen && (
              <div className="absolute top-7 left-0 z-20 w-56 rounded-lg border border-border/70 bg-background shadow-xl p-2 space-y-1">
                <button
                  onClick={() => {
                    setSelectedThemes(allThemes);
                    setThemeDropdownOpen(false);
                  }}
                  className="w-full text-left text-[10px] px-2 py-1 rounded hover:bg-foreground/[0.05] text-muted-foreground"
                >
                  Select all
                </button>
                <div className="h-px bg-border/60 my-1" />
                {allThemes.map((theme) => {
                  const checked = selectedThemes.includes(theme);
                  return (
                    <label key={theme} className="flex items-center gap-2 px-2 py-1 rounded hover:bg-foreground/[0.04] cursor-pointer">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={(e) => {
                          if (e.target.checked) setSelectedThemes((prev) => [...prev, theme]);
                          else setSelectedThemes((prev) => prev.filter((t) => t !== theme));
                        }}
                      />
                            <span className="text-[10px] text-foreground/90">{theme}</span>
                          </label>
                  );
                })}
                <div className="h-px bg-border/60 my-1" />
                <button
                  onClick={() => setThemeDropdownOpen(false)}
                  className="w-full text-left text-[10px] px-2 py-1 rounded hover:bg-foreground/[0.05] text-muted-foreground"
                >
                  Done
                </button>
              </div>
            )}
          </div>
          <span className="text-xs font-semibold text-foreground">Recent News</span>
          <span className="text-muted-foreground/30 text-[11px]">·</span>
          <span className="text-[10px] text-muted-foreground/60">{rows.length} items</span>
        </div>
        <span className="text-[10px] text-muted-foreground/50 uppercase tracking-wider font-mono inline-flex items-center gap-1.5">
          <Sparkles className="w-3 h-3" />
          Chronological
        </span>
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
