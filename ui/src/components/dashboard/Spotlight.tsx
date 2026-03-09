'use client';

import React, { useEffect, useCallback, useState } from 'react';
import {
  X, ChevronLeft, ChevronRight, Star, Copy,
  ExternalLink, RefreshCw, MoreHorizontal,
  Eye, EyeOff, Trash2,
} from 'lucide-react';
import { motion } from 'framer-motion';
import Chart from '../Chart';
import type { ChartMeta } from '@/types/chart';

interface SpotlightProps {
  chart: ChartMeta;
  charts: ChartMeta[]; // full filtered list for navigation
  currentIndex: number;
  onClose: () => void;
  onNavigate: (index: number) => void;
  // Actions
  canEdit: boolean;
  canRefresh: boolean;
  canDelete: boolean;
  canManageVisibility: boolean;
  onOpenStudio?: (chartId: string) => void;
  onCopy?: (chartId: string) => void;
  onRefresh?: (chartId: string) => void;
  onDelete?: (chartId: string) => void;
  onToggleVisibility?: (id: string, status: boolean) => void;
  isRefreshing?: boolean;
  copySignal?: number;
  isFavorite?: boolean;
  onToggleFavorite?: (id: string) => void;
}

export default function Spotlight({
  chart,
  charts,
  currentIndex,
  onClose,
  onNavigate,
  canEdit,
  canRefresh,
  canDelete,
  canManageVisibility,
  onOpenStudio,
  onCopy,
  onRefresh,
  onDelete,
  onToggleVisibility,
  isRefreshing,
  copySignal,
  isFavorite,
  onToggleFavorite,
}: SpotlightProps) {
  const total = charts.length;
  const [copied, setCopied] = useState(false);
  const [localCopySignal, setLocalCopySignal] = useState(copySignal || 0);

  const goPrev = useCallback(() => {
    onNavigate((currentIndex - 1 + total) % total);
  }, [currentIndex, total, onNavigate]);

  const goNext = useCallback(() => {
    onNavigate((currentIndex + 1) % total);
  }, [currentIndex, total, onNavigate]);

  const handleCopy = useCallback(() => {
    setLocalCopySignal(s => s + 1);
    onCopy?.(chart.id);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }, [chart.id, onCopy]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      switch (e.key) {
        case 'Escape':
          e.preventDefault();
          onClose();
          break;
        case 'ArrowLeft':
        case 'k':
          e.preventDefault();
          goPrev();
          break;
        case 'ArrowRight':
        case 'j':
          e.preventDefault();
          goNext();
          break;
        case 'e':
          if (canEdit) {
            e.preventDefault();
            onOpenStudio?.(chart.id);
            onClose();
          }
          break;
        case 'c':
          e.preventDefault();
          handleCopy();
          break;
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose, goPrev, goNext, canEdit, chart.id, onOpenStudio, handleCopy]);

  const creatorLabel = chart.created_by_name || chart.created_by_email || '';

  return (
    <motion.div
      className="fixed inset-0 z-[250] flex flex-col bg-background/95 backdrop-blur-xl"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
    >
      {/* Top bar */}
      <div className="h-11 px-4 flex items-center justify-between border-b border-border/40 shrink-0">
        {/* Left: back + title */}
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <button
            onClick={onClose}
            className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-foreground/[0.06] transition-colors shrink-0"
            title="Close (Esc)"
          >
            <X className="w-4 h-4" />
          </button>
          <h2 className="text-sm font-medium text-foreground truncate">
            {chart.name || 'Untitled'}
          </h2>
          {chart.category && (
            <span className="text-[10px] font-mono text-muted-foreground/50 shrink-0 hidden sm:inline">
              {chart.category}
            </span>
          )}
        </div>

        {/* Right: actions */}
        <div className="flex items-center gap-1 shrink-0">
          {onToggleFavorite && (
            <button
              onClick={() => onToggleFavorite(chart.id)}
              className={`p-1.5 rounded-md transition-colors ${
                isFavorite ? 'text-amber-400' : 'text-muted-foreground/40 hover:text-muted-foreground'
              } hover:bg-foreground/[0.06]`}
              title={isFavorite ? 'Remove favorite' : 'Add favorite'}
            >
              <Star className={`w-3.5 h-3.5 ${isFavorite ? 'fill-current' : ''}`} />
            </button>
          )}
          <button
            onClick={handleCopy}
            className="p-1.5 rounded-md text-muted-foreground/40 hover:text-muted-foreground hover:bg-foreground/[0.06] transition-colors"
            title="Copy as PNG (C)"
          >
            <Copy className={`w-3.5 h-3.5 ${copied ? 'text-emerald-400' : ''}`} />
          </button>
          {canRefresh && (
            <button
              onClick={() => onRefresh?.(chart.id)}
              disabled={isRefreshing}
              className="p-1.5 rounded-md text-muted-foreground/40 hover:text-muted-foreground hover:bg-foreground/[0.06] transition-colors disabled:opacity-40"
              title="Refresh"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            </button>
          )}
          {canManageVisibility && onToggleVisibility && (
            <button
              onClick={() => onToggleVisibility(chart.id, !chart.public)}
              className="p-1.5 rounded-md text-muted-foreground/40 hover:text-muted-foreground hover:bg-foreground/[0.06] transition-colors"
              title={chart.public ? 'Make private' : 'Make public'}
            >
              {chart.public ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            </button>
          )}
          {canEdit && (
            <button
              onClick={() => { onOpenStudio?.(chart.id); onClose(); }}
              className="p-1.5 rounded-md text-muted-foreground/40 hover:text-muted-foreground hover:bg-foreground/[0.06] transition-colors"
              title="Edit in Studio (E)"
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          )}
          {canDelete && (
            <button
              onClick={() => { onDelete?.(chart.id); onClose(); }}
              className="p-1.5 rounded-md text-muted-foreground/40 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
              title="Delete"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Chart area — full screen */}
      <div className="flex-1 min-h-0 relative p-3">
        <div className="w-full h-full rounded-xl overflow-hidden bg-card border border-border/40">
          <Chart
            key={chart.id}
            id={chart.id}
            initialFigure={chart.figure}
            copySignal={localCopySignal}
            interactive={true}
            scrollZoom={true}
          />
        </div>
      </div>

      {/* Bottom bar — navigation + metadata */}
      <div className="h-10 px-4 flex items-center justify-between border-t border-border/40 shrink-0">
        <div className="flex items-center gap-2">
          <button
            onClick={goPrev}
            disabled={total <= 1}
            className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-foreground/[0.06] transition-colors disabled:opacity-30"
            title="Previous (←)"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-[11px] font-mono text-muted-foreground/60 tabular-nums min-w-[4ch] text-center">
            {currentIndex + 1} / {total}
          </span>
          <button
            onClick={goNext}
            disabled={total <= 1}
            className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-foreground/[0.06] transition-colors disabled:opacity-30"
            title="Next (→)"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        <div className="flex items-center gap-4 text-[10px] font-mono text-muted-foreground/40">
          {creatorLabel && <span>by {creatorLabel}</span>}
          {chart.updated_at && (
            <span>
              Updated {new Date(chart.updated_at).toLocaleDateString()}
            </span>
          )}
          <span className="hidden sm:inline">
            <kbd className="px-1 py-0.5 rounded border border-border/30 text-[8px]">←→</kbd> navigate
            <span className="mx-1.5">·</span>
            <kbd className="px-1 py-0.5 rounded border border-border/30 text-[8px]">E</kbd> edit
            <span className="mx-1.5">·</span>
            <kbd className="px-1 py-0.5 rounded border border-border/30 text-[8px]">C</kbd> copy
            <span className="mx-1.5">·</span>
            <kbd className="px-1 py-0.5 rounded border border-border/30 text-[8px]">Esc</kbd> close
          </span>
        </div>
      </div>
    </motion.div>
  );
}
