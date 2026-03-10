'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Star, Maximize2, Eye, EyeOff,
  RefreshCw, Copy, Trash2, Pencil,
} from 'lucide-react';
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
  canEdit,
  canRefresh,
  canDelete,
  canManageVisibility,
  onToggleVisibility,
  onRefresh,
  onCopy,
  onDelete,
  isRefreshing,
  copySignal,
  onOpenSpotlight,
  isFavorite,
  onToggleFavorite,
}: ChartTileProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [isInView, setIsInView] = useState(false);

  // Viewport-based lazy rendering
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

  const handleExpand = useCallback(() => {
    onOpenSpotlight?.(chart.id);
  }, [chart.id, onOpenSpotlight]);

  return (
    <div
      ref={cardRef}
      className="group relative rounded-[var(--radius)] border border-border/30 bg-card overflow-hidden transition-all duration-200 hover:border-primary/25 hover:shadow-lg hover:shadow-black/[0.06] dark:hover:shadow-black/25"
    >
      {/* ── Header ── */}
      <div className="flex items-center gap-2 px-3 py-1.5 min-h-[32px]">
        <span className="text-[11px] font-medium text-foreground/80 truncate flex-1 leading-tight">
          {chart.name || 'Untitled'}
        </span>

        {chart.category && (
          <span className="text-[9px] font-mono text-muted-foreground/40 bg-primary/[0.04] px-1.5 py-0.5 rounded-[calc(var(--radius)-2px)] shrink-0 hidden sm:inline-block">
            {chart.category}
          </span>
        )}

        {/* Favorite — always visible */}
        {onToggleFavorite && (
          <button
            onClick={(e) => { e.stopPropagation(); onToggleFavorite(chart.id); }}
            className={`shrink-0 p-0.5 rounded transition-colors ${
              isFavorite
                ? 'text-amber-400 hover:text-amber-300'
                : 'text-transparent group-hover:text-muted-foreground/25 hover:!text-muted-foreground/60'
            }`}
            title={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
          >
            <Star className={`w-3 h-3 ${isFavorite ? 'fill-current' : ''}`} />
          </button>
        )}

        {/* Private indicator */}
        {canManageVisibility && chart.public === false && (
          <span className="shrink-0 text-muted-foreground/30" title="Private">
            <EyeOff className="w-3 h-3" />
          </span>
        )}
      </div>

      {/* ── Chart area ── */}
      <div
        className="relative h-[300px] cursor-pointer bg-background border-t border-border/15"
        onClick={handleExpand}
      >
        {isInView ? (
          <div className="w-full h-full p-1.5">
            <Chart
              id={chart.id}
              initialFigure={chart.figure}
              copySignal={copySignal}
              interactive={false}
            />
          </div>
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <div className="w-4 h-4 border-2 border-border/30 border-t-primary/40 rounded-full animate-spin" />
          </div>
        )}

        {/* ── Hover action bar ── */}
        <div className="absolute inset-x-0 bottom-0 flex items-center justify-center gap-1 pb-2 pt-6 bg-gradient-to-t from-background/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none group-hover:pointer-events-auto">
          <TileAction
            icon={<Maximize2 className="w-3.5 h-3.5" />}
            title="Expand"
            onClick={(e) => { e.stopPropagation(); handleExpand(); }}
          />
          {canEdit && (
            <TileAction
              icon={<Pencil className="w-3.5 h-3.5" />}
              title="Edit"
              onClick={(e) => { e.stopPropagation(); onOpenSpotlight?.(chart.id); }}
            />
          )}
          {canRefresh && (
            <TileAction
              icon={<RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />}
              title="Refresh"
              onClick={(e) => { e.stopPropagation(); onRefresh?.(chart.id); }}
              disabled={isRefreshing}
            />
          )}
          <TileAction
            icon={<Copy className="w-3.5 h-3.5" />}
            title="Copy as PNG"
            onClick={(e) => { e.stopPropagation(); onCopy?.(chart.id); }}
          />
          {canManageVisibility && (
            <TileAction
              icon={chart.public ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              title={chart.public ? 'Make Private' : 'Make Public'}
              onClick={(e) => { e.stopPropagation(); onToggleVisibility(chart.id, !chart.public); }}
            />
          )}
          {canDelete && (
            <TileAction
              icon={<Trash2 className="w-3.5 h-3.5" />}
              title="Delete"
              onClick={(e) => { e.stopPropagation(); onDelete?.(chart.id); }}
              variant="danger"
            />
          )}
        </div>
      </div>
    </div>
  );
});

/* ── Hover action button ── */
function TileAction({
  icon,
  title,
  onClick,
  disabled,
  variant,
}: {
  icon: React.ReactNode;
  title: string;
  onClick: (e: React.MouseEvent) => void;
  disabled?: boolean;
  variant?: 'danger';
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`w-7 h-7 rounded-[var(--radius)] backdrop-blur-sm flex items-center justify-center transition-colors disabled:opacity-40 ${
        variant === 'danger'
          ? 'bg-background/90 border border-rose-500/20 text-rose-400 hover:bg-rose-500/10 hover:border-rose-500/40'
          : 'bg-background/90 border border-border/40 text-muted-foreground hover:text-primary hover:bg-primary/10 hover:border-primary/25'
      }`}
    >
      {icon}
    </button>
  );
}

export default ChartTile;
