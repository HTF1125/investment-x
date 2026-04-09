'use client';

import { X } from 'lucide-react';
import type { Pane } from './types';

interface PaneControlsProps {
  panes: Pane[];
  onRemovePane: (paneId: number) => void;
}

export default function PaneControls({ panes, onRemovePane }: PaneControlsProps) {
  if (panes.length <= 1) return null;

  return (
    <div className="shrink-0 border-t border-border/20 px-2 py-1 flex flex-wrap items-center gap-1 bg-foreground/[0.015]">
      <span className="stat-label">Panes</span>
      {panes.map((p) => (
        <div key={p.id} className="flex items-center gap-0.5 bg-card border border-border/30 rounded-[3px] pl-1.5 pr-0.5 h-[18px]">
          <span className="text-[11px] font-mono text-muted-foreground/60">{p.label}</span>
          <button onClick={() => onRemovePane(p.id)} className="w-3.5 h-3.5 flex items-center justify-center text-muted-foreground/20 hover:text-destructive transition-colors">
            <X className="w-2.5 h-2.5" />
          </button>
        </div>
      ))}
    </div>
  );
}
