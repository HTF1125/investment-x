import React, { useCallback, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronLeft, Edit3, Check, X, Plus, Globe, Lock, RefreshCw,
  Clock, LineChart, Loader2,
} from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import ChartEditOverlay from './ChartEditOverlay';
import PackChartGrid from './PackChartGrid';
import ConfirmDialog from './ConfirmDialog';
import type { PackDetail, PackSummary, ChartConfig, FlashMessage } from './types';
import { relativeTime } from './types';

// ── Skeleton ──

function DetailSkeleton() {
  return (
    <div className="h-[calc(100vh-56px)] flex flex-col bg-background">
      {/* Header skeleton */}
      <div className="shrink-0 section-header h-12 px-4 gap-3">
        <div className="h-3 w-12 bg-foreground/[0.06] rounded-[var(--radius)] animate-pulse" />
        <div className="w-px h-5 bg-border/20" />
        <div className="h-4 w-40 bg-foreground/[0.06] rounded-[var(--radius)] animate-pulse" />
        <div className="ml-auto flex gap-2">
          <div className="h-8 w-20 bg-foreground/[0.04] rounded-[var(--radius)] animate-pulse" />
          <div className="h-8 w-8 bg-foreground/[0.04] rounded-[var(--radius)] animate-pulse" />
        </div>
      </div>
      {/* Grid skeleton */}
      <div className="flex-1 p-3">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-3" style={{ gridAutoRows: 'clamp(260px, 30vh, 340px)' }}>
          {Array.from({ length: 6 }, (_, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: i * 0.05 }}
              className="rounded-[var(--radius)] border border-border/30 bg-card overflow-hidden flex flex-col"
            >
              <div className="px-3 pt-2.5 pb-2 border-b border-border/20">
                <div className="h-3.5 w-3/4 bg-foreground/[0.06] rounded-[var(--radius)] animate-pulse" />
                <div className="flex gap-1.5 mt-2">
                  <div className="h-2.5 w-14 bg-foreground/[0.04] rounded-[var(--radius)] animate-pulse" />
                  <div className="h-2.5 w-14 bg-foreground/[0.04] rounded-[var(--radius)] animate-pulse" />
                </div>
              </div>
              <div className="flex-1 bg-foreground/[0.02] animate-pulse" />
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Props ──

interface Props {
  activePack: PackDetail | undefined;
  activePackId: string;
  isPackLoading: boolean;
  user: any;
  packs: PackSummary[] | undefined;
  isLight: boolean;
  onBack: () => void;
  onFlash: (msg: FlashMessage) => void;
  refetchPack: () => void;
  refetchPacks: () => void;
  refetchPublished: () => void;
}

export default function PackDetailView({
  activePack, activePackId, isPackLoading, user, packs, isLight,
  onBack, onFlash, refetchPack, refetchPacks, refetchPublished,
}: Props) {
  const queryClient = useQueryClient();

  const [refreshing, setRefreshing] = useState(false);
  const [editingName, setEditingName] = useState(false);
  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [savingName, setSavingName] = useState(false);
  const [editingChartIndex, setEditingChartIndex] = useState<number | null>(null);
  const [justSavedIndex, setJustSavedIndex] = useState<number | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [copyMoveChartIndex, setCopyMoveChartIndex] = useState<number | null>(null);
  const [copyMoveTarget, setCopyMoveTarget] = useState<string | null>(null);
  const [copyMoveLoading, setCopyMoveLoading] = useState(false);

  // Escape to close copy/move modal
  useEffect(() => {
    if (copyMoveChartIndex == null) return;
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape' && !copyMoveLoading) setCopyMoveChartIndex(null); };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [copyMoveChartIndex, copyMoveLoading]);

  const formStyle = {
    colorScheme: isLight ? 'light' as const : 'dark' as const,
    backgroundColor: 'rgb(var(--background))',
    color: 'rgb(var(--foreground))',
  };

  // ── Loading skeleton ──
  if (isPackLoading || !activePack) {
    return <DetailSkeleton />;
  }

  const isOwner = !!user && user.id === activePack.user_id;
  const chartCount = activePack.charts.filter(c => !c.deleted).length;

  // ── Handlers ──

  const handleRefresh = async () => {
    setRefreshing(true);
    queryClient.invalidateQueries({ queryKey: ['pack-batch-data'] });
    queryClient.invalidateQueries({ queryKey: ['pack-chart-code'] });
    queryClient.invalidateQueries({ queryKey: ['chart-figure'] });
    await refetchPack();
    setTimeout(() => setRefreshing(false), 800);
  };

  const handleRefreshChart = async (chartIndex: number) => {
    const chart = activePack.charts[chartIndex];
    if (!chart) return;
    const charts = activePack.charts.map((c: any, i: number) => {
      if (i !== chartIndex) return c;
      const { figure, figureCachedAt, ...rest } = c;
      return rest;
    });
    try {
      await apiFetchJson(`/api/chart-packs/${activePack.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ charts }),
      });
      if (chart.code?.trim()) {
        queryClient.invalidateQueries({ queryKey: ['pack-chart-code', chartIndex] });
      }
      await refetchPack();
    } catch (e: any) {
      onFlash({ type: 'error', text: e?.message || 'Failed to refresh chart' });
    }
  };

  const handleRemoveChart = async (chartIndex: number) => {
    const charts = activePack.charts.map((c, i) =>
      i === chartIndex ? { ...c, deleted: true } : c,
    );
    try {
      await apiFetchJson(`/api/chart-packs/${activePack.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ charts }),
      });
      refetchPack();
      refetchPacks();
      onFlash({ type: 'success', text: 'Chart removed' });
    } catch (e: any) {
      onFlash({ type: 'error', text: e?.message || 'Failed to remove chart' });
    }
  };

  const handleAddChart = () => {
    setEditingChartIndex(-1);
  };

  const handleSaveEditedChart = async (updatedConfig: ChartConfig) => {
    if (editingChartIndex == null) return;
    const isNew = editingChartIndex === -1;
    let charts: ChartConfig[];
    if (isNew) {
      charts = [...activePack.charts, updatedConfig];
    } else {
      charts = activePack.charts.map((c, i) =>
        i === editingChartIndex ? updatedConfig : c,
      );
    }
    try {
      await apiFetchJson(`/api/chart-packs/${activePack.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ charts }),
      });
      await refetchPack();
      setSaveError(null);
      const savedIdx = isNew ? charts.length - 1 : editingChartIndex;
      setJustSavedIndex(savedIdx);
      setTimeout(() => setJustSavedIndex(null), 1800);
      setEditingChartIndex(null);
    } catch (e: any) {
      setSaveError(e?.message || 'Failed to save chart');
    }
  };

  const handleMoveChart = async (from: number, to: number) => {
    const charts = [...activePack.charts];
    const [moved] = charts.splice(from, 1);
    charts.splice(to, 0, moved);
    try {
      await apiFetchJson(`/api/chart-packs/${activePack.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ charts }),
      });
      refetchPack();
    } catch (e: any) {
      onFlash({ type: 'error', text: e?.message || 'Failed to move chart' });
    }
  };

  const handleSaveName = async () => {
    if (!editName.trim() || savingName) return;
    setSavingName(true);
    try {
      await apiFetchJson(`/api/chart-packs/${activePack.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: editName.trim(), description: editDesc.trim() || null }),
      });
      setEditingName(false);
      refetchPack();
      refetchPacks();
    } catch (e: any) {
      onFlash({ type: 'error', text: e?.message || 'Failed to save name' });
    } finally {
      setSavingName(false);
    }
  };

  const handleTogglePublish = async () => {
    const prev = activePack.is_published;
    const next = !prev;
    queryClient.setQueryData(['chart-pack', activePack.id], (old: PackDetail | undefined) =>
      old ? { ...old, is_published: next } : old,
    );
    try {
      await apiFetchJson(`/api/chart-packs/${activePack.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_published: next }),
      });
      refetchPack();
      refetchPacks();
      refetchPublished();
      onFlash({ type: 'success', text: next ? 'Pack published' : 'Pack unpublished' });
    } catch (e: any) {
      queryClient.setQueryData(['chart-pack', activePack.id], (old: PackDetail | undefined) =>
        old ? { ...old, is_published: prev } : old,
      );
      onFlash({ type: 'error', text: e?.message || 'Failed to update publish status' });
    }
  };

  const handleCopyToPack = async () => {
    if (copyMoveChartIndex == null || !copyMoveTarget) return;
    setCopyMoveLoading(true);
    try {
      const chart = activePack.charts[copyMoveChartIndex];
      await apiFetchJson(`/api/chart-packs/${copyMoveTarget}/charts`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chart }),
      });
      const targetPack = packs?.find((p) => p.id === copyMoveTarget);
      setCopyMoveChartIndex(null);
      setCopyMoveTarget(null);
      refetchPacks();
      onFlash({ type: 'success', text: `Chart copied to ${targetPack?.name || 'pack'}` });
    } catch (e: any) {
      onFlash({ type: 'error', text: e?.message || 'Failed to copy chart' });
    } finally { setCopyMoveLoading(false); }
  };

  const handleMoveToPackAction = async () => {
    if (copyMoveChartIndex == null || !copyMoveTarget) return;
    setCopyMoveLoading(true);
    try {
      const chart = activePack.charts[copyMoveChartIndex];
      await apiFetchJson(`/api/chart-packs/${copyMoveTarget}/charts`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chart }),
      });
      const charts = activePack.charts.map((c, i) =>
        i === copyMoveChartIndex ? { ...c, deleted: true } : c,
      );
      await apiFetchJson(`/api/chart-packs/${activePack.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ charts }),
      });
      const targetPack = packs?.find((p) => p.id === copyMoveTarget);
      setCopyMoveChartIndex(null);
      setCopyMoveTarget(null);
      refetchPack();
      refetchPacks();
      onFlash({ type: 'success', text: `Chart moved to ${targetPack?.name || 'pack'}` });
    } catch (e: any) {
      onFlash({ type: 'error', text: e?.message || 'Failed to move chart' });
    } finally { setCopyMoveLoading(false); }
  };

  return (
    <div className="h-[calc(100vh-56px)] flex flex-col bg-background">
      {/* ── Header bar ── */}
      <motion.div
        initial={{ opacity: 0, y: -4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        className="shrink-0 flex items-center px-4 gap-3 border-b border-border/30 bg-foreground/[0.04] h-12"
      >
        {/* Back button */}
        <button
          onClick={onBack}
          className="flex items-center gap-1 text-[12.5px] font-medium text-muted-foreground hover:text-foreground transition-colors shrink-0 -ml-1"
          aria-label="Back to all packs"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Packs</span>
        </button>

        <div className="w-px h-5 bg-border/20" />

        {/* Inline editing mode */}
        {editingName && isOwner ? (
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <input
              autoFocus type="text" value={editName}
              onChange={(e) => setEditName(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleSaveName(); if (e.key === 'Escape') setEditingName(false); }}
              className="form-input h-8 text-[13px] font-semibold flex-1 min-w-0"
              style={formStyle}
              disabled={savingName}
              placeholder="Pack name"
            />
            <input
              type="text" value={editDesc}
              onChange={(e) => setEditDesc(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleSaveName(); if (e.key === 'Escape') setEditingName(false); }}
              placeholder="Description (optional)"
              className="form-input h-8 text-[13px] flex-1 min-w-0 hidden md:block"
              style={formStyle}
              disabled={savingName}
            />
            <button
              onClick={handleSaveName} disabled={savingName}
              className="btn-icon text-success hover:text-success hover:bg-success/10"
              aria-label="Save"
            >
              {savingName ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
            </button>
            <button
              onClick={() => setEditingName(false)} disabled={savingName}
              className="btn-icon text-muted-foreground hover:text-foreground hover:bg-foreground/[0.06]"
              aria-label="Cancel"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          /* Display mode */
          <div className="flex items-center gap-2.5 min-w-0 flex-1">
            {isOwner ? (
              <button
                onClick={() => { setEditName(activePack.name); setEditDesc(activePack.description || ''); setEditingName(true); }}
                className="flex items-center gap-1.5 min-w-0 group/title"
              >
                <span className="page-title truncate">{activePack.name}</span>
                <Edit3 className="w-3 h-3 text-muted-foreground/20 group-hover/title:text-primary transition-colors shrink-0" />
              </button>
            ) : (
              <span className="page-title truncate">{activePack.name}</span>
            )}
            {activePack.description && (
              <span className="text-[12.5px] text-muted-foreground/40 truncate hidden md:block max-w-[220px]" title={activePack.description}>
                {activePack.description}
              </span>
            )}

            <div className="w-px h-4 bg-border/20 hidden lg:block" />

            {/* Metadata chips */}
            <div className="hidden lg:flex items-center gap-3">
              <span className="stat-label inline-flex items-center gap-1 tabular-nums">
                <LineChart className="w-2.5 h-2.5" />
                {chartCount}
              </span>
              <span className="stat-label inline-flex items-center gap-1 tabular-nums opacity-70">
                <Clock className="w-2.5 h-2.5" />
                {relativeTime(activePack.updated_at)}
              </span>
              {activePack.creator_name && !isOwner && (
                <span className="stat-label opacity-60">by {activePack.creator_name}</span>
              )}
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex items-center gap-1.5 shrink-0">
          {isOwner && (
            <button
              onClick={handleTogglePublish}
              className={`btn-toolbar transition-colors ${
                activePack.is_published
                  ? 'bg-success/10 text-success border-success/20 hover:bg-success/15 hover:border-success/30'
                  : ''
              }`}
              title={activePack.is_published ? 'Published \u2014 click to unpublish' : 'Private \u2014 click to publish'}
            >
              {activePack.is_published ? <Globe className="w-3 h-3" /> : <Lock className="w-3 h-3" />}
              <span className="hidden sm:inline ml-1">{activePack.is_published ? 'Published' : 'Private'}</span>
            </button>
          )}
          {isOwner && (
            <button onClick={handleAddChart} className="btn-primary h-8 px-3 text-[12.5px]" title="Add chart">
              <Plus className="w-3 h-3" />
              <span className="hidden sm:inline">Add chart</span>
            </button>
          )}
          <button
            onClick={handleRefresh} disabled={refreshing}
            className="btn-icon" title="Refresh" aria-label="Refresh data"
          >
            <RefreshCw className={`w-3.5 h-3.5 transition-transform ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </motion.div>

      {/* ── Chart grid ── */}
      <div className="flex-1 overflow-y-auto no-scrollbar p-3">
        <PackChartGrid
          pack={activePack} isLight={isLight}
          readOnly={!isOwner}
          justSavedIndex={justSavedIndex}
          onRemoveChart={handleRemoveChart}
          onEditChart={(i) => setEditingChartIndex(i)}
          onMoveChart={handleMoveChart}
          onCopyMoveChart={(i) => { setCopyMoveChartIndex(i); setCopyMoveTarget(null); }}
          onRefreshChart={handleRefreshChart}
          onAddChart={handleAddChart}
        />
      </div>

      {/* ── Edit overlay ── */}
      {editingChartIndex != null && (
        <ChartEditOverlay
          config={editingChartIndex === -1 ? { series: [], code: '' } : activePack.charts[editingChartIndex]}
          chartIndex={editingChartIndex === -1 ? activePack.charts.length : editingChartIndex}
          isLight={isLight}
          onSave={handleSaveEditedChart}
          onClose={() => { setEditingChartIndex(null); setSaveError(null); }}
          saveError={saveError}
        />
      )}

      {/* ── Copy / Move modal ── */}
      <AnimatePresence>
        {copyMoveChartIndex != null && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-background/60"
            onClick={() => !copyMoveLoading && setCopyMoveChartIndex(null)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: 8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 8 }}
              transition={{ duration: 0.2 }}
              className="rounded-[var(--radius)] border border-border/50 bg-card shadow-2xl p-5 w-[400px] mx-4"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal header */}
              <div className="flex items-center justify-between mb-1">
                <h3 className="section-title">Copy / Move chart</h3>
                <button onClick={() => setCopyMoveChartIndex(null)} className="btn-icon" aria-label="Close" title="Close (Esc)" disabled={copyMoveLoading}>
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
              <p className="text-[12.5px] text-muted-foreground truncate mb-4">
                {activePack.charts[copyMoveChartIndex]?.title || `Chart ${copyMoveChartIndex + 1}`}
              </p>

              {packs && packs.filter((p) => p.id !== activePack.id).length > 0 ? (
                <>
                  <label className="form-label block mb-2">Select target pack</label>
                  <div className="space-y-0.5 max-h-[220px] overflow-y-auto no-scrollbar mb-4">
                    {packs.filter((p) => p.id !== activePack.id).map((p) => (
                      <button
                        key={p.id}
                        onClick={() => setCopyMoveTarget(p.id)}
                        className={`w-full text-left px-3 py-2.5 rounded-[var(--radius)] flex items-center gap-2 transition-colors ${
                          copyMoveTarget === p.id
                            ? 'bg-primary/[0.08] border border-primary/20 text-foreground'
                            : 'border border-transparent hover:bg-foreground/[0.04] hover:border-border/30'
                        }`}
                        disabled={copyMoveLoading}
                      >
                        <LineChart className="w-3 h-3 text-primary/40 shrink-0" />
                        <span className="text-[13px] font-medium text-foreground truncate flex-1">{p.name}</span>
                        <span className="stat-label tabular-nums shrink-0">{p.chart_count}</span>
                      </button>
                    ))}
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={handleCopyToPack}
                      disabled={!copyMoveTarget || copyMoveLoading}
                      className="btn-primary flex-1"
                    >
                      {copyMoveLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'Copy'}
                    </button>
                    <button
                      onClick={handleMoveToPackAction}
                      disabled={!copyMoveTarget || copyMoveLoading}
                      className="btn-secondary flex-1"
                    >
                      {copyMoveLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'Move'}
                    </button>
                  </div>
                </>
              ) : (
                <div className="text-center py-8">
                  <p className="text-[13px] text-muted-foreground">No other packs available.</p>
                  <p className="text-[12.5px] text-muted-foreground/60 mt-2">Create another pack first to copy or move charts.</p>
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
