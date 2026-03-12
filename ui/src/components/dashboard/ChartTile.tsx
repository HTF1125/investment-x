'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Star, EyeOff, Copy, Check } from 'lucide-react';
import Chart from '../Chart';
import type { ChartMeta } from '@/types/chart';

export interface ChartTileProps {
  chart: ChartMeta;
  canEdit: boolean;
  canRefresh: boolean;
  canDelete: boolean;
  canManageVisibility: boolean;
  onToggleVisibility: (id: string, status: boolean) => void;
  onRefresh?: (id: string) => void;
  onCopy?: (id: string) => void;
  onDelete?: (id: string) => void;
  isRefreshing?: boolean;
  copySignal?: number;
  onOpenSpotlight?: (chartId: string) => void;
  isFavorite?: boolean;
  onToggleFavorite?: (id: string) => void;
}

const ChartTile = React.memo(function ChartTile({
  chart,
  canManageVisibility,
  onCopy,
  copySignal,
  onOpenSpotlight,
  isFavorite,
  onToggleFavorite,
}: ChartTileProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [isInView, setIsInView] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const el = cardRef.current;
    if (!el) return;
    if (typeof IntersectionObserver === 'undefined') { setIsInView(true); return; }
    const observer = new IntersectionObserver(
      ([entry]) => setIsInView(entry.isIntersecting),
      { rootMargin: '400px 0px 400px 0px', threshold: 0 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const handleClick = useCallback(() => {
    onOpenSpotlight?.(chart.id);
  }, [chart.id, onOpenSpotlight]);

  const handleCopy = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    onCopy?.(chart.id);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }, [chart.id, onCopy]);

  return (
    <div
      ref={cardRef}
      role="button"
      tabIndex={0}
      aria-label={`Open chart: ${chart.name || 'Untitled'}`}
      onClick={handleClick}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleClick(); } }}
      className="group relative panel-card overflow-hidden cursor-pointer transition-all duration-200 hover:border-primary/20 hover:shadow-md hover:shadow-black/[0.04] dark:hover:shadow-black/20 focus:outline-none focus:ring-2 focus:ring-primary/25 focus:ring-offset-1 focus:ring-offset-background"
    >
      {/* Chart area — full bleed, no interaction */}
      <div className="relative h-[260px] bg-background/50">
        {isInView ? (
          <div className="w-full h-full px-1 pt-1 pointer-events-none">
            <Chart
              id={chart.id}
              initialFigure={chart.figure}
              copySignal={copySignal}
              interactive={false}
            />
          </div>
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <div className="w-4 h-4 border-2 border-border/20 border-t-primary/30 rounded-full animate-spin" />
          </div>
        )}
        {/* Click overlay — ensures click always reaches the card */}
        <div className="absolute inset-0 z-10" />
      </div>

      {/* Footer — name + actions */}
      <div className="flex items-center gap-2 px-3 py-2 border-t border-border/15 min-h-[36px]">
        <div className="flex-1 min-w-0">
          <p className="text-[11px] font-medium text-foreground/80 truncate leading-tight">
            {chart.name || 'Untitled'}
          </p>
          {chart.category && (
            <p className="text-[9px] font-mono text-muted-foreground/30 mt-0.5 truncate">
              {chart.category}
            </p>
          )}
        </div>

        {/* Private indicator */}
        {canManageVisibility && chart.public === false && (
          <span className="shrink-0 text-muted-foreground/20" title="Private">
            <EyeOff className="w-3 h-3" />
          </span>
        )}

        {/* Copy */}
        <button
          onClick={handleCopy}
          className="shrink-0 p-1 rounded-[calc(var(--radius)-2px)] opacity-0 group-hover:opacity-100 text-muted-foreground/30 hover:text-foreground hover:bg-primary/[0.06] transition-all"
          title="Copy as PNG"
        >
          {copied ? (
            <Check className="w-3 h-3 text-emerald-400" />
          ) : (
            <Copy className="w-3 h-3" />
          )}
        </button>

        {/* Favorite */}
        {onToggleFavorite && (
          <button
            onClick={(e) => { e.stopPropagation(); onToggleFavorite(chart.id); }}
            className={`shrink-0 p-1 rounded-[calc(var(--radius)-2px)] transition-all ${
              isFavorite
                ? 'text-amber-400 hover:text-amber-300 opacity-100'
                : 'opacity-0 group-hover:opacity-100 text-muted-foreground/20 hover:text-amber-400 hover:bg-amber-500/[0.06]'
            }`}
            title={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
          >
            <Star className={`w-3 h-3 ${isFavorite ? 'fill-current' : ''}`} />
          </button>
        )}
      </div>
    </div>
  );
});

export default ChartTile;
