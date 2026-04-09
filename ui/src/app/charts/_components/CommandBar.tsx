'use client';

import React, { useRef, useEffect } from 'react';
import {
  Loader2, Terminal, ChevronLeft, Save, Plus, MoreVertical,
  Copy, Download, FolderOpen, RotateCcw, Trash2,
  PanelRightOpen, PanelRightClose,
} from 'lucide-react';
import type { WorkspaceSummary } from './types';

interface CommandBarProps {
  // Sidebar toggle
  rightSidebarOpen: boolean;
  onToggleRightSidebar: () => void;
  // Code editor
  expressionMode: boolean;
  onToggleCode: () => void;
  // Date range
  toolbarPresets: { label: string; months: number }[];
  activeRange: string;
  onRangePreset: (label: string, months: number) => void;
  startDate: string;
  endDate: string;
  onStartDateChange: (v: string) => void;
  onEndDateChange: (v: string) => void;
  // Toggle buttons
  showRecessions: boolean;
  onToggleRecessions: () => void;
  allRebased: boolean;
  onToggleRebase: () => void;
  // Hover mode
  hoverMode: string;
  onCycleHoverMode: () => void;
  // Title
  chartTitle: string;
  onChartTitleChange: (v: string) => void;
  // Loading
  isFetching: boolean;
  // Pack context
  packId: string | null;
  packEditCtx: { packId: string; chartIndex: number } | null;
  addToPackId: string | null;
  savingToPack: boolean;
  onBackToPack: () => void;
  onUpdatePackChart: () => void;
  onAddChartToPack: () => void;
  seriesCount: number;
  // Save
  onSaveWorkspace: () => void;
  activeWorkspaceId: string | null;
  // Actions menu
  copyState: 'idle' | 'done';
  onCopyPng: () => void;
  onDownloadCsv: () => void;
  onSaveToPackOpen: () => void;
  onClearAll: () => void;
  workspaces: WorkspaceSummary[];
  onLoadWorkspace: (id: string) => void;
  onDeleteWorkspace: (id: string) => void;
  onFetchWorkspaces: () => void;
  // Form style
  formStyle: React.CSSProperties;
  isLight: boolean;
}

export default function CommandBar({
  rightSidebarOpen,
  onToggleRightSidebar,
  expressionMode,
  onToggleCode,
  toolbarPresets,
  activeRange,
  onRangePreset,
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
  showRecessions,
  onToggleRecessions,
  allRebased,
  onToggleRebase,
  hoverMode,
  onCycleHoverMode,
  chartTitle,
  onChartTitleChange,
  isFetching,
  packId,
  packEditCtx,
  addToPackId,
  savingToPack,
  onBackToPack,
  onUpdatePackChart,
  onAddChartToPack,
  seriesCount,
  onSaveWorkspace,
  activeWorkspaceId,
  copyState,
  onCopyPng,
  onDownloadCsv,
  onSaveToPackOpen,
  onClearAll,
  workspaces,
  onLoadWorkspace,
  onDeleteWorkspace,
  onFetchWorkspaces,
  formStyle,
  isLight,
}: CommandBarProps) {
  const [actionsMenuOpen, setActionsMenuOpen] = React.useState(false);
  const actionsMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!actionsMenuOpen) return;
    const handler = (e: MouseEvent) => {
      if (actionsMenuRef.current && !actionsMenuRef.current.contains(e.target as Node)) setActionsMenuOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [actionsMenuOpen]);

  const hoverModeLabel = hoverMode === 'x unified' ? 'XU' : hoverMode === 'closest' ? 'CL' : 'X';

  return (
    <div className="shrink-0 h-9 border-b border-border/30 flex items-center px-1.5 gap-0 bg-background">
      {/* Code editor toggle */}
      <button
        onClick={onToggleCode}
        className={`w-7 h-7 flex items-center justify-center rounded-[var(--radius)] shrink-0 transition-colors ${
          expressionMode ? 'bg-primary/10 text-primary' : 'text-muted-foreground/30 hover:text-foreground hover:bg-foreground/[0.04]'
        }`}
        title="Code editor (Ctrl+E)"
      >
        <Terminal className="w-3.5 h-3.5" />
      </button>

      <div className="w-px h-5 bg-border/20 mx-0.5 shrink-0" />

      {/* Date Range Presets */}
      <div className="flex items-center gap-0.5 shrink-0">
        {toolbarPresets.map((p) => (
          <button
            key={p.label}
            onClick={() => onRangePreset(p.label, p.months)}
            className={`h-[22px] px-1.5 rounded-[3px] text-[11.5px] font-mono shrink-0 transition-colors ${
              activeRange === p.label
                ? 'bg-foreground text-background'
                : 'text-muted-foreground/40 hover:text-foreground'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Date inputs */}
      <input
        type="date"
        value={startDate}
        onChange={(e) => onStartDateChange(e.target.value)}
        className="h-[22px] w-[95px] px-1 text-[11.5px] font-mono border border-border/30 rounded-[3px] focus:outline-none focus:border-primary/40 shrink-0 ml-1"
        style={formStyle}
        title="Start"
      />
      <span className="text-[11.5px] text-muted-foreground/30 mx-0.5 shrink-0">{'\u2014'}</span>
      <input
        type="date"
        value={endDate}
        onChange={(e) => onEndDateChange(e.target.value)}
        className="h-[22px] w-[95px] px-1 text-[11.5px] font-mono border border-border/30 rounded-[3px] focus:outline-none focus:border-primary/40 shrink-0"
        style={formStyle}
        title="End"
      />

      <div className="w-px h-5 bg-border/20 mx-1 shrink-0" />

      {/* Toggle buttons */}
      <button
        onClick={onToggleRecessions}
        className={`h-[22px] px-1.5 rounded-[3px] text-[11.5px] font-mono font-medium shrink-0 transition-colors ${
          showRecessions ? 'text-primary' : 'text-muted-foreground/40 hover:text-foreground'
        }`}
        title="NBER recession shading"
      >
        REC
      </button>
      <button
        onClick={onToggleRebase}
        className={`h-[22px] px-1.5 rounded-[3px] text-[11.5px] font-mono font-medium shrink-0 transition-colors ${
          allRebased ? 'text-primary' : 'text-muted-foreground/40 hover:text-foreground'
        }`}
        title="Rebase / index all series to 100"
      >
        IDX
      </button>
      <button
        onClick={onCycleHoverMode}
        className="h-[22px] px-1.5 rounded-[3px] text-[11.5px] font-mono font-medium shrink-0 text-muted-foreground/40 hover:text-foreground transition-colors"
        title={`Hover mode: ${hoverMode}`}
      >
        {hoverModeLabel}
      </button>

      <div className="w-px h-5 bg-border/20 mx-1 shrink-0" />

      {/* Title input */}
      <input
        type="text"
        value={chartTitle}
        onChange={(e) => onChartTitleChange(e.target.value)}
        placeholder="Untitled"
        className="flex-1 min-w-[80px] h-[26px] px-2 text-[13px] font-semibold bg-transparent text-foreground placeholder:text-muted-foreground/20 border border-transparent rounded-[var(--radius)] hover:border-border/30 focus:border-border/40 focus:outline-none transition-colors"
      />

      {/* Loading indicator */}
      {isFetching && <Loader2 className="w-3 h-3 animate-spin text-primary/40 shrink-0 mr-1" />}

      <div className="w-px h-5 bg-border/20 mx-1 shrink-0" />

      {/* Pack context */}
      {packId && (
        <button
          onClick={onBackToPack}
          className="h-[26px] px-1.5 flex items-center gap-1 rounded-[var(--radius)] text-muted-foreground/40 hover:text-foreground transition-colors shrink-0"
          title="Back to pack"
        >
          <ChevronLeft className="w-3 h-3" />
          <span className="text-[11.5px] font-mono">PACK</span>
        </button>
      )}
      {packEditCtx && (
        <button
          onClick={onUpdatePackChart}
          disabled={savingToPack}
          className="h-[26px] px-2.5 flex items-center gap-1 rounded-[var(--radius)] bg-foreground text-background text-[11.5px] font-mono font-medium hover:opacity-90 transition-colors disabled:opacity-30 shrink-0 mr-1"
        >
          {savingToPack ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
          Update
        </button>
      )}
      {addToPackId && !packEditCtx && (
        <button
          onClick={onAddChartToPack}
          disabled={savingToPack || seriesCount === 0}
          className="h-[26px] px-2.5 flex items-center gap-1 rounded-[var(--radius)] bg-foreground text-background text-[11.5px] font-mono font-medium hover:opacity-90 transition-colors disabled:opacity-30 shrink-0 mr-1"
        >
          {savingToPack ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
          Add to Pack
        </button>
      )}

      {/* Save workspace */}
      <button
        onClick={onSaveWorkspace}
        className="w-7 h-7 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/30 hover:text-foreground hover:bg-foreground/[0.04] transition-colors shrink-0"
        title={activeWorkspaceId ? 'Update workspace (Ctrl+S)' : 'Save workspace (Ctrl+S)'}
      >
        <Save className="w-3.5 h-3.5" />
      </button>

      {/* Actions dropdown */}
      <div className="relative shrink-0" ref={actionsMenuRef}>
        <button
          onClick={() => { setActionsMenuOpen(!actionsMenuOpen); if (!actionsMenuOpen) onFetchWorkspaces(); }}
          className="w-7 h-7 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/30 hover:text-foreground hover:bg-foreground/[0.04] transition-colors"
          title="Actions"
        >
          <MoreVertical className="w-3.5 h-3.5" />
        </button>
        {actionsMenuOpen && (
          <div className="absolute right-0 top-full mt-1 bg-card border border-border/50 rounded-[var(--radius)] shadow-lg z-50 py-1 min-w-[180px]">
            <button
              onClick={() => { onCopyPng(); setActionsMenuOpen(false); }}
              className="w-full flex items-center gap-2.5 px-3 py-1.5 text-[12.5px] font-mono text-muted-foreground hover:text-foreground hover:bg-foreground/[0.04] transition-colors"
            >
              <Copy className="w-3.5 h-3.5" /> {copyState === 'done' ? 'Copied!' : 'Copy PNG'}
            </button>
            <button
              onClick={() => { onDownloadCsv(); setActionsMenuOpen(false); }}
              className="w-full flex items-center gap-2.5 px-3 py-1.5 text-[12.5px] font-mono text-muted-foreground hover:text-foreground hover:bg-foreground/[0.04] transition-colors"
            >
              <Download className="w-3.5 h-3.5" /> Download CSV
            </button>
            <div className="border-t border-border/15 my-1" />
            <button
              onClick={() => { onSaveWorkspace(); setActionsMenuOpen(false); }}
              className="w-full flex items-center gap-2.5 px-3 py-1.5 text-[12.5px] font-mono text-muted-foreground hover:text-foreground hover:bg-foreground/[0.04] transition-colors"
            >
              <Save className="w-3.5 h-3.5" /> Save Workspace
            </button>
            {seriesCount > 0 && (
              <button
                onClick={() => { onSaveToPackOpen(); setActionsMenuOpen(false); }}
                className="w-full flex items-center gap-2.5 px-3 py-1.5 text-[12.5px] font-mono text-muted-foreground hover:text-foreground hover:bg-foreground/[0.04] transition-colors"
              >
                <FolderOpen className="w-3.5 h-3.5" /> Save to Pack
              </button>
            )}

            {workspaces.length > 0 && (
              <>
                <div className="border-t border-border/15 my-1" />
                <div className="px-3 py-0.5">
                  <span className="stat-label">Workspaces</span>
                </div>
                {workspaces.map((ws) => (
                  <div key={ws.id} className="flex items-center gap-1 px-3 py-1 hover:bg-foreground/[0.04] transition-colors group/ws">
                    <button
                      onClick={() => { onLoadWorkspace(ws.id); setActionsMenuOpen(false); }}
                      className="flex-1 text-left text-[12.5px] font-mono text-muted-foreground hover:text-foreground truncate"
                    >
                      {ws.name}
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); onDeleteWorkspace(ws.id); }}
                      className="w-4 h-4 flex items-center justify-center text-muted-foreground/20 hover:text-destructive opacity-0 group-hover/ws:opacity-100 transition-all shrink-0"
                    >
                      <Trash2 className="w-2.5 h-2.5" />
                    </button>
                  </div>
                ))}
              </>
            )}

            {seriesCount > 0 && (
              <>
                <div className="border-t border-border/15 my-1" />
                <button
                  onClick={() => { onClearAll(); setActionsMenuOpen(false); }}
                  className="w-full flex items-center gap-2.5 px-3 py-1.5 text-[12.5px] font-mono text-destructive/70 hover:text-destructive hover:bg-destructive/[0.06] transition-colors"
                >
                  <RotateCcw className="w-3.5 h-3.5" /> Clear All
                </button>
              </>
            )}
          </div>
        )}
      </div>

      <div className="w-px h-5 bg-border/20 mx-0.5 shrink-0" />

      {/* Right sidebar toggle */}
      <button
        onClick={onToggleRightSidebar}
        className="w-7 h-7 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/30 hover:text-foreground hover:bg-foreground/[0.04] transition-colors shrink-0"
        title={rightSidebarOpen ? 'Hide format panel' : 'Show format panel'}
      >
        {rightSidebarOpen ? <PanelRightClose className="w-3.5 h-3.5" /> : <PanelRightOpen className="w-3.5 h-3.5" />}
      </button>
    </div>
  );
}
