'use client';

import React, { useEffect, useCallback, useState } from 'react';
import {
  X, ChevronLeft, ChevronRight, Star, Copy,
  Pencil, RefreshCw,
  Eye, EyeOff, Trash2, Loader2,
} from 'lucide-react';
import { motion } from 'framer-motion';
import dynamic from 'next/dynamic';
import Chart from '../Chart';
import type { ChartMeta } from '@/types/chart';

const CustomChartEditor = dynamic(() => import('../CustomChartEditor'), {
  ssr: false,
  loading: () => (
    <div className="flex-1 flex items-center justify-center text-muted-foreground/40">
      <Loader2 className="w-5 h-5 animate-spin" />
    </div>
  ),
});

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
  const [editing, setEditing] = useState(false);

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

  const handleToggleEdit = useCallback(() => {
    setEditing(prev => !prev);
  }, []);

  const handleEditorClose = useCallback(() => {
    setEditing(false);
  }, []);

  // Reset editing when navigating to a different chart
  useEffect(() => {
    setEditing(false);
  }, [chart.id]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      // Don't capture arrow keys / escape when editing (Monaco needs them)
      if (editing && e.key !== 'Escape') return;

      switch (e.key) {
        case 'Escape':
          e.preventDefault();
          if (editing) {
            setEditing(false);
          } else {
            onClose();
          }
          break;
        case 'ArrowLeft':
          e.preventDefault();
          goPrev();
          break;
        case 'ArrowRight':
          e.preventDefault();
          goNext();
          break;
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose, goPrev, goNext, editing]);

  const creatorLabel = chart.created_by_name || chart.created_by_email || '';

  return (
    <motion.div
      className="fixed inset-0 z-[250] flex items-center justify-center bg-black/60 backdrop-blur-sm"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      onClick={onClose}
    >
      <motion.div
        className={`flex flex-col bg-background rounded-lg border border-border/50 shadow-lg overflow-hidden ${
          editing
            ? 'w-screen h-[100dvh] sm:w-[98vw] sm:h-[94vh] sm:max-w-[1800px] sm:max-h-[960px] sm:rounded-lg rounded-none'
            : 'w-[95vw] h-[85vh] max-w-[960px] max-h-[640px]'
        }`}
        initial={{ scale: 0.96, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.96, opacity: 0 }}
        transition={{ duration: 0.15 }}
        onClick={(e: React.MouseEvent) => e.stopPropagation()}
      >
      {/* Top bar */}
      <div className="h-11 px-4 flex items-center justify-between border-b border-border/40 shrink-0">
        {/* Left: back + title */}
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <button
            onClick={onClose}
            className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-primary/10 transition-colors shrink-0"
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
                isFavorite ? 'text-warning' : 'text-muted-foreground/40 hover:text-muted-foreground'
              } hover:bg-primary/10`}
              title={isFavorite ? 'Remove favorite' : 'Add favorite'}
            >
              <Star className={`w-3.5 h-3.5 ${isFavorite ? 'fill-current' : ''}`} />
            </button>
          )}
          <button
            onClick={handleCopy}
            className="p-1.5 rounded-md text-muted-foreground/40 hover:text-muted-foreground hover:bg-primary/10 transition-colors"
            title="Copy as PNG"
          >
            <Copy className={`w-3.5 h-3.5 ${copied ? 'text-success' : ''}`} />
          </button>
          {canRefresh && (
            <button
              onClick={() => onRefresh?.(chart.id)}
              disabled={isRefreshing}
              className="p-1.5 rounded-md text-muted-foreground/40 hover:text-muted-foreground hover:bg-primary/10 transition-colors disabled:opacity-40"
              title="Refresh"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            </button>
          )}
          {canManageVisibility && onToggleVisibility && (
            <button
              onClick={() => onToggleVisibility(chart.id, !chart.public)}
              className="p-1.5 rounded-md text-muted-foreground/40 hover:text-muted-foreground hover:bg-primary/10 transition-colors"
              title={chart.public ? 'Make private' : 'Make public'}
            >
              {chart.public ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            </button>
          )}
          {canEdit && (
            <button
              onClick={handleToggleEdit}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-[10px] font-semibold transition-colors ${
                editing
                  ? 'border-primary/40 text-primary bg-primary/10'
                  : 'border-border/40 text-muted-foreground hover:text-foreground hover:border-primary/30 hover:bg-primary/10'
              }`}
              title={editing ? 'Close editor' : 'Edit chart code'}
            >
              <Pencil className="w-3 h-3" />
              {editing ? 'Close Editor' : 'Edit'}
            </button>
          )}
          {canDelete && (
            <button
              onClick={() => { onDelete?.(chart.id); onClose(); }}
              className="p-1.5 rounded-md text-muted-foreground/40 hover:text-destructive hover:bg-destructive/10 transition-colors"
              title="Delete"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Content area: chart only, or split editor + chart */}
      <div className={`flex-1 min-h-0 flex overflow-hidden ${editing ? 'flex-col sm:flex-row' : ''}`}>
        {/* Editor panel (left side, only when editing) */}
        {editing && (
          <div className="w-full sm:w-[60%] sm:min-w-[400px] sm:max-w-[1000px] shrink-0 border-r border-border/40 flex flex-col overflow-hidden">
            <CustomChartEditor
              mode="integrated"
              initialChartId={chart.id}
              onClose={handleEditorClose}
            />
          </div>
        )}

        {/* Chart area (right side, or full width) */}
        <div className="flex-1 min-w-0 relative p-3">
          <div className="w-full h-full overflow-hidden bg-card">
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
      </div>

      {/* Bottom bar — navigation + metadata */}
      <div className="h-10 px-4 flex items-center justify-between border-t border-border/40 shrink-0">
        <div className="flex items-center gap-2">
          <button
            onClick={goPrev}
            disabled={total <= 1}
            className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-primary/10 transition-colors disabled:opacity-30"
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
            className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-primary/10 transition-colors disabled:opacity-30"
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
            <kbd className="px-1 py-0.5 rounded border border-border/30 text-[8px]">Esc</kbd> close
          </span>
        </div>
      </div>
      </motion.div>
    </motion.div>
  );
}
