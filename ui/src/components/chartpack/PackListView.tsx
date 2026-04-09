import React, { useCallback, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { LayoutGrid, LineChart, Plus, Trash2, Users, X, Loader2, Globe, FileText, Clock } from 'lucide-react';
import { COLORWAY } from '@/lib/chartTheme';
import { apiFetchJson } from '@/lib/api';
import ConfirmDialog from './ConfirmDialog';
import ReportModal from './ReportModal';
import ReportEditor, { type Slide } from './ReportEditor';
import type { PackSummary, PackDetail, FlashMessage } from './types';
import { shortDate } from './types';

// ── Skeletons ──

function PackCardSkeleton({ index }: { index: number }) {
  return (
    <div
      className="panel-card overflow-hidden flex flex-col animate-fade-in"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="h-1.5 w-full bg-foreground/[0.03]" />
      <div className="px-4 py-3 flex flex-col flex-1 gap-2.5">
        <div className="h-4 w-3/5 bg-foreground/[0.06] rounded animate-pulse" />
        <div className="h-3 w-full bg-foreground/[0.03] rounded animate-pulse" />
        <div className="flex items-center gap-3 mt-auto pt-2.5 border-t border-border/20">
          <div className="h-3 w-12 bg-foreground/[0.04] rounded animate-pulse" />
          <div className="h-3 w-16 bg-foreground/[0.04] rounded animate-pulse" />
          <div className="h-3 w-14 bg-foreground/[0.04] rounded animate-pulse ml-auto" />
        </div>
      </div>
    </div>
  );
}

// ── Props ──

interface Props {
  user: any;
  packs: PackSummary[] | undefined;
  publishedPacks: PackSummary[] | undefined;
  packsLoading: boolean;
  onSelectPack: (id: string) => void;
  onFlash: (msg: FlashMessage) => void;
  refetchPacks: () => void;
  refetchPublished: () => void;
  isLight: boolean;
}

export default function PackListView({
  user, packs, publishedPacks, packsLoading,
  onSelectPack, onFlash, refetchPacks, refetchPublished, isLight,
}: Props) {
  const [listTab, setListTab] = useState<'mine' | 'published'>(() => user ? 'mine' : 'published');
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newPackName, setNewPackName] = useState('');
  const [newPackDesc, setNewPackDesc] = useState('');
  const [creating, setCreating] = useState(false);
  const [deletePackTarget, setDeletePackTarget] = useState<{ id: string; name: string } | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [editorSlides, setEditorSlides] = useState<Slide[] | null>(null);

  // Escape to close create modal
  useEffect(() => {
    if (!createModalOpen) return;
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape' && !creating) setCreateModalOpen(false); };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [createModalOpen, creating]);

  const formStyle = {
    colorScheme: isLight ? 'light' as const : 'dark' as const,
    backgroundColor: 'rgb(var(--background))',
    color: 'rgb(var(--foreground))',
  };

  const handleCreatePack = useCallback(async () => {
    if (!newPackName.trim() || creating) return;
    setCreating(true);
    try {
      const pack = await apiFetchJson<PackDetail>('/api/chart-packs', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newPackName.trim(), description: newPackDesc.trim() || null, charts: [] }),
      });
      onSelectPack(pack.id);
      setCreateModalOpen(false);
      setNewPackName('');
      setNewPackDesc('');
      refetchPacks();
      onFlash({ type: 'success', text: 'Pack created' });
    } catch (e: any) {
      onFlash({ type: 'error', text: e?.message || 'Failed to create pack' });
    } finally {
      setCreating(false);
    }
  }, [newPackName, newPackDesc, creating, refetchPacks, onSelectPack, onFlash]);

  const handleDeletePackClick = useCallback((id: string, name: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDeletePackTarget({ id, name });
  }, []);

  const handleDeletePackConfirm = useCallback(async () => {
    if (!deletePackTarget || deleting) return;
    setDeleting(true);
    try {
      await apiFetchJson(`/api/chart-packs/${deletePackTarget.id}`, { method: 'DELETE' });
      refetchPacks();
      onFlash({ type: 'success', text: 'Pack deleted' });
    } catch (e: any) {
      onFlash({ type: 'error', text: e?.message || 'Failed to delete pack' });
    } finally {
      setDeleting(false);
      setDeletePackTarget(null);
    }
  }, [deletePackTarget, deleting, refetchPacks, onFlash]);

  const currentPacks = listTab === 'mine' ? packs : publishedPacks;
  const isLoading = listTab === 'mine' ? packsLoading && !packs : !publishedPacks;

  const myCount = packs?.length ?? 0;
  const pubCount = publishedPacks?.length ?? 0;

  return (
    <>
      <div className="page-shell">
        {/* ── Header ── */}
        <div className="page-header">
          <LayoutGrid className="w-3 h-3 text-muted-foreground" />
          <h1 className="page-header-title">CHARTPACK</h1>
          <div className="page-header-divider" aria-hidden />
          <span className="text-[10px] font-mono uppercase tracking-[0.08em] text-muted-foreground tabular-nums">
            {(listTab === 'mine' ? myCount : pubCount)} PACKS
          </span>

          <div className="flex-1" />

          {user && (
            <button
              onClick={() => setReportModalOpen(true)}
              className="h-6 px-2.5 text-[10px] font-mono font-semibold uppercase tracking-[0.10em] border border-border/60 text-muted-foreground hover:text-foreground hover:border-border transition-colors inline-flex items-center gap-1.5"
              title="Generate PDF report from packs"
            >
              <FileText className="w-3 h-3" />
              REPORT
            </button>
          )}
          {user && (
            <button
              onClick={() => setCreateModalOpen(true)}
              className="h-6 px-2.5 text-[10px] font-mono font-semibold uppercase tracking-[0.10em] bg-foreground text-background hover:bg-foreground/90 transition-colors inline-flex items-center gap-1.5"
            >
              <Plus className="w-3 h-3" />
              NEW PACK
            </button>
          )}
        </div>

        {/* ── Tab bar ── */}
        <div className="page-tabs">
          {user && (
            <button
              onClick={() => setListTab('mine')}
              className={`page-tab ${listTab === 'mine' ? 'page-tab-active' : ''}`}
            >
              <LayoutGrid className="w-3 h-3" />
              MY PACKS
              <span className="text-[9px] font-mono text-muted-foreground tabular-nums">({myCount})</span>
            </button>
          )}
          <button
            onClick={() => setListTab('published')}
            className={`page-tab ${listTab === 'published' ? 'page-tab-active' : ''}`}
          >
            <Users className="w-3 h-3" />
            PUBLISHED
            <span className="text-[9px] font-mono text-muted-foreground tabular-nums">({pubCount})</span>
          </button>
        </div>

        {/* ── Pack cards ── */}
        <div className="flex-1 overflow-y-auto no-scrollbar px-3 sm:px-5 lg:px-6 py-4">
          {isLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-3">
              {Array.from({ length: 6 }, (_, i) => <PackCardSkeleton key={i} index={i} />)}
            </div>
          ) : currentPacks && currentPacks.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-3">
              {currentPacks.map((pack, idx) => (
                <button
                  key={pack.id}
                  onClick={() => onSelectPack(pack.id)}
                  className="panel-card text-left overflow-hidden hover:border-primary/30 hover:shadow-md transition-all duration-200 group/pack relative flex flex-col cursor-pointer animate-fade-in"
                  style={{ animationDelay: `${idx * 40}ms` }}
                >
                  {/* Color density bar */}
                  <div className="h-1.5 w-full flex gap-px overflow-hidden">
                    {pack.chart_count > 0
                      ? Array.from({ length: Math.min(pack.chart_count, 12) }, (_, i) => (
                          <div key={i} className="flex-1 h-full transition-opacity group-hover/pack:opacity-80" style={{ backgroundColor: COLORWAY[i % COLORWAY.length], opacity: 0.6 }} />
                        ))
                      : <div className="flex-1 h-full bg-border/10" />
                    }
                  </div>

                  <div className="px-4 py-3 flex flex-col flex-1 gap-1.5">
                    {/* Row 1: Name + delete */}
                    <div className="flex items-center gap-2">
                      <h3 className="text-[13px] font-semibold text-foreground group-hover/pack:text-primary transition-colors duration-200 truncate leading-tight flex-1">
                        {pack.name}
                      </h3>
                      {listTab === 'mine' && (
                        <button
                          onClick={(e) => handleDeletePackClick(pack.id, pack.name, e)}
                          className="btn-icon w-6 h-6 shrink-0 opacity-0 group-hover/pack:opacity-100 text-muted-foreground/25 hover:text-destructive hover:bg-destructive/10 transition-all"
                          aria-label={`Delete ${pack.name}`}
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      )}
                    </div>

                    {/* Row 2: Description (compact) */}
                    {pack.description && (
                      <p className="text-[12px] text-muted-foreground/40 line-clamp-1 leading-snug">{pack.description}</p>
                    )}

                    {/* Row 3: Stats */}
                    <div className="flex items-center gap-3 mt-auto pt-2.5 border-t border-border/20">
                      <span className="stat-label inline-flex items-center gap-1 text-muted-foreground/40">
                        <LineChart className="w-2.5 h-2.5" />
                        <span className="tabular-nums">{pack.chart_count}</span>
                      </span>
                      <span className="stat-label inline-flex items-center gap-1 text-muted-foreground/30">
                        <Clock className="w-2.5 h-2.5" />
                        <span className="tabular-nums">{shortDate(pack.updated_at)}</span>
                      </span>
                      {listTab === 'published' && pack.creator_name && (
                        <span className="stat-label text-muted-foreground/30 truncate ml-auto">{pack.creator_name}</span>
                      )}
                    </div>

                    {/* Row 4: Badges */}
                    {(listTab === 'mine' && pack.is_published) && (
                      <div className="flex items-center gap-1.5 pt-1">
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-[4px] bg-success/[0.08] text-success border border-success/15 text-[9.5px] font-mono font-bold uppercase tracking-wider shrink-0">
                          <Globe className="w-2 h-2" />
                          Live
                        </span>
                      </div>
                    )}
                  </div>
                </button>
              ))}
            </div>
          ) : (
            /* Empty state */
            <div className="h-full flex items-center justify-center">
              <div className="text-center max-w-[280px] animate-fade-in">
                <div className="w-12 h-12 mx-auto rounded-[var(--radius)] border border-border/30 bg-card flex items-center justify-center mb-4">
                  {listTab === 'published' ? <Users className="w-5 h-5 text-muted-foreground/20" /> : <LayoutGrid className="w-5 h-5 text-muted-foreground/20" />}
                </div>
                <p className="text-[13px] font-semibold text-muted-foreground/40">
                  {listTab === 'published' ? 'No published packs yet' : 'No chart packs yet'}
                </p>
                <p className="text-[12.5px] text-muted-foreground/40 mt-2 leading-relaxed">
                  {listTab === 'published'
                    ? 'Published packs from other users will appear here.'
                    : 'Create a pack to organize and monitor your charts in one view.'}
                </p>
                {listTab === 'mine' && (
                  <button onClick={() => setCreateModalOpen(true)} className="btn-primary mt-5">
                    <Plus className="w-3.5 h-3.5" /> Create your first pack
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Delete pack confirmation ── */}
      {deletePackTarget && (
        <ConfirmDialog
          title="Delete chart pack"
          message={<>Delete <span className="font-semibold text-foreground">{deletePackTarget.name}</span>? The pack and all its charts will be archived.</>}
          confirmLabel="Delete"
          onConfirm={handleDeletePackConfirm}
          onCancel={() => !deleting && setDeletePackTarget(null)}
          loading={deleting}
        />
      )}

      {/* ── Create modal ── */}
      <AnimatePresence>
        {createModalOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-background/60"
            onClick={() => !creating && setCreateModalOpen(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: 8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 8 }}
              transition={{ duration: 0.2 }}
              className="rounded-[var(--radius)] border border-border/40 bg-card shadow-2xl p-5 w-[400px] mx-4"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-1">
                <h3 className="text-[14px] font-semibold text-foreground">New chart pack</h3>
                <button onClick={() => setCreateModalOpen(false)} className="btn-icon" aria-label="Close" title="Close (Esc)" disabled={creating}>
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
              <p className="text-[12.5px] text-muted-foreground/40 mb-5">Organize charts into a monitoring view</p>
              <div className="space-y-3">
                <div>
                  <label className="form-label block mb-1.5">Name</label>
                  <input
                    autoFocus type="text" value={newPackName}
                    onChange={(e) => setNewPackName(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter' && newPackName.trim()) handleCreatePack(); }}
                    placeholder="e.g. Macro Dashboard, Equity Watchlist..."
                    className="form-input h-9 text-[13px] placeholder:text-muted-foreground/25"
                    style={formStyle}
                    disabled={creating}
                  />
                </div>
                <div>
                  <label className="form-label block mb-1.5">
                    Description
                    <span className="text-muted-foreground/25 normal-case tracking-normal font-sans ml-1">(optional)</span>
                  </label>
                  <textarea
                    value={newPackDesc} onChange={(e) => setNewPackDesc(e.target.value)}
                    placeholder="What's in this pack?" rows={2}
                    className="w-full px-3 py-2 text-[13px] bg-background border border-border/50 rounded-[var(--radius)] focus:outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/25 resize-none placeholder:text-muted-foreground/25 transition-all"
                    style={formStyle}
                    disabled={creating}
                  />
                </div>
              </div>
              <div className="flex gap-2 mt-5">
                <button onClick={() => setCreateModalOpen(false)} className="btn-secondary flex-1" disabled={creating}>Cancel</button>
                <button
                  onClick={handleCreatePack} disabled={!newPackName.trim() || creating}
                  className="btn-primary flex-1"
                >
                  {creating ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
                  Create pack
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Report modal ── */}
      <AnimatePresence>
        {reportModalOpen && !editorSlides && (
          <ReportModal
            myPacks={packs || []}
            publishedPacks={publishedPacks || []}
            isLight={isLight}
            onClose={() => setReportModalOpen(false)}
            onFlash={onFlash}
            onOpenEditor={(slides) => {
              setEditorSlides(slides);
              setReportModalOpen(false);
            }}
          />
        )}
      </AnimatePresence>

      {/* ── Report editor (full-screen) ── */}
      <AnimatePresence>
        {editorSlides && (
          <ReportEditor
            initialSlides={editorSlides}
            isLight={isLight}
            onClose={() => setEditorSlides(null)}
            onFlash={onFlash}
          />
        )}
      </AnimatePresence>
    </>
  );
}
