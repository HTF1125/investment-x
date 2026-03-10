'use client';

import React from 'react';
import { Loader2, Play, Save, Code, Settings, X, BarChart3 } from 'lucide-react';

interface WorkspaceHeaderProps {
  name: string;
  setName: (name: string) => void;
  category: string;
  createdByLabel: string;
  canEditCurrentChart: boolean;
  loading: boolean;
  saving: boolean;
  showMeta: boolean;
  setShowMeta: (show: boolean) => void;
  showPreview: boolean;
  togglePreview: () => void;
  showCode: boolean;
  toggleCode: () => void;
  handlePreview: () => void;
  handleSave: () => void;
  mode: 'standalone' | 'integrated';
  onClose?: () => void;
}

export default function WorkspaceHeader({
  name,
  setName,
  category,
  createdByLabel,
  canEditCurrentChart,
  loading,
  saving,
  showMeta,
  setShowMeta,
  showPreview,
  togglePreview,
  showCode,
  toggleCode,
  handlePreview,
  handleSave,
  mode,
  onClose,
}: WorkspaceHeaderProps) {
  return (
    <header className="h-11 shrink-0 flex items-center justify-between px-3 border-b border-border/50 bg-background relative z-20">
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          readOnly={!canEditCurrentChart}
          className="bg-transparent text-[13px] font-medium text-foreground placeholder-muted-foreground focus:outline-none truncate min-w-0 flex-shrink read-only:opacity-60"
          placeholder="Untitled Analysis"
        />
        <div className="hidden sm:flex items-center gap-1 text-[11px] text-muted-foreground/50 shrink-0">
          <span>{category || 'Uncategorized'}</span>
          <span className="opacity-40">&middot;</span>
          <span className="truncate max-w-[80px]">{createdByLabel}</span>
        </div>
      </div>

      <div className="flex items-center gap-0.5 shrink-0">
        <button
          onClick={handlePreview}
          disabled={loading}
          className="h-7 px-3 bg-primary text-primary-foreground rounded-md text-[12px] font-medium hover:opacity-80 transition-opacity disabled:opacity-40 flex items-center gap-1.5 mr-1"
          title="Run (Ctrl+Enter)"
        >
          {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3 fill-current" />}
          <span>Run</span>
        </button>
        <button
          onClick={handleSave}
          disabled={saving || !canEditCurrentChart}
          className="p-1.5 rounded-md transition-all text-muted-foreground/40 hover:text-muted-foreground hover:bg-primary/10 disabled:opacity-30"
          title="Save (Ctrl+S)"
        >
          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
        </button>
        <button
          onClick={() => setShowMeta(!showMeta)}
          className={`p-1.5 rounded-md transition-all ${showMeta ? 'text-foreground bg-primary/10' : 'text-muted-foreground/40 hover:text-muted-foreground hover:bg-primary/10'}`}
          title="Properties"
        >
          <Settings className="w-3.5 h-3.5" />
        </button>

        <div className="w-px h-4 bg-border/30 mx-0.5" />

        {/* Chart toggle */}
        <button
          onClick={togglePreview}
          className={`p-1.5 rounded-md transition-all ${showPreview ? 'text-foreground bg-primary/10' : 'text-muted-foreground/40 hover:text-muted-foreground hover:bg-primary/10'}`}
          title={showPreview ? 'Hide Chart' : 'Show Chart'}
        >
          <BarChart3 className="w-3.5 h-3.5" />
        </button>
        {/* Code toggle */}
        <button
          onClick={toggleCode}
          className={`p-1.5 rounded-md transition-all ${showCode ? 'text-foreground bg-primary/10' : 'text-muted-foreground/40 hover:text-muted-foreground hover:bg-primary/10'}`}
          title={showCode ? 'Hide Code' : 'Show Code'}
        >
          <Code className="w-3.5 h-3.5" />
        </button>

        {mode === 'integrated' && onClose && (
          <>
            <div className="w-px h-4 bg-border/60 mx-1" />
            <button
              onClick={onClose}
              className="p-1.5 rounded-md text-muted-foreground/40 hover:text-muted-foreground hover:bg-primary/10 transition-all"
              title="Back to Dashboard"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </>
        )}
      </div>
    </header>
  );
}
