import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { X, ChevronUp, ChevronDown, Loader2, FileText, Presentation } from 'lucide-react';
import { apiFetchJson } from '@/lib/api';
import type { PackSummary, PackDetail, FlashMessage } from './types';
import type { Slide } from './ReportEditor';

interface Props {
  myPacks: PackSummary[];
  publishedPacks: PackSummary[];
  isLight: boolean;
  onClose: () => void;
  onFlash: (msg: FlashMessage) => void;
  onOpenEditor: (slides: Slide[]) => void;
}

export default function ReportModal({ myPacks, publishedPacks, isLight, onClose, onFlash, onOpenEditor }: Props) {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [generating, setGenerating] = useState(false);
  const [loadingEditor, setLoadingEditor] = useState(false);

  // Deduplicate: published packs that aren't in myPacks
  const myIds = new Set(myPacks.map(p => p.id));
  const otherPublished = publishedPacks.filter(p => !myIds.has(p.id));

  const busy = generating || loadingEditor;

  const toggle = (id: string) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id],
    );
  };

  const moveUp = (id: string) => {
    setSelectedIds(prev => {
      const idx = prev.indexOf(id);
      if (idx <= 0) return prev;
      const next = [...prev];
      [next[idx - 1], next[idx]] = [next[idx], next[idx - 1]];
      return next;
    });
  };

  const moveDown = (id: string) => {
    setSelectedIds(prev => {
      const idx = prev.indexOf(id);
      if (idx < 0 || idx >= prev.length - 1) return prev;
      const next = [...prev];
      [next[idx], next[idx + 1]] = [next[idx + 1], next[idx]];
      return next;
    });
  };

  // ── Quick PDF export ──
  const handleGenerate = async () => {
    if (selectedIds.length === 0 || busy) return;
    setGenerating(true);
    try {
      const res = await fetch('/api/chart-packs/report', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pack_ids: selectedIds, theme: 'light' }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail || 'Report generation failed');
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `InvestmentX_PackReport_${new Date().toISOString().slice(0, 10)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      onFlash({ type: 'success', text: 'Report downloaded' });
      onClose();
    } catch (err: any) {
      onFlash({ type: 'error', text: err?.message || 'Report generation failed' });
    } finally {
      setGenerating(false);
    }
  };

  // ── Open editor: fetch pack details → flatten into slides ──
  const handleOpenEditor = async () => {
    if (selectedIds.length === 0 || busy) return;
    setLoadingEditor(true);
    try {
      // Fetch full pack details for each selected pack (in order)
      const packDetails = await Promise.all(
        selectedIds.map(id =>
          apiFetchJson<PackDetail>(`/api/chart-packs/${id}`)
        ),
      );

      // Flatten into slides
      let slideCounter = 0;
      const slides: Slide[] = [];
      for (const pack of packDetails) {
        const activeCharts = (pack.charts || []).filter((c: any) => !c.deleted);
        for (const chart of activeCharts) {
          // Only include charts with a renderable figure
          const figure = chart.figure || null;
          if (!figure) continue;
          slides.push({
            id: `slide-${slideCounter++}`,
            title: chart.title || chart.name || '',
            narrative: '',
            figure,
            packName: pack.name,
          });
        }
      }

      if (slides.length === 0) {
        onFlash({ type: 'error', text: 'No renderable charts found in selected packs' });
        return;
      }

      onOpenEditor(slides);
    } catch (err: any) {
      onFlash({ type: 'error', text: err?.message || 'Failed to load pack data' });
    } finally {
      setLoadingEditor(false);
    }
  };

  const allPacks = [...myPacks, ...otherPublished];
  const packMap = new Map(allPacks.map(p => [p.id, p]));

  const renderPackRow = (p: PackSummary) => {
    const isSelected = selectedIds.includes(p.id);
    const order = isSelected ? selectedIds.indexOf(p.id) + 1 : null;
    return (
      <button
        key={p.id}
        onClick={() => !busy && toggle(p.id)}
        className={`w-full text-left px-3 py-2.5 rounded-[var(--radius)] flex items-center gap-2 transition-all ${
          isSelected
            ? 'bg-primary/[0.08] border border-primary/20 text-foreground'
            : 'border border-transparent hover:bg-foreground/[0.03] hover:border-border/20'
        }`}
        disabled={busy}
      >
        {/* Order number / checkbox */}
        <span className={`w-5 h-5 rounded-[4px] flex items-center justify-center shrink-0 text-[11.5px] font-mono font-bold ${
          isSelected
            ? 'bg-primary/20 text-primary border border-primary/30'
            : 'border border-border/40 text-muted-foreground/20'
        }`}>
          {order || ''}
        </span>

        <FileText className="w-3 h-3 text-primary/30 shrink-0" />
        <span className="text-[13px] font-medium text-foreground truncate flex-1">{p.name}</span>
        <span className="text-[11.5px] font-mono text-muted-foreground/30 tabular-nums shrink-0">
          {p.chart_count}
        </span>

        {/* Reorder buttons */}
        {isSelected && (
          <span className="flex flex-col shrink-0" onClick={e => e.stopPropagation()}>
            <button
              onClick={() => moveUp(p.id)}
              disabled={busy || selectedIds.indexOf(p.id) === 0}
              className="p-0.5 text-muted-foreground/40 hover:text-foreground disabled:opacity-20 transition-colors"
              aria-label="Move up"
            >
              <ChevronUp className="w-3 h-3" />
            </button>
            <button
              onClick={() => moveDown(p.id)}
              disabled={busy || selectedIds.indexOf(p.id) === selectedIds.length - 1}
              className="p-0.5 text-muted-foreground/40 hover:text-foreground disabled:opacity-20 transition-colors"
              aria-label="Move down"
            >
              <ChevronDown className="w-3 h-3" />
            </button>
          </span>
        )}
      </button>
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={() => !busy && onClose()}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.96, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.96, y: 8 }}
        transition={{ duration: 0.2 }}
        className="rounded-[var(--radius)] border border-border/40 bg-card shadow-lg w-[440px] mx-4 flex flex-col max-h-[80vh]"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-5 pb-1">
          <div>
            <h3 className="text-[14px] font-semibold text-foreground">Report Builder</h3>
            <p className="text-[12.5px] text-muted-foreground/40 mt-0.5">
              Select packs, then edit slides or quick-export
            </p>
          </div>
          <button onClick={onClose} className="btn-icon" aria-label="Close" disabled={busy}>
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Pack list */}
        <div className="flex-1 overflow-y-auto no-scrollbar px-5 py-3 space-y-3">
          {myPacks.length > 0 && (
            <div>
              <label className="stat-label block mb-1.5">My Packs</label>
              <div className="space-y-px">
                {myPacks.map(renderPackRow)}
              </div>
            </div>
          )}
          {otherPublished.length > 0 && (
            <div>
              <label className="stat-label block mb-1.5">Published</label>
              <div className="space-y-px">
                {otherPublished.map(renderPackRow)}
              </div>
            </div>
          )}
          {allPacks.length === 0 && (
            <div className="text-center py-8">
              <p className="text-[13px] text-muted-foreground/40">No packs available.</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 pb-5 pt-3 border-t border-border/20 space-y-3">
          {/* Selected summary */}
          {selectedIds.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {selectedIds.map((id, i) => {
                const p = packMap.get(id);
                return (
                  <span key={id} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-[4px] bg-primary/[0.06] border border-primary/15 text-[11.5px] font-mono text-primary">
                    <span className="font-bold">{i + 1}.</span>
                    <span className="truncate max-w-[120px]">{p?.name || 'Pack'}</span>
                  </span>
                );
              })}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-2">
            <div className="flex-1" />

            <button
              onClick={handleGenerate}
              disabled={selectedIds.length === 0 || busy}
              className="btn-toolbar"
              title="Quick export as PDF"
            >
              {generating ? <Loader2 className="w-3 h-3 animate-spin" /> : <FileText className="w-3 h-3" />}
              <span>PDF</span>
            </button>
            <button
              onClick={handleOpenEditor}
              disabled={selectedIds.length === 0 || busy}
              className="btn-primary"
              title="Open slide editor"
            >
              {loadingEditor ? (
                <>
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Loading...
                </>
              ) : (
                <>
                  <Presentation className="w-3 h-3" />
                  Edit &amp; Export
                </>
              )}
            </button>
          </div>
          {busy && (
            <p className="text-[11.5px] text-muted-foreground/30 text-center">
              {generating ? 'Generating PDF...' : 'Loading pack data...'}
            </p>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}
