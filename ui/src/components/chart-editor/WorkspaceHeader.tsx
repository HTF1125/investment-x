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
    <header className="h-10 shrink-0 flex items-center justify-between px-3 border-b border-border/30 bg-card relative z-20">
      <div className="flex items-center gap-2.5 min-w-0 flex-1">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          readOnly={!canEditCurrentChart}
          className="bg-transparent text-[13px] font-semibold text-foreground placeholder:text-muted-foreground/30 focus:outline-none truncate min-w-0 flex-shrink read-only:pointer-events-none read-only:text-foreground/70"
          placeholder="Untitled Analysis"
        />
        <div className="hidden sm:flex items-center gap-1.5 shrink-0">
          <div className="w-px h-3 bg-border/30" />
          <span className="text-[10px] font-mono text-muted-foreground/35 truncate max-w-[100px]">{category || 'Uncategorized'}</span>
          {createdByLabel && (
            <>
              <span className="text-muted-foreground/20 text-[10px]">·</span>
              <span className="text-[10px] font-mono text-muted-foreground/30 truncate max-w-[80px]">{createdByLabel}</span>
            </>
          )}
        </div>
      </div>

      <div className="flex items-center gap-0.5 shrink-0">
        {/* Run — primary CTA */}
        <button
          onClick={handlePreview}
          disabled={loading}
          className="btn-primary h-7 px-3 mr-1"
          title="Run (Ctrl+Enter)"
        >
          {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3 fill-current" />}
          <span>Run</span>
        </button>

        {/* Save */}
        <button
          onClick={handleSave}
          disabled={saving || !canEditCurrentChart}
          className="btn-icon disabled:opacity-30"
          title="Save (Ctrl+S)"
          aria-label="Save (Ctrl+S)"
        >
          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
        </button>

        {/* Properties */}
        <button
          onClick={() => setShowMeta(!showMeta)}
          className={`btn-icon ${showMeta ? 'text-primary bg-primary/10' : ''}`}
          title="Properties"
          aria-label="Properties"
        >
          <Settings className="w-3.5 h-3.5" />
        </button>

        <div className="w-px h-4 bg-border/25 mx-0.5" />

        {/* Chart toggle */}
        <button
          onClick={togglePreview}
          className={`btn-icon ${showPreview ? 'text-primary bg-primary/10' : ''}`}
          title={showPreview ? 'Hide Chart' : 'Show Chart'}
          aria-label={showPreview ? 'Hide Chart' : 'Show Chart'}
        >
          <BarChart3 className="w-3.5 h-3.5" />
        </button>

        {/* Code toggle */}
        <button
          onClick={toggleCode}
          className={`btn-icon ${showCode ? 'text-primary bg-primary/10' : ''}`}
          title={showCode ? 'Hide Code' : 'Show Code'}
          aria-label={showCode ? 'Hide Code' : 'Show Code'}
        >
          <Code className="w-3.5 h-3.5" />
        </button>

        {mode === 'integrated' && onClose && (
          <>
            <div className="w-px h-4 bg-border/25 mx-0.5" />
            <button
              onClick={onClose}
              className="btn-icon"
              title="Back to Dashboard"
              aria-label="Back to Dashboard"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </>
        )}
      </div>
    </header>
  );
}
