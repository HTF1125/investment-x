'use client';

import { Terminal, Table2 } from 'lucide-react';

interface StatusBarProps {
  activeWorkspaceId: string | null;
  workspaceName: string;
  seriesCount: number;
  isFetching: boolean;
  showStats: boolean;
  onToggleStats: () => void;
  expressionMode: boolean;
  onToggleCode: () => void;
}

export default function StatusBar({
  activeWorkspaceId,
  workspaceName,
  seriesCount,
  isFetching,
  showStats,
  onToggleStats,
  expressionMode,
  onToggleCode,
}: StatusBarProps) {
  return (
    <div className="h-6 shrink-0 border-t border-border/20 flex items-center px-2.5 gap-3 bg-foreground/[0.015] text-[11px] font-mono text-muted-foreground/40 select-none">
      {/* Workspace name */}
      {activeWorkspaceId && (
        <>
          <span className="text-primary/60 truncate max-w-[120px]" title={workspaceName}>
            {workspaceName || 'Untitled'}
          </span>
          <div className="w-px h-3 bg-border/20" />
        </>
      )}

      {/* Series count */}
      <span>{seriesCount > 0 ? `${seriesCount} series` : 'No series'}</span>

      {/* Data freshness */}
      <div className="w-px h-3 bg-border/20" />
      <span>{isFetching ? 'Loading...' : 'Ready'}</span>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Toggle buttons */}
      <button
        onClick={onToggleStats}
        className={`h-4 px-1 flex items-center gap-0.5 rounded-[2px] transition-colors ${
          showStats ? 'text-primary/60' : 'text-muted-foreground/25 hover:text-muted-foreground/50'
        }`}
        title="Toggle statistics"
      >
        <Table2 className="w-3 h-3" />
        <span>Stats</span>
      </button>
      <button
        onClick={onToggleCode}
        className={`h-4 px-1 flex items-center gap-0.5 rounded-[2px] transition-colors ${
          expressionMode ? 'text-primary/60' : 'text-muted-foreground/25 hover:text-muted-foreground/50'
        }`}
        title="Toggle code editor (Ctrl+E)"
      >
        <Terminal className="w-3 h-3" />
        <span>Code</span>
      </button>

      <div className="w-px h-3 bg-border/20" />

      {/* Keyboard hints */}
      <span className="text-muted-foreground/20">
        <kbd className="px-0.5">^E</kbd> Code
        {' '}
        <kbd className="px-0.5">^S</kbd> Save
        {' '}
        <kbd className="px-0.5">^B</kbd> Panels
      </span>
    </div>
  );
}
