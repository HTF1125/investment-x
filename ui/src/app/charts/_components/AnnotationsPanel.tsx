'use client';

import { X } from 'lucide-react';
import type { Annotation } from './types';

interface AnnotationsPanelProps {
  annotations: Annotation[];
  onAdd: (type: Annotation['type']) => void;
  onUpdate: (id: string, updates: Partial<Annotation>) => void;
  onRemove: (id: string) => void;
  formStyle: React.CSSProperties;
}

export default function AnnotationsPanel({
  annotations,
  onAdd,
  onUpdate,
  onRemove,
  formStyle,
}: AnnotationsPanelProps) {
  return (
    <div className="flex-1 overflow-y-auto custom-scrollbar px-2 py-2">
      {/* Add buttons */}
      <div className="flex items-center justify-between mb-2">
        <span className="stat-label">Add Annotation</span>
        <div className="flex items-center gap-0.5">
          <button onClick={() => onAdd('hline')} className="h-[20px] px-1.5 text-[11px] font-mono font-medium text-muted-foreground/40 hover:text-foreground hover:bg-foreground/[0.04] rounded-[3px] transition-colors" title="Horizontal line">H-Line</button>
          <button onClick={() => onAdd('vline')} className="h-[20px] px-1.5 text-[11px] font-mono font-medium text-muted-foreground/40 hover:text-foreground hover:bg-foreground/[0.04] rounded-[3px] transition-colors" title="Vertical line">V-Line</button>
          <button onClick={() => onAdd('text')} className="h-[20px] px-1.5 text-[11px] font-mono font-medium text-muted-foreground/40 hover:text-foreground hover:bg-foreground/[0.04] rounded-[3px] transition-colors" title="Text annotation">Text</button>
        </div>
      </div>

      {/* Annotation list */}
      <div className="space-y-1">
        {annotations.map((ann) => (
          <div key={ann.id} className="flex items-center gap-1.5 py-1 px-1.5 rounded-[var(--radius)] bg-foreground/[0.015] border border-border/10 group/ann">
            <input
              type="color"
              value={ann.color}
              onChange={(e) => onUpdate(ann.id, { color: e.target.value })}
              className="w-4 h-4 rounded cursor-pointer border-0 p-0 shrink-0"
            />
            <span className="text-[11px] font-mono text-muted-foreground/50 shrink-0 w-5">{ann.type === 'hline' ? 'H' : ann.type === 'vline' ? 'V' : 'T'}</span>
            {ann.type === 'hline' && (
              <input type="number" value={ann.y ?? 0} onChange={(e) => onUpdate(ann.id, { y: parseFloat(e.target.value) || 0 })}
                className="w-14 h-5 px-1 text-[11.5px] font-mono text-center border border-border/30 rounded-[3px] bg-background text-foreground focus:outline-none" step="any" />
            )}
            {ann.type === 'vline' && (
              <>
                <input type="date" value={ann.x || ''} onChange={(e) => onUpdate(ann.id, { x: e.target.value })}
                  className="h-5 px-1 text-[11px] font-mono border border-border/30 rounded-[3px] bg-background text-foreground focus:outline-none flex-1 min-w-0" style={formStyle} />
                <input type="text" value={ann.text || ''} onChange={(e) => onUpdate(ann.id, { text: e.target.value })} placeholder="Lbl"
                  className="w-10 h-5 px-1 text-[11px] font-mono border border-border/30 rounded-[3px] bg-background text-foreground focus:outline-none" />
              </>
            )}
            {ann.type === 'text' && (
              <input type="text" value={ann.text || ''} onChange={(e) => onUpdate(ann.id, { text: e.target.value })} placeholder="Text"
                className="flex-1 min-w-0 h-5 px-1 text-[11px] font-mono border border-border/30 rounded-[3px] bg-background text-foreground focus:outline-none" />
            )}
            <button onClick={() => onRemove(ann.id)}
              className="w-4 h-4 flex items-center justify-center text-muted-foreground/15 hover:text-destructive opacity-0 group-hover/ann:opacity-100 transition-all shrink-0">
              <X className="w-2.5 h-2.5" />
            </button>
          </div>
        ))}
        {annotations.length === 0 && (
          <p className="text-[11.5px] text-muted-foreground/25 py-3 text-center">No annotations yet</p>
        )}
      </div>
    </div>
  );
}
